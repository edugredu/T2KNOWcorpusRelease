#!/usr/bin/env python3
"""Recover source-document metadata and licence evidence for T2KNOW texts.

The script is intentionally conservative. It finds candidate publications from
released abstract text, records the API evidence, and emits a reviewable table.
It does not overwrite canonical source metadata.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


EUROPE_PMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
CROSSREF_WORKS = "https://api.crossref.org/works"
OPENALEX_SEARCH = "https://api.openalex.org/works"
OPENALEX_WORK = "https://api.openalex.org/works/doi:{doi}"
UNPAYWALL = "https://api.unpaywall.org/v2/{doi}"

PERMISSIVE_LICENSES = {
    "cc0",
    "public-domain",
    "pd",
    "cc-by",
    "cc-by-sa",
}

RESTRICTED_CC_LICENSES = {
    "cc-by-nc",
    "cc-by-nd",
    "cc-by-nc-sa",
    "cc-by-nc-nd",
}

UNCLEAR_LICENSE_MARKERS = {
    "",
    "none",
    "null",
    "unknown",
    "implied-oa",
}

SECTION_HEADINGS = (
    "Abstract",
    "Background",
    "Objective",
    "Objectives",
    "Introduction",
    "Methods",
    "Method",
    "Results",
    "Result",
    "Conclusion",
    "Conclusions",
    "Significance",
)

AUDIT_FIELDS = [
    "doc_id",
    "split",
    "source_file",
    "sha256_txt",
    "match_confidence",
    "match_reason",
    "query_used",
    "source_title",
    "doi",
    "pmid",
    "pmcid",
    "publication_year",
    "journal",
    "publisher",
    "epmc_is_open_access",
    "epmc_license",
    "openalex_is_oa",
    "openalex_oa_status",
    "openalex_licenses",
    "unpaywall_is_oa",
    "unpaywall_oa_status",
    "unpaywall_licenses",
    "crossref_license_urls",
    "source_text_decision",
    "decision_rationale",
]

CANDIDATE_FIELDS = [
    "doc_id",
    "split",
    "source_file",
    "provider",
    "candidate_rank",
    "candidate_title",
    "candidate_doi",
    "candidate_year",
    "candidate_venue",
    "candidate_oa_status",
    "candidate_licenses",
    "abstract_support",
    "support_reason",
    "query_used",
]

STOPWORDS = {
    "about",
    "above",
    "after",
    "again",
    "against",
    "among",
    "because",
    "before",
    "being",
    "between",
    "brain",
    "could",
    "disease",
    "diseases",
    "during",
    "from",
    "have",
    "into",
    "more",
    "most",
    "neurodegenerative",
    "other",
    "patients",
    "should",
    "such",
    "than",
    "that",
    "their",
    "these",
    "this",
    "through",
    "using",
    "were",
    "which",
    "with",
}


def normalize_text(text: str) -> str:
    text = repair_section_heading_spacing(text)
    text = text.lower().replace("’", "'").replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", text).strip()


def repair_section_heading_spacing(text: str) -> str:
    """Repair common abstract heading artifacts such as 'IntroductionWe'."""
    for heading in SECTION_HEADINGS:
        text = re.sub(rf"\b({heading})(?=[A-Z][a-z])", rf"\1 ", text)
    return text


def normalize_license(value: str | None) -> str:
    if not value:
        return ""
    value = value.strip().lower()
    value = re.sub(r"\s+", "-", value)
    value = value.rstrip("/")
    if "creativecommons.org/publicdomain/zero" in value:
        return "cc0"
    match = re.search(r"creativecommons\.org/licenses/([^/]+)/", value)
    if match:
        return match.group(1).lower()
    if value.startswith("https://openalex.org/licenses/"):
        return value.rsplit("/", 1)[-1].lower()
    if value.startswith("cc_"):
        return value.replace("_", "-")
    return value


def iter_license_tokens(values: list[str]) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        if not value:
            continue
        for token in str(value).split("|"):
            normalized = normalize_license(token)
            if normalized.startswith("by-"):
                normalized = "cc-" + normalized
            elif normalized == "by":
                normalized = "cc-by"
            if normalized:
                tokens.add(normalized)
    return tokens


def first_sentence_or_prefix(text: str, max_chars: int) -> str:
    text = repair_section_heading_spacing(text)
    text = re.sub(r"\s+", " ", text).strip()
    match = re.search(r"(.{40,}?[.!?])\s", text)
    candidate = match.group(1) if match else text
    return candidate[:max_chars].strip()


def abstract_phrases(text: str, *, max_chars: int) -> list[str]:
    """Build exact search phrases from several positions in the abstract."""
    text = repair_section_heading_spacing(text)
    text = re.sub(r"\s+", " ", text).strip()
    words = text.split()
    phrases: list[str] = []

    candidates = [
        first_sentence_or_prefix(text, max_chars),
        text[:max_chars].strip(),
    ]
    if len(words) >= 18:
        starts = [0, max(0, len(words) // 5), max(0, len(words) // 2), max(0, (len(words) * 4) // 5 - 18)]
        for start in starts:
            phrase = " ".join(words[start : start + 18])
            if len(phrase) > max_chars:
                phrase = " ".join(words[start : start + 12])
            candidates.append(phrase)

    seen = set()
    for candidate in candidates:
        candidate = candidate.strip(" .,;:")
        if len(candidate) < 40:
            continue
        key = normalize_text(candidate)
        if key not in seen:
            seen.add(key)
            phrases.append(candidate)
    return phrases


def distinctive_keyword_query(text: str, max_terms: int = 12) -> str:
    text = normalize_text(text)
    tokens = re.findall(r"[a-z0-9β]+", text)
    counts: dict[str, int] = {}
    for token in tokens:
        if len(token) < 4 or token in STOPWORDS:
            continue
        counts[token] = counts.get(token, 0) + 1
    ranked = sorted(counts, key=lambda token: (-counts[token], tokens.index(token)))
    return " ".join(ranked[:max_terms])


def candidate_queries(text: str, max_chars: int) -> list[str]:
    phrases = abstract_phrases(text, max_chars=max_chars)
    queries: list[str] = []
    for phrase in phrases[:4]:
        queries.append(f'"{phrase}"')
    keyword_query = distinctive_keyword_query(text)
    if keyword_query:
        queries.append(keyword_query)
    seen = set()
    deduped = []
    for query in queries:
        if query not in seen:
            seen.add(query)
            deduped.append(query)
    return deduped


def load_cache(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def save_cache(path: Path, cache: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(cache, handle, indent=2, sort_keys=True)
    tmp.replace(path)


def http_json(url: str, *, user_agent: str, timeout: int = 30) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def http_text(url: str, *, user_agent: str, timeout: int = 30) -> tuple[str, str]:
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace"), response.geturl()


def cached_get(
    cache: dict[str, Any],
    key: str,
    url: str,
    user_agent: str,
    sleep: float,
    *,
    retries: int = 0,
    retry_sleep: float = 10.0,
) -> dict[str, Any]:
    if key in cache:
        return cache[key]
    data: dict[str, Any] = {}
    for attempt in range(retries + 1):
        try:
            data = http_json(url, user_agent=user_agent)
            break
        except urllib.error.HTTPError as exc:
            data = {"_error": f"HTTP {exc.code}: {exc.reason}"}
            if exc.code == 429 and attempt < retries:
                time.sleep(retry_sleep * (attempt + 1))
                continue
            break
        except Exception as exc:  # pragma: no cover - defensive for API/network instability
            data = {"_error": f"{type(exc).__name__}: {exc}"}
            break
    # Do not persist transient rate-limit failures; a later run with a slower
    # sleep interval should be allowed to retry them.
    if "HTTP 429" not in data.get("_error", ""):
        cache[key] = data
    if sleep:
        time.sleep(sleep)
    return data


def cached_get_text(cache: dict[str, Any], key: str, url: str, user_agent: str, sleep: float) -> dict[str, str]:
    if key in cache:
        return cache[key]
    try:
        text, final_url = http_text(url, user_agent=user_agent)
        data = {"text": text, "final_url": final_url}
    except urllib.error.HTTPError as exc:
        data = {"_error": f"HTTP {exc.code}: {exc.reason}", "text": "", "final_url": url}
    except Exception as exc:  # pragma: no cover - defensive for API/network instability
        data = {"_error": f"{type(exc).__name__}: {exc}", "text": "", "final_url": url}
    cache[key] = data
    if sleep:
        time.sleep(sleep)
    return data


def reconstruct_openalex_abstract(index: dict[str, list[int]] | None) -> str:
    if not index:
        return ""
    positions: list[tuple[int, str]] = []
    for token, token_positions in index.items():
        for position in token_positions:
            positions.append((position, token))
    return " ".join(token for _, token in sorted(positions))


def search_europe_pmc(text: str, cache: dict[str, Any], user_agent: str, sleep: float, max_chars: int) -> dict[str, Any]:
    phrases = abstract_phrases(text, max_chars=max_chars)
    queries = [f'"{phrase}"' for phrase in phrases]
    if phrases:
        # Keep one broad fallback, but do not treat its title-only matches as high confidence.
        queries.append(phrases[0][:220].strip())
    all_results: list[dict[str, Any]] = []
    queries_used: list[str] = []
    for query in queries:
        params = {
            "format": "json",
            "pageSize": "5",
            "resultType": "core",
            "query": query,
        }
        url = EUROPE_PMC + "?" + urllib.parse.urlencode(params)
        key = "epmc:" + hashlib.sha256(query.encode("utf-8")).hexdigest()
        data = cached_get(cache, key, url, user_agent, sleep)
        if data.get("_error"):
            return data
        results = data.get("resultList", {}).get("result", [])
        if results:
            queries_used.append(query)
            all_results.extend(results)
    if all_results:
        deduped: list[dict[str, Any]] = []
        seen_ids = set()
        for result in all_results:
            result_id = result.get("doi") or result.get("pmid") or result.get("id") or result.get("title")
            if result_id in seen_ids:
                continue
            seen_ids.add(result_id)
            deduped.append(result)
        return {
            "hitCount": str(len(deduped)),
            "resultList": {"result": deduped},
            "_query_used": " || ".join(queries_used),
        }
    return {"hitCount": "0", "resultList": {"result": []}, "_query_used": queries[-1]}


def search_openalex(
    text: str,
    cache: dict[str, Any],
    user_agent: str,
    sleep: float,
    max_chars: int,
    openalex_email: str = "",
    openalex_api_key: str = "",
) -> dict[str, Any]:
    phrases = abstract_phrases(text, max_chars=max_chars)
    queries = [f'"{phrase}"' for phrase in phrases]
    all_results: list[dict[str, Any]] = []
    queries_used: list[str] = []
    for query in queries:
        params = {
            "per-page": "5",
            "search": query,
            "select": "id,doi,title,publication_year,open_access,primary_location,locations,abstract_inverted_index,ids",
        }
        if openalex_email:
            params["mailto"] = openalex_email
        if openalex_api_key:
            params["api_key"] = openalex_api_key
        url = OPENALEX_SEARCH + "?" + urllib.parse.urlencode(params)
        key = "openalex-search:" + hashlib.sha256(query.encode("utf-8")).hexdigest()
        data = cached_get(cache, key, url, user_agent, sleep, retries=2, retry_sleep=10)
        if data.get("_error"):
            return data
        results = data.get("results", [])
        if results:
            queries_used.append(query)
            all_results.extend(results)
    if all_results:
        deduped: list[dict[str, Any]] = []
        seen_ids = set()
        for result in all_results:
            result_id = result.get("doi") or result.get("id") or result.get("title")
            if result_id in seen_ids:
                continue
            seen_ids.add(result_id)
            deduped.append(result)
        return {
            "hitCount": str(len(deduped)),
            "results": deduped,
            "_query_used": " || ".join(queries_used),
        }
    return {"hitCount": "0", "results": [], "_query_used": queries[-1] if queries else ""}


def get_crossref(doi: str, cache: dict[str, Any], user_agent: str, sleep: float) -> dict[str, Any]:
    url = f"{CROSSREF_WORKS}/{urllib.parse.quote(doi)}"
    return cached_get(cache, "crossref:" + doi.lower(), url, user_agent, sleep)


def get_openalex(
    doi: str,
    cache: dict[str, Any],
    user_agent: str,
    sleep: float,
    openalex_email: str = "",
    openalex_api_key: str = "",
) -> dict[str, Any]:
    url = OPENALEX_WORK.format(doi=urllib.parse.quote(doi))
    params = {}
    if openalex_email:
        params["mailto"] = openalex_email
    if openalex_api_key:
        params["api_key"] = openalex_api_key
    if params:
        url += "?" + urllib.parse.urlencode(params)
    return cached_get(cache, "openalex:" + doi.lower(), url, user_agent, sleep, retries=2, retry_sleep=10)


def openalex_work_supports_text(text: str, data: dict[str, Any]) -> tuple[bool, str]:
    abstract = normalize_text(reconstruct_openalex_abstract(data.get("abstract_inverted_index")))
    if not abstract:
        return False, "openalex_work_no_abstract"
    text_norm = normalize_text(text)
    phrase_norms = [normalize_text(phrase) for phrase in abstract_phrases(text, max_chars=220)]
    if text_norm[:220] in abstract:
        return True, "openalex_work_abstract_prefix_exact_match"
    if text_norm[:160] in abstract:
        return True, "openalex_work_abstract_prefix_short_match"
    if any(phrase and phrase in abstract for phrase in phrase_norms):
        return True, "openalex_work_abstract_phrase_match"
    return False, "openalex_work_no_abstract_text_support"


def get_unpaywall(doi: str, email: str, cache: dict[str, Any], user_agent: str, sleep: float) -> dict[str, Any]:
    url = UNPAYWALL.format(doi=urllib.parse.quote(doi)) + "?" + urllib.parse.urlencode({"email": email})
    return cached_get(cache, "unpaywall:" + doi.lower(), url, user_agent, sleep)


def pick_epmc_match(text: str, data: dict[str, Any]) -> tuple[dict[str, Any] | None, str, str]:
    results = data.get("resultList", {}).get("result", [])
    if not results:
        return None, "no_match", "0"

    text_norm = normalize_text(text)
    phrase_norms = [normalize_text(phrase) for phrase in abstract_phrases(text, max_chars=220)]
    best: tuple[int, dict[str, Any], str] | None = None
    for result in results:
        abstract = normalize_text(result.get("abstractText") or "")
        score = 0
        reason = "no_abstract_text_support"
        if abstract and text_norm[:220] in abstract:
            score = 100
            reason = "abstract_prefix_exact_match"
        elif abstract and text_norm[:160] in abstract:
            score = 95
            reason = "abstract_prefix_short_match"
        elif abstract and any(phrase and phrase in abstract for phrase in phrase_norms):
            score = 90
            reason = "abstract_phrase_match"
        if best is None or score > best[0]:
            best = (score, result, reason)

    assert best is not None
    confidence = "high" if best[0] >= 90 else "manual_review"
    return best[1], confidence, best[2]


def pick_openalex_match(text: str, data: dict[str, Any]) -> tuple[dict[str, Any] | None, str, str]:
    results = data.get("results", [])
    if not results:
        return None, "no_match", "0"

    text_norm = normalize_text(text)
    phrase_norms = [normalize_text(phrase) for phrase in abstract_phrases(text, max_chars=220)]
    best: tuple[int, dict[str, Any], str] | None = None
    for result in results:
        abstract = normalize_text(reconstruct_openalex_abstract(result.get("abstract_inverted_index")))
        score = 0
        reason = "no_abstract_text_support"
        if abstract and text_norm[:220] in abstract:
            score = 100
            reason = "openalex_abstract_prefix_exact_match"
        elif abstract and text_norm[:160] in abstract:
            score = 95
            reason = "openalex_abstract_prefix_short_match"
        elif abstract and any(phrase and phrase in abstract for phrase in phrase_norms):
            score = 90
            reason = "openalex_abstract_phrase_match"
        if best is None or score > best[0]:
            best = (score, result, reason)

    assert best is not None
    confidence = "high" if best[0] >= 90 else "manual_review"
    if confidence != "high":
        return best[1], confidence, best[2]

    result = best[1]
    doi = str(result.get("doi") or "").removeprefix("https://doi.org/")
    primary_location = result.get("primary_location") or {}
    source = primary_location.get("source") or {}
    ids = result.get("ids") or {}
    match = {
        "doi": doi,
        "pmid": str(ids.get("pmid") or "").removeprefix("https://pubmed.ncbi.nlm.nih.gov/"),
        "pmcid": str(ids.get("pmcid") or "").removeprefix("https://www.ncbi.nlm.nih.gov/pmc/articles/"),
        "title": result.get("title") or "",
        "pubYear": str(result.get("publication_year") or ""),
        "journalTitle": source.get("display_name") or "",
        "isOpenAccess": "Y" if (result.get("open_access") or {}).get("is_oa") else "N",
        "license": primary_location.get("license") or "",
    }
    return match, confidence, best[2]


def support_from_abstract(text: str, abstract: str) -> tuple[str, str]:
    abstract_norm = normalize_text(abstract)
    if not abstract_norm:
        return "no", "no_candidate_abstract"
    text_norm = normalize_text(text)
    phrase_norms = [normalize_text(phrase) for phrase in abstract_phrases(text, max_chars=220)]
    if text_norm[:220] in abstract_norm:
        return "yes", "candidate_abstract_prefix_exact_match"
    if text_norm[:160] in abstract_norm:
        return "yes", "candidate_abstract_prefix_short_match"
    if any(phrase and phrase in abstract_norm for phrase in phrase_norms):
        return "yes", "candidate_abstract_phrase_match"
    return "no", "candidate_abstract_no_text_support"


def support_from_candidate_page(text: str, doi: str, cache: dict[str, Any], args: argparse.Namespace) -> tuple[str, str]:
    if not doi:
        return "no", "no_candidate_doi_for_page_check"
    url = "https://doi.org/" + doi
    key = "candidate-page:" + hashlib.sha256(url.encode("utf-8")).hexdigest()
    page = cached_get_text(cache, key, url, args.user_agent, args.sleep)
    if page.get("_error"):
        return "no", "candidate_page_fetch_error"
    html = page.get("text", "")
    text_content = re.sub(r"<script\\b.*?</script>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    text_content = re.sub(r"<style\\b.*?</style>", " ", text_content, flags=re.IGNORECASE | re.DOTALL)
    text_content = re.sub(r"<[^>]+>", " ", text_content)
    text_content = re.sub(r"&nbsp;|&#160;", " ", text_content)
    support, reason = support_from_abstract(text, text_content)
    if support == "yes":
        return support, "candidate_page_" + reason
    return support, "candidate_page_no_text_support"


def collect_candidate_rows(row: dict[str, str], args: argparse.Namespace, cache: dict[str, Any]) -> list[dict[str, str]]:
    text_path = Path(row["_text_path"])
    text = text_path.read_text(encoding="utf-8", errors="replace")
    candidates: list[dict[str, str]] = []
    seen = set()

    for query in candidate_queries(text, args.snippet_chars):
        params = {
            "per-page": str(args.candidate_limit_per_query),
            "search": query,
            "select": "id,doi,title,publication_year,open_access,primary_location,locations,abstract_inverted_index,ids",
        }
        if args.openalex_email:
            params["mailto"] = args.openalex_email
        if args.openalex_api_key:
            params["api_key"] = args.openalex_api_key
        url = OPENALEX_SEARCH + "?" + urllib.parse.urlencode(params)
        key = "openalex-candidate:" + hashlib.sha256(query.encode("utf-8")).hexdigest()
        data = cached_get(cache, key, url, args.user_agent, args.sleep, retries=2, retry_sleep=10)
        if not data.get("_error"):
            for result in data.get("results", []):
                doi = str(result.get("doi") or "").removeprefix("https://doi.org/")
                title = result.get("title") or ""
                result_id = doi or result.get("id") or title
                if not result_id or result_id in seen:
                    continue
                seen.add(result_id)
                primary_location = result.get("primary_location") or {}
                source = primary_location.get("source") or {}
                abstract = reconstruct_openalex_abstract(result.get("abstract_inverted_index"))
                support, support_reason = support_from_abstract(text, abstract)
                if support != "yes" and args.fetch_candidate_pages:
                    support, support_reason = support_from_candidate_page(text, doi, cache, args)
                open_access = result.get("open_access") or {}
                licences = []
                if primary_location.get("license"):
                    licences.append(str(primary_location["license"]))
                for location in result.get("locations") or []:
                    if location.get("license"):
                        licences.append(str(location["license"]))
                candidates.append(
                    {
                        "doc_id": row.get("doc_id", ""),
                        "split": row.get("split", ""),
                        "source_file": row.get("source_file", ""),
                        "provider": "openalex",
                        "candidate_rank": "",
                        "candidate_title": title,
                        "candidate_doi": doi,
                        "candidate_year": str(result.get("publication_year") or ""),
                        "candidate_venue": str(source.get("display_name") or ""),
                        "candidate_oa_status": str(open_access.get("oa_status") or ""),
                        "candidate_licenses": "|".join(sorted(set(licences))),
                        "abstract_support": support,
                        "support_reason": support_reason,
                        "query_used": query,
                    }
                )

        params = {
            "rows": str(args.candidate_limit_per_query),
            "query.bibliographic": query,
        }
        url = CROSSREF_WORKS + "?" + urllib.parse.urlencode(params)
        key = "crossref-candidate:" + hashlib.sha256(query.encode("utf-8")).hexdigest()
        data = cached_get(cache, key, url, args.user_agent, args.sleep)
        if data.get("_error"):
            continue
        for result in data.get("message", {}).get("items", []):
            doi = result.get("DOI") or ""
            title = (result.get("title") or [""])[0]
            result_id = doi or title
            if not result_id or result_id in seen:
                continue
            seen.add(result_id)
            licences = extract_crossref_licenses({"message": result})
            candidates.append(
                {
                    "doc_id": row.get("doc_id", ""),
                    "split": row.get("split", ""),
                    "source_file": row.get("source_file", ""),
                    "provider": "crossref",
                    "candidate_rank": "",
                    "candidate_title": title,
                    "candidate_doi": doi,
                    "candidate_year": str(((result.get("published-print") or result.get("published-online") or {}).get("date-parts") or [[""]])[0][0]),
                    "candidate_venue": str((result.get("container-title") or [""])[0]),
                    "candidate_oa_status": "",
                    "candidate_licenses": "|".join(licences),
                    "abstract_support": "unknown",
                    "support_reason": "crossref_no_abstract_available",
                    "query_used": query,
                }
            )

    def score(candidate: dict[str, str]) -> tuple[int, int, int, str]:
        support_score = 0 if candidate["abstract_support"] == "yes" else 1
        provider_score = 0 if candidate["provider"] == "openalex" else 1
        doi_score = 0 if candidate["candidate_doi"] else 1
        return (support_score, provider_score, doi_score, candidate["candidate_title"])

    candidates = sorted(candidates, key=score)[: args.candidate_limit_per_row]
    for index, candidate in enumerate(candidates, start=1):
        candidate["candidate_rank"] = str(index)
    return candidates


def extract_crossref_licenses(data: dict[str, Any]) -> list[str]:
    message = data.get("message", {})
    licenses = []
    for item in message.get("license") or []:
        if isinstance(item, dict) and item.get("URL"):
            licenses.append(item["URL"])
    return licenses


def extract_openalex_licenses(data: dict[str, Any]) -> tuple[str, str, str]:
    open_access = data.get("open_access") or {}
    licences = []
    for location in data.get("locations") or []:
        licence = location.get("license") or location.get("license_id")
        if licence:
            licences.append(str(licence))
    return (
        str(open_access.get("is_oa", "")),
        str(open_access.get("oa_status", "")),
        "|".join(sorted(set(licences))),
    )


def extract_unpaywall(data: dict[str, Any]) -> tuple[str, str, str]:
    if not data or data.get("_error"):
        return "", "", ""
    licences = []
    for location in data.get("oa_locations") or []:
        if location.get("license"):
            licences.append(str(location["license"]))
    best = data.get("best_oa_location") or {}
    if best.get("license"):
        licences.append(str(best["license"]))
    return str(data.get("is_oa", "")), str(data.get("oa_status", "")), "|".join(sorted(set(licences)))


def classify_decision(licence_values: list[str], oa_statuses: list[str], api_errors: list[str]) -> tuple[str, str]:
    normalized = iter_license_tokens(licence_values)
    normalized.discard("")
    statuses = {status.lower() for status in oa_statuses if status}

    if normalized & RESTRICTED_CC_LICENSES:
        return "exclude_text", "restrictive_cc_licence:" + "|".join(sorted(normalized & RESTRICTED_CC_LICENSES))
    if normalized & PERMISSIVE_LICENSES:
        return "include_text", "clear_permissive_licence:" + "|".join(sorted(normalized & PERMISSIVE_LICENSES))
    if any("springer.com/tdm" in value.lower() for value in licence_values):
        return "exclude_text", "tdm_licence_only"
    if "bronze" in statuses or "closed" in statuses:
        return "exclude_text", "oa_status_not_redistributable:" + "|".join(sorted(statuses))
    if normalized - UNCLEAR_LICENSE_MARKERS:
        return "exclude_text", "unclassified_licence:" + "|".join(sorted(normalized))
    if api_errors:
        return "manual_review", "api_error:" + "|".join(api_errors)
    return "exclude_text", "no_clear_redistribution_licence"


def read_source_rows(source_metadata: Path, release_root: Path, limit: int | None) -> list[dict[str, str]]:
    rows = []
    with source_metadata.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            path = release_root / row["brat_txt_path"]
            if not path.exists():
                path = release_root / "data" / "t2know-core-v1.0" / "brat_core" / row["split"] / row["source_file"]
            row["_text_path"] = str(path)
            rows.append(row)
            if limit is not None and len(rows) >= limit:
                break
    return rows


def read_previous_audit(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Previous audit not found: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["doc_id"]: row for row in csv.DictReader(handle, delimiter="\t")}


def audit_row(row: dict[str, str], args: argparse.Namespace, cache: dict[str, Any]) -> dict[str, str]:
    text_path = Path(row["_text_path"])
    text = text_path.read_text(encoding="utf-8", errors="replace")

    epmc = search_europe_pmc(text, cache, args.user_agent, args.sleep, args.snippet_chars)
    api_errors = []
    if epmc.get("_error"):
        api_errors.append("epmc")
    match, confidence, match_reason = pick_epmc_match(text, epmc) if not epmc.get("_error") else (None, "api_error", "epmc_error")
    query_used = str(epmc.get("_query_used", ""))

    if confidence != "high" and args.openalex_fallback:
        openalex_search = search_openalex(
            text,
            cache,
            args.user_agent,
            args.sleep,
            args.snippet_chars,
            args.openalex_email,
            args.openalex_api_key,
        )
        if openalex_search.get("_error"):
            api_errors.append("openalex-search")
        else:
            fallback_match, fallback_confidence, fallback_reason = pick_openalex_match(text, openalex_search)
            if fallback_confidence == "high":
                match, confidence, match_reason = fallback_match, fallback_confidence, fallback_reason
                query_used = str(openalex_search.get("_query_used", ""))

    doi = (match or {}).get("doi") or ""
    pmid = (match or {}).get("pmid") or ""
    pmcid = (match or {}).get("pmcid") or ""
    title = (match or {}).get("title") or ""
    journal = ((match or {}).get("journalInfo") or {}).get("journal", {}).get("title") or (match or {}).get("journalTitle") or ""
    pub_year = (match or {}).get("pubYear") or ""
    epmc_is_oa = str((match or {}).get("isOpenAccess") or "")
    epmc_license = str((match or {}).get("license") or "")

    crossref_licenses: list[str] = []
    crossref_publisher = ""
    if doi:
        crossref = get_crossref(doi, cache, args.user_agent, args.sleep)
        if crossref.get("_error"):
            api_errors.append("crossref")
        else:
            crossref_licenses = extract_crossref_licenses(crossref)
            crossref_publisher = str(crossref.get("message", {}).get("publisher") or "")

    openalex_is_oa = openalex_status = openalex_licenses = ""
    openalex_work: dict[str, Any] | None = None
    if doi:
        openalex_work = get_openalex(doi, cache, args.user_agent, args.sleep, args.openalex_email, args.openalex_api_key)
        if openalex_work.get("_error"):
            api_errors.append("openalex")
        else:
            openalex_is_oa, openalex_status, openalex_licenses = extract_openalex_licenses(openalex_work)

    if confidence != "high" and openalex_work is not None and not openalex_work.get("_error"):
        supported, support_reason = openalex_work_supports_text(text, openalex_work)
        if supported:
            confidence = "high"
            match_reason = support_reason

    unpaywall_is_oa = unpaywall_status = unpaywall_licenses = ""
    if doi and args.unpaywall_email:
        unpaywall = get_unpaywall(doi, args.unpaywall_email, cache, args.user_agent, args.sleep)
        if unpaywall.get("_error"):
            api_errors.append("unpaywall")
        else:
            unpaywall_is_oa, unpaywall_status, unpaywall_licenses = extract_unpaywall(unpaywall)

    licence_values = [epmc_license, openalex_licenses, unpaywall_licenses, *crossref_licenses]
    oa_statuses = [openalex_status, unpaywall_status]
    decision, rationale = classify_decision(licence_values, oa_statuses, api_errors)
    if confidence != "high":
        decision = "manual_review"
        rationale = f"match_{confidence}:{match_reason}; {rationale}"

    return {
        "doc_id": row.get("doc_id", ""),
        "split": row.get("split", ""),
        "source_file": row.get("source_file", ""),
        "sha256_txt": row.get("sha256_txt", ""),
        "match_confidence": confidence,
        "match_reason": match_reason,
        "query_used": query_used,
        "source_title": title,
        "doi": doi,
        "pmid": pmid,
        "pmcid": pmcid,
        "publication_year": pub_year,
        "journal": journal,
        "publisher": crossref_publisher,
        "epmc_is_open_access": epmc_is_oa,
        "epmc_license": epmc_license,
        "openalex_is_oa": openalex_is_oa,
        "openalex_oa_status": openalex_status,
        "openalex_licenses": openalex_licenses,
        "unpaywall_is_oa": unpaywall_is_oa,
        "unpaywall_oa_status": unpaywall_status,
        "unpaywall_licenses": unpaywall_licenses,
        "crossref_license_urls": "|".join(crossref_licenses),
        "source_text_decision": decision,
        "decision_rationale": rationale,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-metadata",
        default="release/T2KNOW-release/data/t2know-core-v1.0/metadata/source_metadata.tsv",
        help="TSV with doc_id, split, source_file, brat_txt_path, and checksums.",
    )
    parser.add_argument(
        "--release-root",
        default="release/T2KNOW-release",
        help="Root directory for paths recorded in source metadata.",
    )
    parser.add_argument(
        "--output",
        default="release/T2KNOW-release/provenance/reports/source_license_audit.tsv",
        help="Output TSV path.",
    )
    parser.add_argument(
        "--cache",
        default="release/T2KNOW-release/provenance/cache/source_license_audit_cache.json",
        help="JSON cache for API responses.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Audit only the first N rows.")
    parser.add_argument(
        "--previous-audit",
        default="",
        help="Existing audit TSV to reuse. Rows not selected by --only-previous-decisions are copied unchanged.",
    )
    parser.add_argument(
        "--only-previous-decisions",
        default="",
        help="Comma-separated source_text_decision values to re-audit from --previous-audit, e.g. manual_review.",
    )
    parser.add_argument("--snippet-chars", type=int, default=240, help="Maximum snippet length for search.")
    parser.add_argument("--sleep", type=float, default=0.1, help="Delay between uncached API calls.")
    parser.add_argument(
        "--no-openalex-fallback",
        action="store_false",
        dest="openalex_fallback",
        help="Disable OpenAlex search fallback for rows not matched through Europe PMC.",
    )
    parser.add_argument(
        "--candidate-output",
        default="",
        help="Write ranked source candidates for rows selected from --previous-audit instead of producing an audit table.",
    )
    parser.add_argument(
        "--candidate-limit-per-query",
        type=int,
        default=5,
        help="Candidate-search mode: maximum API results retained per query and provider.",
    )
    parser.add_argument(
        "--candidate-limit-per-row",
        type=int,
        default=20,
        help="Candidate-search mode: maximum ranked candidates written per source row.",
    )
    parser.add_argument(
        "--fetch-candidate-pages",
        action="store_true",
        help="Candidate-search mode: fetch DOI landing pages to verify candidates whose API abstract is unavailable.",
    )
    parser.add_argument(
        "--unpaywall-email",
        default="",
        help="Optional email required by Unpaywall API. If omitted, Unpaywall is skipped.",
    )
    parser.add_argument(
        "--openalex-email",
        default="",
        help="Optional email passed as OpenAlex mailto parameter to reduce rate limiting.",
    )
    parser.add_argument(
        "--openalex-api-key",
        default=os.environ.get("OPENALEX_API_KEY", ""),
        help="Optional OpenAlex API key. Defaults to OPENALEX_API_KEY environment variable.",
    )
    parser.add_argument(
        "--user-agent",
        default="T2KNOW-source-license-audit/0.1 (mailto:unknown@example.org)",
        help="User-Agent sent to metadata APIs.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_metadata = Path(args.source_metadata)
    release_root = Path(args.release_root)
    output = Path(args.output)
    cache_path = Path(args.cache)

    rows = read_source_rows(source_metadata, release_root, args.limit)
    previous_rows: dict[str, dict[str, str]] = {}
    selected_decisions: set[str] = set()
    if args.previous_audit:
        previous_rows = read_previous_audit(Path(args.previous_audit))
        selected_decisions = {value.strip() for value in args.only_previous_decisions.split(",") if value.strip()}
        if not selected_decisions:
            raise ValueError("--only-previous-decisions is required when --previous-audit is used")

    cache = load_cache(cache_path)
    if args.candidate_output:
        if not previous_rows:
            raise ValueError("--candidate-output requires --previous-audit")
        candidate_rows = []
        searched = 0
        copied = 0
        for index, row in enumerate(rows, start=1):
            previous = previous_rows.get(row.get("doc_id", ""))
            if previous is None or previous.get("source_text_decision") not in selected_decisions:
                copied += 1
                continue
            candidate_rows.extend(collect_candidate_rows(row, args, cache))
            searched += 1
            save_cache(cache_path, cache)
            print(f"candidate-searched {searched}; skipped {copied}; processed {index}/{len(rows)}", file=sys.stderr)
        save_cache(cache_path, cache)
        candidate_output = Path(args.candidate_output)
        candidate_output.parent.mkdir(parents=True, exist_ok=True)
        with candidate_output.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CANDIDATE_FIELDS, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(candidate_rows)
        print(json.dumps({"searched": searched, "candidates": len(candidate_rows), "output": str(candidate_output)}, indent=2))
        return 0

    audited = []
    rechecked = 0
    copied = 0
    for index, row in enumerate(rows, start=1):
        previous = previous_rows.get(row.get("doc_id", ""))
        if previous is not None and previous.get("source_text_decision") not in selected_decisions:
            audited.append({field: previous.get(field, "") for field in AUDIT_FIELDS})
            copied += 1
        else:
            audited.append(audit_row(row, args, cache))
            rechecked += 1
        if rechecked and rechecked % 25 == 0:
            save_cache(cache_path, cache)
            print(f"rechecked {rechecked}; copied {copied}; processed {index}/{len(rows)}", file=sys.stderr)
    save_cache(cache_path, cache)

    output.parent.mkdir(parents=True, exist_ok=True)
    fields = AUDIT_FIELDS
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(audited)

    counts: dict[str, int] = {}
    for row in audited:
        counts[row["source_text_decision"]] = counts.get(row["source_text_decision"], 0) + 1
    print(json.dumps({"rows": len(audited), "rechecked": rechecked, "copied": copied, "decisions": counts, "output": str(output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

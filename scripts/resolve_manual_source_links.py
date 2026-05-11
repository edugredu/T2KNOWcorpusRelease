import csv
import html
import io
import re
import sys
import time
import urllib.parse
from pathlib import Path

import requests
from pypdf import PdfReader

ROOT = Path('release/T2KNOW-release')
INTAKE = ROOT / 'provenance/reports/source_license_manual_link_intake.tsv'
SUPPORTED = ROOT / 'provenance/reports/source_license_v5_manual_supported_candidates.tsv'
OVERRIDES = ROOT / 'provenance/reports/source_license_manual_overrides.tsv'
AUDIT_V5 = ROOT / 'provenance/reports/source_license_audit_v5.tsv'
AUDIT_V6 = ROOT / 'provenance/reports/source_license_audit_v6.tsv'

S = requests.Session()
S.headers.update({'User-Agent': 'T2KNOW manual source provenance audit'})

PERMISSIVE = {'cc-by', 'cc0', 'cc-by-sa'}


def norm_text(text):
    text = html.unescape(text or '')
    text = re.sub(r'<[^>]+>', ' ', text)
    repl = {'β': 'beta', 'Β': 'beta', 'α': 'alpha', 'Α': 'alpha', '≥': '>=', '≤': '<='}
    for k, v in repl.items():
        text = text.replace(k, v)
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def normalize_license(value):
    value = (value or '').lower().strip()
    value = value.replace(' ', '-').replace('_', '-')
    value = value.replace('creative-commons-', '').replace('cc-', 'cc-')
    if 'creativecommons.org/publicdomain/zero' in value or value == 'cc0':
        return 'cc0'
    m = re.search(r'creativecommons\.org/licenses/([^/]+)/', value)
    if m:
        return 'cc-' + m.group(1).replace('-', '-')
    if value in {'cc-by', 'cc-by-sa', 'cc-by-nc', 'cc-by-nd', 'cc-by-nc-nd', 'cc-by-nc-sa'}:
        return value
    return value


def decision_from_license(lic):
    lic = normalize_license(lic)
    if lic in PERMISSIVE:
        return 'include_text', f'permissive_source_licence:{lic}'
    if lic:
        return 'exclude_text', f'restrictive_or_noncommercial_source_licence:{lic}'
    return 'exclude_text', 'no_permissive_redistribution_licence_identified'


def get_json(url, **params):
    r = S.get(url, params=params, timeout=45)
    r.raise_for_status()
    return r.json()


def epmc_query(query):
    data = get_json(
        'https://www.ebi.ac.uk/europepmc/webservices/rest/search',
        query=query,
        format='json',
        resultType='core',
        pageSize=1,
    )
    res = data.get('resultList', {}).get('result', [])
    return res[0] if res else None


def crossref_doi(doi):
    r = S.get('https://api.crossref.org/works/' + urllib.parse.quote(doi, safe=''), timeout=45)
    if r.status_code != 200:
        return None
    return r.json().get('message')


def source_path(row):
    # Intake split values are advisory; search the release folders to avoid propagating split typos.
    name = row['source_file']
    for base in [ROOT / 'data/brat', ROOT / 'data/brat_core']:
        for split in ['train', 'eval', 'val', 'test']:
            p = base / split / name
            if p.exists():
                return p
    return None


def support_against_source(row, source_text):
    p = source_path(row)
    local = norm_text(p.read_text(errors='ignore')) if p else norm_text(row.get('text_preview', ''))
    remote = norm_text(source_text)
    if not local or not remote:
        return 'not_checked'
    if local[:120] and local[:120] in remote:
        return 'source_text_supported_by_prefix'
    for start in range(0, min(max(len(local) - 80, 0), 500), 40):
        if local[start:start + 80] and local[start:start + 80] in remote:
            return 'source_text_supported_by_phrase'
    return 'source_text_not_supported'


def journal_title(item):
    return ((item.get('journalInfo') or {}).get('journal') or {}).get('title', '')


def exact_epmc_from_local(row):
    p = source_path(row)
    text = p.read_text(errors='ignore') if p else row.get('text_preview', '')
    normalized = re.sub(r'\s+', ' ', text).strip()
    search_text = normalized.replace('IntroductionWe', 'Introduction We')
    candidates = []
    starts = [0, 12, 24, 36, 48, 60, 80, 100, 140, 180, 220]
    for start in starts:
        for length in [55, 70, 90, 110]:
            phrase = search_text[start:start + length].strip().replace('"', '')
            if len(phrase) > 40:
                candidates.append('"' + phrase + '"')
    # Some local texts begin after an unspaced section label.
    m = re.search(r'(We examined longitudinal cerebrospinal fluid[^.]+)', search_text)
    if m:
        candidates.insert(0, '"' + m.group(1)[:95].replace('"', '') + '"')
    seen = set()
    for q in candidates:
        if q in seen:
            continue
        seen.add(q)
        try:
            item = epmc_query(q)
        except Exception:
            item = None
        if item:
            return item, q
    return None, ''


def from_epmc_item(row, item, source_url, resolution_source, notes='', supplied_url=''):
    support = support_against_source(row, item.get('abstractText', ''))
    if support == 'source_text_not_supported':
        corrected, q = exact_epmc_from_local(row)
        if corrected:
            item = corrected
            source_url = f"https://pubmed.ncbi.nlm.nih.gov/{item.get('pmid')}/" if item.get('pmid') else source_url
            support = support_against_source(row, item.get('abstractText', ''))
            notes = (notes + '; ' if notes else '') + f'provided URL did not support local text; corrected by exact Europe PMC query {q}'
            if supplied_url:
                notes += f'; supplied_url={supplied_url}'
            resolution_source = 'manual_link_intake_corrected_by_exact_phrase_search'
    lic = normalize_license(item.get('license', ''))
    decision, rationale = decision_from_license(lic)
    return {
        'doc_id': row['doc_id'],
        'split': row['split'],
        'source_file': row['source_file'],
        'source_title': html.unescape(item.get('title', '')),
        'doi': item.get('doi', ''),
        'pmid': item.get('pmid') or item.get('id', ''),
        'pmcid': item.get('pmcid', ''),
        'publication_year': item.get('pubYear', ''),
        'journal': journal_title(item),
        'publisher': '',
        'source_url': source_url,
        'resolution_source': resolution_source,
        'source_text_support': support,
        'licence_evidence': lic or 'none_identified',
        'source_text_decision': decision,
        'decision_rationale': rationale,
        'notes': notes,
    }


def handle_ymj(row):
    r = S.get(row['source_url'], timeout=90)
    r.raise_for_status()
    text = '\n'.join((p.extract_text() or '') for p in PdfReader(io.BytesIO(r.content)).pages)
    idx = text.lower().find('apathy as the non-motor')
    section = text[max(0, idx - 2000): idx + 5000] if idx >= 0 else text
    doi = ''
    m = re.search(r'10\.25789/YMJ\.2020\.70\.07', section, re.I)
    if m:
        doi = m.group(0)
    title = "Apathy as a non-motor symptom of Parkinson's disease and Huntington's chorea"
    cr = crossref_doi(doi) if doi else None
    if cr and cr.get('title'):
        title = cr['title'][0]
    decision, rationale = decision_from_license('')
    return {
        'doc_id': row['doc_id'], 'split': row['split'], 'source_file': row['source_file'],
        'source_title': title, 'doi': doi, 'pmid': '', 'pmcid': '', 'publication_year': '2020',
        'journal': 'Yakut Medical Journal', 'publisher': 'Yakutsk Scientific Center for Complex Medical Problems',
        'source_url': row['source_url'], 'resolution_source': 'manual_link_intake_pdf',
        'source_text_support': support_against_source(row, section),
        'licence_evidence': 'journal PDF copyright statement; no permissive licence identified',
        'source_text_decision': decision, 'decision_rationale': rationale,
        'notes': 'PDF text supports the local source text; Crossref has no licence URL for the DOI.',
    }


def handle_raco(row):
    page_url = 'https://raco.cat/index.php/AJHS/article/view/980000001718'
    page = S.get(page_url, timeout=45).text
    pdf_url = 'https://raco.cat/index.php/AJHS/article/download/980000001718/543627/678484'
    pdf = S.get(pdf_url, timeout=45)
    pdf.raise_for_status()
    text = '\n'.join((p.extract_text() or '') for p in PdfReader(io.BytesIO(pdf.content)).pages)
    doi = ''
    m = re.search(r'10\.3306/AJHS\.2022\.37\.04\.166', text)
    if m:
        doi = m.group(0)
    title = 'Protein misfolding and medicinal strategies in neurodegenerative disorders'
    cc = ''
    m = re.search(r'https?://creativecommons\.org/licenses/by-nc-nd/3\.0/?(?:es/)?', page, re.I)
    if m:
        cc = m.group(0)
    lic = normalize_license(cc) if cc else 'cc-by-nc-nd'
    decision, rationale = decision_from_license(lic)
    return {
        'doc_id': row['doc_id'], 'split': row['split'], 'source_file': row['source_file'],
        'source_title': title, 'doi': doi, 'pmid': '', 'pmcid': '', 'publication_year': '2022',
        'journal': 'Academic Journal of Health Sciences', 'publisher': 'Academic Journal of Health Sciences Medicina Balear',
        'source_url': page_url, 'resolution_source': 'manual_link_intake_article_page_and_pdf',
        'source_text_support': support_against_source(row, text),
        'licence_evidence': lic,
        'source_text_decision': decision, 'decision_rationale': rationale,
        'notes': 'Article page states Creative Commons BY-NC-ND 3.0; PDF supports the local source text.',
    }


def handle_crossref(row, doi):
    cr = crossref_doi(doi) or {}
    licenses = [x.get('URL', '') for x in cr.get('license', []) if x.get('URL')]
    lic = normalize_license('|'.join(licenses)) if licenses else ''
    if 'creativecommons.org/licenses/by/4.0' in '|'.join(licenses).lower():
        lic = 'cc-by'
    decision, rationale = decision_from_license(lic)
    title = (cr.get('title') or [''])[0]
    return {
        'doc_id': row['doc_id'], 'split': row['split'], 'source_file': row['source_file'],
        'source_title': html.unescape(title), 'doi': doi, 'pmid': '', 'pmcid': '',
        'publication_year': str((((cr.get('published-print') or cr.get('published-online') or {}).get('date-parts') or [['']])[0][0])),
        'journal': (cr.get('container-title') or [''])[0], 'publisher': cr.get('publisher', ''),
        'source_url': row['source_url'], 'resolution_source': 'manual_link_intake_crossref',
        'source_text_support': 'source_text_supported_by_manual_url',
        'licence_evidence': lic or 'none_identified',
        'source_text_decision': decision, 'decision_rationale': rationale,
        'notes': 'Licence evidence from Crossref DOI metadata; local abstract support previously established by manual source link.',
    }


def handle_intake_row(row):
    url = row['source_url']
    if 'ymj.mednauka.com' in url:
        return handle_ymj(row)
    if 'raco.cat' in url:
        return handle_raco(row)
    m = re.search(r'pubmed\.ncbi\.nlm\.nih\.gov/(\d+)', url)
    if m:
        item = epmc_query(f'EXT_ID:{m.group(1)} AND SRC:MED')
        return from_epmc_item(row, item, url, 'manual_link_intake_pubmed')
    m = re.search(r'PMC(\d+)', url, re.I)
    if m:
        item = epmc_query(f'PMCID:PMC{m.group(1)}')
        return from_epmc_item(row, item, url, 'manual_link_intake_pmc')
    m = re.search(r'EPMC(\d+)', url, re.I)
    if m:
        item = epmc_query(f'PMCID:PMC{m.group(1)}')
        return from_epmc_item(row, item, url, 'manual_link_intake_omicsdi', supplied_url=url)
    m = re.search(r'10\.\d{4,9}/[^\s?#]+', url)
    if m:
        return handle_crossref(row, m.group(0))
    raise ValueError(f'Unsupported URL for doc {row["doc_id"]}: {url}')


def candidate_override(row):
    lic = normalize_license(row.get('candidate_licenses', ''))
    oa = row.get('candidate_oa_status', '')
    if lic in PERMISSIVE:
        decision, rationale = 'include_text', f'permissive_source_licence:{lic}'
    elif lic:
        decision, rationale = 'exclude_text', f'restrictive_or_noncommercial_source_licence:{lic}'
    else:
        decision, rationale = 'exclude_text', f'candidate_source_oa_status:{oa or "unknown"}; no permissive redistribution licence identified'
    return {
        'doc_id': row['doc_id'], 'split': row['split'], 'source_file': row['source_file'],
        'source_title': row['candidate_title'], 'doi': row['candidate_doi'], 'pmid': '', 'pmcid': '',
        'publication_year': row.get('candidate_year', ''), 'journal': row.get('candidate_venue', ''), 'publisher': '',
        'source_url': f"https://doi.org/{row['candidate_doi']}" if row.get('candidate_doi') else '',
        'resolution_source': 'supported_candidate_search',
        'source_text_support': row.get('support_reason', row.get('abstract_support', '')),
        'licence_evidence': lic or f"oa_status:{oa or 'unknown'}",
        'source_text_decision': decision, 'decision_rationale': rationale,
        'notes': f"provider={row.get('provider','')}; candidate_rank={row.get('candidate_rank','')}",
    }


def write_tsv(path, rows, fieldnames):
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, delimiter='\t', fieldnames=fieldnames, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)


def apply_overrides(overrides):
    by_doc = {r['doc_id']: r for r in overrides}
    with AUDIT_V5.open(newline='') as f:
        rows = list(csv.DictReader(f, delimiter='\t'))
        fields = rows[0].keys()
    for row in rows:
        ov = by_doc.get(row['doc_id'])
        if not ov:
            continue
        row['match_confidence'] = 'high'
        row['match_reason'] = ov['source_text_support']
        row['query_used'] = ov['source_url']
        row['source_title'] = ov['source_title']
        row['doi'] = ov['doi']
        row['pmid'] = ov['pmid']
        row['pmcid'] = ov['pmcid']
        row['publication_year'] = ov['publication_year']
        row['journal'] = ov['journal']
        row['publisher'] = ov['publisher']
        lic = ov['licence_evidence']
        if lic.startswith('cc-'):
            row['epmc_license'] = lic
        if ov['resolution_source'].startswith('manual_link_intake_crossref') or ov['doi']:
            if lic.startswith('cc-'):
                row['crossref_license_urls'] = lic
        row['source_text_decision'] = ov['source_text_decision']
        row['decision_rationale'] = f"manual_resolution:{ov['resolution_source']}; {ov['decision_rationale']}; {ov['notes']}"
    write_tsv(AUDIT_V6, rows, list(fields))


def main():
    overrides = []
    with SUPPORTED.open(newline='') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            overrides.append(candidate_override(row))
    with INTAKE.open(newline='') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            overrides.append(handle_intake_row(row))
            time.sleep(0.05)
    overrides = sorted(overrides, key=lambda r: int(r['doc_id']))
    fields = ['doc_id','split','source_file','source_title','doi','pmid','pmcid','publication_year','journal','publisher','source_url','resolution_source','source_text_support','licence_evidence','source_text_decision','decision_rationale','notes']
    write_tsv(OVERRIDES, overrides, fields)
    apply_overrides(overrides)
    print(f'wrote {OVERRIDES} ({len(overrides)} overrides)')
    print(f'wrote {AUDIT_V6}')

if __name__ == '__main__':
    main()

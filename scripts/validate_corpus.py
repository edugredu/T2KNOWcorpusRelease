import json
import argparse
import os
import glob
import re
import csv
from collections import Counter

ALLOWED_JSONL_SPLITS = {"train", "val", "test"}


def load_allowed_labels():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    candidate_paths = [
        os.path.join(root_dir, "T2KNOWcode", "listaCategorias.txt"),
        os.path.join(root_dir, "data", "t2know-core-v1.0", "metadata", "label_schema.tsv"),
    ]
    for labels_path in candidate_paths:
        if not os.path.exists(labels_path):
            continue
        if labels_path.endswith(".tsv"):
            with open(labels_path, newline="", encoding="utf-8") as f:
                return {
                    row["label"].strip()
                    for row in csv.DictReader(f, delimiter="\t")
                    if row.get("label", "").strip()
                }
        with open(labels_path, "r", encoding="utf-8") as f:
            return {line.strip() for line in f if line.strip()}
    raise FileNotFoundError("Could not find label inventory in T2KNOWcode/listaCategorias.txt or data/t2know-core-v1.0/metadata/label_schema.tsv")


def validate_jsonl(file_path, allowed_labels):
    print(f"Validating JSONL file: {file_path}...")
    stats = {"total_sentences": 0, "splits": Counter(), "entities": 0, "errors": 0, "synthetic": 0}
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if not line.strip(): continue
            try:
                data = json.loads(line)
                if data.get('meta', {}).get('is_synthetic', False):
                    stats["synthetic"] += 1
                validate_single_entry(
                    data,
                    i + 1,
                    stats,
                    allowed_labels=allowed_labels,
                    require_meta_fields=("doc_id", "split", "source_file", "is_synthetic"),
                    require_entity_fields=("start", "end", "label", "text", "spans"),
                    allowed_splits=ALLOWED_JSONL_SPLITS,
                    require_spans=True,
                )
            except json.JSONDecodeError:
                print(f"Line {i+1}: Invalid JSON")
                stats["errors"] += 1
    return stats

def validate_json_splits(corpus_dir, allowed_labels):
    print(f"Validating JSON splits in: {corpus_dir}...")
    stats = {"total_sentences": 0, "splits": Counter(), "entities": 0, "errors": 0}
    
    files = ["trainData.json", "trainBalanced.json", "evalData.json", "testData.json"]
    print("  NOTE: JSON splits do not contain entity text labels. Deep text validation (mismatch check) is NOT possible for this format.")
    
    for filename in files:
        path = os.path.join(corpus_dir, filename)
        if not os.path.exists(path):
            print(f"Warning: {filename} not found.")
            continue
            
        print(f"  Checking {filename}...")
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Fix concatenated JSON objects
            content = content.replace('}{', '}\n{')
            
            for i, line in enumerate(content.split('\n')):
                if not line.strip(): continue
                try:
                    data = json.loads(line)
                    # Normalize data structure to match what validate_single_entry expects
                    # JSON splits have 'tags' instead of 'entities', and 'tag' instead of 'label'
                    if 'tags' in data:
                        data['entities'] = []
                        for tag in data['tags']:
                            data['entities'].append({
                                "start": tag['start'],
                                "end": tag['end'],
                                "label": tag['tag'],
                                "text": data['text'][tag['start']:tag['end']] # Extract text since it's not in tags
                            })
                    
                    # Add split info if missing
                    if 'meta' not in data:
                        data['meta'] = {'split': filename.replace('.json', '')}
                        
                    validate_single_entry(
                        data,
                        i + 1,
                        stats,
                        allowed_labels=allowed_labels,
                    )
                    
                except json.JSONDecodeError:
                    print(f"  Line {i+1}: Invalid JSON")
                    stats["errors"] += 1
    return stats

def validate_brat(brat_dir):
    print(f"Validating BRAT folders in: {brat_dir}...")
    stats = {"total_documents": 0, "splits": Counter(), "entities": 0, "errors": 0}
    
    # Check subfolders
    subfolders = ["train", "trainBalanced", "eval", "test"]
    
    for split in subfolders:
        split_dir = os.path.join(brat_dir, split)
        if not os.path.exists(split_dir):
            continue
            
        txt_files = glob.glob(os.path.join(split_dir, "*.txt"))
        print(f"  Checking {split} ({len(txt_files)} files)...")
        
        for txt_path in txt_files:
            stats["total_documents"] += 1
            stats["splits"][split] += 1
            
            ann_path = txt_path.replace('.txt', '.ann')
            if not os.path.exists(ann_path):
                print(f"  Missing .ann file for {os.path.basename(txt_path)}")
                stats["errors"] += 1
                continue
                
            # Read text
            with open(txt_path, 'r', encoding='utf-8') as f:
                text = f.read()
                
            # Read annotations
            with open(ann_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if line.startswith('T'):
                        stats["entities"] += 1
                        parts = line.strip().split('\t')
                        if len(parts) < 3: continue
                        
                        # Parse offsets
                        type_span = parts[1]
                        entity_text = parts[2]
                        
                        # Handle "Type Start End" or "Type Start End;Start End"
                        try:
                            first_space = type_span.find(' ')
                            coords_str = type_span[first_space:].strip()
                            
                            spans = []
                            for pair in coords_str.split(';'):
                                start, end = map(int, pair.split())
                                if start < 0 or end > len(text):
                                    print(f"  {os.path.basename(ann_path)}:{line_num}: Invalid offset {start}-{end} (text len {len(text)})")
                                    stats["errors"] += 1
                                    spans = [] # Invalidate
                                    break
                                spans.append((start, end))
                            
                            if not spans: continue
                            
                            # Extract text
                            extracted_parts = [text[s:e] for s, e in spans]
                            extracted = " ".join(extracted_parts)
                            
                            # Compare
                            if extracted != entity_text:
                                # Allow whitespace diffs
                                if extracted.strip() == entity_text.strip():
                                    continue
                                # Allow if entity_text is a subsequence (discontinuous spans flattened)
                                if entity_text.replace(' ', '') in extracted.replace(' ', ''):
                                    continue
                                    
                                print(f"  {os.path.basename(ann_path)}:{line_num}: Text mismatch. Expected '{entity_text}', got '{extracted}'")
                                stats["errors"] += 1
                                
                        except ValueError:
                            print(f"  {os.path.basename(ann_path)}:{line_num}: Malformed span '{type_span}'")
                            stats["errors"] += 1

    return stats

def validate_single_entry(
    data,
    line_num,
    stats,
    allowed_labels=None,
    require_meta_fields=(),
    require_entity_fields=(),
    allowed_splits=None,
    require_spans=False,
):
    stats["total_sentences"] += 1
    
    text = data.get("text", "")
    if not text:
        print(f"Line {line_num}: Missing text")
        stats["errors"] += 1
        return
        
    meta = data.get("meta", {})
    split = meta.get("split", "unknown")
    stats["splits"][split] += 1

    for field in require_meta_fields:
        if field not in meta:
            print(f"Line {line_num}: Missing required meta field '{field}'")
            stats["errors"] += 1
            continue
        if field in {"doc_id", "split", "source_file"} and not meta.get(field):
            print(f"Line {line_num}: Empty required meta field '{field}'")
            stats["errors"] += 1
        if field == "is_synthetic" and not isinstance(meta.get(field), bool):
            print(f"Line {line_num}: meta.is_synthetic must be boolean")
            stats["errors"] += 1

    if allowed_splits and split not in allowed_splits:
        print(f"Line {line_num}: Invalid split '{split}'")
        stats["errors"] += 1

    sentence_index = meta.get("sentence_index")
    if sentence_index is not None:
        if not isinstance(sentence_index, int) or sentence_index < 0:
            print(f"Line {line_num}: meta.sentence_index must be a non-negative integer")
            stats["errors"] += 1
        expected_sentence_id = f"{meta.get('doc_id')}_{sentence_index}"
        if meta.get("sentence_id") and meta.get("sentence_id") != expected_sentence_id:
            print(f"Line {line_num}: meta.sentence_id does not match doc_id and sentence_index")
            stats["errors"] += 1

    document_start = meta.get("document_start")
    document_end = meta.get("document_end")
    if document_start is not None or document_end is not None:
        if not isinstance(document_start, int) or not isinstance(document_end, int):
            print(f"Line {line_num}: meta.document_start and meta.document_end must be integers")
            stats["errors"] += 1
        elif document_start < 0 or document_end < document_start or document_end - document_start != len(text):
            print(f"Line {line_num}: invalid document-relative sentence offsets [{document_start}, {document_end}]")
            stats["errors"] += 1
    
    entities = data.get("entities", [])
    stats["entities"] += len(entities)
    
    for ent in entities:
        for field in require_entity_fields:
            if field not in ent:
                print(f"Line {line_num}: Missing required entity field '{field}'")
                stats["errors"] += 1

        start = ent.get("start")
        end = ent.get("end")
        label = ent.get("label")
        ent_text = ent.get("text")
        
        if start is None or end is None:
            stats["errors"] += 1
            continue

        if label is None or label == "":
            print(f"Line {line_num}: Missing entity label")
            stats["errors"] += 1
            continue

        if allowed_labels and label not in allowed_labels:
            print(f"Line {line_num}: Invalid label '{label}'")
            stats["errors"] += 1

        if "text" in require_entity_fields and not isinstance(ent_text, str):
            print(f"Line {line_num}: Entity text must be present as a string")
            stats["errors"] += 1
            continue

        if require_spans and "spans" not in ent:
            print(f"Line {line_num}: Missing required entity field 'spans'")
            stats["errors"] += 1
            continue
            
        if 'spans' in ent:
            if not isinstance(ent['spans'], list) or not ent['spans']:
                print(f"Line {line_num}: Entity spans must be a non-empty list")
                stats["errors"] += 1
                continue
            # Reconstruct text from spans
            extracted_parts = []
            for span in ent['spans']:
                if not isinstance(span, (list, tuple)) or len(span) != 2:
                    print(f"Line {line_num}: Malformed span '{span}'")
                    stats["errors"] += 1
                    extracted_parts = []
                    break
                s, e = span
                if s < 0 or e > len(text) or s > e:
                    print(f"Line {line_num}: Invalid span offsets [{s}, {e}] for text len {len(text)}")
                    stats["errors"] += 1
                    extracted_parts = []
                    break
                extracted_parts.append(text[s:e])
            if not extracted_parts:
                continue
            extracted = " ".join(extracted_parts)
        else:
            if start < 0 or end > len(text) or start > end:
                print(f"Line {line_num}: Invalid offsets [{start}, {end}] for text len {len(text)}")
                stats["errors"] += 1
                continue
            extracted = text[start:end]

        if ent_text and extracted != ent_text:
             # Allow whitespace diffs
            if extracted.strip() == ent_text.strip():
                continue
            # Allow if ent_text is a subsequence (discontinuous spans flattened)
            if ent_text.replace(' ', '') in extracted.replace(' ', ''):
                continue
                
            print(f"Line {line_num}: Text mismatch. Expected '{ent_text}', got '{extracted}'")
            stats["errors"] += 1

def print_stats(stats):
    print("\nValidation Results:")
    if "total_documents" in stats:
        print(f"Total Documents: {stats['total_documents']}")
    else:
        print(f"Total Sentences: {stats['total_sentences']}")
    print(f"Total Entities: {stats['entities']}")
    if "synthetic" in stats:
        print(f"Synthetic Sentences: {stats['synthetic']}")
    print(f"Splits: {dict(stats['splits'])}")
    print(f"Errors: {stats['errors']}")
    
    if stats['errors'] == 0:
        print("SUCCESS: Corpus is valid.")
    else:
        print("FAILURE: Corpus has errors.")

def get_doc_ids_from_json(corpus_dir):
    doc_ids = {"train": set(), "trainBalanced": set(), "eval": set(), "test": set()}
    files = {
        "train": "trainData.json",
        "trainBalanced": "trainBalanced.json",
        "eval": "evalData.json",
        "test": "testData.json"
    }
    
    for split, filename in files.items():
        path = os.path.join(corpus_dir, filename)
        if not os.path.exists(path): continue
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read().replace('}{', '}\n{')
            for line in content.split('\n'):
                if not line.strip(): continue
                try:
                    data = json.loads(line)
                    doc_id = data['id'].split('_')[0]
                    doc_ids[split].add(doc_id)
                except: pass
    return doc_ids

def get_doc_ids_from_jsonl(file_path):
    doc_ids = {"train": set(), "trainBalanced": set(), "eval": set(), "test": set()} # trainBalanced might not be in JSONL if not explicitly mapped
    # Note: JSONL usually only has train/val/test. If trainBalanced is separate, we need to know how it's labeled.
    # Based on previous steps, we only mapped train/val/test to JSONL.
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            try:
                data = json.loads(line)
                split = data.get('meta', {}).get('split', 'unknown')
                # Map split names if needed (val -> eval)
                if split == 'val': split = 'eval'
                
                if split in doc_ids:
                    doc_id = data.get('meta', {}).get('doc_id')
                    if not doc_id:
                        # Try to extract from source_file
                        src = data.get('meta', {}).get('source_file', '')
                        match = re.search(r'text(\d+)\.txt', src)
                        if match: doc_id = match.group(1)
                    
                    if doc_id:
                        doc_ids[split].add(doc_id)
            except: pass
    return doc_ids

def get_doc_ids_from_brat(brat_dir):
    doc_ids = {"train": set(), "trainBalanced": set(), "eval": set(), "test": set()}
    for split in doc_ids:
        split_dir = os.path.join(brat_dir, split)
        if not os.path.exists(split_dir): continue
        
        for txt_path in glob.glob(os.path.join(split_dir, "*text*.txt")):
            basename = os.path.basename(txt_path)
            match = re.search(r'text(\d+)\.txt', basename)
            if match:
                doc_ids[split].add(match.group(1))
    return doc_ids

def compare_formats(corpus_dir):
    print("Comparing formats...")
    
    json_ids = get_doc_ids_from_json(corpus_dir)
    brat_ids = get_doc_ids_from_brat(os.path.join(corpus_dir, "BRATformat"))
    # JSONL path
    jsonl_path = os.path.join(corpus_dir, "t2know.jsonl")
    jsonl_ids = get_doc_ids_from_jsonl(jsonl_path) if os.path.exists(jsonl_path) else None
    
    splits = ["train", "eval", "test"] # trainBalanced is usually a subset or separate, let's check main splits first
    
    all_match = True
    
    for split in splits:
        print(f"\nChecking split: {split}")
        j_set = json_ids[split]
        b_set = brat_ids[split]
        
        print(f"  JSON Docs: {len(j_set)}")
        print(f"  BRAT Docs: {len(b_set)}")
        
        if j_set != b_set:
            print("  MISMATCH between JSON and BRAT!")
            only_in_j = j_set - b_set
            only_in_b = b_set - j_set
            if only_in_j: print(f"    In JSON only: {list(only_in_j)[:5]}...")
            if only_in_b: print(f"    In BRAT only: {list(only_in_b)[:5]}...")
            all_match = False
        else:
            print("  JSON and BRAT match.")
            
        if jsonl_ids:
            l_set = jsonl_ids[split]
            print(f"  JSONL Docs: {len(l_set)}")
            
            # JSONL might use 'val' instead of 'eval', handled in loader
            if j_set != l_set:
                 print("  MISMATCH between JSON and JSONL!")
                 only_in_j = j_set - l_set
                 only_in_l = l_set - j_set
                 if only_in_j: print(f"    In JSON only: {list(only_in_j)[:5]}...")
                 if only_in_l: print(f"    In JSONL only: {list(only_in_l)[:5]}...")
                 all_match = False
            else:
                print("  JSON and JSONL match.")
    
    # Check trainBalanced if present in BRAT
    if brat_ids["trainBalanced"]:
        print(f"\nChecking split: trainBalanced")
        j_set = json_ids["trainBalanced"]
        b_set = brat_ids["trainBalanced"]
        print(f"  JSON Docs: {len(j_set)}")
        print(f"  BRAT Docs: {len(b_set)}")
        if j_set != b_set:
            print("  MISMATCH between JSON and BRAT!")
            all_match = False
        else:
            print("  JSON and BRAT match.")

    if all_match:
        print("\nSUCCESS: All formats are consistent.")
    else:
        print("\nFAILURE: Inconsistencies found.")

def infer_format(path):
    if os.path.isdir(path):
        if os.path.exists(os.path.join(path, "document_disjoint")):
            return "core"
        if any(os.path.exists(os.path.join(path, name)) for name in ("trainData.json", "evalData.json", "testData.json")):
            return "json"
        return "brat"
    if path.endswith(".jsonl"):
        return "jsonl"
    return "json"


def load_audit_statuses():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    audit_path = os.path.join(os.path.dirname(script_dir), "provenance", "reports", "source_license_audit_v6.tsv")
    statuses = {}
    if not os.path.exists(audit_path):
        return statuses
    import csv
    with open(audit_path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            statuses[row["doc_id"]] = "included" if row["source_text_decision"] == "include_text" else "excluded"
    return statuses


def validate_public_record(data, line_num, stats, allowed_labels, audit_statuses, source_name="<record>", split_file=None):
    meta = data.get("meta", {})
    doc_id = str(meta.get("doc_id") or data.get("id", "").split("_")[0])
    expected_status = audit_statuses.get(doc_id)
    status = meta.get("text_redistribution_status")
    if status is None and meta.get("source_text_decision"):
        status = "included" if meta.get("source_text_decision") == "include_text" else "excluded"
    if expected_status and status != expected_status:
        print(f"{source_name}:{line_num}: text status for doc {doc_id} is {status!r}, expected {expected_status!r}")
        stats["errors"] += 1
    status = status or expected_status or "included"
    split = meta.get("split", "unknown")
    if split == "val":
        split = "eval"
    stats["splits"][split] += 1
    stats["total_sentences"] += 1

    text = data.get("text")
    entities = data.get("entities")
    if entities is None and "tags" in data:
        entities = [{"start": tag["start"], "end": tag["end"], "label": tag["tag"], "spans": [[tag["start"], tag["end"]]]} for tag in data["tags"]]
    entities = entities or []
    stats["entities"] += len(entities)

    required_meta = {
        "doc_id",
        "split",
        "source_file",
        "sentence_index",
        "sentence_sha256",
        "text_available_in_archive",
        "requires_reconstruction",
        "text_redistribution_status",
        "brat_available_in_archive",
        "source_text_policy",
        "offset_basis",
        "annotation_checksum",
    }
    for field in required_meta:
        if field not in meta:
            print(f"{source_name}:{line_num}: missing meta.{field}")
            stats["errors"] += 1

    if status == "excluded":
        if text is not None:
            print(f"{source_name}:{line_num}: excluded record contains text")
            stats["errors"] += 1
        if meta.get("brat_txt_path") or meta.get("brat_ann_path"):
            print(f"{source_name}:{line_num}: excluded record retains BRAT path metadata")
            stats["errors"] += 1
        if meta.get("text_available_in_archive") is not False or meta.get("requires_reconstruction") is not True:
            print(f"{source_name}:{line_num}: excluded record has inconsistent reconstruction flags")
            stats["errors"] += 1
    else:
        if not isinstance(text, str) or not text:
            print(f"{source_name}:{line_num}: included record is missing text")
            stats["errors"] += 1
            text = ""
        if meta.get("text_available_in_archive") is not True or meta.get("requires_reconstruction") is not False:
            print(f"{source_name}:{line_num}: included record has inconsistent reconstruction flags")
            stats["errors"] += 1

    if split_file:
        expected_split = {"trainData.json": "train", "evalData.json": "eval", "testData.json": "test"}[split_file]
        if split != expected_split:
            print(f"{source_name}:{line_num}: split {split!r} does not match {split_file}")
            stats["errors"] += 1

    for ent in entities:
        label = ent.get("label") or ent.get("tag")
        if label not in allowed_labels:
            print(f"{source_name}:{line_num}: invalid label {label!r}")
            stats["errors"] += 1
        start = ent.get("start")
        end = ent.get("end")
        spans = ent.get("spans", [[start, end]])
        if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end < start:
            print(f"{source_name}:{line_num}: invalid offsets {start}-{end}")
            stats["errors"] += 1
            continue
        if status == "excluded":
            if ent.get("text") is not None:
                print(f"{source_name}:{line_num}: excluded record contains entity surface text")
                stats["errors"] += 1
            continue
        if end > len(text):
            print(f"{source_name}:{line_num}: offsets {start}-{end} exceed text length {len(text)}")
            stats["errors"] += 1
            continue
        if "text" in ent and ent.get("text") is not None:
            extracted = " ".join(text[s:e] for s, e in spans)
            if extracted != ent["text"] and extracted.strip() != ent["text"].strip():
                print(f"{source_name}:{line_num}: entity text mismatch")
                stats["errors"] += 1


def validate_jsonl_mode(file_path, allowed_labels, mode):
    if mode not in {"public-redacted", "reconstructed-full"}:
        return validate_jsonl(file_path, allowed_labels)
    stats = {"total_sentences": 0, "splits": Counter(), "entities": 0, "errors": 0, "synthetic": 0}
    audit_statuses = load_audit_statuses()
    with open(file_path, encoding="utf-8") as handle:
        for line_num, line in enumerate(handle, 1):
            if not line.strip():
                continue
            data = json.loads(line)
            if mode == "reconstructed-full" and data.get("text") is None:
                print(f"{file_path}:{line_num}: reconstructed-full record has text=null")
                stats["errors"] += 1
            validate_public_record(data, line_num, stats, allowed_labels, audit_statuses, source_name=file_path)
    return stats


def validate_json_splits_mode(corpus_dir, allowed_labels, mode):
    if mode not in {"public-redacted", "reconstructed-full"}:
        return validate_json_splits(corpus_dir, allowed_labels)
    stats = {"total_sentences": 0, "splits": Counter(), "entities": 0, "errors": 0}
    audit_statuses = load_audit_statuses()
    for filename in ("trainData.json", "evalData.json", "testData.json"):
        path = os.path.join(corpus_dir, filename)
        if not os.path.exists(path):
            print(f"Warning: {filename} not found.")
            continue
        with open(path, encoding="utf-8") as handle:
            for line_num, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                data = json.loads(line)
                if mode == "reconstructed-full" and data.get("text") is None:
                    print(f"{path}:{line_num}: reconstructed-full record has text=null")
                    stats["errors"] += 1
                validate_public_record(data, line_num, stats, allowed_labels, audit_statuses, source_name=path, split_file=filename)
    return stats


def validate_brat_mode(brat_dir, mode, scope):
    if mode != "public-redacted":
        return validate_brat(brat_dir)
    audit_statuses = load_audit_statuses()
    stats = {"total_documents": 0, "splits": Counter(), "entities": 0, "errors": 0}
    search_dirs = []
    documents_dir = os.path.join(brat_dir, "documents")
    if os.path.isdir(documents_dir):
        search_dirs.append(("documents", documents_dir))
    else:
        for split in ("train", "eval", "test"):
            split_dir = os.path.join(brat_dir, split)
            if os.path.isdir(split_dir):
                search_dirs.append((split, split_dir))
    for name, folder in search_dirs:
        for txt_path in glob.glob(os.path.join(folder, "*.txt")):
            basename = os.path.basename(txt_path)
            match = re.search(r"text(\d+)\.txt", basename)
            doc_id = match.group(1) if match else None
            if doc_id and audit_statuses.get(doc_id) == "excluded":
                print(f"{txt_path}: BRAT text exists for text-excluded doc {doc_id}")
                stats["errors"] += 1
            stats["total_documents"] += 1
            stats["splits"][name] += 1
            ann_path = txt_path[:-4] + ".ann"
            if not os.path.exists(ann_path):
                print(f"{txt_path}: missing .ann")
                stats["errors"] += 1
                continue
            text = open(txt_path, encoding="utf-8").read()
            for line_num, line in enumerate(open(ann_path, encoding="utf-8"), 1):
                if not line.startswith("T"):
                    continue
                stats["entities"] += 1
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 3:
                    print(f"{ann_path}:{line_num}: malformed BRAT annotation")
                    stats["errors"] += 1
                    continue
                coords = parts[1].split(" ", 1)[1]
                try:
                    extracted = " ".join(text[int(s):int(e)] for s, e in (pair.split() for pair in coords.split(";")))
                except Exception:
                    print(f"{ann_path}:{line_num}: malformed offsets")
                    stats["errors"] += 1
                    continue
                if extracted != parts[2] and extracted.strip() != parts[2].strip():
                    print(f"{ann_path}:{line_num}: text mismatch")
                    stats["errors"] += 1
    return stats


def validate_core_dir(path, allowed_labels, mode, scope):
    stats = {"total_sentences": 0, "splits": Counter(), "entities": 0, "errors": 0, "synthetic": 0}
    if mode == "public-redacted" and os.path.isdir(os.path.join(path, "document_disjoint_hybrid")):
        document_dir = os.path.join(path, "document_disjoint_hybrid")
        jsonl_path = os.path.join(document_dir, "t2know_document_disjoint_hybrid.jsonl")
        brat_path = os.path.join(path, "text_included", "brat_core")
    else:
        document_dir = os.path.join(path, "document_disjoint")
        jsonl_path = os.path.join(document_dir, "t2know_document_disjoint.jsonl")
        brat_path = os.path.join(path, "brat_core")
    checks = [
        validate_jsonl_mode(jsonl_path, allowed_labels, mode),
        validate_json_splits_mode(document_dir, allowed_labels, mode),
    ]
    if os.path.exists(brat_path):
        checks.append(validate_brat_mode(brat_path, mode, scope))
    for result in checks:
        stats["errors"] += result.get("errors", 0)
        stats["entities"] += result.get("entities", 0)
        stats["total_sentences"] += result.get("total_sentences", 0)
        stats["synthetic"] += result.get("synthetic", 0)
        stats["splits"].update(result.get("splits", {}))
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate T2KNOW corpus formats")
    parser.add_argument("path", help="Path to file or directory")
    parser.add_argument("--format", choices=["jsonl", "json", "brat", "compare", "core"], help="Format to validate")
    parser.add_argument("--mode", choices=["legacy-full", "public-redacted", "reconstructed-full"], default="legacy-full")
    parser.add_argument("--scope", choices=["all", "text-included"], default="all")

    args = parser.parse_args()
    allowed_labels = load_allowed_labels()
    fmt = args.format or infer_format(args.path)

    if fmt == "core":
        stats = validate_core_dir(args.path, allowed_labels, args.mode, args.scope)
        print_stats(stats)
    elif fmt == "jsonl":
        stats = validate_jsonl_mode(args.path, allowed_labels, args.mode)
        print_stats(stats)
    elif fmt == "json":
        stats = validate_json_splits_mode(args.path, allowed_labels, args.mode)
        print_stats(stats)
    elif fmt == "brat":
        stats = validate_brat_mode(args.path, args.mode, args.scope)
        print_stats(stats)
    elif fmt == "compare":
        compare_formats(args.path)

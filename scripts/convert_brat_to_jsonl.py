import argparse
import json
import os
import glob
import re
from tqdm import tqdm

def load_splits(corpus_dir):
    """
    Loads train/val/test splits from existing JSON files.
    Returns:
        doc_sentences: dict {doc_id: {sent_text: split_name}}
        (Using text as key to handle sentence-level splits if any)
    """
    files = {
        "train": "trainData.json",
        "val": "evalData.json",
        "test": "testData.json"
    }
    
    doc_sentences = {} # doc_id -> list of (text, split, tags)
    
    for split_name, filename in files.items():
        path = os.path.join(corpus_dir, filename)
        print(f"Loading {split_name} from {path}...")
        
        if not os.path.exists(path):
            print(f"Warning: {path} not found.")
            continue
            
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Fix concatenated JSON objects
            content = content.replace('}{', '}\n{')
            
            for line in content.split('\n'):
                if not line.strip(): continue
                try:
                    data = json.loads(line)
                    # ID format: DocID_SentID (e.g., "0_0")
                    parts = data['id'].split('_')
                    doc_id = parts[0]
                    # sent_id = parts[1] # Not strictly needed if we match by text
                    
                    if doc_id not in doc_sentences:
                        doc_sentences[doc_id] = []
                    
                    doc_sentences[doc_id].append({
                        "text": data['text'],
                        "split": split_name,
                        "original_tags": data.get('tags', [])
                    })
                    
                except Exception as e:
                    print(f"Error parsing line in {filename}: {e}")
                    
    return doc_sentences

def parse_brat_file(txt_path, ann_path):
    """
    Reads .txt and .ann files.
    Returns:
        text: full document text
        entities: list of dicts {id, type, start, end, text, spans}
    """
    with open(txt_path, 'r', encoding='utf-8') as f:
        text = f.read()
        
    entities = []
    if os.path.exists(ann_path):
        with open(ann_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or not line.startswith('T'): continue
                
                parts = line.split('\t')
                if len(parts) < 3: continue
                
                tid = parts[0]
                type_span = parts[1]
                entity_text = parts[2]
                
                # Parse type and spans
                # Format: "Type Start End" or "Type Start End;Start End"
                first_space = type_span.find(' ')
                entity_type = type_span[:first_space]
                coords_str = type_span[first_space:].strip()
                
                spans = []
                for pair in coords_str.split(';'):
                    s, e = map(int, pair.split())
                    spans.append((s, e))
                
                # Outer bounds
                start = min(s for s, e in spans)
                end = max(e for s, e in spans)
                
                entities.append({
                    "id": tid,
                    "type": entity_type,
                    "start": start,
                    "end": end,
                    "text": entity_text,
                    "spans": spans # List of (start, end) tuples
                })
                
    return text, entities

def convert(input_dir, output_file, corpus_dir):
    print("Loading splits...")
    known_docs = load_splits(corpus_dir)
    
    print("Processing BRAT files...")
    # Find all .txt files recursively
    txt_files = glob.glob(os.path.join(input_dir, "**", "*text*.txt"), recursive=True)
    
    output_data = []
    
    for txt_path in tqdm(txt_files):
        basename = os.path.basename(txt_path)
        # Extract DocID
        # 0text123.txt -> 123
        # 5text1600.txt -> 1600
        match = re.search(r'text(\d+)\.txt', basename)
        if not match:
            print(f"Skipping {basename}: Cannot extract DocID")
            continue
            
        doc_id = match.group(1)
        ann_path = txt_path.replace('.txt', '.ann')
        
        text, entities = parse_brat_file(txt_path, ann_path)
        
        # Get known sentences for this doc
        doc_known_sents = known_docs.get(doc_id, [])
        
        # If no known sentences, we might want to skip or use a default splitter
        # For now, we only output what was in the original corpus (as requested "robust converter" but context implies reproducing the dataset)
        # However, if we want a FULL converter, we should process everything.
        # But the user said "Fill meta.split using splits.json".
        # If a doc is not in splits.json, it has no split.
        
        if not doc_known_sents:
            # print(f"Doc {doc_id} not found in JSON splits. Skipping.")
            continue
            
        # Align sentences
        # We assume the sentences in JSON appear in order in the text.
        current_pos = 0
        
        for sent_info in doc_known_sents:
            sent_text = sent_info['text']
            # Find sentence in text starting from current_pos
            start_idx = text.find(sent_text, current_pos)
            
            if start_idx == -1:
                # Try finding from beginning if order is messed up (unlikely but possible)
                start_idx = text.find(sent_text)
                if start_idx == -1:
                    print(f"Warning: Sentence not found in Doc {doc_id}: {sent_text[:20]}...")
                    continue
            
            end_idx = start_idx + len(sent_text)
            current_pos = end_idx
            
            # Find entities within this sentence
            sent_entities = []
            for ent in entities:
                # Entity must be fully contained in sentence
                # We check the outer bounds (min start, max end)
                if ent['start'] >= start_idx and ent['end'] <= end_idx:
                    
                    # Iterate over spans to split discontinuous entities
                    # If it's a normal entity, it has 1 span.
                    # If it's discontinuous, it has > 1 span.
                    # We treat each span as a separate entity.
                    
                    current_spans = ent.get('spans', [[ent['start'], ent['end']]])
                    
                    for s, e in current_spans:
                        rel_start = s - start_idx
                        rel_end = e - start_idx
                        
                        # Extract text for this specific span
                        # sent_text is the sentence string. 
                        # rel_start/end are indices into sent_text.
                        span_text = sent_text[rel_start:rel_end]
                        
                        sent_entities.append({
                            "start": rel_start,
                            "end": rel_end,
                            "label": ent['type'],
                            "text": span_text,
                            # We can keep 'spans' for consistency, but it will always be length 1
                            "spans": [[rel_start, rel_end]] 
                        })
            
            # Construct output object
            out_obj = {
                "text": sent_text,
                "entities": sent_entities,
                "meta": {
                    "doc_id": doc_id,
                    "split": sent_info['split'],
                    "source_file": basename,
                    "is_synthetic": basename.startswith("5text")
                }
            }
            output_data.append(out_obj)

    print(f"Writing {len(output_data)} sentences to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        for obj in output_data:
            f.write(json.dumps(obj) + '\n')
            
    print("Done.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", required=True, help="Directory containing BRAT files")
    parser.add_argument("--output_path", required=True, help="Output JSONL file")
    parser.add_argument("--corpus_dir", required=True, help="Directory containing existing JSON splits")
    
    args = parser.parse_args()
    
    convert(args.input_dir, args.output_path, args.corpus_dir)

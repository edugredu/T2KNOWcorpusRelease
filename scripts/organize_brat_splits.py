import json
import os
import shutil
import glob
import re
from tqdm import tqdm

def load_split_ids(json_path):
    """
    Loads unique Document IDs from a JSON split file.
    """
    doc_ids = set()
    print(f"Loading IDs from {json_path}...")
    
    if not os.path.exists(json_path):
        print(f"Warning: {json_path} not found.")
        return doc_ids
        
    with open(json_path, 'r', encoding='utf-8') as f:
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
                doc_ids.add(doc_id)
            except Exception as e:
                print(f"Error parsing line: {e}")
                
    print(f"Found {len(doc_ids)} unique documents.")
    return doc_ids

def organize_splits(corpus_dir, brat_dir, source_dir):
    # Define splits and their source files
    splits = {
        "train": "trainData.json",
        "trainBalanced": "trainBalanced.json",
        "eval": "evalData.json",
        "test": "testData.json"
    }
    
    # Load IDs for each split
    split_ids = {}
    for split_name, filename in splits.items():
        json_path = os.path.join(corpus_dir, filename)
        split_ids[split_name] = load_split_ids(json_path)
        
        # Create output directory
        out_dir = os.path.join(brat_dir, split_name)
        os.makedirs(out_dir, exist_ok=True)
        print(f"Created directory: {out_dir}")

    # Process BRAT files from SOURCE directory
    print(f"Processing BRAT files from {source_dir}...")
    txt_files = glob.glob(os.path.join(source_dir, "*text*.txt"))
    
    if not txt_files:
        print(f"Warning: No .txt files found in {source_dir}")
    
    copied_counts = {k: 0 for k in splits.keys()}
    
    for txt_path in tqdm(txt_files):
        basename = os.path.basename(txt_path)
        
        # Extract DocID
        # 0text123.txt -> 123
        # 5text1600.txt -> 1600
        match = re.search(r'text(\d+)\.txt', basename)
        if not match:
            # print(f"Skipping {basename}: Cannot extract DocID")
            continue
            
        doc_id = match.group(1)
        ann_path = txt_path.replace('.txt', '.ann')
        
        # Check which splits this doc belongs to
        for split_name, ids in split_ids.items():
            if doc_id in ids:
                # Copy files
                dest_dir = os.path.join(brat_dir, split_name)
                shutil.copy2(txt_path, os.path.join(dest_dir, basename))
                if os.path.exists(ann_path):
                    shutil.copy2(ann_path, os.path.join(dest_dir, os.path.basename(ann_path)))
                copied_counts[split_name] += 1

    print("\nSummary:")
    for split_name, count in copied_counts.items():
        print(f"{split_name}: {count} documents copied")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus_dir", default="T2KNOWcorpus")
    parser.add_argument("--source_dir", default="anotaciones/Anotaciones_v12_2_ISABIAL")
    args = parser.parse_args()
    
    brat_dir = os.path.join(args.corpus_dir, "BRATformat")
    
    organize_splits(args.corpus_dir, brat_dir, args.source_dir)

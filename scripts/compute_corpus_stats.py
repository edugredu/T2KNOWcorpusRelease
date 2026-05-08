import json
import argparse
import os
from collections import Counter, defaultdict
import numpy as np

import json
import argparse
import os
from collections import Counter, defaultdict
import numpy as np

def init_stats():
    return {
        "docs": set(),
        "sentences": 0,
        "tokens": 0,
        "entities": 0,
        "labels": Counter(),
        "nested_entities": 0,
        "max_depth": 0,
        "multi_label_spans": 0,
        "unique_spans": 0,
        "discontinuous_entities": 0,
        "synthetic_entities": 0,
        "human_entities": 0,
        "revised_entities": 0,
        "non_revised_entities": 0,
        "text_included_sentences": 0,
        "text_excluded_sentences": 0,
        "token_counts_unavailable": 0
    }

def update_stats(stats, data, mode="legacy-full"):
    stats["sentences"] += 1
    stats["docs"].add(data['meta']['doc_id'])
    
    is_synthetic = data['meta'].get('is_synthetic', False)
    
    text = data.get('text')
    text_status = data.get("meta", {}).get("text_redistribution_status")
    if text_status == "excluded":
        stats["text_excluded_sentences"] += 1
    else:
        stats["text_included_sentences"] += 1
    if text is None:
        if mode == "public-redacted":
            stats["token_counts_unavailable"] += 1
            text = ""
        else:
            raise ValueError("text is null outside public-redacted mode")
    tokens = text.split()
    stats["tokens"] += len(tokens)
    
    entities = data.get('entities', [])
    stats["entities"] += len(entities)
    
    if is_synthetic:
        stats["synthetic_entities"] += len(entities)
    else:
        stats["human_entities"] += len(entities)
        source_file = data['meta'].get('source_file', '')
        if source_file.startswith('0text'):
            stats["revised_entities"] += len(entities)
        elif source_file.startswith('1text'):
            stats["non_revised_entities"] += len(entities)
    
    span_to_labels = defaultdict(set)
    char_mask = np.zeros(len(text), dtype=int)
    
    for ent in entities:
        stats["labels"][ent['label']] += 1
        spans = ent.get('spans', [[ent['start'], ent['end']]])
        
        if len(spans) > 1:
            stats["discontinuous_entities"] += 1
        
        span_key = tuple(tuple(s) for s in spans)
        span_to_labels[span_key].add(ent['label'])
        
        if len(text) > 0:
            for start, end in spans:
                s = max(0, start)
                e = min(len(text), end)
                char_mask[s:e] += 1
    
    if len(entities) > 0 and len(text) > 0:
        current_max_depth = np.max(char_mask)
        stats["max_depth"] = max(stats["max_depth"], int(current_max_depth))
        
        for i, ent1 in enumerate(entities):
            spans1 = ent1.get('spans', [[ent1['start'], ent1['end']]])
            is_nested = False
            for j, ent2 in enumerate(entities):
                if i == j: continue
                spans2 = ent2.get('spans', [[ent2['start'], ent2['end']]])
                
                overlap = False
                for s1, e1 in spans1:
                    for s2, e2 in spans2:
                        if max(s1, s2) < min(e1, e2):
                            overlap = True
                            break
                    if overlap: break
                
                if overlap:
                    if spans1 != spans2:
                        is_nested = True
                        break
            
            if is_nested:
                stats["nested_entities"] += 1

    stats["unique_spans"] += len(span_to_labels)
    for labels in span_to_labels.values():
        if len(labels) > 1:
            stats["multi_label_spans"] += 1

def print_report(title, stats, label_order=None):
    print("="*40)
    print(f"        {title.upper()}")
    print("="*40)
    print(f"Total Documents:      {len(stats['docs'])}")
    print(f"Total Sentences:      {stats['sentences']}")
    print(f"Total Tokens:         {stats['tokens']}")
    if stats.get("token_counts_unavailable"):
        print(f"Token-count unavailable sentences: {stats['token_counts_unavailable']}")
    print(f"Total Entities:       {stats['entities']}")
    if stats['entities'] > 0:
        print(f"  - Human:            {stats['human_entities']} ({stats['human_entities']/stats['entities']*100:.2f}%)")
        if stats['human_entities'] > 0:
            print(f"      - Revised:      {stats['revised_entities']} ({stats['revised_entities']/stats['human_entities']*100:.2f}% of Human)")
            print(f"      - Non-Revised:  {stats['non_revised_entities']} ({stats['non_revised_entities']/stats['human_entities']*100:.2f}% of Human)")
        print(f"  - Synthetic:        {stats['synthetic_entities']} ({stats['synthetic_entities']/stats['entities']*100:.2f}%)")
    print("-" * 40)
    if stats['sentences'] > 0:
        print(f"Avg Sentence Length:  {stats['tokens'] / stats['sentences']:.2f} tokens")
        print(f"Avg Entities/Sent:    {stats['entities'] / stats['sentences']:.2f}")
    if len(stats['docs']) > 0:
        print(f"Avg Entities/Doc:     {stats['entities'] / len(stats['docs']):.2f}")
    print("-" * 40)
    if stats['entities'] > 0:
        print(f"Discontinuous Ents:   {stats['discontinuous_entities']} ({stats['discontinuous_entities']/stats['entities']*100:.2f}%)")
        print(f"Nested Entities:      {stats['nested_entities']} ({stats['nested_entities']/stats['entities']*100:.2f}%)")
    print(f"Max Nesting Depth:    {stats['max_depth']}")
    if stats['unique_spans'] > 0:
        print(f"Multi-label Spans:    {stats['multi_label_spans']} ({stats['multi_label_spans']/stats['unique_spans']*100:.2f}% of unique spans)")
    print("="*40)
    print("LABEL DISTRIBUTION (All Categories)")
    print("="*40)
    
    if label_order is None:
        label_order = [k for k, v in stats['labels'].most_common()]
        
    if stats['entities'] > 0:
        for label in label_order:
            count = stats['labels'][label]
            percentage = (count / stats['entities'] * 100)
            print(f"{label:<40} {count:>5} ({percentage:>6.2f}%)")
    print("\n")

def serializable_stats(stats):
    out = dict(stats)
    out["docs"] = sorted(out["docs"], key=str)
    out["n_docs"] = len(out["docs"])
    out["labels"] = dict(out["labels"].most_common())
    return out


def compute_stats(file_path, mode="legacy-full", output=None):
    print(f"Loading {file_path}...")
    
    global_stats = init_stats()
    split_stats = defaultdict(init_stats)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            data = json.loads(line)
            
            split = data['meta'].get('split', 'unknown')
            
            update_stats(global_stats, data, mode=mode)
            update_stats(split_stats[split], data, mode=mode)

    # Derive global order
    global_label_order = [k for k, v in global_stats['labels'].most_common()]

    # Print Global Report
    print_report("GLOBAL STATISTICS", global_stats, global_label_order)
    
    # Print Split Reports
    for split in sorted(split_stats.keys()):
        print_report(f"{split} SPLIT STATISTICS", split_stats[split], global_label_order)

    if output:
        payload = {
            "mode": mode,
            "global": serializable_stats(global_stats),
            "splits": {split: serializable_stats(stats) for split, stats in sorted(split_stats.items())},
        }
        with open(output, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute statistics for T2KNOW corpus.")
    parser.add_argument("input_file", help="Path to the JSONL file (e.g., T2KNOWcorpus/t2know.jsonl)")
    parser.add_argument("--mode", choices=["legacy-full", "public-redacted", "reconstructed-full"], default="legacy-full")
    parser.add_argument("--output", help="Optional JSON output path.")
    args = parser.parse_args()
    
    if os.path.exists(args.input_file):
        compute_stats(args.input_file, mode=args.mode, output=args.output)
    else:
        print(f"Error: File {args.input_file} not found.")

import pandas as pd
import numpy as np


def _safe_divide(num: pd.Series, den: pd.Series) -> np.ndarray:
    num_arr = num.to_numpy(dtype=float)
    den_arr = den.to_numpy(dtype=float)
    out = np.zeros_like(num_arr, dtype=float)
    np.divide(num_arr, den_arr, out=out, where=den_arr != 0)
    return out


def compute_metrics(gold_data, pred_data, labels=None):
    """
    Computes metrics (Precision, Recall, F1, Accuracy) for NER.
    
    Args:
        gold_data: List of dicts, each containing 'entities' (list of dicts with start, end, label).
        pred_data: List of dicts, each containing 'entities' (list of dicts with start, end, label).
        labels: List of all possible labels. If None, inferred from data.
        
    Returns:
        df: DataFrame with counts (Ca, Pa, Ia, Ma, Sa) and metrics per label.
        global_metrics: Dict with global Precision, Recall, F1, Accuracy.
    """
    
    # Infer labels if not provided
    if labels is None:
        labels = set()
        for item in gold_data:
            for ent in item['entities']:
                labels.add(ent['label'])
        for item in pred_data:
            for ent in item['entities']:
                labels.add(ent['label'])
        labels = sorted(list(labels))

    # Initialize DataFrame
    df = pd.DataFrame(
        0.0,
        columns=['Ca', 'Ia', 'Pa', 'Ma', 'Sa', 'Precision', 'Recall', 'F1', 'Accuracy'],
        index=labels,
    )
    
    # Process each document/sentence
    for gold_item, pred_item in zip(gold_data, pred_data):
        # Prepare entities: rename 'label' to 'tag' to match original logic if needed, 
        # or just use 'tag' internally.
        
        real = [{'start': e['start'], 'end': e['end'], 'tag': e['label']} for e in gold_item['entities']]
        predicted = [{'start': e['start'], 'end': e['end'], 'tag': e['label']} for e in pred_item['entities']]
        
        # Sort
        real = sorted(real, key=lambda row: (row["start"], row["tag"]))
        predicted = sorted(predicted, key=lambda row: (row["start"], row["tag"]))
        
        # --- LOGIC PORTED FROM metrics.ipynb (detectAndClassifyTexts3) ---
        
        # CORRECT - Ca
        for annR in real.copy():
            for annP in predicted.copy():
                if annR['start'] == annP['start'] and annR['end'] == annP['end'] and annR['tag'] == annP['tag']:
                    df.loc[annR['tag'], 'Ca'] += 1
                    real.remove(annR)
                    predicted.remove(annP)
                    break
        
        # PARTIAL - Pa
        for annR in real.copy():
            partialMatch = []
            for annP in predicted.copy():
                # Check overlap
                if (annP['start'] >= annR['start'] and annP['end'] <= annR['end']) or \
                   (annP['start'] <= annR['start'] and annP['end'] >= annR['start'] and annP['end'] <= annR['end']) or \
                   (annP['start'] >= annR['start'] and annP['start'] <= annR['end'] and annP['end'] >= annR['end']) or \
                   (annP['start'] <= annR['start'] and annP['end'] >= annR['end']):
                    partialMatch.append(annP)
            
            if len(partialMatch) != 0:
                # Order by size (end - start) ASCENDING (as per original code)
                partialMatch = sorted(partialMatch, key=lambda row: (row["end"] - row["start"]))
                
                # Check if tags match
                for annP in partialMatch:
                    if annP['tag'] == annR['tag']:
                        df.loc[annR['tag'], 'Pa'] += 1
                        real.remove(annR)
                        predicted.remove(annP)
                        break
        
        # INCORRECT - Ia
        for annR in real.copy():
            for annP in predicted.copy():
                if annP['start'] == annR['start'] and annP['end'] == annR['end'] and annP['tag'] != annR['tag']:
                    df.loc[annR['tag'], 'Ia'] += 1
                    real.remove(annR)
                    predicted.remove(annP)
                    break
        
        # MISSING - Ma
        for annR in real.copy():
            df.loc[annR['tag'], 'Ma'] += 1
            
        # SPURIOUS - Sa
        for annP in predicted:
            # Note: Spurious are assigned to the predicted tag
            if annP['tag'] in df.index:
                df.loc[annP['tag'], 'Sa'] += 1
            else:
                # Handle unknown tags if necessary, or ignore
                pass

    # --- METRIC CALCULATION ---
    
    # Per-label metrics
    # Avoid division by zero
    denominator_prec = (df['Ca'] + df['Ia'] + df['Pa'] + df['Sa'])
    denominator_rec = (df['Ca'] + df['Ia'] + df['Pa'] + df['Ma'])
    denominator_acc = (df['Ca'] + df['Ia'] + df['Pa'] + df['Ma'] + df['Sa'])
    numerator_main = (df['Ca'] + 0.5 * df['Pa'])

    df['Precision'] = _safe_divide(numerator_main, denominator_prec)
    df['Recall'] = _safe_divide(numerator_main, denominator_rec)

    denominator_f1 = (df['Precision'] + df['Recall'])
    df['F1'] = _safe_divide(2 * (df['Precision'] * df['Recall']), denominator_f1)
    df['Accuracy'] = _safe_divide(numerator_main, denominator_acc)

    # Global metrics (Micro-average logic from original code)
    # The original code sums counts then calculates metrics
    
    total_Ca = df['Ca'].sum()
    total_Pa = df['Pa'].sum()
    total_Ia = df['Ia'].sum()
    total_Ma = df['Ma'].sum()
    total_Sa = df['Sa'].sum()
    
    global_prec = (total_Ca + 0.5 * total_Pa) / (total_Ca + total_Ia + total_Pa + total_Sa) if (total_Ca + total_Ia + total_Pa + total_Sa) > 0 else 0
    global_rec = (total_Ca + 0.5 * total_Pa) / (total_Ca + total_Ia + total_Pa + total_Ma) if (total_Ca + total_Ia + total_Pa + total_Ma) > 0 else 0
    global_f1 = 2 * (global_prec * global_rec) / (global_prec + global_rec) if (global_prec + global_rec) > 0 else 0
    global_acc = (total_Ca + 0.5 * total_Pa) / (total_Ca + total_Ia + total_Pa + total_Ma + total_Sa) if (total_Ca + total_Ia + total_Pa + total_Ma + total_Sa) > 0 else 0
    
    global_metrics = {
        'Precision': global_prec,
        'Recall': global_rec,
        'F1': global_f1,
        'Accuracy': global_acc
    }
    
    return df, global_metrics

# T2KNOW-Core BRAT Export

This directory contains the public BRAT standoff inspection export for T2KNOW-Core.

Canonical public folder:

- `documents/`: split-neutral BRAT files for text-included records only.

The public archive does not provide BRAT `.txt` or `.ann` files for text-excluded records. Full BRAT for the 821-document benchmark is regenerated locally after lawful source-text reconstruction.

Important: the document-disjoint benchmark split is defined by `data/t2know-core-v1.0/document_disjoint/`, not by the BRAT folder path. JSONL records contain BRAT path metadata only when public BRAT is available.

The matching benchmark JSON files are stored under `data/t2know-core-v1.0/document_disjoint/`.

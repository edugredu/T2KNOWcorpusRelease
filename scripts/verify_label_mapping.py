import argparse
import csv
import os
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from zipfile import ZipFile


DROP_TARGET = "0.0"


def load_allowed_labels(labels_path):
    with open(labels_path, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def load_csv_semantic_types(csv_path):
    with open(csv_path, "r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows


def load_xlsx_mapping(xlsx_path):
    with ZipFile(xlsx_path) as zf:
        shared_strings = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            for si in root.findall("a:si", ns):
                shared_strings.append("".join(t.text or "" for t in si.findall(".//a:t", ns)))

        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        first_sheet = workbook.find("a:sheets", ns)[0]
        rel_id = first_sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]

        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        rel_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}
        sheet_path = "xl/" + rel_map[rel_id]

        sheet = ET.fromstring(zf.read(sheet_path))
        rows = sheet.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row")

        mapping = []
        for row in rows[1:]:
            values = []
            for cell in row.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"):
                cell_type = cell.attrib.get("t")
                value = cell.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
                if value is None:
                    values.append("")
                elif cell_type == "s":
                    values.append(shared_strings[int(value.text)])
                else:
                    values.append(value.text)

            if len(values) >= 2 and values[0]:
                mapping.append({"source_type": values[0], "target_label": values[1]})

    return mapping


def main():
    parser = argparse.ArgumentParser(description="Verify T2KNOW semantic-type to label mapping artifacts")
    parser.add_argument(
        "--mapping-xlsx",
        default=os.path.join("Anotaciones base", "Tarea EDU", "Mapping UMLS-T2KNOW.xlsx"),
        help="Path to the primary XLSX mapping artifact",
    )
    parser.add_argument(
        "--semantic-types-csv",
        default=os.path.join("old", "UMLS CATEGORIAS_v2.csv"),
        help="Path to the semantic-types reference CSV",
    )
    parser.add_argument(
        "--labels-file",
        default=os.path.join("T2KNOWcode", "listaCategorias.txt"),
        help="Path to the frozen 40-label inventory",
    )
    args = parser.parse_args()

    allowed_labels = load_allowed_labels(args.labels_file)
    semantic_rows = load_csv_semantic_types(args.semantic_types_csv)
    mapping_rows = load_xlsx_mapping(args.mapping_xlsx)

    semantic_type_names = {row["Categoría"].strip().replace(" ", ""): row["Categoría"].strip() for row in semantic_rows if row.get("Categoría")}
    source_types = {row["source_type"] for row in mapping_rows}
    target_labels = {row["target_label"] for row in mapping_rows}

    invalid_targets = sorted(label for label in target_labels if label != DROP_TARGET and label not in allowed_labels)
    unused_labels = sorted(allowed_labels - {label for label in target_labels if label != DROP_TARGET})

    missing_in_semantic_csv = []
    for source_type in sorted(source_types):
        normalized = source_type.replace("_", " ").replace("-", " ").replace(",", "").strip().replace(" ", "")
        if normalized not in semantic_type_names:
            missing_in_semantic_csv.append(source_type)

    target_counts = Counter(row["target_label"] for row in mapping_rows)

    print("Mapping verification results")
    print(f"semantic_types_csv_rows={len(semantic_rows)}")
    print(f"mapping_rows={len(mapping_rows)}")
    print(f"source_types_mapped={len(source_types)}")
    print(f"drop_rows={target_counts[DROP_TARGET]}")
    print(f"kept_target_labels={len([t for t in target_labels if t != DROP_TARGET])}")
    print(f"invalid_targets={len(invalid_targets)}")
    print(f"unused_labels={len(unused_labels)}")
    print(f"source_types_not_matched_in_csv={len(missing_in_semantic_csv)}")

    if invalid_targets:
        print("invalid_target_labels:")
        for label in invalid_targets:
            print(f"  - {label}")

    if unused_labels:
        print("unused_frozen_labels:")
        for label in unused_labels:
            print(f"  - {label}")

    if missing_in_semantic_csv:
        print("source_types_not_found_in_semantic_csv:")
        for source_type in missing_in_semantic_csv[:20]:
            print(f"  - {source_type}")

    print("top_target_counts:")
    for label, count in target_counts.most_common(20):
        print(f"  - {label}: {count}")

    if invalid_targets or unused_labels:
        sys.exit(1)

    print("SUCCESS: Mapping targets are consistent with the frozen 40-label inventory.")


if __name__ == "__main__":
    main()

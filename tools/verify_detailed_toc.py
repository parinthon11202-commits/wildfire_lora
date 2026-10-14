from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from docx import Document

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_detailed_toc as builder


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--docx", required=True)
    parser.add_argument("--combined-outline", required=True)
    parser.add_argument("--appendix-outline", required=True)
    args = parser.parse_args()

    combined = json.loads(Path(args.combined_outline).read_text(encoding="utf-8"))
    appendix = json.loads(Path(args.appendix_outline).read_text(encoding="utf-8"))

    main_entries = builder.chapter_entries(combined)
    back_entries = [builder.Entry("บรรณานุกรม", "102", 0)]
    back_entries.extend(builder.appendix_entries(appendix, 104))
    back_entries.append(builder.Entry("ประวัติผู้เขียน", "116", 0))
    table_entries = builder.caption_entries(combined, "ตารางที่")
    figure_entries = builder.caption_entries(combined, "รูปที่")

    expected = main_entries + back_entries + table_entries + figure_entries
    expected_pairs = [(entry.title, entry.page) for entry in expected]

    doc = Document(args.docx)
    actual_pairs = []
    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if "\t" not in text:
            continue
        title, page = text.rsplit("\t", 1)
        if page.isdigit() and title not in {"หัวข้อ", "ตาราง", "รูป"}:
            actual_pairs.append((title.strip(), page))

    missing = [pair for pair in expected_pairs if pair not in actual_pairs]
    unexpected = [pair for pair in actual_pairs if pair not in expected_pairs]
    duplicates = len(actual_pairs) - len(set(actual_pairs))

    report = {
        "expected_entries": len(expected_pairs),
        "actual_numeric_entries": len(actual_pairs),
        "missing": missing,
        "unexpected": unexpected,
        "duplicate_pairs": duplicates,
        "status": "PASS" if not missing and not unexpected and len(expected_pairs) == len(actual_pairs) else "FAIL",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

\n
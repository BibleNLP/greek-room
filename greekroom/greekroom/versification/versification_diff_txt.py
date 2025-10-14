#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Compares two Bible corpus files (of same versification); prints differing lines with snt. ID and line lengths
# verse_diff.py file1 file2 vref.txt
# Resulting verse can can be used in versification-inspection-config.jsonl as config for script verse_inspection.py

import argparse
import sys
from versification import Versification


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('filename1', type=str)
    parser.add_argument('filename2', type=str)
    parser.add_argument('--snt_id_filename', type=str, default=Versification.vref_filename())
    args = parser.parse_args()
    psalms_with_descriptive_titles_in_org_schema \
        = [3, 4, 5, 6, 7, 8, 9, 12, 13, 18, 19, 20, 21, 22, 30, 31, 34, 36, 38, 39, 40, 41, 42, 44, 45,
           46, 47, 48, 49, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 67, 68, 69, 70,
           75, 76, 77, 80, 81, 83, 84, 85, 88, 89, 92, 102, 108, 140, 142]
    psalm_verse_ids_with_descriptive_titles_in_org_schema = []
    for psalm_number in psalms_with_descriptive_titles_in_org_schema:
        if psalm_number in [51, 52, 54, 60]:
            psalm_verse_ids_with_descriptive_titles_in_org_schema.append(f"PSA {psalm_number}:2")
        else:
            psalm_verse_ids_with_descriptive_titles_in_org_schema.append(f"PSA {psalm_number}:1")
    psalms_with_descriptive_titles_only_in_file1 = []
    psalms_with_descriptive_titles_only_in_file2 = []
    n_diff_lines = 0
    line_number = 0
    with open(args.filename1) as f1, open(args.filename2) as f2, open(args.snt_id_filename) as f_snt_id:
        for line in f1:
            line_number += 1
            line1 = line.rstrip()
            line2 = f2.readline().rstrip()
            snt_id = f_snt_id.readline().rstrip()
            if line1 != line2:
                if (snt_id in psalm_verse_ids_with_descriptive_titles_in_org_schema) and (len(line2) == 0):
                    psalms_with_descriptive_titles_only_in_file1.append(snt_id)
                elif (snt_id in psalm_verse_ids_with_descriptive_titles_in_org_schema) and (len(line1) == 0):
                    psalms_with_descriptive_titles_only_in_file2.append(snt_id)
                else:
                    n_diff_lines += 1
                    sys.stderr.write(f"Diff {snt_id:10s} {len(line1):3d} characters vs. {len(line2):3d} characters\n")
        sys.stderr.write(f"{n_diff_lines}/{line_number} lines differ.\n")
        for i, pdt in ((1, psalms_with_descriptive_titles_only_in_file1),
                       (2, psalms_with_descriptive_titles_only_in_file2)):
            if pdt:
                if pdt == psalm_verse_ids_with_descriptive_titles_in_org_schema:
                    sys.stderr.write(f"... except that all {len(pdt)} psalm descriptive titles occur only in file{i}\n")
                else:
                    standard_pdt = psalm_verse_ids_with_descriptive_titles_in_org_schema
                    max_pdt = len(standard_pdt)
                    if (len(pdt) >= 50) and (set(pdt) < set(standard_pdt)):
                        except_list = sorted(set(standard_pdt) - set(pdt))
                        sys.stderr.write(f"  ... plus {len(pdt)}/{max_pdt} psalm descriptive titles only in file{i}:"
                                         f" except {except_list}\n")
                    else:
                        sys.stderr.write(f"  ... plus {len(pdt)}/{max_pdt} psalm descriptive titles only in file{i}:"
                                         f" {pdt}\n")


if __name__ == "__main__":
    main()

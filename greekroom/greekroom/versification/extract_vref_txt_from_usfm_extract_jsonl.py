#!/usr/bin/env python3

# This tool extracts from a USFM extraction-file a versified corpus (rendered as two parallel files).
# Usage: extract_vref_txt_from_usfm_extract_jsonl.py -i extract.jsonl -o f_usfm.txt -v f_usfm_vref.txt
# Input: extract.jsonl, which is built by Greek Room tool usfm_check.py (which also checks the USFM files for problems).
# Output 1: f_usfm.txt        corpus of verses
# Output 2: f_usfm_vref.txt   file with corresponding verse IDs (same number of lines as f_usfm.txt)

import argparse
from collections import defaultdict
import json
from pathlib import Path
import regex
import sys
from greekroom.gr_utilities import general_util


def normalize_string(s: str, change_count_dict: dict, change_example_dict: dict, verse_id: str | None,
                     line_number: int | None) -> str:
    no_break_space = '\u00A0'
    s0 = s
    s, count = regex.subn(r'\r\n', '\n', s)
    change_count_dict['return'] += count
    s, count = regex.subn(r'\n$', ' ', s)
    change_count_dict['final-newline'] += count
    s, count = regex.subn(r'\n', ' ', s)
    change_count_dict['non-final-newline'] += count
    s, count = regex.subn(r'~([-–—―])', fr'{no_break_space}\1', s)
    change_count_dict['tilde-dash'] += count
    s, count = regex.subn(r'([-–—―])~', fr'\1{no_break_space}', s)
    change_count_dict['dash-tilde'] += count
    s1 = s
    s, count = regex.subn(r'~', no_break_space, s)
    change_count_dict['other-tilde'] += count
    l_clause = f"l.{line_number} " if line_number else ""
    r_clause = f"{verse_id} " if verse_id else ""
    if s1 != s:
        change_example_dict['other-tilde'].append(f"{l_clause}{r_clause}{shorten_text(s0, 200)}")
    s1 = s
    s, count = regex.subn(r' {2,}', ' ', s)
    change_count_dict['multi-space'] += count
    if s1 != s:
        change_example_dict['multi-space'].append(f"{l_clause}{r_clause}{shorten_text(s0, 200)}")
    return s.strip()


def preferred_none_value(raw_value: str, none_value):
    return none_value if ((not raw_value) or (raw_value in ("None", "0"))) else raw_value


def shorten_text(s: str, max_length: int) -> str:
    return f"{s[:max_length]} ..." if len(s) > max_length else s


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input_filename', type=Path, help="Input USFM extract file (jsonl)")
    parser.add_argument('-o', '--output_filename', type=Path, help="Plain text")
    parser.add_argument('-v', '--vref_filename', type=Path, help="vref (e.g. GEN 1:1)")
    args = parser.parse_args()
    line_number = 0
    n_verses = 0
    n_descriptive_titles = 0
    change_count_dict = defaultdict(int)
    change_example_dict = defaultdict(list)
    general_util.mkdirs_in_path(args.output_filename)
    general_util.mkdirs_in_path(args.vref_filename)
    with (open(args.input_filename) as f_in,
          open(args.output_filename, 'w') as f_out,
          open(args.vref_filename, 'w') as f_vref):
        for line in f_in:
            line_number += 1
            line = line.strip()
            if line.startswith("{"):
                if d := json.loads(line):
                    bk = d.get("bk")
                    c = preferred_none_value(d.get("c"), 0)
                    v = preferred_none_value(d.get("v"), 0)
                    txt = d.get("txt")
                    entry_type = d.get("type")
                    tag = d.get("tag")
                    if bk and txt and (entry_type == "v"):
                        verse_id = f"{bk} {c}:{v}"
                        txt = normalize_string(txt, change_count_dict, change_example_dict, verse_id, line_number)
                        if c and v:
                            if m := regex.match(r'(\d+)-(\d+)$', v):
                                from_s, to_s = m.group(1, 2)
                                from_i, to_i = int(from_s), int(to_s)
                                if from_i < to_i:
                                    texts = [txt] + (['<range>'] * (to_i - from_i))
                                    for verse_number in range(from_i, to_i+1):
                                        sys.stderr.write(f"{from_i}-{to_i} {verse_number} ''{txt}'' {texts} {verse_number-from_i}\n")
                                        f_out.write(f"{texts[verse_number-from_i]}\n")
                                        f_vref.write(f"{bk} {c}:{verse_number}\n")
                                        n_verses += 1
                                else:
                                    sys.stderr.write(f"Skipping  {verse_id}  due to bad range  "
                                                     f"{shorten_text(txt, 200)}\n")
                            else:
                                f_out.write(f"{txt}\n")
                                f_vref.write(f"{verse_id}\n")
                                n_verses += 1
                        elif txt and (entry_type == "v"):
                            sys.stderr.write(f"Skipping  {verse_id}  {shorten_text(txt, 200)}\n")
                    if bk and txt and (entry_type == "o") and (tag == "d"):
                        provisional_verse_id = f"{bk} ch.{c} descriptive-title"
                        txt = normalize_string(txt, change_count_dict, change_example_dict, provisional_verse_id,
                                               line_number)
                        if c:
                            if bk == "PSA":
                                descriptive_title_id = f"{bk} {c}:0"
                            elif (bk == "HAB") and (c == 3):
                                descriptive_title_id = f"{bk} {c}:20"
                            else:
                                descriptive_title_id = None
                                sys.stderr.write(f"Unexpected descriptive title in {d}\n")
                            if descriptive_title_id:
                                f_out.write(f"{txt}\n")
                                f_vref.write(f"{descriptive_title_id}\n")
                                n_descriptive_titles += 1
                                # sys.stderr.write(f'Descriptive title {verse_id} "{txt}"\n')
                        else:
                            sys.stderr.write(f"Skipping  {provisional_verse_id}  {shorten_text(txt, 200)}\n")
    sys.stderr.write(f"Extracted {n_verses} verses and {n_descriptive_titles} descriptive titles "
                     f"from {line_number} lines.\n")
    sys.stderr.write(f"Change counts: {change_count_dict}\n")
    if change_example_dict:
        for example_class in change_example_dict.keys():
            examples = change_example_dict.get(example_class)
            sys.stderr.write(f"{example_class} ({len(examples)})\n")
            for i in range(min(10, len(examples))):
                example = examples[i].replace('\n', '␤')
                sys.stderr.write(f"   {example}\n")
        # sys.stderr.write(f"Change examples: {change_example_dict}\n")


if __name__ == "__main__":
    main()

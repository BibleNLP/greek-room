#!/usr/bin/env python

import sys

filename1 = sys.argv[1]
filename2 = sys.argv[2]
filename_ref = sys.argv[3] if len(sys.argv) >= 4 and not (sys.argv[3].startswith('-')) else None
sys.stderr.write(f'filename_ref={filename_ref}\n')
lc_p = ("--lc" in sys.argv or "-lc" in sys.argv)

n_skipped_lines, n_unskipped_lines, n_empty_lines = 0, 0, 0

f_ref = open(filename_ref) if filename_ref else None
with open(filename1) as f1, open(filename2) as f2:
    for line1, line2 in zip(f1, f2):
        line1, line2 = line1.strip(), line2.strip()
        if lc_p:
            line1 = line1.lower()
            line2 = line2.lower()
        tokens1, tokens2 = line1.split(), line2.split()
        n_tokens1, n_tokens2 = len(tokens1) , len(tokens2)
        ref = f_ref.readline().strip() if f_ref else None
        if n_tokens1 and n_tokens2:
            ref_clause = f' ||| {ref}' if ref else ""
            if ((n_tokens1 * 1.5 + 5 > n_tokens2) and (n_tokens2 * 1.5 + 5 > n_tokens1)) \
                    or (ref in ('GEN 1:1', 'JOS 1:1', 'ISA 1:1', 'MAT 1:1', 'ROM 1:1', 'TOB 1:1')):
                # print(f'{line1} ||| {line2}{ref_clause}')
                print(f'{line1} ||| {line2}')
                n_unskipped_lines += 1
            else:
                n_skipped_lines += 1
                sys.stderr.write(f'Skipped: {line1} ||| {line2}{ref_clause}\n')
        else:
            n_empty_lines += 1

sys.stderr.write(f'Skipped {n_skipped_lines}/{n_skipped_lines+n_unskipped_lines} lines.\n')


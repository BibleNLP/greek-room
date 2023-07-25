#!/usr/bin/env python

import argparse
from collections import defaultdict
import os
from pathlib import Path
import regex
import sys
from ualign import DocumentConfiguration

align_viz_root_dir = Path('/Users/ulf/GreekRoom/html')
greek_room_data_root_dir = Path('/Users/ulf/projects/NLP/fast_align/data')
uroman_pl = '/Users/ulf/projects/NLP/uroman/bin/uroman.pl'


def add_token_suffixes_to_token_dict(token_dict: dict[str], max_suffix_len: int = 6, min_type_count: int = 3) -> None:
    tokens = list(token_dict.keys())
    suffix_dict = defaultdict(int)
    for token in tokens:
        for suffix_len in range(1, max_suffix_len+1):
            suffix = token[-suffix_len:]
            if regex.match(r'\pL', suffix):
                suffix_dict[suffix] += 1
    for suffix in suffix_dict.keys():
        if suffix_dict[suffix] >= min_type_count:
            token_dict[suffix] = True


default_ref_filenames = ['vref.txt']
default_config_filenames = ['BibleTranslationConfig.jsonl']

parser = argparse.ArgumentParser()
parser.add_argument('-e', '--e_filename', type=Path, help='source language text file')
parser.add_argument('-f', '--f_filename', type=Path, help='target language text file')
parser.add_argument('-c', '--config_filename', type=Path,
                    help='(optional) document configuration file in JSONL format, will search list of '
                         f'default_config_filenames ({default_config_filenames}) if not provided as arg')
parser.add_argument('-o', '--output_dir', type=Path, help='(optional) bitext directory, '
                                                          'e.g. en-ESVUS16-hi-IRVHin23-v99, '
                                                          'auto-derivable from e_config_id and f_config_id')
parser.add_argument('-E', '--e_config_id', type=str, help='(optional) source language document configuration ID, '
                                                          'e.g. en-ESVUS16, auto-derivable from e_filename')
parser.add_argument('-F', '--f_config_id', type=str, help='(optional) target language document configuration ID, '
                                                          'e.g. hi-IRVHin23, auto-derivable from f_filename')
parser.add_argument('-r', '--ref_filename', type=Path,
                    help='(optional) file, e.g. vref.txt, with snt.IDs, e.g. "GEN 1:1", will search list of '
                         f'default_ref_filenames ({default_ref_filenames}) if not provided as arg')
args = parser.parse_args()

n_skipped_lines, n_unskipped_lines, n_empty_lines = 0, 0, 0
e_file_contains_case_differences, f_file_contains_case_differences = False, False

if not args.e_filename:
    raise ValueError('No e_filename provided')
elif not os.path.exists(args.e_filename):
    raise ValueError(f'e_filename {args.e_filename} does not exist.')
else:
    if not args.e_config_id:
        args.e_config_id = os.path.basename(args.e_filename).removesuffix('.txt')

if not args.f_filename:
    raise ValueError('No f_filename provided')
elif not os.path.exists(args.f_filename):
    raise ValueError(f'f_filename {args.f_filename} does not exist.')
else:
    if not args.f_config_id:
        args.f_config_id = os.path.basename(args.f_filename).removesuffix('.txt')

r = None
if args.ref_filename:
    r = open(args.ref_filename)
else:
    for default_ref_filename in default_ref_filenames:
        if os.path.exists(default_ref_filename):
            try:
                r = open(default_ref_filename)
            except OSError:
                sys.stderr.write(f'Could not open {default_ref_filename}\n')
            break

# create doc_config from some configuration file (provided as arg or one of several default configuration files
config_filename = None
doc_config = {}
if args.config_filename:
    config_filename = args.config_filename
else:
    for default_config_filename in default_config_filenames:
        if os.path.exists(default_config_filename):
            config_filename = default_config_filename
            break
if config_filename:
    doc_config = DocumentConfiguration(Path(config_filename))
else:
    if default_config_filenames:
        raise ValueError(f'No configuration filename provided, '
                         f'neither as argument or default ({default_config_filenames})')
    else:
        raise ValueError('No configuration filename provided')

cwd = Path(os.path.abspath(os.getcwd()))
sys.stderr.write(f'CWD: {cwd}\n')
if not args.output_dir:
    relative_output_dir = Path(f"{args.e_config_id}-{args.f_config_id}-v99")
    args.output_dir = Path(cwd / relative_output_dir)
else:
    relative_output_dir = args.output_dir

out_transfer_dir = cwd / 'transfer_to_from_zion'
if not os.path.exists(out_transfer_dir):
    os.makedirs(out_transfer_dir)
if not os.path.exists(args.output_dir):
    os.makedirs(args.output_dir)
out_log = open(args.output_dir / 'log.txt', 'w')
scripts_file = args.output_dir / 'scripts'
out_scripts = open(scripts_file, 'w')

for out_file in ('e_lc.txt', 'f_lc.txt', 'e_f_ref_lc.txt'):
    if os.path.islink(args.output_dir / out_file):
        os.unlink(args.output_dir / out_file)

if e_config := doc_config.doc_dict.get(args.e_config_id, None):
    e_lang_code = e_config.get('lc', None)
    e_lang_name = e_config.get('lang', None)
else:
    sys.stderr.write(f'No document configuration found for {args.e_config_id}')
    e_lang_code = None
    e_lang_name = None
if f_config := doc_config.doc_dict.get(args.f_config_id, None):
    f_lang_code = f_config.get('lc', None)
    f_lang_name = f_config.get('lang', None)
else:
    sys.stderr.write(f'No document configuration found for {args.f_config_id}')
    f_lang_code = None
    f_lang_name = None
e_lang_code_clause = f' --lc {e_lang_code}' if e_lang_code else ''
f_lang_code_clause = f' --lc {f_lang_code}' if f_lang_code else ''

e_untok_filename = args.output_dir / 'e.untok'
f_untok_filename = args.output_dir / 'f.untok'
if not os.path.exists(e_untok_filename):
    os.link(args.e_filename, e_untok_filename)
if not os.path.exists(f_untok_filename):
    os.link(args.f_filename, f_untok_filename)

# normalize
e_untok_norm_filename = args.output_dir / 'e.untok.norm'
f_untok_norm_filename = args.output_dir / 'f.untok.norm'
if not os.path.exists(e_untok_norm_filename):
    e_norm_command = f"wb_normalize.py -i {args.e_filename} -o {e_untok_norm_filename}{e_lang_code_clause}"
    sys.stderr.write(f'System call: {e_norm_command}\n')
    out_log.write(f'System call: {e_norm_command}\n')
    os.system(e_norm_command)
if not os.path.exists(f_untok_norm_filename):
    f_norm_command = f"wb_normalize.py -i {args.f_filename} -o {f_untok_norm_filename}{f_lang_code_clause}"
    sys.stderr.write(f'System call: {f_norm_command}\n')
    out_log.write(f'System call: {f_norm_command}\n')
    os.system(f_norm_command)

# tokenize
e_norm_tok = args.output_dir / 'e.norm.tok'  # normalized, tokenized
f_norm_tok = args.output_dir / 'f.norm.tok'  # normalized, tokenized
if not os.path.exists(e_norm_tok):
    e_tok_command = f"python -m utoken.utokenize -i {e_untok_norm_filename} -o {e_norm_tok}{e_lang_code_clause}"
    sys.stderr.write(f'System call: {e_tok_command}\n')
    out_log.write(f'System call: {e_tok_command}\n')
    os.system(e_tok_command)
if not os.path.exists(f_norm_tok):
    f_tok_command = f"python -m utoken.utokenize -i {f_untok_norm_filename} -o {f_norm_tok}{f_lang_code_clause}"
    sys.stderr.write(f'System call: {f_tok_command}\n')
    out_log.write(f'System call: {f_tok_command}\n')
    os.system(f_tok_command)
out_log.write('\n')
out_log.flush()

filename_e = args.output_dir / 'e.txt'
filename_f = args.output_dir / 'f.txt'
filename_e_lc = args.output_dir / 'e_lc.txt'
filename_f_lc = args.output_dir / 'f_lc.txt'
filename_e_f_ref = args.output_dir / 'e_f_ref.txt'
filename_e_f_ref_lc = args.output_dir / 'e_f_ref_lc.txt'
filename_e_f_lc = args.output_dir / 'e_f_lc.txt'

basic_filenames \
    = [filename_e, filename_f, filename_e_lc, filename_f_lc, filename_e_f_ref, filename_e_f_ref_lc, filename_e_f_lc]

if all(os.path.exists(filename) for filename in basic_filenames):
    sys.stderr.write(f"Files already exist: {' '.join([os.path.basename(filename) for filename in basic_filenames])}\n")
else:
    out_e = open(filename_e, 'w')
    out_f = open(filename_f, 'w')
    out_e_lc = open(filename_e_lc, 'w')
    out_f_lc = open(filename_f_lc, 'w')
    out_e_f_ref = open(filename_e_f_ref, 'w')
    out_e_f_ref_lc = open(filename_e_f_ref_lc, 'w')
    out_e_f_lc = open(filename_e_f_lc, 'w')
    e_token_dict = {}  # both original and (if applicable, lower case)
    f_token_dict = {}  # both original and (if applicable, lower case)
    line_number = 0
    with open(e_norm_tok) as e, open(f_norm_tok) as f:
        for line1, line2 in zip(e, f):
            line_number += 1
            line1, line2 = line1.strip(), line2.strip()
            lc_line1 = line1.lower()
            lc_line2 = line2.lower()
            e_line_contains_case_differences, f_line_contains_case_differences = False, False
            if lc_line1 != line1:
                e_file_contains_case_differences, e_line_contains_case_differences = True, True
            if lc_line2 != line2:
                f_file_contains_case_differences, f_line_contains_case_differences = True, True
            e_tokens, f_tokens = line1.split(), line2.split()
            n_tokens1, n_tokens2 = len(e_tokens), len(f_tokens)
            ref = r.readline().strip() if r else line_number
            if n_tokens1 and n_tokens2:
                if ((n_tokens1 * 1.5 + 5 > n_tokens2) and (n_tokens2 * 1.5 + 5 > n_tokens1)) \
                        or (ref in ('GEN 1:1', 'JOS 1:1', 'ISA 1:1', 'MAT 1:1', 'ROM 1:1', 'TOB 1:1')):
                    out_e.write(line1 + '\n')
                    out_f.write(line2 + '\n')
                    out_e_lc.write(lc_line1 + '\n')
                    out_f_lc.write(lc_line2 + '\n')
                    out_e_f_ref.write(f'{line1} ||| {line2} ||| {ref}\n')
                    out_e_f_ref_lc.write(f'{lc_line1} ||| {lc_line2} ||| {ref}\n')
                    out_e_f_lc.write(f'{lc_line1} ||| {lc_line2}\n')
                    n_unskipped_lines += 1
                    for e_token in e_tokens:
                        if regex.search(r'\pL', e_token) and not regex.match(r'^[\u0020-\u007F]+$', e_token):
                            e_token_dict[e_token] = True
                            if e_line_contains_case_differences:
                                e_token_dict[e_token.lower()] = True
                    for f_token in f_tokens:
                        if regex.search(r'\pL', f_token) and not regex.match(r'^[\u0020-\u007F]+$', f_token):
                            f_token_dict[f_token] = True
                            if f_line_contains_case_differences:
                                f_token_dict[f_token.lower()] = True
                else:
                    n_skipped_lines += 1
                    out_log.write(f'Skipped: {line1} ||| {line2} ||| {ref}\n')
            else:
                n_empty_lines += 1
            if line_number % 1000 == 0:
                if line_number % 10000 == 0:
                    sys.stderr.write(str(int(line_number / 1000)) + 'k')
                else:
                    sys.stderr.write('.')
                sys.stderr.flush()
    add_token_suffixes_to_token_dict(e_token_dict, max_suffix_len=6, min_type_count=3)
    add_token_suffixes_to_token_dict(f_token_dict, max_suffix_len=6, min_type_count=3)
    sys.stderr.write(f'\nSkipped {n_skipped_lines}/{n_skipped_lines+n_unskipped_lines} lines.\n')
    out_e.close()
    out_f.close()
    out_e_lc.close()
    out_f_lc.close()
    out_e_f_ref.close()
    out_e_f_ref_lc.close()
    out_e_f_lc.close()
    if r:
        r.close()

    out_log.write('\n')
    if e_token_dict:
        e_tok_file = args.output_dir / 'e_tokens.txt'
        e_tok_uroman_file = args.output_dir / 'e_tokens.uroman.txt'
        e_tok_combo_file = args.output_dir / 'e_tokens.uroman-map.txt'
        with open(e_tok_file, 'w') as e:
            for e_token in sorted(e_token_dict.keys(), key=lambda s: s.lower()):
                e.write(e_token + '\n')
        sys.stderr.write(f'uroman on {e_tok_file} ...')
        sys.stderr.flush()
        command1 = f'{uroman_pl}{e_lang_code_clause} < {e_tok_file} > {e_tok_uroman_file}'
        out_log.write('System call: ' + command1 + '\n')
        os.system(command1)
        command2 = f'parallel-corpus-to-triple-pipe-format.py {e_tok_file} {e_tok_uroman_file} > {e_tok_combo_file}'
        out_log.write('System call: ' + command2 + '\n')
        out_log.flush()
        os.system(command2)
        sys.stderr.write('\n')
    if f_token_dict:
        f_tok_file = args.output_dir / 'f_tokens.txt'
        f_tok_uroman_file = args.output_dir / 'f_tokens.uroman.txt'
        f_tok_combo_file = args.output_dir / 'f_tokens.uroman-map.txt'
        with open(args.output_dir / 'f_tokens.txt', 'w') as f:
            for f_token in sorted(f_token_dict.keys(), key=lambda s: s.lower()):
                f.write(f_token + '\n')
        sys.stderr.write(f'uroman on {f_tok_file} ...')
        sys.stderr.flush()
        command1 = f'{uroman_pl}{f_lang_code_clause} < {f_tok_file} > {f_tok_uroman_file}'
        out_log.write('System call: ' + command1 + '\n')
        os.system(command1)
        command2 = f'parallel-corpus-to-triple-pipe-format.py {f_tok_file} {f_tok_uroman_file} > {f_tok_combo_file}'
        out_log.write('System call: ' + command2 + '\n')
        out_log.flush()
        os.system(command2)
        sys.stderr.write('\n')

    if not e_file_contains_case_differences:
        os.remove(filename_e_lc)
        os.symlink('e.txt', filename_e_lc)
    if not f_file_contains_case_differences:
        os.remove(filename_f_lc)
        os.symlink('f.txt', filename_f_lc)
    if not e_file_contains_case_differences and not f_file_contains_case_differences:
        os.remove(filename_e_f_ref_lc)
        os.symlink('e_f_ref.txt', filename_e_f_ref_lc)

used_out_transfer_dir = False
target_filenames = []
out_basename = os.path.basename(os.path.normpath(args.output_dir))
out_basename = regex.sub(r'-v\d+$', '', out_basename)
e_lc_basename = f'{out_basename}.e_lc.txt'
f_lc_basename = f'{out_basename}.f_lc.txt'
if os.path.exists(filename_e_lc):
    target_file = out_transfer_dir / e_lc_basename
    if os.path.exists(target_file):
        os.remove(target_file)
    os.link(filename_e_lc, target_file)
    target_filenames.append(e_lc_basename)
    used_out_transfer_dir = True
if os.path.exists(filename_f_lc):
    target_file = out_transfer_dir / f_lc_basename
    if os.path.exists(target_file):
        os.remove(target_file)
    os.link(filename_f_lc, target_file)
    target_filenames.append(f_lc_basename)
    used_out_transfer_dir = True
if target_filenames:
    out_scripts.write(f'cd {cwd}\n')
    out_scripts.write(f'parallel-corpus-prep.py -e {args.e_filename} -f {args.f_filename}\n')

    out_scripts.write(f"\n# Eflomal alignment (core on zion)\n")
    out_scripts.write(f'cd {out_transfer_dir}\n')
    out_scripts.write(f"tar -cvf corpora.tar {' '.join(target_filenames)}\n")
    out_scripts.write(f"scp -P 22 corpora.tar zion.isi.edu:/mnt/data/share/alignment/data/corpora.tar\n")
    out_scripts.write(f"On zion:\n")
    out_scripts.write(f"    cd /mnt/data/share/alignment/data\n")
    out_scripts.write(f"    tar -xvf corpora.tar\n")
    out_scripts.write(f"    source ../.venv-eflomal/bin/activate\n")
    out_scripts.write(f"    python ../eflomal-cli.py -s {e_lc_basename} -t {f_lc_basename} "
                      f"-f {out_basename}.fwd -r {out_basename}.rev\n")
    out_scripts.write(f"    tar -cvf align.tar {out_basename}.fwd {out_basename}.rev\n")
    out_scripts.write(f"cd {args.output_dir}\n")
    out_scripts.write(f"scp -P 22 zion.isi.edu:/mnt/data/share/alignment/data/align.tar align.tar\n")
    out_scripts.write(f"tar -xvf align.tar\n")
    out_scripts.write(f"../../build/atools -i {out_basename}.fwd -j {out_basename}.rev -c grow-diag-final-and "
                      f"> align_lc\n")
    align_dir = f'{e_lang_code}-{f_lang_code}-ea' if e_lang_code and f_lang_code else 'xxx-xxx-ea'

    out_scripts.write("\n# Greek Room alignment (maybe run twice, at least initially)\n")
    out_scripts.write(f"ualign.py -t e_f_ref.txt -a align_lc -v {align_dir} -o e1.a "
                      f"-r f_tokens.uroman-map.txt -q e_tokens.uroman-map.txt "
                      f"-l log-e1.txt -e {e_lang_name} -f {f_lang_name} "
                      f"-c ../../../smart-edit-distance/data/string-distance-cost-rules.txt "
                      f"-b battery.jsonl -m ../morph_variants.txt\n")

    out_scripts.write("\n# Spell checker\n")
    e_core_name = os.path.basename(args.e_filename).removesuffix('.txt')
    f_core_name = os.path.basename(args.f_filename).removesuffix('.txt')
    out_scripts.write(f"mv battery-e.html spell-check-{e_core_name}.html\n")
    out_scripts.write(f"mv battery-f.html spell-check-{f_core_name}.html\n")
    spell_check_f_filename = f"spell-check-{f_core_name}.html"
    full_spell_check_f_filename = args.output_dir / spell_check_f_filename

    out_scripts.write("\n# Wildebeest\n")
    out_scripts.write(f"cd {cwd}\n")
    target_dir = relative_output_dir / f'wildebeest-{f_core_name}'
    out_scripts.write(f"wb_pprint_html.py -i {args.f_filename} -x {target_dir} -o {target_dir}/index.html "
                      f"-s vref.txt\n")
    wb_target_directory = Path(f'wildebeest-{f_core_name}')
    wb_target_index_filename = wb_target_directory / 'index.html'
    wb_full_target_index_filename = args.output_dir / wb_target_index_filename

    out_scripts.write(f"\n# Alignment visualization:\n")
    full_chapter_filename = None
    for chapter_filename in ['GEN-001.html', 'MAT-001.html']:
        full_chapter_filename_cand = align_viz_root_dir / align_dir / chapter_filename
        if os.path.exists(full_chapter_filename_cand):
            full_chapter_filename = full_chapter_filename_cand
            break
    if full_chapter_filename:
        target_filename = f'{relative_output_dir}/align-{f_core_name}-{os.path.basename(full_chapter_filename)}'
        if os.path.exists(target_filename):
            os.unlink(target_filename)
        os.symlink(full_chapter_filename, target_filename)
    full_align_dir = align_viz_root_dir / align_dir
    sel_align_viz_filename, full_sel_align_viz_filename = None, None
    if os.path.exists(full_align_dir):
        sel_full_filename = full_align_dir / 'sel.txt'
        if os.path.exists(sel_full_filename):
            out_scripts.write(f"# Existed: {sel_full_filename}\n")
        else:
            for sel_candidate in [f'{out_basename}.txt', f'{f_lang_code}.txt', 'default.txt']:
                full_sel_candidate = greek_room_data_root_dir / 'align-viz-sel' / sel_candidate
                if os.path.exists(full_sel_candidate):
                    os.link(full_sel_candidate, sel_full_filename)
                    break
            if os.path.exists(sel_full_filename):
                out_scripts.write(f"# Created: {sel_full_filename}\n")
        if os.path.exists(sel_full_filename):
            out_scripts.write(f"(cd {full_align_dir} && selected_verses.py -s sel.txt -d . -o sel.html)\n")
            sel_full_html_filename = full_align_dir / 'sel.html'
            sel_align_viz_filename = f"align-viz-sel-{f_core_name}.html"
            out_scripts.write(f"ll {sel_full_html_filename}; wc {sel_full_html_filename}\n")
            out_scripts.write(f"cp {sel_full_html_filename} {relative_output_dir}/align-viz-sel-{f_core_name}.html\n")
            full_sel_align_viz_filename = args.output_dir / sel_align_viz_filename

    out_scripts.write(f"\n# URLs:\n")
    if wb_full_target_index_filename and os.path.exists(wb_full_target_index_filename):
        out_scripts.write(f"{wb_full_target_index_filename}\n")  # Wildebeest html index page (f)
    if full_spell_check_f_filename and os.path.exists(full_spell_check_f_filename):
        out_scripts.write(f"{full_spell_check_f_filename}\n")  # Spell checker (f)
    if full_chapter_filename and os.path.exists(full_chapter_filename):
        out_scripts.write(f"{full_chapter_filename}\n")  # Alignment viz
    if full_sel_align_viz_filename and os.path.exists(full_sel_align_viz_filename):
        out_scripts.write(f"{full_sel_align_viz_filename}\n")  # Selected alignment viz

    if wb_target_directory and spell_check_f_filename and sel_align_viz_filename:
        out_scripts.write(f"\n# Greek Room tar ball for porta.isi.edu:\n")
        tar_filename = f'greek-room-{f_core_name}.tar'
        out_scripts.write(f"tar -cvf {tar_filename} {wb_target_directory} {spell_check_f_filename} "
                          f"{sel_align_viz_filename}\n")
        out_scripts.write(f"gzip {tar_filename}\n")
        out_scripts.write(f"scp -P 22 {tar_filename}.gz porta.isi.edu:/tmp/{tar_filename}.gz\n")

out_log.close()
out_scripts.close()


sys.stderr.write(f'Wrote results to directory {args.output_dir}\n')
if used_out_transfer_dir:
    sys.stderr.write(f'  Transfer directory: {out_transfer_dir}\n')
sys.stderr.write(f'  Scripts: {scripts_file}\n')

#!/usr/bin/env python
# Sample calls
# cd /Users/ulf2/projects/NLP/GreekRoom3/greekroom
# cd /Users/ulf2/projects/NLP/GreekRoom3/greekroom
# owl/repeated_words.py -j owl/data/samples_inputs/ceb_01.json -o tmp/repeated_words3.json
# owl/repeated_words.py -i /Users/ulf2/projects/NLP/fast_align/data/ceb-GGvlo4L7.txt
#  -r /Users/ulf2/projects/NLP/fast_align/data/vref.txt --lang_code ceb --lang_name Cebuano
#  --project_name "Cebuano Contemporary Bible (Biblica) 2025-07-10" --message_id "ceb-GGvlo4L7"
#  -o tmp/repeated_words3.json --html tmp/repeated_words3.html --verbose

import argparse
from collections import defaultdict
import datetime
import json
import os
from pathlib import Path
import random
import regex
import string
import sys
from typing import Dict, List, Tuple

from gr_utilities import general_util
from gr_utilities import html_util


def legit_dupl_data_filenames() -> List[str]:
    """find data files that list legitimate repeated words, both system and user defined"""
    result = []
    if owl_dir := os.path.dirname(os.path.realpath(__file__)):
        if owl_data_dir := os.path.join(owl_dir, "data"):
            if os.path.isdir(owl_data_dir):
                if data_filename := os.path.join(owl_data_dir, "legitimate_duplicates.jsonl"):
                    if os.path.exists(data_filename):
                        result.append(data_filename)
    for data_dir in general_util.standard_data_dirs():
        if os.path.isdir(data_dir):
            if owl_data_dir := os.path.join(data_dir, "greekroom", "owl", "data"):
                if os.path.isdir(owl_data_dir):
                    if data_filename := os.path.join(owl_data_dir, "legitimate_duplicates.jsonl"):
                        if os.path.exists(data_filename):
                            result.append(data_filename)
    return result


def read_legitimate_duplicate_data(filename: Path, d: dict, lang_code_restriction: str | None = None, 
                                   verbose: bool = False) -> None:
    """read in data files of legitimate repeated words"""
    with open(filename) as f_in:
        line_number = 0
        n_entries = 0
        lang_codes = set()
        for line in f_in:
            line_number += 1
            if regex.match(r"\s*\{.*\}", line):
                load_d = json.loads(line)
                lang_code = load_d.get('lang-code')
                if lang_code and lang_code_restriction and (lang_code != lang_code_restriction):
                    continue
                text = load_d.get('text')
                text2 = regex.sub(r'([-,]+\s*|\s+)', ' ', text)
                if text:
                    n_entries += 1
                    if lang_code:
                        lang_codes.add(lang_code)
                    d[(lang_code, 'legitimate-duplicate', text2)] = load_d
                    if d.get((lang_code, 'legitimate-duplicates')) is None:
                        d[(lang_code, 'legitimate-duplicates')] = []
                    d[(lang_code, 'legitimate-duplicates')].append(text2)
            elif regex.match(r'(#.*|\s*)$', line):
                # comment or empty line
                pass
            else:
                sys.stderr.write(f"* Warning: ignoring unrecognized line {line_number} "
                                 f"in legitimate duplicate file {filename}: {line.rstrip()}\n")
        n_lang = len(lang_codes)
        if verbose:
            sys.stderr.write(f"Loaded {n_entries} legitimate-duplicate entr{'y' if n_entries == 1 else 'ies'}"
                             f" in {n_lang} language{'' if n_lang == 1 else 's'} from {filename}\n")


def markup_duplicate_words(s: str, duplicate_words: str, color: str) -> str:
    """mark up string with color, typically green (known to be legitimate repeated word), red otherwise"""
    duplicate_word = regex.sub(r'(?:\pZ|\pC).*', '', duplicate_words)
    s = regex.sub(rf'\b({duplicate_word}(?:(?:\pZ|\pC)+{duplicate_word})+)\b',
                  rf'<span style="color:{color};">\1</span>',
                  s, flags=regex.IGNORECASE)
    return s


def check_for_repeated_words_in_line(line: str, snt_id: str, lang_code: str,
                                     repeated_word_list: List[dict], misc_data_dict: dict) \
        -> None:
    """identifies repeated words in a given line and adds result to corpus-wide list of repeated word entries"""
    if line:
        line_lc = line.rstrip().lower()
        words, start_positions, inter_words \
            = general_util.findall3(r"\pL\pM*(?:(?:'|\u200C|\u200D)?\pL\pM*)*", line_lc)
        for i in range(len(words) - 1):
            word = words[i]
            if (word == words[i + 1]) and regex.match(r'(?:\pZ|\pP)+$', inter_words[i + 1]):
                repeated_word = f'{word} {word}'
                surf = line[start_positions[i]:start_positions[i + 1] + len(words[i + 1])]
                legit_dupl_dict = misc_data_dict.get((lang_code, 'legitimate-duplicate', repeated_word))
                severity = 0.1 if legit_dupl_dict else 0.5
                repeated_word_list.append({"snt-id": snt_id,
                                           "repeated-word": repeated_word,
                                           "surf": surf,
                                           "start-position": start_positions[i],
                                           "legitimate": bool(legit_dupl_dict),
                                           "severity": severity})


def check_for_repeated_words(param_d: dict, data_filename_dict: Dict[str, List[str]],
                             corpus: general_util.Corpus | None = None, verbose: bool = False) \
        -> Tuple[dict, dict, dict]:
    """Input object to result object, error object, data dict
    snt_id2snt stores text (needed for HTML output)"""
    misc_data_dict = {}
    lang_code = param_d.get("lang-code")
    check_corpus = param_d.get("check-corpus")
    for data_filename in data_filename_dict.get("repeated-words"):
        read_legitimate_duplicate_data(Path(data_filename), misc_data_dict, None, verbose)
    repeated_word_list = []
    if check_corpus:
        for corpus_entry in check_corpus:
            snt = corpus_entry.get("text", "")
            snt_id = corpus_entry.get("snt-id", "").rstrip()
            check_for_repeated_words_in_line(snt, snt_id, lang_code, repeated_word_list, misc_data_dict)
    elif corpus:
        for snt_id in corpus.get_snt_ids():
            snt = corpus.lookup_snt(snt_id)
            check_for_repeated_words_in_line(snt, snt_id, lang_code, repeated_word_list, misc_data_dict)
    result = {"tool": "GreekRoom", "checks": [{"check": "RepeatedWords", "feedback": repeated_word_list}]}
    error = {}
    return result, error, misc_data_dict


def check_mcp(mcp_request: str, data_filename_dict: dict, corpus: general_util.Corpus, verbose: bool) \
        -> Tuple[dict, dict, List[dict]]:
    """Input object to result object and error object"""
    request_timestamp = datetime.datetime.now().replace(microsecond=0).isoformat()
    load_d = json.loads(mcp_request)
    load_d["request-timestamp"] = request_timestamp
    if verbose:
        load_s = str(load_d)
        snt_ids = regex.findall(r'\bsnt-id\b', load_s)
        if len(snt_ids) <= 100:
            sys.stderr.write(f"Input: {load_s}\n")
        else:
            sys.stderr.write(f"Input: {len(snt_ids)} entries\n")
    message_id = load_d.get("id")
    params = load_d.get("params")
    param_d = params[0]
    check_corpus_list = param_d.get("check-corpus")
    lang_code = param_d.get("lang-code")
    result_d, error_d, misc_data_dict = check_for_repeated_words(param_d, data_filename_dict, corpus, verbose)
    result_timestamp = datetime.datetime.now().replace(microsecond=0).isoformat()
    return_object = {"jsonrpc": "2.0", "id": message_id, "result-timestamp": result_timestamp, "lang-code": lang_code}
    if result_d:
        return_object["result"] = [result_d]
    if error_d:
        return_object["error"] = [error_d]
    return return_object, misc_data_dict, check_corpus_list


def get_feedback(output_d: dict, tool: str, check: str) -> List[dict] | None:
    if output_d.get('jsonrpc') and (results := output_d.get('result')):
        result = results[0]
    else:
        result = output_d
    if result and (result.get('tool') == tool) and (checks := result.get('checks')):
        for check2 in checks:
            if check2.get('check') == check:
                return check2.get('feedback')
    return None


def write_to_html(feedback: list, misc_data_dict: dict, corpus: general_util.Corpus, lang_code: str,
                  args: argparse.Namespace) -> None:
    html_out_filename = args.html
    repeated_word_dict = defaultdict(list)
    n_repeated_words = 0
    for feedback_d in feedback:
        snt_id = feedback_d.get('snt-id')
        if snt := corpus.lookup_snt(snt_id):
            repeated_word = feedback_d.get('repeated-word')
            surf = feedback_d.get('surf')
            start_position = feedback_d.get('start-position')
            legitimate = feedback_d.get('legitimate')
            color = "green" if legitimate else "red"
            end_position = start_position + len(surf)
            marked_up_verse = (f"{snt[:start_position]}"
                               f"<span style='color:{color};'>{snt[start_position:end_position]}</span>"
                               f"{snt[end_position:]}")
            repeated_word_dict[repeated_word].append(marked_up_verse)
            n_repeated_words += 1
    with open(html_out_filename, 'w') as f_html:
        date = f"{datetime.datetime.now():%B %-d, %Y at %-H:%M}"
        title = f"🦉 &nbsp; Greek Room Repeated Word Check"
        if project_id := args.project_name or args.lang_name or lang_code or args.in_filename:
            title += f" for <nobr>{project_id}</nobr>"
        meta_title = 'Dupl'
        if lang_code:
            meta_title += " " + lang_code
        f_html.write(html_util.html_head(title, date, meta_title))
        s = "" if n_repeated_words == 0 else "s"
        f_html.write(f"""<h3>Checking for repeated words (consecutive duplicates): """
                     f"""{n_repeated_words} instance{s}</h3>\n""")
        f_html.write("<ul>\n")
        for duplicate in sorted(repeated_word_dict.keys(), key=lambda x: (-len(repeated_word_dict[x]), x)):
            if legit_dupl_dict := misc_data_dict.get((lang_code, 'legitimate-duplicate', duplicate)):
                eng_gloss = legit_dupl_dict['gloss'].get('eng')
                non_latin_characters = regex.findall(r'(?V1)[\pL--\p{Latin}]', duplicate)
                rom = legit_dupl_dict.get('rom')
                title = duplicate + 50 * ' '
                if rom and non_latin_characters:
                    title += f"&#xA;Romanization: {rom}"
                if eng_gloss:
                    title += f"&#xA;English gloss: {eng_gloss}"
                title += f"&#xA;Listed as legitimate for {args.lang_name}"
                title = html_util.html_title_guard(title)
                duplicate2 = (f"<span patitle='{title}' style='color:green;border-bottom:1px dotted;'>"
                              f"{duplicate}</span>")
            else:
                duplicate2 = duplicate
            n_instances = len(repeated_word_dict[duplicate])
            f_html.write(f"<li> {duplicate2} ({n_instances})\n   <ul>\n")
            for marked_up_verse in repeated_word_dict[duplicate]:
                f_html.write(f"    <li> {marked_up_verse}\n")
            f_html.write("    </ul>\n")
        f_html.write("</ul>\n")
        html_util.print_html_foot(f_html)
        cwd_path = Path(os.getcwd())
        full_html_output_filename = (html_out_filename
                                     if html_out_filename.startswith('/')
                                     else (cwd_path / html_out_filename))
        sys.stderr.write(f"Wrote HTML to {full_html_output_filename}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-j', '--json', type=str, help='input (alternative 1)')
    parser.add_argument('-i', '--in_filename', type=str, help='text file (alternative 2)')
    parser.add_argument('-r', '--ref_filename', type=Path, default='vref.txt', help='ref file (alt. 2)')
    parser.add_argument('-o', '--out_filename', type=str, default=None, help='output JSON filename')
    parser.add_argument('--html', type=str, default=None, help='output HTML filename')
    parser.add_argument('--project_name', type=str, help='full name of Bible translation project')
    parser.add_argument('--lang_code', type=str, default=None,
                        metavar='LANGUAGE-CODE', help="ISO 639-3, e.g. 'fas' for Persian")
    parser.add_argument('--lang_name', type=str, default=None)
    parser.add_argument('--message_id', type=str, default=None)
    parser.add_argument('-d', '--data_filenames', default=None)
    parser.add_argument('--verbose', action='count', default=0)
    args = parser.parse_args()

    verbose = args.verbose
    message_id, lang_code, lang_name, project_name = args.message_id, args.lang_code, args.lang_name, args.project_name
    html_out_filename = args.html
    json_out_filename = args.out_filename
    corpus = None
    task_s = None
    data_filename_dict = defaultdict(list)
    repeated_words_data_filenames = data_filename_dict["repeated-words"]
    data_filenames = args.data_filenames or legit_dupl_data_filenames()
    for data_filename in data_filenames:
        if data_filename not in repeated_words_data_filenames:
            repeated_words_data_filenames.append(data_filename)
    if args.json and os.path.exists(args.json):
        try:
            with open(args.json) as f_in:
                task_s = f_in.read()
        except IOError:
            sys.stderr.write(f"Could not read JSON input file {args.json}")
            return
    if (not task_s) and args.in_filename and os.path.exists(args.in_filename):
        corpus = general_util.Corpus()
        n_entries, error_message = corpus.load_corpus_with_vref(args.in_filename, args.ref_filename)
        if error_message:
            sys.stderr.write(f"{error_message}\n")
            return
        param_d = {'lang-code': lang_code,
                   'lang-name': lang_name,
                   'project-name': project_name,
                   'selectors': [{'tool': 'GreekRoom', 'checks': ['RepeatedWords']}]}
        if not message_id:
            message_id = f"{lang_code}-{''.join(random.choices(string.ascii_letters + string.digits, k=8))}"
        task_d = {'jsonrpc': '2.0',
                  'id': message_id,
                  'method': 'BibleTranslationCheck',
                  'params': [param_d]}
        task_s = json.dumps(task_d)
    mcp_d, misc_data_dict, check_corpus_list = check_mcp(task_s, data_filename_dict, corpus, verbose)
    feedback = get_feedback(mcp_d, 'GreekRoom', 'RepeatedWords')
    if verbose:
        if len(feedback) > 100:
            sys.stderr.write(f"Output: {len(feedback)} entries\n")
        else:
            sys.stderr.write(f"Output: {json.dumps(mcp_d)}\n")
    if json_out_filename:
        try:
            with open(json_out_filename, 'w') as f_out:
                f_out.write(f"{json.dumps(mcp_d)}\n")
        except IOError:
            sys.stderr.write(f"Cannot write JSON output to {json_out_filename}\n")
    if html_out_filename:
        if corpus is None and check_corpus_list:
            corpus = general_util.Corpus()
            corpus.load_corpus_from_in_dict(check_corpus_list)
        lang_code = mcp_d.get("lang-code") or args.lang_code
        write_to_html(feedback, misc_data_dict, corpus, lang_code, args)


if __name__ == "__main__":
    main()

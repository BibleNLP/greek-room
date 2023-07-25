#!/usr/bin/env python
# cd /Users/ulf/projects/NLP/fast_align/data
# /Users/ulf/GreekRoom/utilities/ualign.py -t en-NRSV_de-LU84NR06_ref.txt -e English -f German
# -a en-NRSV_de-LU84NR06.align_lc -v eng-deu -o en-NRSV_de-LU84NR06_lc.i1.a -l log-deu.txt

import argparse
from collections import defaultdict
import copy
import cProfile
import datetime
import json
import math
import os
from pathlib import Path
import pstats
import regex
import sys
from typing import Optional, TextIO, Union
from smart_edit_distance import SmartEditDistance
import unicodedata as ud


def timer(func):
    def wrapper(*args, **kwargs):
        start_time = datetime.datetime.now()
        print(f"Calling: {func.__name__}{args}")
        print(f"Start time: {start_time:%A, %B %d, %Y at %H:%M}")
        result = func(*args, **kwargs)
        end_time = datetime.datetime.now()
        time_diff = (end_time-start_time).total_seconds()
        print(f"End time: {end_time:%A, %B %d, %Y at %H:%M}")
        print(f"Duration: {time_diff} seconds")
        return result
    return wrapper


def guard_html(s):
    s = regex.sub('&', '&amp;', s)
    s = regex.sub('<', '&lt;', s)
    s = regex.sub('>', '&gt;', s)
    s = regex.sub('"', '&quot;', s)
    return s


def is_punct(s: str) -> bool:
    return bool(regex.match(r'\pP+$', s))


def sub_strings(s: str, min_len: int) -> list[str]:
    result = []
    s_len = len(s)
    for sub_len in range(len(s), min_len-1, -1):
        for start_index in range(0, s_len-sub_len+1):
            end_index = start_index+sub_len
            result.append(s[start_index:end_index])
    return result


def pmi(a_count: float, b_count: float, ab_count: float, total_count: float, smoothing: float = 1.0) -> float:
    if a_count == 0 or b_count == 0 or total_count == 0:
        return 0
    else:
        p_a = a_count / total_count
        p_b = b_count / total_count
        expected_ab = p_a * p_b * total_count
        if expected_ab == 0 and smoothing == 0:
            return -99
        else:
            return math.log((ab_count + smoothing) / (expected_ab + smoothing))


def de_tokenize_text(s: str) -> str:
    s = regex.sub(r'''(?<!\S)\@(?=[-—:"“”'‘’])''', '', s)
    s = regex.sub(r'''(?<=[-—:"“”'‘’])\@(?!\S)''', '', s)
    s = regex.sub(' (?=[.,;:?!])', '', s)
    s = regex.sub(' ([-]) ', r'\1', s)
    return s


def decode_unicode_escape(s: str) -> str:
    while m3 := regex.match(r'(.*?)\\u([0-9A-Fa-f]{4,4})(.*)$', s):
        code_point = int(f'0x{m3.group(2)}', 0)
        s = m3.group(1) + chr(code_point) + m3.group(3)
    return s


def encode_unicode_escape(s: str) -> str:
    result = ''
    for c in s:
        cp = ord(c)
        if 0x0080 <= cp <= 0xFFFF:
            result += f'\\u{cp:04X}'
        else:
            result += c
    return result


class DocumentConfiguration:
    def __init__(self, config_filename: Path):
        self.doc_dict = {}
        self.lang_name_to_code = {}
        self.lang_code_to_name = {}
        with open(config_filename) as f:
            line_number = 0
            for line in f:
                line_number += 1
                if line.strip() == '':
                    continue  # ignore empty line
                try:
                    d = json.loads(line)
                except json.decoder.JSONDecodeError as error:
                    sys.stderr.write(f'Error: {config_filename} line {line_number}: {error}\n')
                    continue
                doc_conf_id = d['id']
                lang_code = d['lc']
                lang_name = d['lang']
                if doc_conf_id:
                    if self.doc_dict.get(doc_conf_id, None):
                        sys.stderr.write(f'Ignoring entry with duplicate ID {doc_conf_id} '
                                         f'in {config_filename} line {line_number}\n')
                    else:
                        self.doc_dict[doc_conf_id] = d
                else:
                    sys.stderr.write(f'Ignoring entry with missing ID {doc_conf_id} '
                                     f'in {config_filename} line {line_number}\n')
                if lang_code and lang_name:
                    existing_code = self.lang_name_to_code.get(lang_name, None)
                    if existing_code and (existing_code != lang_code):
                        sys.stderr.write(f'Ignoring conflicting new mapping {lang_name} to {lang_code} '
                                         f'in {config_filename} line {line_number}\n')
                    else:
                        self.lang_name_to_code[lang_name] = lang_code
                    existing_name = self.lang_code_to_name.get(lang_code, None)
                    if existing_name and (existing_name != lang_name):
                        sys.stderr.write(f'Ignoring conflicting new mapping {lang_code} to {lang_name} '
                                         f'in {config_filename} line {line_number}\n')
                    else:
                        self.lang_code_to_name[lang_code] = lang_name


class EvaluationStats:
    def __init__(self):
        self.bible_book_chapter_length = \
            {'GEN': 50, 'EXO': 40, 'LEV': 27, 'NUM': 36, 'DEU': 34, 'JOS': 24, 'JDG': 21, 'RUT': 4,
             '1SA': 31, '2SA': 24, '1KI': 22, '2KI': 25, '1CH': 29, '2CH': 36, 'EZR': 10, 'NEH': 13,
             'EST': 10, 'JOB': 42, 'PSA': 150, 'PRO': 31, 'ECC': 12, 'SNG': 8, 'ISA': 66, 'JER': 52,
             'LAM': 5, 'EZK': 48, 'DAN': 12, 'HOS': 14, 'JOL': 4, 'AMO': 9, 'OBA': 1, 'JON': 4,
             'MIC': 7, 'NAM': 3, 'HAB': 3, 'ZEP': 3, 'HAG': 2, 'ZEC': 14, 'MAL': 3,
             'MAT': 28, 'MRK': 16, 'LUK': 24, 'JHN': 21, 'ACT': 28, 'ROM': 16, '1CO': 16, '2CO': 13,
             'GAL': 6, 'EPH': 6, 'PHP': 4, 'COL': 4, '1TH': 5, '2TH': 3, '1TI': 6, '2TI': 4, 'TIT': 3,
             'PHM': 1, 'HEB': 13, 'JAS': 5, '1PE': 5, '2PE': 3, '1JN': 5, '2JN': 1, '3JN': 1, 'JUD': 1, 'REV': 22,
             'TOB': 14, 'JDT': 16, 'ESG': 7, 'WIS': 19, 'SIR': 51, 'BAR': 5, '1MA': 16, '2MA': 15, 'MAN': 1}
        self.chapter_n_sentences = defaultdict(int)
        self.chapter_weights = defaultdict(float)
        self.chapter_score_sums = defaultdict(float)
        self.chapter_avg_scores = defaultdict(float)
        self.book_n_sentences = defaultdict(int)
        self.book_weights = defaultdict(float)
        self.book_score_sums = defaultdict(float)
        self.book_avg_scores = defaultdict(float)
        self.bible_n_sentences = 0
        self.bible_weights = 0.0
        self.bible_score_sums = 0.0
        self.bible_avg_scores = None

    def add_score(self, score_sum: float, weight: float, snt_id: str) -> None:
        if m2 := regex.match(r'([A-Z1-9][A-Z][A-Z])\s*(\d+):\d+$', snt_id):
            book_id = m2.group(1)
            chapter_number = int(m2.group(2))
        else:
            book_id, chapter_number = None, None
        self.bible_n_sentences += 1
        self.bible_weights += weight
        self.bible_score_sums += score_sum
        self.bible_avg_scores \
            = (self.bible_score_sums / self.bible_weights if self.bible_weights else None)
        if book_id:
            self.book_n_sentences[book_id] += 1
            self.book_weights[book_id] += weight
            self.book_score_sums[book_id] += score_sum
            self.book_avg_scores[book_id] \
                = (self.book_score_sums[book_id] / self.book_weights[book_id]
                   if self.book_weights[book_id] else None)
            if chapter_number:
                chapter_id = (book_id, chapter_number)
                self.chapter_n_sentences[chapter_id] += 1
                self.chapter_weights[chapter_id] += weight
                self.chapter_score_sums[chapter_id] += score_sum
                self.chapter_avg_scores[chapter_id] \
                    = (self.chapter_score_sums[chapter_id] / self.chapter_weights[chapter_id]
                       if self.chapter_weights[chapter_id] else None)


class VerboseManager:
    """Handles verbose cases"""
    def __init__(self):
        self.log_fw_crisp = False
        self.log_stem_probs = True
        self.log_alignment_diff_details = defaultdict(list)


class VisualizationFileManager:
    """Handles the output file by file"""
    def __init__(self, e_lang_name: str, f_lang_name: str, html_filename_dir: Path, text_filename: Path,
                 prop_filename: Optional[Path]):
        self.current_book_id = None
        self.current_chapter_id = None
        self.current_chapter_number = None
        self.e_lang_name = e_lang_name
        self.f_lang_name = f_lang_name
        self.html_filename_dir = html_filename_dir
        self.text_filename = text_filename
        self.prop_filename = prop_filename
        self.f_html = None
        self.eval_stats = EvaluationStats()

        basename = self.html_filename_dir.name
        self.cgi_box = \
            f'<table><form action="http://localhost/cgi-bin/filter-viz-snt-align.py" target="filter" ' \
            f'method="post">' \
            f'<tr><td rowspan="2" valign="middle" align="center">' \
            f'        <span style="font-weight:bold;">Search<br>Bible</span></td> ' \
            f'    <td><input type="text" name="e_search_term" placeholder="{self.e_lang_name} side"/> ' \
            f'        <input type="hidden" name="text_filename" value="{str(self.text_filename)}"/> ' \
            f'        <input type="hidden" name="html_filename_dir" value="{str(self.html_filename_dir)}"/> ' \
            f'        <input type="hidden" name="log_filename" value="log/filter-{basename}.txt"/> ' \
            f'        <input type="hidden" name="e_lang_name" value="{self.e_lang_name}"/> ' \
            f'        <input type="hidden" name="f_lang_name" value="{self.f_lang_name}"/></td> ' \
            f'    <td><input type="text" name="e_prop" placeholder="{self.e_lang_name} meta info">' \
            f'        <input type="hidden" name="prop_filename" value="{str(self.prop_filename)}"/></td> ' \
            f'    <td>Sample: <input type="text" name="sample_percentage" size="2"/>% ' \
            f'      or<input type="checkbox" name="auto_sample">auto</td></tr>' \
            f'<tr><td><input type="text" name="f_search_term" placeholder="{self.f_lang_name} side"/></td> ' \
            f'    <td><input type="text" name="f_prop" placeholder="{self.f_lang_name} meta info">' \
            f'    <td align="center">Max: <input type="text" name="max_number_output_snt" value="100" size="5"/>' \
            f' &nbsp; <input type="submit" value="&nbsp; &nbsp;Submit&nbsp; &nbsp;" /></td></tr>' \
            f'</form></table>'

    def new_ref(self, ref: str):
        if m2 := regex.match(r'([A-Z1-9][A-Z][A-Z])\s*(\d+):\d+$', ref):
            new_book_id = m2.group(1)
            new_chapter_number = int(m2.group(2))
            new_chapter_id = f'{m2.group(1)}-{int(m2.group(2)):03d}'
            if new_chapter_id and new_chapter_id != self.current_chapter_id:
                if self.current_chapter_id:
                    self.finish_visualization_file(new_book_id != self.current_book_id)
                    self.current_chapter_id, self.current_chapter_number = None, None
                if new_chapter_id != '-':
                    self.current_chapter_id = new_chapter_id
                    self.current_chapter_number = new_chapter_number
                    self.current_book_id = new_book_id
                    if self.html_filename_dir:
                        html_filename = self.html_filename_dir / f'{new_chapter_id}.html'
                        self.f_html = open(html_filename, "w")
                        print_html_head(self.f_html, self.e_lang_name, self.f_lang_name, self.cgi_box)
                        self.f_html.write('<a name="index-1">\n')
                        self.print_visualization_index()
                        self.f_html.write('<br>\n')

    def finish_visualization_file(self, end_of_chapter: bool):
        f_html = self.f_html
        if f_html and self.current_chapter_id:
            book_id, chapter_number = self.current_book_id, self.current_chapter_number
            eval_stats = self.eval_stats
            f_html.write('<a name="avg-score">\n')
            avg_score = eval_stats.chapter_avg_scores[(book_id, chapter_number)]
            n_sentences = eval_stats.chapter_n_sentences[(book_id, chapter_number)]
            f_html.write(f'<b>{book_id} {chapter_number}</b> &nbsp; &nbsp; '
                         f'Average alignment score: {round(avg_score, 3)} '
                         f'for {n_sentences} sentences.')
            if (self.html_filename_dir / 'eval.html').is_file():
                f_html.write(f' &nbsp; &nbsp; <a href="eval.html">Evaluation statistics page</a>')
            f_html.write('<br><br>\n')
            f_html.write('<a name="index-2">\n')
            self.print_visualization_index()
            f_html.write('<a name="end">\n')
            print_html_foot(f_html)
            f_html.close()
            self.f_html = None
            if end_of_chapter:
                sys.stderr.write(f" {book_id}")
                sys.stderr.flush()

    def print_visualization_index(self):
        current_book_id, current_chapter_number = self.current_book_id, self.current_chapter_number
        f_html, eval_stats = self.f_html, self.eval_stats
        f_html.write('<table border="0" cellpadding="3" cellspacing="0">')
        for book_id, n_chapters in eval_stats.bible_book_chapter_length.items():
            if book_id == "GEN":
                f_html.write('<tr><td valign="top"><b><nobr>Old Testament:</nobr></b></td><td>')
            elif book_id == "MAT":
                f_html.write('</td></tr>\n<tr><td valign="top"><b><nobr>New Testament:</nobr></b></td><td>')
            elif book_id == "TOB":
                f_html.write('</td></tr>\n<tr><tr><td valign="top"><b><nobr>Apocrypha:</nobr></b></td><td>')
            # search for first available filename (some might not exist)
            html_filename = None
            for chapter_number in range(1, n_chapters+1):
                cand_html_filename = f'{book_id}-{chapter_number:03d}.html'
                full_html_filename = self.html_filename_dir / cand_html_filename
                if full_html_filename.is_file():
                    html_filename = cand_html_filename
                    break
            if book_id == current_book_id:
                f_html.write(f'<span style="font-weight:bold;">{book_id}</span>&nbsp; ')
            elif html_filename:
                f_html.write(f'<a href="{html_filename}" title="{n_chapters} chapter{"" if n_chapters == 1 else "s"}">'
                             f'{book_id}</a>&nbsp; ')
            else:
                f_html.write(f'<span style="color:#777777;">{book_id}</span>&nbsp; ')
        f_html.write('<br>\n')
        if current_book_id and (n_chapters := eval_stats.bible_book_chapter_length.get(current_book_id)):
            f_html.write(f'</td></tr>\n'
                         f'<tr><td valign="top"><b><nobr>Chapters of {current_book_id}:</nobr></b></td><td>')
            for chapter_number in range(1, n_chapters+1):
                html_filename = f'{current_book_id}-{chapter_number:03d}.html'
                full_html_filename = self.html_filename_dir / html_filename
                if chapter_number == current_chapter_number:
                    f_html.write(f'<span style="font-weight:bold;">{chapter_number}</span>&nbsp; ')
                elif Path(full_html_filename).is_file():
                    f_html.write(f'<a href="{html_filename}">{chapter_number}</a>&nbsp; ')
                else:
                    f_html.write(f'<span style="color:#777777;">{chapter_number}</span>&nbsp; ')
        f_html.write('</td></tr></table><br>\n')

    def print_visualization_eval_stats(self):
        eval_stats = self.eval_stats
        html_filename = self.html_filename_dir / 'eval.html'
        with open(html_filename, "w") as f_html:
            self.f_html = f_html
            print_html_head(f_html, self.e_lang_name, self.f_lang_name, self.cgi_box)
            self.print_visualization_index()
            f_html.write('<br>\n')
            f_html.write('<table border="0" cellpadding="3" cellspacing="0">')
            f_html.write(f"<tr><th>Book</th><th>Avg. score</th><th>#snt</th></tr>\n")
            avg_score = eval_stats.bible_avg_scores
            n_sentences = eval_stats.bible_n_sentences
            f_html.write(f"<tr><td><b>All</b></td><td align='center'><b>{round(avg_score, 3):5.3f}</b></td>"
                         f"<td align='right'><b>{n_sentences}</b></td></tr>\n")
            for book_id, n_chapters in eval_stats.bible_book_chapter_length.items():
                avg_score = eval_stats.book_avg_scores[book_id]
                n_sentences = eval_stats.book_n_sentences[book_id]
                if n_sentences == 0:
                    avg_score = ''
                else:
                    avg_score = f'{round(avg_score, 3):5.3f}'
                f_html.write(f"<tr><td>{book_id}</td><td align='center'>{avg_score}</td>"
                             f"<td align='right'>{n_sentences}</td></tr>\n")
            f_html.write('</table>\n')
            print_html_foot(f_html)
            self.f_html = None


class WeightedAlignmentCounts:
    def __init__(self, abwc: float, bawc: float, ac: int, bc: int):
        self.abwc = abwc  # a-b (e-f or f-e) weighted count
        self.bawc = bawc
        self.ac = ac
        self.bc = bc

    def unpack(self):
        return self.abwc, self.bawc, self.ac, self.bc


class ColorStringAlternative:
    def __init__(self):
        pass

    def match_lists(self, l1: list[str], l2: list[str]) -> (list[int], list[int]):
        """Maximally matches lists, returning lists of 0s (no match) and 1s (match)"""
        l1 = [x.lower() for x in l1]
        l2 = [x.lower() for x in l2]
        for length in range(min(len(l1), len(l2)), 0, -1):
            for start1 in range(len(l1)-length+1):
                for start2 in range(len(l2)-length+1):
                    if l1[start1:start1+length] == l2[start2:start2+length]:
                        pre1, pre2 = self.match_lists(l1[0:start1], l2[0:start2])
                        post1, post2 = self.match_lists(l1[start1+length:], l2[start2+length:])
                        return (pre1 + [1] * length + post1, pre2 + [1] * length + post2)
        return ([0] * len(l1), [0] * len(l2))

    @staticmethod
    def split_s(s: str) -> list[str]:
        return regex.findall(r'(?:\pL\pM*?(?:\u094D\pL\pM*?)*\pM*|.)', s)   # \u094D is DEVANAGARI SIGN VIRAMA

    def match_strings(self, s1: str, s2: str) -> str:
        i1, i2 = self.match_lists(self.split_s(s1), self.split_s(s2))
        return ''.join(map(str, i1)) + ' ' + ''.join(map(str, i2))

    @staticmethod
    def markup_string_list(s_list: list[str], i_list: list[int], pale: bool = False, max_i: int = 1) -> str:
        result = ''
        open_span = False
        prev_i = None
        for s, i in zip(s_list, i_list):
            if i == prev_i and open_span:
                result += guard_html(s)
            else:
                if open_span:
                    result += '</span>'
                if i == max_i:
                    result += f"""<span style="color:{'#88CC88' if pale else '#008800'};">"""
                elif i:
                    result += f"""<span style="color:{'#8888FF' if pale else '#0000FF'};">"""
                else:
                    result += f"""<span style="color:{'#FF8888' if pale else '#FF0000'};">"""
                open_span = True
                result += guard_html(s)
            prev_i = i
        if open_span:
            result += '</span>'
        return result

    def markup_strings_diffs(self, s1: str, s2_list: list[str], pale: bool = False, prev_reg: Optional[dict] = None) \
            -> list[str]:
        anchor_list = self.split_s(s1)
        alt_lists = []
        n_alts = 0
        acc_i1 = [0] * len(anchor_list)
        result = []
        all_pale = True
        for s2 in s2_list:
            n_alts += 1
            alt_list = self.split_s(s2)
            alt_lists.append(alt_list)
            i1, i2 = self.match_lists(anchor_list, alt_list)
            acc_i1 = [sum(x) for x in zip(acc_i1, i1)]
            pale2 = pale or (prev_reg and prev_reg[(s2, s1)])
            if not pale2:
                all_pale = False
            result.append(self.markup_string_list(alt_list, i2, pale2))
        result.insert(0, self.markup_string_list(anchor_list, acc_i1, pale or all_pale, n_alts))
        return result


class AffixMorphVariantCheck:
    """Bla"""
    def __init__(self, lang_code: str, suffix_group: list[str],
                 core_suffix_exceptions: list[str], core_suffix_requirements: list[str]) -> None:
        self.lang_code = lang_code
        self.suffix_group = suffix_group
        self.core_suffix_exceptions = core_suffix_exceptions
        self.core_suffix_requirements = core_suffix_requirements

    @staticmethod
    def s_to_word_list(s: str) -> list[str]:
        """Map string representing list of strings to list of strings, e.g. "'', 'en'" to ['', 'en']"""
        result = []
        if s is not None:
            s = decode_unicode_escape(s)
            for quoted_suffix in regex.split(r',\s*', s):
                suffix = quoted_suffix.strip("'")
                result.append(suffix)
        return result

    @staticmethod
    def common_prefix_different_suffixes(s1: str, s2: str) -> tuple[str, str, str]:
        """Returns common leading substring, suffix1, suffix2"""
        min_len = min(len(s1), len(s2))
        for i in range(min_len):
            if s1[i] != s2[i]:
                return (s1[0:i], s1[i:], s2[i:])
        return (s1[0:min_len], s1[min_len:], s2[min_len:])

    @staticmethod
    def read_file(filename: str, d: dict) -> None:
        a = AffixMorphVariantCheck
        n_entries = 0
        with open(filename) as f:
            for line in f:
                if line.startswith('#'):
                    continue
                if regex.match(r'^\s*$', line):   # blank line
                    continue
                line = regex.sub(r'\s{2,}#.*$', '', line)   # remove comments
                lang_code = slot_value_in_double_colon_del_list(line, 'lc')
                s_group = a.s_to_word_list(slot_value_in_double_colon_del_list(line, 'suffix-group'))
                s_exceptions = a.s_to_word_list(slot_value_in_double_colon_del_list(line, 'core-suffix-exceptions'))
                s_requirements = a.s_to_word_list(slot_value_in_double_colon_del_list(line, 'core-suffix-requirements'))
                no_variants = a.s_to_word_list(slot_value_in_double_colon_del_list(line, 'no-variants'))
                affix_morph_variant_check = AffixMorphVariantCheck(lang_code, s_group, s_exceptions, s_requirements)
                n_entries += 1
                if lang_code:
                    if s_group:
                        for s1 in s_group:
                            for s2 in s_group:
                                if s1 != s2:
                                    d[(lang_code, 'suffix', s1, s2)].append(affix_morph_variant_check)
                    elif no_variants:
                        for s1 in no_variants:
                            for s2 in no_variants:
                                if s1 != s2:
                                    d[(lang_code, 'no-variants', s1, s2)].append(affix_morph_variant_check)
        sys.stderr.write(f'Read {n_entries} entries from {filename}\n')

    @staticmethod
    def is_morph_variant(s1: str, s2: str, lang_code: str, d: dict):
        common_prefix, suffix1, suffix2 = AffixMorphVariantCheck.common_prefix_different_suffixes(s1, s2)
        for affix_morph_variant_check in d[(lang_code, 'suffix', suffix1, suffix2)]:
            if affix_morph_variant_check.core_suffix_exceptions:
                rule_exception = False
                for exception in affix_morph_variant_check.core_suffix_exceptions:
                    if common_prefix.endswith(exception):
                        rule_exception = True
                        break
                if rule_exception:
                    continue
            if affix_morph_variant_check.core_suffix_requirements:
                rule_requirement = False
                for requirement in affix_morph_variant_check.core_suffix_requirements:
                    if common_prefix.endswith(requirement):
                        rule_requirement = True
                        break
                if not rule_requirement:
                    continue
            return True
        return False


class AlignmentModel:
    """Captures word counts, translation word counts etc. One AlignmentModel per direction (e.g. e/e_f; f/f_e)."""
    def __init__(self, name: str, lang_code: Optional[str] = None):
        self.lang_code = lang_code
        self.affix_morph_variant_check_dict = None
        self.counts = defaultdict(int)
        self.tc_counts = defaultdict(int)  # true case
        self.tc_alts = defaultdict(list)  # lower case to list of true cases
        self.total_count = 0
        self.avg_total_count = 0
        self.aligned_words = defaultdict(set)
        self.bi_counts = defaultdict(int)
        self.bi_weighted_counts = defaultdict(float)  # example key: ('kings', 'könige')
        self.glosses = defaultdict(str)
        self.fertilities = defaultdict(list)
        self.discontinuities = defaultdict(int)
        self.support_probabilities = {}  # for caching, index: (rev, self.token, rev.token)
        self.romanization = {}
        self.name = name
        self.sub_counts = defaultdict(int)  # example key: 'creat'
        self.sub_bi_weighted_counts = defaultdict(float)  # example key: ('geschaffen', 'creat')
        self.sub_bi_weighted_counts_with_context = defaultdict(float)
        # example key: ('geschaffen', 'creat', '(?<!x)', '(?!y)')
        self.sub_aligned_words = defaultdict(set[str])
        self.sub_super_words_left = defaultdict(set)
        self.sub_super_words_right = defaultdict(set)
        self.stem_exceptions_left = defaultdict(set)  # example key: ('king', 'königs')
        self.stem_exceptions_right = defaultdict(set)
        self.stem_exception_contexts = defaultdict(set)  # example key: 'könig'  value: list of (flc, frc)
        self.stem_to_surf = defaultdict(set)
        self.function_word_scores = defaultdict(float)
        self.aligned_stems = defaultdict(set)  # ex. key: 'e'
        self.aligned_stem_contexts = defaultdict(set)  # ex. key ('e', 'fs') or 'fs'
        self.bi_weighted_stem_counts = defaultdict(float)  # ex. key: ('e', 'fs')
        self.bi_weighted_stem_counts_with_context = defaultdict(float)  # ex. key: ('e', 'fs', 'flc', 'frc')
        self.aligned_bi_stems = defaultdict(set)  # ex. key: 'es'
        self.aligned_bi_stem_contexts = defaultdict(set)  # ex. key ('es', 'fs')
        self.bi_weighted_bi_stem_counts = defaultdict(WeightedAlignmentCounts)  # ex. key: ('es', 'fs')
        self.bi_weighted_bi_stem_counts_with_context = defaultdict(WeightedAlignmentCounts)
        # bi_weighted_bi_stem_counts_with_context ex. key: ('es', 'fs', 'flc', 'frc')
        self.stem_counts = defaultdict(int)
        self.stem_counts_with_context = defaultdict(int)  # example key: ('könig', '(?<!x|y)', '(?!in)')
        self.alignment_context = defaultdict(int)
        self.verses = defaultdict(str)  # key: ref (e.g. "GEN 1:1")  value: "In the beginning ..."

    def sub_super_words_a(self, side):
        return self.sub_super_words_left if side == 'left' else self.sub_super_words_right

    def stem_exceptions_a(self, side):
        return self.stem_exceptions_left if side == 'left' else self.stem_exceptions_right

    def load_romanization(self, filename: str, stderr: Optional[TextIO]):
        """"""
        line_number = 0
        n_entries = 0
        if os.path.exists(filename):
            with open(filename) as f_rom:
                for line in f_rom:
                    line_number += 1
                    if m2 := regex.match(r'\s*(\S.*\S|\S)\s+\|\|\|\s+(\S.*\S|\S)\s*$', line):
                        self.romanization[m2.group(1).lower()] = m2.group(2).lower()
                        n_entries += 1
            if stderr:
                stderr.write(f'load_romanization: {n_entries} entries in {line_number} lines.\n')
        else:
            stderr.write(f'load_romanization: file {filename} does not exist. No entries loaded.\n')

    def load_alignment_model1(self, rev, filename: str, stderr: Optional[TextIO]):
        """rev is reverse AlignmentModel"""
        line_number = 0
        n_entries = 0
        with open(filename) as f_am:
            for line in f_am:
                line_number += 1
                if line.startswith('::e '):
                    e = slot_value_in_double_colon_del_list(line, 'e')
                    count = slot_value_in_double_colon_del_list(line, 'count')
                    if fert := slot_value_in_double_colon_del_list(line, 'fert'):
                        self.fertilities[e] = list(map(int, fert.split('/')))
                    if disc := slot_value_in_double_colon_del_list(line, 'disc'):
                        self.discontinuities[e] = int(disc)
                    if gloss := slot_value_in_double_colon_del_list(line, 'gloss'):
                        self.glosses[e] = gloss
                    if function_word_score := slot_value_in_double_colon_del_list(line, 'fw'):
                        self.function_word_scores[e] = float(function_word_score)
                    self.counts[e] = int_or_float(count)
                    if e != 'NULL':
                        self.total_count += self.counts[e]
                    n_entries += 1
                elif line.startswith('::f '):
                    f = slot_value_in_double_colon_del_list(line, 'f')
                    count = slot_value_in_double_colon_del_list(line, 'count')
                    if fert := slot_value_in_double_colon_del_list(line, 'fert'):
                        rev.fertilities[f] = list(map(int, fert.split('/')))
                    if disc := slot_value_in_double_colon_del_list(line, 'disc'):
                        rev.discontinuities[f] = int(disc)
                    if gloss := slot_value_in_double_colon_del_list(line, 'gloss'):
                        rev.glosses[f] = gloss
                    if function_word_score := slot_value_in_double_colon_del_list(line, 'fw'):
                        rev.function_word_scores[f] = float(function_word_score)
                    rev.counts[f] = int_or_float(count)
                    if f != 'NULL':
                        rev.total_count += rev.counts[f]
                    n_entries += 1
                elif line.startswith('::efc '):
                    e, f, weighted_count, count = regex.split(' {2,}', slot_value_in_double_colon_del_list(line, 'efc'))
                    self.aligned_words[e].add(f)
                    self.bi_weighted_counts[(e, f)] = int_or_float(weighted_count)
                    self.bi_counts[(e, f)] = int(count)
                    if gloss := slot_value_in_double_colon_del_list(line, 'gloss'):
                        self.glosses[f] = gloss
                    n_entries += 1
                elif line.startswith('::fec '):
                    f, e, weighted_count, count = regex.split(' {2,}', slot_value_in_double_colon_del_list(line, 'fec'))
                    rev.aligned_words[f].add(e)
                    rev.bi_weighted_counts[(f, e)] = int_or_float(weighted_count)
                    rev.bi_counts[(f, e)] = int(count)
                    n_entries += 1
                elif line.startswith('::efsc '):
                    e, fs, weighted_stem_count = regex.split(' {2,}', slot_value_in_double_colon_del_list(line, 'efsc'))
                    self.aligned_stems[e].add(fs)
                    elc = slot_value_in_double_colon_del_list(line, 'elc')
                    erc = slot_value_in_double_colon_del_list(line, 'erc')
                    if elc is None and erc is None:
                        self.bi_weighted_stem_counts[(e, fs)] = int_or_float(weighted_stem_count)
                    else:
                        self.aligned_stem_contexts[(e, fs)].add((elc, erc))
                        self.bi_weighted_stem_counts_with_context[(e, fs, elc, erc)] = int_or_float(weighted_stem_count)
                elif line.startswith('::fesc'):
                    f, es, weighted_stem_count = regex.split(' {2,}', slot_value_in_double_colon_del_list(line, 'fesc'))
                    rev.aligned_stems[f].add(es)
                    flc = slot_value_in_double_colon_del_list(line, 'flc')
                    frc = slot_value_in_double_colon_del_list(line, 'frc')
                    if flc is None and frc is None:
                        rev.bi_weighted_stem_counts[(f, es)] = int_or_float(weighted_stem_count)
                    else:
                        rev.aligned_stem_contexts[(f, es)].add((flc, frc))
                        rev.bi_weighted_stem_counts_with_context[(f, es, flc, frc)] = int_or_float(weighted_stem_count)
                elif line.startswith('::esfs'):
                    e_stem = slot_value_in_double_colon_del_list(line, 'es')
                    f_stem = slot_value_in_double_colon_del_list(line, 'fs')
                    efwc = float(slot_value_in_double_colon_del_list(line, 'efc'))  # ef eighted count
                    fewc = float(slot_value_in_double_colon_del_list(line, 'fec'))
                    ec = int(slot_value_in_double_colon_del_list(line, 'ec'))
                    fc = int(slot_value_in_double_colon_del_list(line, 'fc'))
                    self.aligned_bi_stems[e_stem].add(f_stem)
                    self.bi_weighted_bi_stem_counts[(e_stem, f_stem)] = WeightedAlignmentCounts(efwc, fewc, ec, fc)
                    rev.aligned_bi_stems[f_stem].add(e_stem)
                    rev.bi_weighted_bi_stem_counts[(f_stem, e_stem)] = WeightedAlignmentCounts(fewc, efwc, fc, ec)
                elif line.startswith('::fses'):
                    pass  # info redundant with ::esfs
                elif line.startswith('::es'):
                    es = slot_value_in_double_colon_del_list(line, 'es')
                    count = slot_value_in_double_colon_del_list(line, 'count')
                    elc = slot_value_in_double_colon_del_list(line, 'elc')
                    erc = slot_value_in_double_colon_del_list(line, 'erc')
                    if elc is None and erc is None:
                        self.stem_counts[es] = int_or_float(count)
                    else:
                        self.aligned_stem_contexts[es].add((elc, erc))
                        self.stem_counts_with_context[(es, elc, erc)] = int_or_float(count)
                elif line.startswith('::fs'):
                    fs = slot_value_in_double_colon_del_list(line, 'fs')
                    count = slot_value_in_double_colon_del_list(line, 'count')
                    flc = slot_value_in_double_colon_del_list(line, 'flc')
                    frc = slot_value_in_double_colon_del_list(line, 'frc')
                    if flc is None and frc is None:
                        rev.stem_counts[fs] = int_or_float(count)
                    else:
                        rev.aligned_stem_contexts[fs].add((flc, frc))
                        rev.stem_counts_with_context[(fs, flc, frc)] = int_or_float(count)
        self.avg_total_count = (self.total_count + rev.total_count) / 2
        rev.avg_total_count = self.avg_total_count
        if stderr:
            stderr.write(f'load_alignment_model1: {n_entries} entries in {line_number} lines. '
                         f'total_e: {self.total_count} total_f: {rev.total_count} total: {self.avg_total_count}\n')

    @staticmethod
    def stem_exception_list_to_regex(exception_list, stem, affix_side) -> str:
        affix_list = []
        for exception_elem in exception_list:
            affix = exception_elem[:-len(stem)] if affix_side == 'left' else exception_elem[len(stem):]
            affix = regex.sub(r'\\ ', ' ', regex.escape(affix))
            if affix.startswith(' '):
                affix = '\\b' + affix.lstrip(' ')
            if affix.endswith(' '):
                affix = affix.rstrip(' ') + '\\b'
            affix_list.append(affix)
        if affix_side == 'left':
            return f'(?<!{"|".join(sorted(affix_list))})'
        else:
            return f'(?!{"|".join(sorted(affix_list))})'

    def build_weights_with_context(self, rev):
        for side in ['e', 'f']:
            a_am = self if side == 'e' else rev
            b_am = self if side == 'f' else rev
            for a in a_am.counts.keys():
                for b in a_am.aligned_stems[a]:
                    exception_regex_left, exception_regex_right = '', ''
                    if stem_exceptions_left := a_am.stem_exceptions_left[(a, b)]:
                        exception_regex_left = a_am.stem_exception_list_to_regex(stem_exceptions_left, b, 'left')
                    if stem_exceptions_right := a_am.stem_exceptions_right[(a, b)]:
                        exception_regex_right = a_am.stem_exception_list_to_regex(stem_exceptions_right, b, 'right')
                    if (exception_regex_left != '') or (exception_regex_right != ''):
                        b_am.stem_exception_contexts[b].add((exception_regex_left, exception_regex_right))
                        compute_stem_counts_with_context \
                            = not b_am.stem_counts_with_context[(b, exception_regex_left, exception_regex_right)]
                        full_regex_s = exception_regex_left + b + exception_regex_right
                        full_regex = regex.compile(full_regex_s)
                        a_b_count, b_count = 0, 0
                        for b_surf in b_am.stem_to_surf[b]:
                            if full_regex.search(b_surf):
                                a_b_count += a_am.bi_weighted_counts[(a, b_surf)]
                                if compute_stem_counts_with_context:
                                    b_count += b_am.counts[b_surf]
                        if compute_stem_counts_with_context:
                            b_am.stem_counts_with_context[(b, exception_regex_left, exception_regex_right)] = b_count
                        a_am.sub_bi_weighted_counts_with_context[(a, b, exception_regex_left, exception_regex_right)] \
                            = a_b_count

    def write_alignment_model(self, rev, filename: str, _stderr: Optional[TextIO]):
        with open(filename, 'w') as out:
            out.write(f'# Alignment model (by script viz-simple-alignment.py)\n')
            for side in ['e', 'f']:
                a_am = self if side == 'e' else rev
                other_side = 'f' if side == 'e' else 'e'
                for a in sorted(a_am.counts.keys(), key=str.casefold):
                    count = a_am.counts[a]
                    fertility_list = a_am.fertilities[a]
                    gloss = a_am.glosses[a]
                    discontinuity = a_am.discontinuities.get(a, 0)
                    romanization = a_am.romanization.get(a)
                    function_word_score = a_am.function_word_scores[a]
                    out.write(f"\n::{side} {a} ::count {count} ::fert {'/'.join(map(str, fertility_list))}")
                    if discontinuity is not None:
                        out.write(f" ::disc {discontinuity}")
                    if gloss:
                        out.write(f" ::gloss {gloss}")
                    if romanization:
                        out.write(f" ::rom {romanization}")
                    if function_word_score:
                        out.write(f" ::fw {function_word_score}")
                    out.write('\n')
                    aligned_stems = sorted(list(a_am.aligned_stems[a]),
                                           key=lambda k: (round(-1 * a_am.bi_weighted_stem_counts[(a, k)], 3),
                                                          k.casefold()))
                    for b in aligned_stems:
                        exception_regex_left, exception_regex_right, lc_clause, rc_clause = '', '', '', ''
                        out.write(f"::{side}{other_side}sc {a}  {b}  "
                                  f"{round(a_am.bi_weighted_stem_counts[(a, b)], 3)}\n")
                        if stem_exceptions_left := a_am.stem_exceptions_left[(a, b)]:
                            exception_regex_left = a_am.stem_exception_list_to_regex(stem_exceptions_left, b, 'left')
                            lc_clause = f" ::{other_side}lc {exception_regex_left}"
                        if stem_exceptions_right := a_am.stem_exceptions_right[(a, b)]:
                            exception_regex_right = a_am.stem_exception_list_to_regex(stem_exceptions_right, b, 'right')
                            rc_clause = f" ::{other_side}rc {exception_regex_right}"
                        sub_bi_weighted_counts_with_context \
                            = a_am.sub_bi_weighted_counts_with_context[(a, b, exception_regex_left,
                                                                        exception_regex_right)]
                        if (exception_regex_left != '') or (exception_regex_right != ''):
                            a_am.aligned_stem_contexts[(a, b)].add((exception_regex_left, exception_regex_right))
                            a_am.bi_weighted_stem_counts_with_context[(a, b, exception_regex_left,
                                                                       exception_regex_right)] \
                                = sub_bi_weighted_counts_with_context
                            out.write(f"::{side}{other_side}sc {a}  {b}  "
                                      f"{round(sub_bi_weighted_counts_with_context, 3)}"
                                      f"{lc_clause}{rc_clause}\n")
                    aligned_words = sorted(list(a_am.aligned_words[a]),
                                           key=lambda k: (round(-1 * a_am.bi_weighted_counts[(a, k)], 3),
                                                          k.casefold()))
                    for b in aligned_words:
                        out.write(f"::{side}{other_side}c {a}  {b}  "
                                  f"{round(a_am.bi_weighted_counts[(a, b)], 3)}  {a_am.bi_counts[(a, b)]}\n")
                out.write('\n')
                for a_stem in sorted(a_am.aligned_bi_stems.keys(), key=str.casefold):
                    for b_stem in sorted(a_am.aligned_bi_stems[a_stem]):
                        abwc, bawc, ac, bc = a_am.bi_weighted_bi_stem_counts[(a_stem, b_stem)].unpack()
                        out.write(f"::{side}s{other_side}s ::{side}s {a_stem} ::{other_side}s {b_stem} "
                                  f"::{side}{other_side}c {round(abwc, 3)} ::{side}c {ac} "
                                  f"::{other_side}{side}c {round(bawc, 3)} ::{other_side}c {bc}\n")
                out.write('\n')
                for a in sorted(a_am.stem_counts.keys(), key=str.casefold):
                    count = a_am.stem_counts[a]
                    out.write(f"::{side}s {a} ::count {count}\n")
                    for exception_regex_left, exception_regex_right in a_am.stem_exception_contexts[a]:
                        count = a_am.stem_counts_with_context[(a, exception_regex_left, exception_regex_right)]
                        a_am.aligned_stem_contexts[a].add((exception_regex_left, exception_regex_right))
                        out.write(f"::{side}s {a} ::{side}lc {exception_regex_left} ::{side}rc {exception_regex_right} "
                                  f"::count {count}\n")
                out.write(f'\n::{side}-total-count {a_am.total_count}\n')
                # write distortions
                a1, b1, a_rp1, b_rp1 = '', '', 0, 0
                for record in sorted(a_am.alignment_context.keys()):
                    a, b, a_rp, b_rp = record
                    count = a_am.alignment_context[record]
                    if count >= 10:
                        if (a != a1) or (b != b1) or (a_rp != a_rp1):
                            out.write(f'\n::{side}{other_side}-distortion ::{side} {a} ::{other_side} {b} '
                                      f'::{side}-rp {a_rp} ::{other_side}-rp')
                        out.write(f' {b_rp}:{count}')
                        a1, b1, a_rp1, b_rp1 = a, b, a_rp, b_rp
                out.write('\n')

    def process_alignments(self, rev, text_filename: Path, in_align_filename: str, out_align_filename: Optional[str],
                           html_filename_dir: Path, max_number_output_snt: Optional[int],
                           e_lang_name: str, f_lang_name: str, f_log: TextIO, skip_modules: list[str],
                           vm: VerboseManager, prop_filename: Optional[Path], sed: Optional[SmartEditDistance],
                           spc) -> None:  # spc: SpellChecker
        viz_file_manager = VisualizationFileManager(e_lang_name, f_lang_name, html_filename_dir, text_filename,
                                                    prop_filename)
        line_number = 0
        n_outputs = 0
        if out_align_filename:
            f_out_align = open(out_align_filename, 'w')
        else:
            f_out_align = None
        with open(text_filename) as f_text, open(in_align_filename) as f_in_align:
            sys.stderr.write('Building alignment visualizations for\n')
            for text, align in zip(f_text, f_in_align):
                if max_number_output_snt is not None and n_outputs >= max_number_output_snt:
                    break
                line_number += 1
                made_change = False
                text, align = text.strip(), align.strip()
                e, f, ref = regex.split(r'\s*\|{3}\s*', text)
                viz_file_manager.new_ref(ref)
                if not viz_file_manager.current_chapter_id:
                    continue
                snt_id = ref or line_number
                orig_sa = SentenceAlignment(e, f, align, self, rev, snt_id, sed)
                orig_sa.derive_values(snt_id, initial=True)
                orig_sa.record_alignment_context(self, rev, snt_id)
                orig_sa_score = orig_sa.score()
                # if ref == "GEN 14:17":
                #     orig_sa.visualize_alignment(snt_id, 'O1.'+ref, orig_sa_score, viz_file_manager.f_html)
                # TODO: more heuristics
                sa = None
                phase = 0
                if 'delete_weak_remotes' not in skip_modules:
                    if sa is None:
                        sa = orig_sa.copy()
                    phase += 1
                    made_change = sa.delete_weak_remotes(f_log, vm, phase=phase) or made_change
                if 'delete_punct_non_fw_links' not in skip_modules:
                    if sa is None:
                        sa = orig_sa.copy()
                    phase += 1
                    made_change = sa.delete_punct_non_fw_links(f_log, vm, snt_id) or made_change
                if 'markup_spurious' not in skip_modules:
                    if sa is None:
                        sa = orig_sa.copy()
                    phase += 1
                    made_change = sa.markup_spurious(f_log, vm) or made_change
                if 'markup_strong_unambiguous_links' not in skip_modules:
                    if sa is None:
                        sa = orig_sa.copy()
                    phase += 1
                    made_change = sa.markup_strong_unambiguous_links(f_log, vm, snt_id) or made_change
                if 'align_n_on_n_links' not in skip_modules:
                    if sa is None:
                        sa = orig_sa.copy()
                    phase += 1
                    made_change = sa.align_n_on_n_links(f_log, vm, snt_id) or made_change
                    # made_change = sa.old_align_n_on_n_links(f_log, vm, snt_id) or made_change
                if 'link_phonetic_matches' not in skip_modules:
                    if sa is None:
                        sa = orig_sa.copy()
                    made_change = sa.link_phonetic_matches(f_log, vm, snt_id, phase=phase) or made_change
                if 'link_similar_subs' not in skip_modules:
                    if sa is None:
                        sa = orig_sa.copy()
                    made_change = sa.link_similar_subs(f_log, vm, snt_id, orig_sa=orig_sa) or made_change
                if made_change and ('delete_weak_remotes' not in skip_modules):
                    phase += 1
                    sa.derive_values(snt_id)
                    made_change = sa.delete_weak_remotes(f_log, vm, phase=phase) or made_change
                if made_change:
                    sa.derive_values(snt_id)
                else:
                    sa, orig_sa = orig_sa, None
                spc.add_alignment_to_index(sa)
                sa_score = sa.score(eval_stats=viz_file_manager.eval_stats)
                sa.visualize_alignment(snt_id, ref or line_number, sa_score, viz_file_manager.f_html,
                                       orig_sa=orig_sa, orig_sa_score=orig_sa_score, sed=sed, spc=spc,
                                       vfm=viz_file_manager)
                n_outputs += 1
                if f_out_align:
                    sa.output_alignment(f_out_align)
            viz_file_manager.finish_visualization_file(True)
        if f_out_align:
            f_out_align.close()
        viz_file_manager.print_visualization_eval_stats()
        sys.stderr.write(f"\nBuilding eval-stats page: {html_filename_dir / 'eval.html'}\n")

    def build_counts(self, rev, text_filename: str, align_filename: str):
        """includes buidling fertilities and discontinuities"""
        line_number = 0
        lower_case_tokens_p = True
        with open(text_filename) as f_text, open(align_filename) as f_align:
            for text, align in zip(f_text, f_align):
                line_number += 1
                text, align = text.strip(), align.strip()
                if m3 := regex.match(r'(\S|\S.*?\S)\s+\|\|\|\s+(\S|\S.*?\S)\s+\|\|\|\s+(\S|\S.*?\S)\s*$', text):
                    e, f, ref = m3.group(1, 2, 3)
                    self.verses[ref] = e
                    rev.verses[ref] = f
                elif m2 := regex.match(r'(\S|\S.*?\S)\s+\|\|\|\s+(\S|\S.*?\S)\s*$', text):
                    e, f = m2.group(1, 2)
                    ref = None
                else:
                    continue
                sa = SentenceAlignment(e, f, align, self, rev, ref)
                for side in ('e', 'f'):
                    a_am = sa.a_am(side)
                    b_am = sa.b_am(side)
                    a_tokens = sa.lc_a_tokens(side) if lower_case_tokens_p else sa.a_tokens(side)
                    for a_token in a_tokens:
                        a_am.counts[a_token] += 1
                        a_am.total_count += 1
                    for a_token in sa.a_tokens(side):
                        a_am.tc_counts[a_token] += 1  # true case
                        if a_token not in a_am.tc_alts[a_token.lower()]:
                            a_am.tc_alts[a_token.lower()].append(a_token)
                    for a_pos, a_token in enumerate(a_tokens):
                        fertility = sa.a_pos_fert(side)[a_pos]
                        fertility_count_list = a_am.fertilities[a_token]
                        if len(fertility_count_list) <= fertility:
                            fertility_count_list.extend([0] * (fertility + 1 - len(fertility_count_list)))
                        fertility_count_list[fertility] += 1
                        if fertility == 0:
                            a_am.aligned_words[a_token].add('NULL')
                            a_am.bi_counts[(a_token, 'NULL')] += 1
                            a_am.bi_weighted_counts[(a_token, 'NULL')] += 1
                            b_am.counts['NULL'] += 1
                            b_am.aligned_words['NULL'].add(a_token)
                            b_am.bi_counts[('NULL', a_token)] += 1
                            b_am.bi_weighted_counts[('NULL', a_token)] += 1
                        if b_pos_list := sorted(sa.a_b_pos_list(side)[a_pos]):
                            prev_b_pos = b_pos_list[0] - 1
                            for b_pos in b_pos_list:
                                if prev_b_pos + 1 != b_pos:
                                    a_am.discontinuities[a_token] += 1
                                prev_b_pos = b_pos
                for e_pos_s, f_pos_s in sa.alignment_pairs:
                    try:
                        e_pos, f_pos = int(e_pos_s), int(f_pos_s)
                    except ValueError:
                        continue
                    # sys.stderr.write(f'   {e_pos}/{len(e_tokens)} {f_pos}/{len(f_tokens)}\n')
                    if lower_case_tokens_p:
                        e_token, f_token = sa.lc_e_tokens[e_pos], sa.lc_f_tokens[f_pos]
                    else:
                        e_token, f_token = sa.e_tokens[e_pos], sa.f_tokens[f_pos]
                    self.bi_counts[(e_token, f_token)] += 1
                    rev.bi_counts[(f_token, e_token)] += 1
                    self.bi_weighted_counts[(e_token, f_token)] += 1 / sa.e_pos_fert[e_pos]
                    rev.bi_weighted_counts[(f_token, e_token)] += 1 / sa.f_pos_fert[f_pos]
                    self.aligned_words[e_token].add(f_token)
                    rev.aligned_words[f_token].add(e_token)
        self.avg_total_count = (self.total_count + rev.total_count) / 2
        rev.avg_total_count = self.avg_total_count

    def build_glosses(self, rev):
        self.glosses.clear()
        for a in sorted(self.counts.keys(), key=str.casefold):
            a_count = self.counts[a]
            gloss_list = []
            max_a_b_count = 0.0
            b_tokens = sorted(list(self.aligned_words[a]),
                              key=lambda k: (-1 * self.bi_weighted_counts[(a, k)], k.lower()))
            for b_rank, b in enumerate(b_tokens, 1):
                b_count = rev.counts[b]
                a_b_weighted_count = self.bi_weighted_counts[(a, b)]
                if len(gloss_list) == 0:
                    gloss_list.append(b.strip('@'))
                    max_a_b_count = a_b_weighted_count
                elif len(gloss_list) >= 5:
                    break
                elif b_rank > 10:
                    break
                elif a_b_weighted_count <= 0.5:
                    continue
                elif a_b_weighted_count <= 1.0 and a_b_weighted_count < a_count * 0.1:
                    continue
                elif a_b_weighted_count / b_count < 0.01:
                    continue
                elif a_b_weighted_count < max_a_b_count * 0.05:
                    continue
                elif b in (",", ".", "@-@"):
                    continue
                else:
                    gloss_list.append(b.strip('@'))
            self.glosses[a] = ', '.join(gloss_list)

    def single_path_super_word_a(self, affix_side: str, sub_word: str) -> str:
        super_word = sub_word
        while (super_words := self.sub_super_words_a(affix_side)[super_word]) and (len(super_words) == 1):
            super_word_cand = list(super_words)[0]
            if affix_side == 'left':
                if super_word_cand.startswith(' '):
                    break
            else:  # affix_side == 'right'
                if super_word_cand.endswith(' '):
                    break
            super_word = super_word_cand
        return super_word

    def morph_clustering(self, rev, side_a: str, side_b: str, f_out: Optional[TextIO], vm: VerboseManager):
        self.morph_clustering_side(rev, side_a, f_out, vm)
        rev.morph_clustering_side(self, side_b, f_out, vm)
        for a in self.counts.keys():
            for b_stem in self.aligned_stems[a]:
                self.bi_stem_clustering(rev, a, b_stem, side_a)
        for b in rev.counts.keys():
            for a_stem in rev.aligned_stems[b]:
                rev.bi_stem_clustering(self, b, a_stem, side_b)

    def morph_clustering_side(self, rev, slot_prefix: str, f_out: Optional[TextIO], vm: VerboseManager):
        # HERE a=könig...  b=king
        rev.aligned_stems.clear()
        rev.bi_weighted_stem_counts.clear()
        self.stem_counts.clear()
        for a in self.counts.keys():
            count = self.counts[a]
            a2 = ' ' + a + ' '
            for start_pos in range(len(a2)-2):
                for end_pos in range(max(start_pos+2, 3), len(a2) + 1):
                    sub_word = a2[start_pos:end_pos]
                    self.stem_to_surf[sub_word].add(a)
                    self.sub_counts[sub_word] += count
                    if start_pos > 0:
                        self.sub_super_words_left[sub_word].add(a2[start_pos-1:end_pos])
                    if end_pos < len(a2):
                        self.sub_super_words_right[sub_word].add(a2[start_pos:end_pos+1])
        for b in sorted(rev.counts.keys(), key=str.casefold):
            # if b not in ['king', 'kings', 'queen', 'queens', 'royal', 'kingdom', 'kingdoms']:
            #     continue
            if b == 'NULL':
                continue
            b_is_punct = bool(regex.match(r'\pP+$', b))
            b_count = rev.counts[b]
            for a in rev.aligned_words[b]:
                bi_weighted_counts = rev.bi_weighted_counts[(b, a)]
                a2 = ' ' + a + ' '
                for start_pos in range(len(a2)-2):
                    for end_pos in range(max(start_pos+2, 3), len(a2) + 1):
                        sub_word = a2[start_pos:end_pos]
                        self.sub_aligned_words[b].add(sub_word)
                        self.sub_bi_weighted_counts[(b, sub_word)] += bi_weighted_counts
            dominated_sub_words = {}
            for a in sorted(self.sub_aligned_words[b], key=lambda s: (-len(s), s)):
                if a.startswith(' ') and a.endswith(' '):
                    continue
                sub_bi_weighted_count = self.sub_bi_weighted_counts[(b, a)]
                sub_count = self.sub_counts[a]
                if sub_bi_weighted_count > 0.01 * sub_count and sub_bi_weighted_count > 0.01 * b_count:
                    for a_sub in [a[1:], a[:-1]]:
                        a_sub_bi_weighted_count = self.sub_bi_weighted_counts[(b, a_sub)]
                        a_sub_count = self.sub_counts[a_sub]
                        if (((a.startswith(' ') and not a_sub.startswith(' '))
                                or (a.endswith(' ') and not a_sub.endswith(' ')))
                                and sub_bi_weighted_count <= 1.02 * a_sub_bi_weighted_count):
                            dominated_sub_words[a] = True
                        elif a_sub_bi_weighted_count <= 1.02 * sub_bi_weighted_count:
                            dominated_sub_words[a_sub] = True
                        elif a_sub_count * sub_bi_weighted_count < sub_count * a_sub_bi_weighted_count \
                                and not dominated_sub_words.get(a):
                            dominated_sub_words[a] = True
                    if (not dominated_sub_words.get(a)) \
                            and sub_bi_weighted_count > rev.bi_weighted_counts[(b, a)] \
                            and (not (len(a) <= 3 and (sub_bi_weighted_count/sub_count) < 0.1)) \
                            and (not (len(a) <= 4 and (sub_bi_weighted_count/sub_count) < 0.03)) \
                            and (not (b_is_punct and (sub_bi_weighted_count/sub_count) < 0.1)) \
                            and (not (b_is_punct and sub_bi_weighted_count < 10))\
                            and (not sub_bi_weighted_count < 1.5):
                        if vm.log_stem_probs and f_out:
                            f_out.write(f'::{slot_prefix}-stem {b} c:{b_count} {a}'
                                        f' {round(sub_bi_weighted_count, 3)}/{sub_count}'
                                        f' = {round(sub_bi_weighted_count/sub_count, 3)}\n')
                        rev.aligned_stems[b].add(a)
                        rev.bi_weighted_stem_counts[(b, a)] = sub_bi_weighted_count
                        self.stem_counts[a] = sub_count
                        for affix_side in ('left', 'right'):
                            a_super_words = self.sub_super_words_a(affix_side)[a]
                            for a_super_word in a_super_words:
                                sub_super_count = self.sub_counts[a_super_word]
                                if sub_super_count < 2:
                                    continue
                                sub_super_bi_weighted_count = self.sub_bi_weighted_counts[(b, a_super_word)]
                                ratio = sub_super_bi_weighted_count / sub_super_count
                                if ratio < 0.03:
                                    exp_a_super_word = self.single_path_super_word_a(affix_side, a_super_word)
                                    rev.stem_exceptions_a(affix_side)[(b, a)].add(exp_a_super_word)

    def bi_stem_clustering(self, rev, a_stem: str, b_stem: str, side: str):
        # a_stem: king  b_stem: könig
        verbose = a_stem.startswith('king') or a_stem.startswith('queen') or a_stem.startswith('royal') \
                  or a_stem.startswith('könig')
        # if verbose: sys.stderr.write(f' A-{side} {a_stem} {b_stem}\n')
        a_stem_count = 0
        for a in self.stem_to_surf[a_stem]:
            a_stem_count += self.counts.get(a, 0)
        if a_stem_count < 2:
            return
        b_stem_count = 0
        for b in rev.stem_to_surf[b_stem]:
            b_stem_count += rev.counts.get(b, 0)
        if b_stem_count < 2:
            return
        # if verbose: sys.stderr.write(f'  H-{side} {a_stem} ({a_stem_count}) {b_stem} ({b_stem_count})\n')
        a_b_weighted_count = 0.0
        b_a_weighted_count = 0.0
        for a in self.stem_to_surf[a_stem]:
            for b in rev.stem_to_surf[b_stem]:
                a_b_weighted_count += self.bi_weighted_counts[(a, b)]
                b_a_weighted_count += rev.bi_weighted_counts[(b, a)]
                # if verbose and self.bi_weighted_counts[(a, b)]:
                #     sys.stderr.write(f'     F {a} {b} {self.bi_weighted_counts[(a, b)]}\n')
        if a_b_weighted_count / a_stem_count >= 0.1 and a_b_weighted_count / b_stem_count >= 0.1:
            if verbose:
                sys.stderr.write(f'  G-{side} {a_stem} {a_b_weighted_count}/{a_stem_count} '
                                 f'{b_stem} {b_a_weighted_count}/{b_stem_count}\n')
            self.aligned_bi_stems[a_stem].add(b_stem)
            self.bi_weighted_bi_stem_counts[(a_stem, b_stem)] \
                = WeightedAlignmentCounts(a_b_weighted_count, b_a_weighted_count, a_stem_count, b_stem_count)
            rev.aligned_bi_stems[b_stem].add(a_stem)
            rev.bi_weighted_bi_stem_counts[(b_stem, a_stem)] \
                = WeightedAlignmentCounts(b_a_weighted_count, a_b_weighted_count, b_stem_count, a_stem_count)

    def find_function_words(self, slot_prefix: str, f_out: Optional[TextIO], vm: VerboseManager):
        self.function_word_scores.clear()
        total_count = self.total_count
        for a in sorted(self.counts.keys(), key=str.casefold):
            count = self.counts[a]
            count_ratio = count/total_count
            if count_ratio >= 0.001:
                bi_count_weighted_sum = 0
                for b in self.aligned_words[a]:
                    if b == "NULL":
                        continue
                    bi_count = self.bi_weighted_counts[(a, b)]
                    bi_count_weighted_sum += bi_count * bi_count
                crisp_score = bi_count_weighted_sum / (count * count)
                if regex.match(r'\pP+$', a) \
                        or (crisp_score < 0.3) \
                        or ((count_ratio >= 0.003) and (crisp_score < 0.5)) \
                        or (count_ratio >= 0.01):
                    self.function_word_scores[a] = 1.0
                    if vm.log_fw_crisp and f_out:
                        f_out.write(f'::{slot_prefix}-fw {a}  c:{count}  crisp:{round(crisp_score, 3)}\n')

    def support_probability(self, rev, a_token: str, b_token: str, _snt_id: Optional[str], side: str,
                            sed: Optional[SmartEditDistance] = None, initial_o_score: bool = False,
                            min_sub_length: int = 4,
                            sa=None, a_pos: Optional[int] = None, b_pos: Optional[int] = None) -> float:
        sp = self.support_probabilities.get((rev, a_token, b_token), None)
        if sp is None:
            b_count = max(rev.counts[b_token] - 1, 0)
            joint_count = max(self.bi_counts[(a_token, b_token)] - 1, 0)
            rom_a_token = self.romanization.get(a_token, a_token)
            rom_b_token = rev.romanization.get(b_token, b_token)
            cost, cost_log = sed.string_distance_cost(rom_a_token, rom_b_token, max_cost=1)
            if cost is not None and cost < 1:
                sed_boost = 4 * (1 - cost) * (1 - cost)
                sp = (joint_count + sed_boost) / (b_count + sed_boost)
            elif b_count:
                sp = joint_count / b_count
            else:
                sp = 0.01
            if (sp < 1) and sa and a_pos is not None and b_pos is not None:
                o_score = WordAlignmentSupport.get_best_word_alignment_support_score(sa, side, a_pos, b_pos,
                                                                                     default_result=None)
                if o_score is None:
                    if initial_o_score:
                        o_score = sa.get_a_b_partial_overlap_score(side, a_pos, b_pos, min_sub_length)
                    else:
                        o_score = 0.0
                sp = sp + o_score / (1 - sp)
            self.support_probabilities[(rev, a_token, b_token)] = sp
            if False and {rom_a_token.lower(), rom_b_token.lower()} in ({'piishon', 'pishon'}, {'gihon', 'giihon'}):
                sys.stderr.write(f'\nsupport_probability {a_token} {b_token} {b_count} ::jc {joint_count} ::sp {sp} '
                                 f'::sed {cost}\n')
        return sp


class SentenceAlignment:
    """For one sentence pair. align: '0-1 1-3 2-0 3-3'"""
    def __init__(self, e: str, f: str, align: str, e_am: AlignmentModel, f_am: AlignmentModel, snt_id: Optional[str],
                 sed: Optional[SmartEditDistance] = None):
        self.snt_id = snt_id
        self.e, self.f = e, f
        self.e_tokens, self.f_tokens = e.split(), f.split()
        self.lc_e_tokens, self.lc_f_tokens = list(map(str.lower, self.e_tokens)), list(map(str.lower, self.f_tokens))
        self.e_f_pos_list, self.f_e_pos_list = defaultdict(list), defaultdict(list)
        self.e_f_candidates, self.f_e_candidates = defaultdict(list), defaultdict(list)
        self.e_pos_fert, self.f_pos_fert = defaultdict(int), defaultdict(int)
        self.e_exclusion_pos_list, self.f_exclusion_pos_list = defaultdict(bool), defaultdict(bool)
        self.alignment_pairs = regex.findall(r'(\d+)-(\d+)', align)
        self.e_am = e_am
        self.f_am = f_am
        self.best_support_probability_for_e = defaultdict(float)
        self.best_support_probability_for_f = defaultdict(float)
        self.best_support_pos_for_e = defaultdict(int)
        self.best_support_pos_for_f = defaultdict(int)
        self.best_count_for_e = defaultdict(int)
        self.best_count_for_f = defaultdict(int)
        self.e_is_contiguous = defaultdict(bool)
        self.f_is_contiguous = defaultdict(bool)
        self.sed = sed
        self.e_f_partial_overlap_score = defaultdict(float)   # key: (e_pos, f_pos)  value: score [0..1]
        self.word_alignments = []  # list of WordAlignment
        self.word_align_index = defaultdict(list)
        for alignment_pair in self.alignment_pairs:
            alignment_element1, alignment_element2 = alignment_pair[0], alignment_pair[1]
            if regex.match(r'\d+$', alignment_element1):
                if regex.match(r'\d+$', alignment_element2):
                    e_pos, f_pos = int(alignment_element1), int(alignment_element2)
                    self.e_f_pos_list[e_pos].append(f_pos)
                    self.f_e_pos_list[f_pos].append(e_pos)
                    self.e_pos_fert[e_pos] += 1
                    self.f_pos_fert[f_pos] += 1
                elif alignment_element2 == 'x':
                    self.e_exclusion_pos_list[int(alignment_element1)] = True
            elif alignment_element1 == 'x':
                if regex.match(r'\d+$', alignment_element2):
                    self.f_exclusion_pos_list[int(alignment_element2)] = True
        self.e_fw_weights, self.f_fw_weights = [], []
        self.e_fw_weight_sum, self.f_fw_weight_sum = 0.0, 0.0

    def a_tokens(self, side):
        return self.e_tokens if side == 'e' else self.f_tokens

    def b_tokens(self, side):
        return self.f_tokens if side == 'e' else self.e_tokens

    def lc_a_tokens(self, side):
        return self.lc_e_tokens if side == 'e' else self.lc_f_tokens

    def lc_b_tokens(self, side):
        return self.lc_f_tokens if side == 'e' else self.lc_e_tokens

    def a_b_pos_list(self, side):
        return self.e_f_pos_list if side == 'e' else self.f_e_pos_list

    def b_a_pos_list(self, side):
        return self.f_e_pos_list if side == 'e' else self.e_f_pos_list

    def get_overlap_score(self, lc_a_token, lc_b_token, aligned_words, side, min_sub_length) -> float:
        """lc_a_token needed for weighted_count"""
        best_score = 0.0
        a_count = self.a_am(side).counts[lc_a_token]
        for aligned_word in aligned_words:
            if aligned_word == 'NULL':
                continue
            weighted_count = self.a_am(side).bi_weighted_counts[(lc_a_token, aligned_word)]
            if (weighted_count < 1) or (weighted_count / a_count <= 0.01):
                continue
            for aligned_sub_word in sub_strings(aligned_word, min_sub_length):
                if regex.search(aligned_sub_word, lc_b_token):
                    if len(aligned_sub_word) == min_sub_length:
                        if not lc_b_token.startswith(aligned_sub_word):
                            continue
                    length_factor = (len(aligned_sub_word) - min_sub_length + 1) / len(aligned_word)
                    weight_factor = max(min(math.log(weighted_count) / 5, 1), 0)
                    score = length_factor * weight_factor
                    if score > best_score:
                        best_score = score
        return best_score

    def get_e_f_partial_overlap_score(self, e_pos, f_pos, min_sub_length):
        cached_value = self.e_f_partial_overlap_score.get((e_pos, f_pos), None)
        if cached_value is None:
            lc_e_token = self.lc_e_tokens[e_pos]
            lc_f_token = self.lc_f_tokens[f_pos]
            e_f_aligned_words = self.e_am.aligned_words[lc_e_token]
            e_f_score = self.get_overlap_score(lc_e_token, lc_f_token, e_f_aligned_words, 'e', min_sub_length)
            f_e_aligned_words = self.f_am.aligned_words[lc_f_token]
            f_e_score = self.get_overlap_score(lc_f_token, lc_e_token, f_e_aligned_words, 'f', min_sub_length)
            cached_value = max(e_f_score, f_e_score)
            self.e_f_partial_overlap_score[(e_pos, f_pos)] = cached_value
        return cached_value

    def get_a_b_partial_overlap_score(self, side, a_pos, b_pos, min_sub_length):
        if side == 'e':
            return self.get_e_f_partial_overlap_score(a_pos, b_pos, min_sub_length)
        else:
            return self.get_e_f_partial_overlap_score(b_pos, a_pos, min_sub_length)

    def set_a_b_partial_overlap_score(self, side, a_pos, b_pos, value):
        if side == 'e':
            self.e_f_partial_overlap_score[(a_pos, b_pos)] = value
        else:
            self.e_f_partial_overlap_score[(b_pos, a_pos)] = value

    def a_b_candidates(self, side):
        return self.e_f_candidates if side == 'e' else self.f_e_candidates

    def b_a_candidates(self, side):
        return self.f_e_candidates if side == 'e' else self.e_f_candidates

    def a_pos_fert(self, side):
        return self.e_pos_fert if side == 'e' else self.f_pos_fert

    def b_pos_fert(self, side):
        return self.f_pos_fert if side == 'e' else self.e_pos_fert

    def a_exclusion_pos_list(self, side):
        return self.e_exclusion_pos_list if side == 'e' else self.f_exclusion_pos_list

    def b_exclusion_pos_list(self, side):
        return self.f_exclusion_pos_list if side == 'e' else self.e_exclusion_pos_list

    def a_am(self, side):
        return self.e_am if side == 'e' else self.f_am

    def b_am(self, side):
        return self.f_am if side == 'e' else self.e_am

    def a_fw_weights(self, side):
        return self.e_fw_weights if side == 'e' else self.f_fw_weights

    def b_fw_weights(self, side):
        return self.f_fw_weights if side == 'e' else self.e_fw_weights

    def a_fw_weight_sum(self, side):
        return self.e_fw_weight_sum if side == 'e' else self.f_fw_weight_sum

    def b_fw_weight_sum(self, side):
        return self.f_fw_weight_sum if side == 'e' else self.e_fw_weight_sum

    def a_fw_weight_increase(self, side, addend):
        if side == 'e':
            self.e_fw_weight_sum += addend
        else:
            self.f_fw_weight_sum += addend

    def b_fw_weight_increase(self, side, addend):
        if side == 'e':
            self.f_fw_weight_sum += addend
        else:
            self.e_fw_weight_sum += addend

    def a_is_contiguous(self, side):
        return self.e_is_contiguous if side == 'e' else self.f_is_contiguous

    def b_is_contiguous(self, side):
        return self.f_is_contiguous if side == 'e' else self.e_is_contiguous

    def best_support_probability_for_a(self, side):
        return self.best_support_probability_for_e if side == 'e' else self.best_support_probability_for_f

    def best_support_probability_for_b(self, side):
        return self.best_support_probability_for_f if side == 'e' else self.best_support_probability_for_e

    def best_support_pos_for_a(self, side):
        return self.best_support_pos_for_e if side == 'e' else self.best_support_pos_for_f

    def best_support_pos_for_b(self, side):
        return self.best_support_pos_for_f if side == 'e' else self.best_support_pos_for_e

    def best_count_for_a(self, side):
        return self.best_count_for_e if side == 'e' else self.best_count_for_f

    def best_count_for_b(self, side):
        return self.best_count_for_f if side == 'e' else self.best_count_for_e

    def copy(self):
        sa_copy = SentenceAlignment(self.e, self.f, '', self.e_am, self.f_am, self.snt_id)
        sa_copy.e_tokens = self.e_tokens.copy()
        sa_copy.f_tokens = self.f_tokens.copy()
        sa_copy.lc_e_tokens = self.lc_e_tokens.copy()
        sa_copy.lc_f_tokens = self.lc_f_tokens.copy()
        sa_copy.alignment_pairs = self.alignment_pairs.copy()
        sa_copy.e_f_pos_list = copy.deepcopy(self.e_f_pos_list)
        sa_copy.f_e_pos_list = copy.deepcopy(self.f_e_pos_list)
        sa_copy.e_f_candidates = self.e_f_candidates.copy()
        sa_copy.f_e_candidates = self.f_e_candidates.copy()
        sa_copy.e_exclusion_pos_list = self.e_exclusion_pos_list.copy()
        sa_copy.f_exclusion_pos_list = self.f_exclusion_pos_list.copy()
        sa_copy.e_fw_weights = self.e_fw_weights.copy()
        sa_copy.f_fw_weights = self.f_fw_weights.copy()
        sa_copy.e_fw_weight_sum = self.e_fw_weight_sum
        sa_copy.f_fw_weight_sum = self.f_fw_weight_sum
        sa_copy.e_pos_fert = self.e_pos_fert.copy()
        sa_copy.f_pos_fert = self.f_pos_fert.copy()
        sa_copy.best_support_probability_for_e = self.best_support_probability_for_e.copy()
        sa_copy.best_support_probability_for_f = self.best_support_probability_for_f.copy()
        sa_copy.best_support_pos_for_e = self.best_support_pos_for_e.copy()
        sa_copy.best_support_pos_for_f = self.best_support_pos_for_f.copy()
        sa_copy.best_count_for_e = self.best_count_for_e.copy()
        sa_copy.best_count_for_f = self.best_count_for_f.copy()
        sa_copy.e_is_contiguous = self.e_is_contiguous.copy()
        sa_copy.f_is_contiguous = self.f_is_contiguous.copy()
        sa_copy.sed = self.sed
        sa_copy.e_f_partial_overlap_score = self.e_f_partial_overlap_score.copy()
        sa_copy.word_alignments = self.word_alignments.copy()
        sa_copy.word_align_index = self.word_align_index.copy()
        return sa_copy

    def output_alignment(self, f_out_align: TextIO):
        alignment_elements = []
        for e_pos in range(len(self.e_tokens)):
            for f_pos in sorted(self.e_f_pos_list[e_pos]):
                alignment_elements.append(f'{e_pos}-{f_pos}')
            if self.e_exclusion_pos_list[e_pos]:
                alignment_elements.append(f'{e_pos}-x')
        for f_pos in range(len(self.f_tokens)):
            if self.f_exclusion_pos_list[f_pos]:
                alignment_elements.append(f'x-{f_pos}')
        f_out_align.write(' '.join(alignment_elements) + '\n')

    def max_support_probability(self, a_pos: int, side: str, snt_id: Optional[str],
                                initial_o_score: bool = False, min_sub_length=4,
                                sed: Optional[SmartEditDistance] = None) -> float:
        result = 0.0
        a_am, b_am = self.a_am(side), self.b_am(side)
        lc_a_token = self.lc_a_tokens(side)[a_pos]
        for b_pos in self.a_b_pos_list(side)[a_pos]:
            lc_b_token = self.lc_b_tokens(side)[b_pos]
            support_prob = a_am.support_probability(b_am, lc_a_token, lc_b_token, snt_id, side, sed=sed,
                                                    initial_o_score=initial_o_score, min_sub_length=min_sub_length,
                                                    sa=self, a_pos=a_pos, b_pos=b_pos)
            if support_prob > result:
                result = support_prob
        return result

    def score(self, eval_stats: Optional[EvaluationStats] = None, side: Optional[str] = None,
              e_exclude_pos: Optional[list] = None, f_exclude_pos: Optional[list] = None,
              a_exclude_pos: Optional[list] = None, b_exclude_pos: Optional[list] = None):
        """x_exclude_pos list positions to be excluded in score to help identify spurious tokens"""
        if e_exclude_pos is None and side is not None:
            e_exclude_pos = a_exclude_pos if side == 'e' else b_exclude_pos
        if f_exclude_pos is None and side is not None:
            f_exclude_pos = b_exclude_pos if side == 'e' else a_exclude_pos
        verbose = (self.snt_id == 'ABC 1:1')
        if verbose:
            sys.stderr.write(f'\nScore -e:{e_exclude_pos} -f:{f_exclude_pos}\n')
        score_sum, weight_sum = 0.0, 0.0  # over both side
        for side in ('e', 'f'):
            a_exclude_pos = e_exclude_pos if side == 'e' else f_exclude_pos
            for a_pos, lc_a_token in enumerate(self.lc_a_tokens(side)):
                if self.a_exclusion_pos_list(side)[a_pos] or (a_exclude_pos and a_pos in a_exclude_pos):
                    continue
                a_fw_weight = self.a_fw_weights(side)[a_pos]  # baseline: 1.0 for content word, 0.1 for function word
                weight_sum += a_fw_weight
                b_pos_list = self.a_b_pos_list(side)[a_pos]
                b_fw_sum = 0.0
                for b_pos in b_pos_list:
                    b_fw_sum += self.b_fw_weights(side)[b_pos]
                sub_score = 0.0
                if b_fw_sum:
                    for b_pos in b_pos_list:
                        if self.b_exclusion_pos_list(side)[b_pos]:
                            continue
                        lc_b_token = self.lc_b_tokens(side)[b_pos]
                        b_fw_weight = self.b_fw_weights(side)[b_pos]
                        support_probability = self.a_am(side).support_probability(self.b_am(side), lc_a_token,
                                                                                  lc_b_token, self.snt_id, side,
                                                                                  sed=self.sed)
                        sub_score += support_probability * a_fw_weight * b_fw_weight / b_fw_sum
                else:
                    support_probability = self.a_am(side).support_probability(self.b_am(side), lc_a_token, 'NULL',
                                                                              self.snt_id, side, sed=self.sed)
                    sub_score = support_probability * a_fw_weight
                score_sum += sub_score
                if verbose:
                    sys.stderr.write(f'Score {side} {self.snt_id} {a_pos} {lc_a_token} w:{round(a_fw_weight, 3)} '
                                     f's:{round(sub_score, 3)}\n')
        # TODO: improve score: consider phonetic match component
        score = score_sum / weight_sum if weight_sum else None
        if eval_stats:
            eval_stats.add_score(score_sum, weight_sum, self.snt_id)
        if verbose:
            sys.stderr.write(f'Return score {score}\n\n')
        return score

    def derive_values(self, snt_id: Optional[str], initial: bool = False):
        # verbose = snt_id in ('GEN 4:2', 'MAT 1:4')
        self.e_fw_weights, self.f_fw_weights = [], []
        self.e_fw_weight_sum, self.f_fw_weight_sum = 0.0, 0.0
        for side in ('e', 'f'):
            a_am, b_am = self.a_am(side), self.b_am(side)
            for a_pos, lc_a_token in enumerate(self.lc_a_tokens(side)):
                best_support_probability = None
                best_count = None
                best_support_pos = None
                alignments_are_contiguous = True
                b_pos_list = sorted(self.a_b_pos_list(side)[a_pos])
                if b_pos_list:
                    prev_b_pos = b_pos_list[0] - 1
                    for b_pos in b_pos_list:
                        if prev_b_pos + 1 != b_pos:
                            alignments_are_contiguous = False
                        lc_b_token = self.lc_b_tokens(side)[b_pos]
                        support_probability = a_am.support_probability(b_am, lc_a_token, lc_b_token, snt_id, side,
                                                                       sed=self.sed)
                        if best_support_probability is None or support_probability > best_support_probability:
                            best_support_probability = support_probability
                            best_count = a_am.bi_counts[(lc_a_token, lc_b_token)]
                            best_support_pos = b_pos
                        prev_b_pos = b_pos
                if side == 'e':
                    self.best_support_probability_for_e[a_pos] = best_support_probability
                    self.best_support_pos_for_e[a_pos] = best_support_pos
                    self.best_count_for_e[a_pos] = best_count
                    self.e_is_contiguous[a_pos] = alignments_are_contiguous
                else:  # side == 'f'
                    self.best_support_probability_for_f[a_pos] = best_support_probability
                    self.best_support_pos_for_f[a_pos] = best_support_pos
                    self.best_count_for_f[a_pos] = best_count
                    self.f_is_contiguous[a_pos] = alignments_are_contiguous
                a_fw_score = a_am.function_word_scores[lc_a_token]
                a_fw_weight = (1 - a_fw_score * 0.9)
                self.a_fw_weights(side).append(a_fw_weight)
                self.a_fw_weight_increase(side, a_fw_weight)
        self.build_alignment_candidates(self.e_am, self.f_am, snt_id, initial=initial)

    def record_alignment_context(self, e_am: AlignmentModel, _f_am: AlignmentModel, _snt_id: Optional[str]):
        for e_pos, lc_e_token in enumerate(self.lc_e_tokens):
            if lc_e_token not in ('and', 'from', 'of', 'gave', 'said', 'young', 'mighty'):
                continue
            f_pos_list = self.e_f_pos_list[e_pos]
            if len(f_pos_list) != 1:
                continue
            f_pos = f_pos_list[0]
            lc_f_token = self.lc_f_tokens[f_pos]
            if e_pos > 0:
                e_pos_left1 = e_pos-1
                f_pos_left1_list = self.e_f_pos_list[e_pos_left1]
                if len(f_pos_left1_list) == 1:
                    f_pos_left1 = f_pos_left1_list[0]
                    rel_pos = f_pos_left1 - f_pos
                    e_am.alignment_context[(lc_e_token, lc_f_token, -1, rel_pos)] += 1
            if e_pos < len(self.lc_e_tokens) - 1:
                e_pos_right1 = e_pos+1
                f_pos_right1_list = self.e_f_pos_list[e_pos_right1]
                if len(f_pos_right1_list) == 1:
                    f_pos_right1 = f_pos_right1_list[0]
                    rel_pos = f_pos_right1 - f_pos
                    e_am.alignment_context[(lc_e_token, lc_f_token, 1, rel_pos)] += 1

    def title(self, side: str, pos: int, snt_id: Optional[str], orig_sa=None,
              cost: Optional[float] = None, best_b_pos: Optional[int] = None) -> Optional[str]:
        lc_token = self.lc_a_tokens(side)[pos]
        b_pos_list = self.a_b_pos_list(side)[pos]
        orig_b_pos_list = orig_sa.a_b_pos_list(side)[pos] if orig_sa else []
        lc_b_tokens = self.lc_b_tokens(side)
        a_am, b_am = self.a_am(side), self.b_am(side)
        exclusion_pos_list = self.a_exclusion_pos_list(side)
        b_candidates = self.a_b_candidates(side)[pos]
        ### HHHERE escape guard
        title = guard_html(lc_token.strip('@'))
        title += f' [{pos}]'
        if (romanization := a_am.romanization.get(lc_token)) and (romanization != lc_token):
            title += f' &nbsp; rom:{guard_html(romanization)}'
        if count := a_am.counts[lc_token]:
            title += f' &nbsp; c:{count - 1}'
        if gloss := a_am.glosses[lc_token]:
            title += f' &nbsp; gloss: {guard_html(gloss)}'
        if function_word_score := a_am.function_word_scores[lc_token]:
            title += f' &nbsp; fw: {function_word_score}'
        if not b_pos_list:
            if exclusion_pos_list[pos]:
                title += '&#xA;Spurious &nbsp;'
            else:
                title += '&#xA;Unaligned &nbsp;'
        for phase in ('new', 'old'):
            phase_b_pos_list = b_pos_list if phase == 'new' else orig_b_pos_list
            for b_pos in phase_b_pos_list:
                if phase == 'new':
                    if orig_sa:
                        comp_note = 'duplicate' if b_pos in orig_b_pos_list else 'added'
                    else:
                        comp_note = 'no-reference'
                else:
                    comp_note = 'duplicate-skip' if b_pos in b_pos_list else 'deleted'
                if comp_note != 'duplicate-skip':
                    lc_b_token = lc_b_tokens[b_pos]
                    b_count = b_am.counts[lc_b_token] - 1
                    a_b_support_probability = a_am.support_probability(b_am, lc_token, lc_b_token, snt_id, side,
                                                                       sed=self.sed)
                    b_a_support_probability = b_am.support_probability(a_am, lc_b_token, lc_token, snt_id, side,
                                                                       sed=self.sed)
                    joint_count = max(a_am.bi_counts[(lc_token, lc_b_token)] - 1, 0)
                    title += "&#xA;"
                    title += "Deleted: &nbsp;" if comp_note == 'deleted' else "&mdash;"
                    title += f" {guard_html(lc_b_token.strip('@'))} [{b_pos}]" \
                             f' &nbsp; c:{b_count}' \
                             f' &nbsp; p:{round(b_a_support_probability, 3)}/{round(a_b_support_probability, 3)}' \
                             f' &nbsp; jc:{joint_count}'
                    if b_pos == best_b_pos and cost is not None and cost < 2:
                        title += f' &nbsp; sed: {cost}'
                    if comp_note == 'added':
                        title += ' &nbsp; (added)'
        prev_printed = defaultdict(bool)
        for wa_support in WordAlignmentSupport.get_word_alignment_supports_with_side(self, side, pos, None):
            if isinstance(wa_support, WordAlignmentSupportPartialMatch):
                title += f'&#xA;Partial match: &quot;{guard_html(wa_support.sub)}&quot; related to ' \
                         f'{guard_html(wa_support.e_aligned)} = {guard_html(wa_support.f_aligned)} &nbsp; ' \
                         f'jc:{wa_support.weight} s:{round(wa_support.score, 3)}'
                # unused: self.e, self.f
            elif isinstance(wa_support, WordAlignmentSupportPhonetic):
                e_suffix = wa_support.e[len(wa_support.e_sub):]
                f_suffix = wa_support.f[len(wa_support.f_sub):]
                e_suffix_clause = f'(\u2011{e_suffix})' if e_suffix else ''   # \u2011 is non-breaking hyphen
                f_suffix_clause = f'(\u2011{f_suffix})' if f_suffix else ''
                partial_match = f'{wa_support.e_sub}{e_suffix_clause} = {wa_support.f_sub}{f_suffix_clause}'
                if not prev_printed[partial_match]:
                    prev_printed[partial_match] = True
                    title += f'&#xA;Phonetic match: {guard_html(partial_match)} ' \
                             f'&nbsp; cost:{round(wa_support.cost, 2)} s:{round(wa_support.score, 3)}'
        if b_candidates:
            best_candidate_score = b_candidates[0][1]  # of top candidate, select score (at tuple position 1)
            for b_tuple in b_candidates:
                b_pos = b_tuple[0]
                candidate_score = b_tuple[1]
                if candidate_score < best_candidate_score * 0.5:
                    break
                if b_pos in b_pos_list:
                    continue
                lc_b_token = lc_b_tokens[b_pos]
                b_count = b_am.counts[lc_b_token] - 1
                a_b_support_probability = a_am.support_probability(b_am, lc_token, lc_b_token, snt_id, side,
                                                                   sed=self.sed)
                if a_b_support_probability < 0.01:
                    continue
                b_a_support_probability = b_am.support_probability(a_am, lc_b_token, lc_token, snt_id, side,
                                                                   sed=self.sed)
                if b_a_support_probability < 0.01:
                    continue
                if a_b_support_probability <= 0.05 and b_a_support_probability <= 0.05:
                    continue
                joint_count = a_am.bi_counts[(lc_token, lc_b_token)] - 1
                if joint_count < 4:
                    continue
                title += "&#xA;Candidate: &nbsp;"
                title += f" {guard_html(lc_b_token.strip('@'))} [{b_pos}]" \
                         f' &nbsp; c:{b_count}' \
                         f' &nbsp; p:{round(b_a_support_probability, 3)}/{round(a_b_support_probability, 3)}' \
                         f' &nbsp; jc:{joint_count}' \
                         f' &nbsp; s:{round(candidate_score, 3)}'
        title = title.replace(' ', '&nbsp;').replace('&#xA;', ' ')
        return title

    def decoration(self, side: str, pos: int, _snt_id: Optional[str], mouseover_action_s,
                   cost: Optional[float] = None):
        text_decoration = None
        alignment_changed = "'1+'" in mouseover_action_s or "'1-'" in mouseover_action_s
        best_support = self.best_support_probability_for_a(side)[pos]
        best_count = self.best_count_for_a(side)[pos]
        alignments_are_contiguous = self.a_is_contiguous(side)[pos]
        am = self.a_am(side)
        lc_tokens = self.lc_a_tokens(side)
        exclusion_pos_list = self.a_exclusion_pos_list(side)
        best_phonetic_score, best_partial_match_score = 0, 0
        for b_pos in self.a_b_pos_list(side)[pos]:
            for wa_support in WordAlignmentSupport.get_word_alignment_supports_with_side(self, side, pos, b_pos):
                if isinstance(wa_support, WordAlignmentSupportPartialMatch):
                    if wa_support.score > best_partial_match_score:
                        best_partial_match_score = wa_support.score
                elif isinstance(wa_support, WordAlignmentSupportPhonetic):
                    if wa_support.score > best_phonetic_score:
                        best_phonetic_score = wa_support.score
        if exclusion_pos_list[pos]:
            color = "orange"
        elif best_support is None:  # unaligned
            lc_token = lc_tokens[pos]
            a_count = am.counts[lc_token]
            a_b_count = am.bi_counts[(lc_token, "NULL")]
            ratio = a_b_count / a_count
            if ratio >= 0.25 and a_b_count >= 100:
                color = "#00AA00"
            elif ratio >= 0.2 and a_b_count >= 50:
                color = "#33AA33"
            elif ratio >= 0.15 and a_b_count >= 20:
                color = "#66AA66"
            elif ratio >= 0.1 and a_b_count >= 10:
                color = "#996666"
            elif ratio >= 0.05 and a_b_count >= 5:
                color = "#996666"
            else:
                color = "#ff0000"
            text_decoration = "underline"
        else:  # aligned
            if best_support >= 0.2 and best_count >= 24:
                color = "#00AA00"
            elif best_support >= 0.06 and best_count >= 16:
                color = "#33AA33"
            elif cost is not None and cost < 0.4:
                color = "#0000FF"
            elif best_phonetic_score > 0.19:
                color = "#3333AA"
            elif cost is not None and cost < 0.8:
                color = "#3333AA"
            elif best_support >= 0.02 and best_count >= 8:
                color = "#66AA66"
            elif best_support >= 0.01 and best_count >= 2:
                color = "#996666"
            elif best_support >= 0.005:
                color = "#dd2222"
            else:
                color = "#ff0000"
            if not alignments_are_contiguous:
                text_decoration = "underline dashed"
        if alignment_changed:
            text_decoration = f"underline double"
        return color, text_decoration

    @staticmethod
    def markup_confidence_class(score_full: float, score_core: float, score_spurious: float, surf: str):
        if score_core > score_full and score_spurious < 0.08:
            if score_core > score_full * 1.05 and score_spurious < 0.04 and regex.search(r'\d @:@ \d', surf):
                conf_class = '++'
            else:
                conf_class = '+?'
        elif score_spurious >= 0.3:
            conf_class = '--'
        elif score_core <= score_full * 1.1 and score_spurious >= 0.25:
            conf_class = '-?'
        elif score_spurious >= score_full * 0.8:
            conf_class = '-?'
        else:
            conf_class = '??'
        return conf_class + ' spurious' + (' changed' if conf_class.startswith('+') else '')

    @staticmethod
    def delimiter_open_close_match(open_delimiter: str, close_deliter: str) -> bool:
        return (open_delimiter == '(' and close_deliter == ')') \
            or (open_delimiter == '[' and close_deliter == ']')

    def markup_spurious(self, f_log: TextIO, vm: VerboseManager):
        score_full = None
        made_change = False
        for side in ('e', 'f'):
            uc_side = side.upper()
            open_delimiter_stack = []
            for a_pos, a_token in enumerate(self.a_tokens(side)):
                if a_token in '([':
                    open_delimiter_stack.append((a_token, a_pos))
                elif open_delimiter_stack and self.delimiter_open_close_match(open_delimiter_stack[-1][0], a_token):
                    start_pos, end_pos = open_delimiter_stack[-1][1], a_pos
                    del open_delimiter_stack[-1]
                    if not self.span_has_strong_link_to_other_side(side, start_pos, end_pos):
                        surf = ' '.join(self.a_tokens(side)[start_pos:end_pos+1])
                        if score_full is None:
                            score_full = self.score()
                        score_core = self.score(side=side, a_exclude_pos=list(range(start_pos, end_pos+1)))
                        score_spurious = self.score(side=side, b_exclude_pos=list(range(len(self.b_tokens(side)))),
                                                    a_exclude_pos=list(range(0, start_pos))
                                                    + list(range(end_pos+1, len(self.a_tokens(side)))))
                        conf_class = self.markup_confidence_class(score_full, score_core, score_spurious, surf)
                        if vm.log_alignment_diff_details is not None:
                            vm.log_alignment_diff_details[(uc_side, self.snt_id)].append(conf_class)
                            f_log.write(f'::diff spurious ::snt-id {self.snt_id} '
                                        f'::side {uc_side} ::range {start_pos}-{end_pos} ::surf {surf} '
                                        f'::f {round(score_full, 3)} ::c {round(score_core, 3)} '
                                        f'::s {round(score_spurious, 3)} '
                                        f'::class {conf_class}\n')
                        if conf_class.startswith('+'):
                            for a_pos2 in range(start_pos, end_pos+1):
                                self.a_exclusion_pos_list(side)[a_pos2] = True
                                for b_pos2 in self.a_b_pos_list(side)[a_pos2]:
                                    self.b_a_pos_list(side)[b_pos2].remove(a_pos2)
                                    self.a_b_pos_list(side)[a_pos2] = []
                            made_change = True
        return made_change

    def delete_weak_remotes(self, f_log: TextIO, vm: VerboseManager, phase: Optional[int] = None):
        made_change = False
        # if self.snt_id == 'MAT 1:1': sys.stderr.write(f'\ndelete_weak_remotes {phase}\n')
        for side in ('e', 'f'):
            for a_pos, lc_a_token in enumerate(self.lc_a_tokens(side)):
                if not self.a_is_contiguous(side)[a_pos]:
                    # if self.snt_id == 'MAT 1:1': sys.stderr.write(f' test3 {side} {a_pos}\n')
                    if not (b_candidates := self.a_b_candidates(side)[a_pos]):
                        continue
                    b_candidate_pos_list = [b_candidate[0] for b_candidate in b_candidates]
                    b_top_candidate = b_candidates[0]
                    b_top_pos, b_top_score = b_top_candidate[0], b_top_candidate[1]
                    # if self.snt_id == 'MAT 1:1': sys.stderr.write(f' test4 {side} {a_pos} {b_candidate_pos_list}\n')
                    if b_top_pos in self.a_b_pos_list(side)[a_pos]:
                        for b_pos in self.a_b_pos_list(side)[a_pos]:
                            # if self.snt_id == 'MAT 1:1': sys.stderr.write(f' test5 {side} {a_pos} {b_pos}\n')
                            if (abs(b_pos - b_top_pos) > 2) \
                                    and ((b_pos not in b_candidate_pos_list)
                                         or (b_candidates[b_candidate_pos_list.index(b_pos)][1] < b_top_score * 0.2)):
                                # if self.snt_id == 'MAT 1:1': sys.stderr.write(f' weak {side} {a_pos} {b_pos}\n')
                                if vm.log_alignment_diff_details is not None:
                                    a_descr = f'{lc_a_token} [{a_pos}]'
                                    b_descr = f'{self.lc_b_tokens(side)[b_pos]} [{b_pos}]'
                                    f_log.write(f'::rm weak ::snt-id {self.snt_id} ::phase {phase} '
                                                f'::e {a_descr if side == "e" else b_descr} '
                                                f'::f {b_descr if side == "e" else a_descr}\n')
                                self.a_b_pos_list(side)[a_pos].remove(b_pos)
                                self.b_a_pos_list(side)[b_pos].remove(a_pos)
                                made_change = True
        return made_change

    def build_alignment_candidates(self, e_am, f_am, snt_id, initial: bool = False, min_sub_length: int = 4):
        # TODO: consider SED: sed = self.sed
        self.e_f_candidates, self.f_e_candidates = defaultdict(list), defaultdict(list)
        for e_pos, lc_e_token in enumerate(self.lc_e_tokens):
            e_count = e_am.counts[lc_e_token]
            for f_pos, lc_f_token in enumerate(self.lc_f_tokens):
                f_count = f_am.counts[lc_f_token]
                score, e_f_prob, f_e_prob = 0.0, 0.0, 0.0
                o_score = WordAlignmentSupport.get_best_word_alignment_support_score(self, 'e', e_pos, f_pos)
                if initial and (e_count < 100) and (f_count < 100):
                    rom_e = self.e_am.romanization.get(lc_e_token, lc_e_token)
                    rom_f = self.f_am.romanization.get(lc_f_token, lc_f_token)
                    cost, log, l1, l2 = self.sed.string_distance_cost(rom_e, rom_f, max_cost=0.99,
                                                                      partial=True, min_len=min_sub_length)
                    if cost is not None:
                        min_sub_length1 = min(min_sub_length, len(rom_e))
                        min_sub_length2 = min(min_sub_length, len(rom_f))
                        length_factor1 = (l1 - min_sub_length1 + 1) / (len(rom_e) - min_sub_length1 + 1)
                        length_factor2 = (l2 - min_sub_length2 + 1) / (len(rom_f) - min_sub_length2 + 1)
                        cost_factor = max(1 - cost, 0)
                        u_score = length_factor1 * length_factor2 * cost_factor
                        if snt_id == 'MAT 1:333':
                            sys.stderr.write(f'PHON {rom_e} {rom_f} {round(cost, 3)} {l1} {l2} '
                                             f'{round(length_factor1, 3)}*{round(length_factor2, 2)}*'
                                             f'{round(cost_factor, 3)}={round(u_score, 3)} {log}\n')
                        WordAlignmentSupportPhonetic(self, [e_pos], [f_pos], rom_e, rom_f,
                                                     rom_e[:l1], rom_f[:l2], cost, u_score)
                if (e_f_count := e_am.bi_counts[(lc_e_token, lc_f_token)]) < 2:
                    pass
                elif (e_f_prob := e_am.support_probability(f_am, lc_e_token, lc_f_token,
                                                           snt_id, 'e', sed=self.sed)) < 0.01:
                    pass
                elif (f_e_prob := f_am.support_probability(e_am, lc_f_token, lc_e_token,
                                                           snt_id, 'f', sed=self.sed)) < 0.01:
                    pass
                elif e_f_count > 1:
                    score = e_f_prob * f_e_prob * (1-1/math.log(e_f_count, 2))
                # if score < 1:
                #     o_score = self.get_a_b_partial_overlap_score('e', e_pos, f_pos, min_sub_length)
                #     score = score + o_score / (1 - score)
                if score := max(score, o_score):
                    self.e_f_candidates[e_pos].append((f_pos, score, e_f_prob, f_e_prob, e_f_count))
                    self.f_e_candidates[f_pos].append((e_pos, score, f_e_prob, e_f_prob, e_f_count))
        for e_pos in range(len(self.lc_e_tokens)):
            self.e_f_candidates[e_pos].sort(key=lambda x: x[1], reverse=True)
        for f_pos in range(len(self.lc_f_tokens)):
            self.f_e_candidates[f_pos].sort(key=lambda x: x[1], reverse=True)

    def has_strong_link_to_other_side(self, a_side: str, a_pos: int) -> bool:
        if self.a_exclusion_pos_list(a_side)[a_pos]:
            return False
        lc_a_token = self.lc_a_tokens(a_side)[a_pos]
        if self.a_am(a_side).function_word_scores[lc_a_token]:
            return False
        if not (b_candidates := self.a_b_candidates(a_side)[a_pos]):
            return False
        if len(b_candidates) >= 2 and b_candidates[1][1] > b_candidates[0][1] * 0.5:  # close 2nd
            return False
        b_top_candidate = b_candidates[0]
        b_pos = b_top_candidate[0]
        if self.b_exclusion_pos_list(a_side)[b_pos]:
            return False
        lc_b_token = self.lc_b_tokens(a_side)[b_pos]
        if self.b_am(a_side).function_word_scores[lc_b_token]:
            return False
        a_b_prob, b_a_prob, a_b_count = b_top_candidate[2:5]
        if (a_b_prob < 0.1) or (b_a_prob < 0.1) or (a_b_count < 10):  # too weak
            return False
        a_candidates = self.b_a_candidates(a_side)[b_pos]
        a_top_candidate = a_candidates[0]
        if a_top_candidate[0] != a_pos:
            return False
        if len(a_candidates) >= 2 and a_candidates[1][1] > a_candidates[0][1] * 0.5:  # close 2nd
            return False
        return True

    def span_has_strong_link_to_other_side(self, side, start_pos, end_pos):
        for pos in range(start_pos, end_pos+1):
            if self.has_strong_link_to_other_side(side, pos):
                return True
        return False

    def markup_strong_unambiguous_links(self, f_log: TextIO, vm: VerboseManager, _snt_id):
        # verbose = (self.snt_id == 'GEN 1:1')
        made_change = False
        for side in ('e', 'f'):
            uc_side = side.upper()
            other_side = 'f' if side == 'e' else 'e'
            for a_pos, lc_a_token in enumerate(self.lc_a_tokens(side)):
                if self.a_exclusion_pos_list(side)[a_pos]:
                    continue
                if self.a_am(side).function_word_scores[lc_a_token]:
                    continue
                if self.a_b_pos_list(side)[a_pos]:  # e has current links to f
                    continue
                if not (b_candidates := self.a_b_candidates(side)[a_pos]):
                    continue
                b_pos_list = self.a_b_pos_list(side)[a_pos]
                b_new_candidates = [b_candidate for b_candidate in b_candidates if b_candidate[0] not in b_pos_list]
                if not b_new_candidates:
                    continue
                if len(b_new_candidates) >= 2 and b_new_candidates[1][1] > b_new_candidates[0][1] * 0.5:  # close 2nd
                    continue
                b_top_new_candidate = b_new_candidates[0]
                b_pos = b_top_new_candidate[0]
                if self.b_exclusion_pos_list(side)[b_pos]:
                    continue
                if self.b_a_pos_list(side)[b_pos]:  # f has current links to e
                    continue
                lc_b_token = self.lc_b_tokens(side)[b_pos]
                if self.b_am(side).function_word_scores[lc_b_token]:
                    continue
                a_b_prob, b_a_prob, a_b_count = b_top_new_candidate[2:5]
                if (a_b_prob < 0.1) or (b_a_prob < 0.1) or (a_b_count < 10):  # too weak
                    continue
                a_new_candidates = [a_candidate for a_candidate in self.b_a_candidates(side)[b_pos]
                                    if a_candidate[0] not in self.b_a_pos_list(side)[b_pos]]
                if len(a_new_candidates) >= 2 and a_new_candidates[1][1] > a_new_candidates[0][1] * 0.5:  # close 2nd
                    continue
                self.a_b_pos_list(side)[a_pos].append(b_pos)
                self.b_a_pos_list(side)[b_pos].append(a_pos)
                lc_b_token = self.lc_b_tokens(side)[b_pos]
                made_change = True
                if vm.log_alignment_diff_details is not None:
                    f_log.write(f'::diff str-unamb-link ::snt-id {self.snt_id} '
                                f'::side {uc_side} ::pos {a_pos}-{b_pos} ::surf {lc_a_token}-{lc_b_token} '
                                f'::p{side}{other_side} {round(a_b_prob, 3)} '
                                f'::p{other_side}{side} {round(b_a_prob, 3)} '
                                f'::class changed added strong unambiguous link\n')
        return made_change

    def old_align_n_on_n_links(self, f_log: TextIO, vm: VerboseManager, snt_id):  # Obsolete?
        made_change = False
        verbose = regex.match(r'(?:GEN 4:9|MAT 1:2)$', snt_id)
        visited_e_pos, visited_f_pos = [], []
        for side in ('e', 'f'):
            visited_a_pos = visited_e_pos if side == 'e' else visited_f_pos
            visited_b_pos = visited_f_pos if side == 'e' else visited_e_pos
            uc_side = side.upper()
            # other_side = 'f' if side == 'e' else 'e'
            for a_pos, lc_a_token in enumerate(self.lc_a_tokens(side)):
                made_local_change = False
                if a_pos in visited_a_pos:
                    continue
                if self.a_exclusion_pos_list(side)[a_pos]:
                    continue
                if self.a_am(side).function_word_scores[lc_a_token]:
                    continue
                a_count = self.a_am(side).counts[lc_a_token]
                total_count = self.a_am(side).total_count
                a_count_ratio = a_count/total_count
                if a_count_ratio >= 0.0002:
                    continue  # common word
                a_pos_list = [i for i, x in enumerate(self.lc_a_tokens(side)) if x == lc_a_token]
                if len(a_pos_list) < 2:
                    continue
                if a_count_ratio >= 0.0001:
                    if verbose:
                        sys.stderr.write(f'\nNNA {snt_id} {side}:{a_pos} {lc_a_token} {a_pos_list} {a_count_ratio} - ')
                    continue  # common word
                best_b_pos = self.best_support_pos_for_a(side)[a_pos]
                if best_b_pos is None:
                    continue
                lc_best_b_token = self.lc_b_tokens(side)[best_b_pos]
                b_pos_list = [i for i, x in enumerate(self.lc_b_tokens(side))
                              if (x == lc_best_b_token)
                              and (not self.b_exclusion_pos_list(side)[i])
                              and (not self.b_am(side).function_word_scores[x])]
                lc_best_b_token = self.lc_b_tokens(side)[best_b_pos]
                if len(a_pos_list) != len(b_pos_list):
                    continue
                problem_alignment = False
                for x_pos in a_pos_list:
                    if len(self.a_b_pos_list(side)[x_pos]) == 0:
                        problem_alignment = True
                    if self.a_is_contiguous(side)[x_pos]:
                        problem_alignment = True
                for x_pos in b_pos_list:
                    if len(self.b_a_pos_list(side)[x_pos]) == 0:
                        problem_alignment = True
                    if self.a_is_contiguous(side)[x_pos]:
                        problem_alignment = True
                if not problem_alignment:
                    continue
                for a2_index, a2_pos in enumerate(a_pos_list):
                    visited_a_pos.append(a2_pos)
                    for b2_index, b2_pos in enumerate(b_pos_list):
                        if a2_index == b2_index:
                            if b2_pos not in self.a_b_pos_list(side)[a2_pos]:
                                self.a_b_pos_list(side)[a2_pos].append(b2_pos)
                                made_local_change = True
                            if a2_pos not in self.b_a_pos_list(side)[b2_pos]:
                                self.b_a_pos_list(side)[b2_pos].append(a2_pos)
                                made_local_change = True
                        else:
                            if b2_pos in self.a_b_pos_list(side)[a2_pos]:
                                self.a_b_pos_list(side)[a2_pos].remove(b2_pos)
                                made_local_change = True
                            if a2_pos in self.b_a_pos_list(side)[b2_pos]:
                                self.b_a_pos_list(side)[b2_pos].remove(a2_pos)
                                made_local_change = True
                for b2_pos in b_pos_list:
                    visited_b_pos.append(b2_pos)
                if made_local_change:
                    made_change = True
                    if a_count_ratio >= 0.0001:
                        if side == 'e':
                            sys.stderr.write(f'\nNNA {snt_id} {side}:{a_pos_list} {lc_a_token} {a_count_ratio} + ')
                    if verbose or len(a_pos_list) > 2:
                        sys.stderr.write(f'\nNNB {snt_id} {side} {lc_a_token} {lc_best_b_token} {a_pos_list} '
                                         f'{b_pos_list} {a_count}/{total_count}')
                    if vm.log_alignment_diff_details is not None:
                        f_log.write(f'::diff n-n-link-old ::snt-id {self.snt_id} '
                                    f'::side {uc_side} ::pos {a_pos_list}-{b_pos_list} '
                                    f'::surf {lc_a_token}-{lc_best_b_token} '
                                    f'::class changed n-n link old\n')
        return made_change

    def align_n_on_n_links(self, f_log: TextIO, vm: VerboseManager, _snt_id) -> bool:
        made_change = False
        # verbose = regex.match(r'(?:GEN 4:9|MAT 1:2)$', snt_id)
        for side in ('e', 'f'):
            uc_side = side.upper()
            # other_side = 'f' if side == 'e' else 'e'
            for a_pos, lc_a_token in enumerate(self.lc_a_tokens(side)):
                if self.a_exclusion_pos_list(side)[a_pos]:
                    continue
                if self.a_am(side).function_word_scores[lc_a_token]:
                    continue
                a_count = self.a_am(side).counts[lc_a_token]
                total_count = self.a_am(side).total_count
                a_count_ratio = a_count/total_count
                if a_count_ratio >= 0.0002:
                    continue  # common word
                a_pos_list = [i for i, x in enumerate(self.lc_a_tokens(side)) if x == lc_a_token]
                if len(a_pos_list) < 2:
                    continue
                best_b_pos = self.best_support_pos_for_a(side)[a_pos]
                if best_b_pos is None:
                    continue
                lc_best_b_token = self.lc_b_tokens(side)[best_b_pos]
                b_pos_list = [i for i, x in enumerate(self.lc_b_tokens(side))
                              if (x == lc_best_b_token)
                              and (not self.b_exclusion_pos_list(side)[i])
                              and (not self.b_am(side).function_word_scores[x])]
                lc_best_b_token = self.lc_b_tokens(side)[best_b_pos]
                a_b_pos_list = sorted(self.a_b_pos_list(side)[a_pos])
                if self.a_is_contiguous(side)[a_pos]:
                    continue
                a_b_pos_list2 = sorted(list(set(a_b_pos_list).intersection(set(b_pos_list))))
                if len(a_b_pos_list2) < 1:
                    continue
                a_pos_list_index = a_pos_list.index(a_pos)
                if a_pos_list_index > 0:
                    a_alt_pos = a_pos_list[a_pos_list_index-1]
                    a_alt_b_pos_list = sorted(self.a_b_pos_list(side)[a_alt_pos])
                    b_pos_to_be_realigned = a_b_pos_list2[0]
                elif a_pos_list_index+1 < len(a_pos_list):
                    a_alt_pos = a_pos_list[a_pos_list_index+1]
                    a_alt_b_pos_list = sorted(self.a_b_pos_list(side)[a_alt_pos])
                    b_pos_to_be_realigned = a_b_pos_list2[-1]
                else:
                    a_alt_pos, a_alt_b_pos_list, b_pos_to_be_realigned = None, None, None
                if a_alt_pos is not None:
                    if (len(a_alt_b_pos_list) == 0) and (len(a_b_pos_list2) == 2):
                        self.a_b_pos_list(side)[a_pos].remove(b_pos_to_be_realigned)
                        self.a_b_pos_list(side)[a_alt_pos].append(b_pos_to_be_realigned)
                        self.b_a_pos_list(side)[b_pos_to_be_realigned].remove(a_pos)
                        self.b_a_pos_list(side)[b_pos_to_be_realigned].append(a_alt_pos)
                        made_change = True
                        if vm.log_alignment_diff_details is not None:
                            f_log.write(f'::diff n-n-link ::snt-id {self.snt_id} '
                                        f'::side {uc_side} ::pos {a_pos}->{a_alt_pos}-{b_pos_to_be_realigned} '
                                        f'::surf {lc_a_token}-{lc_best_b_token} '
                                        f'::class changed n-n link\n')
        return made_change

    def delete_punct_non_fw_links(self, f_log: TextIO, vm: VerboseManager, snt_id) -> bool:
        verbose = False  # verbose = regex.match(r'(?:GEN 1:|MAT 1:)', snt_id)
        made_change = False
        for side in ('e', 'f'):
            uc_side = side.upper()
            # other_side = 'f' if side == 'e' else 'e'
            for a_pos, lc_a_token in enumerate(self.lc_a_tokens(side)):
                if self.a_exclusion_pos_list(side)[a_pos]:
                    continue
                if not is_punct(lc_a_token):
                    continue
                b_pos_list = self.a_b_pos_list(side)[a_pos]
                for b_pos in b_pos_list:
                    lc_b_token = self.lc_b_tokens(side)[b_pos]
                    if self.a_exclusion_pos_list(side)[b_pos]:
                        continue
                    if is_punct(lc_b_token):
                        continue
                    if self.b_am(side).function_word_scores[lc_b_token]:
                        continue
                    a_pos_list2 = self.b_a_pos_list(side)[b_pos]
                    if (a_pos-1 in a_pos_list2) and (a_pos+1 in a_pos_list2):
                        continue
                    self.a_b_pos_list(side)[a_pos].remove(b_pos)
                    self.b_a_pos_list(side)[b_pos].remove(a_pos)
                    made_change = True
                    if verbose:
                        sys.stderr.write(f'\nDelPunct {snt_id} {side} {lc_a_token} {lc_b_token} {a_pos}-{b_pos}')
                    if vm.log_alignment_diff_details is not None:
                        f_log.write(f'::diff del-punct-link ::snt-id {self.snt_id} '
                                    f'::side {uc_side} ::pos {a_pos}-{b_pos} '
                                    f'::surf {lc_a_token}-{lc_b_token} '
                                    f'::class deleted punct link\n')
        return made_change

    def link_phonetic_matches(self, f_log: TextIO, vm: VerboseManager, snt_id, phase: Optional[int] = None) -> bool:
        verbose = (self.snt_id == 'MAT 1:3')   # verbose = regex.match(r'(?:GEN 1:|MAT 1:)', snt_id)
        made_change = False
        for e_pos, lc_e_token in enumerate(self.lc_e_tokens):
            if self.e_exclusion_pos_list[e_pos]:
                continue
            if is_punct(lc_e_token):
                continue
            if self.e_am.function_word_scores[lc_e_token]:
                continue
            for word_align in self.word_align_index[('e', e_pos)]:
                f_span = word_align.f_span
                if len(f_span) != 1:
                    continue
                f_pos = f_span[0]
                lc_f_token = self.lc_f_tokens[f_pos]
                if self.f_exclusion_pos_list[f_pos]:
                    continue
                if is_punct(lc_f_token):
                    continue
                if self.f_am.function_word_scores[lc_f_token]:
                    continue
                verdict = ''
                e_f_pos_list = self.e_f_pos_list[e_pos]
                f_e_pos_list = self.f_e_pos_list[f_pos]
                if f_pos in e_f_pos_list:
                    # verdict = 'already-linked-to-phon-cand'
                    continue  # already linked
                for alt_e_pos in f_e_pos_list:
                    if alt_e_pos != e_pos:
                        alt_lc_e_token = self.lc_e_tokens[alt_e_pos]
                        if self.word_align_index[('ef', alt_e_pos, f_pos)]:
                            verdict = 'alt-already-linked-to-phon'
                        elif self.e_am.bi_weighted_counts[(alt_lc_e_token, lc_f_token)] >= 4:
                            verdict = 'alt-already-linked-with-weight'
                if verdict:
                    continue
                for alt_f_pos in e_f_pos_list:
                    if alt_f_pos != f_pos:
                        alt_lc_f_token = self.lc_f_tokens[alt_f_pos]
                        if self.word_align_index[('ef', e_pos, alt_f_pos)]:
                            verdict = 'alt-already-linked-to-phon'
                        elif self.e_am.bi_weighted_counts[(lc_e_token, alt_lc_f_token)] >= 4:
                            verdict = 'alt-already-linked-with-weight'
                if verdict:
                    continue
                s_score = self.e_am.support_probability(self.f_am, lc_e_token, lc_f_token, snt_id, 'e', sed=self.sed,
                                                        sa=self, a_pos=e_pos, b_pos=f_pos, initial_o_score=True,
                                                        min_sub_length=4)
                if s_score < 0.2:
                    continue
                for word_align_support in word_align.supports:
                    if isinstance(word_align_support, WordAlignmentSupportPhonetic):
                        for alt_e_pos in f_e_pos_list:
                            if alt_e_pos != e_pos:
                                self.e_f_pos_list[alt_e_pos].remove(f_pos)
                                self.f_e_pos_list[f_pos].remove(alt_e_pos)
                        for alt_f_pos in e_f_pos_list:
                            if alt_f_pos != f_pos:
                                self.e_f_pos_list[e_pos].remove(alt_f_pos)
                                self.f_e_pos_list[alt_f_pos].remove(e_pos)
                        if f_pos not in self.e_f_pos_list[e_pos]:
                            self.e_f_pos_list[e_pos].append(f_pos)
                        if e_pos not in self.f_e_pos_list[f_pos]:
                            self.f_e_pos_list[f_pos].append(e_pos)
                        made_change = True
                        if verbose:
                            sys.stderr.write(f'LNK-PHON {lc_e_token} [{e_pos}] {lc_f_token} [{f_pos}] '
                                             f'{word_align_support.e_sub} {word_align_support.f_sub} '
                                             f'{word_align_support.cost} {s_score} {verdict}\n')

                        if vm.log_alignment_diff_details is not None:
                            f_log.write(f'::diff link-phon ::snt-id {self.snt_id} '
                                        f'::side E ::pos {e_pos}-{f_pos} '
                                        f'::surf {lc_e_token}-{lc_f_token} '
                                        f' ::phase {phase}\n')
                        break
        # HHHHERE
        return made_change

    def link_similar_subs(self, f_log: TextIO, vm: VerboseManager, snt_id, orig_sa=None) -> bool:
        verbose = regex.match(r'(?:GEN 1:|GEN 2:|GEN 13:|MAT 1:|MAT 2:)', snt_id)
        verbose2 = (snt_id in ("MAT 1:1"))
        made_change = False
        min_sub_length = 4
        sub_dict = defaultdict(list)
        jc_dict = defaultdict(float)
        score_dict = {}  # values: tuple[float, float, list, str]
        for side in ('e', 'f'):
            for a_pos, lc_a_token in enumerate(self.lc_a_tokens(side)):
                a_b_pos_list = sorted(self.a_b_pos_list(side)[a_pos])
                best_jc = 0
                for b_pos in a_b_pos_list:
                    lc_b_token = self.lc_b_tokens(side)[b_pos]
                    weighted_count = self.a_am(side).bi_weighted_counts[(lc_a_token, lc_b_token)]
                    if weighted_count > best_jc:
                        best_jc = weighted_count
                if best_jc:
                    jc_dict[(side, a_pos)] = best_jc
                if best_jc < 10:
                    for sub in sub_strings(lc_a_token, min_sub_length):
                        if a_pos not in sub_dict[(side, sub)]:
                            sub_dict[(side, sub)].append(a_pos)
        if False and verbose2:
            sys.stderr.write(f'\n   ** {jc_dict}')
            sys.stderr.write(f'\n   *** {sub_dict}')
        for side in ('e', 'f'):
            other_side = 'f' if side == 'e' else 'e'
            for a_pos, lc_a_token in enumerate(self.lc_a_tokens(side)):
                if self.a_am(side).function_word_scores[lc_a_token]:
                    continue
                if jc_dict[(side, a_pos)] > 10:
                    continue
                if self.a_exclusion_pos_list(side)[a_pos]:
                    continue
                if len(lc_a_token) < min_sub_length:
                    continue
                a_count = self.a_am(side).counts[lc_a_token]
                a_aligned = self.a_tokens(side)[a_pos]
                aligned_words = self.a_am(side).aligned_words[lc_a_token]
                best_b_pos_list, best_b_sub, best_b_aligned, best_b_score, best_weight = [], '', '', 0, 0
                for aligned_word in aligned_words:
                    if aligned_word == 'NULL':
                        continue
                    weighted_count = self.a_am(side).bi_weighted_counts[(lc_a_token, aligned_word)]
                    if (weighted_count < 1) or (weighted_count / a_count <= 0.01):
                        continue
                    for aligned_sub_word in sub_strings(aligned_word, min_sub_length):
                        b_pos_list = sub_dict[(other_side, aligned_sub_word)]
                        if not b_pos_list:
                            continue
                        if [b_pos for b_pos in b_pos_list
                                if (jc_dict[(other_side, b_pos)] > 10)
                                    or self.b_am(side).function_word_scores[(b_token := self.lc_b_tokens(side)[b_pos])]
                                    or ((len(aligned_sub_word) == 4) and not b_token.startswith(aligned_sub_word))
                                    or ((len(aligned_sub_word) <= 3) and (aligned_sub_word != b_token))]:
                            continue
                        b_score = len(aligned_sub_word) ** 2 / len(lc_a_token) ** 2 * weighted_count
                        if b_score > best_b_score:
                            best_b_pos_list, best_b_sub, best_b_aligned, best_b_score, best_weight \
                                = b_pos_list, aligned_sub_word, aligned_word, b_score, weighted_count
                if best_b_sub:
                    score_dict[(side, a_pos)] = \
                        (best_b_score, best_weight, best_b_pos_list, best_b_sub, a_aligned, best_b_aligned)
        for side in ('e', 'f'):
            uc_side = side.upper()
            other_side = 'f' if side == 'e' else 'e'
            for side2, a_pos in score_dict.keys():
                if side == side2:
                    lc_a_token = self.lc_a_tokens(side)[a_pos]
                    best_b_score, best_weight, best_b_pos_list, best_b_sub, best_a_aligned, best_b_aligned \
                        = score_dict[(side2, a_pos)]
                    found_novel_b_pos = False
                    if b_pos_set := set(self.a_b_pos_list(side)[a_pos]).intersection(set(best_b_pos_list)):
                        if orig_sa:
                            for b_pos2 in b_pos_set:
                                if b_pos2 in orig_sa.a_b_pos_list(side)[a_pos]:
                                    found_novel_b_pos = True
                                    break
                            if found_novel_b_pos:
                                continue
                        else:
                            continue
                    # best_b_lc_tokens = [self.lc_b_tokens(side)[b_pos] for b_pos in best_b_pos_list]
                    best_b_pos, best_link_proximity = None, 0
                    for b_pos in best_b_pos_list:
                        link_proximity = self.link_proximity(a_pos, b_pos, side)
                        if link_proximity > best_link_proximity:
                            best_b_pos, best_link_proximity = b_pos, link_proximity
                    if best_b_pos and best_link_proximity:
                        lc_b_token = self.lc_b_tokens(side)[best_b_pos]
                        a_b_weighted_count = round(self.a_am(side).bi_weighted_counts[(lc_a_token, lc_b_token)] or 0, 2)
                        best_link_proximity = round(best_link_proximity, 3)
                        # raw_jc_a = round(jc_dict[(side, a_pos)] or 0, 2)
                        # raw_jc_b = round(jc_dict[(side, best_b_pos)] or 0, 2)
                        jc_a = round((jc_dict[(side, a_pos)] or 1) - 1, 2)
                        jc_b = round((jc_dict[(other_side, best_b_pos)] or 1) - 1, 2)
                        best_b_score = round(best_b_score, 2)
                        best_a_score2, best_weight2, best_a_pos_list2, best_a_sub2, best_a_aligned2, best_b_aligned2 \
                            = score_dict.get((other_side, best_b_pos), (0, 0, [], '', '', ''))
                        a_am, b_am = self.a_am(side), self.b_am(side)
                        best_support_probability_for_a \
                            = self.max_support_probability(a_pos, side, snt_id, sed=self.sed, initial_o_score=True,
                                                           min_sub_length=min_sub_length)
                        new_support_probability_for_a \
                            = a_am.support_probability(b_am, lc_a_token, lc_b_token, snt_id, side, sed=self.sed,
                                                       sa=self, a_pos=a_pos, b_pos=best_b_pos, initial_o_score=True,
                                                       min_sub_length=min_sub_length)
                        best_support_probability_for_b \
                            = self.max_support_probability(best_b_pos, other_side, snt_id, sed=self.sed,
                                                           initial_o_score=True, min_sub_length=min_sub_length)
                        new_support_probability_for_b \
                            = b_am.support_probability(a_am, lc_b_token, lc_a_token, snt_id, side, sed=self.sed,
                                                       sa=self, a_pos=a_pos, b_pos=best_b_pos, initial_o_score=True,
                                                       min_sub_length=min_sub_length)
                        if jc_a > best_b_score:
                            connect = False
                            rationale = f"weak best_b_score={best_b_score} (jc_a={jc_a})"
                        elif best_weight2 > best_weight:
                            connect = False
                            rationale = f"insufficient weight={best_weight} weight2={best_weight2}"
                        elif best_support_probability_for_a >= new_support_probability_for_a:
                            connect = False
                            rationale = f"support prob ({side}) not improving " \
                                        f"({round(best_support_probability_for_a, 3)}, " \
                                        f"{round(new_support_probability_for_a, 3)})"
                        elif best_support_probability_for_b >= new_support_probability_for_b:
                            connect = False
                            rationale = f"support prob ({other_side}) not improving " \
                                        f"({round(best_support_probability_for_b, 3)}, " \
                                        f"{round(new_support_probability_for_b, 3)})"
                        elif jc_b > best_b_score:
                            connect = False
                            rationale = f"weak best_b_score={best_b_score} (jc_b={jc_b})"
                        elif (best_link_proximity >= 0.3) and (jc_a + jc_b < a_b_weighted_count + 1.5):
                            # and (not (raw_jc_a and raw_jc_b))
                            connect = True
                            rationale = f"good best_link_proximity={best_link_proximity} "
                        elif (a_b_weighted_count > jc_a) and (a_b_weighted_count > jc_b) \
                                and (best_link_proximity >= 0.2):
                            connect = True
                            rationale = f"strong a_b_weighted_count={a_b_weighted_count} jc_a={jc_a} jc_b={jc_b}"
                        elif (best_link_proximity >= 0.2) \
                                and (min(best_weight, best_b_score) > 2 * max(a_b_weighted_count, jc_a, jc_b)):
                            connect = True
                            rationale = f"decent best_link_proximity={best_link_proximity} strong weight/score"
                        elif (best_link_proximity >= 0.1) and (min(best_weight, best_b_score) > 3) \
                                and (jc_a == 0) and (jc_b == 0):
                            connect = True
                            rationale = f"ok best_link_proximity={best_link_proximity}, jc_a={jc_a}, jc_b={jc_b})"
                        elif best_link_proximity < 0.1:
                            connect = False
                            rationale = f"low best_link_proximity={best_link_proximity}"
                        else:
                            connect = False
                            rationale = f"default (prox={best_link_proximity} jc_a={jc_a} jc_b={jc_b} " \
                                        f"ab={a_b_weighted_count} wt={best_weight} sc={best_b_score})"
                        if verbose:
                            sys.stderr.write(f'SubGloss {snt_id} {side} {lc_a_token} [{a_pos}] {best_b_sub} '
                                             f'{best_b_pos} {lc_b_token} '
                                             f'weight:{round(best_weight, 2)} score:{round(best_b_score, 3)} '
                                             f'prox:{round(best_link_proximity, 2)} r:{rationale} '
                                             f'a:{"ACCEPT" if connect else "REJECT"}\n')
                        notify_without_making_changes = True
                        if new_support_probability_for_a <= best_support_probability_for_a - 0.1:
                            notify_without_making_changes = False
                        else:
                            for wa_support in WordAlignmentSupport.get_word_alignment_supports_with_side(self, side,
                                                                                                         a_pos,
                                                                                                         best_b_pos):
                                if isinstance(wa_support, WordAlignmentSupportPartialMatch):
                                    notify_without_making_changes = False
                                    break
                        if connect or notify_without_making_changes:
                            a_token, b_token = self.a_tokens(side)[a_pos], self.b_tokens(side)[best_b_pos]
                            o_score = self.get_a_b_partial_overlap_score(side, a_pos, best_b_pos, min_sub_length)
                            if connect or (o_score > 0.1):
                                WordAlignmentSupportPartialMatch.create_with_side(self, side, a_pos, best_b_pos,
                                                                                  a_token, b_token, best_b_sub,
                                                                                  best_a_aligned, best_b_aligned,
                                                                                  o_score, best_weight)
                            # if self.snt_id.startswith('MAT 1:'):
                            #     descr = WordAlignment.describe_word_alignment(self, side, a_pos, best_b_pos)
                            #     sys.stderr.write(f'\nGG {connect} {descr}\n')
                        if connect:
                            if best_b_pos not in self.a_b_pos_list(side)[a_pos]:
                                self.a_b_pos_list(side)[a_pos].append(best_b_pos)
                            if a_pos not in self.b_a_pos_list(side)[best_b_pos]:
                                self.b_a_pos_list(side)[best_b_pos].append(a_pos)
                            made_change = True
                            if vm.log_alignment_diff_details is not None:
                                f_log.write(f'::diff sub_gloss ::snt-id {self.snt_id} '
                                            f'::side {uc_side} ::pos {a_pos} {best_b_pos_list} '
                                            f'::surf {lc_a_token} {best_b_sub} '
                                            f'::class sub-gloss link\n')
                # TODO: HHHHERE
        return made_change

    def link_proximity(self, ref_a_pos: int, ref_b_pos: int, ref_side: str) -> Optional[float]:
        """0 is worst link_proximity"""
        window_size = 5
        ref_other_side = 'f' if ref_side == 'e' else 'e'
        weight_sum, prox_sum = 0, 0
        ref_a_token = self.lc_a_tokens(ref_side)[ref_a_pos]
        ref_b_token = self.lc_b_tokens(ref_side)[ref_b_pos]
        verbose = False  # (ref_a_token in ('void', 'separate', 'left'))
        for side in (ref_side, ref_other_side):
            if side == ref_side:
                a_pos, b_pos, a_token, b_token = ref_a_pos, ref_b_pos, ref_a_token, ref_b_token
            else:
                a_pos, b_pos, a_token, b_token = ref_b_pos, ref_a_pos, ref_b_token, ref_a_token
            for a_pos_alt in range(max(0, a_pos-window_size), min(a_pos+window_size+1, len(self.lc_a_tokens(side)))):
                a_diff = abs(a_pos_alt - a_pos)
                if a_pos_alt != a_pos:
                    weight = 1 / a_diff
                    best_b_diff, best_b_pos_alt = None, None
                    for b_pos_alt in self.a_b_pos_list(side)[a_pos_alt]:
                        b_diff = abs(b_pos_alt - b_pos)
                        if (best_b_diff is None) or (b_diff < best_b_diff):
                            best_b_diff, best_b_pos_alt = b_diff, b_pos_alt
                    if verbose:
                        sys.stderr.write(f'\n   LP {side} {a_token} [{a_pos}] {b_token} [{b_pos}] '
                                         f'a:{a_pos_alt} b:{best_b_pos_alt} {best_b_diff}')
                    weight_sum += weight
                    if best_b_diff is not None:
                        prox_sum += weight * ((1 / best_b_diff) if best_b_diff else 1)
        result = prox_sum / weight_sum if weight_sum else None
        if verbose:
            sys.stderr.write(f'\n LP result: {result}')
        return result

    def visualize_alignment(self, snt_id: str, ref: str, sa_score: float, f_html: TextIO,
                            orig_sa=None, orig_sa_score: Optional[float] = None,
                            sed: Optional[SmartEditDistance] = None, spc=None, vfm=None):
        ref2 = regex.sub(' ', '_', ref)
        f_html.write(f'<a name="{ref2}">\n')
        orig_score_clause = '' if orig_sa_score is None or orig_sa_score == sa_score \
            else f'{round(orig_sa_score, 3)} &rarr; '
        f_html.write(f'<b>{ref}</b> &nbsp; &nbsp; Alignment score: {orig_score_clause}{round(sa_score, 3)}'
                     f'<br>\n')
        for side in ('e', 'f'):
            other_side = 'f' if side == 'e' else 'e'
            for a_pos, a_token in enumerate(self.a_tokens(side)):
                a_span_id = f'{ref2}-{side}{a_pos}'
                mouseover_action_s = f"h('{a_span_id}','1');"
                mouseout_action_s = f"h('{a_span_id}','0');"
                b_pos_list = self.a_b_pos_list(side)[a_pos]
                orig_b_pos_list = orig_sa.a_b_pos_list(side)[a_pos] if orig_sa else b_pos_list
                for b_pos in b_pos_list:
                    b_span_id = f'{ref2}-{other_side}{b_pos}'
                    if b_pos in orig_b_pos_list:
                        mouseover_action_s += f"h('{b_span_id}','1');"
                    else:
                        mouseover_action_s += f"h('{b_span_id}','1+');"
                    mouseout_action_s += f"h('{b_span_id}','0');"
                for b_pos in orig_b_pos_list:
                    if b_pos not in b_pos_list:
                        b_span_id = f'{ref2}-{other_side}{b_pos}'
                        mouseover_action_s += f"h('{b_span_id}','1-');"
                        mouseout_action_s += f"h('{b_span_id}','0');"
                cost, best_b_pos = None, None
                if sed:
                    lc_a_token = self.lc_a_tokens(side)[a_pos]
                    best_b_pos = self.best_support_pos_for_a(side)[a_pos]
                    if best_b_pos is not None:
                        lc_b_token = self.lc_b_tokens(side)[best_b_pos]
                        if side == 'e':
                            lc_e_token, lc_f_token = lc_a_token, lc_b_token
                        else:
                            lc_e_token, lc_f_token = lc_b_token, lc_a_token
                        rom_e_token = self.e_am.romanization.get(lc_e_token, lc_e_token)
                        rom_f_token = self.f_am.romanization.get(lc_f_token, lc_f_token)
                        if self.e_am.counts[lc_e_token] < 100 and self.f_am.counts[lc_f_token] < 100:
                            cost, cost_log = sed.string_distance_cost(rom_e_token, rom_f_token, max_cost=2)
                            if cost is not None:
                                cost = round(cost, 2)
                            # if 'minadab' in lc_e_token or 'minadab' in lc_f_token:
                            #   print(f'Point X: {snt_id} {lc_e_token} {lc_f_token};{rom_e_token} {rom_f_token} {cost}')
                ptitle = self.title(side, a_pos, snt_id, orig_sa=orig_sa, cost=cost, best_b_pos=best_b_pos)
                color, text_decoration = self.decoration(side, a_pos, snt_id, mouseover_action_s, cost=cost)
                text_decoration_clause = f'text-decoration:{text_decoration};' if text_decoration else ''
                span_param_s = f'''id="{a_span_id}"'''
                if ptitle:
                    span_param_s += f''' {'patitle' if side == 'e' else 'pbtitle'}="{ptitle}"'''
                span_param_s += f''' style="color:{color};{text_decoration_clause}"'''
                span_param_s += f''' onmouseover="{mouseover_action_s}"'''
                span_param_s += f''' onmouseout="{mouseout_action_s}"'''
                assert('\n' not in span_param_s)
                f_html.write(f"""<span {span_param_s}>{a_token.strip('@')}</span>""")
                spc_note = spc.spc_note(side, a_pos, snt_id, self, vfm)
                f_html.write(spc_note)
                f_html.write(' ')
            f_html.write('<br>\n' if side == 'e' else '\n<hr />\n')


class WordAlignment:
    """Inside a sentence alignment, a specific (multi-) word alignment that can have one or more support elements,
    e.g. based on partial word match, phonetic similarity"""
    def __init__(self, e_span: list[int], f_span: list[int]):
        self.e_span = e_span
        self.f_span = f_span
        self.supports = []
        self.active = True

    def add_word_alignment(self, snt_align: SentenceAlignment):
        """Adds word alignment to sentence alignment, including index"""
        snt_align.word_alignments.append(self)
        e_span = self.e_span
        f_span = self.f_span
        for e_pos in e_span:
            snt_align.word_align_index[('e', e_pos)].append(self)
            for f_pos in f_span:
                snt_align.word_align_index[('ef', e_pos, f_pos)].append(self)
        for f_pos in f_span:
            snt_align.word_align_index[('f', f_pos)].append(self)

    @staticmethod
    def describe_word_alignment(snt_align: SentenceAlignment, side: str, a_pos: int, b_pos: int):
        e_pos, f_pos = (a_pos, b_pos) if side == 'e' else (b_pos, a_pos)
        supports = WordAlignmentSupport.describe_word_alignment_supports(snt_align, e_pos, f_pos)
        head_info = f'WA {snt_align.snt_id} [{e_pos}][{f_pos}]'
        return '\n    '.join([head_info] + supports)


class WordAlignmentSupport:
    def __init__(self, snt_align: SentenceAlignment, e_span: list[int], f_span: list[int], score: float = 0.0):
        """Also finds or creates word alignment inside SentenceAlignment and adds support to it"""
        word_align = None
        for word_align_cand in snt_align.word_align_index[('ef', e_span[0], f_span[0])]:
            # sys.stderr.write(f'  WAS {snt_align.snt_id} {e_span} {f_span} {word_align_cand}\n')
            if (word_align_cand.e_span == e_span) and (word_align_cand.f_span == f_span):
                word_align = word_align_cand
                break
        if word_align is None:
            word_align = WordAlignment(e_span, f_span)
            word_align.add_word_alignment(snt_align)
        word_align.supports.append(self)
        self.score: float = score

    @staticmethod
    def get_word_alignment_supports(snt_align: SentenceAlignment, e_pos: Optional[int], f_pos: Optional[int]) -> list:
        """Returns a list of WordAlignmentSupport"""
        if e_pos is None:
            if f_pos is None:
                return []
            else:
                key = ('f', f_pos)
        else:
            if f_pos is None:
                key = ('e', e_pos)
            else:
                key = ('ef', e_pos, f_pos)
        word_alignment_supports = []
        for word_align in snt_align.word_align_index[key]:
            for word_align_support in word_align.supports:
                word_alignment_supports.append(word_align_support)
        return sorted(word_alignment_supports, key=lambda x: x.score)

    @staticmethod
    def get_word_alignment_supports_with_side(snt_align: SentenceAlignment, side: str,
                                              a_pos: Optional[int], b_pos: Optional[int]) -> list:
        e_pos, f_pos = (a_pos, b_pos) if side == 'e' else (b_pos, a_pos)
        return WordAlignmentSupport.get_word_alignment_supports(snt_align, e_pos, f_pos)

    @staticmethod
    def get_best_word_alignment_support(snt_align: SentenceAlignment, e_pos: int, f_pos: int):
        """Returns a WordAlignmentSupport (or None)"""
        best_word_alignment_support, best_score = None, 0.0
        for word_align in snt_align.word_align_index[('ef', e_pos, f_pos)]:
            for word_align_support in word_align.supports:
                if word_align_support.score > best_score:
                    best_word_alignment_support, best_score = word_align_support, word_align_support.score
        return best_word_alignment_support

    @staticmethod
    def get_best_word_alignment_support_score(snt_align: SentenceAlignment, side, a_pos: int, b_pos: int,
                                              default_result: Optional[float] = 0.0) -> float:
        e_pos, f_pos = (a_pos, b_pos) if side == 'e' else (b_pos, a_pos)
        if best_word_alignment_support := WordAlignmentSupport.get_best_word_alignment_support(snt_align, e_pos, f_pos):
            return best_word_alignment_support.score
        else:
            return default_result

    @staticmethod
    def describe_word_alignment_supports(snt_align: SentenceAlignment, e_pos: int, f_pos: int):
        return [str(x) for x in WordAlignmentSupport.get_word_alignment_supports(snt_align, e_pos, f_pos)]


class WordAlignmentSupportPartialMatch(WordAlignmentSupport):
    def __init__(self, snt_alignment: SentenceAlignment, e_span: list[int], f_span: list[int],
                 e: str, f: str, sub: str, e_aligned: str, f_aligned: str, score: float = 0.0, weight: float = 0.0):
        WordAlignmentSupport.__init__(self, snt_alignment, e_span, f_span)
        self.e = e
        self.f = f
        self.sub = sub
        self.e_aligned = e_aligned
        self.f_aligned = f_aligned
        self.score = score
        self.weight = weight

    @staticmethod
    def create_with_side(snt_alignment: SentenceAlignment, side, a_pos, b_pos, a_str, b_str, sub, a_aligned, b_aligned,
                         score, weight):
        if side == 'e':
            e_span, e_str, f_span, f_str, f_aligned = [a_pos], a_str, [b_pos], b_str, b_aligned
        else:
            e_span, e_str, f_span, f_str, e_aligned = [b_pos], b_str, [a_pos], a_str, a_aligned
        return WordAlignmentSupportPartialMatch(snt_alignment, e_span, f_span, e_str, f_str, sub, a_aligned, b_aligned,
                                                score, weight)

    def __str__(self):
        return f'PartialMatch(e: {self.e} f: {self.f} sub: {self.sub} s: {round(self.score, 4)} ' \
               f'e2: {self.e_aligned} f2: {self.f_aligned} w: {self.weight})'


class WordAlignmentSupportPhonetic(WordAlignmentSupport):
    def __init__(self, snt_alignment: SentenceAlignment, e_span: list[int], f_span: list[int],
                 e: str, f: str,  e_sub: str, f_sub: str, cost: float, score: float = 0.0):
        WordAlignmentSupport.__init__(self, snt_alignment, e_span, f_span)
        self.e = e
        self.f = f
        self.e_sub = e_sub
        self.f_sub = f_sub
        self.cost = cost
        self.score = score

    def __str__(self):
        return f'Phonetic(e: {self.e} f: {self.f} subs: {self.e_sub}/{self.f_sub} ' \
               f'c: {round(self.cost, 2)} s: {round(self.score, 3)})'


class SpellChecker():
    def __init__(self):
        # Record where tokens occur. key: (token, side) (str, str), value: locations (type: [(snt_id, word_index)])
        self.token_index = defaultdict(list)

        # Cache of sed. Key: (token, token, side), value: smart edit distance (float)
        # side is one of 'e', 'f', 'ef'
        self.sed_cache = {}
        self.battery_dict = {}

        # Spelling variation dictionary
        self.spell_var_a_dict = defaultdict(list)  # key (a_token, side)  value: a2_token
        self.spell_var_aa_dict = defaultdict(list)  # key (a_token, a2_token, side)  value: b_token
        self.spell_var_aab_dict = defaultdict(float)  # key (a_token, a2_token, b_token, side)  value: weight

    def add_alignment_to_index(self, sa: SentenceAlignment) -> None:
        snt_id = sa.snt_id
        for side in ('e', 'f'):
            a_lc_tokens = sa.lc_a_tokens(side)
            for a_pos, a_lc_token in enumerate(a_lc_tokens):
                self.token_index[(a_lc_token, side)].append((snt_id, a_pos))

    def cached_string_distance_cost(self, sed: SmartEditDistance, tok1: str, tok2: str, side: str,
                                    max_cost: float) -> float:
        if tok1 == tok2:
            return 0
        cached_cost = self.sed_cache.get((tok1, tok2, side), None)
        if cached_cost is not None:
            return cached_cost
        else:
            cost, cost_log = sed.string_distance_cost(tok1, tok2, max_cost=max_cost)
            self.sed_cache[(tok1, tok2, side)] = cost
            return cost

    @staticmethod
    def skip_token(s: str) -> bool:
        return (len(s) <= 3) or not regex.search(r'\pL', s) or (s == 'NULL')

    # @timer
    def build_alignment_based_spelling_variations(self, side: str, a_am: AlignmentModel, b_am: AlignmentModel,
                                                  sed: SmartEditDistance):
        print('Start build_alignment_based_spelling_variations ...')
        prev_b_prefix = ''
        for b_token in sorted(b_am.counts):
            if self.skip_token(b_token):
                continue
            # if not regex.search(r'a', b_token): continue
            b_prefix = b_token[:1]
            if b_prefix != prev_b_prefix:
                sys.stderr.write(b_prefix + ' ')
                sys.stderr.flush()
                prev_b_prefix = b_prefix
            a_tokens = b_am.aligned_words[b_token]
            # print(f"Point A: {b_token} {a_tokens}")
            for a_token in a_tokens:
                if self.skip_token(a_token):
                    continue
                rom_a_token = a_am.romanization.get(a_token, a_token)
                # bi_counts = a_am.bi_counts[(a_token, b_token)]
                # bi_weighted_counts = a_am.bi_weighted_counts[(a_token, b_token)]
                # print(f"  Point B: {b_token} {a_token} ({bi_counts}/{bi_weighted_counts})")
                for a2_token in a_tokens:
                    if self.skip_token(a2_token):
                        continue
                    if a_token == a2_token:
                        continue
                    rom_a2_token = a_am.romanization.get(a2_token, a2_token)
                    if True:
                        cost = self.cached_string_distance_cost(sed, rom_a_token, rom_a2_token, side, max_cost=0.6)
                        # print(f"  Point C: {b_token} {a_token} {a2_token} {cost}")
                        if cost is not None and cost < 0.6:
                            if a2_token not in self.spell_var_a_dict[(a_token, side)]:
                                self.spell_var_a_dict[(a_token, side)].append(a2_token)
                            self.spell_var_aa_dict[(a_token, a2_token, side)].append(b_token)
                            # bi_counts2 = a_am.bi_counts[(a2_token, b_token)]
                            bi_weighted_counts2 = a_am.bi_weighted_counts[(a2_token, b_token)]
                            # print(f"  Point D: {b_token} {a2_token} ({bi_counts2}/{bi_weighted_counts2})")
                            self.spell_var_aab_dict[(a_token, a2_token, b_token, side)] = bi_weighted_counts2
        print('End build_alignment_based_spelling_variations')

    def report(self, battery_filename: Path, e_am: AlignmentModel, f_am: AlignmentModel, sed: SmartEditDistance) \
            -> None:
        print(f'Spell-check report')
        """
        for e_lc_token in ('aminadab', 'amminadab'):
            print(f"  {e_lc_token} occurs in {self.token_index[(e_lc_token, 'e')]}")
        for args in (('aminadab', 'amminadab', 'amminadab', 'e'),
                     ('aminadab', 'amminadab', 'amminadabs', 'e')):
            a_token, a2_token, b_token, side = args
            print(f"   a:{a_token} a2:{a2_token} b:{b_token}")
            print(f"   A2: {self.spell_var_a_dict[(a_token, side)]}")
            print(f"   B: {self.spell_var_aa_dict[(a_token, a2_token, side)]}")
            if (a_token, a2_token, b_token, side) in self.spell_var_aab_dict:
                print(f"   W: {self.spell_var_aab_dict[(a_token, a2_token, b_token, side)]}")
        print(f"  A {self.spell_var_a_dict}")
        print(f"  AA {self.spell_var_aa_dict}")
        print(f"  AAB {self.spell_var_aab_dict}")
        """
        if battery_filename:
            battery_e_html_filename = Path(str(battery_filename).removesuffix('.jsonl') + '-e.html')
            battery_f_html_filename = Path(str(battery_filename).removesuffix('.jsonl') + '-f.html')
            with open(battery_filename, 'w') as f_out, \
                    open(battery_e_html_filename, 'w') as f_e_out, \
                    open(battery_f_html_filename, 'w') as f_f_out:
                self.report_side('e', f_out, e_am, f_am, sed, f_e_out)
                self.report_side('f', f_out, f_am, e_am, sed, f_f_out)

    @staticmethod
    # TODO: HHHERE ending
    def exclude_morph_variants(s1: str, s2: str) -> bool:
        for i in (0, 1):
            t1 = s1 if i else s2
            t2 = s2 if i else s1
            for ending in ('e', 'es', '\u0940'):
                if t1 + ending == t2:
                    return True
            if t1 + 's' == t2 and not t1.endswith('s'):
                return True
        return False

    @staticmethod
    def round_to_near_int(x: float) -> Union[float, int]:
        y = round(x)
        if -0.1 < y - x < 0.1:
            return y
        else:
            return x

    @staticmethod
    def dominant_tc_token(a_token: str, a_am: AlignmentModel) -> str:
        a_tc_token = a_token
        best_count = 0
        for a_tc_token_cand in a_am.tc_alts[a_token]:
            if a_am.tc_counts[a_tc_token_cand] > best_count:
                best_count = a_am.tc_counts[a_tc_token_cand]
                a_tc_token = a_tc_token_cand
        return a_tc_token

    def pro_list(self, spell_alt_dict: dict, b_am: AlignmentModel) -> list[str]:
        result = []
        if spell_alt_dict['pros']:
            for pro_dict in spell_alt_dict['pros']:
                if pro_dict['pro']:
                    for pro_tok_dict in pro_dict['pro']:
                        if tok := pro_tok_dict['tok']:
                            if b_am:
                                tok = self.dominant_tc_token(tok, b_am)
                            result.append(tok)
        return result

    @staticmethod
    def mark_non_printable_chars(s: str) -> str:
        return regex.sub(r'[\u200B-\u200F]', lambda m: f'<{ud.name(m.group(0))}>', s)

    def non_printable_char_clause(self, s: str) -> str:
        if regex.search(r'[\u200B-\u200F]', s):
            return regex.sub(' ', '&nbsp;', f'  with hidden characters: {guard_html(self.mark_non_printable_chars(s))}')
        else:
            return ''

    # @timer
    def report_side(self, side: str, f_out, a_am: AlignmentModel, b_am: AlignmentModel, sed: SmartEditDistance,
                    f_html_out) -> None:
        lang_code = a_am.lang_code or side   # e.g. 'eng'  with fallback 'e'
        ref_lang_code = b_am.lang_code
        lang_name = lang_to_langcode(lang_code) or lang_code
        ref_lang_name = lang_to_langcode(ref_lang_code) or ref_lang_code
        date = f"{datetime.datetime.now():%B %d, %Y at %H:%M}"
        color_string_alt = ColorStringAlternative()
        if f_html_out:
            f_html_out.write(html_head(f'Greek Room Spell Checker for {lang_name}', date, f'{lang_code} spell'))
            f_html_out.write('<ol style="margin-top:0px;margin-bottom:0px;"></ol>')
            f_html_out.write(f'This page lists spell-checker alerts that could indicate spelling '
                             f'inconsistencies.<br>\n')
            f_html_out.write(f'<span style="text-decoration:underline" onclick="toggle_info(\'top-note\');">'
                             f'Click here</span> for more information about the purpose and the features of '
                             f'this page.')
            f_html_out.write('<div id="top-note" style="display:none"><p><ul style="margin-top:0px;">')
            f_html_out.write(f'<li> The purpose of this page is to help human Bible translators improve the quality '
                             f'of their translation by showing targeted potential spelling inconsistencies. '
                             f'<ul><li> This Greek Room tool does so without the need of a curated list of valid '
                             f'{lang_name} words.</ul>\n')
            f_html_out.write(f'<li> The spell-checker alerts listed below are based on two factors: '
                             f'<ol style="margin-top:0px;margin-bottom:0px;"> '
                             f'<li> Phonetic similarity between two words'
                             f'<li> Likely similar meaning, based on sharing an alignment (i.e. link, correspondence) '
                             f'to the same word in a reference Bible translation.</ol>\n')
            f_html_out.write(f'<li> Reference Bible translation used for this spell checker page: {ref_lang_name}\n')
            f_html_out.write(f'<li> <i>Phonetic</i> similarity would rank a word pair such as <i>phase/feiz</i> as more'
                             f' similar than <i>cat/mat</i>, even though the latter pair differs in only one letter.\n')
            f_html_out.write(f'<li> The numbers at the first position in square brackets below are the phonetic'
                             f' distances between a head word and its spelling alternative.\n')
            f_html_out.write(f'<li> The words at the second position in square brackets are words in the '
                             f'reference Bible translation that are aligned to both the head word and the spelling '
                             f'alternative.\n')
            f_html_out.write(f'<li> Click on a Bible verse reference to show/hide the Bible verse.\n')
            f_html_out.write(f'<li> Hover over a {lang_name} word to see its romanization.\n')
            f_html_out.write(f'<li> This page is a spell-checking <i>summary</i> page. Spell-checking alerts are also '
                             f'included in the chapter-by-chapter visualized word alignment pages.\n')
            f_html_out.write(f'<li> The human translator will make the final decision on whether a spell-checker '
                             f'alert should be followed up on by spelling corrections or not.\n')
            f_html_out.write(f'<li> Spelling variations reported by this tool are sometimes legitimate, '
                             f'e.g. because <ul>'
                             f'<li> they reflect valid morphological variations (such as drank/drunk), '
                             f'<li> because the underlying word alignment is imperfect due to insufficient data, '
                             f'<li> or for some other reason.</ul>\n')
            f_html_out.write(f'</ul></div>\n<p>\n<hr>\n<p>\n')
        # challenges:
        tokens_mentioned = {}
        spelling_alts_dict = {}
        a_tokens = sorted(a_am.counts)
        for a_token in a_tokens:
            rom_a_token = a_am.romanization.get(a_token, a_token)
            a_count = a_am.counts[a_token]
            spell_alternatives = self.spell_var_a_dict[(a_token, side)]
            selected_spell_alternatives = []
            spell_alt_list = []
            max_pmi_a1b = -99
            for spell_alt in spell_alternatives:
                rom_a2_token = a_am.romanization.get(spell_alt, spell_alt)
                cost = self.cached_string_distance_cost(sed, rom_a_token, rom_a2_token, side, max_cost=0.6)
                if cost > 0.5:
                    continue
                if AffixMorphVariantCheck.is_morph_variant(a_token, spell_alt, lang_code,
                                                           a_am.affix_morph_variant_check_dict):
                    # if self.exclude_morph_variants(a_token, spell_alt):
                    if lang_code in ['xxx']:
                        sys.stderr.write(f'  AMVC {a_token}, {spell_alt}, {lang_code}: True (not recording)\n')
                    continue
                if a_am.affix_morph_variant_check_dict[(lang_code, 'no-variants', a_token, spell_alt)]:
                    # sys.stderr.write(f'  AMVC-lit {a_token}, {spell_alt}, {lang_code}: True (not recording)\n')
                    continue
                # Hindi negation prefix 'अ' (to be transferred to morph_variants.txt)
                if (lang_code == 'hin') and ((a_token == 'अ' + spell_alt) or (spell_alt == 'अ' + a_token)):
                    sys.stderr.write(f'  AMVC-neg {a_token}, {spell_alt}, {lang_code}: True (not recording)\n')
                    continue
                a2_count = a_am.counts[spell_alt]
                b_tokens = self.spell_var_aa_dict[(a_token, spell_alt, side)]
                b_support_list = []
                total_b_count, total_a1b_count, total_a2b_count = 0, 0, 0
                for b_token in b_tokens:
                    b_count = self.round_to_near_int(b_am.counts[b_token])
                    a1b_count = a_am.bi_weighted_counts[(a_token, b_token)]
                    a2b_count = self.spell_var_aab_dict[(a_token, spell_alt, b_token, side)]
                    pmi_a1b = pmi(a_count, b_count, a1b_count, a_am.avg_total_count, smoothing=0.3)
                    pmi_a2b = pmi(a2_count, b_count, a2b_count, a_am.avg_total_count, smoothing=0.3)
                    min_count_ratio = 0.01 if cost < 0.35 else 0.1
                    if (pmi_a1b >= 0.5) \
                            and (pmi_a2b >= 1.0) \
                            and (a1b_count / a_count >= min_count_ratio) \
                            and ((a1b_count / b_count >= min_count_ratio) or (a1b_count / a_count >= 0.1)) \
                            and (a2b_count / a2_count >= min_count_ratio) \
                            and (a2b_count / b_count >= min_count_ratio):
                        total_b_count += b_count
                        total_a1b_count += a1b_count
                        total_a2b_count += a2b_count
                        if pmi_a1b > max_pmi_a1b:
                            max_pmi_a1b = pmi_a1b
                        b_support_list.append({'tok': b_token, 'n3': b_count,
                                               'pmi13': round(pmi_a1b, 1), 'pmi23': round(pmi_a2b, 1)})
                b_support_list.sort(key=lambda x: (-(x.get('pmi13', 0) + x.get('pmi23', 0)), b_token))
                if total_a2b_count >= 1.0:
                    total_pmi_a1b = pmi(a_count, total_b_count, total_a1b_count, a_am.avg_total_count, smoothing=0.3)
                    total_pmi_a2b = pmi(a2_count, total_b_count, total_a2b_count, a_am.avg_total_count, smoothing=0.3)
                    spell_alt_list.append({'alt': spell_alt, 'sed': round(cost, 2), 'n2': a2_count,
                                           'pros': [{'pro': b_support_list}], 'n3': total_b_count,
                                           'n13': round(total_a1b_count, 1), 'n23': round(total_a2b_count, 1),
                                           'pmi13': round(total_pmi_a1b, 1), 'pmi23': round(total_pmi_a2b, 1)})
                    selected_spell_alternatives.append(spell_alt)
                    tokens_mentioned[a_token] = True
                    tokens_mentioned[spell_alt] = True
            if spell_alt_list:
                result = {'cat': 'spc', 'lng': side, 'tok': a_token, 'n1': a_count, 'alts': spell_alt_list}
                a_tc_token = self.dominant_tc_token(a_token, a_am)
                spelling_alts_dict[a_tc_token] \
                    = [(self.dominant_tc_token(x['alt'], a_am), x['sed'], self.pro_list(x, b_am))
                            for x in spell_alt_list]
                # support for original spelling
                b_support_list = []
                for b_token in a_am.aligned_words[a_token]:
                    b_count = self.round_to_near_int(b_am.counts[b_token])
                    a1b_count = a_am.bi_weighted_counts[(a_token, b_token)]
                    pmi_a1b = pmi(a_count, b_count, a1b_count, a_am.avg_total_count, smoothing=0.3)
                    max_pmi_a2b, max_a2_count = 0, 0
                    for a2_token in selected_spell_alternatives:
                        a2_count = a_am.counts[a2_token]
                        a2b_count = a_am.bi_weighted_counts[(a2_token, b_token)]
                        pmi_a2b = pmi(a2_count, b_count, a2b_count, a_am.avg_total_count, smoothing=0.3)
                        if pmi_a2b > max_pmi_a2b:
                            max_pmi_a2b = pmi_a2b
                            max_a2_count = a2_count
                        if False and (a_token == 'this') and (b_token == 'so'):
                            sys.stderr.write(f'Point A a: {a_token} ({a_count}) a2: {a2_token} ({a2_count}) '
                                             f'b: {b_token} ({b_count}) a1b: {a1b_count} a2b: {a2b_count} '
                                             f'pmi_a1b: {pmi_a1b} pmi_a2b: {pmi_a2b}\n')
                    min_count_ratio = 0.01
                    if (pmi_a1b >= 1.0) \
                            and (a1b_count / a_count >= min_count_ratio) \
                            and (a1b_count / b_count >= min_count_ratio) \
                            and ((pmi_a1b > max_pmi_a1b)
                                 or ((pmi_a1b > max_pmi_a2b) and (a_count > max_a2_count) and (a_count > 10))):
                        b_support_list.append({'tok': b_token, 'n3': b_count, 'pmi13': round(pmi_a1b, 1)})
                if b_support_list:
                    b_support_list.sort(key=lambda x: (-(x.get('pmi13', 0) + x.get('pmi23', 0)), b_token))
                    result['cons'] = [{'con': b_support_list}]
                f_out.write(json.dumps(result) + "\n")
        for a_token in a_tokens:
            if tokens_mentioned.get(a_token, False):
                result = {'cat': 'idx', 'lng': side, 'tok': a_token, 'locs': self.token_index[(a_token, side)]}
                f_out.write(json.dumps(result) + "\n")
        highlight_style = 'style="color:#0000FF;font-weight:bold;background-color:yellow;"'
        suffix_diff_dict = defaultdict(int)
        n_anchors = 0
        if f_html_out:
            toggle_index = 0
            full_verse_elems = []
            max_instances_printed = 10
            prev_registered_anchor_alts = defaultdict(bool)
            for a_tc_token in sorted(spelling_alts_dict.keys()):
                rom_a_token = a_am.romanization.get(a_tc_token, None) or a_am.romanization.get(a_tc_token.lower(), None)
                spelling_alts = []
                anchor_title = ''
                all_spelling_alts_prev_registered = True
                if rom_a_token:
                    anchor_title += f'{guard_html(a_tc_token)}&nbsp;&nbsp;{guard_html(rom_a_token)}'
                anchor_title += self.non_printable_char_clause(a_tc_token)
                for spelling_alt in spelling_alts_dict[a_tc_token]:
                    spelling_alts.append(spelling_alt[0])
                    rom_alt = a_am.romanization.get(spelling_alt[0], None) \
                              or a_am.romanization.get(spelling_alt[0].lower(), None)
                    if rom_alt:
                        anchor_title += f'&#xA;&bull;&nbsp;{guard_html(spelling_alt[0])}' \
                                        f'&nbsp;&nbsp;{guard_html(rom_alt)}'
                        anchor_title += self.non_printable_char_clause(spelling_alt[0])
                    if not prev_registered_anchor_alts[(spelling_alt[0], a_tc_token)]:
                        all_spelling_alts_prev_registered = False
                colored_string_list = color_string_alt.markup_strings_diffs(a_tc_token, spelling_alts,
                                                                            prev_reg=prev_registered_anchor_alts)
                colored_a_tc_token = colored_string_list.pop(0)
                refs = [x[0] for x in self.token_index[(a_tc_token.lower(), side)]]
                ref_word_indexes = [x[1] for x in self.token_index[(a_tc_token.lower(), side)]]
                refs2 = []
                for i in range(len(refs)):
                    if i >= max_instances_printed:
                        refs2.append(f'... +{len(refs) - max_instances_printed}')
                        break
                    else:
                        ref = refs[i]
                        ref_word_index = ref_word_indexes[i]
                        toggle_index += 1
                        if verse := a_am.verses[ref]:
                            tokens = verse.split()
                            tokens[ref_word_index] = f'<span {highlight_style}>{tokens[ref_word_index]}</span>'
                            verse = ' '.join(tokens)
                            verse = de_tokenize_text(verse)
                            refs2.append(f"""<span style="text-decoration:underline" """
                                       + f"""onclick="toggle_info('t{toggle_index}');">{ref}</span>""")
                            full_verse_elems.append(f"""        <div id="t{toggle_index}" style="display:none" """
                                                  + f"""onclick="toggle_info('t{toggle_index}');">"""
                                                  + f"""<br> <span style="text-decoration:underline">{ref}</span> """
                                                  + f"""&nbsp; {verse}</div>\n""")
                        else:
                            refs.append(ref)
                n_anchors += 1
                if anchor_title:
                    anchor_clause = f"<span patitle='{anchor_title}'>{colored_a_tc_token}</span>"
                else:
                    anchor_clause = colored_a_tc_token
                color_clause = ' style="color:#AAAAAA;"' if all_spelling_alts_prev_registered else ''
                f_html_out.write(f"        {anchor_clause} &nbsp; "
                                 f"<span{color_clause}>({', '.join(refs2)})</span>\n")
                f_html_out.write('<ul style="margin-top:0px;">')
                for spelling_alt in spelling_alts_dict[a_tc_token]:
                    alt, sed, pro_list = spelling_alt
                    rom_alt = a_am.romanization.get(alt, None) or a_am.romanization.get(alt.lower(), None)
                    colored_alt = colored_string_list.pop(0) or alt
                    common_prefix, s1, s2 = AffixMorphVariantCheck.common_prefix_different_suffixes(a_tc_token, alt)
                    suffix_diff_dict[(lang_code, s1, s2)] += 1
                    refs = [x[0] for x in self.token_index[(alt.lower(), side)]]
                    ref_word_indexes = [x[1] for x in self.token_index[(alt.lower(), side)]]
                    refs2 = []
                    for i in range(len(refs)):
                        ref = refs[i]
                        toggle_index += 1
                        ref_word_index = ref_word_indexes[i]
                        if i >= max_instances_printed:
                            refs2.append(f'... +{len(refs) - max_instances_printed}')
                            break
                        else:
                            if verse := a_am.verses[ref]:
                                tokens = verse.split()
                                tokens[ref_word_index] = f'<span {highlight_style}>{tokens[ref_word_index]}</span>'
                                verse = ' '.join(tokens)
                                verse = de_tokenize_text(verse)
                                refs2.append(f"""<span style="text-decoration:underline" """
                                           + f"""onclick="toggle_info('t{toggle_index}');">{ref}</span>""")
                                full_verse_elems.append(f"""<div id="t{toggle_index}" style="display:none" """
                                                        + f"""onclick="toggle_info('t{toggle_index}');">"""
                                                        + f"""<br> """
                                                        + f"""<span style="text-decoration:underline">{ref}</span> """
                                                        + f""" &nbsp; {verse}</div>\n""")
                    sed_title = f'{sed} is the phonetic distance between {a_tc_token} and {alt}'
                    if rom_a_token and rom_alt:
                        alt_title = f'{guard_html(a_tc_token)}&nbsp;&nbsp;{guard_html(rom_a_token)}'
                        alt_title += self.non_printable_char_clause(a_tc_token)
                        alt_title += f'&#xA;&bull;&nbsp;{guard_html(alt)}&nbsp;&nbsp;{guard_html(rom_alt)}'
                        alt_title += self.non_printable_char_clause(alt)
                        alt_clause = f"<span patitle='{alt_title}'>{colored_alt}</span>"
                    else:
                        alt_clause = colored_alt
                    color_clause = ' style="color:#AAAAAA;"' \
                        if prev_registered_anchor_alts[(alt, a_tc_token)] else ''
                    f_html_out.write(f"        <li> {alt_clause} &nbsp; <span{color_clause} "
                                     f"title='{sed_title}'>[{sed}; {', '.join(pro_list)}]</span> &nbsp; "
                                     f"<span{color_clause}>({', '.join(refs2)})</span>\n")
                    prev_registered_anchor_alts[(a_tc_token, alt)] = True
                f_html_out.write("<br>")
                for full_verse_elem in full_verse_elems:
                    f_html_out.write(full_verse_elem)
                full_verse_elems = []
                f_html_out.write('</ul>\n')
        if n_anchors:
            f_html_out.write(f'<p><hr>Printed {n_anchors} spell-check summary entries.\n')
        f_html_out.write('    </body>\n</html>\n')
        for suffix_pair in sorted(suffix_diff_dict, key=lambda x: (x[0], -suffix_diff_dict[x])):
            count = suffix_diff_dict[suffix_pair]
            if count >= 3:
                sys.stderr.write(f'# Suffix pair: {suffix_pair} ({count})   '
                                 f'{encode_unicode_escape(str(suffix_pair[1:]))}\n')
        sys.stderr.write(f'Printed {n_anchors} spell-check summary entries.\n')

    def read_battery_file(self, filename: str):
        n_entries = 0
        try:
            with open(filename) as f:
                for line in f:
                    d = json.loads(line)
                    cat = d.get('cat', None)
                    lang_code = d.get('lng', None)
                    tok = d.get('tok', None)
                    if cat in ("spc", "idx"):
                        self.battery_dict[(cat, lang_code, tok)] = d
                        n_entries += 1
        except TypeError:
            sys.stderr.write('No valid battery filename specified.\n')
        except OSError:
            sys.stderr.write(f'Could not open {filename}\n')
        else:
            sys.stderr.write(f'Read in {n_entries} entries from {filename}\n')

    @staticmethod
    def re_case(s: str, orig_s: str) -> str:
        if len(orig_s) > 0 and orig_s[0].isupper():
            return s.capitalize()
        else:
            return s

    def idx_locs(self, side: str, lc_token: str) -> str:
        if index_d := self.battery_dict.get(('idx', side, lc_token), None):
            locs = index_d.get('locs', [])
            core_locs = [x[0] for x in locs]
            max_n_locs = 5
            if len(core_locs) >= max_n_locs + 2:
                sel_core_locs = core_locs[0:max_n_locs]
                n_rest = f' + {len(core_locs) - len(sel_core_locs)} more'
            else:
                sel_core_locs = core_locs
                n_rest = ''
            return ', '.join(sel_core_locs) + n_rest
        return ''

    def spc_note(self, a_side: str, a_pos: int, snt_id: str, sa: SentenceAlignment, vfm: VisualizationFileManager) \
            -> str:
        a_token = sa.a_tokens(a_side)[a_pos]
        alt_tokens = []
        a_lc_token = sa.lc_a_tokens(a_side)[a_pos]
        b_pos_list = sa.a_b_pos_list(a_side)[a_pos]
        b_tokens = [sa.lc_b_tokens(a_side)[b_pos] for b_pos in b_pos_list]
        if spc_dict := self.battery_dict.get(('spc', a_side, a_lc_token), None):
            loc_s = self.idx_locs(a_side, a_lc_token)
            g_note = f'''Current spelling: {guard_html(a_token)} ({guard_html(loc_s)})'''
            max_con = 0
            for con_d in spc_dict.get('cons', []):
                for con_d2 in con_d.get('con', []):
                    tok = con_d2.get('tok', '')
                    pmi13 = con_d2.get('pmi13', 0)
                    if (tok in b_tokens) and (pmi13 > max_con):
                        max_con = pmi13
            if max_con > 1.5:
                return ''
            n_high, n_medium, n_low, n_very_low = 0, 0, 0, 0
            minus_class = '\u2011'  # nb hyphen
            for alt_d in spc_dict.get('alts', []):
                if alt_token := alt_d.get('alt', None):
                    alt_tokens.append(alt_token)
                    pmi13, pmi23 = 0, 0
                    for pro_d in alt_d.get('pros', []):
                        for pro_d2 in pro_d.get('pro', []):
                            tok = pro_d2.get('tok', '')
                            if tok in b_tokens:
                                pmi13 = pro_d2.get('pmi13', 0)
                                pmi23 = pro_d2.get('pmi23', 0)
                            if pmi13 or pmi23:
                                break
                        if pmi13 or pmi23:
                            break
                    if pmi13 == 0 and pmi23 == 0:
                        pmi13 = alt_d.get('pmi13', 0)
                        pmi23 = alt_d.get('pmi23', 0)
                    if pmi23 + 0.5 <= max_con:
                        n_low += 1
                        prob_class = minus_class
                    elif pmi23 + 1.0 <= max_con:
                        n_very_low += 1
                        prob_class = minus_class
                    elif pmi13 + 0.5 <= pmi23:
                        n_high += 1
                        prob_class = '+'
                    elif pmi23 + 1.0 <= pmi13:
                        n_very_low += 1
                        prob_class = minus_class
                    elif pmi23 + 0.5 <= pmi13:
                        n_low += 1
                        prob_class = minus_class
                    else:
                        n_medium += 1
                        prob_class = '\u25CB'  # white circle
                    loc_s = self.idx_locs(a_side, alt_token)
                    sed = alt_d.get('sed', None)
                    g_note += f'&#xA; {prob_class} Similar ({round(sed, 2)}): ' \
                              f'{guard_html(self.re_case(alt_token, a_token))} ' \
                              f'({guard_html(loc_s)})'
            g_title = g_note.replace(' ', '&nbsp;').replace('&#xA;', ' ')
            # g_title = guard_html(json.dumps(spc_dict))
            if n_high:
                color = 'red'
            elif n_medium:
                color = 'blue'
            elif n_low:
                color = '#888888'
            else:  # very low
                return ''
            snt_id2 = snt_id.replace(' ', '_')
            if vfm:
                e_search_term_s, f_search_term_s = '', ''
                if a_side == 'e':
                    e_search_terms = [a_token]
                    e_search_terms.extend(alt_tokens)
                    e_search_term_s = '|'.join(e_search_terms)
                if a_side == 'f':
                    f_search_terms = [a_token]
                    f_search_terms.extend(alt_tokens)
                    f_search_term_s = '|'.join(f_search_terms)
                form_id = f'span-spc-{a_side}-{snt_id2}-{a_pos}'
                # onclick_clause = f'''onclick="set_inner_html('log', '{form_id}');"'''
                onclick_function = f"submit_form('{form_id}', '{vfm.text_filename}', '{str(vfm.html_filename_dir)}', " \
                                   f"'{vfm.e_lang_name}', '{vfm.f_lang_name}', '{e_search_term_s}', " \
                                   f"'{f_search_term_s}', 'log/spell-check.txt')"
                onclick_clause = f'onclick="{onclick_function}"'
            else:
                onclick_clause = ''
            span_attr = f'''style="color:{color};text-decoration:none;"''' \
                        + f''' {'patitle' if a_side == 'e' else 'pbtitle'}="{g_title}"'''
            if onclick_clause:
                span_attr += ' ' + onclick_clause
                span_id = f'span-spc-{a_side}-{snt_id2}-{a_pos}'
                span_attr += f' id="{span_id}"'
                mouseover_action_s = f"h('{span_id}','1');"
                mouseout_action_s = f"h('{span_id}','0');"
                span_attr += f' onmouseover="{mouseover_action_s}"'
                span_attr += f' onmouseout="{mouseout_action_s}"'
            return f'''<a {span_attr} target="_SPC">\u27E1</a>'''
        return ''


def slot_value_in_double_colon_del_list(line: str, slot: str, default: Optional = None) -> str:
    """For a given slot, e.g. 'cost', get its value from a line such as '::s1 of course ::s2 ::cost 0.3' -> 0.3
    The value can be an empty string, as for ::s2 in the example above."""
    m = regex.match(fr'(?:.*\s)?::{slot}(|\s+\S.*?)(?:\s+::\S.*|\s*)$', line)
    return m.group(1).strip() if m else default


def int_or_float(s, default=0):
    if isinstance(s, (int, float)):
        return s
    elif isinstance(s, str):
        try:
            x = float(s)
            return int(x) if x.is_integer() else x
        except ValueError or TypeError:
            return default
    else:
        return default


def print_html_head(f_html, e_lang_name: str, f_lang_name: str, cgi_box: str):
    assert isinstance(e_lang_name, str), f'Function print_html_head: e_lang_name type error: {e_lang_name}'
    assert isinstance(f_lang_name, str), f'Function print_html_head: f_lang_name type error: {f_lang_name}'
    date = f"{datetime.datetime.now():%B %d, %Y at %H:%M}"
    f_html.write("""
<html>
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    <title>Alignments</title>
    <style>
      [patitle]:hover:after {opacity: 1; transition: all 0.05s ease 0.1s; visibility: visible;}
      [patitle]:after {
        content: attr(patitle);
        position: absolute;
        bottom: 1.4em;
        left: -9px;
        padding: 5px 10px 5px 10px;
        color: #000;
        font-weight: normal;
        white-space: wrap;
        -moz-border-radius: 5px;
        -webkit-border-radius: 5px;
        border-radius: 5px;
        -moz-box-shadow: 0px 0px 4px #222;
        -webkit-box-shadow: 0px 0px 4px #222;
        box-shadow: 0px 0px 4px #222;
        font-size: 100%;
        background-color: #E0E7FF;
        opacity: 0;
        z-index: 99999;
        visibility: hidden;}
      [patitle] {position: relative; }
      [pbtitle]:hover:after {opacity: 1; transition: all 0.05s ease 0.1s; visibility: visible;}
      [pbtitle]:after {
        content: attr(pbtitle);
        position: absolute;
        top: 1.4em;
        left: -9px;
        padding: 5px 10px 5px 10px;
        color: #000;
        font-weight: normal;
        white-space: wrap;
        -moz-border-radius: 5px;
        -webkit-border-radius: 5px;
        border-radius: 5px;
        -moz-box-shadow: 0px 0px 4px #222;
        -webkit-box-shadow: 0px 0px 4px #222;
        box-shadow: 0px 0px 4px #222;
        font-size: 100%;
        background-color: #FFE0E7;
        opacity: 0;
        z-index: 99999;
        visibility: hidden;}
      [pbtitle] {position: relative; }
    </style>
    <script type="text/javascript">
    <!--
    function h(id, value) {
       if ((s = document.getElementById(id)) != null) {
          if (! s.origColor) {
             if (s.style.color) {
                s.origColor = s.style.color;
             } else {
                s.origColor = '#000000';
             }
          }
          if (! s.origFontWeight) {
             if (s.style.fontWeight) {
                s.origFontWeight = s.style.fontWeight;
             } else {
                s.origFontWeight = 'normal';
             }
          }
          if (value == '1') {
             s.style.color = '#0000FF';
             s.style.fontWeight = 'bold';
          } else if (value == '1+') {
             s.style.color = '#00AAFF';
             s.style.fontWeight = 'bold';
          } else if (value == '1-') {
             s.style.color = '#FF00FF';
             s.style.fontWeight = 'bold';
          } else {
             s.style.color = s.origColor;
             s.style.fontWeight = s.origFontWeight;
          }
       }
    }
    
    function set_inner_html(id, value) {
       var s;
       if ((s = document.getElementById(id)) != null) {
          s.innerHTML = value;
       }
    }
    
    function submit_form(form_id, text_filename, html_filename_dir, e_lang_name, f_lang_name, 
                         e_search_terms, f_search_terms, log_filename) {
       newwindow= window.open('', 'SPELLING-' + form_id);
       var tmp = newwindow.document;
       tmp.write('<html>\\n  <head><title>GR Spellings</title></head>\\n');
       tmp.write(' <body style="background-color:#FFFFEE;" onload="document.getElementById(\\'spc\\').submit();">\\n');
       tmp.write('  Greek Room Spellings\\n');
       tmp.write('  <form id="spc" enctype="multipart/form-data"' 
               + ' action="http://localhost/cgi-bin/filter-viz-snt-align.py" method="post">\\n');
       tmp.write('  <input type="hidden" name="text_filename" value="' + text_filename + '">\\n');
       tmp.write('  <input type="hidden" name="html_filename_dir" value="' + html_filename_dir + '">\\n');
       tmp.write('  <input type="hidden" name="e_lang_name" value="' + e_lang_name + '">\\n');
       tmp.write('  <input type="hidden" name="f_lang_name" value="' + f_lang_name + '">\\n');
       tmp.write('  <input type="hidden" name="max_number_output_snt" value="20">\\n');
       if (e_search_terms) {
           tmp.write('  <input type="hidden" name="e_search_terms" value="' + e_search_terms + '">\\n');
       }
       if (f_search_terms) {
           tmp.write('  <input type="hidden" name="f_search_terms" value="' + f_search_terms + '">\\n');
       }
       tmp.write('  <input type="hidden" name="log_filename" value="' + log_filename + '">\\n');
       tmp.write('  </form>\\n');
       tmp.write(' </body>\\n');
       tmp.write('</html>\\n');
       tmp.close();
       newwindow.focus();
    }

    -->
    </script>
  </head>
  <body bgcolor="#FFFFEE" onload="set_inner_html('log', 'init');">
    <table width="100%" border="0" cellpadding="0" cellspacing="0">
      <tr bgcolor="#BBCCFF">
        <td><table border="0" cellpadding="3" cellspacing="0"><tr>
          <td><b><font class="large2" size="+2">&nbsp; Alignment Visualization</font></b></td>
          <td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td>
          <td><table border="0" style="font-size:-1;">
                <tr><td>""" + e_lang_name + """ &ndash; """ + f_lang_name + """</td></tr>
                <tr><td>""" + date + """</td></tr></table></td>
          <td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td>
          <td>""" + cgi_box + """</td>
          <td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td>
          <td><table border="0" style="color:#777777;font-size:-1;">
                <tr><td>Script ualign.py version 0.0.8</td></tr>
                <tr><td>By Ulf Hermjakob, USC/ISI</td></tr></table></td>
      </tr>
    </table></td></tr></table><p>
""")
# Log: <span id="log"></span><p>


def html_head(title: str, date: str, meta_title: str) -> str:
    return f"""<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
        <title>{meta_title}</title>
            <style>""" + """
          [patitle]:hover:after {opacity: 1; transition: all 0.05s ease 0.1s; visibility: visible;}
          [patitle]:after {
            content: attr(patitle);
                position: absolute;
                bottom: 1.4em;
                left: -9px;
                padding: 5px 10px 5px 10px;
                color: #000;
                font-weight: normal;
                white-space: wrap;
                -moz-border-radius: 5px;
                -webkit-border-radius: 5px;
                border-radius: 5px;
                -moz-box-shadow: 0px 0px 4px #222;
                -webkit-box-shadow: 0px 0px 4px #222;
                box-shadow: 0px 0px 4px #222;
                font-size: 100%;
                background-color: #E0E7FF;
                opacity: 0;
                z-index: 99999;
                visibility: hidden;}
              [patitle] {position: relative; }
              [pbtitle]:hover:after {opacity: 1; transition: all 0.05s ease 0.1s; visibility: visible;}
              [pbtitle]:after {
            content: attr(pbtitle);
                position: absolute;
                top: 1.4em;
                left: -9px;
                padding: 5px 10px 5px 10px;
                color: #000;
                font-weight: normal;
                white-space: wrap;
                -moz-border-radius: 5px;
                -webkit-border-radius: 5px;
                border-radius: 5px;
                -moz-box-shadow: 0px 0px 4px #222;
                -webkit-box-shadow: 0px 0px 4px #222;
                box-shadow: 0px 0px 4px #222;
                font-size: 100%;
                background-color: #FFE0E7;
                opacity: 0;
                z-index: 99999;
                visibility: hidden;}
              [pbtitle] {position: relative; }
            </style>
        <script type="text/javascript">
        <!--
        function toggle_info(j) {
            if ((s = document.getElementById(j)) != null) {
                if (s.style.display == 'inline') {
                    s.style.display = 'none';
                } else {
                    s.style.display = 'inline';
                }
            }
        }
        -->""" + f"""
        </script>
    </head>
    <body bgcolor="#FFFFEE">
        <table width="100%" border="0" cellpadding="0" cellspacing="0">
            <tr bgcolor="#BBCCFF">
                <td><table border="0" cellpadding="3" cellspacing="0">
                        <tr>
                            <td><b><font class="large" size="+1">&nbsp; {title}</font></b></td>
                            <td>&nbsp;&nbsp;&nbsp;{date}&nbsp;&nbsp;&nbsp;</td>
                            <td style="color:#777777;font-size:80%;">Script &nbsp;
                                                                    by Ulf Hermjakob</td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table><p>
"""


def print_html_foot(f_html):
    f_html.write('''
  </body>
</html>
''')


def lang_to_langcode(lang: str) -> str:
    d = {'English': 'eng', 'German': 'deu', 'Russian': 'rus', 'Ukrainian': 'ukr',
         'Hindi': 'hin', 'Kolami': 'kfb', 'Haira': 'hry', 'Kukna': 'kex', 'Varli': 'vav',
         'Limbu': 'lif',
         'Cebuao': 'ceb', 'Lao': 'lao'}
    inv_d = {v: k for k, v in d.items()}
    return d.get(lang, None) or inv_d.get(lang, None)


def main():
    vm = VerboseManager()
    html_root_dir = Path(__file__).parent.parent / "html"
    # sys.stderr.write(f'F: {Path(__file__)} P: {Path(__file__).parent} root: {html_root_dir}\n')
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--text_filename', type=Path, help='format: e ||| f ||| ref')
    parser.add_argument('-a', '--in_align_filename', type=Path, help='format: Pharaoh (e.g. 0-0 1-2 2-1 3-3)')
    parser.add_argument('-i', '--in_model_filename', type=Path, help='input model file (incl. ttables)')
    parser.add_argument('-r', '--f_romanization_filename', type=Path, help='format: f || uroman')
    parser.add_argument('-q', '--e_romanization_filename', type=Path, help='format: e || uroman')
    parser.add_argument('-v', '--html_filename_dir', type=str, help='visualization output')
    parser.add_argument('-o', '--out_model_filename', type=Path, help='output model file (incl. ttables)')
    parser.add_argument('-z', '--out_align_filename', type=Path, help='format: Pharaoh (e.g. 0-0 1-2 2-1 3-3)')
    parser.add_argument('-l', '--log_filename', type=str, help='output')
    parser.add_argument('-b', '--battery_filename', type=Path, help='battery of tests output file (json)')
    parser.add_argument('-m', '--affix_morph_variant_check_filename', type=Path)
    parser.add_argument('-e', '--e_lang_name', type=str)
    parser.add_argument('-f', '--f_lang_name', type=str)
    parser.add_argument('-n', '--max_number_output_snt', type=int)
    parser.add_argument('-s', '--skip_modules', type=str)
    parser.add_argument('-p', '--profile', type=argparse.FileType('w', encoding='utf-8', errors='ignore'),
                        default=None, metavar='PROFILE-FILENAME', help='(optional output for performance analysis)')
    parser.add_argument('-c', '--cost', type=argparse.FileType('r', encoding='utf-8', errors='ignore'),
                        default=None, metavar='COST-FILENAME', help='(default: Levenshtein distance)')
    args = parser.parse_args()
    if args.log_filename:
        f_log = open(args.log_filename, 'w')
    else:
        f_log = None
    if pr := cProfile.Profile() if args.profile else None:
        pr.enable()
    e_lang_code = lang_to_langcode(args.e_lang_name)
    f_lang_code = lang_to_langcode(args.f_lang_name)
    sd = None
    spc = None
    if args.cost:
        sd = SmartEditDistance()
        sd.load_smart_edit_distance_data(args.cost, e_lang_code, f_lang_code)
        spc = SpellChecker()
        spc.read_battery_file(args.battery_filename)
    else:
        sys.stderr.write('No smart-edit-distance cost file provided.\n')
    e_am = AlignmentModel('e AlignmentModel', e_lang_code)
    f_am = AlignmentModel('f AlignmentModel', f_lang_code)
    affix_morph_variant_check_dict = defaultdict(list)
    if args.affix_morph_variant_check_filename:
        AffixMorphVariantCheck.read_file(args.affix_morph_variant_check_filename, affix_morph_variant_check_dict)
        e_am.affix_morph_variant_check_dict = affix_morph_variant_check_dict
        f_am.affix_morph_variant_check_dict = affix_morph_variant_check_dict
    skip_modules = regex.split(r',\s*', args.skip_modules) if args.skip_modules else []
    # sys.stderr.write(f'skip_modules: {skip_modules}\n')
    if args.in_model_filename:
        sys.stderr.write(f'Loading alignment model ...\n')
        e_am.load_alignment_model1(f_am, args.in_model_filename, sys.stderr)
    else:
        sys.stderr.write(f'Building alignment model ...\n')
        e_am.build_counts(f_am, args.text_filename, args.in_align_filename)
        f_am.build_glosses(e_am)
        e_am.build_glosses(f_am)
        e_am.find_function_words('e', f_log, vm)
        f_am.find_function_words('f', f_log, vm)
        e_am.morph_clustering(f_am, 'e', 'f', f_log, vm)
    # sys.stderr.write(f'e-total: {e_am.total_count} f-total: {f_am.total_count}\n')
    if args.f_romanization_filename:
        f_am.load_romanization(args.f_romanization_filename, sys.stderr)
    if args.e_romanization_filename:
        e_am.load_romanization(args.e_romanization_filename, sys.stderr)
    if args.html_filename_dir:
        if args.html_filename_dir.startswith('/'):
            full_html_filename_dir = Path(args.html_filename_dir)
        else:
            full_html_filename_dir = html_root_dir / args.html_filename_dir
        if str(args.text_filename).startswith('/'):
            full_text_filename = Path(args.text_filename)
        else:
            full_text_filename = Path(os.getcwd()) / args.text_filename
        if args.log_filename is None:
            full_prop_filename = None
        elif args.log_filename.startswith('/'):
            full_prop_filename = Path(args.log_filename)
        else:
            full_prop_filename = Path(os.getcwd()) / args.log_filename
        if not os.path.exists(full_html_filename_dir):
            os.makedirs(full_html_filename_dir)
            sys.stderr.write(f'Created dir {full_html_filename_dir} for alignment viz.\n')
        if full_html_filename_dir.is_dir():
            e_am.process_alignments(f_am, full_text_filename, args.in_align_filename, args.out_align_filename,
                                    full_html_filename_dir, args.max_number_output_snt, args.e_lang_name,
                                    args.f_lang_name, f_log, skip_modules, vm, full_prop_filename, sd, spc)
        else:
            sys.stderr.write(f'Error: invalid html directory {args.html_filename_dir} -> {full_html_filename_dir}\n')
    if args.in_model_filename:
        sys.stderr.write(f'Rebuilding alignment model ...\n')
        e_am.build_glosses(f_am)
        f_am.build_glosses(e_am)
        e_am.find_function_words('e', f_log, vm)
        f_am.find_function_words('f', f_log, vm)
        e_am.morph_clustering(f_am, 'e', 'f', f_log, vm)
    if args.out_model_filename:
        e_am.build_weights_with_context(f_am)
        sys.stderr.write(f'Writing model to {args.out_model_filename}\n')
        e_am.write_alignment_model(f_am, args.out_model_filename, sys.stderr)
    if spc:
        spc.build_alignment_based_spelling_variations('e', e_am, f_am, sd)
        spc.build_alignment_based_spelling_variations('f', f_am, e_am, sd)
        spc.report(args.battery_filename, e_am, f_am, sd)
    if pr:
        pr.disable()
        ps = pstats.Stats(pr, stream=args.profile).sort_stats(pstats.SortKey.TIME)
        ps.print_stats()
    if f_log:
        sys.stderr.write(f'Log: {args.log_filename}\n')
        f_log.close()


if __name__ == "__main__":
    main()

#!/usr/bin/env python
# cd /Users/ulf/projects/NLP/fast_align/data
# /Users/ulf/projects/NLP/greek-room/utilities/viz-simple-alignments.py -t en-NRSV_de-LU84NR06_ref.txt
# -a en-NRSV_de-LU84NR06.align_lc -v eng-deu -o en-NRSV_de-LU84NR06_lc.i1.a -l log-deu.txt

import argparse
from collections import defaultdict
import copy
import cProfile
import datetime
import math
import os
from pathlib import Path
import pstats
import regex
import sys
from typing import Optional, TextIO


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
        self.log_stem_probs = False
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


class AlignmentModel:
    """Captures word counts, translation word counts etc. One AlignmentModel per direction (e.g. e/e_f; f/f_e)."""
    def __init__(self, name: str):
        self.counts = defaultdict(int)
        self.total_count = 0
        self.avg_total_count = 0
        self.aligned_words = defaultdict(set)
        self.bi_counts = defaultdict(int)
        self.bi_weighted_counts = defaultdict(float)
        self.glosses = defaultdict(str)
        self.fertilities = defaultdict(list)
        self.discontinuities = defaultdict(int)
        self.support_probabilities = {}  # for caching, index: (rev, self.token, rev.token)
        self.romanization = {}
        self.name = name
        self.sub_counts = defaultdict(int)
        self.sub_bi_weighted_counts = defaultdict(float)
        self.sub_aligned_words = defaultdict(set[str])
        self.function_word_scores = defaultdict(float)
        self.aligned_stems = defaultdict(set)
        self.bi_weighted_stem_counts = defaultdict(float)
        self.stem_counts = defaultdict(int)
        self.alignment_context = defaultdict(int)

    def load_romanization(self, filename: str, stderr: Optional[TextIO]):
        """"""
        line_number = 0
        n_entries = 0
        with open(filename) as f_rom:
            for line in f_rom:
                line_number += 1
                if m2 := regex.match(r'\s*(\S.*\S|\S)\s+\|\|\|\s+(\S.*\S|\S)\s*$', line):
                    self.romanization[m2.group(1)] = m2.group(2)
                    n_entries += 1
        if stderr:
            stderr.write(f'load_romanization: {n_entries} entries in {line_number} lines.\n')

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
                    self.counts[e] = float(count) if '.' in count else int(count)
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
                    rev.counts[f] = float(count) if '.' in count else int(count)
                    if f != 'NULL':
                        rev.total_count += rev.counts[f]
                    n_entries += 1
                elif line.startswith('::efc '):
                    e, f, weighted_count, count = regex.split(' {2,}', slot_value_in_double_colon_del_list(line, 'efc'))
                    self.aligned_words[e].add(f)
                    self.bi_weighted_counts[(e, f)] = float(weighted_count) \
                        if '.' in weighted_count else int(weighted_count)
                    self.bi_counts[(e, f)] = int(count)
                    if gloss := slot_value_in_double_colon_del_list(line, 'gloss'):
                        self.glosses[f] = gloss
                    n_entries += 1
                elif line.startswith('::fec '):
                    f, e, weighted_count, count = regex.split(' {2,}', slot_value_in_double_colon_del_list(line, 'fec'))
                    rev.aligned_words[f].add(e)
                    rev.bi_weighted_counts[(f, e)] = float(weighted_count) \
                        if '.' in weighted_count else int(weighted_count)
                    rev.bi_counts[(f, e)] = int(count)
                    n_entries += 1
                elif line.startswith('::efsc '):
                    e, fs, weighted_stem_count = regex.split(' {2,}', slot_value_in_double_colon_del_list(line, 'efsc'))
                    self.aligned_stems[e].add(fs)
                    self.bi_weighted_stem_counts[(e, fs)] = float(weighted_stem_count) \
                        if '.' in weighted_stem_count else int(weighted_stem_count)
                elif line.startswith('::fesc'):
                    f, es, weighted_stem_count = regex.split(' {2,}', slot_value_in_double_colon_del_list(line, 'fesc'))
                    rev.aligned_stems[f].add(es)
                    rev.bi_weighted_stem_counts[(f, es)] = float(weighted_stem_count) \
                        if '.' in weighted_stem_count else int(weighted_stem_count)
                elif line.startswith('::es'):
                    es = slot_value_in_double_colon_del_list(line, 'es')
                    count = slot_value_in_double_colon_del_list(line, 'count')
                    self.stem_counts[es] = float(count) if '.' in count else int(count)
                elif line.startswith('::fs'):
                    fs = slot_value_in_double_colon_del_list(line, 'fs')
                    count = slot_value_in_double_colon_del_list(line, 'count')
                    rev.stem_counts[fs] = float(count) if '.' in count else int(count)
        self.avg_total_count = (self.total_count + rev.total_count) / 2
        rev.avg_total_count = self.avg_total_count
        if stderr:
            stderr.write(f'load_alignment_model1: {n_entries} entries in {line_number} lines. '
                         f'total_e: {self.total_count} total_f: {rev.total_count} total: {self.avg_total_count}\n')

    def write_alignment_model(self, rev, filename: str, _stderr: Optional[TextIO]):
        with open(filename, 'w') as out:
            out.write(f'# Alignment model (by script viz-simple-alignment.py)\n')
            for side in ['e', 'f']:
                am = self if side == 'e' else rev
                other_side = 'f' if side == 'e' else 'e'
                for a in sorted(am.counts.keys(), key=str.casefold):
                    count = am.counts[a]
                    fertility_list = am.fertilities[a]
                    gloss = am.glosses[a]
                    discontinuity = am.discontinuities.get(a, 0)
                    romanization = am.romanization.get(a)
                    function_word_score = am.function_word_scores[a]
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
                    aligned_stems = sorted(list(am.aligned_stems[a]),
                                           key=lambda k: (round(-1 * am.bi_weighted_stem_counts[(a, k)], 3),
                                                          k.casefold()))
                    for b in aligned_stems:
                        out.write(f"::{side}{other_side}sc {a}  {b}  {round(am.bi_weighted_stem_counts[(a, b)], 3)}\n")
                    aligned_words = sorted(list(am.aligned_words[a]),
                                           key=lambda k: (round(-1 * am.bi_weighted_counts[(a, k)], 3),
                                                          k.casefold()))
                    for b in aligned_words:
                        out.write(f"::{side}{other_side}c {a}  {b}  "
                                  f"{round(am.bi_weighted_counts[(a, b)], 3)}  {am.bi_counts[(a, b)]}\n")
                out.write('\n')
                for a in sorted(am.stem_counts.keys(), key=str.casefold):
                    count = am.stem_counts[a]
                    out.write(f"::{side}s {a} ::count {count}\n")
                out.write(f'\n::{side}-total-count {am.total_count}\n')

    def process_alignments(self, rev, text_filename: Path, in_align_filename: str, out_align_filename: Optional[str],
                           html_filename_dir: Path, max_number_output_snt: Optional[int],
                           e_lang_name: str, f_lang_name: str, f_log: TextIO, skip_modules: list[str],
                           vm: VerboseManager, prop_filename: Optional[Path]):
        viz_file_manager = VisualizationFileManager(e_lang_name, f_lang_name, html_filename_dir, text_filename,
                                                    prop_filename)
        line_number = 0
        n_outputs = 0
        if out_align_filename:
            f_out_align = open(out_align_filename, 'w')
        else:
            f_out_align = None
        with open(text_filename) as f_text, open(in_align_filename) as f_in_align:
            sys.stderr.write('Building alignment visualizations for')
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
                orig_sa = SentenceAlignment(e, f, align, self, rev, snt_id)
                orig_sa.derive_values(self, rev, snt_id)
                orig_sa.record_alignment_context(self, rev, snt_id)
                orig_sa_score = orig_sa.score()
                # if ref == "GEN 14:17":
                #     orig_sa.visualize_alignment(self, rev, snt_id, 'O1.'+ref, orig_sa_score, viz_file_manager.f_html)
                sa = None
                if 'delete_weak_remotes' not in skip_modules:
                    if sa is None:
                        sa = orig_sa.copy()
                    made_change = sa.delete_weak_remotes(f_log, vm) or made_change
                if 'markup_spurious' not in skip_modules:
                    if sa is None:
                        sa = orig_sa.copy()
                    made_change = sa.markup_spurious(f_log, vm) or made_change
                if 'markup_strong_unambiguous_links' not in skip_modules:
                    if sa is None:
                        sa = orig_sa.copy()
                    made_change = sa.markup_strong_unambiguous_links(self, rev, f_log, vm, snt_id) or made_change
                if made_change:
                    sa.derive_values(self, rev, snt_id)
                else:
                    sa, orig_sa = orig_sa, None
                sa_score = sa.score(eval_stats=viz_file_manager.eval_stats)
                sa.visualize_alignment(self, rev, snt_id, ref or line_number, sa_score, viz_file_manager.f_html,
                                       orig_sa=orig_sa, orig_sa_score=orig_sa_score)
                n_outputs += 1
                if f_out_align:
                    sa.output_alignment(f_out_align)
            viz_file_manager.finish_visualization_file(True)
        self.print_alignment_context_model()
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
                    e, f, _ref = m3.group(1, 2, 3)
                elif m2 := regex.match(r'(\S|\S.*?\S)\s+\|\|\|\s+(\S|\S.*?\S)\s*$', text):
                    e, f = m2.group(1, 2)
                    _ref = None
                else:
                    continue
                if lower_case_tokens_p:
                    e = e.lower()
                    f = f.lower()
                e_tokens, f_tokens = e.split(), f.split()
                for e_token in e_tokens:
                    self.counts[e_token] += 1
                    self.total_count += 1
                for f_token in f_tokens:
                    rev.counts[f_token] += 1
                    rev.total_count += 1
                alignments = regex.findall(r'(\d+)-(\d+)', align)
                e_pos_in_snt_count, f_pos_in_snt_count = defaultdict(int), defaultdict(int)
                e_pos_in_snt_list, f_pos_in_snt_list = defaultdict(list), defaultdict(list)
                for alignment in alignments:
                    e_pos, f_pos = int(alignment[0]), int(alignment[1])
                    e_pos_in_snt_count[e_pos] += 1
                    f_pos_in_snt_count[f_pos] += 1
                    e_pos_in_snt_list[e_pos].append(f_pos)
                    f_pos_in_snt_list[f_pos].append(e_pos)
                for e_pos, e_token in enumerate(e_tokens):
                    fertility = e_pos_in_snt_count[e_pos]
                    fertility_count_list = self.fertilities[e_token]
                    if len(fertility_count_list) <= fertility:
                        fertility_count_list.extend([0] * (fertility + 1 - len(fertility_count_list)))
                    fertility_count_list[fertility] += 1
                    if fertility == 0:
                        self.aligned_words[e_token].add('NULL')
                        self.bi_counts[(e_token, 'NULL')] += 1
                        self.bi_weighted_counts[(e_token, 'NULL')] += 1
                        rev.counts['NULL'] += 1
                        rev.aligned_words['NULL'].add(e_token)
                        rev.bi_counts[('NULL', e_token)] += 1
                        rev.bi_weighted_counts[('NULL', e_token)] += 1
                    if f_pos_list := sorted(e_pos_in_snt_list[e_pos]):
                        prev_f_pos = f_pos_list[0] - 1
                        for f_pos in f_pos_list:
                            if prev_f_pos + 1 != f_pos:
                                self.discontinuities[e_token] += 1
                            prev_f_pos = f_pos
                for f_pos, f_token in enumerate(f_tokens):
                    fertility = f_pos_in_snt_count[f_pos]
                    fertility_count_list = rev.fertilities[f_token]
                    if len(fertility_count_list) <= fertility:
                        fertility_count_list.extend([0] * (fertility + 1 - len(fertility_count_list)))
                    fertility_count_list[fertility] += 1
                    if fertility == 0:
                        rev.aligned_words[f_token].add('NULL')
                        rev.bi_counts[(f_token, 'NULL')] += 1
                        rev.bi_weighted_counts[(f_token, 'NULL')] += 1
                        self.counts['NULL'] += 1
                        self.aligned_words['NULL'].add(f_token)
                        self.bi_counts[('NULL', f_token)] += 1
                        self.bi_weighted_counts[('NULL', f_token)] += 1
                    if e_pos_list := sorted(f_pos_in_snt_list[f_pos]):
                        prev_e_pos = e_pos_list[0] - 1
                        for e_pos in e_pos_list:
                            if prev_e_pos + 1 != e_pos:
                                rev.discontinuities[f_token] += 1
                            prev_e_pos = e_pos
                for alignment in alignments:
                    e_pos, f_pos = int(alignment[0]), int(alignment[1])
                    # sys.stderr.write(f'   {e_pos}/{len(e_tokens)} {f_pos}/{len(f_tokens)}\n')
                    e_token, f_token = e_tokens[e_pos], f_tokens[f_pos]
                    self.bi_counts[(e_token, f_token)] += 1
                    rev.bi_counts[(f_token, e_token)] += 1
                    self.bi_weighted_counts[(e_token, f_token)] += 1 / e_pos_in_snt_count[e_pos]
                    rev.bi_weighted_counts[(f_token, e_token)] += 1 / f_pos_in_snt_count[f_pos]
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

    def morph_clustering(self, rev, slot_prefix: str, f_out: Optional[TextIO], vm: VerboseManager):
        # HHHHERE a=könig...  b=king
        rev.aligned_stems.clear()
        rev.bi_weighted_stem_counts.clear()
        self.stem_counts.clear()
        for a in self.counts.keys():
            count = self.counts[a]
            a2 = ' ' + a + ' '
            for start_pos in range(len(a2)-2):
                for end_pos in range(max(start_pos+2, 3), len(a2) + 1):
                    sub_word = a2[start_pos:end_pos]
                    self.sub_counts[sub_word] += count
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

    def support_probability(self, rev, a_token: str, b_token: str, _snt_id: Optional[str])\
            -> float:
        sp = self.support_probabilities.get((rev, a_token, b_token), None)
        if sp is None:
            b_count = rev.counts[b_token] - 1
            joint_count = self.bi_counts[(a_token, b_token)] - 1
            sp = joint_count / b_count if b_count else 0.01
            self.support_probabilities[(rev, a_token, b_token)] = sp
        return sp

    def print_alignment_context_model(self):
        e1, f1, e_rp1, f_rp1 = '', '', 0, 0
        sys.stderr.write('\n')
        for record in sorted(self.alignment_context.keys()):
            e, f, e_rp, f_rp = record
            count = self.alignment_context[record]
            if count >= 10:
                if (e != e1) or (f != f1) or (e_rp != e_rp1):
                    sys.stderr.write(f'\nACM: {e} {f} {e_rp}')
                sys.stderr.write(f' {f_rp}:{count}')
                e1, f1, e_rp1, f_rp1 = e, f, e_rp, f_rp
        sys.stderr.write('\n')


class SentenceAlignment:
    """For one sentence pair. align: '0-1 1-3 2-0 3-3'"""
    def __init__(self, e: str, f: str, align: str, e_am: AlignmentModel, f_am: AlignmentModel, snt_id: Optional[str]):
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
        self.best_count_for_e = defaultdict(int)
        self.best_count_for_f = defaultdict(int)
        self.e_is_contiguous = defaultdict(bool)
        self.f_is_contiguous = defaultdict(bool)
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

    def a_is_contiguous(self, side):
        return self.e_is_contiguous if side == 'e' else self.f_is_contiguous

    def b_is_contiguous(self, side):
        return self.f_is_contiguous if side == 'e' else self.e_is_contiguous

    def copy(self):
        sa_copy = SentenceAlignment(self.e, self.f, '', self.e_am, self.f_am, self.snt_id)
        sa_copy.e_tokens = self.e_tokens.copy()
        sa_copy.f_tokens = self.f_tokens.copy()
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
        sa_copy.e_is_contiguous = self.e_is_contiguous.copy()
        sa_copy.f_is_contiguous = self.f_is_contiguous.copy()
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

    def score(self, eval_stats: Optional[EvaluationStats] = None,
              e_exclude_pos: Optional[list] = None, f_exclude_pos: Optional[list] = None):
        verbose = (self.snt_id == 'ABC 1:1')
        if verbose:
            sys.stderr.write(f'\nScore -e:{e_exclude_pos} -f:{f_exclude_pos}\n')
        score_sum, weight_sum = 0.0, 0.0  # over both side
        for side in ('e', 'f'):
            a_exclude_pos = e_exclude_pos if side == 'e' else f_exclude_pos
            for a_pos, lc_a_token in enumerate(self.lc_a_tokens(side)):
                if self.a_exclusion_pos_list(side)[a_pos] or (a_exclude_pos and a_pos in a_exclude_pos):
                    continue
                a_fw_weight = self.a_fw_weights(side)[a_pos]
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
                                                                                  lc_b_token, self.snt_id)
                        sub_score += support_probability * a_fw_weight * b_fw_weight / b_fw_sum
                else:
                    support_probability = self.a_am(side).support_probability(self.b_am(side), lc_a_token, 'NULL',
                                                                              self.snt_id)
                    sub_score = support_probability * a_fw_weight
                score_sum += sub_score
                if verbose:
                    sys.stderr.write(f'Score {side} {self.snt_id} {a_pos} {lc_a_token} w:{round(a_fw_weight, 3)} '
                                     f's:{round(sub_score, 3)}\n')
        score = score_sum / weight_sum if weight_sum else None
        if eval_stats:
            eval_stats.add_score(score_sum, weight_sum, self.snt_id)
        if verbose:
            sys.stderr.write(f'Return score {score}\n\n')
        return score

    def derive_values(self, e_am: AlignmentModel, f_am: AlignmentModel, snt_id: Optional[str]):
        self.e_fw_weights = []
        self.e_fw_weight_sum = 0.0
        for e_pos, lc_e_token in enumerate(self.lc_e_tokens):
            best_support_probability = None
            best_count = None
            alignments_are_contiguous = True
            f_pos_list = sorted(self.e_f_pos_list[e_pos])
            if f_pos_list:
                prev_f_pos = f_pos_list[0] - 1
                for f_pos in f_pos_list:
                    if prev_f_pos + 1 != f_pos:
                        alignments_are_contiguous = False
                    lc_f_token = self.lc_f_tokens[f_pos]
                    support_probability = e_am.support_probability(f_am, lc_e_token, lc_f_token, snt_id)
                    if best_support_probability is None or support_probability > best_support_probability:
                        best_support_probability = support_probability
                        best_count = e_am.bi_counts[(lc_e_token, lc_f_token)]
                    prev_f_pos = f_pos
            self.best_support_probability_for_e[e_pos] = best_support_probability
            self.best_count_for_e[e_pos] = best_count
            self.e_is_contiguous[e_pos] = alignments_are_contiguous
            e_fw_score = self.e_am.function_word_scores[lc_e_token]
            e_fw_weight = (1 - e_fw_score * 0.9)
            self.e_fw_weights.append(e_fw_weight)
            self.e_fw_weight_sum += e_fw_weight
        self.f_fw_weights = []
        self.f_fw_weight_sum = 0.0
        for f_pos, lc_f_token in enumerate(self.lc_f_tokens):
            best_support_probability = None
            best_count = None
            alignments_are_contiguous = True
            e_pos_list = sorted(self.f_e_pos_list[f_pos])
            if e_pos_list:
                prev_e_pos = e_pos_list[0] - 1
                for e_pos in e_pos_list:
                    if prev_e_pos + 1 != e_pos:
                        alignments_are_contiguous = False
                    lc_e_token = self.lc_e_tokens[e_pos]
                    support_probability = f_am.support_probability(e_am, lc_f_token, lc_e_token, snt_id)
                    if best_support_probability is None or support_probability > best_support_probability:
                        best_support_probability = support_probability
                        best_count = f_am.bi_counts[(lc_f_token, lc_e_token)]
                    prev_e_pos = e_pos
            self.best_support_probability_for_f[f_pos] = best_support_probability
            self.best_count_for_f[f_pos] = best_count
            self.f_is_contiguous[f_pos] = alignments_are_contiguous
            f_fw_score = self.f_am.function_word_scores[lc_f_token]
            f_fw_weight = (1 - f_fw_score * 0.9)
            self.f_fw_weights.append(f_fw_weight)
            self.f_fw_weight_sum += f_fw_weight
        self.build_alignment_candidates(e_am, f_am, snt_id)

    def record_alignment_context(self, e_am: AlignmentModel, _f_am: AlignmentModel, _snt_id: Optional[str]):
        for e_pos, lc_e_token in enumerate(self.lc_e_tokens):
            if lc_e_token not in ('and', 'from', 'of'):
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

    def title(self, side: str, pos: int, am: AlignmentModel, rev_am: AlignmentModel, snt_id: Optional[str],
              orig_sa=None) -> Optional[str]:
        if side == 'e':
            lc_token = self.lc_e_tokens[pos]
            b_pos_list = self.e_f_pos_list[pos]
            orig_b_pos_list = orig_sa.e_f_pos_list[pos] if orig_sa else []
            lc_b_tokens = self.lc_f_tokens
            a_am, b_am = am, rev_am
            exclusion_pos_list = self.e_exclusion_pos_list
            b_candidates = self.e_f_candidates[pos]
        elif side == 'f':
            lc_token = self.lc_f_tokens[pos]
            b_pos_list = self.f_e_pos_list[pos]
            orig_b_pos_list = orig_sa.f_e_pos_list[pos] if orig_sa else []
            lc_b_tokens = self.lc_e_tokens
            a_am, b_am = rev_am, am
            exclusion_pos_list = self.f_exclusion_pos_list
            b_candidates = self.f_e_candidates[pos]
        else:
            return None
        title = lc_token.strip('@')
        title += f' [{pos}]'
        if romanization := a_am.romanization.get(lc_token):
            title += f' &nbsp; rom:{romanization}'
        if count := a_am.counts[lc_token]:
            title += f' &nbsp; c:{count - 1}'
        if gloss := a_am.glosses[lc_token]:
            title += f' &nbsp; gloss: {gloss}'
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
                    a_b_support_probability = a_am.support_probability(b_am, lc_token, lc_b_token, snt_id)
                    b_a_support_probability = b_am.support_probability(a_am, lc_b_token, lc_token, snt_id)
                    joint_count = a_am.bi_counts[(lc_token, lc_b_token)] - 1
                    title += "&#xA;"
                    title += "Deleted: &nbsp;" if comp_note == 'deleted' else "&mdash;"
                    title += f" {lc_b_token.strip('@')} [{b_pos}]" \
                             f' &nbsp; c:{b_count}' \
                             f' &nbsp; p:{round(b_a_support_probability, 3)}/{round(a_b_support_probability, 3)}' \
                             f' &nbsp; jc:{joint_count}'
                    if comp_note == 'added':
                        title += ' &nbsp; (added)'
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
                a_b_support_probability = a_am.support_probability(b_am, lc_token, lc_b_token, snt_id)
                if a_b_support_probability < 0.01:
                    continue
                b_a_support_probability = b_am.support_probability(a_am, lc_b_token, lc_token, snt_id)
                if b_a_support_probability < 0.01:
                    continue
                if a_b_support_probability <= 0.05 and b_a_support_probability <= 0.05:
                    continue
                joint_count = a_am.bi_counts[(lc_token, lc_b_token)] - 1
                if joint_count < 4:
                    continue
                title += "&#xA;Candidate: &nbsp;"
                title += f" {lc_b_token.strip('@')} [{b_pos}]" \
                         f' &nbsp; c:{b_count}' \
                         f' &nbsp; p:{round(b_a_support_probability, 3)}/{round(a_b_support_probability, 3)}' \
                         f' &nbsp; jc:{joint_count}'
        title = title.replace(' ', '&nbsp;').replace('&#xA;', ' ')
        return title

    def decoration(self, side: str, pos: int, e_am: AlignmentModel, f_am: AlignmentModel, _snt_id: Optional[str],
                   mouseover_action_s):
        text_decoration = None
        alignment_changed = "'1+'" in mouseover_action_s or "'1-'" in mouseover_action_s
        if side == 'e':
            best_support = self.best_support_probability_for_e[pos]
            best_count = self.best_count_for_e[pos]
            alignments_are_contiguous = self.e_is_contiguous[pos]
            am = e_am
            lc_tokens = self.lc_e_tokens
            exclusion_pos_list = self.e_exclusion_pos_list
        elif side == 'f':
            best_support = self.best_support_probability_for_f[pos]
            best_count = self.best_count_for_f[pos]
            alignments_are_contiguous = self.f_is_contiguous[pos]
            am = f_am
            lc_tokens = self.lc_f_tokens
            exclusion_pos_list = self.f_exclusion_pos_list
        else:
            return None
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
        open_delimiter_stack = []
        for f_pos, f_token in enumerate(self.f_tokens):
            if f_token in '([':
                open_delimiter_stack.append((f_token, f_pos))
            elif open_delimiter_stack and self.delimiter_open_close_match(open_delimiter_stack[-1][0], f_token):
                start_pos, end_pos = open_delimiter_stack[-1][1], f_pos
                del open_delimiter_stack[-1]
                if not self.span_has_strong_link_to_other_side('f', start_pos, end_pos):
                    surf = ' '.join(self.f_tokens[start_pos:end_pos+1])
                    if score_full is None:
                        score_full = self.score()
                    score_core = self.score(f_exclude_pos=list(range(start_pos, end_pos+1)))
                    score_spurious = self.score(e_exclude_pos=list(range(len(self.e_tokens))),
                                                f_exclude_pos=list(range(0, start_pos))
                                                + list(range(end_pos+1, len(self.f_tokens))))
                    conf_class = self.markup_confidence_class(score_full, score_core, score_spurious, surf)
                    if vm.log_alignment_diff_details is not None:
                        vm.log_alignment_diff_details[('F', self.snt_id)].append(conf_class)
                        f_log.write(f'::diff spurious ::snt-id {self.snt_id} '
                                    f'::side F ::range {start_pos}-{end_pos} ::surf {surf} '
                                    f'::f {round(score_full, 3)} ::c {round(score_core, 3)} '
                                    f'::s {round(score_spurious, 3)} '
                                    f'::class {conf_class}\n')
                    if conf_class.startswith('+'):
                        for f_pos2 in range(start_pos, end_pos+1):
                            self.f_exclusion_pos_list[f_pos2] = True
                            for e_pos2 in self.f_e_pos_list[f_pos2]:
                                self.e_f_pos_list[e_pos2].remove(f_pos2)
                                self.f_e_pos_list[f_pos2] = []
                        made_change = True
        open_delimiter_stack = []
        for e_pos, e_token in enumerate(self.e_tokens):
            if e_token in '([':
                open_delimiter_stack.append((e_token, e_pos))
            elif open_delimiter_stack and self.delimiter_open_close_match(open_delimiter_stack[-1][0], e_token):
                start_pos, end_pos = open_delimiter_stack[-1][1], e_pos
                del open_delimiter_stack[-1]
                if not self.span_has_strong_link_to_other_side('e', start_pos, end_pos):
                    surf = ' '.join(self.e_tokens[start_pos:end_pos+1])
                    if score_full is None:
                        score_full = self.score()
                    score_core = self.score(e_exclude_pos=list(range(start_pos, end_pos+1)))
                    score_spurious = self.score(f_exclude_pos=list(range(len(self.f_tokens))),
                                                e_exclude_pos=list(range(0, start_pos))
                                                + list(range(end_pos+1, len(self.e_tokens))))
                    conf_class = self.markup_confidence_class(score_full, score_core, score_spurious, surf)
                    if vm.log_alignment_diff_details is not None:
                        vm.log_alignment_diff_details[('E', self.snt_id)].append(conf_class)
                        f_log.write(f'::diff spurious ::snt-id {self.snt_id} '
                                    f'::side E ::range {start_pos}-{end_pos} ::surf {surf} '
                                    f'::f {round(score_full, 3)} ::c {round(score_core, 3)} '
                                    f'::s {round(score_spurious, 3)} '
                                    f'::class {conf_class}\n')
                    if conf_class.startswith('+'):
                        for e_pos2 in range(start_pos, end_pos+1):
                            self.e_exclusion_pos_list[e_pos2] = True
                            for f_pos2 in self.e_f_pos_list[e_pos2]:
                                self.f_e_pos_list[f_pos2].remove(e_pos2)
                                self.e_f_pos_list[e_pos2] = []
                        made_change = True
        return made_change

    def delete_weak_remotes(self, f_log: TextIO, vm: VerboseManager):
        made_change = False
        for side in ('e', 'f'):
            for a_pos, lc_a_token in enumerate(self.lc_a_tokens(side)):
                if not self.a_is_contiguous(side)[a_pos]:
                    if not (b_candidates := self.a_b_candidates(side)[a_pos]):
                        continue
                    b_candidate_pos_list = [b_candidate[0] for b_candidate in b_candidates]
                    b_top_candidate = b_candidates[0]
                    b_top_pos, b_top_score = b_top_candidate[0], b_top_candidate[1]
                    if b_top_pos in self.a_b_pos_list(side)[a_pos]:
                        for b_pos in self.a_b_pos_list(side)[a_pos]:
                            if (abs(b_pos - b_top_pos) > 2) \
                                    and ((b_pos not in b_candidate_pos_list)
                                         or (b_candidates[b_candidate_pos_list.index(b_pos)][1] < b_top_score * 0.2)):
                                if vm.log_alignment_diff_details is not None:
                                    a_descr = f'{lc_a_token} [{a_pos}]'
                                    b_descr = f'{self.lc_b_tokens(side)[b_pos]} [{b_pos}]'
                                    f_log.write(f'::rm weak ::snt-id {self.snt_id} '
                                                f'::e {a_descr if side == "e" else b_descr} '
                                                f'::f {b_descr if side == "e" else a_descr}\n')
                                self.a_b_pos_list(side)[a_pos].remove(b_pos)
                                self.b_a_pos_list(side)[b_pos].remove(a_pos)
                                made_change = True
        return made_change

    def build_alignment_candidates(self, e_am, f_am, snt_id):
        self.e_f_candidates, self.f_e_candidates = defaultdict(list), defaultdict(list)
        for e_pos, lc_e_token in enumerate(self.lc_e_tokens):
            for f_pos, lc_f_token in enumerate(self.lc_f_tokens):
                if (e_f_count := e_am.bi_counts[(lc_e_token, lc_f_token)]) < 2:
                    continue
                e_f_prob = e_am.support_probability(f_am, lc_e_token, lc_f_token, snt_id)
                if e_f_prob < 0.01:
                    continue
                f_e_prob = f_am.support_probability(e_am, lc_f_token, lc_e_token, snt_id)
                if f_e_prob < 0.01:
                    continue
                score = e_f_prob * f_e_prob * (1-1/math.log(e_f_count, 2)) if e_f_count > 1 else 0.0
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

    def markup_strong_unambiguous_links(self, e_am, f_am, f_log: TextIO, vm: VerboseManager, _snt_id):
        # verbose = (self.snt_id == 'GEN 1:1')
        made_change = False
        for e_pos, lc_e_token in enumerate(self.lc_e_tokens):
            if self.e_exclusion_pos_list[e_pos]:
                continue
            if e_am.function_word_scores[lc_e_token]:
                continue
            if self.e_f_pos_list[e_pos]:  # e has current links to f
                continue
            if not (f_candidates := self.e_f_candidates[e_pos]):
                continue
            f_pos_list = self.e_f_pos_list[e_pos]
            f_new_candidates = [f_candidate for f_candidate in f_candidates if f_candidate[0] not in f_pos_list]
            if not f_new_candidates:
                continue
            if len(f_new_candidates) >= 2 and f_new_candidates[1][1] > f_new_candidates[0][1] * 0.5:  # close 2nd
                continue
            f_top_new_candidate = f_new_candidates[0]
            f_pos = f_top_new_candidate[0]
            if self.f_exclusion_pos_list[f_pos]:
                continue
            if self.f_e_pos_list[f_pos]:  # f has current links to e
                continue
            lc_f_token = self.lc_f_tokens[f_pos]
            if f_am.function_word_scores[lc_f_token]:
                continue
            e_f_prob, f_e_prob, e_f_count = f_top_new_candidate[2:5]
            if (e_f_prob < 0.1) or (f_e_prob < 0.1) or (e_f_count < 10):  # too weak
                continue
            e_new_candidates = [e_candidate for e_candidate in self.f_e_candidates[f_pos]
                                if e_candidate[0] not in self.f_e_pos_list[f_pos]]
            if len(e_new_candidates) >= 2 and e_new_candidates[1][1] > e_new_candidates[0][1] * 0.5:  # close 2nd
                continue
            self.e_f_pos_list[e_pos].append(f_pos)
            self.f_e_pos_list[f_pos].append(e_pos)
            lc_f_token = self.lc_f_tokens[f_pos]
            made_change = True
            if vm.log_alignment_diff_details is not None:
                f_log.write(f'::diff str-unamb-link ::snt-id {self.snt_id} '
                            f'::side E ::pos {e_pos}-{f_pos} ::surf {lc_e_token}-{lc_f_token} '
                            f'::pef {round(e_f_prob, 3)} ::pfe {round(f_e_prob, 3)} '
                            f'::class changed added strong unambiguous link\n')
        return made_change

    def visualize_alignment(self, e_am, f_am, snt_id: str, ref: str, sa_score: float, f_html: TextIO,
                            orig_sa=None, orig_sa_score: Optional[float] = None):
        ref2 = regex.sub(' ', '_', ref)
        f_html.write(f'<a name="{ref2}">\n')
        orig_score_clause = '' if orig_sa_score is None or orig_sa_score == sa_score \
            else f'{round(orig_sa_score, 3)} &rarr; '
        f_html.write(f'<b>{ref}</b> &nbsp; &nbsp; Alignment score: {orig_score_clause}{round(sa_score, 3)}'
                     f'<br>\n')
        for e_pos, e_token in enumerate(self.e_tokens):
            e_span_id = f'{ref2}-e{e_pos}'
            mouseover_action_s = f"h('{e_span_id}','1');"
            mouseout_action_s = f"h('{e_span_id}','0');"
            f_pos_list = self.e_f_pos_list[e_pos]
            orig_f_pos_list = orig_sa.e_f_pos_list[e_pos] if orig_sa else f_pos_list
            for f_pos in f_pos_list:
                f_span_id = f'{ref2}-f{f_pos}'
                if f_pos in orig_f_pos_list:
                    mouseover_action_s += f"h('{f_span_id}','1');"
                else:
                    mouseover_action_s += f"h('{f_span_id}','1+');"
                mouseout_action_s += f"h('{f_span_id}','0');"
            for f_pos in orig_f_pos_list:
                if f_pos not in f_pos_list:
                    f_span_id = f'{ref2}-f{f_pos}'
                    mouseover_action_s += f"h('{f_span_id}','1-');"
                    mouseout_action_s += f"h('{f_span_id}','0');"
            patitle = self.title('e', e_pos, e_am, f_am, snt_id, orig_sa=orig_sa)
            color, text_decoration = self.decoration('e', e_pos, e_am, f_am, snt_id, mouseover_action_s)
            text_decoration_clause = f'text-decoration:{text_decoration};' if text_decoration else ''
            span_param_s = f'''id="{e_span_id}"'''
            if patitle:
                span_param_s += f''' patitle="{patitle}"'''
            span_param_s += f''' style="color:{color};{text_decoration_clause}"'''
            span_param_s += f''' onmouseover="{mouseover_action_s}"'''
            span_param_s += f''' onmouseout="{mouseout_action_s}"'''
            f_html.write(f"""<span {span_param_s}>{e_token.strip('@')}</span> """)
        f_html.write('<br>\n')
        for f_pos, f_token in enumerate(self.f_tokens):
            f_span_id = f'{ref2}-f{f_pos}'
            mouseover_action_s = f"h('{f_span_id}','1');"
            mouseout_action_s = f"h('{f_span_id}','0');"
            e_pos_list = self.f_e_pos_list[f_pos]
            orig_e_pos_list = orig_sa.f_e_pos_list[f_pos] if orig_sa else e_pos_list
            for e_pos in e_pos_list:
                e_span_id = f'{ref2}-e{e_pos}'
                if e_pos in orig_e_pos_list:
                    mouseover_action_s += f"h('{e_span_id}','1');"
                else:
                    mouseover_action_s += f"h('{e_span_id}','1+');"
                mouseout_action_s += f"h('{e_span_id}','0');"
            for e_pos in orig_e_pos_list:
                if e_pos not in e_pos_list:
                    e_span_id = f'{ref2}-e{e_pos}'
                    mouseover_action_s += f"h('{e_span_id}','1-');"
                    mouseout_action_s += f"h('{e_span_id}','0');"
            pbtitle = self.title('f', f_pos, e_am, f_am, snt_id, orig_sa=orig_sa)
            color, text_decoration = self.decoration('f', f_pos, e_am, f_am, snt_id, mouseover_action_s)
            text_decoration_clause = f'text-decoration:{text_decoration};' if text_decoration else ''
            span_param_s = f'''id="{f_span_id}"'''
            if pbtitle:
                span_param_s += f''' pbtitle="{pbtitle}"'''
            span_param_s += f''' style="color:{color};{text_decoration_clause}"'''
            span_param_s += f''' onmouseover="{mouseover_action_s}"'''
            span_param_s += f''' onmouseout="{mouseout_action_s}"'''
            f_html.write(f"""<span {span_param_s}>{f_token.strip('@')}</span> """)
        f_html.write('\n<hr />\n')


def slot_value_in_double_colon_del_list(line: str, slot: str, default: Optional = None) -> str:
    """For a given slot, e.g. 'cost', get its value from a line such as '::s1 of course ::s2 ::cost 0.3' -> 0.3
    The value can be an empty string, as for ::s2 in the example above."""
    m = regex.match(fr'(?:.*\s)?::{slot}(|\s+\S.*?)(?:\s+::\S.*|\s*)$', line)
    return m.group(1).strip() if m else default


def pmi(a_count: float, b_count: float, ab_count: float, total_count: float, smoothing: float = 1.0) -> float:
    if a_count <= 0 or b_count <= 0 or total_count <= 0:
        return 0
    else:
        p_a = a_count / total_count
        p_b = b_count / total_count
        expected_ab = p_a * p_b * total_count
        if expected_ab == 0 and smoothing == 0:
            return -99
        else:
            return math.log((ab_count + smoothing) / (expected_ab + smoothing))


def print_html_head(f_html, e_lang_name: str, f_lang_name: str, cgi_box: str):
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

    -->
    </script>
  </head>
  <body bgcolor="#FFFFEE">
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
                <tr><td>Script ualign.py version 0.0.6</td></tr>
                <tr><td>By Ulf Hermjakob, USC/ISI</td></tr></table></td>
      </tr>
    </table></td></tr></table><p>
""")


def print_html_foot(f_html):
    f_html.write('''
  </body>
</html>
''')


def main():
    vm = VerboseManager()
    html_root_dir = Path(__file__).parent.parent / "html"
    # sys.stderr.write(f'F: {Path(__file__)} P: {Path(__file__).parent} root: {html_root_dir}\n')
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--text_filename', type=Path, help='format: e ||| f ||| ref')
    parser.add_argument('-a', '--in_align_filename', type=Path, help='format: Pharaoh (e.g. 0-0 1-2 2-1 3-3)')
    parser.add_argument('-i', '--in_model_filename', type=Path, help='input model file (incl. ttables)')
    parser.add_argument('-r', '--f_romanization_filename', type=Path, help='format: f || uroman')
    parser.add_argument('-v', '--html_filename_dir', type=str, help='visualization output')
    parser.add_argument('-o', '--out_model_filename', type=Path, help='output model file (incl. ttables)')
    parser.add_argument('-z', '--out_align_filename', type=Path, help='format: Pharaoh (e.g. 0-0 1-2 2-1 3-3)')
    parser.add_argument('-l', '--log_filename', type=str, help='output')
    parser.add_argument('-e', '--e_lang_name', type=str)
    parser.add_argument('-f', '--f_lang_name', type=str)
    parser.add_argument('-n', '--max_number_output_snt', type=int)
    parser.add_argument('-s', '--skip_modules', type=str)
    parser.add_argument('-p', '--profile', type=argparse.FileType('w', encoding='utf-8', errors='ignore'),
                        default=None, metavar='PROFILE-FILENAME', help='(optional output for performance analysis)')
    args = parser.parse_args()
    if args.log_filename:
        f_log = open(args.log_filename, 'w')
    else:
        f_log = None
    if pr := cProfile.Profile() if args.profile else None:
        pr.enable()
    e_am = AlignmentModel('e AlignmentModel')
    f_am = AlignmentModel('f AlignmentModel')
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
        e_am.morph_clustering(f_am, 'e', f_log, vm)
        f_am.morph_clustering(e_am, 'f', f_log, vm)
    # sys.stderr.write(f'e-total: {e_am.total_count} f-total: {f_am.total_count}\n')
    if args.f_romanization_filename:
        f_am.load_romanization(args.f_romanization_filename, sys.stderr)
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
        if full_html_filename_dir.is_dir():
            e_am.process_alignments(f_am, full_text_filename, args.in_align_filename, args.out_align_filename,
                                    full_html_filename_dir, args.max_number_output_snt, args.e_lang_name,
                                    args.f_lang_name, f_log, skip_modules, vm, full_prop_filename)
        else:
            sys.stderr.write(f'Error: invalid html directory {args.html_filename_dir} -> {full_html_filename_dir}\n')
    if args.in_model_filename:
        sys.stderr.write(f'Rebuilding alignment model ...\n')
        e_am.build_glosses(f_am)
        f_am.build_glosses(e_am)
        e_am.find_function_words('e', f_log, vm)
        f_am.find_function_words('f', f_log, vm)
        e_am.morph_clustering(f_am, 'e', f_log, vm)
        f_am.morph_clustering(e_am, 'f', f_log, vm)
    if args.out_model_filename:
        sys.stderr.write(f'Writing model to {args.out_model_filename}\n')
        e_am.write_alignment_model(f_am, args.out_model_filename, sys.stderr)
    if pr:
        pr.disable()
        ps = pstats.Stats(pr, stream=args.profile).sort_stats(pstats.SortKey.TIME)
        ps.print_stats()
    if f_log:
        sys.stderr.write(f'Log: {args.log_filename}\n')
        f_log.close()


if __name__ == "__main__":
    main()

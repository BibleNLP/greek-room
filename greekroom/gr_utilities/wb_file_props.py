#!/usr/bin/env python
# wb_file_props.py -i f.untok -o owl/props.html -j owl/props.json --lang_code eng --lang_name English

import argparse
from collections import defaultdict
import datetime
import json
import os
import regex
import sys
from typing import TextIO
import unicodedata as ud
sys.path.append(os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)))))
# from gr_utilities import general_util, html_util
# import gr_utilities.general_util as general_util
from gr_utilities import general_util, html_util


# script_direction = ScriptDirection(lang_code, lang_name)
# script_direction.add_stats(token, count)
# script_direction.is_right_to_left()
class ScriptDirection:
    """Initialized with a copy from ualign.py"""
    def __init__(self, lang_code: str | None = None, lang_name: str | None = None, text: str | None = None):
        self.lang_code = lang_code
        self.lang_name = lang_name
        self.bidirectional_class_counts = defaultdict(int)
        self.direction = None  # "left-to-right" or "right-to-left"
        self.report = None
        self.monitor = False
        if text:
            self.add_stats(text)

    def add_stats(self, text: str, count: int = 1, loc: int | str | None = None) -> None:
        if text not in (None, 'NULL'):
            for c in text:
                bidirectional_class = ud.bidirectional(c)
                # L: left-to-right
                # R: right-to-left
                # AL: Arabic letter (right-to-left)
                # B: paragraph separator
                # ES: European separator
                # WS: whitespace
                # ON: other neutral
                self.bidirectional_class_counts[bidirectional_class] += count
                if self.monitor:
                    if self.lang_code in ('eng', ) and bidirectional_class in ('AL', 'R'):
                        sys.stderr.write(f"RTL char {c} for {self.lang_name or self.lang_code}"
                                         f"{(' in ' + loc) if loc else ''}\n")
                    if self.lang_code in ('ara', 'bal', 'fas', 'heb', 'hbo', 'kas', 'pan', 'pus', 'snd',
                                          'uig', 'urd', 'yid') and bidirectional_class in ('L',):
                        sys.stderr.write(f"LTR char {repr(c)} for {self.lang_name or self.lang_code}"
                                         f"{(' in ' + loc) if loc else ''}\n")

    def direction_class_counts(self) -> tuple[int, int]:
        # Right-to-left: Arabic letters (AL), Hebrew (R)
        # Classes: https://www.unicode.org/reports/tr9/tr9-3.html
        n_ltr = self.bidirectional_class_counts['L']
        n_rtl = self.bidirectional_class_counts['AL'] + self.bidirectional_class_counts['R']
        return n_ltr, n_rtl

    def determine_direction(self) -> str:
        n_ltr, n_rtl = self.direction_class_counts()
        self.direction = "right-to-left" if n_rtl > n_ltr else "left-to-right"
        return self.direction

    def is_right_to_left(self) -> bool:
        return self.determine_direction() == "right-to-left"

    @staticmethod
    def string_is_right_to_left(text: str) -> bool:
        return ScriptDirection(text=text).is_right_to_left()

    def make_report(self, details: bool = False) -> str:
        message = f"Determined script direction for {self.lang_name or self.lang_code} to be "
        message += self.determine_direction()  # "left-to-right" or "right-to-left"
        if details:
            message += " with character direction counts "
            n_ltr, n_rtl = self.direction_class_counts()
            message += (f"{n_rtl}:{n_ltr}" if self.is_right_to_left() else f"{n_ltr}:{n_rtl}") + " in favor."
        self.report = message
        return message

    @staticmethod
    def switchable_open_close_delimiters_for_rtl_scripts() -> str:
        return '“”‘’'

    def text_contains_switchable_chars(self, s: str) -> bool:
        return any([x in s for x in self.switchable_open_close_delimiters_for_rtl_scripts()])

    def switch_delimiters_for_rtl_scripts(self, s: str) -> str:
        if self.string_is_right_to_left(s):
            s = s.replace('\u0091', '')  # PRIVATE USE ONE character
            rest = self.switchable_open_close_delimiters_for_rtl_scripts()
            while len(rest) >= 2:
                open_delimiter, close_delimiter, rest = rest[0], rest[1], rest[2:]
                s = s.replace(open_delimiter, '\u0091')
                s = s.replace(close_delimiter, open_delimiter)
                s = s.replace('\u0091', close_delimiter)
        return s

    @staticmethod
    def print_to_html(d: dict, f_html: TextIO) -> None:
        if d:
            f_html.write(f"    <li> Script direction\n")
            f_html.write("      <ul>\n")
            direction = d.get("direction")
            f_html.write(f"        <li> Direction: {direction}\n")
            if counts := d.get("counts"):
                f_html.write(f"        <li> Counts: {dict(counts)}\n")
            if report := d.get("report"):
                f_html.write(f"        <li> Report: {report}\n")
            f_html.write("      </ul>\n")


class PunctStyle:
    """Initialized with a copy from ualign.py"""
    def __init__(self, text: str | None = None):
        self.d = defaultdict(lambda: defaultdict(int))
        self.pair_counts = defaultdict(lambda: defaultdict(int))
        self.quotation_mark_characters = """‘’‚"“”„«»‹›"""
        self.quotation_mark_characters2 = self.quotation_mark_characters + "'ʼ"
        self.quotation_pair_candidates = [
            ['“', '”'], ['„', '”'], ['”', '”'], ['“', '“'], ['„', '“'], ['«', '»'], ['‹', '›'],
            ["‘", "’"], ["‚", "’"], ["’", "’"]]
        self.quotation_mark_character_d = defaultdict(list)
        for quotation_pair_candidate in self.quotation_pair_candidates:
            left_q, right_q = quotation_pair_candidate
            if right_q not in self.quotation_mark_character_d[left_q]:
                self.quotation_mark_character_d[left_q].append(right_q)
        self.quotation_pairs = []
        self.n_chars = 0
        if text:
            self.add_stats(text)

    def add_stats(self, text: str, verbose: bool = False) -> None:
        for c in self.quotation_mark_characters2:
            if c in text:
                start_word_s = regex.findall(rf"(?<!\pL|\pM){c}(?=\pL)", text)
                start2_word_s = regex.findall(rf"(?<!(?:\pL|\pM|\d)\S*){c}\S*(?=\pL|\d)", text)
                in_word_s = regex.findall(rf"(?<=\pL|\pM){c}(?=\pL)", text)
                end_word_s = regex.findall(rf"(?<=\pL|\pM){c}(?!\pL)", text)
                end2_word_s = regex.findall(rf"(?<=\pL|\pM|\d)\S*(?:[’]\s)?{c}(?!(?:\S*(?:\pL|\d)))", text)
                if verbose:
                    if (c == "„") and (len(start2_word_s) != text.count(c)):
                        sys.stderr.write(f"Point A: {text}")
                    if (c == "”") and (len(end2_word_s) != text.count(c)):
                        sys.stderr.write(f"Point B: {text}")
                self.d[c]['n_start_word'] += len(start_word_s)
                self.d[c]['n_start2_word'] += len(start2_word_s)
                self.d[c]['n_end_word'] += len(end_word_s)
                self.d[c]['n_end2_word'] += len(end2_word_s)
                self.d[c]['n_in_word'] += len(in_word_s)
                self.d[c]['total'] += text.count(c)
        for c1 in self.quotation_mark_character_d.keys():
            if c1 in text:
                for c2 in self.quotation_mark_character_d[c1]:
                    if c2 in text:
                        if quotes := (
                                regex.findall(rf"(?<!\pL\pM*){c1}[^{c1}{c2}]*?{c2}(?!\pL)",
                                              text)):
                            self.pair_counts[c1][c2] += len(quotes)
        self.n_chars += len(text)

    def add_conclusions(self):
        for candidate_pair in self.quotation_pair_candidates:
            c1, c2 = candidate_pair
            if (c1 in self.d.keys()) and (c2 in self.d.keys()):
                if c1 == c2:
                    if ((self.d[c1]['n_start2_word'] + self.d[c2]['n_end2_word'] >= 0.9 * self.d[c1]['total'])
                            and (self.d[c1]['n_start2_word'] >= 0.8 * self.d[c2]['n_end2_word'])
                            and (self.d[c1]['n_start2_word'] <= 1.4 * self.d[c2]['n_end2_word'])):
                        self.quotation_pairs.append(candidate_pair)
                else:
                    # noinspection PyUnboundLocalVariable
                    if ((self.d[c1]['n_start2_word'] >= 0.8 * self.d[c1]['total'])
                            and (self.d[c2]['n_end2_word'] >= 0.3 * self.d[c2]['total'])
                            and (self.d[c2]['n_end2_word'] + self.d[c2]['n_in_word'] >= 0.9 * self.d[c2]['total'])
                            and (self.d[c1]['n_start2_word'] >= 0.8 * self.d[c2]['n_end2_word'])
                            and (self.d[c1]['n_start2_word'] <= 1.4 * self.d[c2]['n_end2_word'])):
                        self.quotation_pairs.append(candidate_pair)
                    elif (self.pair_counts[c1]
                            and (count := self.pair_counts[c1][c2])
                            and (count >= 0.8 * self.d[c1]['total'])
                            and (count >= 0.8 * self.d[c2]['total'])):
                        self.quotation_pairs.append(candidate_pair)

    @staticmethod
    def print_to_html(d: dict, f_html: TextIO) -> None:
        if d:
            f_html.write(f"    <li> Punctuation style\n")
            f_html.write("      <ul>\n")
            if quotation_pairs := d.get('quotation-pairs'):
                f_html.write("        <li> Quotation pairs\n")
                f_html.write("          <table>\n")
                for quotation_pair in quotation_pairs:
                    c1, c2 = quotation_pair[0], quotation_pair[1]
                    name1, name2 = ud.name(c1), ud.name(c2)
                    sep = "…"
                    f_html.write(f"          <tr><td>{c1}</td><td>{sep}</td><td>{c2}</td><td>&nbsp;&nbsp;</td>"
                                 f"<td>{name1}</td><td>{sep}</td><td>{name2}</td></tr>\n")
                f_html.write("          </table>\n")
            if count_d := d.get('counts'):
                f_html.write(f"        <li> Counts\n")
                f_html.write("          <table>\n")
                f_html.write(f"<tr><th>Punct</th><th>Unicode name</th>"
                             f"<th>Total</th><th>Start+</th><th>Start</th><th>Inside</th>"
                             f"<th>End</th><th>End+</th></tr>\n")
                for c in count_d.keys():
                    name = ud.name(c, '')
                    counts = count_d.get(c)
                    total = counts.get("total")
                    start = counts.get("n_start_word")
                    start2 = counts.get("n_start2_word")
                    inside = counts.get("n_in_word")
                    end = counts.get("n_end_word")
                    end2 = counts.get("n_end2_word")
                    f_html.write(f"<tr><td>{html_util.guard_html(c)}</td>"
                                 f"<td>{name}</td>"
                                 f"<td align='right'>{total}</td>"
                                 f"<td align='right'>{start2}</td>"
                                 f"<td align='right'>{start}</td>"
                                 f"<td align='right'>{inside}</td>"
                                 f"<td align='right'>{end}</td>"
                                 f"<td align='right'>{end2}</td></tr>\n")
                f_html.write("          </table>\n")
            if pair_counts := d.get('pair-counts'):
                f_html.write("        <li> Pair counts\n")
                f_html.write("          <table>\n")
                for c1 in pair_counts.keys():
                    for c2 in pair_counts[c1].keys():
                        count = pair_counts[c1][c2]
                        name1, name2 = ud.name(c1), ud.name(c2)
                        sep = "…"
                        f_html.write(f"          <tr><td>{c1}</td><td>{sep}</td><td>{c2}</td><td>&nbsp;&nbsp;</td>"
                                     f"<td>{name1}</td><td>{sep}</td><td>{name2}</td><td>&nbsp;&nbsp;</td>"
                                     f"<td>{count}</td></tr>\n")
                f_html.write("          </table>\n")
            f_html.write("      </ul>\n")


def script_punct(input_filename: str | None = None, input_string: str | None = None,
                 lang_code: str | None = None, lang_name: str | None = None)\
        -> dict:
    script_direction = ScriptDirection(lang_code, lang_name)
    punct_style = PunctStyle()
    if input_filename:
        with open(input_filename) as f:
            for line in f:
                punct_style.add_stats(line)
                for c in line:
                    script_direction.add_stats(c, 1)
    if input_string:
        punct_style.add_stats(input_string)
        for c in input_string:
            script_direction.add_stats(c, 1)
    punct_style.add_conclusions()
    report = script_direction.make_report(True)
    result = {"script-direction": {"direction": script_direction.determine_direction(),
                                   "counts": script_direction.bidirectional_class_counts,
                                   "report": report},
              "punct-style": {"quotation-pairs": punct_style.quotation_pairs,
                              "counts": punct_style.d,
                              "pair-counts": punct_style.pair_counts},
              "n-chars": punct_style.n_chars}
    if lang_code:
        result["lang-code"] = lang_code
    if lang_name:
        result["lang-name"] = lang_name
    return result


def print_meta_to_html(lang_code: str | None, lang_name: str | None, f_html: TextIO) -> None:
    if lang_code or lang_code:
        f_html.write(f"    <li> General\n")
        f_html.write("      <ul>\n")
        if lang_code:
            f_html.write(f"        <li> Language code: {lang_code}\n")
        if lang_name:
            f_html.write(f"        <li> Language name: {lang_name}\n")
        f_html.write("      </ul>\n")


def print_to_html(d: dict, f_html: TextIO) -> None:
    date = f"{datetime.datetime.now():%B %-d, %Y at %-H:%M}"
    f_html.write(html_util.html_head("Global file properties", date, "prop"))
    f_html.write("  <ul>\n")
    print_meta_to_html(d.get("lang-code"), d.get("lang-name"), f_html)
    ScriptDirection.print_to_html(d.get("script-direction"), f_html)
    PunctStyle.print_to_html(d.get("punct-style"), f_html)
    f_html.write("  </ul>\n")
    html_util.print_html_foot(f_html)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input_filename', type=str)
    parser.add_argument('-s', '--input_string', type=str)
    parser.add_argument('-j', '--json_out_filename', type=str, default=None)
    parser.add_argument('-o', '--html_out_filename', type=str, default=None)
    parser.add_argument('--lang_code', type=str, default=None)
    parser.add_argument('--lang_name', type=str, default=None)

    args = parser.parse_args()

    # read lang_code, lang_name from file info.json if not already given
    lang_code = args.lang_code
    lang_name = args.lang_name
    if not lang_code and not lang_name:
        if info_d := general_util.read_corpus_json_info("info.json"):
            lang_code = info_d.get("lc")
            lang_name = info_d.get("lang")
    json_out_filename = args.json_out_filename
    html_out_filename = args.html_out_filename

    # set defaults for json_out_filename and html_out_filename if neither are given
    if not json_out_filename and not html_out_filename:
        owl_folder = "owl"
        if not os.path.isdir(owl_folder):
            os.mkdir(owl_folder, mode=0o775)
        json_out_filename = f"{owl_folder}/props.json"
        html_out_filename = f"{owl_folder}/props.html"

    d = script_punct(args.input_filename, args.input_string, lang_code, lang_name)
    if json_out_filename:
        with open(json_out_filename, "w") as f_json:
            f_json.write(f"{json.dumps(d)}\n")
        if not args.json_out_filename:
            sys.stderr.write(f"Wrote JSON output to {json_out_filename}\n")
    if html_out_filename:
        with open(html_out_filename, "w") as f_html:
            print_to_html(d, f_html)
        if not args.html_out_filename:
            sys.stderr.write(f"Wrote HTML output to {html_out_filename}\n")


if __name__ == "__main__":
    main()

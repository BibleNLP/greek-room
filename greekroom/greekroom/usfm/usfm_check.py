#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""USFM checks"""
# todo: fq can be both self-closing as well as paired, similarly fqa, fk
# todo: \+bk mixed with \bk*  CODED
# todo: repair: add old-fashioned \bk to \+bk


from __future__ import annotations
import argparse
from collections import defaultdict
import datetime
import json
import math
import os
from os import listdir
from os.path import isfile, join
from pathlib import Path
import regex
import sys
from typing import List, Tuple
from ualign_utilities import BibleUtilities, DocumentConfiguration, ScriptDirection, BibleRefSpan, DataManager
import unicodedata as ud

n_usfm_objects = 0
n_toggle_indexes = 0


def html_head(title: str, date: str, meta_title: str) -> str:
    title2 = regex.sub(r' {2,}', '<br>', title)
    return f"""<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
        <link rel="shortcut icon" href="../images/GreekRoomFavicon-32x32.png">
        <title>{meta_title}</title>
            <style>""" + """
          [patitle]:hover:after {opacity: 1; transition: all 0.05s ease 0.1s; visibility: visible;}
          [patitle]:after {
                content: attr(patitle);
                min-width: 250px;
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
          [patitle] {word-break: keep-all; }
          [patitle] {line-break: strict; }
          [pbtitle]:hover:after {opacity: 1; transition: all 0.05s ease 0.1s; visibility: visible;}
          [pbtitle]:after {
                content: attr(pbtitle);
                min-width: 250px;
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
          [pbtitle] {word-break: keep-all; }
          [pbtitle] {line-break: strict; }
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
                            <td>&nbsp;&nbsp;&nbsp;</td>
                            <td><b><font class="large" size="+1">{title2}</font></b></td>
                            <td>&nbsp;&nbsp;&nbsp;</td>
                            <td>{date}</td>
                            <td>&nbsp;&nbsp;&nbsp;</td>
                            <td style="color:#777777;font-size:80%;">Script by Ulf Hermjakob</td>
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


def guard_html(s: str) -> str:
    s = regex.sub('&', '&amp;', s)
    s = regex.sub('<', '&lt;', s)
    s = regex.sub('>', '&gt;', s)
    s = regex.sub('"', '&quot;', s)
    s = regex.sub("'", '&apos;', s)
    return s


def guard_regex(s: str) -> str:
    return regex.sub(r'([.^*+?\\|$\(\)\[\]{}])', r'\\\1', s)


def html_nobr(s: str) -> str:
    s = regex.sub(r'(?<! ) (?! )', '&nbsp;', s)
    s = s.replace('-', '\u2011')  # non-breaking hyphen
    return s


def control_character_name(char: str) -> str | None:
    # Dictionary with the names of the most common control characters.
    control_character_dict = {
        '\x00': 'NULL', '\x01': 'START OF HEADING', '\x02': 'START OF TEXT', '\x03': 'END OF TEXT',
        '\x07': 'BELL', '\x08': 'BACKSPACE', '\x09': 'TAB', '\x0A': 'NEW LINE',
        '\x0D': 'CARRIAGE RETURN', 'x1B': 'ESCAPE', '\x7F': 'DELETE'}
    if char in control_character_dict:
        return f'control character {control_character_dict[char]}'
    elif char <= '\x1F':            # Unicode block C0
        return "control character"
    elif '\x80' <= char <= '\x9F':  # Unicode block C1
        return "control character"
    else:
        return None


def print_char_unicode_name(char: str) -> str:
    c_name = ud.name(char, None) or control_character_name(char) or ''
    invisible_char = regex.match(r'(\pZ|\pC)', char)
    hex_code = f"U+{ord(char):04X}"
    return f"{c_name} ({hex_code})" if invisible_char else f"{char} ({c_name}, {hex_code})"


def print_str_unicode_names(s: str, delimiter: str = ', ') -> str:
    return delimiter.join(map(print_char_unicode_name, s))


def viz_str(s: str) -> str:
    """visualizes string by revealing spaces (except plain ' ') and control characters by code"""
    result = ''
    for char in s:
        if char == '\n':
            result += '<LF>'
        elif char == '\r':
            result += '<CR>'
        elif char == '\t':
            result += '<TAB>'
        elif char in ' ':
            result += char
        elif char.isspace() or regex.match(r'\pC', char):
            result += f"<{ord(char):04X}>"
        else:
            result += char
    return result


def group_integers_into_spans(int_list: list[int], delimiter: str = ', ', max_n_spans: int | None = None) -> str:
    """group_integers_into_spans([2, 3, 5, 10, 11, 12, 13, 14]) = '2-3, 5, 10-14'"""
    spans = []
    span_start, span_end = None, None
    for i in int_list:
        if span_end is None:
            span_start, span_end = i, i
        elif span_end + 1 == i:
            span_end = i
        else:
            spans.append(str(span_end) if span_end == span_start else f"{span_start}-{span_end}")
            span_start, span_end = i, i
            if max_n_spans is not None and len(spans) >= max_n_spans:
                spans.append('...')
                return delimiter.join(spans)
    if span_end:
        spans.append(str(span_end) if span_end == span_start else f"{span_start}-{span_end}")
    return delimiter.join(spans)


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


class StringDiff:
    def __init__(self, s1: str, s2: str):
        self.s1 = s1
        self.s2 = s2
        self.word_span_list1 = None
        self.word_span_list2 = None
        self.word_ngram_set1 = None
        self.word_ngram_set2 = None
        self.options = {'match_style_start': '<span style="color:#008800;">',
                        'non_match_style_start': '<span style="color:#FF0000;background-color:yellow;">',
                        'context_style_start': '<span style="color:#008800;background-color:yellow;">',
                        'default_style_end': '</span>',
                        'stop_score': 10}

    @staticmethod
    def split_match_before_non_match(match: str, non_match1: str, non_match2: str) -> tuple[str, str]:
        if ((m2 := regex.match(r'(.*)(\\\+?(?:\pL\pM*)*)$', match))
                and (regex.match(r'(?:\+|\pL)', non_match1)
                     or regex.match(r'(?:\+|\pL)', non_match2))):
            return m2.group(1), m2.group(2)
        else:
            return match, ""

    @staticmethod
    def split_match_after_non_match(match: str, pre_match1: str, pre_match2: str) -> tuple[str, str]:
        if ((m2 := regex.match(r'((?:\pL\pM*)+)(.*)$', match))
                and (regex.match(r'\\?\+?(?:\pL\pM*)*', pre_match1)
                     or regex.match(r'\\?\+?(?:\pL\pM*)*', pre_match2))):
            return m2.group(1), m2.group(2)
        else:
            return "", match

    @staticmethod
    def bg_color_tokenize(s: str) -> list[tuple[str, int, int]]:
        result = []
        rest = s
        offset = 0
        while m3 := regex.match(r'(.*?)(\\\+?[a-z]+\d*\*?|(?:(?:\pL\pM*)+)|\d+)(.*)$',
                                rest, regex.IGNORECASE):
            pre, token, rest = m3.group(1, 2, 3)
            if pre:
                offset_start, offset_end = offset, offset + len(pre)
                result.append((pre, offset_start, offset_end))
                offset += len(pre)
            offset_start, offset_end = offset, offset + len(token)
            result.append((token, offset_start, offset_end))
            offset += len(token)
        if rest:
            offset_start, offset_end = offset, offset + len(rest)
            result.append((rest, offset_start, offset_end))
        return result

    @staticmethod
    def spans_intersect(s1: int, e1: int, s2: int, e2: int) -> bool:
        return s1 < s2 < e1 < e2 or s2 < s1 < e2 < e1

    def diff(self, options: dict | None = None, _loc: str | None = None) -> tuple[str, str]:
        if options:
            # overwrite any default options
            for key in options:
                self.options[key] = options[key]
        n_non_match_fragments = 0
        offset1, offset2 = 0, 0
        tokens1 = self.bg_color_tokenize(self.s1)
        tokens2 = self.bg_color_tokenize(self.s2)
        match_style_start = self.options.get('match_style_start') or ''
        match_style_end = self.options.get('match_style_end') or self.options.get('default_style_end') or ''
        non_match_style_start = self.options.get('non_match_style_start') or ''
        non_match_style_end = self.options.get('non_match_style_end') or self.options.get('default_style_end') or ''
        context_style_start = self.options.get('context_style_start') or ''
        context_style_end = self.options.get('context_style_end') or self.options.get('default_style_end') or ''
        stop_score = self.options.get('stop_score', 10)
        result1, result2 = "", ""
        rest1 = regex.findall(r'.\pM*', self.s1)
        rest2 = regex.findall(r'.\pM*', self.s2)
        while rest1 and rest2:
            match1, match2 = "", ""
            while rest1 and rest2 and rest1[0] == rest2[0]:
                match1 += rest1[0]
                match2 += rest2[0]
                rest1 = rest1[1:]
                rest2 = rest2[1:]
            if match1 and match2:
                offset1b = offset1 + len(match1)
                offset2b = offset2 + len(match2)
                while tokens1 and (tokens1[0][2] <= offset1):
                    tokens1 = tokens1[1:]
                while tokens2 and (tokens2[0][2] <= offset2):
                    tokens2 = tokens2[1:]
                # token1b = tokens1[0] if tokens1 else None
                # token2b = tokens2[0] if tokens2 else None
                # if "GEN 9:26" in loc:
                #     sys.stderr.write(f"B TOK1: {tokens1[0:1]} {offset1}-{offset1b}\n")
                #     sys.stderr.write(f"B TOK2: {tokens2[0:1]} {offset2}-{offset2b}\n")
                cut = None
                if tokens1 and (cut := tokens1[0][2] - offset1) > 0 and offset1 > tokens1[0][1]:
                    match1a, match1bc = match1[:cut], match1[cut:]
                else:
                    match1a, match1bc = "", match1
                if tokens2 and (cut := tokens2[0][2] - offset2) > 0 and offset2 > tokens2[0][1]:
                    match2a, match2bc = match2[:cut], match2[cut:]
                else:
                    match2a, match2bc = "", match2
                while tokens1 and (tokens1[0][2] <= offset1b):
                    tokens1 = tokens1[1:]
                while tokens2 and (tokens2[0][2] <= offset2b):
                    tokens2 = tokens2[1:]
                # token1a = tokens1[0] if tokens1 else None
                # token2a = tokens2[0] if tokens2 else None
                # if "GEN 9:26" in loc:
                #     sys.stderr.write(f"A TOK1: {tokens1[0:1]} {offset1}-{offset1b}\n")
                #     sys.stderr.write(f"A TOK2: {tokens2[0:1]} {offset2}-{offset2b}\n")
                if tokens1 and (cut := offset1b-tokens1[0][1]) > 0 and offset1b < tokens1[0][2]:
                    match1b, match1c = match1bc[:-cut], match1bc[-cut:]
                else:
                    match1b, match1c = match1bc, ""
                if tokens2 and (cut := offset2b - tokens2[0][1]) > 0 and offset2b < tokens2[0][2]:
                    match2b, match2c = match2bc[:-cut], match2bc[-cut:]
                else:
                    match2b, match2c = match2bc, ""
                # if "GEN" in loc:
                #    if match1a or match1c:
                #       sys.stderr.write(f"TO1: {loc} {token1a} {token1b} {offset1}-{offset1b} {match1a}::{match1c}\n")
                #    if match2a or match2c:
                #       sys.stderr.write(f"TO2: {loc} {token2a} {token2b} {offset2}-{offset2b} {match2a}::{match2c}\n")
                if match1a:
                    result1 += f"{context_style_start}{match1a}{context_style_end}"
                result1 += f"{match_style_start}{match1b}{match_style_end}"
                if match1c:
                    result1 += f"{context_style_start}{match1c}{context_style_end}"
                if match2a:
                    result2 += f"{context_style_start}{match2a}{context_style_end}"
                result2 += f"{match_style_start}{match2b}{match_style_end}"
                if match2c:
                    result2 += f"{context_style_start}{match2c}{context_style_end}"
                offset1 += len(match1)
                offset2 += len(match2)
            if rest1 and rest2:
                rest2_len = len(rest2)
                best_score, best_sub1_len, best_sub2_len = 0, None, None
                for sub1_sub2_len in range(1, len(rest1) + len(rest2) + 1):
                    for sub1_len in range(0, min(sub1_sub2_len, len(rest1)) + 1):
                        if (sub2_len := sub1_sub2_len - sub1_len) > rest2_len:
                            continue
                        match_len = 0
                        max_i = min(len(rest1)-sub1_len, len(rest2)-sub2_len)
                        for i in range(0, max_i):
                            if rest1[sub1_len+i] == rest2[sub2_len+i]:
                                match_len += 1
                            else:
                                break
                        if match_len:
                            score = min(match_len, 40) / max(sub1_len, sub2_len)
                            if score > best_score:
                                best_score, best_sub1_len, best_sub2_len = score, sub1_len, sub2_len
                    if best_score >= stop_score:
                        break
                if best_sub1_len is not None:
                    non_match1 = ''.join(rest1[:best_sub1_len])
                    non_match2 = ''.join(rest2[:best_sub2_len])
                    result1 += f"{non_match_style_start}{non_match1}{non_match_style_end}"
                    result2 += f"{non_match_style_start}{non_match2}{non_match_style_end}"
                    rest1 = rest1[best_sub1_len:]
                    rest2 = rest2[best_sub2_len:]
                    offset1 += len(non_match1)
                    offset2 += len(non_match2)
                else:
                    result1 += f"{non_match_style_start}{''.join(rest1)}{non_match_style_end}"
                    result2 += f"{non_match_style_start}{''.join(rest2)}{non_match_style_end}"
                    rest1 = ""
                    rest2 = ""
                n_non_match_fragments += 1
        if rest1:
            result1 += f"{non_match_style_start}{''.join(rest1)}{non_match_style_end}"
        if rest2:
            result2 += f"{non_match_style_start}{''.join(rest2)}{non_match_style_end}"
        return result1, result2

    @staticmethod
    def word_span_list(s: str) -> list[tuple[int, int]]:
        # word_span_list("Go away!") = [(0, 2), (3, 7)]
        result = []
        position = 0
        rest = s
        while m := regex.match(r'(.*?)((?:\pL\pM*)+)(.*)$', rest, regex.DOTALL):
            pre, word, rest = m.group(1, 2, 3)
            start = position + len(pre)
            end = start + len(word)
            position = end
            result.append((start, end))
        return result

    def build_word_span_lists(self) -> None:
        if self.word_span_list1 is None:
            self.word_span_list1 = self.word_span_list(self.s1)
        if self.word_span_list2 is None:
            self.word_span_list2 = self.word_span_list(self.s2)

    def word_ngram_set(self, s: str) -> set[str]:
        result = set()
        wsl = self.word_span_list(s)
        for start in range(len(wsl)):
            for end in range(start + 1, len(wsl) + 1):
                result.add(s[wsl[start][0]:wsl[end-1][1]])
        return result

    def build_word_ngram_sets(self) -> None:
        self.build_word_span_lists()
        if self.word_ngram_set1 is None:
            self.word_ngram_set1 = self.word_ngram_set(self.s1)
        if self.word_ngram_set2 is None:
            self.word_ngram_set2 = self.word_ngram_set(self.s2)

    def max_overlap_words(self) -> str | None:
        self.build_word_ngram_sets()
        max_ngram, max_length = None, 0
        for ngram in self.word_ngram_set1:
            if ngram in self.word_ngram_set2:
                if len(ngram) > max_length:
                    max_ngram, max_length = ngram, len(ngram)
        return max_ngram

    def max_overlap_words_at_end(self, ref_side: int = 2, at_start: bool = True) -> str | None:
        self.build_word_ngram_sets()
        if ref_side == 1:
            s, wsl, other_word_ngram_set = self.s1, self.word_span_list1, self.word_ngram_set2
        else:
            s, wsl, other_word_ngram_set = self.s2, self.word_span_list2, self.word_ngram_set1
        n_overlapping_words = 0
        max_ngram = None
        while n_overlapping_words < len(wsl):
            n_overlapping_words += 1
            ngram = s[wsl[0][0]:wsl[n_overlapping_words - 1][1]] \
                if at_start \
                else s[wsl[-n_overlapping_words][0]:wsl[-1][1]]
            if ngram in other_word_ngram_set:
                max_ngram = ngram
            else:
                break
        return max_ngram


class SmartFindall:
    def __init__(self, r: str, s: str, flags: int = 0):
        self.did_you_mean: list[str, str, str, str] | None = None  # pre, core, post, style
        self.regex_elements = []
        self.other_elements = []  # text between regex_elements
        self.regex_element_styles = defaultdict(str)
        self.len = 0
        if m4 := regex.match(r"(.*?)(\s+\[?Did you mean\s*)([^()]+?)(\s*\(.*|\s*)$", s, regex.DOTALL):
            self.did_you_mean = [m4.group(2), m4.group(3), m4.group(4), 'color:green;']
            rest = m4.group(1)
        else:
            rest = s
        while m3 := regex.search(f"(.*?)({r})(.*$)$", rest, flags | regex.DOTALL):
            pre, regex_element, rest = m3.group(1, 2, 3)
            self.other_elements.append(pre)
            self.regex_elements.append(regex_element)
            self.len += 1
        self.other_elements.append(rest)

    def markup_tag_style(self, tags: list[str], style: str) -> str:
        # e.g. sf.markup_tag_style(['\v'], 'color:green;')
        for i in range(len(self.regex_elements)):
            if self.regex_elements[i] in tags:
                self.regex_element_styles[i] = style
        return str(self)

    def markup_repeat_tag_style(self, tags: list[str], style: str) -> str:
        # e.g. sf.markup_tag_style(['\v'], 'color:green;')
        for i in range(1, len(self.regex_elements)):
            if (self.regex_elements[i-1] in tags) and (self.regex_elements[i] in tags):
                self.regex_element_styles[i-1] = style
                self.regex_element_styles[i] = style
        return str(self)

    def markup_tag2_style(self, tags1: list[str], style1: str, tags2: list[str], style2: str) -> str:
        for i in range(len(self.regex_elements)):
            if self.regex_elements[i] in tags1:
                self.regex_element_styles[i] = style1
            elif self.regex_elements[i] in tags2:
                self.regex_element_styles[i] = style2
        return str(self)

    def nth_tag(self, i: int) -> str:
        if 0 <= i < self.len:
            return self.regex_elements[i]
        else:
            return ""

    def __str__(self):
        result = ""
        for i in range(self.len):
            result += self.other_elements[i]
            if style := self.regex_element_styles.get(i):
                result += f"<span style='{style}'>{self.regex_elements[i]}</span>"
            else:
                result += self.regex_elements[i]
        result += self.other_elements[self.len]
        if self.did_you_mean:
            if self.did_you_mean[3]:
                result += (f"{self.did_you_mean[0]}"
                           f"<span style='{self.did_you_mean[3]}'>{self.did_you_mean[1]}</span>"
                           f"{self.did_you_mean[2]}")
            else:
                result += f"{self.did_you_mean[0]}{self.did_you_mean[1]}{self.did_you_mean[2]}"
        return result


class CorpusModel:
    def __init__(self, sc: UsfmCheck | None = None):
        self.sc = sc
        self.lc_token_count = defaultdict(int)
        self.lc_pre_number_count = defaultdict(int)
        self.lc_post_number_count = defaultdict(int)
        self.matching_punct_candidates = "()[]{}«»»«‹››‹⌞⌟（）［］【】「」『』《》〈〉“”‘’„”‚’''\"\""
        self.num_pattern1 = r"\d+(?:[.,]\d{3})+(?!\d)"
        self.num_pattern2 = r"\d+(?:[-‑–—:.,/]\d+)+"
        self.pattern_count = defaultdict(int)
        self.paired_delimiter_count = defaultdict(int)
        self.letter_ngram_count = defaultdict(int)
        self.letter_ngram_size = 0
        self.n_logs = 0

    @staticmethod
    def might_be_reference_number(s) -> bool:
        integer_list = regex.findall(r'\d+', s)
        for i in integer_list:
            if int(i) > 180:
                return False
            elif i[0] in '0':
                return False
        return True

    @staticmethod
    def strip_punct(token: str) -> str:
        new_token = token.lstrip('(“‘⌞')
        new_token = new_token.rstrip(';,.:!’”⌟)')
        # reattach final '.' in abbreviations such as 'e.g.'
        if ('.' in new_token) and regex.search(r'\pL\pM*\.\pL', new_token):
            new_token2 = new_token + '.'
            if new_token2 in token:
                new_token = new_token2
        return new_token

    def add_txt(self, s: str) -> None:
        tokens = s.split()
        for i, raw_token in enumerate(tokens):
            token = self.strip_punct(raw_token)
            self.lc_token_count[token.lower()] += 1
            if i and (m := regex.match(r'\d+(?:[-‑–—:.,/]\d+)+', token)):
                raw_prev_token = tokens[i-1]
                prev_token = raw_prev_token.lstrip('/([')
                if i >= 2:
                    raw_prev_2tokens = f"{tokens[i - 2]} {tokens[i - 1]}"
                    prev_2tokens = raw_prev_2tokens.lstrip('/([')
                    if (self.sc.ref_stats.book_name_normalization.get(raw_prev_2tokens.lower())
                            or self.sc.ref_stats.book_name_normalization.get(prev_2tokens.lower())):
                        prev_token = prev_2tokens
                if self.might_be_reference_number(m.group(0)):
                    self.lc_pre_number_count[prev_token.lower()] += 1
            if (i+1 < len(tokens)) and regex.match(r'(?:[1-9]?[¼½]|\d+(?:[.,/]\d+)*)$', raw_token):
                next_token = tokens[i+1]
                next_token = self.strip_punct(next_token)
                if regex.match(r'[0-9]+$', raw_token) and (1970 <= int(raw_token) <= 2070):
                    pass
                else:
                    self.lc_post_number_count[next_token.lower()] += 1
        i = 0
        self.n_logs += 1
        while i+1 <= len(self.matching_punct_candidates):
            left_punct, right_punct = self.matching_punct_candidates[i], self.matching_punct_candidates[i+1]
            g_left_punct, g_right_punct = guard_regex(left_punct), guard_regex(right_punct)
            i += 2
            re = fr'(?<!\pL\pM*\pP*){g_left_punct}\pP*\pL.*?\pL\pM*\pP*{g_right_punct}(?!\pP*\pL)'
            self.paired_delimiter_count[(left_punct, right_punct)] += len(regex.findall(re, s))
        num1_list = regex.findall(self.num_pattern1, s)
        num2_list = regex.findall(self.num_pattern2, s)
        for num2 in num2_list:
            if self.might_be_reference_number(num2):
                p = num2
                if num2 in num1_list:
                    p = regex.sub(r'(?<=[.,])\d\d\d\b', 'DDD', p)
                p = regex.sub(r'\d+', 'Number', p)
                p = regex.sub(r'DDD', 'Number3', p)
                self.pattern_count[p] += 1

    def stats(self) -> dict:
        d = {'pre-number-token': {}, 'post-number-token': {}}
        for token in self.lc_pre_number_count.keys():
            token_count = self.lc_token_count[token]
            pre_number_token_count = self.lc_pre_number_count[token]
            if (pre_number_token_count >= 2) and (pre_number_token_count >= 0.1 * token_count):
                d['pre-number-token'][token] = (pre_number_token_count, token_count)
        for token in self.lc_post_number_count.keys():
            token_count = self.lc_token_count[token]
            post_number_token_count = self.lc_post_number_count[token]
            if (post_number_token_count >= 2) and (post_number_token_count >= 0.1 * token_count):
                d['post-number-token'][token] = (post_number_token_count, token_count)
        return d

    def letter_ngram_stats(self):
        for lc_token in self.lc_token_count.keys():
            lc_token_count = self.lc_token_count[lc_token]
            bordered_token = ' ' + lc_token + ' '
            self.letter_ngram_size += len(bordered_token)
            max_pos = len(bordered_token)
            for start_pos in range(max_pos):
                for end_pos in range(start_pos + 1, min(start_pos + 15, max_pos + 1)):
                    sub_s = bordered_token[start_pos:end_pos]
                    self.letter_ngram_count[sub_s] += lc_token_count
        hapaxes = []
        for sub_token in self.letter_ngram_count.keys():
            sub_token_len = len(sub_token)
            sub_token_count = self.letter_ngram_count[sub_token]
            if sub_token_count == 1 and sub_token_len <= 4 and regex.match(r'\pL+$', sub_token):
                hapaxes.append(sub_token)
            pmi_min, pmi_max = 99, -99
            best_s1, best_s2 = None, None
            for mid in range(1, sub_token_len):
                s1, s2 = sub_token[:mid], sub_token[mid:]
                pmi1 = pmi(self.letter_ngram_count[s1],
                           self.letter_ngram_count[s2],
                           sub_token_count,
                           self.letter_ngram_size,
                           smoothing=0.3)
                if pmi1 > pmi_max:
                    pmi_max = pmi1
                    best_s1, best_s2 = s1, s2
                if pmi1 < pmi_min:
                    pmi_min = pmi1
            if sub_token_len > 6 and pmi_max < -2.5:
                count1 = self.letter_ngram_count[best_s1]
                count2 = self.letter_ngram_count[best_s2]
                sys.stderr.write(f"{sub_token} {self.letter_ngram_count[sub_token]} {pmi_min}:{pmi_max}"
                                 f" {best_s1} ({count1}) {best_s2} ({count2})\n")
        """
        for hapax in sorted(hapaxes, key=lambda x: (len(x), x)):
            sys.stderr.write(f"{hapax} ")
        sys.stderr.write("\n")
        """
        # PMI

    def report_stats(self, filename: str | Path | None):
        sc = self.sc
        ref_words = sc.doc_config.ref_words.get(sc.lang_code, []) if sc else None
        chapter_keywords = ref_words.get('_CHAPTER_', []) if ref_words else []
        chapter_keywords_lc = [x.lower() for x in chapter_keywords]
        verse_keywords = ref_words.get('_VERSE_', []) if ref_words else []
        verse_keywords_lc = [x.lower() for x in verse_keywords]
        none_keywords = ref_words.get('_NONE_', []) if ref_words else []
        none_keywords_lc = [x.lower() for x in none_keywords]
        known_book_ids = []
        known_numbered_book_ids = set()   # e.g. chronicles, corinthians
        known_chapter_keywords = []
        known_verse_keywords = []
        known_none_keywords = []
        # sys.stderr.write(f"BOOK NORM: {sc.ref_stats.book_name_normalization}\n")
        with (open(filename, 'w') as f):
            d = self.stats()
            f.write(f'# Corpus props\n')
            for key in sorted(self.paired_delimiter_count.keys(),
                              key=lambda x: self.paired_delimiter_count[x], reverse=True):
                left_punct, right_punct = key
                if count := self.paired_delimiter_count[key]:
                    f.write(f"  Paired-delimiter count for {left_punct}{right_punct}: {count}\n")
            for key in sorted(self.pattern_count.keys(),
                              key=lambda x: self.pattern_count[x], reverse=True):
                if count := self.pattern_count[key]:
                    f.write(f"  Pattern count for {key}: {count}\n")
            pre_number_token_d = d['pre-number-token']
            if pre_number_token_d.keys():
                f.write(f"Keyword candidates (before numbers):\n")
            smooth = 10
            pre_number_tokens = sorted(pre_number_token_d.keys(),
                                       key=lambda x: pre_number_token_d[x][0] / (pre_number_token_d[x][1] + smooth),
                                       reverse=True)
            for pre_number_token in pre_number_tokens:
                value = pre_number_token_d[pre_number_token]
                if self.sc \
                        and self.sc.ref_stats \
                        and (norm_book_name := self.sc.ref_stats.book_name_normalization.get(pre_number_token)):
                    known_book_ids.append(norm_book_name)
                    if m := regex.match(r'\d\s+(.*)$', norm_book_name):
                        known_numbered_book_ids.add(str(m.group(1)).lower())
                elif pre_number_token in chapter_keywords_lc:
                    known_chapter_keywords.append(pre_number_token)
                elif pre_number_token in verse_keywords_lc:
                    known_verse_keywords.append(pre_number_token)
                elif pre_number_token in none_keywords_lc:
                    known_none_keywords.append(pre_number_token)
                elif pre_number_token in known_numbered_book_ids:
                    pass
                elif not regex.search(r'\pL', pre_number_token):
                    pass
                elif regex.search(r'//\d', pre_number_token):
                    pass
                elif pre_number_token.endswith(':'):
                    pass
                elif pre_number_token.endswith(','):
                    pass
                elif pre_number_token.endswith('”'):
                    pass
                else:
                    f.write(f"  Possible keyword (preceding numbers): {pre_number_token} ({value})\n")
            if known_book_ids:
                f.write(f"  Known to be book IDs: {', '.join(known_book_ids)}\n")
            if known_numbered_book_ids:
                f.write(f"  Known to be numbered book IDs: {', '.join(known_numbered_book_ids)}\n")
            if known_chapter_keywords:
                f.write(f"  Known to be chapter keywords: {', '.join(known_chapter_keywords)}\n")
            if known_verse_keywords:
                f.write(f"  Known to be verse keywords: {', '.join(known_verse_keywords)}\n")

            post_number_token_d = d['post-number-token']
            post_number_tokens = sorted(post_number_token_d.keys(),
                                        key=lambda x: post_number_token_d[x][0] / (post_number_token_d[x][1] + smooth),
                                        reverse=True)
            for post_number_token in post_number_tokens:
                value = post_number_token_d[post_number_token]
                if self.sc \
                        and self.sc.ref_stats \
                        and (norm_book_name := self.sc.ref_stats.book_name_normalization.get(post_number_token)):
                    known_book_ids.append(norm_book_name)
                    if m := regex.match(r'\d\s?(.*)$', norm_book_name):
                        known_numbered_book_ids.add(str(m.group(1)).lower())
                elif post_number_token in known_numbered_book_ids:
                    pass
                elif not regex.search(r'\pL', post_number_token):
                    pass
                else:
                    f.write(f"  Possible unit (following numbers): {post_number_token} ({value})\n")


class BibleTextExtracts:
    def __init__(self, key: tuple[str, int | None, int | str | None]):
        self.book_id, self.chapter_number, self.verse_number = key
        self.verse_text = None
        self.footnotes: list[dict] = []
        self.figures: list[dict] = []
        self.titles: list[dict] = []
        self.misc_texts: list[dict] = []

    def __str__(self) -> str:
        result = ""
        verse_texts = [self.verse_text] if self.verse_text else []
        # if self.book_id == 'MAT':
        for extract in (verse_texts + self.footnotes + self.figures + self.titles + self.misc_texts):
            # or [{"bk": self.book_id, "c": self.chapter_number, "v": self.verse_number}]
            if (extract.get('type') == "o") and (extract.get('tag') is None) and (extract.get('txt') == ""):
                continue
            result += json.dumps(extract) + "\n"
        return result

    @staticmethod
    def update_line_info(so: UsfmObject, verse_text_d: dict) -> None:
        if ((old_l := verse_text_d.get('l'))
                and (old_l_elements := regex.match(r'(\d+)-?(\d*)$', str(old_l)))):
            old_l_start = old_l_elements[0]
            old_l_end_i = int(old_l_elements[1]) if old_l_elements[1] else int(old_l_start)
            new_l_end = max(old_l_end_i, int(so.sc.current_line_number_end))
            if new_l_end > old_l_end_i:
                verse_text_d['l'] = f"{old_l_start}-{new_l_end}"

    def add_so(self, so: UsfmObject) -> None:
        sc = so.sc
        for element in so.elements:
            element2 = element
            if isinstance(element, UsfmElement):
                tag = element.tag
                result = self.add_se(element)
                if (sc.tag_props.get(('entity-category-markup', tag))
                        or sc.tag_props.get(('visual-style', tag))
                        or sc.tag_props.get(('word-p', tag))
                        or sc.tag_props.get(('table-content', tag))
                        or sc.tag_props.get(('quotation-markup', tag))):
                    element2 = result
                else:
                    continue
            if isinstance(element2, str) and element2:
                # Loose text
                key = (sc.current_book_id,
                       sc.current_chapter,
                       sc.current_verse_s or (str(sc.current_verse) if sc.current_verse else None))
                if sc.current_book_id and sc.current_chapter and sc.current_verse:
                    bte = sc.bible_text_extract_dict.get(key)
                    if bte and (verse_text_d := bte.verse_text):
                        if verse_text_d.get('txt'):
                            verse_text_d['txt'] += element2
                            verse_text_d['verse-discontiguous'] = True
                            sc.log_count_dict['# verse-discontiguous'] += 1
                            self.update_line_info_based_on_current_position(so)
                else:
                    bte = sc.bible_text_extract_dict.get(key)
                    if bte is None:
                        bte = BibleTextExtracts(key)
                        sc.bible_text_extract_dict[key] = bte
                    misc_text = None
                    current_line_number_s = str(sc.current_line_number_end)
                    for misc_text_cand in self.misc_texts:
                        if misc_text_cand['l'] == current_line_number_s:
                            misc_text = misc_text_cand
                            break
                    if misc_text is None:
                        misc_text = {"bk": self.book_id}
                        if self.chapter_number:
                            misc_text["c"] = self.chapter_number
                        misc_text["type"] = "o"
                        misc_text['tag'] = None
                        misc_text['l'] = current_line_number_s
                        misc_text['txt'] = ''
                        self.misc_texts.append(misc_text)
                        sc.log_count_dict['# uncategorized texts (tag=none)'] += 1
                    if misc_text['txt'] or regex.search(r'\S', element2):
                        misc_text['txt'] += element2
                    self.update_line_info_based_on_current_position(so, misc_text)
                    if isinstance(element, UsfmElement):
                        sc.log_count_dict['# tag-inside-uncategorized-text'] += 1
                        misc_text['tag-inside-uncategorized-text'] = True

    def check(self, so: UsfmObject) -> None:
        skip_tests = ['Consecutive duplicate words']   # Moved to owl
        if 'Consecutive duplicate words' in skip_tests:
            return None
        sc = so.sc
        misc_data_dict = sc.misc_data_dict
        lang_code = sc.lang_code
        lang_name = sc.doc_config.langcode_to_langname(lang_code) or lang_code
        if self.verse_text and (txt := self.verse_text['txt']):
            words = regex.findall(r"\pL\pM*(?:(?:'|\u200C|\u200D)?\pL\pM*)*", txt.lower())
            for i in range(len(words) - 1):
                word = words[i]
                if (word == words[i+1]) and regex.search(rf'\b{word}(?:\pZ|\pC)+{word}\b',
                                                         sc.current_line.lower()):
                    duplicate = f'{word} {word}'
                    legit_dupl_dict = misc_data_dict.get((sc.lang_code, 'legitimate-duplicate', duplicate))
                    if legit_dupl_dict:
                        eng_gloss = legit_dupl_dict['gloss'].get('eng')
                        non_latin_characters = regex.findall(r'(?V1)[\pL--\p{Latin}]', word)
                        rom = legit_dupl_dict.get('rom')
                        title = duplicate + 50 * ' '
                        if rom and non_latin_characters:
                            title += f"&#xA;Romanization: {rom}"
                        if eng_gloss:
                            title += f"&#xA;English gloss: {eng_gloss}"
                        title += f"&#xA;Listed as legitimate for {lang_name}"
                        title = DataManager.html_title_guard(title)
                        error_cat_element = (f"<span patitle='{title}' "
                                             f"style='color:green;border-bottom:1px dotted;'>{duplicate}</span>")
                        error_cat = ('Alerts', 'Consecutive duplicate words', error_cat_element)
                        sc.record_error(error_cat, self.book_id, None, count_only_full_error_cat=True)
                    else:
                        error_cat = ('Alerts', 'Consecutive duplicate words', duplicate)
                        error_location = f"{self.book_id} {self.chapter_number}:{self.verse_number}"
                        error_context = sc.current_line
                        sc.record_error(error_cat, error_location, error_context)

    @staticmethod
    def line_info_based_on_se_position(se: UsfmElement | None = None) -> str | None:
        if se and se.start_position:
            line_s = str(se.start_position[0])
            if se.end_position and (se.end_position[0] != se.start_position[0]):
                line_s += f"-{se.end_position[0]}"
            return line_s
        else:
            return None

    def update_line_info_based_on_current_position(self, so: UsfmObject | None = None, text_dict: dict | None = None)\
            -> None:
        if text_dict is None:
            text_dict = self.verse_text
        if so and so.current_line_number:
            if text_dict:
                if old_line_info := text_dict.get('l'):
                    if m := regex.match(r'(\d+)(-?)(\d*)', old_line_info):
                        start_line_number = int(m.group(1))
                        end_line_number = int(m.group(3)) if m.group(3) else start_line_number
                        current_line = so.current_line_number - 1
                        if current_line > end_line_number:
                            new_line_info = f'{start_line_number}-{current_line}'
                            text_dict['l'] = new_line_info
                else:
                    text_dict['l'] = str(so.current_line_number - 1)

    def add_se(self, se: UsfmElement, anchor_tag: str | None = None) -> str | None:
        # typical anchor tags: None, v, f, fig
        so = se.so
        sc = so.sc
        _location = f"{self.book_id} {self.chapter_number}:{self.verse_number}"
        # verbose = (location == "GEN 1:2")
        # if verbose: sys.stderr.write(f"ADD-SE 1 {location} {se}\n")
        if sc.tag_props.get(('paragraph-format', se.tag)):
            return ""
        # Do not write/display/include in verse text:
        elif se.tag in ('sd', 'sd1', 'sd2', 'sd3', 'fm', 'fr', 'vp', 'x'):
            return ""
        else:
            result = ""
            for i, sub_element in enumerate(se.sub_elements):
                if isinstance(sub_element, str):
                    result += sub_element
                elif isinstance(sub_element, UsfmElement):
                    if not sc.tag_is_registered(sub_element.tag):
                        pass
                        # sc.message_count[f'Ignoring unregistered \\{sub_element.tag}'] += 1
                    elif sub_element.tag in ('va',):  # va extracted as separate slot
                        pass
                    elif sub_element.tag in ('rem',):
                        sc.extract_ignore_tag_count[sub_element.tag] += 1
                    else:
                        if sub_element.tag in ('f', 'ef'):
                            footnote_index = len(self.footnotes) + 1
                            footnote_dict = {"bk": self.book_id, "c": self.chapter_number}
                            if self.verse_number:
                                footnote_dict["v"] = self.verse_number
                            footnote_dict["type"] = "f"
                            footnote_dict["f#"] = footnote_index
                            footnote_dict["txt"] = ""
                            self.footnotes.append(footnote_dict)
                        if sub_element.tag in ('fig',):
                            figure_index = len(self.figures) + 1
                            figure_dict = {"bk": self.book_id, "c": self.chapter_number}
                            if self.verse_number:
                                figure_dict["v"] = self.verse_number
                            figure_dict["type"] = "fig"
                            figure_dict["fig#"] = figure_index
                            figure_dict["desc"] = ""
                            for attribute in ('desc', 'src', 'size', 'loc', 'copy', 'cap', 'ref'):
                                if value := sub_element.attributes.get(attribute):
                                    figure_dict[attribute] = value
                            self.figures.append(figure_dict)
                        sub_result = self.add_se(sub_element, anchor_tag)
                        # if verbose: sys.stderr.write(f"ADD-SE 1b {location} \\{se.tag} R:{sub_result} "
                        #                              f"S:{sub_element} A:{anchor_tag}\n")
                        if isinstance(sub_result, str):
                            if sub_element.tag in ('f', 'ef'):
                                self.footnotes[-1]['txt'] += sub_result
                            elif sub_element.tag in ('fig',):
                                self.figures[-1]['desc'] += sub_result
                            else:
                                if (sc.tag_props.get(('table-content', sub_element.tag))
                                        and result and sub_result
                                        and (not regex.search(r'(?:\pZ$|\n)\pC*$', result))
                                        and (not regex.match(r'\pC*(?:\pZ$|\r|\n)', sub_result))):
                                    result += ' '
                                result += sub_result
                        elif sub_element.tag in ('f', 'ef', 'fig'):
                            pass
                        else:
                            error_message = f"add_se_issue: unexpected sub-result type {type(sub_result)} " \
                                            f"for \\{se.tag} ... \\{sub_element.tag}"
                            if error_message not in sc.log_message_count:
                                sys.stderr.write(error_message + '\n')
                            sc.log_message_count[error_message] += 1
                else:
                    sys.stderr.write(f"add_se_issue: unknown sub_element type {type(sub_element)}\n")
            # if verbose: sys.stderr.write(f"ADD-SE 2 {location} \\{se.tag} {result}\n")
            for tag, key in (('fq', 'quotes'), ('fk', 'keywords')):
                value = result.strip()
                value = value.rstrip(":")
                if se.tag == tag and self.footnotes:
                    if self.footnotes[-1].get(key):
                        self.footnotes[-1][key].append(value)
                    else:
                        self.footnotes[-1][key] = [value]
            if sc.tag_props.get(('paragraph-format', se.tag)):
                return result
            elif sc.tag_props.get(('entity-category-markup', se.tag)):
                return result
            elif sc.tag_props.get(('visual-style', se.tag)):
                return result
            elif sc.tag_props.get(('word-p', se.tag)):
                return result
            elif sc.tag_props.get(('quotation-markup', se.tag)):
                return result
            elif sc.tag_props.get(('table-content', se.tag)):
                return result
            elif regex.match(r'(?:v|q\d?|qm\d?|qc|qr)$', se.tag):
                if result:
                    if self.verse_text and self.verse_text.get('txt'):
                        if self.verse_text['txt'] and self.verse_text['txt'][-1] not in " \n":
                            self.verse_text['txt'] += ' '
                        self.verse_text['txt'] += result
                        self.update_line_info_based_on_current_position(so)
                    elif regex.search(r'\S', result):
                        self.verse_text = {"bk": self.book_id, "c": self.chapter_number,
                                           "v": str(self.verse_number), "type": "v"}
                        if va_s := se.attributes.get('va'):
                            self.verse_text['va'] = va_s
                        if line_s := self.line_info_based_on_se_position(se):
                            self.verse_text['l'] = line_s
                        # self.update_line_info_based_on_current_position(so)
                        self.verse_text['txt'] = result
            elif regex.match(r'(?:c|q\d?|qm\d?|qc|qr)$', se.tag):
                pass
            elif sc.tag_props.get(('one-liner', se.tag)):
                misc_dict = {"bk": self.book_id}
                if self.chapter_number:
                    misc_dict["c"] = self.chapter_number
                if self.verse_number:
                    misc_dict["v"] = str(self.verse_number)
                misc_dict["type"] = "o"
                misc_dict["tag"] = se.tag
                sc.other_tag_count_dict[se.tag] += 1
                if line_s := self.line_info_based_on_se_position(se):
                    misc_dict['l'] = line_s
                if result:
                    misc_dict['txt'] = result
                self.misc_texts.append(misc_dict)
            elif sc.tag_props.get(('registered-tag', se.tag)):
                return result
        return None


class LineStruct:
    def __init__(self, s: str,
                 line: int | None = None,       # starting with 1
                 filename: str | None = None,
                 prev_ls: LineStruct | None = None,
                 next_ls: LineStruct | None = None,
                 from_line_number: int | None = None,
                 to_line_number: int | None = None,
                 from_col: int | None = None,   # starting with 1
                 to_col: int | None = None,
                 original_lines: list[LineStruct] | None = None,
                 revised_lines: list[LineStruct] | None = None):
        self.s = s
        self.repaired_s = None
        self.filename = filename
        self.line_number = line
        self.prev_ls = prev_ls
        self.next_ls = next_ls
        self.from_line_number = from_line_number
        self.to_line_number = to_line_number
        self.from_col = from_col
        self.to_col = to_col
        self.original_lines = original_lines or []
        self.revised_lines = revised_lines or []
        self.revised_line_number = None
        self.book_id = None
        self.chapter = None
        self.verse = None

    def file_loc(self, revised_line_number_p: bool = False) -> tuple[str, str, str]:
        # returns primary surf location (e.g. book/chapter/verse), secondary surf location (e.g. filename/line_number)
        elements = []
        file_loc \
            = f"{self.from_line_number or ''}:{self.from_col or ''}-{self.to_line_number or ''}:{self.to_col or ''}"
        if revised_line_number_p and self.revised_line_number and (self.revised_line_number != self.from_line_number):
            file_loc = f"l.{self.revised_line_number}"
        elif (self.from_line_number
              and ((self.to_line_number is None)
                   or (self.to_line_number and (self.from_line_number == self.to_line_number)))):
            if (next_ls := self.next_ls) and (next_ls.from_line_number > self.from_line_number):
                file_loc = f"l.{self.from_line_number}"
            else:
                file_loc = f"l.{self.from_line_number}:{self.from_col}-{self.to_col}"
        elif self.from_line_number and self.to_line_number and (self.from_line_number < self.to_line_number):
            if (next_ls := self.next_ls) and (next_ls.from_line_number > self.to_line_number):
                file_loc = f"l.{self.from_line_number}-{self.to_line_number}"
            else:
                file_loc = f"l.{self.from_line_number}-{self.to_line_number}:{self.to_col}"
        if self.book_id:
            elements.append(self.book_id)
        if self.chapter and self.verse:
            elements.append(f"{self.chapter}:{self.verse}")
        elif self.chapter:
            elements.append(f"{self.chapter}")
        return ' '.join(elements), self.filename, file_loc

    def __str__(self) -> str:
        primary_loc, filename, file_loc = self.file_loc()
        result = primary_loc
        if filename not in primary_loc or file_loc not in primary_loc:
            if primary_loc:
                result += f" ({filename} {file_loc})"
            else:
                result = f"{filename} {file_loc}"
        result += f" {self.s}"
        if self.repaired_s:
            result += f' --> {self.repaired_s}'
        return result

    def __repr__(self) -> str:
        return str(self)


class FileLineStruct:
    def __init__(self,
                 filename: str | Path | None = None,       # preferred arg
                 lines: list[str] | None = None,           # alternative arg
                 sc: UsfmCheck | None = None):
        self.line_structs = {}  # key: line_number, value: LineStruct
        self.first_ls = None
        self.last_ls = None
        self.current_ls = None
        self.carriage_returns = []    # line numbers with \r
        self.only_linefeeds = []      # line numbers with \n but without carriage_return \r
        self.n_linefeeds = 0          # number of lines with linefeed \n
        self.lines_end_in_cr_lf: bool | None = None
        self.filename = filename
        if filename and not lines:
            with open(filename, 'r', newline='') as f:
                # lines = f.read().rstrip('\n').split('\n')
                lines = f.readlines()
                for i, line in enumerate(lines, 1):
                    if line.endswith('\r\n'):
                        self.carriage_returns.append(i)
                        self.n_linefeeds += 1
                    elif line.endswith('\n'):
                        self.only_linefeeds.append(i)
                        self.n_linefeeds += 1
                    ls = LineStruct(line, line=i, from_line_number=i, to_line_number=i, from_col=1, to_col=len(line),
                                    filename=os.path.basename(self.filename))
                    self.line_structs[i] = ls
                    if prev_ls := self.line_structs.get(i-1):
                        prev_ls.next_ls = ls
                        ls.prev_ls = prev_ls
                self.first_ls = self.line_structs[1]
                self.last_ls = self.line_structs[len(lines)]
        n_carriage_returns = len(self.carriage_returns)
        n_only_linefeeds = len(self.only_linefeeds)
        if n_carriage_returns > 0 and n_carriage_returns == self.n_linefeeds:
            self.lines_end_in_cr_lf = True
        elif n_carriage_returns == 0 and self.n_linefeeds > 0:
            self.lines_end_in_cr_lf = False
        elif 0 < n_carriage_returns < self.n_linefeeds:
            error_location = os.path.basename(filename)
            if n_carriage_returns > self.n_linefeeds * 0.66:
                error_cat = ('Info', 'Inconsistent carriage return usage',
                             'Minority of lines in file do NOT include an extra carriage return before linefeed')
                plural_s = "" if n_only_linefeeds == 1 else "s"
                error_context = (f"line{plural_s} " + group_integers_into_spans(self.only_linefeeds, max_n_spans=10)
                                 + (f" ({n_only_linefeeds} out of {self.n_linefeeds} of lines)"
                                    if n_only_linefeeds > 3 else ""))
                self.lines_end_in_cr_lf = True
            elif n_carriage_returns < self.n_linefeeds * 0.33:
                error_cat = ('Info', 'Inconsistent carriage return usage',
                             'Minority of lines in file include an extra carriage return before linefeed')
                plural_s = "" if n_carriage_returns == 1 else "s"
                error_context = (f"line{plural_s} " + group_integers_into_spans(self.carriage_returns, max_n_spans=10)
                                 + (f" ({n_carriage_returns} out of {self.n_linefeeds} lines)"
                                    if n_carriage_returns > 3 else ""))
            else:
                error_cat = ('Info', 'Inconsistent carriage return usage',
                             'Comparable number of lines in file with and without carriage return before linefeed')
                error_context = f"With CR: {len(self.carriage_returns)}; without CR: {len(self.only_linefeeds)}"
            # sys.stderr.write(f"EOL for {filename}: \\r: {n_carriage_returns} \\n: {self.n_linefeeds}\n")
            sc.record_error(error_cat, error_location, error_context)

    def combine_lines(self, lss: list[LineStruct]) -> LineStruct:
        comb_ls = LineStruct(''.join(map(lambda x: x.s, lss)),
                             filename=lss[0].filename,
                             from_line_number=lss[0].from_line_number,
                             to_line_number=lss[-1].to_line_number,
                             from_col=lss[0].from_col,
                             to_col=lss[-1].to_col,
                             prev_ls=lss[0].prev_ls,
                             next_ls=lss[-1].next_ls,
                             original_lines=lss)
        if prev_ls := lss[0].prev_ls:
            prev_ls.next_ls = comb_ls
        else:
            self.first_ls = comb_ls
        if next_ls := lss[-1].next_ls:
            next_ls.prev_ls = comb_ls
        else:
            self.last_ls = comb_ls
        for orig_ls in lss:
            orig_ls.revised_lines.append(comb_ls)
        return comb_ls

    def split_line(self, ls: LineStruct, s_fragments: list[str], _sc: UsfmCheck) -> List[LineStruct]:
        """Splits line and returns list of new split LineStruct"""
        current_from_line_number = ls.from_line_number
        current_from_col = ls.from_col
        new_lss = []
        for s_fragment in s_fragments:
            n_newlines = s_fragment.count('\n')
            s_after_last_newline = regex.sub(r'.*\n', '', s_fragment)
            to_col = len(s_after_last_newline) if n_newlines else current_from_col + len(s_fragment) - 1
            new_ls = LineStruct(s_fragment,
                                filename=ls.filename,
                                from_line_number=current_from_line_number,
                                to_line_number=current_from_line_number + n_newlines,
                                from_col=current_from_col,
                                to_col=to_col,
                                original_lines=[ls])
            if new_lss:
                new_ls.prev_ls = new_lss[-1]
                new_lss[-1].next_ls = new_ls
            new_lss.append(new_ls)
            current_from_line_number = new_ls.to_line_number
            current_from_col = new_ls.to_col + 1
        ls.revised_lines = new_lss
        prev_ls = ls.prev_ls
        new_lss[0].prev_ls = prev_ls
        if prev_ls:
            prev_ls.next_ls = new_lss[0]
        else:
            self.first_ls = new_lss[0]
        next_ls = ls.next_ls
        new_lss[-1].next_ls = next_ls
        if next_ls:
            next_ls.prev_ls = new_lss[-1]
        else:
            self.last_ls = new_lss[-1]
        return new_lss

    def split_usfm_chapters_and_verses(self, sc: UsfmCheck) -> None:
        next_ls = self.first_ls
        while current_ls := next_ls:
            next_ls = current_ls.next_ls
            if m := regex.match(r'(.*?)(\\[cv]\b.*)', current_ls.s, regex.DOTALL):
                s_fragment, rest = m.group(1, 2)
                if regex.search(r'\S', m.group(1)):
                    prev_ls = current_ls.prev_ls
                    # sys.stderr.write(f"  ** GHJ1 {prev_ls.s} + {current_ls.s}\n")
                    split_lines = self.split_line(current_ls, [s_fragment, rest], sc)
                    if prev_ls:
                        _combined_line = self.combine_lines([prev_ls, split_lines[0]])
                        # sys.stderr.write(f"  ** GHJ2 {_combined_line.s} + {split_lines[1].s}\n")
                    else:
                        sc.n_operations_in_split_usfm_chapters_and_verses += 1
                        # sys.stderr.write(f"  ** GHJ3 {split_lines[0].s} + {split_lines[1].s}\n")
            if regex.search(r'\\[cv]\b.*\\[cv]\b', current_ls.s, regex.DOTALL):
                error_location = f"{os.path.basename(sc.current_filename)} l.{current_ls.from_line_number}"
                error_location = sc.add_versification(error_location, ignore_chapter=True)
                for core_tag in ('c', 'v'):
                    if regex.search(fr'\\{core_tag}\b.*\\{core_tag}\b', current_ls.s, regex.DOTALL):
                        error_cat = ('Auto-repairable errors',
                                     'Unexpected multiple instances of the same tag in same line', f'\\{core_tag}')
                        sc.record_error(error_cat, error_location, current_ls.s)
                if regex.search(r'\\c\b', current_ls.s) and regex.search(r'\\v\b', current_ls.s,
                                                                         regex.DOTALL):
                    error_cat = ('Auto-repairable errors',
                                 'Unexpected occurrence of both chapter and verse tags on the same line')
                    sc.record_error(error_cat, error_location, current_ls.s)
                s_fragments = []
                rest = current_ls.s
                while m := regex.match(r'(.*?\S.*?)(\\[cv]\b.*)', rest, regex.DOTALL):
                    s_fragment, rest = m.group(1, 2)
                    s_fragments.append(s_fragment)
                s_fragments.append(rest)
                if len(s_fragments) > 1:
                    self.split_line(current_ls, s_fragments, sc)
                    sc.n_operations_in_split_usfm_chapters_and_verses += 1
                    sc.n_additional_lines_in_split_usfm_chapters_and_verses += len(s_fragments) - 1
                    # sys.stderr.write(f"SPLIT {self.filename} {current_ls.from_line_number} {repr(s_fragments)}\n")

    @staticmethod
    def expand_usfm_verse(anchor_ls: LineStruct, next_ls: LineStruct, sc: UsfmCheck) -> bool:
        # Determines whether next_ls should be combined with anchor_ls as a continuation of \v, \q etc.
        if next_ls.from_line_number - anchor_ls.from_line_number >= 20:
            return False
        for tag in regex.findall(r'\\([a-z]+\d?)', next_ls.s):   # \f, \x etc. ok, but not \id, \c, \v
            if sc.tag_props.get(('paragraph-format', sc.core_tag(tag)[0])):
                pass
            elif sc.tag_props.get(('table-content', sc.core_tag(tag)[0])):
                pass
            elif sc.tag_props.get(('one-liner', sc.core_tag(tag)[0])):
                return False
        return True

    def expand_usfm_verses(self, sc: UsfmCheck) -> None:
        # Combines lines anchor_ls \v, \q etc. with any continuation line (non-one-liners, e.g. plain text)
        current_ls = self.first_ls
        while current_ls:
            expanded_lss = [current_ls]
            if regex.match(r'\s*\\(?:v|q\d?|qm\d?|qc|qr|ip|periph|rem)\b', current_ls.s):
                while next_ls := current_ls.next_ls:
                    if self.expand_usfm_verse(expanded_lss[0], next_ls, sc):
                        expanded_lss.append(next_ls)
                        current_ls = next_ls
                    else:
                        break
                if len(expanded_lss) > 1:
                    self.combine_lines(expanded_lss)
                    sc.n_operations_in_expand_usfm_verses += 1
                    sc.n_fewer_lines_in_expand_usfm_verses += len(expanded_lss) - 1
            current_ls = expanded_lss[-1].next_ls


class UsfmObject:
    def __init__(self, s: str, usfm_check: UsfmCheck,
                 filename: str | None, start_line_number: int = 1, start_column: int = 1):
        self.sc = usfm_check
        self.elements = []
        self.open_elements = []
        self.open_tags = []
        self.s = s                             # full string, can include newline characters
        self.rest = s                          # still to be processed
        self.current_filename = filename
        self.current_line_number = start_line_number  # starting at 1
        self.current_column = start_column     # starting at 1
        self.versification = None
        self.verbose = set()
        # self.verbose = {'new', 'attach', 'closing'}
        # self.verbose = {'closing'}
        # self.subsumed_elements = set()

        self.process_usfm_elements()
        self.post_process()

    def post_process(self) -> None:
        # close tags; more tests to follow
        for open_element in self.open_elements:
            open_tag = open_element.open_tag
            if self.sc.tag_props.get(('closing-p', open_tag)):
                open_element.is_open = False
                open_element.end_position = self.current_position()

    def close_applicable_open_elements_at_end_of_line(self) -> None:
        for open_element_pos, open_element in enumerate(self.open_elements):
            tag = open_element.tag
            if tag in self.sc.tag_props.get(('closes', "end-of-line"), []):
                versification = self.versification
                # sys.stderr.write(f"** CCC {open_element_pos} {tag} {versification} "
                #                  f"line:{self.sc.current_line} \n")
                while len(self.open_elements) > open_element_pos:
                    o = self.open_elements[-1]
                    # sys.stderr.write(f"  ** Closing {versification}\n{o}")
                    o.close_tag = None
                    o.is_open = False
                    o.end_position = self.current_position()
                    error_cat = ('Silent', 'Paired tags',
                                 'Absence of close-tag conforms to guidelines, '
                                 'but implied close-tag was explicitly used in many other places.',
                                 f'Implied close-tag: \\{o.tag}*')
                    self.sc.record_error(error_cat, versification, self.sc.current_line, f"I-no-\\{o.tag}*")
                    # sys.stderr.write(f"  record_error {versification} {error_cat} \n")
                    self.pop_last_stack_element()
                return

    def pretty_loc(self) -> str:
        return f"[{self.current_line_number}:{self.current_column}]"

    def current_position(self) -> tuple[int, int]:
        return self.current_line_number, self.current_column

    def process_usfm_elements(self):
        while self.rest:
            if m3 := regex.match(r'(.*?)(\\\+?[a-z]+[0-9]*[ \*]?)(.*)$', self.rest,
                                 flags=regex.IGNORECASE | regex.DOTALL):
                pre, tag, rest = m3.group(1, 2, 3)
                if pre != '':
                    self.elements.append(pre)
                    self.update_current_position(pre)
                if tag.endswith('*'):
                    UsfmElement(self)
                    self.update_current_position(tag)
                else:
                    UsfmElement(self)
            elif self.rest != '':
                self.elements.append(self.rest)
                self.update_current_position(self.rest)

    def update_current_position(self, s: str):
        if n_newlines := s.count('\n'):
            self.current_line_number += n_newlines
            self.current_column = len(s.replace(r'.*\n', '')) + 1
        else:
            self.current_column += + len(s)
        self.rest = self.rest[len(s):]

    def pop_last_stack_element(self) -> UsfmElement | None:
        if self.open_elements:
            open_element = self.open_elements[-1]
            open_element.is_open = False
            open_element.end_position = self.current_position()
            del self.open_elements[-1]
            del self.open_tags[-1]
            return open_element
        else:
            return None

    def attachment_eligible(self, parent_element: UsfmElement, child_element: UsfmElement | None) -> bool:
        if child_element is None:
            return True
        if child_element is parent_element:
            return False
        if isinstance(parent_element, str) or isinstance(child_element, str):
            return True
        parent_tag = parent_element.tag
        child_tag = child_element.tag
        if parent_tag in self.sc.tag_props.get(('exclusive-siblings', child_tag), ()):
            return False
        return True

    def last_open_element(self, exception_element: UsfmElement | None = None) -> UsfmElement | None:
        for open_element in reversed(self.open_elements):
            if self.attachment_eligible(open_element, exception_element):
                return open_element
        return None

    def attach_element(self, element: UsfmElement | str):
        """Attach new element as appropriate, at top level or as sub-element"""
        if self.open_tags and (parent := self.last_open_element(element)):
            parent.sub_elements.append(element)
            if isinstance(element, UsfmElement):
                element.parent = parent
                self.sc.stats_key_values[('tag-children', parent.tag)].add(element.tag)
                self.sc.stats_counts[('tag-children', parent.tag, element.tag)] += 1
                self.sc.stats_key_values[('tag-parents', element.tag)].add(parent.tag)
                self.sc.stats_counts[('tag-parents', element.tag, parent.tag)] += 1
                if redirections := self.sc.tag_props.get(('redirections', element.tag)):
                    redirected = False
                    for open_element in self.open_elements[::-1]:
                        if redirected:
                            break
                        for redirection in redirections:
                            if open_element.tag == (improper_parent_tag := redirection.get('improper-parent')):
                                proper_parent_tag = redirection.get('proper-parent')
                                equivalent_child = redirection.get('equivalent-child-at-improper-parent')
                                last_error_cat = f'Did not expect \\{element.tag} under \\{improper_parent_tag}.'
                                if proper_parent_tag:
                                    last_error_cat += (f' Instead, \\{element.tag} is a sub-tag of '
                                                       f'\\{proper_parent_tag}.')
                                if equivalent_child:
                                    last_error_cat += (f' Under \\{improper_parent_tag}, a more appropriate tag '
                                                       f'might be \\{equivalent_child}')
                                    if equivalent_child_exp := self.sc.tag_props.get(('exp', equivalent_child)):
                                        last_error_cat += f' ("{equivalent_child_exp}")'
                                error_cat = ('Errors', 'Unexpected sub-tag', last_error_cat)
                                self.sc.record_error(error_cat, self.sc.versification(), self.sc.current_line)
                                redirected = True
                                break
        else:
            parent = None
            self.elements.append(element)
        if isinstance(element, str):
            self.update_current_position(element)
        if ('attach' in self.verbose) and isinstance(element, UsfmElement) and (parent is None):
            sys.stderr.write(f"Attach OL: {list(map(lambda x: x.id, self.open_elements))} "
                             f"EL: {element if isinstance(element, str) else element.id} "
                             f"-> {parent.id if parent else 'top'}\n")

    def pprint(self) -> str:
        result = ''
        for element in self.elements:
            result += repr(element).rstrip() + '\n'
        return result

    def flat_print(self) -> str:
        result = ''
        for element in self.elements:
            if isinstance(element, UsfmElement):
                result += element.flat_print()
            else:
                result += element
        return result

    def check(self, filename_loc: str):
        for element in self.elements:
            if isinstance(element, UsfmElement):
                element.check(filename_loc)

    def extract_struct_args(self):
        for element in self.elements:
            if isinstance(element, UsfmElement):
                element.extract_struct_args()

    def repair(self, filename_loc: str, fls: FileLineStruct | None = None):
        for element in self.elements:
            if isinstance(element, UsfmElement):
                element.repair(filename_loc, fls)


class UsfmElement:
    def __init__(self, so: UsfmObject):
        global n_usfm_objects
        n_usfm_objects += 1
        self.id = f"i{n_usfm_objects}"
        self.start_position = so.current_position()  # (line number, column number)
        self.end_position = None          # (line number, column number)
        self.is_open = False
        self.tag = None                   # e.g. mt1, bk
        self.open_tag = None              # e.g. \mt1, \mt, \+bk (or None if, in error, there is only a close_tag)
        self.close_tag = None             # e.g. \mt1*, \mt*, \+bk* (or None if not explicitly closed)
        self.attributes = {}
        self.left_arg_s = None            # e.g. surface arg string before sub_elements, e.g. the "16 " in "\v 16 hello"
        self.right_arg_s = None           # e.g. surface arg string after sub_elements, e.g. the "|..." in "\w ..."
        self.sub_elements = []  # list of sub-elements which can be str or UsfmObject
        self.parent = None
        self.so = so

        sc = so.sc
        versification = sc.versification()
        # open tag
        if m2 := regex.match(r'(\\\+?[a-z]+(?![a-z\*])[0-9]*(?![0-9\*])(?: |\r\n|\n)?)(.*)$', so.rest,
                             flags=regex.IGNORECASE | regex.DOTALL):
            tag, rest = m2.group(1, 2)
            self.tag, registered_p, missing_space, missing_1_p, missing_backslash, plus_p, close_p = sc.core_tag(tag)
            self.open_tag = tag.rstrip()
            tag_is_immediately_self_closing = sc.tag_props.get(('immediately-self-closing', self.tag))
            self.is_open = not tag_is_immediately_self_closing   # True unless self-closing
            if tag.endswith('\r\n'):
                self.attributes['newline-after-tag'] = '\r\n'
            elif tag.endswith('\n'):
                self.attributes['newline-after-tag'] = '\n'
            if missing_space:
                self.attributes['missing-space-after-tag'] = True
                if rest and sc.tag_is_registered(self.tag):
                    error_cat = ('Auto-repairable errors', 'Open tag', 'Missing space after open tag', self.open_tag)
                    error_context = sc.current_line
                    error_context += (f"  [Note: {self.open_tag} is followed by "
                                      f"{print_char_unicode_name(rest[0])}]")
                    sc.record_error(error_cat, versification, error_context)
            if (sc.current_line
                    and sc.tag_props.get(('one-liner', self.tag))
                    and (not sc.tag_props.get(('paragraph-format', self.tag)))
                    and (not sc.tag_props.get(('table-content', self.tag)))
                    and so.current_column > 1):
                tags = regex.findall(fr'\\\+?{self.tag}\b(?!\*)', sc.current_line)
                tag_at_start_of_line_p = bool(regex.match(fr'(?:.*?\n)?\\\+?{self.tag}(?!\*)', sc.current_line))
                if len(tags) >= 2:
                    error_cat = ('Errors', 'Unexpected multiple instances of the same tag in same line',
                                 '\\' + self.tag)
                    if versification not in sc.error_locations[error_cat]:
                        for _ in tags:
                            sc.record_error(error_cat, versification, sc.current_line)
                if not tag_at_start_of_line_p:
                    pre_tag = sc.current_line[:so.current_column - 1]
                    if regex.match(r'(\pZ|\pC)+$', pre_tag):
                        error_top_cat = 'Auto-repairable errors'
                    else:
                        error_top_cat = 'Errors'
                    error_cat = (error_top_cat, 'Expected the following tags to be at the beginning of the line',
                                 '\\' + self.tag)
                    error_context = sc.current_line
                    if ((so.current_column > 1)
                            and sc.current_line
                            and pre_tag
                            and not regex.search(r'\S', pre_tag)):
                        error_context += f"  [Note: \\{self.tag} is preceded by {print_char_unicode_name(pre_tag[-1])}]"
                    sc.record_error(error_cat, versification, error_context)
            for closable_tag in so.sc.tag_props.get(('closes', self.tag), []):
                if closable_tag in so.open_tags:
                    # sys.stderr.write(f"  CC ct:{closable_tag} lop:{so.open_tags[-1]} st:{self.tag} {versification}\n")
                    if so.open_tags[-1] == closable_tag:
                        o = so.open_elements[-1]
                        o.end_position = so.current_position()
                        o.close_tag = None
                        o.is_open = False
                        so.pop_last_stack_element()
                        if closable_tag == self.tag:
                            error_cat = ('Silent', 'Paired tags',
                                         'Absence of close-tag conforms to guidelines, '
                                         'but implied close-tag was explicitly used in many other places.',
                                         f'Implied close-tag: \\{self.tag}*')
                            so.sc.record_error(error_cat, versification, sc.current_line,
                                               f"I-no-\\{self.tag}*")
                        if 'closing' in so.verbose:
                            sys.stderr.write(f"Closed-by-based closing {o.id} {o.open_tag} {o.close_tag}"
                                             f" {o.end_position} {so.open_tags}\n")
            if not tag_is_immediately_self_closing:
                so.open_elements.append(self)
                so.open_tags.append(self.tag)
            so.update_current_position(tag)
            so.attach_element(self)
            so.sc.record_tag(self.tag, open_tag=self.open_tag)
            # Check for any args (e.g. \v number, \c number, \f +, \w content|attributes\w* etc.)
            if self.tag == 'v':
                if m := regex.match(r'(\s*\d+(?:[ab](?=\s)|)\u200F?(?:[-,]\d+(?:[ab](?=\s)|))*\s*)', so.rest):
                    self.left_arg_s = m.group(1)
                    so.update_current_position(self.left_arg_s)
            elif self.tag == 'c':
                if m := regex.match(r'(\s*[0-9]+\s*)', so.rest):
                    self.left_arg_s = m.group(1)
                    so.update_current_position(self.left_arg_s)
            elif self.tag in ('f', 'ef', 'fe'):
                if m := regex.match(r'(\s*(?:\+|-|[a-zA-Z0-9]+)\s*)', so.rest):
                    self.left_arg_s = m.group(1)
                    so.update_current_position(self.left_arg_s)
            elif sc.tag_props.get(('can-have-attributes', self.tag)):  # e.g. \w word|attributes\w*
                if m := regex.match(r'([^\\\|]*)(\|[^\\]*)\\', so.rest):
                    arg_s = m.group(1)
                    so.attach_element(arg_s)
                    self.right_arg_s = m.group(2)
                    so.update_current_position(self.right_arg_s)
                    if self.tag == 'fig':
                        fig_args = self.right_arg_s.split('|')
                        if '=' in self.right_arg_s:
                            rest = self.right_arg_s
                            while m := regex.match(r'((?:\pZ|\pC|\|)*)([a-z][-_a-zA-Z0-9]*)\s*'
                                                   r'=\s*("[^"]*"|[-_a-zA-Z0-9]+)(.*)$',
                                                   rest):
                                pre, fig_attribute, value, rest = m.group(1, 2, 3, 4)
                                if value.startswith('"') and value.endswith('"'):
                                    value = value[1:-1]
                                self.attributes[fig_attribute] = value
                            if not regex.match(r'(?:\pZ|\pC|\|)*$', rest):
                                sys.stderr.write(f" ** FIG rest: {rest} {print_str_unicode_names(rest)}\n")
                        else:
                            fig_attributes = ('desc', 'src', 'size', 'loc', 'copy', 'cap', 'ref')
                            for i, fig_attribute in enumerate(fig_attributes):
                                if i < len(fig_args) and fig_args[i]:
                                    self.attributes[fig_attribute] = fig_args[i]
        # close tag
        elif m2 := regex.match(r'(\\\+?[a-z]+[0-9]*\*)(.*)$', so.rest, regex.DOTALL):
            tag, rest = m2.group(1, 2)
            self.tag, registered_p, missing_space, missing_1_p, missing_backslash, plus_p, close_p = sc.core_tag(tag)
            self.close_tag = tag
            so.update_current_position(tag)
            self.end_position = so.current_position()
            so.attach_element(self)
            so.sc.record_tag(self.tag, close_tag=self.close_tag)
        else:
            error_cat = ('Errors', 'Paired tags', 'Missing open tag', 'Check code')
            error_context = f"rest:{so.rest}"
            so.sc.record_error(error_cat, versification, error_context)
        if 'new' in so.verbose:
            sys.stderr.write(f"New {self.open_tag or self.close_tag} {versification} {self.id}\n")

        prev_rest_length = math.inf
        while so.rest:
            if len(so.rest) >= prev_rest_length:
                break
            else:
                prev_rest_length = len(so.rest)
            if m3 := regex.match(r'(.*?)(\\\+?[a-z]+[0-9]*(?: |\*|))(.*)$', so.rest,
                                 flags=regex.IGNORECASE | regex.DOTALL):
                pre, tag, rest = m3.group(1, 2, 3)
                if pre != '':
                    so.attach_element(pre)
                if tag.endswith('*'):
                    core_tag, registered_p, missing_space, missing_1_p, missing_backslash, plus_p, close_p \
                        = sc.core_tag(tag)
                    if self.tag:
                        if (core_tag == self.tag) and self.is_open:
                            so.update_current_position(tag)
                            self.end_position = so.current_position()
                            self.close_tag = tag.rstrip()
                            self.is_open = False
                            so.sc.record_tag(self.tag, close_tag=self.close_tag, new_tag=False)
                            so.pop_last_stack_element()
                            if 'closing' in so.verbose:
                                print(f"Direct-closing {self.id} {self.open_tag} {self.close_tag} {self.end_position}"
                                      f" {so.open_tags}")
                            return
                        elif core_tag in so.open_tags:
                            while o := so.last_open_element():
                                assert (isinstance(o, UsfmElement))
                                self.end_position = so.current_position()
                                self.is_open = False
                                if o.tag == core_tag:
                                    so.update_current_position(tag)
                                    o.end_position = so.current_position()
                                    o.close_tag = tag.rstrip()
                                    o.is_open = False
                                    so.sc.record_tag(o.tag, close_tag=o.close_tag, new_tag=False)
                                    so.pop_last_stack_element()
                                    if 'closing' in so.verbose:
                                        sys.stderr.write(f"Matching-closing {o.id} {o.open_tag} {o.close_tag}"
                                                         f" {o.end_position} {so.open_tags}\n")
                                    return
                                else:
                                    o.end_position = so.current_position()
                                    o.close_tag = None
                                    o.is_open = False
                                    so.pop_last_stack_element()
                                    if 'closing' in so.verbose:
                                        sys.stderr.write(f"Self-closing {o.id} {o.open_tag} {o.close_tag}"
                                                         f" {o.end_position} {so.open_tags}\n")
                        else:
                            se = UsfmElement(so)
                            if so.rest.startswith(tag):
                                location = f"{so.current_filename} l.{so.current_line_number}:{so.current_column}"
                                sys.stderr.write(f"** Warning: check code X1 {location} {se.tag} {tag}::{so.rest}::\n")
                                # so.update_current_position(tag)
                else:
                    UsfmElement(so)
            elif so.rest != '':
                so.attach_element(so.rest)

    def __str__(self):
        return self.pprint()

    def __repr__(self):
        return self.pprint()

    @staticmethod
    def append_element(anchor: UsfmElement | list, element: UsfmElement | str, _d: dict, _caller_id: str = ''):
        # element_repr = element.id if isinstance(element, SfmObject) else repr(element)
        if isinstance(anchor, UsfmElement):
            # anchor_repr = anchor.id
            if element not in anchor.sub_elements:
                anchor.sub_elements.append(element)
        else:  # top level
            if element not in anchor:
                anchor.append(element)
            # anchor_repr = 'top'
        # print(f"Anchor: {anchor_repr} E:{element_repr} cid:{_caller_id} {anchor == _d['elements']}")
        # if anchor_repr == 'top':
        #     print(f"Added to {anchor_repr}: {element_repr} {caller_id}")

    def pprint(self, indent: str = '', max_depth: int = 10) -> str:
        result = ''
        if self.tag:
            result += indent + '\\' + self.tag
            start_line, start_column = self.start_position
            if self.end_position:
                end_line, end_column = self.end_position
                if end_column:
                    end_pprint = f"{end_line}:{end_column-1}"
                else:
                    end_pprint = f"{end_line}:None"
            else:
                end_pprint = None
            result += f" [{start_line}:{start_column}-{end_pprint}]"
            if not self.open_tag:
                result += f" [self-opening]"
            if self.is_open:
                result += f" [open]"
            elif not self.close_tag:
                result += f" [self-closing]"
            if self.id:
                result += f" {self.id}"
            if self.parent:
                result += f" p:\\{self.parent.tag}"
            if self.left_arg_s:
                result += f" las:{self.left_arg_s}"
            if self.right_arg_s:
                result += f" ras:{self.right_arg_s}"
            for attribute in self.attributes:
                value = self.attributes.get(attribute)
                result += f" {attribute}:{value}"
            result += "\n"
            if max_depth >= 1:
                for sub_element in self.sub_elements:
                    if isinstance(sub_element, UsfmElement):
                        result += sub_element.pprint(indent + '    ', max_depth-1)
                    else:
                        result += indent + '    "' + sub_element + '"\n'
        return result

    def flat_print(self) -> str:
        result = ''
        if self.tag:
            if self.open_tag:
                result += self.open_tag
                if newline := self.attributes.get('newline-after-tag'):
                    result += newline  # might also include carriage return before newline character
                elif not self.attributes.get('missing-space-after-tag'):
                    result += ' '
            if self.left_arg_s:
                result += self.left_arg_s
            for sub_element in self.sub_elements:
                if isinstance(sub_element, UsfmElement):
                    result += sub_element.flat_print()
                else:
                    result += sub_element
            if self.right_arg_s:
                result += self.right_arg_s
            if self.close_tag:
                result += self.close_tag
        return result

    def pretty_loc(self) -> str:
        start_line, start_column = self.start_position
        result = f"{start_line}:{start_column}-"
        if self.end_position:
            end_line, end_column = self.end_position
            result += f"{end_line}:{end_column-1}"
        else:
            result += "None"
        return result

    @staticmethod
    def add_plus_to_tag(tag: str) -> str:
        if tag.startswith('\\+'):
            return tag
        elif tag.startswith('\\'):
            return '\\+' + tag[1:]

    def nested_pattern(self, child: UsfmElement, plus: bool = False) -> str:
        child_open_tag_w_plus = self.add_plus_to_tag(child.open_tag) if plus else child.open_tag
        child_close_tag_w_plus = self.add_plus_to_tag(child.close_tag) if plus and child.close_tag else child.close_tag
        result = f"{self.open_tag} ... {child_open_tag_w_plus}"
        if child.close_tag:
            result += f" ... {child_close_tag_w_plus}"
        if self.close_tag:
            result += f" ... {self.close_tag}"
        else:
            result += " ..."
        return result

    def check(self, filename_loc: str):
        subtag_count = defaultdict(int)
        so = self.so
        sc = so.sc
        loc = sc.versification() or filename_loc
        loc_book = sc.current_book_id
        if not sc.tag_is_registered(self.tag):
            error_string = sc.current_line
            if m := regex.match(r'([vc])(\d+)', self.tag):
                tag, number = m.group(1, 2)
                error_string += f'  [Did you mean \\{tag} {number} (with a space between \\{tag} and {number})?]'
            elif self.tag.endswith('1') and sc.tag_is_registered(self.tag[:-1]):
                error_string += f'  [Did you mean \\{self.tag[:-1]} (without the final "1")?]'
            error_cat_top = 'Severe errors'
            unrecognized_elem = 'Unrecognized tags'
            if self.tag.startswith("z"):
                error_cat_top = 'Info'
                unrecognized_elem = 'User-defined tags'
                loc = sc.current_book_id or filename_loc
                error_string = None
                sc.user_defined_tags.add(self.tag)
            elif regex.match(r'v\d+$', self.tag):
                unrecognized_elem += ', presumably due to a missing space between \\v and verse number'
                error_cat_top = 'Auto-repairable errors'
            error_cat = (error_cat_top, 'Tags', unrecognized_elem, f'\\{self.tag}')
            self.so.sc.record_error(error_cat, loc, error_string)
        if self.open_tag and self.close_tag and not (self.open_tag + '*' == self.close_tag):
            error_cat = ('Errors', 'Paired tags', 'Open/close tags do not match',
                         f'{self.open_tag}...{self.close_tag}')
            self.so.sc.record_error(error_cat, loc, None)
        # self.parent.tag sc.tag_props.get(('dont-close-inside', self.tag), [])
        if (sc.tag_props.get(('closing-p', self.tag)) is True) and (self.close_tag is None):
            dont_close_inside_tags = sc.tag_props.get(('dont-close-inside', self.tag), [])
            if dont_close_inside_tags and self.parent and (self.parent.tag in dont_close_inside_tags):
                error_message = f"Closing tag exemption for {self.tag} inside {self.parent.tag}"
                if error_message not in sc.log_message_count:
                    sys.stderr.write(error_message + '\n')
                sc.log_message_count[error_message] += 1
            else:
                error_cat = ('Errors', 'Paired tags', 'Missing closing tag', f'Missing closing tag {self.open_tag}*')
                sc.record_error(error_cat, loc, sc.current_line)
        elif (sc.tag_props.get(('closing-p', self.tag)) is True) and self.close_tag:
            dont_close_inside_tags = sc.tag_props.get(('dont-close-inside', self.tag), [])
            if dont_close_inside_tags and self.parent and (self.parent.tag in dont_close_inside_tags):
                error_cat_element = f'Unexpected close tag {self.open_tag}*'
                if self.tag == 'xt':
                    sc.error_cat_element_to_explanation_id[error_cat_element] = 'XT-STAR'
                error_cat = ('Auto-repairable errors', 'Paired tags', 'Unexpected close tag in context',
                             f'Parent tag: \\{self.parent.tag}', error_cat_element)
                sc.record_error(error_cat, loc, sc.current_line)
        elif (sc.tag_props.get(('closing-p', self.tag)) is False) and (self.close_tag is not None):
            if sc.tag_props.get(('closing-deprecated', self.tag)):
                error_cat_element = f'Deprecated close tag {self.close_tag}'
                if self.tag == 'fq':
                    sc.error_cat_element_to_explanation_id[error_cat_element] = 'FQ-STAR'
                elif self.tag == 'fqa':
                    sc.error_cat_element_to_explanation_id[error_cat_element] = 'FQA-STAR'
                elif self.tag == 'ft':
                    sc.error_cat_element_to_explanation_id[error_cat_element] = 'FT-STAR'
                error_cat = ('Auto-repairable errors', 'Paired tags', 'Deprecated close tag', error_cat_element)
            else:
                error_cat = ('Errors', 'Paired tags', 'Unexpected close tag',
                             f'Unexpected close tag for {self.open_tag}: {self.close_tag}')
            display_element: UsfmElement = self.parent or self
            display_string = display_element.flat_print()
            sc.record_error(error_cat, loc, display_string, f"E-\\{self.tag}*")
        if self.close_tag and not self.open_tag:

            error_cat = ('Errors', 'Paired tags', 'Missing open tag',
                         f'Missing open tag {self.close_tag.removesuffix("*")}')
            sc.record_error(error_cat, loc, sc.current_line)
        if self.open_tag:
            tag_variant = sc.core_tag(self.open_tag, norm1=False)[0]
            if sc.tag_props.get(('registered-tag', tag_variant + '1')):
                sc.tag_locations[tag_variant].append(loc_book)
            elif tag_variant.endswith('1') and sc.tag_props.get(('registered-tag', tag_variant)):
                sc.tag_locations[tag_variant].append(loc_book)
        for element in self.sub_elements:
            if isinstance(element, UsfmElement):
                subtag_count[element.tag] += 1
                # Change \tag to \+tag inside nested markup
                if sc.user in ('dev', None):
                    if not (sc.tag_props.get(('one-liner', self.tag))
                            or (element.open_tag is None)
                            or (element.tag in sc.tag_props.get(('children', self.tag), []))
                            or (element.open_tag.startswith('\\+'))):
                        if sc.tag_props.get(('can-have-entity-category-markup-children', self.tag)) \
                                and sc.tag_props.get(('entity-category-markup', element.tag)) \
                                and sc.tag_props.get(('closing-p', element.tag)) \
                                and element.close_tag:
                            error_cat_top = 'Auto-repairable errors'
                        elif sc.tag_is_registered(self.tag) and sc.tag_is_registered(element.tag):
                            error_cat_top = 'Warnings'
                        else:
                            error_cat_top = None
                        if error_cat_top:
                            recommendation = (f"Nested tags '{self.nested_pattern(element)}' "
                                              f"should be changed to '{self.nested_pattern(element, plus=True)}'")
                            error_cat = (error_cat_top, 'Sub tags', 'Change \\tag to \\+tag inside nested markup',
                                         recommendation)
                            display_element = self
                            while display_element.parent and display_element.parent.tag in ('f', 'ft'):
                                display_element = display_element.parent
                            display_string = display_element.flat_print()
                            sc.record_error(error_cat, loc, display_string)
                element.check(filename_loc)
            elif isinstance(element, str):
                if self.tag in ('xt', 'toc1', 'toc2', 'toc3'):
                    sc.ref_stats.add_evidence(self.tag, element.rstrip())
                if self.tag == 'id' and sc.current_book_id:
                    sc.ref_stats.add_evidence(self.tag, sc.current_book_id)

    def parent_element_pair_need_plus_sign(self, element: UsfmElement) -> bool:
        so = self.so
        sc = so.sc
        if sc.tag_props.get(('one-liner', self.tag)):
            return False
        if sc.tag_props.get(('one-liner', element.tag)):
            return False
        if element.open_tag is None:
            return False
        if element.tag in sc.tag_props.get(('children', self.tag), []):
            return False
        if element.open_tag.startswith('\\+'):
            return False
        if not sc.tag_is_registered(element.tag):
            return False
        return True

    def repair(self, loc: str, fls: FileLineStruct | None = None) -> None:
        for i, element in enumerate(self.sub_elements):
            so = self.so
            sc = so.sc
            if isinstance(element, UsfmElement):
                if ('add-plus' in sc.repair_set) and self.parent_element_pair_need_plus_sign(element):
                    repair_message = f"Repairing {self.tag} {element.open_tag} {element.close_tag} ..."
                    sc.repair_message_counts[repair_message] += 1
                    repair_message_count = sc.repair_message_counts[repair_message]
                    max_repair_message_count = 3
                    if repair_message_count > max_repair_message_count:
                        pass
                    elif repair_message_count == max_repair_message_count:
                        sys.stderr.write(f"{repair_message} ({repair_message_count}; last mention)\n")
                    elif repair_message_count == 1:
                        sys.stderr.write(f"{repair_message}\n")
                    else:
                        sys.stderr.write(f"{repair_message} ({repair_message_count})\n")
                    orig_open_tag, orig_close_tag = element.open_tag, element.close_tag
                    element.open_tag = self.add_plus_to_tag(element.open_tag)
                    from_struct = f'\\{self.tag} ... {orig_open_tag}'
                    to_struct = f'\\{self.tag} ... {element.open_tag}'
                    if element.close_tag:
                        element.close_tag = self.add_plus_to_tag(element.close_tag)
                        from_struct += f' ... {orig_close_tag}'
                        to_struct += f' ... {element.close_tag}'
                    sc.record_repair(('Added +', f'Changed “{from_struct}” to “{to_struct}”'), loc)
                if ((element.tag in ('fq', 'fqa'))
                        and (self.tag == 'f')
                        and (f'{element.tag}-star' in sc.repair_set)  # e.g. 'fq-star'
                        and (not element.is_open)
                        and (0 < i < len(self.sub_elements) - 1)
                        and isinstance(self.sub_elements[i+1], str)):
                    # sys.stderr.write(f"FQ* -> FT {loc}\n{self.pprint()}\n")
                    open_tag = f'\\{element.tag}'
                    close_tag = f'\\{element.tag}*'
                    element.close_tag = None
                    new_cut_col = element.end_position[1] - len(close_tag)
                    element.end_position = (element.end_position[0], new_cut_col)
                    ft_element = UsfmElement(so)
                    ft_element.tag = 'ft'
                    ft_element.open_tag = '\\ft'
                    ft_element.close_tag = None
                    ft_element.sub_elements = [self.sub_elements[i+1]]
                    ft_element.start_position = (element.end_position[0], new_cut_col)
                    ft_element.end_position = (element.end_position[0],
                                               new_cut_col + len('\\ft ') + len(self.sub_elements[i+1]))
                    ft_element.parent = self
                    ft_element.parent.sub_elements[i+1] = ft_element
                    sc.record_repair(('Changed deprecated close-tag',
                                      f'Changed “\\f ...{open_tag} ...{close_tag}...” '
                                      f'to “\\f ...{open_tag} ...\\ft ...”'), loc)
                    # sys.stderr.write(f"FQ* -> FT {loc}\n{self.pprint()}\n")
                # recursion
                element.repair(loc, fls)
            elif isinstance(element, str):
                # Chapter number followed by (relatively little) spurious material
                if ('post-chapter-number' in sc.repair_set) and (self.tag == 'c') and (i == 0):
                    if m := regex.match(r'([1-9][0-9]*)(.*?)(\s*)$', element):
                        chapter_number, spurious_s, space = m.group(1, 2, 3)
                        if ((0 < len(spurious_s) < 5)
                                and ('\\' not in spurious_s)
                                and (not regex.search(r'\pL.*\pL', spurious_s))):
                            new_element = chapter_number + space
                            self.sub_elements[i] = new_element
                            if regex.search(r'(?:\pC|\pZ)', spurious_s.replace(' ', '')):
                                spurious_s2 = print_str_unicode_names(spurious_s)
                            else:
                                spurious_s2 = spurious_s
                            sc.record_repair(('Deleted spurious material',
                                              'Deleted spurious material after chapter number',
                                              f' Deleted “{spurious_s2}”'),
                                             loc)

    def get_subs(self, tags: list[str]) -> list[UsfmElement | str]:
        if tags:
            str_list = []
            sub_list = []
            if (value := self.attributes.get(tags[0])) is not None:
                return [value]
            for sub_element in self.sub_elements:
                if tags[0] == 'txt':
                    if isinstance(sub_element, str):
                        str_list.append(sub_element)
                else:
                    if isinstance(sub_element, UsfmElement) and sub_element.tag == tags[0]:
                        sub_list.extend(sub_element.get_subs(tags[1:]))
            return str_list or sub_list
        else:
            return [self]

    def extract_struct_args(self) -> None:
        for tag, sub_tag in (('v', 'va'), ('f', 'fr')):
            if self.tag == tag:
                elements = []
                for s in self.get_subs([sub_tag, 'txt']):
                    elements.append(s.strip())
                self.attributes[sub_tag] = ','.join(elements)
        for sub_element in self.sub_elements:
            if isinstance(sub_element, UsfmElement):
                sub_element.extract_struct_args()


class ReferenceStats:
    def __init__(self, sc: UsfmCheck):
        self.sc = sc
        self.book_name_evidence_types = defaultdict(list)   # value: 'file', 'toc1', 'xt', ...
        self.reference_count = defaultdict(int)
        # reference_count keys: ('xt', book)
        # reference_count keys: ('c-v-sep', ':')|('v-range', '-')|('v-list-sep', ',')|('ref-sep', ';')
        # reference_count keys: (book)|(book, chapter)|(book, chapter, verse)
        self.book_name_to_book_id = dict[str]()
        self.book_name_normalization = dict[str]()
        self.keywords = defaultdict(list)  # key: 'chapter', 'verse', 'to', 'this', 'next', ... value: list(str)
        self.n_error_messages = 0

        self.connector_re = '[-–—:.,]'
        if sc and sc.doc_config:
            if ref_words := sc.doc_config.ref_words.get(sc.lang_code):
                for kw in ref_words.get('_AND_', []) + ref_words.get('_TO_', []):
                    self.connector_re += '|' + f'\\s?{kw}\\s?'
                self.connector_re = '(?:' + self.connector_re + ')'
            if book_refs := sc.doc_config.book_refs.get(sc.lang_code):
                for book_id in book_refs.keys():
                    for book_name in [book_id] + book_refs[book_id]:
                        self.add_evidence('config', book_name)
                        self.book_name_to_book_id[book_name] = book_id
                        self.book_name_evidence_types[book_name].append('config')
                        self.book_name_normalization[book_name] = book_name
                        self.book_name_normalization[book_name.lower()] = book_name
        # sys.stderr.write(f"Connector: {self.connector_re}\n")

    def __str__(self) -> str:
        # ref-stats reference stats
        result = ''
        # result += f"IDs: {self.book_name_to_book_id}\n"
        # result += f"Evidence: {self.book_name_evidence_types}\n"
        # result += f"Counts: {self.reference_count}\n"
        return result

    def add_evidence(self, evidence_type: str, evidence_text: str) -> None:
        # if 'gen' in evidence_text.lower():
        #     sys.stderr.write(f"  add_evidence {evidence_type} {evidence_text}\n")
        if evidence_type.startswith('toc') or evidence_type == 'id':
            self.book_name_evidence_types[evidence_text].append(evidence_type)
            if self.sc.current_book_id:
                if self.book_name_to_book_id.get(evidence_text):
                    pass
                else:
                    self.book_name_to_book_id[evidence_text] = self.sc.current_book_id
                    self.book_name_normalization[evidence_text] = evidence_text
                    self.book_name_normalization[evidence_text.lower()] = evidence_text
        elif evidence_type == 'xt':
            ref_text_s = evidence_text.strip(' .()')
            ref_texts = regex.split(r';\s*', ref_text_s)
            prev_book_name = None
            for ref_text in ref_texts:
                if m := regex.match(fr'\s*(\S.*?\pL\pM*|)\s*(\d+(?:{self.connector_re}\d+)*|)\s*$', ref_text):
                    book_name, cv_span = m.group(1, 2)
                    if not book_name:
                        book_name = prev_book_name
                    if book_name:
                        if 'xt' not in self.book_name_evidence_types[book_name]:
                            self.book_name_evidence_types[book_name].append('xt')
                        self.reference_count[('xt', book_name)] += 1
                        prev_book_name = book_name
                else:
                    self.n_error_messages += 1
                    if self.n_error_messages <= 20:
                        sys.stderr.write(f"Cannot process \\xt: {ref_text.strip()} :: {evidence_text.strip()} "
                                         f"{self.sc.current_filename} {self.sc.current_line_number_start}\n")

    def check_so(self, so: UsfmObject) -> None:
        for element in so.elements:
            if isinstance(element, UsfmElement):
                self.check_se(element, so)

    def check_se(self, se: UsfmElement, so: UsfmObject) -> None:
        sc = so.sc
        ref_words = sc.doc_config.ref_words.get(sc.lang_code, [])
        chapter_keywords = ref_words.get('_CHAPTER_', []) if ref_words else []
        chapter_keywords_lc = [x.lower() for x in chapter_keywords]
        verse_keywords = ref_words.get('_VERSE_', []) if ref_words else []
        verse_keywords_lc = [x.lower() for x in verse_keywords]
        for sub_element in se.sub_elements:
            if isinstance(sub_element, UsfmElement):
                self.check_se(sub_element, so)
            elif isinstance(sub_element, str):
                if se.tag not in ('xt', 'fr', 'r', 'cl', 'id'):
                    left_context, rest = '', sub_element
                    candidate_tuples = []
                    while m := regex.match(fr'(.*?)(\d+(?:{self.connector_re}\d+)*)(.*)$', rest):
                        pre, num, rest = m.group(1, 2, 3)
                        left_context += pre
                        if m2 := regex.search(fr"((?:\b(?:[1-9]|\pL\pM*)(?:\pL\pM*|')*\s+)?\pL\pM*(?:\pL\pM*|')*)\s+$",
                                              left_context):
                            candidate_tuples.append((m2.group(1), num))
                        left_context += num
                    for candidate_tuple in candidate_tuples:
                        num = candidate_tuple[1]
                        cand0 = candidate_tuple[0]
                        cand1 = regex.sub(r'^\S+\s+', '', cand0)
                        candidates = [cand0]
                        if cand1 != cand0:
                            candidates.append(cand1)
                        for sub_cand in candidates:
                            ref = " ".join([sub_cand, num])
                            if sub_cand in self.book_name_evidence_types:
                                brs = BibleRefSpan(so.versification)
                                brs_ref = BibleRefSpan(ref, sc.ref_stats.book_name_to_book_id)
                                loc_contains_ref = brs_ref.contains(brs)
                                if loc_contains_ref:
                                    error_cat = ('Info', 'Found self-reference', f'\\{se.tag}')
                                    mark_up = [(ref, 'color:green;')]
                                else:
                                    error_cat = ('Alerts', 'Consider adding reference tags (e.g. \\xt)', f'\\{se.tag}')
                                    mark_up = [(ref, 'color:red;')]
                                sc.record_error(error_cat, so.versification, so.s.strip(), mark_up=mark_up)
                                # sys.stderr.write(f'  Consider adding \\xt under \\{se.tag} to: '
                                #                  f'{ref} ({so.versification}; '
                                #                  f'{so.current_filename} l.{so.current_line_number - 1})\n')
                            elif sub_cand.lower() in chapter_keywords_lc:
                                error_cat = ('Info', 'Found chapter reference', f'\\{se.tag}')
                                mark_up = [(ref, 'color:red;')]
                                sc.record_error(error_cat, so.versification, so.s.strip(), mark_up=mark_up)
                            elif sub_cand.lower() in verse_keywords_lc:
                                error_cat = ('Info', 'Found verse reference', f'\\{se.tag}')
                                mark_up = [(ref, 'color:red;')]
                                sc.record_error(error_cat, so.versification, so.s.strip(), mark_up=mark_up)


class UsfmCheck:

    def __init__(self, directory: str | Path | None = None, user: str | None = None,
                 doc_config: DocumentConfiguration | None = None,
                 lang_code: str | None = None):
        self.dir = Path(directory) if isinstance(directory, str) else directory
        self.filenames = []
        self.current_book_id = None  # 1CH
        self.current_book_name = None  # 1 Chronicles
        self.current_book = None  # self.current_book_id or self.current_book_name
        self.current_chapter = 0
        self.current_verse = None
        self.current_verse_s = None  # e.g. 50 or "50, 52-54"
        self.current_filename = None
        self.current_line = None
        self.current_line_number_start = None
        self.current_line_number_end = None
        self.chapters_in_book = defaultdict(list)
        self.verses_in_chapter = defaultdict(list)
        self.tag_props = dict()
        self.stats_key_values = defaultdict(set)      # key: tag
        self.stats_counts = defaultdict(int)          # key: (tag, open/close_tag)
        self.error_key_values = defaultdict(set)
        self.error_counts = defaultdict(int)
        self.error_locations = defaultdict(list)
        self.error_strings = defaultdict(list)
        self.error_sub_strings = defaultdict(list)
        self.error_id_to_error_tuple = {}
        self.bible_config: BibleUtilities | None = None
        self.tag_locations = defaultdict(list)
        self.user = user
        self.user_defined_tags = set()
        self.n_operations_in_expand_usfm_verses = 0
        self.n_fewer_lines_in_expand_usfm_verses = 0
        self.n_operations_in_split_usfm_chapters_and_verses = 0
        self.n_additional_lines_in_split_usfm_chapters_and_verses = 0
        self.repair_dir = None
        self.repair_fh = None
        self.repair_set = {'add-plus', 'chapter-and-verse-tag', 'post-chapter-number', 'fq-star', 'fqa-star'}
        self.repair_key_values = defaultdict(set)
        self.repair_counts = defaultdict(int)
        self.repair_locations = defaultdict(list)
        self.repair_id_to_repair_tuple = {}
        self.repair_message_counts = defaultdict(int)
        self.bible_text_extract_dict = {}  # key: (book_id, chapter_number, verse_number) value: BibleTextExtracts
        self.extract_ignore_tag_count = defaultdict(int)
        self.log_message_count = defaultdict(int)
        self.log_count_dict = defaultdict(int)
        self.other_tag_count_dict = defaultdict(int)
        self.explanation_id_to_explanation = {}
        self.error_cat_element_to_explanation_id = {}
        self.doc_config = doc_config
        self.lang_code = lang_code
        self.ref_stats = ReferenceStats(self)
        self.so_list: list[UsfmObject] = []
        self.corpus_model = CorpusModel(sc=self)
        self.ellipsis_counts = defaultdict(int)      # key: (?:...|....|…)
        self.ellipsis_locations = defaultdict(list)  # as above  # value: (verse-id, footnote)
        self.misc_data_dict = None

        script_path = os.path.realpath(__file__)
        script_dir = Path(script_path).parent
        # sys.stderr.write(f"script dir: {script_dir}\n")
        self.read_tag_prop_data(script_dir / "Bible_USFM_tag_data.jsonl")
        self.read_usfm_explanations(script_dir / "Bible_USFM_explanations.txt")

    def core_tag(self, s: str, norm1: bool = True) -> tuple[str, bool, bool, bool, bool, bool, bool]:
        registered_p, missing_space, missing_1_p, missing_backslash, plus_p, close_p \
            = False, False, False, False, False, False
        if s.endswith(' '):
            s = s.rstrip()
        elif s.endswith('\n'):
            s = s.rstrip()
        else:
            missing_space = True
        if s.startswith('\\'):
            s = s[1:]
        else:
            missing_backslash = True
        if s.startswith('+'):
            s = s[1:]
            plus_p = True
        if s.endswith('*'):
            s = s[:-1]
            close_p = True
            missing_space = False
        if self.tag_props.get(('registered-tag', s)):
            registered_p = True
        if (norm1
                and regex.search(r'[a-z]$', s, regex.IGNORECASE)
                and self.tag_props.get(('registered-tag', s + '1'))):
            s = s + '1'
            missing_1_p = True
            registered_p = True
        return s, registered_p, missing_space, missing_1_p, missing_backslash, plus_p, close_p

    def tag_is_registered(self, s: str) -> bool:
        return self.tag_props.get(('registered-tag', s)) or self.tag_props.get(('registered-tag', s + '1'))

    def record_error(self, error_cat: tuple, error_loc: str | None, error_string: str | None,
                     error_id: str | None = None, count_only_full_error_cat: bool = False,
                     mark_up: list[tuple[str, str]] | None = None):  # tuple: (sub-str, style)
        error_top_cat = error_cat[0] if error_cat else None
        # Downgrade errors to warnings for issues in auxiliary material
        if (error_top_cat
                and ('error' in error_top_cat.lower())
                and (self.current_book_id in self.bible_config.other_texts)):
            error_cat_list = list(error_cat)
            error_cat_list = ['Warnings', 'Errors in auxiliary material'] + error_cat_list[1:]
            error_cat = tuple(error_cat_list)
        if error_cat and (error_cat[0] != 'Silent') and (not count_only_full_error_cat):
            self.error_counts[()] += 1
        if error_id:
            self.error_id_to_error_tuple[error_id] = error_cat
        # sys.stderr.write(f"*** Record error: {error_cat} {error_loc} {error_string}\n")
        for error_sub_cat_index in range(len(error_cat)):
            error_sub_cat = error_cat[error_sub_cat_index]
            error_pre_cat = error_cat[0:error_sub_cat_index]
            error_acc_cat = error_cat[0:error_sub_cat_index + 1]
            self.error_key_values[error_pre_cat].add(error_sub_cat)
            if (error_acc_cat == error_cat) or (not count_only_full_error_cat):
                self.error_counts[error_acc_cat] += 1
            if error_loc and (error_sub_cat_index == len(error_cat) - 1):  # full error_cat
                self.error_locations[error_cat].append(error_loc)
                if error_string:
                    self.error_strings[(error_cat, error_loc)].append(error_string)
                    if mark_up:
                        key_tuple = (error_cat, error_loc, error_string)
                        self.error_sub_strings[key_tuple] += mark_up
                        # sys.stderr.write(f" ! error_sub_strings({key_tuple}) {self.error_sub_strings[key_tuple]}\n")

    def location_sort(self, s: str | LineStruct) -> tuple[int, int, int, str]:
        # target filename and line number, e.g. 44JHN_abc.SFM l.151
        if isinstance(s, LineStruct):
            if m := regex.match(r"(\d\d)\S+\.U?SFM\s*$", s.filename):
                return int(m.group(1)), s.from_line_number, s.from_col, ''
            elif m := regex.match(r"([A-F])(\d)\S+\.U?SFM\s*$", s.filename):
                return 100 + 10*(ord(m.group(1))-64) + int(m.group(2)), s.from_line_number, s.from_col, ''
            else:
                return 999, s.from_line_number, s.from_col, ''
        elif m := regex.match(r"(\d\d)\S+\.U?SFM\s+(?:line|l\.)\s*(\d+)", s, regex.IGNORECASE):
            return int(m.group(1)), int(m.group(2)), 0, ''
        elif m := regex.match(r"([A-F])(\d)\S+\.U?SFM\s+(?:line|l\.)\s*(\d+)", s, regex.IGNORECASE):
            return 100 + 10*(ord(m.group(1))-64) + int(m.group(2)), int(m.group(3)), 0, ''
        # alternatively, target location in this format: JHN 3:16
        elif m := regex.search(r"\b([A-Z1-3][A-Z][A-Z])\s+(\d+)[:.](\d+)", s):
            return self.bible_config.book_to_book_number.get(m.group(1), 99), int(m.group(2)), int(m.group(3)), ''
        elif m := regex.search(r"\b([A-Z1-3][A-Z][A-Z])\s+(\d+)", s):
            return self.bible_config.book_to_book_number.get(m.group(1), 99), int(m.group(2)), 0, ''
        elif m := regex.search(r"\b([A-Z1-3][A-Z][A-Z])", s):
            return self.bible_config.book_to_book_number.get(m.group(1), 99), 0, 0, ''
        else:
            return 99999, 99999, 99999, s  # todo check sort '[1430:147]'

    def error_sub_cat_sort(self, error_cat: tuple) -> tuple[int, str]:
        if error_cat == ('Severe errors',):
            return 0, ''
        elif error_cat == ('Errors',):
            return 10, ''
        elif error_cat == ('Auto-repairable errors',):
            return 20, ''
        elif error_cat == ('Moderate errors',):
            return 30, ''
        elif error_cat == ('Warnings',):
            return 50, ''
        elif error_cat == ('Alerts',):
            return 60, ''
        elif error_cat == ('Info',):
            return 70, ''
        elif error_cat == ('Silent',):
            return 99, ''
        # elif error_cat:
        #     sub_error_cat = error_cat[-1]
        #     return something
        else:
            return -self.error_counts[error_cat], error_cat[-1]

    @staticmethod
    def bundle_duplicates(elements: list[str], explicit_counts_p: bool = False) -> list[str]:
        # ['a', 'b', 'b', 'b', 'c'] -> ['a', 'b (3)', 'c']
        # assumption: list is already presorted
        result = []
        current_element, n_occurrences = None, 0
        for new_element in elements:
            if new_element == current_element:
                n_occurrences += 1
            else:
                if n_occurrences:
                    if explicit_counts_p:
                        result.append((current_element, n_occurrences))
                    elif n_occurrences >= 2:
                        result.append(f"{current_element} ({n_occurrences})")
                    else:
                        result.append(current_element)
                current_element = new_element
                n_occurrences = 1
        if explicit_counts_p and n_occurrences:
            result.append((current_element, n_occurrences))
        elif n_occurrences >= 2:
            result.append(f"{current_element} ({n_occurrences})")
        elif n_occurrences:
            result.append(current_element)
        return result

    def error_propagation(self) -> None:
        for i_key in self.error_id_to_error_tuple.keys():
            if m := regex.match(r'I-no-\\([a-z]+[1-3]*)\*\s*$', i_key):
                tag = m.group(1)
                i_error_cat = self.error_id_to_error_tuple.get(i_key)
                # i_count = self.error_counts[i_error_cat]
                e_key = f"E-\\{tag}*"
                e_error_cat = self.error_id_to_error_tuple.get(e_key)
                e_count = self.error_counts[e_error_cat]
                e_count2 = self.stats_counts[('tag', tag)]
                # sys.stderr.write(f"error_propagation3 {tag} {i_key} {i_error_cat} {i_count} {e_key} "
                #                  f"{e_error_cat} {e_count} {e_count2}\n")
                if e_count and e_count2 and ((e_count / e_count2) >= 0.3):
                    new_error_cat = ('Info',) + i_error_cat[1:]
                    for error_location in self.error_locations[i_error_cat]:
                        for error_string in self.error_strings[(i_error_cat, error_location)]:
                            self.record_error(new_error_cat, error_location, error_string)

    @staticmethod
    def some_error_cat_element_includes(error_cat: tuple, sub_string: str) -> bool:
        for error_cat_elem in error_cat:
            if sub_string in error_cat_elem:
                return True
        return False

    @staticmethod
    def open_close_tags_from_core_tag(core_tag: str, slash: str = '\\') -> tuple[list[str], list[str]]:
        if core_tag:
            open_tags = [f"{slash}{core_tag}", f"{slash}+{core_tag}"]
            close_tags = [f"{slash}{core_tag}*", f"{slash}+{core_tag}*"]
            core_tag_w1 = core_tag.removesuffix('1')
            if core_tag_w1 != core_tag:
                open_tags.extend([f"{slash}{core_tag_w1}", f"{slash}+{core_tag_w1}"])
                close_tags.extend([f"{slash}{core_tag_w1}*", f"{slash}+{core_tag_w1}*"])
        else:
            open_tags, close_tags = [], []
        return open_tags, close_tags

    def color_error_cat_element(self, s: str, error_pre_cat: tuple[str]) -> str:
        if self.some_error_cat_element_includes(error_pre_cat, "Inconsistent tag variants") \
                and ("use both" in s):
            s = regex.sub(fr'(\\\+?[a-zA-Z]+[1-9]?\*?)', r'<span style="color:blue;">\1</span>', s)
        if "oldest Bible manuscripts" in s:
            s = s.replace('  ', '<br>\n')
        if "Inconsistent footnote quote ellipses" in s:
            s = regex.sub(rf'(?<=Dominant footnote quote ellipsis:)\s*([.…]+)',
                          r' <span style="color:green;"><b>\1</b></span>', s)
        return s

    @staticmethod
    def trailing_punct(quote: str, verse: str) -> Tuple[str, str] | Tuple[None, None]:
        norm_verse = regex.sub(r'\s*\n\s*', ' ', verse).lower()
        for punct_suffix in ('.', ',', ';', ':', '”', '-', '–', ' –', '।'):
            if quote.endswith(punct_suffix):
                quote_without_punct_suffix = quote.removesuffix(punct_suffix)
                if quote_without_punct_suffix.lower() in norm_verse:
                    return quote_without_punct_suffix, punct_suffix
        return None, None

    def color_verse(self, s: str, error_cat: tuple, error_loc: str) -> str:
        orig_s = s
        s = guard_html(s)
        sf = SmartFindall(r'\\\+?[a-z]+[0-9]*\*?', s, flags=regex.IGNORECASE)
        m = regex.search(r'\\\+?([a-z]+[0-9]*)\*?', error_cat[-1], regex.IGNORECASE)
        tag = m.group(1) if m else None
        core_tag = self.core_tag(tag)[0] if tag else None
        open_tags, close_tags = self.open_close_tags_from_core_tag(core_tag)
        # if "\\q." in s: sys.stderr.write(f"**CV {tag} {s} OT:{open_tags}\n")
        if "Missing space between \\v and verse number" in error_cat:
            s = regex.sub(r'(\\v\d+)', r'<span style="color:red;">\1</span>', s)
        elif "Missing space after verse number or verse number range" in error_cat:
            s = regex.sub(r'(\\v\s*\d+(?:-\d+)?)', r'<span style="color:red;">\1</span>', s)
        elif "Missing space after open tag" in error_cat:
            s = sf.markup_tag_style(open_tags, 'color:red;')
        elif "Spurious material after chapter number" in error_cat:
            s = regex.sub(r'(\\c\s*\d+)(\s*)(.*)',
                          r'<span style="color:008800;">\1</span>\2<span style="color:red;">\3</span>', s, regex.DOTALL)
        elif self.some_error_cat_element_includes(error_cat, "Unrecognized tags") and tag:
            s = sf.markup_tag_style(open_tags + close_tags, 'color:red;')
        elif ("Unexpected multiple instances of the same tag in same line" in error_cat) and tag:
            s = sf.markup_tag_style(open_tags, 'color:red;')
        elif ("Missing closing tag" in error_cat) and tag:
            sf.markup_tag2_style(open_tags, 'color:red;', close_tags, 'color:green;')
            s = sf.markup_repeat_tag_style(open_tags, 'color:red;font-weight:bold;')
        elif ("Unexpected close tag in context" in error_cat) and tag:
            sf.markup_tag2_style(open_tags, 'color:green;', close_tags, 'color:red;')
            s = sf.markup_repeat_tag_style(open_tags, 'color:red;font-weight:bold;')
            if len(error_cat) >= 2:
                m_parent = regex.search(r'\\\+?([a-z]+[0-9]*)\*?', error_cat[-2], regex.IGNORECASE)
                parent_tag = m_parent.group(1) if m_parent else None
                if parent_tag:
                    core_parent_tag = self.core_tag(parent_tag)[0] if parent_tag else None
                    open_tags, close_tags = self.open_close_tags_from_core_tag(core_parent_tag)
                    s = sf.markup_tag_style(open_tags + close_tags, 'color:blue;')
        elif ("Missing open tag" in error_cat) and tag:
            sf.markup_tag2_style(open_tags, 'color:green;', close_tags, 'color:red;')
            s = sf.markup_repeat_tag_style(close_tags, 'color:red;font-weight:bold;')
        elif ("Expected the following tags to be at the beginning of the line" in error_cat) and tag:
            s = sf.markup_tag2_style(open_tags, 'color:red;', close_tags, 'color:blue;')
        elif (("Suspicious pseudo-tag with wrong kind of slash" in error_cat)
                and (m := regex.search(r'([\/\|])(\S+)', error_cat[-1]))):
            bad_slash, core_tag = m.group(1, 2)
            open_tags, close_tags = self.open_close_tags_from_core_tag(core_tag)
            s = sf.markup_tag_style(open_tags + close_tags, 'color:green;')
            s = regex.sub(fr'({guard_regex(bad_slash)}\+?{core_tag}\*?(?![a-z0-9*]))',
                          r'<span style="color:red;">\1</span>', s)
        elif "Tags with spurious spaces after slash" in error_cat:
            s = regex.sub(fr'({guard_regex(error_cat[-1])})', r'<span style="color:red;">\1</span>', str(sf))
        elif self.some_error_cat_element_includes(error_cat, "Slash followed by control character"):
            s = regex.sub(fr'(\\\pC)', r'<span style="color:red;">\1</span>', str(sf))
        elif self.some_error_cat_element_includes(error_cat, "Slash followed by an invalid string"):
            s = regex.sub(fr'(\\(?![a-zA-Z])\S+)', r'<span style="color:red;">\1</span>', str(sf))
        elif "Missing verse number" in error_cat:
            s = sf.markup_tag_style(['\\v'], 'color:red;')
        elif "Missing chapter number" in error_cat:
            s = sf.markup_tag_style(['\\c'], 'color:red;')
        elif self.some_error_cat_element_includes(error_cat, "Slash followed by space"):
            s = regex.sub(fr'(\\\s)', r'<span style="color:red;font-weight:bold;">\1</span>', str(sf))
        elif self.some_error_cat_element_includes(error_cat, "Unexpected close tag for") and tag:
            s = sf.markup_tag2_style(open_tags, 'color:green;', close_tags, 'color:red;')
        elif self.some_error_cat_element_includes(error_cat, "Deprecated close tag") and tag:
            s = sf.markup_tag2_style(open_tags, 'color:green;', close_tags, 'color:red;')
        elif self.some_error_cat_element_includes(error_cat, "Implied close-tag") and tag:
            sf.markup_tag2_style(open_tags, 'color:red;', close_tags, 'color:green;')
            s = sf.markup_repeat_tag_style(open_tags, 'color:red;font-weight:bold;')
        elif "New verse is preceded by open delimiter on same line" in error_cat:
            delimiter = error_cat[-1]
            s = regex.sub(rf'({guard_regex(delimiter)}(?:\pC|\pZ)*\\v)', r'<span style="color:red;">\1</span>', s)
        elif "New chapter is preceded by open delimiter on same line" in error_cat:
            delimiter = error_cat[-1]
            s = regex.sub(rf'({guard_regex(delimiter)}(?:\pC|\pZ)*\\c)', r'<span style="color:red;">\1</span>', s)
        elif "Line ends in open delimiter" in error_cat:
            delimiter = error_cat[-1]
            s = regex.sub(rf'({guard_regex(delimiter)}(?:\pC|\pZ)*)$', r'<span style="color:red;">\1</span>', s)
        elif m := regex.match(r'Did not expect (\\[a-z]+[1-9]*) under (\\[a-z]+[1-9]*)', error_cat[-1]):
            s = regex.sub(rf'({guard_regex(m.group(1))}(?![a-z0-9*]))', r'<span style="color:red;">\1</span>', s)
            s = regex.sub(rf'({guard_regex(m.group(2))}(?![a-z0-9*]))', r'<span style="color:blue;">\1</span>', s)
        elif self.some_error_cat_element_includes(error_cat, "self-closing tag"):
            delimiter = error_cat[-1]
            s = regex.sub(rf'({guard_regex(delimiter)}(?![a-z0-9*]))', r'<span style="color:blue;">\1</span>', s)
            s = regex.sub(r'(\\\*)', r'<span style="color:red;">\1</span>', s)
        elif "Verse number includes letter" in error_cat:
            verse_number = error_cat[-1]
            s = regex.sub(rf'\b({verse_number})\b', r'<span style="color:red;">\1</span>', s)
        elif "Unexpected occurrence of both chapter and verse tags on the same line" in error_cat:
            s = regex.sub(rf'(\\[cv])\b', r'<span style="color:red;">\1</span>', s)
        elif self.some_error_cat_element_includes(error_cat, "Inconsistent footnote quote ellipses"):
            ellipsis_s = error_cat[-1]
            re_ellipsis = guard_regex(ellipsis_s)
            s = regex.sub(rf'(?<!\.|…)({re_ellipsis})(?!\.|…)', r'<span style="color:red;"><b>\1</b></span>', s)
        elif "Consecutive duplicate words" in error_cat:
            duplicate_words = guard_html(error_cat[-1])
            duplicate_word = regex.sub(r'(?:\pZ|\pC).*', '', duplicate_words)
            s = regex.sub(rf'\b({duplicate_word}(?:(?:\pZ|\pC)+{duplicate_word})+)\b',
                          r'<span style="color:red;">\1</span>',
                          s, flags=regex.IGNORECASE)
        elif "Verse tag with missing backslash?" in error_cat:
            sys.stderr.write(f"  V 1 {error_cat} {s}\n")
            s = regex.sub(rf'\b(?<!\\)(v\s+\d+)', r'<span style="color:red;">\1</span>', s, flags=regex.IGNORECASE)
            s = regex.sub(rf'(\\v\s+\d+)', r'<span style="color:green;">\1</span>', s, flags=regex.IGNORECASE)
        elif (self.some_error_cat_element_includes(error_cat, "Consider adding reference tags")
              or self.some_error_cat_element_includes(error_cat, "Found self-reference")
              or self.some_error_cat_element_includes(error_cat, "Found chapter reference")
              or self.some_error_cat_element_includes(error_cat, "Found verse reference")):
            s = sf.markup_tag2_style(open_tags, 'color:blue;', close_tags, 'color:blue;')
            key_tuple1 = (error_cat, error_loc, orig_s)
            key_tuples = [key_tuple1]
            if self.some_error_cat_element_includes(error_cat, "Consider adding reference tags"):
                error_cat2 = tuple(["Info", "Found self-reference"] + list(error_cat)[2:])
                key_tuple2 = (error_cat2, error_loc, orig_s)
                key_tuples.append(key_tuple2)
            elif self.some_error_cat_element_includes(error_cat, "Found self-reference"):
                error_cat2 = tuple(["Alerts", "Consider adding reference tags (e.g. \\xt)"] + list(error_cat)[2:])
                key_tuple2 = (error_cat2, error_loc, orig_s)
                key_tuples.append(key_tuple2)
            for i, key_tuple in enumerate(key_tuples):
                if mark_up := self.error_sub_strings[key_tuple]:
                    for mark_up_element in mark_up:
                        ref, style = mark_up_element
                        ref_g = guard_html(ref)
                        # sys.stderr.write(f" ? error_sub_strings({key_tuple}) {s} => {ref_g} :: {style}\n")
                        s = regex.sub(rf'\b({ref_g})\b', fr'<span style="{style}">\1</span>', s)
                elif i == 0:
                    sys.stderr.write(f" ? error_sub_strings({key_tuple}) {s} => ???\n")
        elif "Footnote quotation does not appear in verse" in error_cat:
            last_error_component = error_cat[-1]
            f_quotation = last_error_component.removeprefix('Footnote quotation: ')
            if m := regex.match(r'(Verse:)(.*) • (Footnote:)(.*)$', s, regex.DOTALL):
                verse_kw, verse, footnote_kw, footnote = m.group(1, 2, 3, 4)
                sd = StringDiff(verse, footnote)
                verse2 = verse
                footnote2 = footnote.replace(f_quotation,
                                             f"<span style='color:red;font-style:italic;'>{f_quotation}</span>")
                if max_overlap := sd.max_overlap_words():
                    footnote2 = regex.sub(max_overlap, f"<span style='color:blue;'>{max_overlap}</span>", footnote2)
                    verse2 = regex.sub(max_overlap, f"<span style='color:blue;'>{max_overlap}</span>", verse2)
                if end_overlap := sd.max_overlap_words_at_end(ref_side=2, at_start=False):
                    footnote2 = regex.sub(end_overlap, f"<span style='color:purple;'>{end_overlap}</span>",
                                          footnote2)
                    verse2 = regex.sub(end_overlap, f"<span style='color:purple;'>{end_overlap}</span>", verse2)
                if start_overlap := sd.max_overlap_words_at_end(ref_side=2, at_start=True):
                    footnote2 = regex.sub(start_overlap, f"<span style='color:green;'>{start_overlap}</span>",
                                          footnote2)
                    verse2 = regex.sub(start_overlap, f"<span style='color:green;'>{start_overlap}</span>", verse2)
                suggestion = ""
                f_quotation_without_punct_suffix, punct_suffix = self.trailing_punct(f_quotation, verse)
                if f_quotation_without_punct_suffix:
                    suggestion = (f" <li> Did you mean to limit the footnote quotation "
                                  f"to <span style='color:red;font-style:italic;'>"
                                  f"{f_quotation_without_punct_suffix}</span>"
                                  f", i.e. without the trailing <span style='color:red;'>"
                                  f"{print_str_unicode_names(punct_suffix)}</span> "
                                  f"inside the footnote quotation?")
                # for punct_suffix in ('.', ',', ';', ':'):
                #     if f_quotation.endswith(punct_suffix):
                #         f_quotation_without_punct_suffix = f_quotation.removesuffix(punct_suffix)
                #         if f_quotation_without_punct_suffix.lower() in verse.lower():
                #             suggestion = (f" <li> Did you mean to limit the footnote quotation "
                #                           f"to <span style='color:red;font-style:italic;'>"
                #                           f"{f_quotation_without_punct_suffix}</span>"
                #                           f", i.e. without the trailing <span style='color:red;'>"
                #                           f"{print_str_unicode_names(punct_suffix)}</span> "
                #                           f"inside the footnote quotation?")
                #             break
                # ओड़ै मै दाऊद की पीढियाँ नै महान राजा बणा दियुँगा अर याड़ै मै चुणे होया के राज्य की रुखाळी करुँगा;
                # ओड़ै मै दाऊद की पीढियाँ नै महान राजा बणा दियुँगा अर याड़ै मै चुणे होया के राज्य की रुखाळी करुँगा,
                # \v 17 ओड़ै मै दाऊद की पीढियाँ नै महान राजा बणा दियुँगा
                # \q अर याड़ै मै चुणे होया के राज्य की रुखाळी करुँगा;
                # \f + \fr 132:17 \fq ओड़ै मै दाऊद की पीढियाँ नै महान राजा बणा दियुँगा अर याड़ै मै चुणे होया के राज्य की रुखाळी करुँगा, \ft ओड़ै मै दाऊद का एक सींग उगाऊँगा, मन्<200d>नै अपणे अभिषिक्त खात्तर एक दीवा बणा राख्या सै। \f*
                for punct_prefix in ('.', ',', ';', ':'):
                    if f_quotation.startswith(punct_prefix):
                        f_quotation_without_punct_prefix = f_quotation.removeprefix(punct_prefix)
                        if f_quotation_without_punct_prefix.lower() in verse.lower():
                            suggestion += (f" <li> Did you mean to limit the footnote quotation "
                                           f"to <span style='color:red;font-style:italic;'>"
                                           f"{f_quotation_without_punct_prefix}</span>"
                                           f", i.e. without the leading <span style='color:red;'>"
                                           f"{print_str_unicode_names(punct_prefix)}</span> "
                                           f"inside the footnote quotation?")
                            break
                s = f"<i>{verse_kw}</i>{verse2} <ul> <li> <i>{footnote_kw}</i>{footnote2}{suggestion}</ul>"
        if m := regex.match(r'(.*?)\s+\[((?:Note:|Did you mean).+)\]\s*$', s, regex.DOTALL):
            s = f"{m.group(1)}<br>\n<i>{m.group(2)}</i>"
        s = regex.sub(r'  ', '&nbsp; &nbsp;', s)
        return s

    def error_report(self, error_pre_cat: tuple = (), html_p: bool = False) -> str:
        # f_html_out is None: plain text format
        global n_toggle_indexes
        if error_pre_cat:
            result = ''
        else:
            n = self.error_counts[()]
            s = '' if n == 1 else 's'
            title = f'Report of {n} error{s}/warning{s}/alert{s}/info{s}'
            result = f"<h3>{title}</h3>\n" if html_p else f"{title}:\n"
        indent0 = (' ' * 4 * (len(error_pre_cat) + 0))
        indent1 = (' ' * 4 * (len(error_pre_cat) + 1))
        indent2 = (' ' * 4 * (len(error_pre_cat) + 2))
        if html_p:
            result += indent0 + "<ul>\n"
            li = "<li> "
        else:
            li = ""
        for error_sub_cat in sorted(self.error_key_values[error_pre_cat],
                                    key=lambda x: self.error_sub_cat_sort(error_pre_cat + (x,))):
            error_cat = error_pre_cat + (error_sub_cat,)
            if error_cat == ('Silent',):
                continue
            out_error_sub_cat = self.color_error_cat_element(error_sub_cat, error_pre_cat) \
                if html_p else error_sub_cat
            result += f"{indent1}{li}{out_error_sub_cat} ({self.error_counts[error_pre_cat + (error_sub_cat,)]})"
            if html_p:
                explanation_id = self.error_cat_element_to_explanation_id.get(error_sub_cat)
                explanation = self.explanation_id_to_explanation.get(explanation_id) if explanation_id else None
                # sys.stderr.write(f"  EXPL insert {error_cat} {explanation_id} {len(explanation)}\n")
                if explanation_id and explanation:
                    n_toggle_indexes += 1
                    toggle_index = f"t{n_toggle_indexes}"
                    style_clause = 'style="color:navy; text-decoration:underline;font-weight:bold;"'
                    onclick_clause = f"""onclick="toggle_info('{toggle_index}');" """
                    toggle_text = f"""&nbsp; &nbsp; <span {style_clause} {onclick_clause}>Explain</span>"""
                    result += toggle_text
                    explanation_box = (f"<table border='1' cellpadding='10' cellspacing='1' bgcolor='#FCFCE3'>"
                                       f"<tr><td>{explanation}</td></tr></table>")
                    result += f"<br>\n<div id='{toggle_index}' style='display:none;'>{explanation_box}</div>"
            error_locations = sorted(self.error_locations[error_cat], key=self.location_sort)
            if html_p:
                result += indent2 + "<ul>\n"
            if any([self.error_strings[(error_cat, error_loc)] for error_loc in error_locations]):
                result += '\n'
                elements = []
                prev_loc = None
                for error_loc in error_locations:
                    if error_loc != prev_loc:  # skip duplicate locations
                        prev_loc = error_loc
                        if strings := self.error_strings[(error_cat, error_loc)]:
                            for string in strings:
                                string = string.rstrip()
                                colored_string = self.color_verse(string, error_cat, error_loc) if html_p else string
                                elements.append(f"{indent2}{li}{error_loc}: {colored_string}")
                        else:
                            elements.append(f"{indent2}{error_loc}")
                bundled_elements = self.bundle_duplicates(elements)
                max1, max2 = 50, 60
                # max1, max2 = 3, 4
                if html_p and (len(bundled_elements) > max2):
                    n_toggle_indexes += 1
                    toggle_index = f"t{n_toggle_indexes}"
                    n_more = len(bundled_elements) - max1
                    style_clause = 'style="color:navy; text-decoration:underline;font-weight:bold;"'
                    onclick_clause = f"""onclick="toggle_info('{toggle_index}');" """
                    toggle_text = f"""<span {style_clause} {onclick_clause}>Show {n_more} more entries</span>"""
                    result += '\n'.join(bundled_elements[:max1]) + '\n'
                    result += f'<br> {toggle_text}</ul>\n'
                    result += f"<div id='{toggle_index}' style='display:none;'><ul>\n"
                    result += '\n'.join(bundled_elements[max1:]) + '\n'
                    result += f'</ul></div><ul>\n'
                else:
                    result += '\n'.join(bundled_elements) + '\n'
            else:
                max_n_bundles_to_show = 300
                bundles = self.bundle_duplicates(error_locations)
                if (len(bundles) > max_n_bundles_to_show) and ("Warnings" in error_cat):
                    bundles = bundles[:max_n_bundles_to_show] + ['...']
                result += ' ' + ', '.join(bundles) + '\n'
            if html_p:
                result += indent2 + "</ul>\n"
            result += self.error_report(error_cat, html_p)
        if html_p:
            result += indent0 + "</ul>\n"
        return result

    def record_tag(self, tag: str, open_tag: str | None = None, close_tag: str | None = None, new_tag: bool = True):
        self.stats_key_values['tag'].add(tag)
        if new_tag:
            self.stats_counts[('tag', tag)] += 1
        if open_tag:
            self.stats_key_values[('tag', tag)].add(open_tag)
            self.stats_counts[('tag', tag, open_tag)] += 1
        if close_tag:
            self.stats_key_values[('tag', tag)].add(close_tag)
            self.stats_counts[('tag', tag, close_tag)] += 1

    def markup_tags_with_exp_title(self, tag_clause: str, relation_type: str, core_tag2: str | None = None) -> str:
        # relation_type should be "child" (for subs) or "parent" (for supers)
        result = tag_clause
        tag, count_s = tag_clause.split()
        if core_tag := (self.core_tag(tag)[0] if tag_clause else None):
            title_key = 'pbtitle' if relation_type == 'child' else 'patitle'
            exp = self.tag_props.get(('exp-long', core_tag)) or self.tag_props.get(('exp', core_tag))
            if not exp:
                if core_tag in self.user_defined_tags:
                    exp = "\U0001F477 user-defined tag"
                else:
                    exp = "\U0001F914 unrecognized tag"
            count = int(count_s)
            plural_s = '' if count == 1 else 's'
            if core_tag2:
                if relation_type == 'child':
                    count_clause = f"({count} instance{plural_s} of \\{core_tag} under \\{core_tag2})"
                else:
                    count_clause = f"({count} instance{plural_s} of \\{core_tag2} under \\{core_tag})"
            else:
                count_clause = f"({count} instance{plural_s} of \\{core_tag})"
            count_clause = count_clause.replace(' ', '&nbsp;')
            result = f'<span {title_key}="\\{core_tag} &nbsp; {exp} {count_clause}">{tag}&nbsp;{count_s}</span>'
        return result

    @staticmethod
    def join2(elements: list[str], max_col_len: int, nobr: bool = True, sep1: str = ',', sep2: str = ' ') -> str:
        result = ''
        line_len = 0
        n_elements = len(elements)
        nobr1 = "<nobr>" if nobr else ""
        nobr2 = "</nobr>" if nobr else ""
        for i, element in enumerate(elements):
            sep1b = '' if i == n_elements - 1 else sep1
            sep2b = '' if i == 0 else sep2
            sep2c = sep2b.replace(' ', '&nbsp;') if nobr else sep2b
            element_len = len(regex.sub(r'(?<!\\)<.*?>', '', element))
            if line_len and (line_len + element_len + len(sep1b) + len(sep2b) > max_col_len):
                result += "<br> " + nobr1 + element + sep1b + nobr2
                line_len = element_len + len(sep1b)
            else:
                result += sep2c + nobr1 + element + sep1b + nobr2
                line_len += len(sep2b) + element_len + len(sep1b)
        return result

    def tag_stats(self, html_p: bool = False) -> str:
        # f_html_out is None: plain text format
        title = 'Tag statistics'
        if html_p:
            result = f"<h3>{title}</h3>\n"
            result += f"<table cellpadding='3' cellspacing='0'>\n"
            result += (f"  <tr><td align='left' valign='top'><b>Tag</b></td>"
                       f"<td valign='top' align='right'><b>Count</b></td>"
                       f"<td></td>"
                       f"<td align='left' valign='top'><b>Usage</b></td>"
                       f"<td align='left'><b>Surface tags</b><br><span style='font-size:80%'>(with counts)</span></td>"
                       f"<td></td>"
                       f"<td align='left' bgcolor='#FCFCE3'><b>Child tags</b><br><span style='font-size:80%'>"
                       f"(with counts)</span></td>"
                       f"<td></td>"
                       f"<td align='left'><b>Parent tags</b><br><span style='font-size:80%'>(with counts)</span></td>"
                       f"</tr>\n")
        else:
            result = f"{title}  (post-tag integers are counts)\n"
        for tag in sorted(self.stats_key_values['tag'], key=lambda x: (-self.stats_counts[('tag', x)], x)):
            if html_p:
                result += "  <tr>"
            tag_count = self.stats_counts[('tag', tag)]
            if html_p:
                # result += f"<td valign='top'>\\{tag}</td><td valign='top' align='right'>{tag_count}</td>"
                result += (f"<td colspan='2' valign='top' nowrap>"
                           f"<div style='float:left;'>\\{tag}</div>"
                           f"<div style='float:right;'>&nbsp;{tag_count}</div>"
                           f"</td>")
            else:
                result += f"    \\{tag}{' ' * max(1, 9 - len(tag) - len(str(tag_count)))}{tag_count}"
            notes = []
            html_notes = []
            if self.tag_props.get(('deprecated', tag)):
                note = "deprecated tag"
                notes.append(note)
                html_notes.append(f"<span style='color:blue;'><nobr>{note}</nobr></span>")
            if self.tag_props.get(('undocumented', tag)):
                note = "undocumented tag"
                notes.append(note)
                html_notes.append(f"<span style='color:red;'><nobr>{note}</nobr></span>")
            exp = self.tag_props.get(('exp', tag))
            exp_max_width = 44 if html_p else 30
            full_exp = exp
            # if too long, use short version
            if exp and (len(exp) > exp_max_width) and (exp_short := self.tag_props.get(('exp-short', tag))):
                exp = exp_short
            if exp_long := self.tag_props.get(('exp-long', tag)):
                full_exp = exp_long
                if len(exp_long) <= exp_max_width:
                    exp = exp_long
            if exp:
                c1s, c1e = '', ''
            elif self.tag_props.get(('registered-tag', tag)):
                exp = "No description"
                c1s, c1e = "<span style='color:blue;'>", "</span>"
            elif tag in self.user_defined_tags:
                exp = "User-defined tag"
                c1s, c1e = "<span style='color:blue;'>", "</span>"
            else:
                exp = "Unrecognized tag"
                c1s, c1e = "<span style='color:red;'>", "</span>"
            if html_p:
                result += "<td>&nbsp;&nbsp;</td>"
                sep = '<br>' if len(exp) > 24 else " "
                notes_clause = f"{sep}({', '.join(html_notes)})" if html_notes else ""
                if (full_exp is None) or (full_exp == exp):
                    result += f"<td valign='top'>{c1s}{exp}{c1e}{notes_clause}</td>"
                else:
                    result += (f"<td valign='top'><span patitle='{full_exp}' "
                               f"style='border-bottom:1px dotted;'>{c1s}{exp}{c1e}</span>{notes_clause}</td>")
            else:
                result += f"  {exp:{exp_max_width}s}"
            tags2 = []
            tags2_width = 30
            for tag2 in sorted(self.stats_key_values[('tag', tag)],
                               key=lambda x: (1 if x.endswith('*') else 0, -self.stats_counts[('tag', tag, x)])):
                tag2_count = self.stats_counts[('tag', tag, tag2)]
                c1s, c1e, c2s, c2e = '', '', '', ''  # c1s = color 1 start
                if html_p:
                    tag2b = tag2[:-1] if tag2.endswith('*') else tag2 + '*'  # open to close and vice versa
                    tag2b_count = self.stats_counts[('tag', tag, tag2b)]
                    if (tag2b_count or tag2.endswith('*')) and (tag2_count != tag2b_count):
                        c2s, c2e = "<span style='color:red;'>", "</span>"
                    tag2c = tag2[:-1] if tag2.endswith('1') else tag2 + '1'
                    tag2c_count = self.stats_counts[('tag', tag, tag2c)]
                    if not self.tag_is_registered(tag):
                        if tag in self.user_defined_tags:
                            c1s, c1e = "<span style='color:blue;'>", "</span>"
                        else:
                            c1s, c1e = "<span style='color:red;'>", "</span>"
                    elif tag2c_count > tag2_count:
                        c1s, c1e = "<span style='color:blue;'>", "</span>"
                tags2.append(f"{c1s}{tag2}{c1e} {c2s}{tag2_count}{c2e}")
            tags2_s = ('  Surfs: ' + ', '.join(tags2)) if tags2 else ''
            if html_p:
                result += f"<td valign='top'>{self.join2(tags2, 30)}</td>"
            else:
                result += f"{tags2_s:{tags2_width}s}"
            tags2_overage = max(0, len(tags2_s) - tags2_width)
            tags3 = []
            tags3_width = max(0, 35 - tags2_overage)
            for tag3 in sorted(self.stats_key_values[('tag-children', tag)],
                               key=lambda x: (-self.stats_counts[('tag-children', tag, x)], x)):
                tag3_count = self.stats_counts[('tag-children', tag, tag3)]
                tags3.append(f"\\{tag3} {tag3_count}")
            if html_p:
                result += "<td valign='top'>&nbsp;&nbsp;</td>"
                tags3b = list(map(lambda x: self.markup_tags_with_exp_title(x, 'child', tag), tags3))
                result += f"<td valign='top' bgcolor='#FCFCE3'>{self.join2(tags3b, 60)}</td>"
                tags3_s = ''
            else:
                tags3_s = ('  Children: ' + ', '.join(tags3)) if tags3 else ''
                result += f"{tags3_s:{tags3_width}s}"
            tags3_overage = max(0, len(tags3_s) - tags3_width)
            tags4 = []
            tags4_width = max(0, 35 - tags3_overage)
            for tag4 in sorted(self.stats_key_values[('tag-parents', tag)],
                               key=lambda x: (-self.stats_counts[('tag-parents', tag, x)], x)):
                tag4_count = self.stats_counts[('tag-parents', tag, tag4)]
                tags4.append(f"\\{tag4} {tag4_count}")
            if html_p:
                result += "<td valign='top'>&nbsp;&nbsp;</td>"
                tags4b = list(map(lambda x: self.markup_tags_with_exp_title(x, 'parent', tag), tags4))
                result += f"<td valign='top'>{self.join2(tags4b, 60)}</td>"
                # tags4_s = ''
            else:
                tags4_s = ('  Parents: ' + ', '.join(tags4)) if tags4 else ''
                result += f"{tags4_s:{tags4_width}s}"
            if notes and not html_p:
                result += "  " + ", ".join(notes)
            # result += ' END'  # for format testing only
            result += "\n"
            if html_p:
                result += "</tr>\n"
        if html_p:
            result += f"</table>\n"
        return result

    def final_check(self):
        for so in self.so_list:
            self.ref_stats.check_so(so)
        for tag2a in self.stats_key_values['tag']:
            if tag2a.endswith('1') and self.tag_locations[tag2a]:
                tag2b = tag2a[:-1]
                if self.tag_locations[tag2b]:
                    count2a = len(self.tag_locations[tag2a])
                    count2b = len(self.tag_locations[tag2b])
                    count_only_full_error_cat_2a = (count2a > count2b)
                    count_only_full_error_cat_2b = (count2b > count2a)
                    s2a = '' if count2a == 1 else 's'
                    s2b = '' if count2b == 1 else 's'
                    error_cat = ('Warnings', 'Inconsistent tag variants',
                                 f"The files use both the numbered variant \\{tag2a} ({count2a} instance{s2a}) "
                                 f"and the equivalent unnumbered variant \\{tag2b} ({count2b} instance{s2b}). "
                                 f"They both mean the same thing.")
                    for loc in self.tag_locations[tag2a]:
                        self.record_error(error_cat + (f"\\{tag2a}",), loc, None,
                                          count_only_full_error_cat=count_only_full_error_cat_2a)
                    for loc in self.tag_locations[tag2b]:
                        self.record_error(error_cat + (f"\\{tag2b}",), loc, None,
                                          count_only_full_error_cat=count_only_full_error_cat_2b)
        for tag in self.user_defined_tags:
            self.record_error(("Warnings", "User-defined tags"), tag, None)

    def add_item_to_tag_prop_list(self, key, item):
        if self.tag_props.get(key) is None:
            self.tag_props[key] = []
        if item not in self.tag_props[key]:
            self.tag_props.get(key).append(item)

    def read_usfm_explanations(self, filename):
        with open(filename) as f:
            line_number = 0
            n_entries = 0
            current_explanation_id, current_explanation = None, ""
            for line in f:
                line_number += 1
                if m := regex.match(r'::explanation\s+(\S+)\s*$', line):
                    explanation_id = m.group(1)
                    if self.explanation_id_to_explanation.get(explanation_id):
                        sys.stderr.write(f"Error: duplicate explanation ID {explanation_id}"
                                         f" in line {line_number} of {filename} (ignoring duplicate)\n")
                        current_explanation_id, current_explanation = None, ""
                    else:
                        # record any prior explanation
                        if current_explanation_id and current_explanation:
                            self.explanation_id_to_explanation[current_explanation_id] = current_explanation
                            n_entries += 1
                        current_explanation_id, current_explanation = explanation_id, ""
                elif line.startswith(':'):
                    sys.stderr.write(f"Suspicious line {line_number} ({line.rstrip()}) in {filename}\n")
                elif current_explanation_id:
                    current_explanation += line
            # record any final explanation
            if current_explanation_id and current_explanation:
                self.explanation_id_to_explanation[current_explanation_id] = current_explanation
                n_entries += 1
            sys.stderr.write(f"Loaded {n_entries} explanations from the {line_number} lines of {filename}\n")

    def read_tag_prop_data(self, filename):
        with open(filename) as f:
            line_number = 0
            n_tag_entries = 0
            paragraph_format_tag_set = set()
            heading_tag_set = set()
            for line in f:
                line = line.strip()
                line_number += 1
                line_is_an_entry = False
                if line.strip() == '':
                    continue  # ignore any empty lines
                try:
                    d = json.loads(line)
                except json.decoder.JSONDecodeError as error:
                    sys.stderr.write(f'Error: {filename} line {line_number}: {error}\n')
                    continue
                tag_id = d.get('tag')
                if not tag_id:
                    sys.stderr.write(f"No tag ID found in {filename} line {line_number}: {line}\n")
                    continue
                self.tag_props[('registered-tag', tag_id)] = True
                for attribute in ('exp', 'exp-short', 'exp-long', 'default-attribute',                 # str
                                  'opening-tag', 'closing-tag',                                        # str
                                  'closing-p', 'immediately-self-closing', 'one-liner',                # bool
                                  'entity-category-markup', 'quotation-markup', 'visual-style',        # bool
                                  'can-have-attributes', 'can-have-entity-category-markup-children',   # bool
                                  'deprecated', 'undocumented', 'closing-deprecated', 'heading-p',     # bool
                                  'paragraph-format', 'word-p', 'intro-p', 'table-content',            # bool
                                  'closed-by', 'dont-close-inside',                                    # list[str]
                                  'redirections',                                                      # list[dict]
                                  'format', 'comment',                                                 # complex str
                                  ):
                    if (value := d.get(attribute)) is not None:
                        self.tag_props[(attribute, tag_id)] = value
                        line_is_an_entry = True
                        if attribute == 'paragraph-format':
                            paragraph_format_tag_set.add(tag_id)
                        elif attribute == 'heading-p':
                            heading_tag_set.add(tag_id)
                if isinstance(closed_by_tags := d.get('closed-by'), list):  # i.e. explicitly provided, not None
                    for closed_by_tag in closed_by_tags:
                        self.add_item_to_tag_prop_list(('closes', closed_by_tag), tag_id)
                else:  # by default, every tag closes itself
                    self.add_item_to_tag_prop_list(('closes', tag_id), tag_id)
                if exclusive_children := d.get('exclusive-children', []):
                    line_is_an_entry = True
                    self.tag_props[('exclusive-children', tag_id)] = exclusive_children
                    for exclusive_child in exclusive_children:
                        self.tag_props[('exclusive-siblings', exclusive_child)] = exclusive_children
                        for exclusive_child2 in exclusive_children:
                            self.add_item_to_tag_prop_list(('closes', exclusive_child), exclusive_child2)
                if children := d.get('children', []):
                    line_is_an_entry = True
                if all_children := exclusive_children + children:
                    self.tag_props[('children', tag_id)] = all_children
                    for child in all_children:
                        # Old: self.tag_props[('parent-tag', child)] = tag_id
                        self.add_item_to_tag_prop_list(('parent-tags', child), tag_id)
                        self.tag_props[('siblings', child)] = children
                        self.tag_props[('registered-tag', child)] = True
                if line_is_an_entry:
                    n_tag_entries += 1
            for paragraph_format_tag in paragraph_format_tag_set:
                for heading_tag in heading_tag_set:
                    self.add_item_to_tag_prop_list(('closes', paragraph_format_tag), heading_tag)
            sys.stderr.write(f"Read {n_tag_entries} tag entries from {filename}\n")

    def current_line_s(self) -> str | None:
        if self.current_line_number_start:
            if self.current_line_number_start == self.current_line_number_start:
                return f"{self.current_line_number_start}"
            else:
                return f"{self.current_line_number_start}-{self.current_line_number_end}"
        elif self.current_line_number_end:
            return f"{self.current_line_number_end}"
        else:
            return None

    def versification(self, ignore_verse: bool = False, ignore_chapter: bool = False) -> str | None:
        if self.current_chapter and not ignore_chapter:
            if self.current_verse and not ignore_verse:
                if self.current_book_id:
                    return f"{self.current_book_id} {self.current_chapter}:{self.current_verse}"
                else:
                    return f"{self.current_chapter}:{self.current_verse}"
            elif self.current_book_id:
                return f"{self.current_book_id} {self.current_chapter}"
        elif self.current_book_id:
            return self.current_book_id
        elif self.current_filename:
            if current_line_s := self.current_line_s():
                return f"{self.current_filename} l.{current_line_s}"
            else:
                return self.current_filename
        elif current_line_s := self.current_line_s():
            return f"l.{current_line_s}"
        else:
            return None

    def add_versification(self, error_location: str, ignore_verse: bool = False, ignore_chapter: bool = False) -> str:
        if versification := self.versification(ignore_verse=ignore_verse, ignore_chapter=ignore_chapter):
            return f"{error_location} ({versification})"
        else:
            return error_location

    def check_book_info(self, line: str, error_location: str, ls: LineStruct | None = None) -> None:
        numbered_book_ids = {"01GEN", "02EXO", "03LEV", "04NUM", "05DEU", "06JOS", "07JDG", "08RUT", "091SA", "102SA",
                             "111KI", "122KI", "131CH", "142CH", "15EZR", "16NEH", "17EST", "18JOB", "19PSA", "20PRO",
                             "21ECC", "22SNG", "23ISA", "24JER", "25LAM", "26EZK", "27DAN", "28HOS", "29JOL", "30AMO",
                             "31OBA", "32JON", "33MIC", "34NAM", "35HAB", "36ZEP", "37HAG", "38ZEC", "39MAL",
                             "41MAT", "42MRK", "43LUK", "44JHN", "45ACT", "46ROM", "471CO", "482CO", "49GAL", "50EPH",
                             "51PHP", "52COL", "531TH", "542TH", "551TI", "562TI", "57TIT", "58PHM", "59HEB", "60JAS",
                             "611PE", "622PE", "631JN", "642JN", "653JN", "66JUD", "67REV"}
        if m_line_number := regex.search(r'(?:line|l\.)\s*(\d+)', error_location):
            line_number = int(m_line_number.group(1))
        else:
            line_number = None
        if m_file := regex.search(r'\b(\d\d)([A-Z1-4][A-Z][A-Z])\S+', error_location):
            book_number_s, book_id = m_file.group(1, 2)
            if (line_number == 1) and ((book_number_s + book_id) in numbered_book_ids):
                self.current_book_id = book_id
                self.current_book = book_id
                # sys.stderr.write(f"Found book {book_id} (index {book_number_s})\n")
        new_book_p = False
        if book_m := regex.match(r'(?:\pC|\pZ)*\\id\s+([A-Z1-3][A-Z][A-Z])\b\s*(\S.*\S|\S|)\s*$', line,
                                 regex.IGNORECASE | regex.DOTALL):
            book_id = book_m.group(1)
            if (uc_book_id := book_id.upper()) != book_id:
                error_cat = ('Auto-repairable errors', 'Book ID',
                             f'Book ID "{book_id}" should be upper case: "{uc_book_id}"')
                self.record_error(error_cat, error_location, line)
                book_id = uc_book_id
            self.current_book_id = book_id
            self.current_book = self.current_book_id
            self.current_chapter = 0
            self.current_verse = None
            self.current_verse_s = None
            new_book_p = True
        # sys.stderr.write(f"New book ID:{self.current_book_id}: c:{self.current_chapter} l:{line_number}\n")
        # sys.stderr.write(f"Found book ID {self.current_book_id}\n")
        if ls:
            ls.book_id = self.current_book_id
        if (not self.current_book_id) and (book_m := regex.match(r'\\mt1?\s(\S.*\S)\s*$', line, regex.DOTALL)):
            self.current_book_name = book_m.group(1)
            if self.current_book_id is None:
                self.current_book = self.current_book_name
            # sys.stderr.write(f"New book name: {self.current_book_name} CB: {self.current_book}\n")
            self.current_chapter = 0
            self.current_verse = None
            self.current_verse_s = None
            new_book_p = True
        if new_book_p:
            self.check_for_missing_verses()

    def check_chapter_info(self, line: str, error_location: str, ls: LineStruct | None = None) -> None:
        # integrate with verse_info
        error_location = self.add_versification(error_location, ignore_chapter=True)
        if chapter_m := regex.match(r'^(.*)\\c\b(\s*)(\d+|)(.*)$', line, regex.DOTALL):
            pre_c, space, chapter_number_s, post_c = chapter_m.group(1, 2, 3, 4)
            if regex.match(r'[1-9]\d*', chapter_number_s):
                chapter_number = int(chapter_number_s)
                if chapter_number in self.chapters_in_book[self.current_book]:
                    error_cat = ('Errors', 'Chapter info', 'Duplicate chapter number')
                    self.record_error(error_cat, error_location, f"Duplicate chapter number {chapter_number}")
                elif chapter_number > self.current_chapter + 1:
                    error_cat = ('Errors', 'Chapter info', 'Missing chapter')
                    if self.current_chapter:
                        error_context = (f"Chapter {self.current_chapter} is directly followed by chapter"
                                         f" {chapter_number}")
                    else:
                        error_context = f"Book starts with chapter {chapter_number}"
                    self.record_error(error_cat, error_location, error_context)
                elif chapter_number < self.current_chapter:
                    error_cat = ('Errors', 'Chapter info', 'Wrong order of chapter numbers')
                    error_context = f"Chapter {self.current_chapter} is followed by chapter {chapter_number}"
                    self.record_error(error_cat, error_location, error_context)
                self.check_for_missing_verses()
                self.chapters_in_book[self.current_book].append(chapter_number)
                self.current_chapter = chapter_number
                self.current_verse = None
                self.current_verse_s = None
            else:
                error_cat = ('Errors', 'Chapter info', 'Missing chapter number')
                self.record_error(error_cat, error_location, line)
            if space == '':
                error_cat = ('Errors', 'Chapter info', 'Missing space before chapter number')
                self.record_error(error_cat, error_location, line)
            if not regex.match(r' *(?:\r?\n)?$', post_c):
                error_cat = ('Errors', 'Chapter info', 'Spurious material after chapter number')
                error_context = line
                if invisible_chars := regex.findall(r'(\pC|\pZ)', regex.sub(r'[ \r\n]', '', post_c)):
                    error_context += (f"   [Note: Spurious material includes invisible "
                                      f"{print_str_unicode_names(''.join(invisible_chars), ', ')}")
                self.record_error(error_cat, error_location, error_context)
        if ls:
            ls.chapter = self.current_chapter

    def combined_error_location(self, ignore_verse: bool = False) -> str | None:
        versification = self.versification(ignore_verse=ignore_verse)
        if self.current_filename and versification:
            error_location = f"{self.current_filename} ({versification})"
        elif self.current_filename:
            error_location = self.current_filename
        elif versification:
            error_location = versification
        else:
            error_location = None
        return error_location

    def check_for_missing_verses(self) -> None:
        if self.current_book_id and self.current_chapter:
            verses_in_chapter = sorted(set(self.verses_in_chapter[(self.current_book, self.current_chapter)]))
            current_verse_number = 0
            n_missing_verses = 0
            missing_verse_segments = []
            exempt_missing_verses = []
            for verse_number in verses_in_chapter:
                while verse_number > current_verse_number + 1:
                    next_versification = f"{self.current_book_id} {self.current_chapter}:{current_verse_number + 1}"
                    if next_versification in self.bible_config.often_omitted_verses:
                        exempt_missing_verses.append(current_verse_number + 1)
                        current_verse_number += 1
                    else:
                        break
                if verse_number > current_verse_number + 1:
                    n_missing_verses += (verse_number - (current_verse_number + 1))
                    if verse_number > current_verse_number + 2:
                        missing_verse_segments.append(f"{current_verse_number+1}-{verse_number-1}")
                    else:
                        missing_verse_segments.append(str(current_verse_number+1))
                current_verse_number = verse_number
            for exempt_missing_verse in exempt_missing_verses:
                error_cat = ('Info', 'Verse info', self.bible_config.often_omitted_verses_note,
                             'Missing verses of that kind')
                versification = f"{self.current_book_id} {self.current_chapter}:{exempt_missing_verse}"
                self.record_error(error_cat, versification, None)
            if missing_verse_segments:
                missing_verse_s = ', '.join(missing_verse_segments)
                error_cat = ('Errors', 'Verse info', 'Chapters with missing verses')
                error_context = f"Missing verse{'' if n_missing_verses == 1 else 's'}: {missing_verse_s}"
                self.record_error(error_cat, self.combined_error_location(ignore_verse=True), error_context)

    def check_line(self, line: str, error_location: str) -> None:
        error_location = self.add_versification(error_location)
        # merge_markers = ('=======', '<<<<<<<', '>>>>>>>')
        # for merge_marker in merge_markers:
        #     if merge_marker in line:
        #         error_cat = ('Severe errors', 'Unexpected merge marker', merge_marker)
        #         self.record_error(error_cat, error_location, line)
        if tags_with_spurious_spaces := regex.findall(r'\\(\s+)(\S+)', line):
            for space, text in tags_with_spurious_spaces:
                if m := regex.match(r'([a-z]+\d*)', text):
                    core_tag = m.group(1)
                    if self.tag_is_registered(core_tag):
                        error_cat = ('Auto-repairable errors', 'Tags',
                                     "Tags with spurious spaces after slash", f"\\ {core_tag}")
                        error_context = f"{line}  [Did you mean \\{core_tag} (without the space after \\)?]"
                        self.record_error(error_cat, error_location, error_context)
                else:
                    error_cat = ('Severe errors', 'Tags', "Slash followed by space. Cannot recognize a valid tag.")
                    self.record_error(error_cat, error_location, line)
        if tags_with_control_characters := regex.findall(r'\\(\pC)', line):
            for control_char in tags_with_control_characters:
                error_cat = ('Severe errors', 'Tags',
                             "Slash followed by control character. Cannot recognize a valid tag.")
                error_context = f"{line}  [Note: Slash followed by {print_char_unicode_name(control_char)}]"
                self.record_error(error_cat, error_location, error_context)
        if self_closing_tags := regex.findall(r'(\\\+?[a-z]+[1-9]?(?!\*)|)[^\\]*\\\*', line):
            for self_closing_tag in self_closing_tags:
                if self_closing_tag:
                    error_cat = ('Warnings', 'Tags', 'Special self-closing tag \\*', self_closing_tag)
                else:
                    error_cat = ('Severe errors', 'Tags', 'Orphan self-closing tag \\*')
                self.record_error(error_cat, error_location, line)
        if tags_with_bad_strings := regex.findall(r'\\(?!\+?[a-zA-Z]|\*)(\S+)', line):
            for _ in tags_with_bad_strings:
                error_cat = ('Severe errors', 'Tags',
                             "Slash followed by an invalid string. Cannot recognize a valid tag.")
                self.record_error(error_cat, error_location, line)
        if verse_tags_with_missing_backslash := regex.findall(r'\b(?<!\\)(v\s+\d+)', line,
                                                              flags=regex.IGNORECASE):
            for verse_tag_with_missing_backslash in verse_tags_with_missing_backslash:
                error_cat = ('Warnings', 'Tags', 'Verse tag with missing backslash?', verse_tag_with_missing_backslash)
                self.record_error(error_cat, error_location, line)
        if m := regex.search(r'([\[{“‘«‹⌞（［【「『《〈])((?:\pC|\pZ)*)$', line):
            delimiter = m.group(1)
            if (delimiter in "“‘") and ScriptDirection(text=line).is_right_to_left():
                error_cat = ('Info', 'Delimiters',
                             'A number of lines end in open delimiters, which is usually not a good sign, '
                             'but the lines tallied below are in a right-to-left script, '
                             'so those end-of-line open delimiters are apparently used as close delimiters instead.',
                             delimiter)
                self.record_error(error_cat, self.current_book_id, None)
            elif (delimiter == '“') and self.lang_code in ("rus", "ukr", "bel"):
                pass
            else:
                error_cat = ('Errors', 'Delimiters', 'Line ends in open delimiter', delimiter)
                error_context = line
                self.record_error(error_cat, error_location, error_context)
        if m := regex.search(r'([\[{“‘«‹⌞（［【「『《〈])((?:\pC|\pZ)*)(\\v|\\c)\s+(\d+)', line):
            d = {"\\v": "verse", "\\c": "chapter"}
            error_cat = ('Errors', 'Delimiters',
                         f'New {d.get(m.group(3))} is preceded by open delimiter on same line', m.group(1))
            error_context = line
            self.record_error(error_cat, error_location, error_context)
        if '|' in line:
            for line2 in line.split('\n'):
                if m := regex.match(r'(\s*)(\|)([a-z]+[1-9]?)(\s.*|)$', line2):
                    space, bad_slash, tag, rest = m.group(1, 2, 3, 4)
                    if self.tag_is_registered(tag):
                        error_cat = ('Auto-repairable errors', 'Suspicious pseudo-tag with wrong kind of slash',
                                     bad_slash + tag)
                        error_context = f"{line2}  [Did you mean \\{tag} (with a backslash instead of a vertical bar)?]"
                        self.record_error(error_cat, error_location, error_context)

    def check_verse_info(self, line: str, error_location: str, ls: LineStruct | None = None) -> None:
        # sys.stderr.write(f"CVI: EL:{error_location} CV:{self.current_verse} {line}\n")
        # todo pivot from single regex to findall+
        initial_current_verse_number = self.current_verse
        error_location = self.add_versification(error_location, ignore_verse=True)
        reported_missing_verse_number = False
        if verses_m := regex.match(r'^(.*)\\v(?![a-z])(\s*)(\d+)([ab](?=\s)|)\u200F?([-,])(\d+)([ab](?=\s)|)(\s*)(.*)$',
                                   line, regex.DOTALL):
            pre_v, space1, verse_number1_s, letter1, connector, verse_number2_s, letter2, space2, verse \
                = verses_m.group(1, 2, 3, 4, 5, 6, 7, 8, 9)
            verse_argument = f"{verse_number1_s}-{verse_number2_s}"
        elif verse_m := regex.match(r'^(.*)\\v(?![a-z])(\s*)(\d+|)([ab](?=\s)|)\u200F?(\s*)(.*)$', line, regex.DOTALL):
            pre_v, space1, verse_number1_s, letter1, space2, verse = verse_m.group(1, 2, 3, 4, 5, 6)
            verse_number2_s = verse_number1_s
            verse_argument = verse_number1_s
            letter2 = ''
        else:
            if ls:
                ls.verse = self.current_verse
            return
        if regex.match(r'[1-9]\d*', verse_number1_s):
            verse_number1 = int(verse_number1_s)
            self.current_verse = verse_number1
        else:
            error_cat = ('Severe errors', 'Verse info', 'Missing verse number')
            self.record_error(error_cat, error_location, line)
            verse_number1 = None
            reported_missing_verse_number = True
        if regex.match(r'[1-9]\d*', verse_number2_s):
            verse_number2 = int(verse_number2_s)
        else:
            verse_number2 = None
            if not reported_missing_verse_number:
                error_cat = ('Errors', 'Verse info', 'Missing verse number')
                self.record_error(error_cat, error_location, line)
        verse_numbers = []
        if verse_number1 and verse_number2:
            # line contains range: \v 10-11 ... \v 14, 15 ... \v 17-16,19
            line_without_control_character = regex.sub(r'\pC', '', line)
            verse_number_compounds_s = regex.findall(r'\\v\s*(\d+(?:-\d+)?(?:,\s?\d+(?:-\d+)?)*)',
                                                     line_without_control_character)
            for verse_number_compound in verse_number_compounds_s:
                for verse_section in regex.split(r',\s*', verse_number_compound):
                    if m := regex.match(r'(\d+)-?(\d*)$', verse_section):
                        verse_n1 = int(m.group(1))
                        verse_n2 = int(m.group(2)) if m.group(2) else verse_n1
                        if verse_n1 > verse_n2:
                            verse_n1, verse_n2 = verse_n2, verse_n1
                        for verse_n in range(verse_n1, verse_n2+1):
                            verse_numbers.append(verse_n)
            for verse_number in verse_numbers:
                if verse_number in self.verses_in_chapter[(self.current_book, self.current_chapter)]:
                    error_cat = ('Severe errors', 'Verse info', 'Duplicate verse number')
                    self.record_error(error_cat, error_location, f"Duplicate verse number {verse_number}")
            if verse_number1 > verse_number2:
                error_cat = ('Severe errors', 'Verse info', 'Wrong verse range order')
                error_context = f"Verse range {verse_number1}-{verse_number2}"
                self.record_error(error_cat, error_location, error_context)
            elif verses_m and (verse_number1 == verse_number2):
                error_cat = ('Errors', 'Verse info', 'Overly complicated verse range')
                error_context = f"Verse range {verse_number1}-{verse_number2}"
                self.record_error(error_cat, error_location, error_context)
            for verse_number in verse_numbers:
                self.verses_in_chapter[(self.current_book, self.current_chapter)].append(verse_number)
            self.current_verse = verse_number2
        elif verse_number1 and not verse_numbers:
            verse_numbers.append(verse_number1)
        self.current_verse_s = group_integers_into_spans(verse_numbers)
        if verse_numbers and initial_current_verse_number and (verse_numbers[0] < initial_current_verse_number):
            error_cat = ('Warnings', 'Verse info', 'Unexpected order of verse numbers')
            error_context = f"Verse {initial_current_verse_number} is directly followed by verse {verse_numbers[0]}"
            self.record_error(error_cat, error_location, error_context)
        if space1 == '':
            error_cat = ('Auto-repairable errors', 'Verse info', 'Missing space between \\v and verse number')
            self.record_error(error_cat, error_location, line)
        if verse == '':
            error_cat = ('Warnings', 'Verse info', 'No verse text on the same line as the verse tag (\\v)')
            self.record_error(error_cat, error_location, line)
        elif verse_number1_s and space2 == '':
            error_cat = ('Auto-repairable errors', 'Verse info',
                         'Missing space after verse number or verse number range')
            error_context = line
            if verse:
                error_context += (f"  [Note: \\v {verse_argument} is directly followed by "
                                  f"{print_char_unicode_name(verse[0])}]")
            self.record_error(error_cat, error_location, error_context)
        for verse_number, letter in [(verse_number1, letter1), (verse_number2, letter2)]:
            if letter:
                error_cat = ('Warnings', 'Verse info', 'Verse number includes letter', f'{verse_number}{letter}')
                self.record_error(error_cat, error_location, line)
        if ls:
            ls.verse = self.current_verse

    def read_file(self, filename: Path) -> None:
        if filename in self.filenames:
            sys.stderr.write(f"Warning: {filename} already read in.\n")
        else:
            file_basename = os.path.basename(filename)
            self.current_filename = file_basename
            self.filenames.append(file_basename)
            self.chapters_in_book = defaultdict(list)
            self.verses_in_chapter = defaultdict(list)
            self.current_book_id: str | None = None
            self.current_book_name: str | None = None
            self.current_book: str | None = None
            if self.repair_dir:
                repair_filename = self.repair_dir / file_basename
                self.repair_fh = open(repair_filename, 'w')
            fls = FileLineStruct(filename, sc=self)
            merge_markers = ('=======', '<<<<<<<', '>>>>>>>', '|||||||')
            next_ls = fls.first_ls
            while current_ls := next_ls:
                next_ls = current_ls.next_ls
                line = current_ls.s
                line_number = current_ls.from_line_number
                if (current_ls == fls.first_ls) and regex.match(r'\\id ', line):
                    self.current_chapter = 0
                    self.current_verse = None
                    self.current_verse_s = None
                for merge_marker in merge_markers:
                    if merge_marker in line:
                        error_cat = ('Severe errors', 'Unexpected merge conflict marker', merge_marker)
                        error_location = f"{file_basename} l.{line_number}"
                        self.record_error(error_cat, error_location, line)
            fls.expand_usfm_verses(self)
            fls.split_usfm_chapters_and_verses(self)
            next_ls = fls.first_ls
            current_revised_line_number = 0
            prev_key = None
            texts_for_current_key = set()
            while current_ls := next_ls:
                # if 'MAT' in str(self.current_filename):
                # sys.stderr.write(f"  TEST {current_ls}\n")  # todo
                current_revised_line_number += 1
                next_ls = current_ls.next_ls
                line = current_ls.s
                self.current_line = line
                self.current_line_number_start = current_ls.from_line_number
                self.current_line_number_end = current_ls.to_line_number
                current_ls.revised_line_number = current_revised_line_number
                start, end = self.current_line_number_start, self.current_line_number_end
                line_number_s = str(start) if start == end else f"{start}-{end}"
                error_location = f"{file_basename} l.{line_number_s}"
                if self.repair_fh:
                    line = self.repair_line(line, current_ls, fls)
                so = UsfmObject(line, self, file_basename, start, 1)
                for open_element in so.open_elements:
                    if open_element.is_open:
                        open_element.is_open = False
                        if open_element.end_position is None:
                            current_line, current_column = so.current_position()
                            open_element.end_position = (max(current_line-1, open_element.start_position[0] or 0),
                                                         None)
                flat = so.flat_print()
                if flat != line:
                    sys.stderr.write(f"INPUT ne FLAT for {file_basename} l.{line_number_s}:\n"
                                     f"{viz_str(line)}\n{viz_str(flat)}\n\n")
                self.check_book_info(line, error_location, current_ls)
                self.check_chapter_info(line, error_location, current_ls)
                self.check_verse_info(line, error_location, current_ls)
                self.check_line(line, error_location)
                so.versification = self.versification()
                so.close_applicable_open_elements_at_end_of_line()
                so.check(error_location)
                if line and regex.match(r'(?:\pZ|\pC)*\pL', line):
                    context_clause = f" (prev: {current_ls.prev_ls.s.rstrip()})" \
                        if current_ls.prev_ls and ('\\' in current_ls.prev_ls.s) \
                        else ""
                    sys.stderr.write(f"Line starts with plain text {so.versification} l.{line_number_s} "
                                     f"{context_clause}\n")
                    if self.user in ('dev', 'translator', None):
                        error_cat = ('Warnings', 'Line starts with plain text, not a tag such as \\v')
                        self.record_error(error_cat, so.versification, line)
                for reg_slasher in \
                        regex.findall(r'(?<!\/\/\/|https?:[-_\/#%&.a-zA-Z0-9]+)(\/\+?[a-z]+[0-9]?)\b',
                                      line):
                    tag = reg_slasher.lstrip('/+')
                    if self.tag_is_registered(tag):
                        error_cat = ('Auto-repairable errors', 'Suspicious pseudo-tag with wrong kind of slash',
                                     reg_slasher)
                        error_context = f"{line}  [Did you mean \\{tag} (with a backslash instead of a regular slash)?]"
                        self.record_error(error_cat, so.versification, error_context)
                if self.repair_fh:
                    so.repair(current_ls, fls)
                    repaired_line = so.flat_print()
                    current_ls.repaired_s = repaired_line
                    self.repair_fh.write(repaired_line)
                key = (self.current_book_id,
                       self.current_chapter or None,
                       self.current_verse_s or (str(self.current_verse) if self.current_verse else None))
                bte = self.bible_text_extract_dict.get(key)
                if bte is None:
                    so.extract_struct_args()
                    bte = BibleTextExtracts(key)
                    self.bible_text_extract_dict[key] = bte
                bte.add_so(so)
                bte.check(so)
                self.so_list.append(so)
                if key != prev_key:
                    texts_for_current_key = set()
                verse_texts = [bte.verse_text] if bte.verse_text else []
                for extract in (verse_texts + bte.footnotes + bte.figures + bte.titles + bte.misc_texts):
                    if txt := extract.get('txt'):
                        if txt not in texts_for_current_key:
                            self.corpus_model.add_txt(txt)
                            texts_for_current_key.add(txt)
                prev_key = key
            if self.repair_fh:
                self.repair_fh.close()

    @staticmethod
    def regex_form(s: str) -> str:
        rest = s
        result = ''
        while m3 := regex.match(r'(.*?)(?:\.{3,}|…)(.*)', rest):
            pre_ellipsis, rest = m3.group(1, 2)
            result += guard_regex(pre_ellipsis) + '.*'
        result += guard_regex(rest)
        result = regex.sub(r'\s+', r'\\s+', result)
        return result

    @staticmethod
    def string_contains_ellipsis(s: str) -> bool:
        return bool(regex.search(r"(?:\.{3,}|…)", s))

    def register_footnote_quote_ellipses(self, quote: str, bte_key: Tuple[str, str, str]):
        if ellipses := regex.findall(r"(?:\.{3,}|…)", quote):
            error_location = self.error_location_based_on_bte_key(bte_key)
            for ellipsis_s in ellipses:
                self.ellipsis_counts[ellipsis_s] += 1
                if self.current_book_id and self.current_chapter and self.current_verse:
                    self.ellipsis_locations[ellipsis_s].append((error_location, quote))

    def find_quote_in_verse_text(self, quote: str, verse_text: str) -> str | None:
        """
        quote might include ellipses
        quote might have different capitalization
        quote and verse_text might have different whitespace groups
        returns sub-string of verse_text matching quote (with any ellipses expanded), case non-sensitive
        """
        if (position := verse_text.lower().find(quote.lower())) >= 0:
            return verse_text[position:position+len(quote)]
        re_quote = self.regex_form(quote)
        if m := regex.search(re_quote, verse_text, flags=regex.IGNORECASE | regex.DOTALL):
            return m[0]
        return None

    @staticmethod
    def error_location_based_on_bte_key(bte_key: Tuple[str, str, str]) -> str:
        if (len(bte_key) >= 1) and bte_key[0]:
            error_location = f"{bte_key[0]}"
        else:
            error_location = "?"
        if (len(bte_key) >= 2) and bte_key[1]:
            error_location += f" {bte_key[1]}"
        if (len(bte_key) >= 3) and bte_key[2]:
            error_location += f":{bte_key[2]}"
        return error_location

    def check_bible_text_extracts(self) -> None:
        n = 0
        for bte_key in self.bible_text_extract_dict:
            bte = self.bible_text_extract_dict[bte_key]
            verse_text = bte.verse_text.get('txt') if bte.verse_text else ''
            for footnote in bte.footnotes:
                footnote_text = footnote.get('txt', '')
                for quote in footnote.get('quotes', []):
                    n += 1
                    self.register_footnote_quote_ellipses(quote, bte_key)
                    quote_in_verse_text = self.find_quote_in_verse_text(quote, verse_text)
                    if not quote_in_verse_text:
                        # quote.lower() not in verse_text.lower():
                        error_cat_element = 'Footnote quotation does not appear in verse'
                        self.error_cat_element_to_explanation_id[error_cat_element] = 'FQ-NOT-IN-V'
                        f_quotation_without_punct_suffix, punct_suffix = self.trailing_punct(quote, verse_text)
                        if punct_suffix:
                            error_cat = ('Warnings', error_cat_element, 'Spurious trailing quote punctuation',
                                         punct_suffix, f'Footnote quotation: {quote}')
                        else:
                            error_cat = ('Warnings', error_cat_element, f'Footnote quotation: {quote}')
                        error_location = self.error_location_based_on_bte_key(bte_key)
                        # re_quote = self.regex_form(quote)
                        # sys.stderr.write(f"quote regex {quote} ||| {re_quote} ||| {quote_in_verse_text}\n")
                        # sys.stderr.write(f"FNE: {error_location} Verse: {verse_text}
                        # • Quote: {quote} • Footnote: {footnote_text}\n")
                        self.record_error(error_cat, error_location,
                                          f"Verse: {verse_text} • Footnote: {footnote_text}")

    def check_for_inconsistent_ellipses(self):
        if len(self.ellipsis_counts.keys()) > 1:
            sys.stderr.write(f"ELLIPSES: {self.ellipsis_counts}\n")
            ellipses = sorted(self.ellipsis_counts.keys(), key=lambda e: self.ellipsis_counts[e], reverse=True)
            max_count = self.ellipsis_counts[ellipses[0]]
            max2_count = self.ellipsis_counts[ellipses[1]]
            error_cat_element = 'Inconsistent footnote quote ellipses'
            if max_count > 2 * max2_count:
                dominant_ellipsis = ellipses[0]
                error_cat_element += (f" &mdash; Dominant footnote quote ellipsis: "
                                      f"{ellipses[0]} ({max_count}) Non-dominant")
            else:
                dominant_ellipsis = None
            for ellipsis_s in ellipses:
                error_cat = ('Warnings', error_cat_element, ellipsis_s)
                # count = self.ellipsis_counts[ellipsis_s]
                if ellipsis_s != dominant_ellipsis:
                    locations = self.ellipsis_locations[ellipsis_s]
                    for location, footnote_quote in locations:
                        self.record_error(error_cat, location, footnote_quote or ellipsis_s)

    def repair_line(self, s: str, filename_loc: str, fls: FileLineStruct | None = None) -> str:
        if 'chapter-and-verse-tag' in self.repair_set:
            orig_s = s
            recorded_change_p = False
            rest, s = s, ''
            while m := regex.match(r'(.*?)([\\\/])((?:\pC|\pZ)*)(c|v)(?![a-z])((?:\pC|\pZ)*)(.*)$', rest,
                                   flags=regex.IGNORECASE | regex.DOTALL):
                pre, slash, post_slash, raw_core_tag, post_tag, rest = m.group(1, 2, 3, 4, 5, 6)
                core_tag = raw_core_tag.lower()
                new_open_tag = f'\\{core_tag} '
                s += pre + new_open_tag
                # wrong slash
                if slash == '/':
                    self.record_repair((f'\\{core_tag} tag repair',
                                        f'Changed type of slash from /{core_tag} to \\{core_tag}'), filename_loc)
                    recorded_change_p = True
                # spurious material inside \\c or \\v
                if post_slash != '':
                    self.record_repair((f'\\{core_tag} tag repair',
                                        f'Deleted “{print_str_unicode_names(post_slash)}” inside \\{core_tag}'),
                                       filename_loc)
                    recorded_change_p = True
                # Missing space after \\c or \\v
                if post_tag == '':
                    self.record_repair((f'\\{core_tag} tag repair',
                                        f'Added missing space after \\{core_tag}'), filename_loc)
                    recorded_change_p = True
                # Non-standard space after \\c or \\v
                elif post_tag != ' ':
                    self.record_repair((f'\\{core_tag} tag repair',
                                        f'Changed “{print_str_unicode_names(post_tag)}” to space after \\{core_tag}'),
                                       filename_loc)
                    recorded_change_p = True
            s += rest
            # Catch any other repairs
            if (s != orig_s) and (not recorded_change_p):
                self.record_repair((f'\\c and \\v tag repair',),
                                   filename_loc)
        if not s.endswith('\n'):
            if (not s.endswith('\r')) and fls and fls.lines_end_in_cr_lf:
                s += '\r'
            s += '\n'
        return s

    def record_repair(self, repair_cat: tuple, repair_loc: str | None, repair_id: str | None = None) -> None:
        if repair_cat and (repair_cat[0] != 'Silent'):
            self.repair_counts[()] += 1
        if repair_id:
            self.repair_id_to_repair_tuple[repair_id] = repair_cat
        # sys.stderr.write(f"*** Record repair: {repair_cat} {repair_loc} {repair_string}\n")
        for repair_sub_cat_index in range(len(repair_cat)):
            repair_sub_cat = repair_cat[repair_sub_cat_index]
            repair_pre_cat = repair_cat[0:repair_sub_cat_index]
            repair_acc_cat = repair_cat[0:repair_sub_cat_index + 1]
            self.repair_key_values[repair_pre_cat].add(repair_sub_cat)
            self.repair_counts[repair_acc_cat] += 1
            if repair_loc and (repair_sub_cat_index == len(repair_cat) - 1):  # full repair_cat
                self.repair_locations[repair_cat].append(repair_loc)

    def repair_report_to_html(self) -> None:
        timestamp = datetime.datetime.now().replace(microsecond=0).isoformat()
        repair_log_filename_with_timestamp = self.repair_dir / f"repair-log-{timestamp}.html"
        repair_log_filename = self.repair_dir / f"repair-log.html"
        with open(repair_log_filename_with_timestamp, 'w') as f_log:
            info_filename = None
            info_file_dir_candidates = []
            if dir1 := (Path(os.path.abspath(self.dir)) if self.dir else None):
                info_file_dir_candidates.append(dir1)
            if dir2 := (Path(os.path.dirname(dir1)) if dir1 else None):
                info_file_dir_candidates.append(dir2)
            for info_file_dir_candidate in info_file_dir_candidates:
                info_file_candidate = info_file_dir_candidate / 'info.json'
                if isfile(str(info_file_candidate)):
                    info_filename = info_file_candidate
                    break
            try:
                f_info = open(info_filename)
                info_dict = json.loads(f_info.read())
                f_full = info_dict.get('full') or info_dict.get('short') or info_dict.get('lc') or 'f'
                f_lang_code = info_dict.get('lc')
                f_log.write(html_head(f'USFM Repair Log for  {f_full}', timestamp, f'UR {f_lang_code}'))
                f_info.close()
            except FileNotFoundError:
                f_log.write(html_head(f'USFM Repair Log', timestamp, 'UR'))
            n = self.repair_counts[()]
            s = '' if n == 1 else 's'
            title = f'Repair log ({n} instance{s})'
            f_log.write(f"<h3>{title}</h3>\n")
            f_log.write("Note: Some verses might contain multiple types of repairs. "
                        "In that case, any such verses will be listed in all appropriate repair type sections, "
                        "with all repairs shown for any given verse.<p>\n")
            self.repair_report_to_html_rec(f_log)
            print_html_foot(f_log)
            if os.path.islink(repair_log_filename):
                os.unlink(repair_log_filename)
            os.symlink(repair_log_filename_with_timestamp, repair_log_filename)
            sys.stderr.write(f"Wrote repair logs to {repair_log_filename}\n")

    def repair_report_to_html_rec(self, f_log, report_pre_cat: tuple = ()) -> None:
        global n_toggle_indexes
        f_log.write("  <ul>\n")
        for report_sub_cat in sorted(self.repair_key_values[report_pre_cat],
                                     key=lambda x: -self.repair_counts[report_pre_cat + (x,)]):
            report_cat = report_pre_cat + (report_sub_cat,)
            report_cat_count = self.repair_counts[report_cat]
            plural_s = '' if report_cat_count == 1 else 's'
            f_log.write(f"  <li> Repair log: {report_sub_cat} ({report_cat_count} instance{plural_s})\n")
            if repair_locations := sorted(self.repair_locations[report_cat], key=self.location_sort):
                f_log.write("  <table cellpadding='3' cellspacing='0'>\n")
                bundled_repair_locations = self.bundle_duplicates(repair_locations, explicit_counts_p=True)
                max1, max2 = 30, 40
                n_locations, n_instances = 0, 0
                in_hiding = False
                n_bundled_repair_locations = len(bundled_repair_locations)
                for (bundled_repair_location, count) in bundled_repair_locations:
                    if (not in_hiding) and n_locations >= max1 and n_bundled_repair_locations > max2:
                        n_toggle_indexes += 1
                        toggle_index = f"t{n_toggle_indexes}"
                        n_more = n_bundled_repair_locations - n_locations
                        style_clause = 'style="color:navy; text-decoration:underline;font-weight:bold;"'
                        onclick_clause = f"""onclick="toggle_info('{toggle_index}');" """
                        # number of additional instances: report_cat_count-n_instances
                        toggle_text = (f"<span {style_clause} {onclick_clause}>Show {n_more} more entries</span> "
                                       f"for repair log: <i>{report_sub_cat}</i>")
                        f_log.write(f'<tr><td colspan="2">{toggle_text}</td></tr>\n')
                        f_log.write("  </table>\n")
                        f_log.write(f" <div id='{toggle_index}' style='display:none;'>\n")
                        f_log.write("  <table cellpadding='3' cellspacing='0'>\n")
                        in_hiding = True
                    n_locations += 1
                    n_instances += count
                    if isinstance(bundled_repair_location, LineStruct):
                        ls = bundled_repair_location
                        loc, filename, line_col = ls.file_loc()
                        loc_rev, filename_rev, line_col_rev = ls.file_loc(revised_line_number_p=True)
                        line_col_exp = regex.sub(r'\bl\.', 'line: ', line_col)
                        line_col_rev_exp = regex.sub(r'\bl\.', 'line: ', line_col_rev)
                        title = html_nobr(f"{filename}&nbsp;&nbsp;&nbsp; {line_col_exp}")
                        title_rev = html_nobr(f"{filename_rev}&nbsp;&nbsp;&nbsp; {line_col_rev_exp}")
                        colored_s, colored_repaired_s = StringDiff(ls.s, ls.repaired_s).diff(_loc=loc)
                        count_clause = ''
                        if count >= 2:
                            count_clause = f"&nbsp;<span style='color:#AAAAAA;font-size:80%;'>({count})</span>"
                            title += f"&nbsp;&nbsp;&nbsp;{count}&nbsp;instances"
                        f_log.write(f'<tr><td valign="top"><span patitle="{title}">'
                                    f'{html_nobr(loc)}{count_clause}</span></td>'
                                    f'<td>{colored_s}</td></tr>\n')
                        f_log.write(f'<tr><td valign="top"><span pbtitle="{title_rev}">{"&nbsp;" * 8}</span></td>'
                                    f'<td>{colored_repaired_s}</td></tr>\n')
                    else:
                        f_log.write(f'<tr><td colspan="3">{bundled_repair_location} (???)</tr>\n')
                f_log.write("  </table>\n")
                if in_hiding:
                    f_log.write(" </div><p>\n")
            self.repair_report_to_html_rec(f_log, report_cat)
        f_log.write("  </ul>\n")


def main() -> None:
    default_config_filenames = ['BibleTranslationConfig.jsonl']

    parser = argparse.ArgumentParser()
    parser.add_argument("filenames", type=Path, nargs="*", help='default: *sfm files')
    parser.add_argument('-d', '--dir', type=str, default='.', metavar='DEFAULT INPUT FILENAMES DIRECTORY')
    parser.add_argument('-o', '--out', type=str, default='usfm_check.txt', metavar='TXT-OUTPUT-FILENAME')
    parser.add_argument('-x', '--html', type=str, default='usfm_check.html', metavar='HTML-OUTPUT-FILENAME')
    parser.add_argument('-j', '--json', type=str, default='usfm_check.json', metavar='JSON-OUTPUT-FILENAME')
    parser.add_argument('-e', '--extract', type=str, default='extract.jsonl',
                        metavar='JSONL-TEXT-EXTRACT-OUTPUT-FILENAME',
                        help="output of plain verse texts, footnotes, titles")
    parser.add_argument('--lc', type=str, default=None,
                        metavar='LANGUAGE-CODE', help="ISO 639-3, e.g. 'fas' for Persian")
    parser.add_argument('-s', '--scorecard', type=str, default='usfm_scorecard.json',
                        metavar='SCORECARD-OUTPUT-FILENAME')
    parser.add_argument("-r", "--repair", type=str, metavar='OUTPUT DIRECTORY FOR REPAIRED FILES')
    parser.add_argument("-p", "--parse", type=str, help='for testing')
    parser.add_argument('-c', '--config_filename', type=Path,
                        help='(optional) document configuration file in JSONL format, will search list of '
                             f'default_config_filenames ({default_config_filenames}) if not provided as arg')
    parser.add_argument('-u', '--user', type=str, default=None, help='values: dev|translator')
    parser.add_argument('-m', '--misc_data_filename', default='../morph_variants.txt')
    parser.add_argument('--s1', type=str, default=None, help='for testing')
    parser.add_argument('--s2', type=str, default=None, help='for testing')
    args = parser.parse_args()
    if args.s1 and args.s2:
        d1, d2 = StringDiff(args.s1, args.s2).diff()
        sys.stderr.write(f"D1: {d1}\n")
        sys.stderr.write(f"D2: {d2}\n")
    if args.user not in ('dev', 'translator', 'consultant', None):
        raise ValueError(f'Invalid args.user: {args.user}')
    date = f"{datetime.datetime.now():%B %-d, %Y at %-H:%M}"
    lang_code = args.lc
    info_filename = 'info.json'
    try:
        f_info = open(info_filename)
        info_dict = json.loads(f_info.read())
        f_lang_code = info_dict.get('lc')
        f_full = info_dict.get('full') or info_dict.get('short') or f_lang_code or 'f'
        if not lang_code:
            lang_code = f_lang_code
    except FileNotFoundError:
        f_full = None
    cwd = Path(os.path.abspath(os.getcwd()))
    parent_dir = Path(os.path.dirname(cwd))

    config_filename = None
    if args.config_filename:
        config_filename = args.config_filename
    else:
        for config_dir in (cwd, parent_dir):
            for default_config_filename in default_config_filenames:
                config_filename_cand = config_dir / default_config_filename
                if os.path.exists(config_filename_cand):
                    config_filename = config_filename_cand
                    break
    if config_filename:
        # sys.stderr.write(f"Config: {str(config_filename)}\n")
        doc_config = DocumentConfiguration(Path(config_filename))
    else:
        if default_config_filenames:
            raise ValueError(f'No configuration filename provided, '
                             f'neither as argument or default ({default_config_filenames})')
        else:
            raise ValueError('No configuration filename provided')
    misc_data_dict = {}
    if args.misc_data_filename and os.path.exists(args.misc_data_filename):
        DataManager.read_file(args.misc_data_filename, misc_data_dict, selectors=['owl'])
    bible_config = BibleUtilities()
    usfm_check = UsfmCheck(directory=args.dir, user=args.user, doc_config=doc_config, lang_code=lang_code)
    usfm_check.bible_config = bible_config
    usfm_check.misc_data_dict = misc_data_dict
    if args.repair:
        if args.repair.startswith('/'):
            usfm_check.repair_dir = args.repair
        else:
            usfm_check.repair_dir = cwd / args.repair
        if not os.path.isdir(usfm_check.repair_dir):
            os.mkdir(usfm_check.repair_dir, mode=0o775)
    usfm_folder = 'usfm'
    if not os.path.isdir(usfm_folder):
        os.mkdir(usfm_folder, mode=0o775)
    if args.html:
        full_html_output_filename = cwd / args.html
        f_html_out = open(args.html, 'w')
        if f_full and lang_code:
            f_html_out.write(html_head(f'Selected USFM (Paratext format) Checks for  {f_full}', date,
                                       f'USFM {lang_code}'))
        else:
            f_html_out.write(html_head(f'Selected USFM (Paratext format) Checks', date, 'USFM'))
    else:
        f_html_out = None
        full_html_output_filename = None
    if args.parse:
        # line = "\\v 28 \\f + \\ft The ... have Mark 15:28, \\fqa The ... says, 'He was ... ones,'\n"
        # line = "\\v 22 He left. \\f + \\fr 49.10 \\ft prime boat \\fq broom\\fq* am I what-what you bear.\\f*"
        # line = "\\v 22 hello \\fig Offering platform|lb00255c.tif|span|8:20|Louise Bass|An das Land|8:20\\fig*"
        # line = "\\id GEN\n\\c 1\n\\v 22 hello\n\\p para \\m more"
        # line = "\\v 22 verse\n\\s1 heading\n\\m more"
        # line = "\\s1 heading\n\\m more"
        # line = "\\m quoted \\bk Book\\bk*again"
        line = "\\v 1 verse text\n\\b\n\\v 2 more text"
        usfm_check.current_line = line
        usfm_check.current_line_number_start = 1
        usfm_check.current_line_number_end = usfm_check.current_line_number_start
        print(f'Input: {line} [len: {len(line)}]\n')
        so = UsfmObject(line, usfm_check, None, 1, 1)
        so.close_applicable_open_elements_at_end_of_line()
        so.extract_struct_args()
        print(so.pprint())
        flat = so.flat_print()
        print(f'FlatO: {flat} [len: {len(flat)}]\n')
        usfm_check.error_propagation()
        print(usfm_check.tag_stats())
        print(usfm_check.error_report())
        return
    if args.filenames:
        for filename in args.filenames:
            usfm_check.read_file(usfm_check.dir / filename)
    else:
        for filename in sorted([f for f in listdir(usfm_check.dir) if isfile(join(usfm_check.dir, f))]):
            if regex.search(r'\.u?sfm$', filename, regex.IGNORECASE):
                usfm_check.read_file(usfm_check.dir / filename)
    usfm_check.check_for_missing_verses()
    usfm_check.check_bible_text_extracts()
    usfm_check.check_for_inconsistent_ellipses()
    n_files = len(usfm_check.filenames)
    sys.stderr.write(f"Read in {n_files} USFM file{'' if n_files == 1 else 's'}.\n")
    if usfm_check.n_operations_in_expand_usfm_verses:
        sys.stderr.write(f"  Expand USFM verse operation (no. ops/no. fewer lines): "
                         f"{usfm_check.n_operations_in_expand_usfm_verses}"
                         f"/{usfm_check.n_fewer_lines_in_expand_usfm_verses}\n")
    if usfm_check.n_operations_in_split_usfm_chapters_and_verses:
        sys.stderr.write(f"  Split USFM verse operations (no. ops/no. additional lines): "
                         f"{usfm_check.n_operations_in_split_usfm_chapters_and_verses}"
                         f"/{usfm_check.n_additional_lines_in_split_usfm_chapters_and_verses}\n")
    usfm_check.final_check()
    if args.out:
        f_txt = open(args.out, 'w')
    else:
        f_txt = sys.stdout
    usfm_check.error_propagation()
    f_txt.write(usfm_check.tag_stats() + '\n')
    f_txt.write(usfm_check.error_report())
    if f_html_out:
        f_html_out.write(f"Note: These Selected USFM (Paratext format) Checks "
                         f"are new and still under development.\n")
        f_html_out.write(f"<p><hr><p>\n")
        f_html_out.write(usfm_check.tag_stats(html_p=True) + '\n')
        f_html_out.write(f"<p><hr><p>\n")
        f_html_out.write(usfm_check.error_report(html_p=True))
    if args.out:
        f_txt.close()
    if args.scorecard:
        with open(args.scorecard, 'w') as f_scorecard:
            d = {}
            for top_error_cat in ("Severe errors", "Errors", "Auto-repairable errors", "Warnings"):
                d[top_error_cat] = usfm_check.error_counts[(top_error_cat,)]
            f_scorecard.write(json.dumps(d) + "\n")
    if f_html_out:
        print_html_foot(f_html_out)
        f_html_out.close()
        sys.stderr.write(f"Wrote HTML output to {full_html_output_filename}\n")
    usfm_check.corpus_model.letter_ngram_stats()
    usfm_check.corpus_model.report_stats(Path(usfm_folder) / "log-keyword-candidates.txt")
    if usfm_check.repair_counts[()]:
        # sys.stderr.write(f"Repair-key-values:{usfm_check.repair_key_values}\n")
        # sys.stderr.write(f"Repair-counts: {usfm_check.repair_counts}\n")
        # sys.stderr.write(f"Repair-locations:\n")
        # for repair_cat in usfm_check.repair_locations:
        #     repair_locations = usfm_check.repair_locations[repair_cat]
        #     n_repair_locations = len(repair_locations)
        #     sys.stderr.write(f"  {repair_cat} [{n_repair_locations}] instance(s)\n")
        #     max_n_repair_locations = 1
        #     for repair_location in repair_locations[0:max_n_repair_locations]:
        #         sys.stderr.write(f"    {repair_location}\n")
        usfm_check.repair_report_to_html()
    if args.extract and args.extract not in ('None', ):
        try:
            with open(args.extract, 'w') as f_extract:
                for key in usfm_check.bible_text_extract_dict:
                    bte = usfm_check.bible_text_extract_dict.get(key)
                    f_extract.write(str(bte))
                if usfm_check.extract_ignore_tag_count:
                    sys.stderr.write("  In extraction, ignored tags:")
                    for tag in usfm_check.extract_ignore_tag_count:
                        count = usfm_check.extract_ignore_tag_count[tag]
                        sys.stderr.write(f" {tag} ({count})")
                    sys.stderr.write("\n")
                sys.stderr.write(f"Wrote extracted texts to {args.extract}\n")

        except IOError:
            sys.stderr.write(f"Could not write to {args.extract}\n")
    if usfm_check.log_message_count:
        sys.stderr.write("Message summary:\n")
        for message in usfm_check.log_message_count:
            count = usfm_check.log_message_count[message]
            sys.stderr.write(f"  {message} ({count})\n")
    if usfm_check.log_count_dict:
        for key in usfm_check.log_count_dict:
            sys.stderr.write(f"  {key}: {usfm_check.log_count_dict[key]}\n")
    if usfm_check.other_tag_count_dict:
        other_heading_tag_count_elements = []
        other_intro_tag_count_elements = []
        other_tag_count_elements = []
        for key in sorted(usfm_check.other_tag_count_dict.keys(),
                          key=lambda x: usfm_check.other_tag_count_dict[x], reverse=True):
            element = f"\\{key} ({usfm_check.other_tag_count_dict[key]})"
            element_assigned_p = False
            if usfm_check.tag_props.get(('heading-p', key)):
                other_heading_tag_count_elements.append(element)
                element_assigned_p = True
            if usfm_check.tag_props.get(('intro-p', key)):
                other_intro_tag_count_elements.append(element)
                element_assigned_p = True
            if not element_assigned_p:
                other_tag_count_elements.append(element)
        if other_heading_tag_count_elements:
            sys.stderr.write(f"  # other heading tags: {', '.join(other_heading_tag_count_elements)}\n")
        if other_intro_tag_count_elements:
            sys.stderr.write(f"  # other intro tags: {', '.join(other_intro_tag_count_elements)}\n")
        if other_tag_count_elements:
            sys.stderr.write(f"  # other tags: {', '.join(other_tag_count_elements)}\n")
    # if result := usfm_check.ref_stats:
    #     sys.stderr.write(f"Ref-stats:\n{result}\n")


if __name__ == "__main__":
    main()

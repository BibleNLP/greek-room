#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Written by Ulf Hermjakob, USC/ISI
This script analyzes a given text for a wide range of anomalies.
When using STDIN and/or STDOUT, it might be necessary, particularly for older versions of Python, to do
'export PYTHONIOENCODING=UTF-8' before calling this Python script to ensure UTF-8 encoding.
"""
# -*- encoding: utf-8 -*-

from __future__ import annotations
import argparse
import io
import json
import datetime
from collections import defaultdict
import logging as log
import os
from pathlib import Path
import re
import regex
import sys
from tqdm.auto import tqdm
from typing import IO, Optional, TextIO, Tuple, List
import unicodedata as ud
import greekroom.wildebeest.wb_pprint_html as wb_pp
# from utilities import ScriptDirection
from greekroom.gr_utilities import general_util, html_util, script_direction, corpus
from greekroom import __version__ as __greekRoomVersion__
from greekroom import __formatVersion__ as __greekRoomFormatVersion__
from greekroom.wildebeest import __version__ as __wildebeestVersion__
from greekroom.wildebeest import last_mod_date as wildebeest_last_mod_date
from greekroom.wildebeest.wb_normalize import Wildebeest
from greekroom.versification.versification import BackVersification


log.basicConfig(level=log.INFO)


def guard_html(s: str) -> str:
    s = re.sub('&', '&amp;', s)
    s = re.sub('<', '&lt;', s)
    s = re.sub('>', '&gt;', s)
    s = re.sub('"', '&quot;', s)
    return s


def slot_value_in_double_colon_del_list(line: str, slot: str, default: Optional = None) -> str:
    """For a given slot, e.g. 'cost', get its value from a line such as '::s1 of course ::s2 ::cost 0.3' -> 0.3
    The value can be an empty string, as for ::s2 in the example above."""
    m = regex.match(fr'(?:.*\s)?::{slot}(|\s+\S.*?)(?:\s+::\S.*|\s*)$', line)
    return m.group(1).strip() if m else default


def control_character_name(char: str) -> str | None:
    # Dictionary with the names of the most common control characters.
    control_character_dict = {
        '\x00': 'NULL', '\x01': 'START OF HEADING', '\x02': 'START OF TEXT', '\x03': 'END OF TEXT',
        '\x07': 'BELL', '\x08': 'BACKSPACE', '\x09': 'TAB', '\x0A': 'NEW LINE',
        '\x0D': 'CARRIAGE RETURN', 'x1B': 'ESCAPE', '\x7F': 'DELETE'}
    if char in control_character_dict:
        return f'control character {control_character_dict[char]}'
    hex_code = f"U+{ord(char):04X}"
    if char <= '\x1F':            # Unicode block C0
        return f"control character {hex_code}"
    elif '\x80' <= char <= '\x9F':  # Unicode block C1
        return f"control character {hex_code}"
    else:
        return None


def simple_char_unicode_name(char: str) -> str:
    return ud.name(char, None) or control_character_name(char) or f"U+{ord(char):04X}"


def simple_unicode_names(s: str, delimiter: str = ', ') -> str:
    return delimiter.join(map(simple_char_unicode_name, s))


def print_char_unicode_name(char: str) -> str:
    c_name = ud.name(char, None) or control_character_name(char) or ''
    invisible_char = regex.match(r'(\pZ|\pC)', char)
    hex_code = f"U+{ord(char):04X}"
    return f"{c_name} ({hex_code})" if invisible_char else f"{char} ({c_name}, {hex_code})"


def print_str_unicode_names(s: str, delimiter: str = ', ') -> str:
    return delimiter.join(map(print_char_unicode_name, s))


class ScriptRepair:
    """For automatic repair of look-alike characters in the wrong script."""
    def __init__(self, wb: WildebeestAnalysis):
        self.wb = wb
        cyr2lat = {'Ѕ': 'S', 'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M', 'Н': 'H', 'О': 'O', 'Р': 'P',
                   'С': 'C', 'Т': 'T', 'Х': 'X', 'Ԛ': 'Q', 'Ԝ': 'W', 'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p',
                   'с': 'c', 'у': 'y', 'х': 'x', 'ѕ': 's', 'і': 'i', 'ј': 'j', 'ԛ': 'q', 'ԝ': 'w'}
        grk2lat = {'Α': 'A', 'Β': 'B', 'Ε': 'E', 'Ζ': 'Z', 'Η': 'H', 'Ι': 'I', 'Κ': 'K', 'Μ': 'M', 'Ν': 'N',
                   'Ο': 'O', 'Ρ': 'P', 'Τ': 'T', 'Υ': 'Y', 'Χ': 'X',
                   'α': 'a', 'γ': 'y', 'η': 'n', 'κ': 'k', 'ν': 'v', 'ο': 'o', 'ρ': 'p', 'υ': 'u', 'χ': 'x',
                   'ε': 'ɛ'}
        misc2lat = {'ɑ': 'a',   # LATIN SMALL LETTER ALPHA
                    'ɡ': 'g'}   # LATIN SMALL LETTER SCRIPT G
        # ?? ipa2lat = {'ɑ': 'a', 'ɡ': 'g'}
        self.char_map = defaultdict(dict)
        for key, value in cyr2lat.items():
            self.char_map["LATIN"][key] = value
            self.char_map["CYRILLIC"][value] = key
        for key, value in grk2lat.items():
            self.char_map["LATIN"][key] = value
            self.char_map["GREEK"][value] = key
        for key, value in misc2lat.items():
            self.char_map["LATIN"][key] = value
        # to be added: greek <-> cyrillic, Persian <-> Arabic (k, y), ...

    def repair_string(self, s: str, target_script: str) -> Tuple[str, str]:
        n_letters = 0
        n_repaired_letters = 0
        n_irreparable_letters = 0
        result = ""
        char_map = self.char_map.get(target_script)
        for char in s:
            n_letters += 1
            repaired_char = char_map.get(char) if char_map else None
            if repaired_char is not None:
                result += repaired_char
                n_repaired_letters += 1
            else:
                result += char
                unicode_script = self.wb.unicode_util.char_unicode_script(char)
                if unicode_script != target_script:
                    n_irreparable_letters += 1
        if n_repaired_letters and n_irreparable_letters:
            category = "partially repaired"
        elif n_repaired_letters:
            category = "repaired"
        elif n_irreparable_letters:
            category = "unrepaired"
        else:
            category = "no repair needed"
        return result, category


class DynJsonResults:
    """
    Manages list of GreekRoom results, especially sorting the output.
    """
    def __init__(self):
        self.n_issues = 0
        self.snt_id_set = set()
        self.results_by_snt_id = defaultdict(list)
        self.results_by_check_id = defaultdict(list)
        self.results_by_check_id_and_snt_id = defaultdict(list)
        self.check_id_snt_ids = defaultdict(list)

    def add(self, result: dict, snt_id: str | None = None) -> None:
        if snt_id is None:
            snt_id = result.get('sntId')
        self.results_by_snt_id[snt_id].append(result)
        check_id = result.get('check', "GreekRoom:unspecified")   # "unspecified" should never actually occur
        self.results_by_check_id[check_id].append(result)
        self.results_by_check_id_and_snt_id[(check_id, snt_id)].append(result)
        if snt_id not in self.check_id_snt_ids[check_id]:
            self.check_id_snt_ids[check_id].append(snt_id)
        self.snt_id_set.add(snt_id)
        self.n_issues += 1

    def listify(self, snt_id_list: List[str]) -> List[dict]:
        result = []
        # sort by sentence ID, position, length of substring (longer first), severity (higher first)
        for snt_id in snt_id_list:
            for result_for_snt_id in sorted(self.results_by_snt_id[snt_id],
                                            key=lambda d: (d.get('span', [[0]])[0][0],
                                                           -len(d.get('orig', 0)),
                                                           -d.get('severity', 0))):
                result.append(result_for_snt_id)
        return result


class WildebeestAnalysis:
    """
    Object stores raw and aggregate information of a Wildebeest test checking analysis.
    Final results are stored in self.analysis
    """
    def __init__(self, args, verbose: Optional[bool] = False):
        self.wildebeest = Wildebeest()
        self.lang_code = args.lc
        self.lang_name = None
        self.corpus_id = None
        self.corpus_name = None
        self.verbose = verbose
        self.filename = None
        self.character_count = defaultdict(int)
        self.token_count = defaultdict(int)
        self.token_examples = defaultdict(list)  # values are lists of lists(token, line number)
        # noinspection SpellCheckingInspection
        self.pattern_characters_of_interest = ("-‐‑−‒–—―=\u00AD+~*_.,:꞉;!¡¿?/⁄§'‚‘’ʼˊˋˈˀˆˉ`«»‹›„“”\"()\\[\\]<>⌞⌟"
                                               "、。．،٫٬，；？（）।॥።፣፤፥፦፧՜՝՞։؛؟۔@#&%$€£¥₪¢¤₨₹µ‌¦|‍")
        self.pattern_characters_of_interest += 'ـ'  # Arabic tatweel
        self.pattern_characters_of_interest_re = regex.compile(rf'[{self.pattern_characters_of_interest}]')
        self.pattern_count = defaultdict(int)
        self.pattern_examples = defaultdict(list)
        self.pattern_lines = defaultdict(set)
        self.max_pattern_lines = args.max_pattern_lines
        self.max_bad_pattern_lines = args.max_bad_pattern_lines
        self.max_n_token_examples = args.max_examples
        self.max_n_viz_examples = 5 if args.max_examples_viz is None else args.max_examples_viz
        self.max_n_cases = args.max_cases
        self.script_count_letter = defaultdict(int)
        self.script_count_number = defaultdict(int)
        self.script_count_other = defaultdict(int)
        self.script_examples_letter = defaultdict(str)
        self.script_examples_number = defaultdict(str)
        self.script_examples_other = defaultdict(str)
        self.mixed_script_count_letter = defaultdict(int)
        self.mixed_script_instances_letter = defaultdict(list)
        self.script_lines = defaultdict(set)
        self.max_script_lines = args.max_script_lines
        self.non_canonical_lines = defaultdict(set)
        self.max_non_canonical_lines = args.max_non_canonical_lines
        self.char_conflict_lines = defaultdict(set)
        self.max_char_conflict_lines = args.max_char_conflict_lines
        self.notable_token_lines = defaultdict(set)
        self.max_notable_token_lines = args.max_notable_token_lines
        self.open_quot_refresh_class_prev_unexpected_sub_result_values = []  # used in stderr duplicate reduction
        self.analysis = {'n_lines': 0,
                         'n_empty_lines': 0,
                         'n_characters': 0,
                         'letter-script': defaultdict(dict),
                         'number-script': defaultdict(dict),
                         'other-script': defaultdict(dict),
                         'non-canonical': defaultdict(dict),
                         'rival-char-sets': defaultdict(list),
                         'notable-token': defaultdict(dict),
                         'notable-token-meta': defaultdict(dict),
                         'pattern': defaultdict(dict),
                         'block': defaultdict(dict)}
        self.pattern_class_counts = defaultdict(lambda: [0, 0, 0])
        # Key: (pattern_character_of_interest, pattern)
        # Value: List of counts for '-'/''/'+'
        self.script_direction = script_direction.ScriptDirection(lang_code=self.lang_code or args.input)
        self.log_message_counts = defaultdict(int)
        self.abbreviations = defaultdict(set)         # key: lang_code, e.g. "fas"
        self.active_abbreviations = defaultdict(set)  # key: lang_code, e.g. "fas"
        self.in_word_punct_patterns = set()
        self.norm_char_dict = {}
        self.dyn_json = {}
        self.dyn_json_results = DynJsonResults()
        self.dyn_check_selectors: List[str] | None = None
        self.dyn_skipped_checks: List[str] | None = []
        self.snt_list = []
        self.ref_id_list = []
        self.snt_index_to_ref_id = defaultdict(str)
        self.ref_id_to_snt_index = defaultdict(int)
        self.ref_id_to_text = {}  # HHERE possibly use self.text_corpus.snt_id_to_snt
        self.script_repair = None
        self.char_script_dict = {}
        self.auto_correct_threshold: float | None = None
        self.n_snt = 0
        self.wb_corpus = {}
        self.unicode_util = corpus.UnicodeUtilities()
        self.text_corpus = None

        # The following blocks will be printed out in order as specified below:
        for block in ['LOW_SURROGATES', 'REPLACEMENT', 'C0_CONTROL', 'C1_CONTROL', 'ZERO_WIDTH', 'DIRECTIONAL',
                      'VARIATION_SELECTORS', 'VARIATION_SELECTORS_SUPPLEMENT',
                      'ASCII_PUNCTUATION', 'GENERAL_PUNCTUATION', 'ARABIC_PUNCTUATION', 'ETHIOPIC_PUNCTUATION',
                      'CHINESE_PUNCTUATION', 'DEVANAGARI_PUNCTUATION', 'ARMENIAN_PUNCTUATION',
                      'CURRENCY_SYMBOLS', 'SPACE',
                      'ASCII_DIGIT', 'FULLWIDTH_DIGIT', 'VULGAR_FRACTION', 'ROMAN_NUMERAL',
                      'ARABIC_INDIC_DIGIT', 'EXTENDED_ARABIC_INDIC_DIGIT',
                      'NUMBER_FORMS', 'SUPERSCRIPT_DIGIT', 'SUBSCRIPT_DIGIT', 'SUPERSCRIPTS_AND_SUBSCRIPTS',
                      'COMBINING_DIACRITICAL_MARKS',
                      'BASIC_LATIN', 'LATIN_EXTENDED_LETTER', 'LATIN_EXTENDED_A', 'LATIN_EXTENDED_B',
                      'LATIN_EXTENDED_C', 'LATIN_EXTENDED_D', 'LATIN_ALPHABETIC_PRESENTATION_FORMS',
                      'LATIN', 'IPA_EXTENSIONS', 'LETTERLIKE_SYMBOLS', 'FULLWIDTH_LATIN',
                      'CYRILLIC',
                      'ARMENIAN', 'ARMENIAN_ALPHABETIC_PRESENTATION_FORMS',
                      'GREEK', 'GREEK_EXTENDED',
                      'ARABIC', 'ARABIC_PRESENTATION_FORMS_A', 'ARABIC_PRESENTATION_FORMS_B',
                      'HEBREW', 'HEBREW_ALPHABETIC_PRESENTATION_FORMS', 'HEBREW_PRESENTATION_FORMS']:
            self.analysis['block'][block] = {}

        self.token_to_pattern_dict = defaultdict(list)
        self.corpus_w_rtf_delimiter_adjustments = None
        self.lrm = '‎'  # left-to-right directional mark
        # structure of dictionaries for unmatched, nesting_l, nesting_r:
        #   key: char (paired_delimiter)
        #   value: list[(line_number, char_pos)]
        # structure of dictionaries for open_lefts, refresher_lefts:
        #   key: char (paired_delimiter)
        #   value: list[(line_number, char_pos, n_chars_in_line)]   # helps gauge approximate pos. in translation
        # structure of dictionary for open_first_lefts:
        #   key: char (paired_delimiter)
        #   value: (line_number, char_pos) | None
        # structure of dictionary for cross_snt_spans:
        #   key: char (paired_delimiter)
        #   value: list[((open_line_number, open_char_pos, open_line_len),
        #                (close_line_number, close_char_pos, close_line_len))]
        self.punct_analysis = {'stack': [],       # list of characters
                               'stack_plus': [],  # list of (character, (line_number, char_pos, line_len), snt_id)
                               'open_lefts': defaultdict(list),
                               'matching_punct': '()[]{}«»‹›（）［］【】「」『』《》〈〉⌞⌟',
                               'matching_punct_supplement_low_quote': '„”‚’',    # German, Danish
                               'matching_punct_supplement_low_quote2': '„“‚‘',   # Ukrainian, Belarusian
                               'matching_punct_supplement_low_quote3': '„“‘’',   # Russian
                               'matching_punct_supplement_default': '“”‘’',
                               'refreshable_punct': '“‘«‹',             # Refreshable across sentences
                               'unmatched': {},
                               'open-quote-legitimate-refresher': {},
                               'open-quote-legitimate-span': {},
                               'open-quote-refresher': {},
                               'nesting_l': {},
                               'nesting_r': {},
                               'open_first_lefts': {},    # Start of long quote
                               'last_close_right': {},
                               'refresher_lefts': defaultdict(list),   # Refresher open quote (often at start of para)
                               'last_legit_open_refresher_line_number': {},
                               'last_illegit_open_refresher_line_number': {},
                               'line_lengths': {},
                               'cross_snt_spans': defaultdict(list),
                               'triple_nesting': defaultdict(list),
                               'ref_translations': []}
        self.paired_delimiter_state = {}
        if self.lang_code in ('dan', 'deu'):
            self.punct_analysis['matching_punct'] += self.punct_analysis['matching_punct_supplement_low_quote']
        elif self.lang_code in ('ukr', 'bel'):
            self.punct_analysis['matching_punct'] += self.punct_analysis['matching_punct_supplement_low_quote2']
        elif self.lang_code in ('rus',):
            self.punct_analysis['matching_punct'] += self.punct_analysis['matching_punct_supplement_low_quote3']
        else:
            self.punct_analysis['matching_punct'] += self.punct_analysis['matching_punct_supplement_default']
        i, punct_list = 0, self.punct_analysis.get('matching_punct')
        # sys.stderr.write(f'''MP lc: {self.lang_code} m_punct: {punct_list}\n''')
        self.init_paired_delimiter_state(punct_list)
        while i < len(punct_list):
            punct_l, punct_r = punct_list[i], punct_list[i+1]
            self.punct_analysis[('lr', punct_l)] = punct_r
            self.punct_analysis[('rl', punct_r)] = punct_l
            self.punct_analysis['unmatched'][punct_l] = []
            self.punct_analysis['unmatched'][punct_r] = []
            self.punct_analysis['open-quote-legitimate-refresher'][punct_l] = []
            self.punct_analysis['open-quote-legitimate-refresher'][punct_r] = []
            self.punct_analysis['open-quote-legitimate-span'][punct_l] = []
            self.punct_analysis['open-quote-legitimate-span'][punct_r] = []
            self.punct_analysis['open-quote-refresher'][punct_l] = []
            self.punct_analysis['open-quote-refresher'][punct_r] = []
            self.punct_analysis['nesting_l'][punct_l] = []
            self.punct_analysis['nesting_r'][punct_r] = []
            i += 2
        for punct_l in self.punct_analysis['refreshable_punct']:
            self.punct_analysis['open_first_lefts'][punct_l] = None
        self.load_tok_resource()

    def load_tok_resource(self):
        wb_src_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        tok_data_dir = wb_src_dir / "data-tok"
        for lang_code in (self.lang_code,):
            filename = tok_data_dir / f"tok-resource-{lang_code}.txt"
            if os.path.isfile(filename):
                with open(filename) as f:
                    for line in f:
                        if abbreviation := slot_value_in_double_colon_del_list(line, 'abbrev'):
                            self.abbreviations[lang_code].add(abbreviation)
                n_abbreviations = len(self.abbreviations[lang_code])
                sys.stderr.write(f"load_tok_resource {self.lang_code} {filename} {n_abbreviations} entries\n")

    def remove_empty_dicts(self):
        """Remove any empty dictionaries, which might have been created as empty to proscribe output order."""
        for key1 in ('block', 'notable-token'):
            blocks = self.analysis[key1].keys()
            blocks_with_dicts_to_be_deleted = []
            for block in blocks:
                block_dict = self.analysis[key1].get(block)
                if isinstance(block_dict, dict) and len(block_dict) == 0:
                    blocks_with_dicts_to_be_deleted.append(block)
            for block in blocks_with_dicts_to_be_deleted:
                del self.analysis[key1][block]

    def pattern_to_regex(self, pattern: str):
        pattern = regex.sub(r'[]', '', pattern)
        active_abbreviations_regex = None
        if 'Abbreviation.' in pattern:
            reg_active_abbreviations = map(regex.escape, self.active_abbreviations[self.lang_code])
            active_abbreviations_regex = f"(?:{'|'.join(reg_active_abbreviations)})"
            pattern = regex.sub(r'Abbreviation\\?.', '', pattern)
        s = regex.escape(pattern)
        s = regex.sub('Xml', r'&(?:[aA][mM][pP];)*(?:#[xX][0-9A-Fa-f]{1,6}|#\\d{1,7}|[A-Za-z]{1,6});', s)
        s = regex.sub('WordWLM', r'[\\u064E-\\u0650]\\pL\\pM*(?:[\\u200C\\u200D]?\\pL\\pM*)*', s)
        if self.lang_code in ('enb', 'tuy'):
            s = regex.sub('Word', r"(?::|\\*|\\*:|/|\\*/)?\\pL+(?:'\\pL+)*'?", s)
        else:
            s = regex.sub('Word', r'\\pL\\pM*(?:[\\u200C\\u200D]?\\pL\\pM*)*', s)
        s = regex.sub('NumberWP', r'(?<!\\pN)\\pN{1,3}(?:\\.\\pN{3})+(?!\\.?\\pN)', s)
        s = regex.sub('NumberWC', r'(?<!\\pN)\\pN{1,3}(?:,\\pN{3})+(?!,?\\pN)', s)
        s = regex.sub('Number', r'\\pN+', s)
        s = regex.sub('Modifiers', r'\\pM{2,}', s)
        s = regex.sub('Modifier', r'\\pM', s)
        if active_abbreviations_regex:
            s = s.replace('', active_abbreviations_regex)
        return s

    def token_to_patterns(self, token: str) -> List[str]:
        # check for cached result
        if result := self.token_to_pattern_dict[token]:
            return result
        pattern = token
        pattern = regex.sub(r'[]', '', pattern)
        if self.lang_code:
            if m := regex.match(r'(.*?)((?:(?:\pL\pM*)+\.){2,})(.*)$', pattern):
                pre, abbreviation, post = m.group(1, 2, 3)
                if abbreviation in self.abbreviations[self.lang_code]:
                    self.active_abbreviations[self.lang_code].add(abbreviation)
                    pattern = pre + '' + post
        pattern = regex.sub('\u0640', '', pattern)  # tatweel
        pattern = regex.sub(r'&(?:[aA][mM][pP];)*(?:#[xX][0-9A-Fa-f]{1,6}|#\d{1,7}|[A-Za-z]{1,6});',
                            r'&;', pattern, regex.IGNORECASE)  # problem with IGNORECASE
        pattern = regex.sub(r'(?:%(?:25)*[0-9A-Fa-f]{2}){2,}',
                            r'%', pattern, regex.IGNORECASE)  # problem with IGNORECASE
        pattern = regex.sub(r'(?<!\pL\pM*|\pM)[\u064E-\u0650]\pL\pM*(?:[\u200C\u200D]?\pL\pM*)*', '', pattern)
        if self.lang_code in ('enb', 'tuy'):
            pattern = regex.sub(r"(?::|\*|\*:|/|\*/)?\pL+(?:'\pL+)*'?", 'Word', pattern)
        else:
            pattern = regex.sub(r"\pL\pM*(?:[\u00AD\u200C\u200Dʼ']?\pL\pM*)*", 'Word', pattern)
        pattern = regex.sub(r'\pM{2,}', 'Modifiers', pattern)
        pattern = regex.sub(r'\pM', 'Modifier', pattern)
        pattern = regex.sub(r'(?<!\pN)\pN{1,3}(\.\pN{3})+(?!\.?\pN)', 'NumberWP', pattern)
        pattern = regex.sub(r'(?<!\pN)\pN{1,3}(,\pN{3})+(?!,?\pN)', 'NumberWC', pattern)
        pattern = regex.sub(r'\pN+', 'Number', pattern)
        pattern = regex.sub(r'', 'Abbreviation.', pattern)
        pattern = regex.sub(r'', 'WordWLM', pattern)
        pattern = regex.sub(r'', 'Xml', pattern)
        pattern = regex.sub(r'', '\u0640', pattern)
        # if "\u00AD" in token:
        #     sys.stderr.write(f"  SH:{token} P:{pattern}\n")
        pattern1 = pattern
        pattern2 = regex.sub(r'(?:Word)+\u0640+(?:Word)+', 'Word', pattern)
        result = [pattern1]
        if pattern2 != pattern1:
            result.append(pattern2)
        for in_word_punct in "ʼ'\u00AD":
            # MODIFIER LETTER APOSTROPHE e.g. as in "donʼt"
            # regular apostrophe
            # soft hyphen
            if in_word_punct in token:
                if (in_word_punct == "'") and not regex.match(r"[^']*\pL\pM*(?:'\pL\pM*)+[^']*$", token):
                    continue
                if ((in_word_punct == "\u00AD")
                        and not regex.match(r"[^\u00AD]*\pL\pM*(?:\u00AD\pL\pM*)+[^\u00AD]*$", token)):
                    continue
                pattern3 = regex.sub(r'[]', '', token)
                pattern3 = pattern3.replace(in_word_punct, '')
                pattern3 = regex.sub(r'\pL\pM*(?:[\u200C\u200D]?\pL\pM*)*', 'Word', pattern3)
                pattern3 = pattern3.replace('', in_word_punct)
                pattern3 = regex.sub(r'[.,;:!?})]+’[ ”»⌟]*$', '', pattern3)
                pattern3 = pattern3.lstrip("‘“«⌞([{ ")
                pattern3 = pattern3.rstrip(".,;:?!)]}”»⌟ ")
                result.append(pattern3)
                self.in_word_punct_patterns.add(pattern3)
        # Cache result, but avoid clogging run-time memory space
        if len(self.token_to_pattern_dict) < 1000000:
            self.token_to_pattern_dict[token] = result
        return result

    def snt_id(self, line_number: int, default: str = None) -> str:
        default_snt_id = default if default else str(line_number)
        return self.snt_index_to_ref_id.get(line_number, default_snt_id) if self.snt_index_to_ref_id else default_snt_id

    def punct_analysis_in_line(self, line: str, line_number: int):
        refreshable_punctuations = self.punct_analysis['refreshable_punct']
        punct_stack = self.punct_analysis['stack']
        last_non_space_char_position = len(line.rstrip()) - 1
        verbose = False  # (25420 <= line_number <= 25427)  # or (1730 < line_number < 1760)
        for char_pos, char in enumerate(line):
            # found left delimiter
            # Example for triple: https://www.biblegateway.com/passage/?search=Matthew+22%3A43-45&version=NIV
            # Example for "quad": https://www.biblegateway.com/passage/?search=ISA+7%3A3-9&version=ESV
            full_pos = (line_number, char_pos)
            full_pos2 = (line_number, char_pos, last_non_space_char_position)  # len helps gauge position in translation
            if right_char := self.punct_analysis.get(('lr', char), None):
                triple_nesting = ((len(punct_stack) >= 2)
                                  and (punct_stack[-2] == char)
                                  and (punct_stack[-1] in refreshable_punctuations)
                                  and (punct_stack[-2] in refreshable_punctuations)
                                  and (punct_stack[-1] != punct_stack[-2]))
                # if verbose and triple_nesting: print("PRELIM", line_number, char_pos, punct_stack)
                quad_nesting1 = (triple_nesting and line[char_pos+1:].lstrip().startswith(punct_stack[-1]))
                quad_nesting2 = ((len(punct_stack) >= 2)
                                 and (punct_stack[-1] == char)
                                 and (punct_stack[-1] in refreshable_punctuations)
                                 and (punct_stack[-2] in refreshable_punctuations)
                                 and (punct_stack[-1] != punct_stack[-2])
                                 and line[:char_pos].rstrip().endswith(punct_stack[-2]))
                if quad_nesting1 or quad_nesting2:
                    triple_nesting = False
                # if verbose and triple_nesting: print("TRIPLE", line_number, char_pos, punct_stack)
                # if verbose and quad_nesting1: print("QUAD1", line_number, char_pos, punct_stack)
                # if verbose and quad_nesting2: print("QUAD2", line_number, char_pos, punct_stack)
                # if triple_nesting and verbose:
                #     print("TRIPLE", char, full_pos2, self.snt_id(line_number), punct_stack)
                if ((char in self.punct_analysis['refreshable_punct'])
                        and self.punct_analysis['open_lefts'][char]
                        and (not triple_nesting)):
                    refresher_category = (self.open_quotation_refresher_classification(char, full_pos, line)
                                          or 'unmatched')
                    if refresher_category == 'unmatched':
                        open_first_pos = self.punct_analysis['open_first_lefts'][char]
                        if (open_first_pos and (open_first_pos[0] < line_number)
                                and (open_first_pos not in self.punct_analysis[refresher_category][char])):
                            self.punct_analysis[refresher_category][char].append(open_first_pos)
                    self.punct_analysis[refresher_category][char].append(full_pos2)
                    if verbose:
                        print('REFRESHER', line_number, char_pos, char, self.snt_id(line_number), refresher_category)
                else:
                    if verbose and triple_nesting:
                        print("TRIPLE2", char, full_pos2, self.snt_id(line_number), self.punct_analysis['stack_plus'])
                    if not self.punct_analysis['nesting_r'][right_char]:
                        self.punct_analysis['nesting_l'][char].append(full_pos)
                    self.punct_analysis['nesting_r'][right_char] = []
                    punct_stack.append(char)
                    self.punct_analysis['stack_plus'].append((char, full_pos2, self.snt_id(full_pos[0])))
                    self.punct_analysis['open_lefts'][char].append(full_pos)
                if char in self.punct_analysis['refreshable_punct']:
                    if self.punct_analysis['open_first_lefts'][char]:
                        self.punct_analysis['refresher_lefts'][char].append(full_pos2)
                    else:
                        self.punct_analysis['open_first_lefts'][char] = full_pos2
                self.punct_analysis['line_lengths'][line_number] = last_non_space_char_position
                self.punct_analysis['last_close_right'][right_char] = None
            # found right delimiter
            elif left_char := self.punct_analysis.get(('rl', char), None):
                self.punct_analysis['nesting_r'][char].append(full_pos)
                if verbose:
                    print('CLOSE', line_number, left_char, char, self.snt_id(line_number),
                          self.punct_analysis['stack_plus'], self.punct_analysis['open_lefts'][left_char])
                triple_nesting = ((len(punct_stack) >= 3)
                                  and (punct_stack[-1] == punct_stack[-3])
                                  and (punct_stack[-1] in refreshable_punctuations)
                                  and (punct_stack[-2] in refreshable_punctuations)
                                  and (punct_stack[-1] != punct_stack[-2]))
                popped_pos = None
                if punct_stack and (punct_stack[-1] == left_char):
                    popped_pos = self.punct_analysis['stack_plus'][-1][1]
                    del punct_stack[-1]
                    del self.punct_analysis['stack_plus'][-1]
                    if self.punct_analysis['open_lefts'][left_char]:
                        del self.punct_analysis['open_lefts'][left_char][-1]
                else:
                    last_close_right_pos = self.punct_analysis['last_close_right'].get(char)
                    if (last_close_right_pos and (last_close_right_pos[0] < line_number)
                            and (last_close_right_pos not in self.punct_analysis['unmatched'][char])):
                        self.punct_analysis['unmatched'][char].append(last_close_right_pos)
                        if verbose: print("FLAG", char, 'unmatched', last_close_right_pos)
                    self.punct_analysis['unmatched'][char].append(full_pos)
                    if verbose: print("FLAG", char, 'unmatched', full_pos)
                if triple_nesting and popped_pos:
                    span_info = self.span_info_with_ids(popped_pos, full_pos2)
                    self.punct_analysis['triple_nesting'][left_char].append(span_info)
                    if verbose:
                        print("**TRIPLE-SPAN", left_char, char, "TRIPLE" if triple_nesting else "", span_info)
                if popped_pos and not triple_nesting and self.punct_analysis['open_lefts'][left_char]:
                    # todo: possibly elaborate
                    log_message = f"-----CLEAN?? {left_char}, {char}, {self.punct_analysis['open_lefts'][left_char]}"
                    if log_message not in self.log_message_counts:
                        pass
                        # sys.stderr.write(log_message + "\n")
                    self.log_message_counts[log_message] += 1
                if ((left_char in self.punct_analysis['open_first_lefts'])
                        and (not (triple_nesting and popped_pos))
                        and (open_pos := self.punct_analysis['open_first_lefts'][left_char])):
                    if open_pos[0] < line_number:
                        span_info = self.span_info_with_ids(open_pos, full_pos2)
                        self.punct_analysis['cross_snt_spans'][left_char].append(span_info)
                        if verbose:
                            print("**CROSS", left_char, char, "TRIPLE" if triple_nesting else "", span_info)
                    self.punct_analysis['open_first_lefts'][left_char] = None
                if (left_char in self.punct_analysis['refreshable_punct']) and not triple_nesting:
                    self.punct_analysis['open_lefts'][left_char] = []
                self.punct_analysis['last_close_right'][char] = full_pos2
                self.punct_analysis['last_legit_open_refresher_line_number'][left_char] = None
                self.punct_analysis['last_illegit_open_refresher_line_number'][left_char] = None
                if verbose:
                    print('CLOSE2', line_number, left_char, char, self.snt_id(line_number),
                          self.punct_analysis['stack_plus'], self.punct_analysis['open_lefts'][left_char])
        if self.snt_index_to_ref_id:
            snt_id = self.snt_id(line_number)
            next_snt_id = self.snt_id(line_number+1, 'None')
            snt_id_tokens1 = snt_id.split()
            snt_id_tokens2 = next_snt_id.split()
            if (len(snt_id_tokens1) >= 2) and (len(snt_id_tokens2) >= 2) and (snt_id_tokens1[0] != snt_id_tokens2[0]):
                # if punct_stack: print('CLEAN at EOC?', snt_id, next_snt_id, self.punct_analysis['stack_plus'])
                while punct_stack:
                    popped_pos = self.punct_analysis['stack_plus'][-1][1]
                    popped_char = self.punct_analysis['stack_plus'][-1][0]
                    # print('  CLEAN at EOC unmatched', self.punct_analysis['stack_plus'][-1])
                    self.punct_analysis['unmatched'][popped_char].append(popped_pos)
                    del punct_stack[-1]
                    del self.punct_analysis['stack_plus'][-1]
                    if self.punct_analysis['open_lefts'][popped_char]:
                        del self.punct_analysis['open_lefts'][popped_char][-1]

    def span_info_with_ids(self, pos1: tuple, pos2: tuple) -> tuple:
        snt_id1 = self.snt_id(pos1[0])
        snt_id2 = self.snt_id(pos2[0])
        snt_id_span = self.combine_vref_start_end(snt_id1, snt_id2) if snt_id1 and snt_id2 else None
        return (pos1, pos2, snt_id_span) if snt_id_span else (pos1, pos2)

    @staticmethod
    def combine_vref_start_end(snt_id1: str, snt_id2: str) -> str:
        if snt_id1 == snt_id2:
            return snt_id1
        # Bible format
        m1 = regex.search(r'([A-Z1-3][A-Z][A-Z])\s+(\d+):(\d+)$', snt_id1)
        m2 = regex.search(r'([A-Z1-3][A-Z][A-Z])\s+(\d+):(\d+)$', snt_id2)
        if m1 and m2:
            if m1.group(1) == m2.group(1):
                if m1.group(2) == m2.group(2):
                    return f'{m1.group(1)} {m1.group(2)}:{m1.group(3)}-{m2.group(3)}'
                else:
                    return f'{m1.group(1)} {m1.group(2)}:{m1.group(3)}-{m2.group(2)}:{m2.group(3)}'
        return f"{snt_id1}-{snt_id2}"

    def punct_analysis_at_end(self, verbose: bool = False):
        # to be called after last line to mark any open punctuation as unmatched
        if verbose and self.punct_analysis['stack_plus']:
            print("FINAL-PUNCT-STACK", self.punct_analysis['stack_plus'], len(self.punct_analysis['stack_plus']))
        ref_translation_names = [x.get('translation') for x in self.punct_analysis['ref_translations']
                                 if x.get('translation')]
        ref_translation_name_clause = ", ".join(ref_translation_names) if ref_translation_names else ''
        for punct_analysis_key, analysis_report_title, ass_class, ass_descr \
                in [('unmatched',
                     'Paired delimiters:    unmatched',
                     '-', f"Note regarding open quotation marks (e.g. {self.punct_analysis['refreshable_punct']})"
                          f"&xxxnbsp;&#xA;\n"
                          f" — Crossing delimiter pairs are flagged (e.g. “…[…”…]) &#xA;\n"
                          f"&xnbsp;whereas nested delimiter pairs are ok (e.g. “…[…]…”).\n"
                          f" — Suspicious repeated unclosed open quotation marks (e.g. «…«…») are flagged "
                          f"in both places.\n"
                          f" — ‘Suspicious’ means that they are not supported by any reference translation: "
                          f"{ref_translation_name_clause}\n"
                          f"Similarly, repeated close quotation marks (e.g. »…») are flagged in both places."),
                    ('open-quote-refresher',
                     'Paired delimiters:   refreshing open quotation mark (maybe ok)',
                     'o',
                     f'Refreshing open quotation mark does NOT fall inside a long quotation '
                     f'in a reference translation: {ref_translation_name_clause}\n'),
                    ('open-quote-legitimate-refresher',
                     'Paired delimiters: refreshing open quotation mark matched in reference (most likely ok)',
                     '+',
                     f'Refreshing open quotation mark has corresponding refreshing open quotation mark in '
                     f'a reference translation: {ref_translation_name_clause}'),
                    ('open-quote-legitimate-span',
                     'Paired delimiters:  refreshing open quotation mark inside reference quotation span (probably ok)',
                     '+',
                     f'Refreshing open quotation mark falls inside a long quotation '
                     f'in a reference translation: {ref_translation_name_clause}\n(Probably ok.)')]:
            for char in self.punct_analysis['matching_punct']:
                if example_pos_list := self.punct_analysis[punct_analysis_key][char]:
                    code_point = ord(char)
                    unicode_id = 'U+%04X' % code_point
                    unicode_name = self.unicode_util.unicode_name(char)
                    self.analysis['notable-token-meta'][analysis_report_title]['ass-class'] = ass_class
                    self.analysis['notable-token-meta'][analysis_report_title]['ass-descr'] = ass_descr
                    self.analysis['notable-token'][analysis_report_title][char] \
                        = {'token': char,
                           'id': unicode_id,
                           'name': unicode_name,
                           'count': len(example_pos_list),
                           'ex': list(map(lambda x: [char, x[0], x[1]], example_pos_list))}

    def refreshing_quote_candidate(self, char: str, open_line_number: int, open_char_pos: int, line: str) -> bool:
        """checks whether character (e.g. '“') is open quote at position 0 (or nearby) and has match on stack"""
        if self.punct_analysis.get(('lr', char)) \
                and self.punct_analysis['stack_plus'] \
                and (char == self.punct_analysis['stack_plus'][-1][0]):
            if open_char_pos == 0:
                return True
            else:
                char2 = line[0:open_char_pos].rstrip()  # Example: char==‘  char2==“
                if self.punct_analysis.get(('lr', char2)) \
                        and (len(self.punct_analysis['stack_plus']) >= 2) \
                        and (char2 == self.punct_analysis['stack_plus'][-2][0]):
                    return True
        else:
            last_illegit_orln = self.punct_analysis['last_illegit_open_refresher_line_number'][char]
            if last_illegit_orln and (open_line_number-last_illegit_orln <= 10):
                return True
        return False
        
    def open_quotation_refresher_classification(self, char: str, open_pos, line: str) -> str | None:
        result = None
        result_priority = 0
        result_value_order = (None, 'unmatched', 'open-quote-legitimate-span', 'open-quote-legitimate-refresher')
        ref_translations: list[dict] = self.punct_analysis['ref_translations']
        if ref_translations:
            for ref_translation in ref_translations:
                sub_result = self.open_quotation_refresher_classification_rec(char, open_pos, ref_translation)
                try:
                    sub_priority = result_value_order.index(sub_result)
                    if sub_priority > result_priority:
                        result = sub_result
                        result_priority = sub_priority
                except ValueError:
                    if not (sub_result in self.open_quot_refresh_class_prev_unexpected_sub_result_values):
                        sys.stderr.write(f'Warning from open_quotation_refresher_classification: '
                                         f'unexpected sub-result {sub_result}\n')
                        self.open_quot_refresh_class_prev_unexpected_sub_result_values.append(sub_result)
        if result in (None, 'unmatched'):
            open_line_number, open_char_pos = open_pos
            if self.refreshing_quote_candidate(char, open_line_number, open_char_pos, line):
                top_of_stack = self.punct_analysis['stack_plus'][-1]
                tos_full_pos = top_of_stack[1]
                tos_line_number = tos_full_pos[0]
                last_legit_orln = self.punct_analysis['last_legit_open_refresher_line_number'][char]
                last_illegit_orln = self.punct_analysis['last_illegit_open_refresher_line_number'][char]
                if (((open_line_number-tos_line_number <= 20)
                            or ((last_legit_orln is not None)
                                and (open_line_number-last_legit_orln <= 15)))
                        or ((last_illegit_orln is not None) and (open_line_number-last_illegit_orln <= 10))):
                    if tos_full_pos not in self.punct_analysis['open-quote-refresher'][char]:
                        self.punct_analysis['open-quote-refresher'][char].append(tos_full_pos)
                    self.punct_analysis['last_legit_open_refresher_line_number'][char] = open_line_number
                    return 'open-quote-refresher'
            if open_char_pos == 0:
                self.punct_analysis['last_illegit_open_refresher_line_number'][char] = open_line_number

        return result

    def open_quotation_refresher_classification_rec(self, char: str, open_pos: list[int, int], ref_translation: dict)\
            -> str | None:
        refresher_dict: dict | None = ref_translation.get('refresher-dict', None)
        cross_snt_span_dict: dict | None = ref_translation.get('cross-snt-span-dict', None)
        char_count: dict | None = ref_translation.get('char_count', None)
        ref_line_length_dict: dict | None = ref_translation.get('line-length', None)
        line_length_dict = self.punct_analysis['line_lengths']
        map_char = {'«': '“', '‹': '‘'}
        char2 = char
        if char_count and (char_count[char] == 0) and (char_count[map_char.get(char)]):
            char2 = map_char.get(char)
        open_line_number, open_char_pos = open_pos
        last_line_pos = line_length_dict.get(open_line_number)
        ref_last_line_pos = ref_line_length_dict.get(open_line_number)
        if refresher_dict:
            for refresher_elem in refresher_dict.get((char2, open_line_number), []):
                if self.similar_relative_line_position(open_char_pos, last_line_pos,
                                                       refresher_elem[0], ref_last_line_pos):
                    return 'open-quote-legitimate-refresher'
                # if 23300 <= open_line_number <= 26000:
                #     print('REFRESHER2', char, char2, open_pos, refresher_elem, last_line_pos, ref_last_line_pos)
        if cross_snt_span_dict:
            for cross_snt_span in cross_snt_span_dict.get((char2, open_line_number), []):
                cross_snt_start, cross_snt_end, *optional_args = cross_snt_span
                cross_snt_start_line_number, cross_snt_start_char_pos, cross_snt_start_len = cross_snt_start
                cross_snt_end_line_number, cross_snt_end_char_pos, cross_snt_end_len = cross_snt_end
                if cross_snt_start_line_number <= open_line_number <= cross_snt_end_line_number:
                    # if 26700 <= open_line_number <= 26800:
                    #     print('REFRESHER3', char, char2, open_pos, cross_snt_span, last_line_pos, ref_last_line_pos)
                    if ((open_line_number == cross_snt_start_line_number)
                            and (self.relative_line_pos_diff(open_char_pos, last_line_pos,
                                                             cross_snt_start_char_pos, cross_snt_start_len) <= 0.1)):
                        continue
                    elif ((open_line_number == cross_snt_end_line_number)
                            and (self.relative_line_pos_diff(open_char_pos, last_line_pos,
                                                             cross_snt_end_char_pos, cross_snt_end_len) >= -0.1)):
                        continue
                    else:
                        return 'open-quote-legitimate-span'
        return 'unmatched'

    @staticmethod
    def relative_line_pos_diff(a_pos, a_last_pos, b_pos, b_last_pos) -> float:
        if a_last_pos or b_last_pos:
            a_rel_pos = a_pos/(a_last_pos or b_last_pos)
            b_rel_pos = b_pos/(b_last_pos or a_last_pos)
            return a_rel_pos - b_rel_pos
        return 0

    def similar_relative_line_position(self, a_pos, a_last_pos, b_pos, b_last_pos, max_rel_diff: float = 0.25) -> bool:
        return abs(self.relative_line_pos_diff(a_pos, a_last_pos, b_pos, b_last_pos)) <= max_rel_diff

    @staticmethod
    def rearrange_selected_tokens(tokens: list[str]) -> list[str]:
        """Make single tokens out of “ ‘ and of ’ ”"""
        # tokens = regex.findall(r'((?:[“‘][ \u202F][“‘])?\S+(?![ \u202F][’”])(?:[’”](?:[ \u202F][’”])*)?)', line)
        i = 1
        while i < len(tokens):
            if ((tokens[i-1].endswith('“') and tokens[i].startswith('‘'))
                    or (tokens[i-1].endswith('‘') and tokens[i].startswith('“'))
                    or (tokens[i-1].endswith('’') and tokens[i] == '”')
                    or (tokens[i-1].endswith('”') and tokens[i] == '’')):
                tokens = tokens[:i-1] + [' '.join(tokens[i-1:i+1])] + tokens[i+1:]
            else:
                i += 1
        return tokens

    def collect_counts_and_examples_in_line(self, line: str, line_number: int):
        max_token_examples = max(self.max_n_token_examples, self.max_n_viz_examples)
        self.analysis['n_characters'] += len(line)
        line = line.strip()
        if line == '<range>':
            return
        # line_id = str(line_number)
        char_position = 0
        for char in line:
            self.character_count[char] += 1
            char_position += 1
            if len(self.token_examples[char]) < max_token_examples:
                # if char.isalpha():
                if regex.search(r'(?:\pL|\pM|�)', char):
                    token_examples = regex.findall(rf'((?:\pL\pM*|�)*\pM*{char}\pM*(?:\pL\pM*|�)*)', line)
                elif char.isnumeric():
                    token_examples = regex.findall(rf'(\pN*{char}\pN*)', line)
                else:
                    token_examples = [char]
                for token_example in token_examples:
                    token_tuple = [token_example, line_number]
                    if len(self.token_examples[char]) < max_token_examples \
                            and (token_tuple not in self.token_examples[char]):
                        self.token_examples[char].append(token_tuple)
            # uc_block = None
            if not (uc_script := self.unicode_util.char_to_script_dict[char]):
                uc_block = self.unicode_util.unicode_block(char)
                uc_script = self.unicode_util.unicode_script(uc_block, char)
            if len(self.script_lines[uc_script]) < self.max_script_lines:
                self.script_lines[uc_script].add(line_number)
        words = regex.findall(r'((?:\pL\pM*){2,})', line, re.IGNORECASE)
        complex_chars = regex.findall(r'(\pL\pM+)', line, re.IGNORECASE)
        xml_esc_dec_tokens = regex.findall(r'(&#\d{1,7};)', line, regex.IGNORECASE)
        xml_esc_hex_tokens = regex.findall(r'(&#X[0-9A-F]{1,6};)', line, regex.IGNORECASE)
        xml_esc_abc_tokens = regex.findall(r'(&(?:[a-z]{1,6});)', line, regex.IGNORECASE)
        xml_esc_nst_tokens = regex.findall(r'&(?:amp;)+(?:#X[0-9A-F]{1,6}|#\d{1,7}|[a-z]{1,6});',
                                           line, regex.IGNORECASE)
        for token in words + complex_chars + xml_esc_dec_tokens + xml_esc_hex_tokens \
                     + xml_esc_abc_tokens + xml_esc_nst_tokens:
            self.token_count[token] += 1
            token_tuple = [token, line_number]
            if (len(self.token_examples[token]) < max_token_examples) \
                    and (token_tuple not in self.token_examples[token]):
                self.token_examples[token].append(token_tuple)
        # tokens = regex.findall(r'((?:[“‘][ \u202F][“‘])?\S+(?![ \u202F][’”])(?:[’”](?:[ \u202F][’”])*)?)', line)
        tokens = regex.findall(r'(\S+)', line)
        tokens = self.rearrange_selected_tokens(tokens)
        # if line_number in (59, 507, 3848, 3848, 509): print("TOK", line_number, tokens, line)
        for token in tokens:
            if self.pattern_characters_of_interest_re.search(token) \
                    or regex.search(r'(?<!\pL\pM*)\pM', token):
                token_tuple = [token, line_number]
                for pattern in self.token_to_patterns(token):
                    self.pattern_count[pattern] += 1
                    if len(self.pattern_examples[pattern]) < max_token_examples \
                            and (token_tuple not in self.pattern_examples[pattern]):
                        self.pattern_examples[pattern].append(token_tuple)
                    if len(self.pattern_lines[pattern]) < self.max_bad_pattern_lines:
                        self.pattern_lines[pattern].add(line_number)

    def collect_counts_and_examples_in_text(self, line: str, stats: dict):
        try:
            line_w_rtf_delimiter_adjustments = None
            stats['line_number'] += 1
            line_number = stats['line_number']
            if not regex.match(r'\S', line):
                stats['n_empty_lines'] += 1
            self.collect_counts_and_examples_in_line(line, line_number)
            ref_id = self.snt_id(line_number)
            self.wb_corpus[ref_id] = line
            line_rtl = script_direction.ScriptDirection.string_is_right_to_left(line)
            if line_rtl:
                if not self.corpus_w_rtf_delimiter_adjustments.get(ref_id):
                    if self.script_direction.text_contains_switchable_chars(line):
                        line_w_rtf_delimiter_adjustments \
                            = self.script_direction.switch_delimiters_for_rtl_scripts(line)
                        self.corpus_w_rtf_delimiter_adjustments[ref_id] = line_w_rtf_delimiter_adjustments
            self.punct_analysis_in_line(line_w_rtf_delimiter_adjustments or line, line_number)
        # Exception for safety only. Should not occur.
        except UnicodeError as error:
            sys.stderr.write(f"*** Unicode error: {error}\n")
            sys.stderr.write(f"***    Input aborted. The input is not in valid UTF-8 encoding.\n")
        self.punct_analysis_at_end()

    def collect_counts_and_examples_in_file(self, args, total_bytes=None, progress_bar=True) -> None:
        """Collect counts and examples for characters, tokens, and patterns occurring in file."""
        stats = {'line_number': 0, 'n_empty_lines': 0}
        prefix = 'Checking'
        input_file: IO = args.input
        if input_file:
            with (tqdm(input_file, total=total_bytes, disable=not progress_bar, unit='b', unit_scale=True,
                      dynamic_ncols=True, desc=prefix) as data_bar):
                for line in data_bar:
                    self.collect_counts_and_examples_in_text(line, stats)
        elif self.snt_list:
            # sys.stderr.write(f' ARGS: {args}\n\n')
            # sys.stderr.write(f'** Sentences: {args.snt_list}\nRefIdDict: {args.snt_index_to_ref_id}\n')
            for line in self.snt_list:
                self.collect_counts_and_examples_in_text(line, stats)
        elif args.strings:
            for line in args.strings:
                self.collect_counts_and_examples_in_text(line, stats)
        self.analysis['n_lines'] = stats['line_number']
        self.analysis['n_empty_lines'] = stats['n_empty_lines']
        for char in self.character_count.keys():
            self.script_direction.add_stats(char, self.character_count[char])
        if self.script_direction.is_right_to_left():
            sys.stderr.write(self.script_direction.report(details=True))

    def assess_pattern(self, pattern_character_of_interest: str, pattern: str) -> Tuple[str, str]:
        ass_class, ass_descr = '', ''
        if len(pattern_character_of_interest) == 1:
            ass_char_name = self.unicode_util.unicode_name(pattern_character_of_interest) or pattern_character_of_interest
        else:
            ass_char_name = pattern_character_of_interest
        a = "an" if regex.match('AEIOU', ass_char_name, re.IGNORECASE) else "a"
        # count = self.pattern_count[pattern]
        if (pattern_character_of_interest in '।॥.።։!?,፣;፤:፦،؛؟۔)]>”’›»⌟') and pattern.startswith(pattern_character_of_interest):
            ass_class = '-'
            ass_descr = (f'Token starts with {a} {ass_char_name} {pattern_character_of_interest}\n'
                         f'Please check whether there is any spurious space before it.')
        if (pattern_character_of_interest in '([<“‘‹«⌞‚„') and pattern.endswith(pattern_character_of_interest):
            ass_class = '-'
            ass_descr = (f'Token ends in {a} {ass_char_name} {pattern_character_of_interest}\n'
                         f'Please check whether there is any spurious space after it.')
        if regex.search(r'''Word:?[„“”]?[.።։।॥!?,፣;፤:፦،؛؟۔«»'][„“”]?Word''', pattern):
            ass_class = '-'
            ass_descr = (f'Word token includes {a} {ass_char_name} {pattern_character_of_interest}\n'
                         f'Please check for any missing space.')
        if regex.search(r'[:፦;፤,፣،.።।։]{2}', pattern) and not ('..' in pattern):
            ass_class = '-'
            ass_descr = (f'Word token includes {a} {ass_char_name} {pattern_character_of_interest}\n'
                         f'with multiple competing end-of-clause marks.')
        if regex.search(r'[`−]', pattern):
            ass_class = '-'
            ass_descr = (f'Word token includes {a} {ass_char_name} {pattern_character_of_interest}\n'
                         f'which is an unusual character.')
        # ?? etc.
        if (pattern_character_of_interest in '-?!,？՞') and ((pattern_character_of_interest * 2) in pattern):
                ass_class = '-'
                ass_descr = f'Word token includes a double {ass_char_name} {pattern_character_of_interest}\n'
        for bad_substring in ["//", "\u00AD\u00AD", "<SOFT HYPHEN><SOFT HYPHEN>"]:
            if bad_substring in pattern:
                ass_class = '-'
                ass_descr = (f"Word token includes suspicious sub-sequence "
                             f"'{self.repl_invisible_chars_in_pattern(bad_substring)}'\n")
        if regex.match(
                #  \u202f is narrow space
                '([\\(\\[])?([“‘‚„«‹⌞]|“‘|“[ \u202f]*‘|‘[ \u202f]“)?(Word(?:ʼWord)*(-Word(?:ʼWord)*)*ʼ?|WordWLM|Number|NumberWP|NumberWC)([।॥.።։,፣;፤!?:፦،؛؟۔])?((?:”[ \u202f]’[ \u202f]”|”[ \u202f]’|’[.።?! \u202f]”|’”|[”’»›⌟"])[.።]?)?([\\)\\]])?$',
                pattern):
            ass_class = '+'
        elif regex.match(
                '([\\(\\[])?([“‘‚„«‹⌞]|“‘|“[ \u202f]*‘|‘[ \u202f]“)?(Word(?:ʼWord)*(-Word(?:ʼWord)*)*ʼ?|WordWLM|Number|NumberWP|NumberWC)([।॥.።։,፣;፤!?:፦،؛؟۔])?[\\)\\]]((?:”[ \u202f]’[ \u202f]”|”[ \u202f]’|’[.።?! \u202f]”|’”|[”’»›⌟"]))?$',
                pattern):
            ass_class = '+'
        elif regex.match(
                '([\\(\\[])?([“‘‚„«‹⌞]|“‘|“[ \u202f]*‘|‘[ \u202f]“)?(Word(?:ʼWord)*(-Word(?:ʼWord)*)*ʼ?|WordWLM|Number|NumberWP|NumberWC)[\\)\\]]([।॥.።։,፣;፤!?:፦،؛؟۔])?((?:”[ \u202f]’[ \u202f]”|”[ \u202f]’|’[.።?! \u202f]”|’”|[”’»›⌟"]))?$',
                pattern):
            ass_class = '+'
        elif regex.match('([\\(\\[])?([“‘‚„«‹⌞]|“‘|“[ \u202f]‘|“[ \u202f]‘[ \u202f]“|‘[ \u202f]“)?(Word(?:ʼWord)*(-Word(?:ʼWord)*)*ʼ?|WordWLM|Number|NumberWP|NumberWC)([”’»›⌟"])?([\\)\\]])?([।॥.።։,፣;፤!?:፦،؛؟۔])?$',
                       pattern):
            ass_class = '+'
        elif regex.search(r'^Word(ʼWord)+$', pattern):  # ʼ (U+02BC MODIFIER LETTER APOSTROPHE)
            ass_class = '+'
        elif regex.search(r'^(?:(?:“|‘)?Word(?:”|’)?(?:）|\))?(?:？|՞|，|՝|：|、|；|．|）))+(?:(?:“|‘|（)?Word(?:？|՞|，|՝|：|:|、|；|．|）)*(?:”|’|’”)?)?$',
                          pattern):
            ass_class = '+'
        elif regex.search(r'^（?“?Word(?:？|՞|．)?(?:’|”|’”)?）?$', pattern):
            ass_class = '+'
        elif regex.search(r'^Word（“?Word？?(?:’|”)?）?$', pattern):
            ass_class = '+'
        if (pattern_character_of_interest == "ORPHAN MODIFIER") and ("Modifier" in pattern):
            if "Word" not in pattern:
                ass_class = '-'
                ass_descr = 'Word token includes a Modifier without any Letter'
            elif not regex.search('Modifiers?Word', pattern) or regex.search('WordModifier', pattern):
                ass_class = '-'
                ass_descr = 'Modifier in pattern disconnected from any Letter'
        # if ass_class.startswith('-'): sys.stderr.write(f"{ass_class} {pattern} ({count}) {ass_descr}\n")
        return ass_class, ass_descr

    def update_pattern_class_counts(self, pattern_character_of_interest: str, pattern: Optional[str],
                                    assess_class: str, pattern_count: int) -> None:
        updated_counts = self.pattern_class_counts[(pattern_character_of_interest, pattern)]
        if assess_class == '-':
            updated_counts[0] += pattern_count
        elif assess_class == '+':
            updated_counts[2] += pattern_count
        else:
            updated_counts[1] += pattern_count
        self.pattern_class_counts[(pattern_character_of_interest, pattern)] = updated_counts

    def norm_char(self, token: str, dyn: bool) -> Tuple[str, dict|None]:
        if cached_result := self.norm_char_dict.get(token):
            return cached_result
        elif regex.match(r'\pL\pM*$', token):
            norm0 = token
            norm1 = self.wildebeest.normalize_arabic_pres_form_characters(norm0)
            norm2 = self.wildebeest.normalize_ligatures(norm1)
            norm3 = self.wildebeest.normalize_hangul(norm2)
            norm4 = self.wildebeest.repair_combining_modifiers_with_nukta(norm3)
            norm5 = self.wildebeest.apply_combining_modifiers_compose(norm4)
            norm6 = self.wildebeest.apply_combining_modifiers_decompose(norm5)
            norm = norm6
            if norm != token:
                norm_count = self.token_count[norm] or self.character_count[norm]
                changes = []
                if norm1 != norm0:
                    changes.append('arabic-presentation')
                if norm2 != norm1:
                    changes.append('ligature')
                if norm3 != norm2:
                    changes.append('hangul')
                if norm4 != norm3:
                    changes.append('nukta-position' if dyn else 'moved-nukta')
                if norm5 != norm4:
                    changes.append('compose')
                if norm6 != norm5:
                    changes.append('decompose')
                unicode_form = self.unicode_util.unicode_form(token)
                unicode_form2 = self.unicode_util.unicode_form(norm)
                if sorted(token) == sorted(norm):
                    form_clause = ''
                    form_clause2 = 'REORDERED, '
                elif sorted(set(token)) == sorted(set(norm)):
                    form_clause = ''
                    form_clause2 = 'REMOVED-DUPLICATE-DIACRITIC, '
                elif changes == ['arabic-presentation']:
                    form_clause = ''
                    form_clause2 = 'NORM-ARABIC-PRES-FORM, '
                elif changes == ['moved-nukta', 'compose']:
                    form_clause = ''
                    form_clause2 = 'REORDERED-AND-COMPOSED, '
                elif unicode_form == 'NFD' and unicode_form2 == 'NFC' and changes == ['compose']:
                    form_clause = f'{unicode_form}, '
                    form_clause2 = f'{unicode_form2}, '
                elif unicode_form is None and unicode_form2 in ['NFC', 'NFD'] \
                        and (changes == ['compose'] or changes == ['decompose']):
                    form_clause = ''
                    form_clause2 = f'{unicode_form2}, '
                else:
                    form_clause = f'{unicode_form}, '
                    form_clause2 = f'{unicode_form2}, '
                d = {"form-clause": form_clause, "form-clause2": form_clause2, "norm_count": norm_count, "changes": changes}
                return norm, d
        return token, None

    def dyn_selector_match(self, check: str) -> bool:
        if self.dyn_check_selectors is None:
            # sys.stderr.write(f'Smatch disabled {check}\n')
            return True
        else:
            for check_selector in self.dyn_check_selectors:
                if (check_selector == check) \
                        or check_selector.startswith(check + ':') \
                        or check.startswith(check_selector + ':'):
                    # sys.stderr.write(f'Smatch {check} {check_selector}\n')
                    return True
            self.dyn_skipped_checks.append(check)
            # sys.stderr.write(f'Smatch failed {check} {self.dyn_check_selectors}\n')
        return False

    @staticmethod
    def simple_span(offset: int, s: str) -> List[List[int]]:
        return [[offset, offset+len(s)]]

    def dyn_encoding_check(self) -> None:
        for snt, snt_id in zip(self.snt_list, self.ref_id_list):
            self.wildebeest.set_lv(snt)
            # sys.stderr.write(f' CC {snt_id} {snt}\n')
            matches, start_positions, inter_matches = general_util.findall3(r'\pL\pM*', snt)
            for match_s, start_pos in zip(matches, start_positions):
                norm, norm_d = self.norm_char(match_s, True)
                if _verbose := (len(match_s) > 111):
                    sys.stderr.write(f'    D {norm} {norm_d}\n')
                if (norm != match_s) and norm_d:
                    # end_pos = start_pos + len(match_s)
                    changes = norm_d.get("changes")
                    change_s = ", ".join(changes)
                    span = self.simple_span(start_pos, match_s)
                    self.dyn_json_results.add({"sntId": snt_id, "span": span, "orig": match_s,
                                               "check": f"GreekRoom:Wildebeest:encoding:{change_s}",
                                               "severity": 0.9,
                                               "actionMenu": [{"substitute": norm, "confidence": 0.99}]})
                    # sys.stderr.write(f"NORM-CHAR in {snt_id} {start_pos}-{end_pos}: {match_s}->{norm} ({changes})\n")

    def dyn_script_check(self) -> None:
        unicode_scripts_letter = sorted(self.script_count_letter, key=self.script_count_letter.get, reverse=True)
        # unicode_scripts_number = sorted(self.script_count_number, key=self.script_count_number.get, reverse=True)
        # _unicode_scripts_other = sorted(self.script_count_other, key=self.script_count_other.get, reverse=True)
        dominant_script_letter = unicode_scripts_letter[0] if unicode_scripts_letter else None
        # _dominant_script_number = unicode_scripts_number[0] if unicode_scripts_number else None
        if len(unicode_scripts_letter) <= 1:
            check_for_minority_letter_scripts = False
        elif self.script_count_letter[unicode_scripts_letter[0]] < 0.5 * self.script_count_letter[unicode_scripts_letter[1]]:
            check_for_minority_letter_scripts = False
        elif self.lang_code == "jap" and set(unicode_scripts_letter).issubset({"KANJI", "HIRAGANA", "KATAKANA"}):
            check_for_minority_letter_scripts = False
        else:
            check_for_minority_letter_scripts = True
        if check_for_minority_letter_scripts:
            # for unicode_script in unicode_scripts_letter:
            for snt, snt_id in zip(self.snt_list, self.ref_id_list):
                tokens, start_positions, inter_tokens = general_util.findall3(r'(?:\pL\pM*)+', snt)
                for token, start_pos in zip(tokens, start_positions):
                    letters, start_positions2, inter_letters = general_util.findall3(r'\pL\pM*', token)
                    token_script_counts = defaultdict(int)
                    non_dominant_letters = []
                    positions3 = []
                    for letter, start_pos2 in zip(letters, start_positions2):
                        core_letter = letter[0]
                        # _unicode_cat = self.unicode_util.unicode_category(core_letter)
                        unicode_script = self.unicode_util.char_unicode_script(core_letter)
                        token_script_counts[unicode_script] += 1
                        if unicode_script != dominant_script_letter:
                            non_dominant_letters.append(core_letter)
                            positions3.append((start_pos+start_pos2, start_pos+start_pos2+len(letter)))
                    token_scripts = list(token_script_counts.keys())
                    n_base_scripts = len(token_script_counts)
                    for script in ('SPACING_MODIFIER_LETTERS', 'MODIFIER_TONE_LETTERS'):
                        if token_script_counts.get(script):
                            n_base_scripts -= 1
                    if len(token_script_counts) == 1:
                        if not token_script_counts[dominant_script_letter]:
                            check_type = f"GreekRoom:Wildebeest:script:token-in-minority-script"
                            span = self.simple_span(start_pos, token)
                            dyn_feedback_item = {"sntId": snt_id, "span": span, "orig": token,
                                                 "check": check_type, "minorityScript": token_scripts[0],
                                                 "severity": 0.7}
                            repaired_token, repair_outcome = self.script_repair.repair_string(token,
                                                                                              dominant_script_letter)
                            if repair_outcome == "repaired":
                                action_menu = [{"substitute": repaired_token, "confidence": 0.6}]
                                dyn_feedback_item["actionMenu"] = action_menu
                            # sys.stderr.write(f'Script1: {json.dumps(dyn_feedback_item)}\n')
                            self.dyn_json_results.add(dyn_feedback_item)
                    elif n_base_scripts >= 2:
                        check_type = f"GreekRoom:Wildebeest:script:token-with-multiple-scripts"
                        span = self.simple_span(start_pos, token)
                        dyn_feedback_item = {"sntId": snt_id, "span": span, "orig": token,
                                             "check": check_type, "severity": 0.9,
                                             "scripts": token_scripts,
                                             "minorityScriptLetters": non_dominant_letters,
                                             "minorityScriptSpan": positions3}
                        repaired_token, repair_outcome = self.script_repair.repair_string(token, dominant_script_letter)
                        if repair_outcome == "repaired":
                            action_menu = [{"substitute": repaired_token, "confidence": 0.9}]
                            dyn_feedback_item["actionMenu"] = action_menu
                        # sys.stderr.write(f'Script2: {json.dumps(dyn_feedback_item)}\n')
                        self.dyn_json_results.add(dyn_feedback_item)

    def init_paired_delimiter_state(self, punct_list) -> None:
        self.paired_delimiter_state['all-open-delimiters'] = set()
        self.paired_delimiter_state['all-close-delimiters'] = set()
        self.paired_delimiter_state['close-to-open-delimiters'] = defaultdict(list)  # key: close-delimiter
        self.paired_delimiter_state['open-to-close-delimiters'] = defaultdict(list)  # key: open-delimiter
        self.paired_delimiter_state['unpaired-open-delimiters'] = defaultdict(list)  # key: open-del v:list(sntId, pos)
        self.paired_delimiter_state['repeating-open-delimiters'] = defaultdict(list)  # key: open-del v:list(sntId, pos)
        self.paired_delimiter_state['paired-delimiters'] = defaultdict(list)  # key open-or-clise-del v:list(open,close)
        for i in range(int(len(punct_list) / 2)):
            open_delimiter = punct_list[2 * i]
            close_delimiter = punct_list[2 * i + 1]
            self.paired_delimiter_state['all-open-delimiters'].add(open_delimiter)
            self.paired_delimiter_state['all-close-delimiters'].add(close_delimiter)
            self.paired_delimiter_state['close-to-open-delimiters'][close_delimiter].append(open_delimiter)
            self.paired_delimiter_state['open-to-close-delimiters'][open_delimiter].append(close_delimiter)
        # sys.stderr.write(f' PDS: {self.paired_delimiter_state}\n')

    def is_repeating_open_delimiter(self, char: str, pos4: Tuple) -> bool:
        line_number, pos, snt_id, c = pos4
        unpaired_open_delimiters = self.paired_delimiter_state['unpaired-open-delimiters'][char]
        repeating_open_delimiters = self.paired_delimiter_state['repeating-open-delimiters'][char]
        if unpaired_open_delimiters or repeating_open_delimiters:
            last_unpaired_line_number = unpaired_open_delimiters[-1][0] if unpaired_open_delimiters else -999
            last_repeating_line_number = repeating_open_delimiters[-1][0] if repeating_open_delimiters else -999
            last_open_pos4 = unpaired_open_delimiters[-1] if last_unpaired_line_number > last_repeating_line_number \
                else repeating_open_delimiters[-1]
            verbose = False
            # verbose = snt_id.startswith('ACT 7:')
            last_line_number, last_pos, last_snt_id, last_c = last_open_pos4
            if paired_delimiters := self.paired_delimiter_state['paired-delimiters'][char]:
                paired_open_pos4, paired_close_pos4 = paired_delimiters[-1]
                if paired_open_pos4[0] > last_line_number:
                    if verbose: sys.stderr.write(
                        f"is_repeating_open_delimiter False1 {char} {pos4} {unpaired_open_delimiters} {repeating_open_delimiters}\n")
                    return False
            if (pos == 0) and (line_number - last_line_number <= 10):
                if verbose: sys.stderr.write(f"is_repeating_open_delimiter True {char} {pos4} {unpaired_open_delimiters} {repeating_open_delimiters}\n")
                return True
            if verbose: sys.stderr.write(f"is_repeating_open_delimiter False2 {char} {pos4} {unpaired_open_delimiters} {repeating_open_delimiters}\n")
        return False

    def dyn_paired_delimiter_check(self) -> None:
        # self.paired_delimiter_state['all-open-delimiters'].add(open_delimiter)
        # self.paired_delimiter_state['all-close-delimiters'].add(close_delimiter)
        # self.paired_delimiter_state['close-to-open-delimiters'][close_delimiter].append(open_delimiter)
        # self.paired_delimiter_state['unpaired-open-delimiters'] = defaultdict(list) # key: open-del v:list(sntId, pos)
        testing_verbose = False

        line_number = 0
        for snt, snt_id in zip(self.snt_list, self.ref_id_list):
            testing_verbose = False   # snt_id.startswith('ACT 7:')
            line_number += 1
            pos = 0
            for char in snt:
                pos4 = (line_number, pos, snt_id, char)
                if char in self.paired_delimiter_state['all-close-delimiters']:
                    # sys.stderr.write(f'close {char} {snt_id} {pos}\n')
                    open_delimiters = self.paired_delimiter_state['close-to-open-delimiters'][char]
                    most_recent_open_delimiter, most_recent_open_delimiter_pos = None, None
                    for open_delimiter in open_delimiters:
                        if positions := self.paired_delimiter_state['unpaired-open-delimiters'][open_delimiter]:
                            # sys.stderr.write(f'open_delimiters {open_delimiter} {positions}\n')
                            last_pos = positions[-1]
                            if (most_recent_open_delimiter_pos is None) \
                                    or (last_pos > most_recent_open_delimiter_pos):
                                most_recent_open_delimiter = open_delimiter
                                most_recent_open_delimiter_pos = last_pos
                    # sys.stderr.write(f"most_recent_open_delimiter {most_recent_open_delimiter} {self.paired_delimiter_state['unpaired-open-delimiters'][most_recent_open_delimiter]}\n")
                    if most_recent_open_delimiter:
                        open_pos4 = self.paired_delimiter_state['unpaired-open-delimiters'][most_recent_open_delimiter].pop()
                        open_char = open_pos4[3]
                        self.paired_delimiter_state['paired-delimiters'][char].append([open_pos4, pos4])
                        self.paired_delimiter_state['paired-delimiters'][open_char].append([open_pos4, pos4])
                        self.paired_delimiter_state['repeating-open-delimiters'][open_char] = []
                        if testing_verbose:
                            sys.stderr.write(f'''pair: {open_pos4} {pos4} {self.paired_delimiter_state['unpaired-open-delimiters'][most_recent_open_delimiter]}\n''')
                    else:
                        snt_id, pos = pos4[2], pos4[1]
                        close_delimiter = char
                        unicode_name = self.unicode_util.unicode_name(close_delimiter)
                        check_type = f"GreekRoom:Wildebeest:punctuation:unpaired-delimiter:close:{unicode_name.lower()}"
                        span = self.simple_span(pos, char)
                        dyn_feedback_item = {"sntId": snt_id, "span": span, "orig": close_delimiter,
                                             "check": check_type, "severity": 0.5}
                        self.dyn_json_results.add(dyn_feedback_item)
                elif char in self.paired_delimiter_state['all-open-delimiters']:
                    if testing_verbose:
                        sys.stderr.write(f'open {char} {snt_id} {pos}\n')
                    if self.is_repeating_open_delimiter(char, pos4):
                        self.paired_delimiter_state['repeating-open-delimiters'][char].append(pos4)
                    else:
                        # if any long distance open of same type, flag them and reset
                        if open_pos4_list := self.paired_delimiter_state['unpaired-open-delimiters'][char]:
                            distance = line_number - open_pos4_list[-1][0]
                            if distance > 50:
                                for prev_open_pos4 in open_pos4_list:
                                    (prev_line_number, prev_pos, prev_snt_id, prev_char) = prev_open_pos4
                                    open_delimiter = prev_char
                                    unicode_name = self.unicode_util.unicode_name(open_delimiter)
                                    check_type = f"GreekRoom:Wildebeest:punctuation:unpaired-delimiter:open:{unicode_name.lower()}"
                                    prev_span = self.simple_span(prev_pos, prev_char)
                                    dyn_feedback_item = {"sntId": prev_snt_id, "span": prev_span, "orig": open_delimiter,
                                                         "check": check_type, "severity": 0.5}
                                    self.dyn_json_results.add(dyn_feedback_item)
                                self.paired_delimiter_state['unpaired-open-delimiters'][char] = []
                            # elif distance > 10:
                            #    sys.stderr.write(f"Somewhat long distance re-open: {pos4} ** {open_pos4_list}\n")
                        self.paired_delimiter_state['unpaired-open-delimiters'][char].append(pos4)
                pos += 1
        if testing_verbose:
            sys.stderr.write(f"unpaired-open {self.paired_delimiter_state['unpaired-open-delimiters']}\n")
        for open_delimiter in self.paired_delimiter_state['unpaired-open-delimiters'].keys():
            for pos4 in self.paired_delimiter_state['unpaired-open-delimiters'][open_delimiter]:
                snt_id, pos = pos4[2], pos4[1]
                unicode_name = self.unicode_util.unicode_name(open_delimiter)
                check_type = f"GreekRoom:Wildebeest:punctuation:unpaired-delimiter:open:{unicode_name.lower()}"
                span = self.simple_span(pos, open_delimiter)
                dyn_feedback_item = {"sntId": snt_id, "span": span, "orig": open_delimiter,
                                     "check": check_type, "severity": 0.5}
                self.dyn_json_results.add(dyn_feedback_item)

    def dyn_punctuation_cluster_check(self) -> None:
        for snt, snt_id in zip(self.snt_list, self.ref_id_list):
            matches, start_positions, inter_matches = general_util.findall3(r'[।॥.።։,፣;፤!?:፦،؛؟۔]{2,}', snt)
            for i in range(len(matches)):
                punct_chars = matches[i]
                # don't flag "..."
                if regex.match(r'\.+$', punct_chars):
                    continue
                else:
                    punct_start_pos = start_positions[i]
                    check_type = "GreekRoom:Wildebeest:punctuation:cluster"
                    span = self.simple_span(punct_start_pos, punct_chars)
                    dyn_feedback_item = {"sntId": snt_id, "span": span, "orig": punct_chars,
                                         "check": check_type, "severity": 0.7}
                    if len(punct_chars) == 2:
                        if punct_chars[0] == punct_chars[1]:
                            action_menu = [{"substitute": punct_chars[1], "confidence": 0.8}]
                        else:
                            action_menu = [{"substitute": punct_chars[1], "confidence": 0.4},
                                           {"substitute": punct_chars[0], "confidence": 0.4}]
                        dyn_feedback_item["actionMenu"] = action_menu
                    self.dyn_json_results.add(dyn_feedback_item)

    def dyn_punctuation_unexpected_check(self) -> None:   # suspicious
        for snt, snt_id in zip(self.snt_list, self.ref_id_list):
            matches, start_positions, inter_matches = general_util.findall3(r'[+*<=>|`_]', snt)
            for i in range(len(matches)):
                punct_char = matches[i]
                punct_start_pos = start_positions[i]
                left_context = inter_matches[i]
                # right_context = inter_matches[i+1]
                check_type = "GreekRoom:Wildebeest:punctuation:unexpected"
                span = self.simple_span(punct_start_pos, punct_char)
                dyn_feedback_item = {"sntId": snt_id, "span": span, "orig": punct_char,
                                     "check": check_type, "severity": 0.7}
                if punct_char == "|":
                    m = regex.search(r'(\pL)(\pM*)$', left_context)
                    if self.unicode_util.char_unicode_script(m.group(1)) in ("DEVANAGARI", ):
                        action_menu = [{"substitute": "।", "confidence": 0.6}]
                        dyn_feedback_item["actionMenu"] = action_menu
                        dyn_feedback_item["check"] = "GreekRoom:Wildebeest:punctuation:repair:vertical line:danda"
                # sys.stderr.write(f'Script1: {json.dumps(dyn_feedback_item)}\n')
                self.dyn_json_results.add(dyn_feedback_item)

    def dyn_suspicious_char_check(self) -> None:
        for snt, snt_id in zip(self.snt_list, self.ref_id_list):
            for offset in range(len(snt)):
                char = snt[offset]
                if char in self.unicode_util.suspicious_characters:
                    check_type = "GreekRoom:Wildebeest:character:suspicious"
                    action_menu = None
                    block_name = self.unicode_util.char_to_block_dict.get(char)
                    if block_name in ('C1_CONTROL', 'VARIATION_SELECTORS'):
                        check_type += ':' + block_name
                        action_menu = [{"substitute": '', "confidence": 0.9}]
                    span = self.simple_span(offset, char)
                    dyn_feedback_item = {"sntId": snt_id, "span": span, "orig": char,
                                         "check": check_type, "severity": 0.8}
                    if action_menu:
                        dyn_feedback_item["actionMenu"] = action_menu
                    self.dyn_json_results.add(dyn_feedback_item)

    def dyn_rare_char_check(self) -> None:
        total_char_count = self.text_corpus.total_char_count
        if total_char_count >= 50000:
            for snt, snt_id in zip(self.snt_list, self.ref_id_list):
                for offset in range(len(snt)):
                    char = snt[offset]
                    char_count = self.text_corpus.counts[char]
                    check_type = None
                    if char.isdigit():
                        unicode_block = self.unicode_util.unicode_block(char)
                        block_count = self.text_corpus.counts[unicode_block]
                        if block_count * 100000 <= total_char_count:
                            check_type = f"GreekRoom:Wildebeest:character:rare:{unicode_block}"
                    elif (char_count == 1) or (char_count * 1000000 <= total_char_count):
                        check_type = "GreekRoom:Wildebeest:character:rare"
                        unicode_name = self.unicode_util.unicode_name(char)
                        if "ZERO WIDTH" in unicode_name:
                            check_type += ':zero width'
                    if check_type:
                        span = self.simple_span(offset, char)
                        dyn_feedback_item = {"sntId": snt_id, "span": span, "orig": char,
                                             "check": check_type, "severity": 0.6}
                        self.dyn_json_results.add(dyn_feedback_item)

    def dyn_punctuation_space_check(self) -> None:
        for snt, snt_id in zip(self.snt_list, self.ref_id_list):
            matches, start_positions, inter_matches = general_util.findall3(r'[।॥.።։,፣;፤!?:፦،؛؟۔]', snt)
            for i in range(len(matches)):
                punct_char = matches[i]
                punct_start_pos = start_positions[i]
                left_context = inter_matches[i]
                right_context = inter_matches[i+1]
                m_left = regex.search(r'(\pL\pM*|\d)([’”»›」』⌟)\]}）］】》〉]*)(\s*)$', left_context)
                m_right = regex.match(r'(\s*)([‘“«‹「『⌞(\[{（［【《〈]*)(\pL|\d)', right_context)
                left_space = m_left.group(3) if m_left else None
                right_space = m_right.group(1) if m_right else None
                # exclude numerical items such as 3.14 or 20,000 or 3:16
                if m_left and m_right and (left_space == '') and (right_space == '') \
                    and m_left.group(1).isdigit() and m_right.group(3).isdigit():
                    continue
                if left_space or (right_space == ''):
                    punct_name = self.unicode_util.unicode_name(punct_char)
                    if left_space and (right_space == ''):
                        orig = left_space + punct_char
                        start_pos = punct_start_pos - len(left_space)
                        subst = punct_char + ' '
                        sub_type = 'reattach-to-left'
                    elif left_space:
                        orig = left_space + punct_char
                        start_pos = punct_start_pos - len(left_space)
                        subst = punct_char
                        sub_type = 'attach-to-left'
                    elif right_space == '':
                        orig = punct_char
                        start_pos = punct_start_pos
                        subst = punct_char + ' '
                        sub_type = 'detach-from-right'
                    else:
                        continue   # should not happen
                    check_type = f"GreekRoom:Wildebeest:punctuation:space:{punct_name.lower()}:{sub_type}"
                    span = self.simple_span(start_pos, orig)
                    dyn_feedback_item = {"sntId": snt_id, "span": span, "orig": orig,
                                         "check": check_type, "severity": 0.6,
                                         "actionMenu": [{"substitute": subst, "confidence": 0.9}]}
                    self.dyn_json_results.add(dyn_feedback_item)
                    # sys.stderr.write(f'Punct-space: {json.dumps(dyn_feedback_item)}\n')

    def dyn_checks(self):
        if self.dyn_selector_match("GreekRoom:Wildebeest"):
            if self.dyn_selector_match("GreekRoom:Wildebeest:encoding"):
                self.dyn_encoding_check()
            if self.dyn_selector_match("GreekRoom:Wildebeest:punctuation"):
                if self.dyn_selector_match("GreekRoom:Wildebeest:punctuation:space"):
                    self.dyn_punctuation_space_check()
                if self.dyn_selector_match("GreekRoom:Wildebeest:punctuation:unexpected"):
                    self.dyn_punctuation_unexpected_check()
                if self.dyn_selector_match("GreekRoom:Wildebeest:punctuation:cluster"):
                    self.dyn_punctuation_cluster_check()
                if self.dyn_selector_match("GreekRoom:Wildebeest:punctuation:unpaired-delimiter"):
                    self.dyn_paired_delimiter_check()
            if self.dyn_selector_match("GreekRoom:Wildebeest:character:suspicious"):
                self.dyn_suspicious_char_check()
            if self.dyn_selector_match("GreekRoom:Wildebeest:character:rare"):
                self.dyn_rare_char_check()
            if self.dyn_selector_match("GreekRoom:Wildebeest:script"):
                self.dyn_script_check()
        self.dyn_json["result"] = self.dyn_json_results.listify(self.ref_id_list)

    def aggregate(self) -> None:
        """Aggregate raw counts and examples into result Wildebeest analysis structure."""
        # Collect info on letter scripts (e.g. LATIN, CYRILLIC), number scripts (e.g. ASCII_DIGIT, ARABIC_INDIC_DIGIT),
        #    other scripts (e.g. ASCII_PUNCTUATION, GENERAL_PUNCTUATION, SPACE)
        for char in sorted(self.character_count):
            unicode_cat = self.unicode_util.unicode_category(char)
            unicode_block = self.unicode_util.unicode_block(char)
            unicode_script = self.unicode_util.unicode_script(unicode_block, char)
            unicode_script = self.unicode_util.modified_unicode_script(unicode_cat, unicode_script)
            if unicode_cat.startswith('L') \
                    and unicode_block not in ('SPACING_MODIFIER_LETTERS', 'MODIFIER_TONE_LETTERS'):
                if unicode_script:
                    count = self.character_count[char]
                    self.script_count_letter[unicode_script] += count
                    self.script_examples_letter[unicode_script] += char
            elif unicode_cat.startswith('N'):  # number
                if unicode_script:
                    count = self.character_count[char]
                    self.script_count_number[unicode_script] += count
                    self.script_examples_number[unicode_script] += char
            else:
                if unicode_script:
                    unicode_script = self.unicode_util.modified_unicode_script(unicode_cat, unicode_script)
                    count = self.character_count[char]
                    self.script_count_other[unicode_script] += count
                    self.script_examples_other[unicode_script] += char
        unicode_scripts_letter = sorted(self.script_count_letter, key=self.script_count_letter.get, reverse=True)
        unicode_scripts_number = sorted(self.script_count_number, key=self.script_count_number.get, reverse=True)
        unicode_scripts_other = sorted(self.script_count_other, key=self.script_count_other.get, reverse=True)
        dominant_script_letter = unicode_scripts_letter[0] if unicode_scripts_letter else None
        dominant_script_number = unicode_scripts_number[0] if unicode_scripts_number else None
        for unicode_script in unicode_scripts_letter:
            self.analysis['letter-script'][unicode_script] = {'count': self.script_count_letter[unicode_script]}
            script_examples_letter = self.script_examples_letter.get(unicode_script, "")
            if unicode_script != dominant_script_letter and len(script_examples_letter) <= 500:
                self.analysis['letter-script'][unicode_script]['ex'] = script_examples_letter
                self.analysis['letter-script'][unicode_script]['lines'] = sorted(self.script_lines[unicode_script])
        for unicode_script in unicode_scripts_number:
            self.analysis['number-script'][unicode_script] = {'count': self.script_count_number[unicode_script]}
            script_examples_number = self.script_examples_number.get(unicode_script, "")
            if ((len(script_examples_number) <= 80)
                    or (unicode_script != dominant_script_number and len(script_examples_number) <= 500)):
                self.analysis['number-script'][unicode_script]['ex'] = script_examples_number
                self.analysis['number-script'][unicode_script]['lines'] = sorted(self.script_lines[unicode_script])
        for unicode_script in unicode_scripts_other:
            self.analysis['other-script'][unicode_script] = {'count': self.script_count_other[unicode_script]}
            script_examples_other = self.script_examples_other.get(unicode_script, "")
            if len(script_examples_other) <= 80:
                self.analysis['other-script'][unicode_script]['ex'] = script_examples_other
                self.analysis['other-script'][unicode_script]['lines'] = sorted(self.script_lines[unicode_script])
        # Collect info of characters by block (e.g. BASIC_LATIN, ASCII_PUNCTUATION).
        for char in sorted(self.character_count):
            count = self.character_count[char]
            code_point = ord(char)
            unicode_id = 'U+%04X' % code_point
            unicode_name = self.unicode_util.unicode_name(char)
            unicode_block = self.unicode_util.unicode_block(char)
            # unicode_cat = self.unicode_util.unicode_category(char)
            # if (unicode_cat.startswith('L') and (dominant_script_letter == 'LATIN' and re.match('[a-zA-Z]$', char))) \
            #         or (dominant_script_letter == 'ETHIOPIC' and char in '፡።፣፤፥፦') \
            #         or (dominant_script_letter == 'ARABIC' and char in '۔،؛؟') \
            #         or (dominant_script_letter == 'HEBREW' and char in '־׀׃׆׳״') \
            #         or (dominant_script_letter in ['DEVANAGARI', 'BENGALI', 'GURMUKHI', 'ORIYA', 'TELUGU']
            #             and char in '।॥॰') \
            #         or (dominant_script_letter == 'TIBETAN' and char in '་༌།༎༼༽྅') \
            #         or (dominant_script_letter in ['CJK_UNIFIED_IDEOGRAPHS', 'HIRAGANA']
            #             and char in '·、。！（），：；？「」『』《》') \
            #         or (dominant_script_letter == 'GREEK' and char in ';·᾽΄᾿') \
            #         or (dominant_script_letter == 'MYANMAR' and char in '၊။၌၍၎၏႟') \
            #         or (dominant_script_letter == 'KHMER' and char in '។៕៖៚') \
            #         or (dominant_script_letter == 'SYRIAC' and char in '܀܁܅܈') \
            #         or (dominant_script_letter == 'UNIFIED_CANADIAN_ABORIGINAL_SYLLABICS' and char in '᙭᙮'):
            #     continue
            is_surrogate = code_point in range(0xDC80, 0xDD00)
            self.analysis['block'][unicode_block][char] \
                = {'char': '�' if is_surrogate else char,
                   'id': f'0x{(code_point - 0xDC00):X}' if is_surrogate else unicode_id,
                   'name': f'UTF-8 ENCODING ERROR (BYTE SURROGATE: {unicode_id})' if is_surrogate else unicode_name,
                   'count': count,
                   'ex': self.token_examples[char]}
        # noinspection PyBroadException
        try:
            _sorted_tokens = sorted(list(self.token_count.keys()) + list(self.character_count.keys()))
        except Exception:
            sys.stderr.write(f'sorted_tokens*** {self.token_count.keys()} :: {self.character_count.keys()}\n')
        for token in sorted(list(self.token_count.keys()) + list(self.character_count.keys())):
            # Check token for any non-canonical form (e.g. e + ́ instead of composed é; wrong order of modifiers)
            self.wildebeest.set_lv(token)
            count = self.token_count[token] or self.character_count[token]
            if regex.match(r'\pL\pM*$', token):
                norm, norm_d = self.norm_char(token, False)
                if (norm != token) and norm_d:
                    norm_count = norm_d.get("norm_count")
                    form_clause = norm_d.get("form-clause")
                    form_clause2 = norm_d.get("form-clause2")
                    changes = norm_d.get("changes")
                    self.analysis['non-canonical'][token] \
                        = {'orig': token, 'norm': norm, 'orig-count': count, 'norm-count': norm_count,
                           'orig-form': form_clause, 'norm-form': form_clause2, 'changes': changes}
            elif self.token_count[token] == 0:
                pass
            # Check for XML escape token
            elif token.startswith('&'):
                # noinspection SpellCheckingInspection
                if regex.match(r'&(?:amp|apos|gt|lt|nbsp|quot);$', token, regex.IGNORECASE):
                    self.analysis['notable-token']['XML ESCAPE TOKENS (BASIC)'][token] \
                        = {'token': token,
                           'count': self.token_count[token],
                           'ex': self.token_examples[token]}
                elif regex.match(r'&(?:[a-z]{1,6});$', token, regex.IGNORECASE):
                    self.analysis['notable-token']['XML ESCAPE TOKENS (EXTENDED)'][token] \
                        = {'token': token,
                           'count': self.token_count[token],
                           'ex': self.token_examples[token]}
                elif regex.match(r'&#\d{1,7};$', token, regex.IGNORECASE):
                    self.analysis['notable-token']['XML ESCAPE TOKENS (DECIMAL)'][token] \
                        = {'token': token,
                           'count': self.token_count[token],
                           'ex': self.token_examples[token]}
                elif regex.match(r'&#X[0-9A-F]{1,6};$', token, regex.IGNORECASE):
                    self.analysis['notable-token']['XML ESCAPE TOKENS (HEX)'][token] \
                        = {'token': token,
                           'count': self.token_count[token],
                           'ex': self.token_examples[token]}
                elif regex.match(r'&(?:amp;)+(?:#X[0-9A-F]{1,6}|#\d{1,7}|[a-z]{1,6});$', token, regex.IGNORECASE):
                    self.analysis['notable-token']['XML ESCAPE TOKENS (NESTED)'][token] \
                        = {'token': token,
                           'count': self.token_count[token],
                           'ex': self.token_examples[token]}
            else:
                # Check for token with characters with multiple scripts
                script_dict = {}
                for char in token:
                    if char.isalpha():
                        unicode_script = self.unicode_util.char_unicode_script(char)
                        script_dict[unicode_script] = True
                n_base_scripts = len(script_dict)
                for script in ('SPACING_MODIFIER_LETTERS', 'MODIFIER_TONE_LETTERS'):
                    if script_dict.get(script):
                        n_base_scripts -= 1
                if n_base_scripts >= 2:
                    key2 = f"WORDS WITH CHARACTERS FROM MULTIPLE SCRIPTS ({', '.join(sorted(script_dict.keys()))})"
                    self.analysis['notable-token'][key2][token] \
                        = {'token': token,
                           'count': self.token_count[token],
                           'ex': self.token_examples[token]}
        # Check for patters with characters of interest (such as @)
        corpus_rtl = self.script_direction.is_right_to_left()
        for orig_pattern in self.pattern_count:
            pattern = orig_pattern
            if corpus_rtl and self.script_direction.text_contains_switchable_chars(pattern):
                adj_pattern = self.script_direction.switch_delimiters_for_rtl_scripts(orig_pattern, skip_rtl_check=True)
                pattern = adj_pattern
            self.wildebeest.set_lv(pattern)
            for pattern_character_of_interest in self.pattern_characters_of_interest:
                if pattern_character_of_interest in orig_pattern:
                    key2 = f"TOKENS WITH {pattern_character_of_interest} " \
                           f"({'U+%04X' % ord(pattern_character_of_interest)} " \
                           f"{self.unicode_util.unicode_name(pattern_character_of_interest)})"
                    pattern_count = self.pattern_count[orig_pattern]
                    self.analysis['pattern'][key2][orig_pattern] \
                        = {'pattern': self.repl_invisible_chars_in_pattern(pattern),
                           'count': pattern_count,
                           'ex': self.pattern_examples[orig_pattern],
                           'lines': sorted(self.pattern_lines[orig_pattern])}
                    ass_class, ass_descr = self.assess_pattern(pattern_character_of_interest, pattern)
                    self.update_pattern_class_counts(key2, orig_pattern, ass_class, pattern_count)
                    self.update_pattern_class_counts(key2, None, ass_class, pattern_count)
                    if ass_class and isinstance(ass_descr, str):
                        self.analysis['pattern'][key2][orig_pattern]['ass-class'] = ass_class
                        self.analysis['pattern'][key2][orig_pattern]['ass-descr'] = ass_descr
                    if highlight_regex := self.pattern_to_regex(pattern):
                        self.analysis['pattern'][key2][orig_pattern]['highlight-regex'] = highlight_regex
            if ('Modifier' in pattern) or ('WordWLM' in pattern):
                key2 = f"TOKENS WITH ORPHAN MODIFIER"
                pattern_count = self.pattern_count[orig_pattern]
                self.analysis['pattern'][key2][orig_pattern] \
                    = {'pattern': self.repl_invisible_chars_in_pattern(pattern),
                       'count': pattern_count,
                       'ex': self.pattern_examples[orig_pattern],
                       'lines': sorted(self.pattern_lines[orig_pattern])}
                ass_class, ass_descr = self.assess_pattern("ORPHAN MODIFIER", pattern)
                self.update_pattern_class_counts(key2, orig_pattern, ass_class, pattern_count)
                self.update_pattern_class_counts(key2, None, ass_class, pattern_count)
                if ass_class and isinstance(ass_descr, str):
                    self.analysis['pattern'][key2][orig_pattern]['ass-class'] = ass_class
                    self.analysis['pattern'][key2][orig_pattern]['ass-descr'] = ass_descr
        # Check for conflict sets (e.g. text containing both Arabic k and Farsi k)
        char_conflict_set = ['əǝә', # LATIN SMALL LETTER SCHWA, LATIN SMALL LETTER TURNED E, CYRILLIC SMALL LETTER SCHWA
                             'كک',  # Arabic/Farsi k
                             'يی',  # Arabic/Farsi y
                             'μµ',  # Greek letter mu/micro sign
                             '"“',  # ASCII QUOTATION MARK/LEFT DOUBLE QUOTATION MARK
                             '"”',  # ASCII QUOTATION MARK/RIGHT DOUBLE QUOTATION MARK
                             "'‘",  # ASCII APOSTROPHE/LEFT SINGLE QUOTATION MARK
                             "'’",  # ASCII APOSTROPHE/RIGHT SINGLE QUOTATION MARK
                             "'ʼˈ",  # ASCII APOSTROPHE/MODIFIER LETTER APOSTROPHE/MODIFIER LETTER VERTICAL LINE
                             "'ꞌ",  # ASCII APOSTROPHE/LATIN SMALL LETTER SALTILLO
                             "'՛",  # ASCII APOSTROPHE/ARMENIAN emphasis sign
                             "‚‘",  # ASCII LOW/LEFT SINGLE QUOTATION MARK
                             "„“",  # ASCII LOW/LEFT DOUBLE QUOTATION MARK
                             "·‧",  # MIDDLE DOT, HYPHENATION POINT
                             "/⁄",  # SOLIDUS, FRACTION SLASH

                             ',\u060C，',  # ASCII/Arabic/Chinese comma
                             ';\u061B፤；',  # ASCII/Arabic/Ethiopic/Chinese semicolon
                             ':꞉፥：',        # ASCII/modifier letter/Ethiopic/Chinese colon
                             '!！',        # ASCII/Chinese exclamation mark
                             '?\u061F፧？',  # ASCII/ARABIC/Ethiopic/Chinese question mark
                             '.\u06D4।።。．', # ASCII/ARABIC full stop/DANDA/Ethiopic/CHINESE PERIOD/FULLWIDTH PERIOD
                             '–—―',        # EN DASH/EM DASH/HORIZONTAL BAR
                             '-−',         # HYPHEN-MINUS, MINUS SIGN
                             '|।৷',         # VERTICAL LINE/DEVANAGARI DANDA/BENGALI CURRENCY NUMERATOR FOUR
                             '(（',        # ASCII/Chinese left parenthesis
                             ')）',        # ASCII/Chinese right parenthesis
                             '«《⟪',       # ASCII/Chinese/mathematical left double angle bracket/quotation mark
                             '»》⟫',       # ASCII/Chinese/mathematical right double angle bracket/quotation mark
                             '!՜',         # ASCII/Armenian exclamation mark
                             ',՝',         # ASCII/Armenian comma
                             '?՞',         # ASCII/Armenian question mark
                             '.։',         # ASCII/Armenian full stop
                             ':։',         # ASCII colon/Armenian full stop
                             '`՝',          # ASCII grave accent/Armenian comma

                            ]
        for char_conflict in char_conflict_set:
            # Matching quotations such as ASCII LOW/LEFT DOUBLE QUOTATION MARK in Ukrainian should not be marked as conflict set
            if (len(char_conflict) == 2) and (self.punct_analysis.get(('lr', char_conflict[0])) == char_conflict[1]):
                # sys.stderr.write(f'MP skipping {char_conflict} conflict set\n')
                continue
            char_list = []
            info_list = []
            count_info_list = []
            for char in list(char_conflict):
                if count := self.character_count[char]:
                    unicode_int = ord(char)
                    unicode_id = 'U+%04X' % unicode_int
                    unicode_name = self.unicode_util.unicode_name(char)
                    count_info_list.append(f'{char} {unicode_id} ({unicode_name}) count: {count}')
                    char_list.append(char)
                    info_list.append([char, unicode_id, unicode_name, count])
            if len(count_info_list) >= 2:
                conflict_key = '/'.join(char_list)
                for info_elem in info_list:
                    self.analysis['rival-char-sets'][conflict_key].append({'char': info_elem[0],
                                                                           'id': info_elem[1],
                                                                           'name': info_elem[2],
                                                                           'count': info_elem[3]})

    def sort_pattern_headings_in_analysis_pattern(self):
        sorted_analysis_pattern = defaultdict(dict)
        for pattern_heading in sorted(self.analysis['pattern'].keys(),
                                      key=lambda ph: self.pattern_class_counts[(ph, None)],
                                      reverse=True):
            sorted_analysis_pattern[pattern_heading] = self.analysis['pattern'][pattern_heading]
            sorted_analysis_pattern_pattern_heading = {}
            if patterns := self.analysis['pattern'][pattern_heading].keys():
                for pattern in sorted(patterns,
                                      key=lambda p: self.pattern_class_counts[(pattern_heading, p)],
                                      reverse=True):
                    sorted_analysis_pattern_pattern_heading[pattern] = sorted_analysis_pattern[pattern_heading][pattern]
            sorted_analysis_pattern[pattern_heading] = sorted_analysis_pattern_pattern_heading
        self.analysis['pattern'] = sorted_analysis_pattern

    def format_examples(self, examples: list, s: str) -> str:
        """Group examples in pretty format string"""
        max_display_len = self.max_n_viz_examples
        ex_l_dict = defaultdict(list)
        ex_r_dict = defaultdict(list)
        ref_id_p = False
        for example in examples:
            example_s, line_number_s = example[0], str(example[1])
            if line_number_s not in ex_l_dict[example_s]:
                ex_l_dict[example_s].append(line_number_s)
                if self.snt_index_to_ref_id and (ref_id := self.snt_index_to_ref_id[int(line_number_s)]):
                    ex_r_dict[example_s].append(ref_id)
                    ref_id_p = True
                else:
                    ex_r_dict[example_s].append(f'l.{line_number_s}')
        if (len(ex_l_dict) == 1) and ex_l_dict.get(s) and not ref_id_p:
            line_numbers = ex_l_dict[s]
            return f"line{'' if len(line_numbers) == 1 else 's'}: {', '.join(line_numbers)[:max_display_len]}"
        else:
            formatted_examples = []
            for example in ex_l_dict.keys():
                if ref_id_p:
                    formatted_examples.append(f"{example} ({', '.join(ex_r_dict[example][:max_display_len])})")
                else:
                    formatted_examples.append(f"{example} (l.{', '.join(ex_l_dict[example][:max_display_len])})")
            return f"example{'' if len(formatted_examples) == 1 else 's'}: {', '.join(formatted_examples)}"

    @staticmethod
    def insert_spaces_before_any_letter_modifiers(s: str):
        """for better human legibility"""
        return ''.join(list(map(lambda c: f' {c}' if regex.match(r'\pM$', c) else c, s)))

    @staticmethod
    def repl_invisible_chars_in_pattern(s: str):
        """for better human legibility"""
        result = ''.join(list(map(lambda c: f'<U+{ord(c):04X}>'  # {self.unicode_util.unicode_name(c)}'
                 if (regex.match(r'(?:\pC|\pZ|\pM)', c) and (not c in ' \u00AD\u202F')) else c, s)))
        for old, new in (('\u00AD', '<SOFT HYPHEN>'),):
            result = result.replace(old, new)
        return result

    @staticmethod
    def string_contains_right_to_left_letters(s: str):
        return regex.search(r'(?V1)[[\p{Arabic}||\p{Hebrew}||\p{Syriac}||\p{Thaana}]&&\pL]', s)

    def pretty_print(self, output_file: TextIO) -> None:
        """Output Wildebeest analysis in human-readable format."""
        n_lines = self.analysis['n_lines']
        n_empty_lines = self.analysis['n_empty_lines']
        n_non_empty_lines = n_lines - n_empty_lines
        output_file.write("OVERVIEW:\n")
        output_file.write(f"File size: {count_plus_noun(n_lines, 'line')}")
        if n_empty_lines:
            output_file.write(f" ({count_plus_noun(n_non_empty_lines, 'non-empty line')},"
                              f" {count_plus_noun(n_empty_lines, 'empty line')})")
        output_file.write(f", {count_plus_noun(self.analysis['n_characters'], 'character')}\n")
        for heading, keyword in (('Letter scripts', 'letter-script'),
                                 ('Number scripts', 'number-script'),
                                 ('Other character groups', 'other-script')):
            output_file.write(f"{heading}: {len(self.analysis[keyword])}\n")
            for unicode_script in self.analysis[keyword].keys():
                letter_script_dict = self.analysis[keyword][unicode_script]
                count = letter_script_dict['count']
                output_file.write(f"    {unicode_script} ({count_plus_noun(count, 'instance')})")
                if ((unicode_script not in ('C0_CONTROL', 'C1_CONTROL', 'SPACE', 'ZERO_WIDTH', 'DIRECTIONAL',
                                            'VARIATION_SELECTORS', 'LOW_SURROGATES'))
                        and (ex_s := letter_script_dict.get('ex'))):
                    ex_s = self.insert_spaces_before_any_letter_modifiers(ex_s)
                    try:
                        output_file.write(f": {ex_s}")
                    except UnicodeError as error:
                        sys.stderr.write(f"*** Unicode error: {error}\n")
                output_file.write("\n")
        non_canonical_char_combs = self.analysis['non-canonical'].keys()
        if n_non_canonical_char_combs := len(non_canonical_char_combs):
            output_file.write(f"Non-canonical character combinations: {n_non_canonical_char_combs}\n")
        char_conflicts = self.analysis['rival-char-sets'].keys()
        if n_char_conflicts := len(char_conflicts):
            output_file.write(f"Rival character sets: {n_char_conflicts}\n")
        notable_dict = defaultdict(dict)
        # {'XML escape tokens': {'GROUP_COUNT': 0, 'TYPE_COUNT': 0, 'TOKEN_COUNT': 0}, ...}
        for notable_heading in sorted(self.analysis['notable-token'].keys()):
            if re.search(r'XML', notable_heading, re.IGNORECASE):
                key1 = 'XML escape tokens'
            elif re.search(r'multi.*script', notable_heading, re.IGNORECASE):
                key1 = 'Words with characters from multiple scripts'
            else:
                continue
            notable_dict[key1]['GROUP_COUNT'] = notable_dict[key1].get('GROUP_COUNT', 0) + 1
            tokens = self.analysis['notable-token'][notable_heading].keys()
            for token in tokens:
                notable_dict[key1]['TYPE_COUNT'] = notable_dict[key1].get('TYPE_COUNT', 0) + 1
                notable_dict[key1]['TOKEN_COUNT'] = notable_dict[key1].get('TOKEN_COUNT', 0) \
                                                    + self.analysis['notable-token'][notable_heading][token]['count']
        for key1 in notable_dict.keys():
            group_count = notable_dict[key1]['GROUP_COUNT']
            type_count = notable_dict[key1]['TYPE_COUNT']
            token_count = notable_dict[key1]['TOKEN_COUNT']
            output_file.write(f"{key1}: "
                              f"{group_count} {'category' if (group_count == 1) else 'categories'}, "
                              f"{type_count} {'unique type' if type_count == 1 else 'unique types'}, "
                              f"{token_count} {'instance' if token_count == 1 else 'instances'}\n")

        output_file.write("\nDETAILS:\n")
        output_file.write(f"Non-canonical character combinations: {len(non_canonical_char_combs)}\n")
        for char_comb in self.analysis['non-canonical'].keys():
            non_canonical_dict = self.analysis['non-canonical'][char_comb]
            orig = non_canonical_dict.get('orig')
            norm = non_canonical_dict.get('norm')
            orig_seq = ' + '.join(list(orig))
            norm_seq = ' + '.join(list(norm))
            orig_count = non_canonical_dict.get('orig-count')
            norm_count = non_canonical_dict.get('norm-count')
            orig_form = non_canonical_dict.get('orig-form')
            norm_form = non_canonical_dict.get('norm-form')
            changes = non_canonical_dict.get('changes')
            output_info = f"Non-canonical: {orig} ({orig_form}{orig_seq}, count: {orig_count})" \
                          f"  Canonical: {norm} ({norm_form}{norm_seq}, count: {norm_count})"
            if self.string_contains_right_to_left_letters(output_info):
                output_file.write(self.lrm)
            output_file.write(f'    {output_info}')
            if changes and not norm_form:
                output_file.write(f"  Changes: {', '.join(changes)}")
            output_file.write("\n")
        output_file.write(f"Rival character sets: {len(char_conflicts)}\n")
        for char_conflict_key in char_conflicts:
            # noinspection SpellCheckingInspection
            char_infos = []
            info_list = self.analysis['rival-char-sets'][char_conflict_key]
            for info_elem in info_list:
                char_infos.append(f"{info_elem['char']} {info_elem['id']} ({info_elem['name']}) "
                                  f"count: {info_elem['count']}")
            output_info = f"{'; '.join(char_infos)}"
            if self.string_contains_right_to_left_letters(output_info):
                output_file.write(self.lrm)
            output_file.write(f"    {output_info}\n")
        if n := self.n_tatweels():
            output_file.write(f"Number of Arabic tatweel characters: {n}\n")
        for notable_heading in sorted(self.analysis['notable-token'].keys()):
            tokens = self.analysis['notable-token'][notable_heading].keys()
            if tokens:
                output_file.write(f"{notable_heading}:\n")
                for i, token in enumerate(tokens, 1):
                    if i > self.max_n_cases:
                        output_file.write('    ...\n')
                        break
                    d = self.analysis['notable-token'][notable_heading][token]
                    output_info = f"{d['token']} count: {d['count']}, {self.format_examples(d['ex'], token)}"
                    if self.string_contains_right_to_left_letters(output_info):
                        output_file.write(self.lrm)
                    output_file.write(f'    {output_info}\n')
        for unicode_block in self.analysis['block'].keys():
            chars = self.analysis['block'][unicode_block].keys()
            if chars:
                output_file.write(f"{unicode_block} characters:\n")
                for i, char in enumerate(chars, 1):
                    if i > self.max_n_cases:
                        output_file.write('    ...\n')
                        break
                    d = self.analysis['block'][unicode_block][char]
                    output_info = f"{self.insert_spaces_before_any_letter_modifiers(d['char'])} " \
                                  f"{d['id']} {d['name']} count: {d['count']}, " \
                                  f"{self.format_examples(d['ex'], char)}"
                    if (decomp_s := ud.decomposition(char)) \
                            and regex.match(r'[0-9A-Z]{4,}$', decomp_s) \
                            and (decomp_c := chr(int(f"0x{decomp_s}", 0))):
                        decomp_name = self.unicode_util.unicode_name(decomp_c)
                        output_info += f", decomposition: {decomp_c} ({decomp_name})"
                    if self.string_contains_right_to_left_letters(output_info):
                        output_file.write(self.lrm)
                    output_file.write(f'    {output_info}\n')
        # for pattern_heading in sorted(self.analysis['pattern'].keys()):
        for pattern_heading in self.analysis['pattern'].keys():
            patterns = self.analysis['pattern'][pattern_heading].keys()
            if patterns:
                output_file.write(f"{pattern_heading}:\n")
                # for i, pattern in enumerate(sorted(patterns, key=lambda p: self.analysis['pattern'][pattern_heading][p]['count'], reverse=True), 1):
                for i, pattern in enumerate(patterns, 1):
                    if i > self.max_n_cases:
                        output_file.write('    ...\n')
                        break
                    d = self.analysis['pattern'][pattern_heading][pattern]
                    ass_class = d.get('ass-class', '')
                    if ass_class.startswith('-'):
                        ass_class_marker = '[-]'
                    elif ass_class.startswith('+'):
                        ass_class_marker = '[+]'
                    else:
                        ass_class_marker = '   '
                    output_info = (f"{ass_class_marker} {d['pattern']} count: {d['count']}, "
                                   f"{self.format_examples(d['ex'], pattern)}")
                    if self.string_contains_right_to_left_letters(output_info):
                        output_file.write(self.lrm)
                    output_file.write(f'    {output_info}\n')

    def n_tatweels(self) -> int:
        # noinspection SpellCheckingInspection
        """Number of Arabic tatweels (also called kahida), a character for non-white-space justification)"""
        try:
            return self.analysis['block']['ARABIC']['\u0640']['count'] or 0
        except KeyError:
            return 0

    def summary_list_of_issues(self) -> List[str]:
        """List of major issues found in Wildebeest analysis, for a 1-line summary, useful for multi-file input"""
        result = []
        letter_scripts = sorted(self.analysis['letter-script'].keys(),
                                key=lambda script: self.analysis['letter-script'][script]['count'], reverse=True)
        if len(letter_scripts) >= 2:
            letter_script_info_list = []
            for letter_script in letter_scripts:
                if (ex_s := self.analysis['letter-script'][letter_script].get('ex')) and len(ex_s) < 10:
                    letter_script_info_list.append(f"{letter_script} "
                                                   f"({self.insert_spaces_before_any_letter_modifiers(ex_s)})")
                else:
                    letter_script_info_list.append(letter_script)
            result.append(f"{count_plus_noun(len(letter_scripts), 'letter script')}: "
                          f"{', '.join(letter_script_info_list)}")
        number_scripts = sorted(self.analysis['number-script'].keys(),
                                key=lambda script: self.analysis['number-script'][script]['count'], reverse=True)
        if (len(number_scripts) >= 2) and not number_scripts == ['ASCII_DIGIT', 'VULGAR_FRACTION']:
            number_script_info_list = []
            for number_script in number_scripts:
                if (ex_s := self.analysis['number-script'][number_script].get('ex')) and len(ex_s) < 10:
                    number_script_info_list.append(f"{number_script} ({ex_s})")
                else:
                    number_script_info_list.append(number_script)
            result.append(f"{count_plus_noun(len(number_scripts), 'number script')}: "
                          f"{', '.join(number_script_info_list)}")
        if self.analysis['other-script']['C0_CONTROL']:
            result.append('C0_CONTROL')
        if self.analysis['other-script']['C1_CONTROL']:
            result.append('C1_CONTROL')
        non_canonical_char_combs = self.analysis['non-canonical'].keys()
        if n_non_canonical_char_combs := len(non_canonical_char_combs):
            n_instances = 0
            for char_comb in non_canonical_char_combs:
                n_instances += self.analysis['non-canonical'][char_comb]['orig-count']
            result.append(f"{count_plus_noun(n_non_canonical_char_combs, 'non-canonical character combination')} "
                          f"({count_plus_noun(n_instances, 'instance')})")
        char_conflicts = self.analysis['rival-char-sets'].keys()
        if n_char_conflicts := len(char_conflicts):
            result.append(count_plus_noun(n_char_conflicts, 'character set conflict'))
        flag_class_dict = {r'^XML ESCAPE': 'XML escape token',
                           r'^REPLACEMENT': 'Replacement character',
                           r'ORPHAN.?MODIFIER': 'Orphan modifier',
                           r'VARIATION.?SELECTOR': 'Variation selector',
                           r'IPA.?EXTENSION': 'IPA character',
                           r'WORDS.?WITH.?CHARACTERS.?FROM.?MULTIPLE.?SCRIPTS': 'multi-script word',
                           r'PRIVATE.?USE': 'Private use character',
                           r'SURROGATES': 'Surrogate'}
        flag_bool_dict = {}
        for key2 in sorted(list(self.analysis['notable-token'].keys())
                           + list(self.analysis['pattern'].keys())
                           + list(self.analysis['letter-script'].keys())
                           + list(self.analysis['other-script'].keys())):
            for regex_term in flag_class_dict.keys():
                if regex.search(regex_term, key2):
                    flag_bool_dict[flag_class_dict[regex_term]] = True
        for flag_class in flag_bool_dict.keys():
            result.append(flag_class)
        if self.n_tatweels():
            result.append('Tatweel')
        return result

    def add_corpus_snt(self, text: str, snt_id: str) -> None:
        if snt_id and text:
            self.snt_list.append(text)
            self.ref_id_list.append(snt_id)
            self.n_snt += 1
            self.snt_index_to_ref_id[self.n_snt] = snt_id
            self.ref_id_to_snt_index[snt_id] = self.n_snt
            self.ref_id_to_text[snt_id] = text

    def extract_json_input(self, args) -> int:
        if isinstance(args.json, str):
            try:
                in_json = json.loads(args.json)
            except json.JSONDecodeError as e:
                sys.stderr.write(f'Invalid JSON input {e}\n{args.json}\n')
                return 0
        elif isinstance(args.json, dict):
            in_json = args.json
        else:
            sys.stderr.write(f'Invalid JSON input type {args.json}\n')
            return 0

        if jsonrpc := in_json.get('jsonrpc'):
            self.dyn_json['jsonrpc'] = jsonrpc
        if json_id := in_json.get('id'):
            self.dyn_json['id'] = json_id
        if result_timestamp := datetime.datetime.now().replace(microsecond=0).isoformat():
            self.dyn_json['resultTimestamp'] = result_timestamp
        # sys.stderr.write(f'{args.jsonrpc} {args.json_id}\n')
        if json_params := in_json.get('params'):
            for json_param in json_params:
                self.dyn_check_selectors = json_param.get('checks')
                if self.dyn_check_selectors is None:
                    self.dyn_check_selectors = json_param.get('selectors')
                if json_corpus := json_param.get('corpus'):
                    self.corpus_id = json_corpus.get('corpusId')
                    self.corpus_name = json_corpus.get('corpusName')
                    self.lang_code = json_corpus.get('langCode', self.lang_code)
                    self.lang_name = json_corpus.get('langName')
                    if self.lang_code and (self.dyn_json.get('langCode') is None):
                        self.dyn_json['corpusLangCode'] = self.lang_code
                    if corpus_body := json_corpus.get('body'):
                        for check_snt in corpus_body:
                            snt_id = check_snt.get('sntId')
                            text = check_snt.get('text')
                            self.add_corpus_snt(text, snt_id)
                    elif corpus_filename := json_corpus.get('filename'):
                        vref_filename = json_corpus.get('vref')
                        vref_prefix_filter = json_corpus.get('vrefPrefixFilter')
                        try:
                            f_vref = open(vref_filename)
                        except IOError:
                            f_vref = None
                        with open(corpus_filename) as f_in:
                            for line in f_in:
                                text = line.strip()
                                snt_id = f_vref.readline().strip() if f_vref else f"Line{self.n_snt + 1}"
                                if text == "<range>":
                                    continue
                                if vref_prefix_filter and not snt_id.startswith(vref_prefix_filter):
                                    continue
                                self.add_corpus_snt(text, snt_id)
        self.dyn_json['result'] = []
        self.dyn_json['version'] = defaultdict(str)
        self.populate_version(self.dyn_json['version'])
        self.dyn_json['skippedChecks'] = self.dyn_skipped_checks
        return self.n_snt

    @staticmethod
    def populate_version(version: dict | None = None) -> dict:
        if version is None:
            version = defaultdict(str)
        version['GreekRoom'] = __greekRoomVersion__
        version['GreekRoomFormat'] = __greekRoomFormatVersion__
        version['GreekRoomWildebeest'] = __wildebeestVersion__
        return version

    @staticmethod
    def load_ref_ids(snt_index_to_ref_id: dict, filename) -> None:
        """Load file mapping line numbers to sentence IDs."""
        with open(filename, 'r', encoding='utf-8') as f:
            line_number = 0
            for line in f:
                line_number += 1
                snt_index_to_ref_id[line_number] = line.strip()

    def load_cross_snt_spans(self, filename) -> None:
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                s = f.read()
        except (NameError, TypeError, ValueError, OSError) as err:
            sys.stderr.write(f'*** {type(err).__name__}: Could not read file {filename}\n{err}\n')
            return
        try:
            d = json.loads(s)
        except (NameError, TypeError, ValueError) as err:
            sys.stderr.write(f'*** {type(err).__name__}: Could not load cross-snt info from {filename}\n{err}\n')
            return
        translation = d.get("translation")
        json_corpus = d.get("corpus")
        refresher_dict = defaultdict(list)
        cross_snt_span_dict = defaultdict(list)
        triple_nesting_dict = defaultdict(list)
        line_length = defaultdict(int)
        char_count = defaultdict(int)
        cross_snt_span_list = d.get("cross-snt-spans", [])
        refresher_left_list = d.get("refresher-lefts", [])
        triple_nesting_list = d.get("triple-nesting", [])
        ref_translation_elem = {'translation': translation, 'corpus': json_corpus, 'line-length': line_length,
                                'refresher-dict': refresher_dict, 'cross-snt-span-dict': cross_snt_span_dict,
                                'cross_snt_spans': cross_snt_span_list, 'char_count': char_count,
                                'triple-dict': triple_nesting_dict}
        self.punct_analysis['ref_translations'].append(ref_translation_elem)
        for c in cross_snt_span_list:
            char_count[c] += 1
            for cross_snt_span in cross_snt_span_list[c]:
                open_pos, close_pos = cross_snt_span[0], cross_snt_span[1]
                open_line_number, open_char_pos, open_line_len = open_pos
                close_line_number, close_char_pos, close_line_len = close_pos
                for line_number in range(open_line_number, close_line_number+1):
                    cross_snt_span_dict[(c, line_number)].append(cross_snt_span)
        for c in triple_nesting_list:
            for cross_snt_span in triple_nesting_list[c]:
                open_pos, close_pos = cross_snt_span[0], cross_snt_span[1]
                open_line_number, open_char_pos, open_line_len = open_pos
                close_line_number, close_char_pos, close_line_len = close_pos
                for line_number in range(open_line_number, close_line_number+1):
                    triple_nesting_dict[(c, line_number)].append(cross_snt_span)
        for c in refresher_left_list:
            prev_refresher_line_number = None
            refresher_lefts = refresher_left_list[c]
            for refresher_left in refresher_lefts:
                line_number, char_pos, line_len, *optional_args = refresher_left
                cross_snt_span = None
                for cross_snt_span_cand in cross_snt_span_dict[(c, line_number)]:
                    open_pos, close_pos = cross_snt_span_cand[0], cross_snt_span_cand[1]
                    open_line_number, open_char_pos, open_line_len = open_pos
                    close_line_number, close_char_pos, close_line_len = close_pos
                    if (open_line_number == line_number) and (char_pos < open_char_pos):
                        continue
                    elif (close_line_number == line_number) and (char_pos > close_char_pos):
                        continue
                    else:
                        cross_snt_span = cross_snt_span_cand
                        break
                refresher_dict[(c, line_number)].append((char_pos, prev_refresher_line_number, cross_snt_span))
                if char_pos:
                    line_length[line_number] = line_len
                prev_refresher_line_number = line_number

    @staticmethod
    def dyn_json_pretty_print(s: str) -> str:
        s = regex.sub(r'({"sntId":)', r'\n  \1', s)
        s = regex.sub(r'("check":)', r'\n     \1', s)
        s = regex.sub(r'("scripts":)', r'\n       \1', s)
        s = regex.sub(r'("actionMenu":)', r'\n     \1', s)
        s = regex.sub(r'(?<=, )({"substitute":)', r'\n                    \1', s)
        s = regex.sub(r'("version":)', r'\n \1', s)
        s = regex.sub(r'("skippedChecks":)', r'\n \1', s)
        return s

    def verbalize_greek_room_check_id(self, check: str, _lang_code, sub_s: str | None = None) -> str | None:
        if m_check := regex.match(r'GreekRoom:Wildebeest:punctuation:space:([^:]*):detach-from-right', check):
            return f"add missing space to the right of {m_check.group(1)}"
        if m_check := regex.match(r'GreekRoom:Wildebeest:punctuation:space:([^:]*):attach-to-left', check):
            return f"remove spurious space on the left of {m_check.group(1)}"
        if m_check := regex.match(r'GreekRoom:Wildebeest:punctuation:space:([^:]*):reattach-to-left', check):
            return f"remove spurious space on the left, and add missing space to the right of {m_check.group(1)}"
        if regex.match(r'GreekRoom:Wildebeest:encoding:nukta-position', check):
            return f"move the nukta to the correct position right after the main letter"
        if regex.match(r'GreekRoom:Wildebeest:punctuation:unpaired-delimiter:open', check):
            result = f"no matching close delimiter"
            if close_delimiters := self.paired_delimiter_state['open-to-close-delimiters'][sub_s]:
                result += ' such as: ' + ' '.join(close_delimiters)
            return result
        if regex.match(r'GreekRoom:Wildebeest:punctuation:unpaired-delimiter:close', check):
            result = f"no matching open delimiter"
            if open_delimiters := self.paired_delimiter_state['close-to-open-delimiters'][sub_s]:
                result += ' such as: ' +  ' '.join(open_delimiters)
            return result
        if m_check := regex.match(r'GreekRoom:Wildebeest:punctuation:punctuation:repair:([^:]*):([^:]*)', check):
            return f"replace {m_check.group(1)} by {m_check.group(2)}"
        if check == 'GreekRoom:Wildebeest:punctuation:unexpected':
            return f"unexpected punctuation"
        if check == 'GreekRoom:Wildebeest:character:suspicious:C1_CONTROL':
            return f"remove control character"
        if check == 'GreekRoom:Wildebeest:character:suspicious:VARIATION_SELECTORS':
            return f"remove variation selector"
        return None

    def verbalize_action_menu(self, action_menu: list, check: str, lang_code) -> str:
        result = ""
        index = 0
        for menu_item in action_menu:
            index += 1
            substitute = menu_item.get('substitute')
            if substitute is not None:
                # sys.stderr.write(f"Verb subst {check} {menu_item} {substitute}\n")
                check_verbalization = self.verbalize_greek_room_check_id(check, lang_code)
                substitute_clause = f'''Replace by "{substitute}"''' if substitute else "Delete"
                if check_verbalization:
                        result += f'''  [{index}] {substitute_clause} ({check_verbalization})'''
                else:
                    result += f'''  [{index}] {substitute_clause}  ({simple_unicode_names(substitute, ',  ')})'''
            else:
                result += f'''  [{index}] {menu_item}'''
        return result

    @staticmethod
    def dyn_wrap_text(s: str, in_delimiter: str, out_delimiter, limit: int) -> str:
        delimiter_elems, start_positions, text_elems = general_util.findall3(in_delimiter, s)
        result = text_elems[0]
        current_line_length = len(result)
        for delimiter_s, text_elem in zip(delimiter_elems, text_elems[1:]):
            if current_line_length + len(delimiter_s) + len(text_elem) <= limit:
                result += delimiter_s + text_elem
                current_line_length += len(delimiter_s) + len(text_elem)
            else:
                result += out_delimiter + text_elem
                current_line_length = len(out_delimiter) + len(text_elem)
        return result

    def html_markup_snt(self, snt: str, feedback_items: list, min_auto_correct: float) -> str:
        pos2items = defaultdict(list)
        for feedback_item in feedback_items:
            span = feedback_item.get('span')
            for start_pos, end_pos in span:
                for pos in range(start_pos, end_pos):
                    # sys.stderr.write(f"B {pos} {snt}\n")
                    pos2items[pos].append(feedback_item)
        result = ""
        title_newline = "\n"
        # title_newline = "&#10;&#10;"
        start_pos, max_pos = 0, len(snt)
        while start_pos < max_pos:
            if local_feedback_items := pos2items[start_pos]:
                end_pos = start_pos + 1
                while (end_pos < max_pos) and (pos2items[end_pos] == local_feedback_items):
                    end_pos += 1
                sub_s = snt[start_pos:end_pos]
                # sys.stderr.write(f"G {start_pos}-{end_pos} {snt}\n")
                unicode_names = simple_unicode_names(sub_s, ',  ')
                title = wb_pp.guard_html(f'''Original string: "{sub_s}"{title_newline}''', True)
                if len(sub_s) == 1:
                    name_clause = f"  • Character name: {unicode_names}  (at position {start_pos})"
                else:
                    name_clause = f"  • Character names ({len(sub_s)}): {unicode_names}  (starting at position {start_pos})"
                wrapped_name_clause = self.dyn_wrap_text(name_clause, r', {2,}', f',{title_newline}&xnbsp;', 80)
                title += wb_pp.guard_html(wrapped_name_clause + title_newline, True)
                best_substitute, best_substitute_start, best_substitute_end, best_confidence = None, None, None, 0
                for local_feedback_item in local_feedback_items:
                    check = local_feedback_item.get("check")
                    title += wb_pp.guard_html(f'''{'‾'*100}{title_newline}Check alert: {check}  {title_newline}''', True)
                    if scripts := local_feedback_item.get('scripts'):
                        title += wb_pp.guard_html(f'''  • Scripts: {", ".join(scripts)}{title_newline}''', True)
                    if minority_script := local_feedback_item.get('minorityScript'):
                        title += wb_pp.guard_html(f'''  • Minority script: {minority_script}{title_newline}''', True)
                    if minority_script_letters := local_feedback_item.get('minorityScriptLetters'):
                        title += wb_pp.guard_html(f'''  • Minority script letters: {", ".join(minority_script_letters)}{title_newline}''', True)
                    if action_menu := local_feedback_item.get('actionMenu'):
                        action_menu_pp = "  • Action menu:" + self.verbalize_action_menu(action_menu, check, self.lang_code)
                        # sys.stderr.write(f'  action_menu_pp: {action_menu_pp}\n')
                        wrapped_action_menu_pp = self.dyn_wrap_text(action_menu_pp, r' {2,}', f'{title_newline}&xnbsp;', 80)
                        title += wb_pp.guard_html(f'''{wrapped_action_menu_pp}{title_newline}''', True)
                        for menu_item in action_menu:
                            substitute = menu_item.get('substitute')
                            confidence = menu_item.get('confidence')
                            if ((substitute is not None) and confidence and (confidence > best_confidence)
                                    and (local_feedback_item.get('span') == [[start_pos, end_pos]])):
                                best_substitute, best_substitute_start, best_substitute_end, best_confidence \
                                    = substitute, start_pos, end_pos, confidence
                    elif check_verbalization := self.verbalize_greek_room_check_id(check, self.lang_code, sub_s):
                        verbalization_pp = "  • Help: " + check_verbalization
                        wrapped_verbalization_pp = self.dyn_wrap_text(verbalization_pp, r' {2,}', f'{title_newline}&xnbsp;', 80)
                        title += wb_pp.guard_html(f'''{wrapped_verbalization_pp}{title_newline}''', True)
                if best_substitute == '':
                    print_string = sub_s
                    text_deco = "text-decoration:line-through;"
                    color = "red"
                else:
                    print_string = best_substitute
                    text_deco = ''
                    color = '#008800'
                if best_confidence >= min_auto_correct:
                    if len(local_feedback_items) >= 2:
                        markup = f'''<span style="color:blue;background-color:#DFDFFF;font-weight:bold;white-space: pre;{text_deco}" pbtitle="{title}">'''

                    else:
                        markup = f'''<span style="color:{color};background-color:#DFFFDF;font-weight:bold;white-space: pre;{text_deco}" pbtitle="{title}">'''
                    markup += html_util.guard_html(print_string)
                else:
                    markup = f'''<span style="color:red;background-color:#FFDFDF;font-weight:bold;white-space: pre;" pbtitle="{title}">'''
                    if sub_s in self.unicode_util.invisible_characters:  # e.g. ZERO WIDTH SPACE
                        markup += '\u2009' + sub_s   # ADD THIN SPACE
                    else:
                        markup += html_util.guard_html(sub_s)
                markup += '''</span>'''
                result += markup
                start_pos = end_pos
            else:
                result += html_util.guard_html(snt[start_pos])
                start_pos += 1
        return result

    def write_corpus_info(self, out: io.TextIOWrapper) -> None:
        out.write('<ul>\n')
        if self.corpus_name:
            if self.corpus_id:
                out.write(f'''<li> Corpus: {self.corpus_name} &nbsp; <span style="color:#AAAAAA">(ID: {self.corpus_id})</span>\n''')
            else:
                out.write(f'''<li> Corpus: {self.corpus_name}\n''')
        elif self.corpus_id:
            out.write(f'''<li> Corpus ID: {self.corpus_id}\n''')
        if self.lang_name:
            if self.lang_code:
                out.write(f'''<li> Language: {self.lang_name} &nbsp; <span style="color:#AAAAAA">(code: {self.lang_code})</span>\n''')
            else:
                out.write(f'''<li> Language: {self.lang_name}\n''')
        elif self.lang_code:
            out.write(f'''<li> Language code: {self.lang_code}\n''')
        if self.auto_correct_threshold is not None:
            out.write(f'''<li> Threshold for automatic correction: {self.auto_correct_threshold}\n''')
        if total_count := self.dyn_json_results.n_issues:
            n_snt_ids = len(self.dyn_json_results.snt_id_set)
            suffix = "" if n_snt_ids == 1 else "s"
            out.write(f'''<li> Total number of issues flagged: {total_count} &nbsp; <span style="color:#AAAAAA">(in {n_snt_ids} verse{suffix})</span>\n''')
        if self.dyn_json['version']:
            key_value_elements = map(lambda k: f"{k}: {self.dyn_json['version'][k]}", self.dyn_json['version'])
            out.write(f'''<li> Software version: &nbsp; {" &nbsp; ".join(key_value_elements)}\n''')
        out.write('</ul>\n')

    def dyn_html_print_by_snt(self, out: io.TextIOWrapper) -> None:
        out.write(html_util.html_head(f"Dynamic Wildebeest Visualization", datetime.datetime.now().strftime('%B %d, %Y at %H:%M'), "wb viz"))
        self.write_corpus_info(out)
        out.write('''    <table cellpadding="10">\n''')
        for snt, snt_id in zip(self.snt_list, self.ref_id_list):
            if feedback_items := self.dyn_json_results.results_by_snt_id[snt_id]:
                snt_id_g = html_util.guard_html(snt_id).replace(' ', '&nbsp;')
                marked_up_snt = self.html_markup_snt(snt, feedback_items, 0.3)
                out.write(f"      <tr><td>{snt_id_g}</td><td>{marked_up_snt}</td>\n")
        out.write("    </table>\n")
        out.write(f"    {'<br>' * 6}\n")
        html_util.print_html_foot(out)

    def dyn_html_print_by_check(self, out: io.TextIOWrapper) -> None:
        out.write(html_util.html_head(f"Dynamic Wildebeest Visualization (by check type)",
                                      datetime.datetime.now().strftime('%B %d, %Y at %H:%M'), "wb viz"))
        self.write_corpus_info(out)
        out.write('''    <table cellpadding="10">\n''')
        for check_id in sorted(self.dyn_json_results.results_by_check_id.keys()):
            count = len(self.dyn_json_results.results_by_check_id[check_id])
            count_s = "" if count == 1 else "s"
            out.write(f'''      <tr><td colspan="2"><b>Check: {check_id}</b> ({count} instance{count_s})</td>\n''')
            for snt_id in sorted(self.dyn_json_results.check_id_snt_ids[check_id], key=lambda x: self.ref_id_to_snt_index[x]):
                if feedback_items := self.dyn_json_results.results_by_check_id_and_snt_id[(check_id, snt_id)]:
                    snt = self.ref_id_to_text.get(snt_id, "???")
                    snt_id_g = html_util.guard_html(snt_id).replace(' ', '&nbsp;')
                    marked_up_snt = self.html_markup_snt(snt, feedback_items, 0.3)
                    out.write(f"      <tr><td>{snt_id_g}</td><td>{marked_up_snt}</td>\n")
        out.write("    </table>\n")
        out.write(f"    {'<br>' * 6}\n")
        html_util.print_html_foot(out)

    def check_w_args(self, args: argparse.Namespace, text_corpus: corpus.TextCorpus | None = None) -> dict:
        _n_snt = self.extract_json_input(args)
        self.text_corpus = text_corpus or corpus.TextCorpus()
        self.text_corpus.add_text_corpus(self.snt_list, self.ref_id_list)
        self.dyn_checks()
        return self.dyn_json


def init_text_corpus() -> corpus.TextCorpus:
    return corpus.TextCorpus()


def check(json_check_request: dict, text_corpus: corpus.TextCorpus | None = None) -> dict:
    lang_code = json_check_request['params'][0]['corpus']['langCode']
    args = argparse.Namespace(json=json_check_request,
                              lc=lang_code)
    add_missing_default_argparse_args(args)
    wb = WildebeestAnalysis(args)
    return wb.check_w_args(args, text_corpus)


def plural_noun_form(noun: str) -> str:
    """Quick and dirty plural form, e.g. 'baby' -> 'babies'"""
    if noun.endswith('y'):
        return regex.sub(r'y$', 'ies', noun)
    else:
        return noun + 's'


def count_plus_noun(count: int, noun: str) -> str:
    """Quick and dirty count + plural form, e.g. (2, 'baby') -> '2 babies'"""
    return f'{count} {noun if count == 1 else plural_noun_form(noun)}'


def process_args(args) -> WildebeestAnalysis:
    """Perform Wildebeest analysis for 1 file, using argparse args."""
    wb = WildebeestAnalysis(args)
    scripts_repair = ScriptRepair(wb)
    wb.script_repair = scripts_repair
    if args.snt_index_to_ref_id:
        wb.snt_index_to_ref_id = args.snt_index_to_ref_id
    wb.corpus_w_rtf_delimiter_adjustments = defaultdict(str)
    wb.auto_correct_threshold = args.auto_correct_threshold
    args.total_bytes = None
    if args.json:
        _n_snt = wb.extract_json_input(args)
        # sys.stderr.write(f'Extracted {n_snt} verses from JSON object.\n')
    if args.input is sys.stdin:
        args.input = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='surrogateescape')
        if not re.search('utf-8', sys.stdin.encoding, re.IGNORECASE):
            log.error(f"Bad STDIN encoding '{sys.stdin.encoding}' as opposed to 'utf-8'. "
                      f"Suggestion: 'export PYTHONIOENCODING=UTF-8' or use '--input FILENAME' option")
    elif args.input:
        inp_path = args.input
        assert isinstance(inp_path, Path)
        if not inp_path.exists():
            raise ValueError(f"{inp_path} does not exist.")
        args.total_bytes = inp_path.stat().st_size
        args.input = argparse.FileType('r', encoding='utf-8', errors='surrogateescape')(str(inp_path))
        wb.filename = inp_path

    for ref_cross_snt_span_file in args.ref_cross_snt_span_files:
        if args.verbose:
            sys.stderr.write(f'Load ref {ref_cross_snt_span_file}\n')
        wb.load_cross_snt_spans(ref_cross_snt_span_file)
    if args.legacy_text_output is sys.stdout and not re.search('utf-8', sys.stdout.encoding, re.IGNORECASE):
        log.error(f"Error: Bad STDIN/STDOUT encoding '{sys.stdout.encoding}' as opposed to 'utf-8'. \
                        Suggestion: 'export PYTHONIOENCODING=UTF-8' or use use '--output FILENAME' option")
    if args.input or wb.snt_list or args.strings:
        wb.collect_counts_and_examples_in_file(args,
                                               total_bytes=args.total_bytes,
                                               progress_bar=args.progress_bar)
    else:  # nothing to process
        log.warning('Called function process_with_args with neither args.input nor args.snt_list nor args.strings')
    wb.aggregate()  # Aggregate raw counts and examples into analysis.
    wb.text_corpus = corpus.TextCorpus(snt_list = wb.snt_list, snt_id_list = wb.ref_id_list)
    wb.dyn_checks()
    wb.remove_empty_dicts()  # Remove empty dictionaries that were created to impose a specific order
    wb.sort_pattern_headings_in_analysis_pattern()
    if args.json_legacy_out:
        args.json_legacy_out.write(json.dumps(wb.analysis) + "\n")
    if args.json_out_filename:
        args.json_out_filename.write(wb.dyn_json_pretty_print(json.dumps(wb.dyn_json) + "\n"))
        n_snt = len(wb.snt_list)
        n_issues = wb.dyn_json_results.n_issues
        snt_kw = "verse" if n_snt == 1 else "verses"
        issues_kw = "issue" if n_issues == 1 else "issues"
        log.info(f'Dynamic Wildebeest identified {n_issues} {issues_kw} in {n_snt} {snt_kw}.')
    if args.html_out_filename_by_snt_id:
        wb.dyn_html_print_by_snt(args.html_out_filename_by_snt_id)
        log.info(f"Wrote HTML viz to {general_util.full_filename(args.html_out_filename_by_snt_id)}")
    if args.html_out_filename_by_check:
        wb.dyn_html_print_by_check(args.html_out_filename_by_check)
        log.info(f"Wrote HTML viz (by check) to {general_util.full_filename(args.html_out_filename_by_check)}")
    if args.summary or args.summary_file:
        summary = '; '.join(wb.summary_list_of_issues())
        if args.summary:
            args.legacy_text_output.write(f"{args.file_id}: {summary}\n")
        if args.summary_file:
            with open(args.summary_file, 'w') as f_summary:
                f_summary.write(f"{summary}\n")
    elif args.legacy_text_output:
        wb.pretty_print(args.legacy_text_output)
    if args.legacy_text_output:
        args.legacy_text_output.flush()
    return wb


def process(in_file: str | None = None,     # provide exactly one input: input filename, strings or string
            strings: list[str] | None = None,
            string: str | None = None,
            legacy_text_output: TextIO | None = None,    # output filename (for pretty-print)
            json_legacy_out: TextIO | None = None,  # output filename (in json)
            lang_code: str | None = None,
            ref_cross_snt_span_files: list[str] = (),
            max_cases: int = 500,                  # max cases per block (e.g. number of characters in script)
            max_examples: int = 100,               # max examples per case
            max_examples_viz: int = 5,             # max examples per case in visualization
            max_script_lines: int = 200,
            max_pattern_lines: int = 200,
            max_bad_pattern_lines: int = 2000,
            max_non_canonical_lines: int = 100,
            max_char_conflict_lines: int = 100,
            max_notable_token_lines: int = 1000,
            verbose: int = 0,
            # snt_index_to_ref_id is a dictionary mapping line_numbers/string_indexes (int, starting at 1) to snt IDs (str)
            summary_file: Optional[str] = None,
            snt_index_to_ref_id: Optional[dict] = None) -> WildebeestAnalysis:
    """Entry point when Wildebeest Analysis for non-CLI use; maps to CLI interface"""
    return process_args(argparse.Namespace(strings=[string] if string and not strings else strings,
                                           input=Path(in_file) if in_file else None,
                                           legacy_text_output=legacy_text_output, json_legacy_out=json_legacy_out,
                                           lc=lang_code, max_cases=max_cases,
                                           ref_cross_snt_span_files=ref_cross_snt_span_files,
                                           max_examples=max_examples,
                                           max_examples_viz=max_examples_viz,
                                           max_script_lines=max_script_lines,
                                           max_pattern_lines=max_pattern_lines,
                                           max_bad_pattern_lines=max_bad_pattern_lines,
                                           max_non_canonical_lines=max_non_canonical_lines,
                                           max_char_conflict_lines=max_char_conflict_lines,
                                           max_notable_token_lines=max_notable_token_lines,
                                           summary=None, summary_file=summary_file,
                                           progress_bar=None, snt_index_to_ref_id=snt_index_to_ref_id,
                                           verbose=verbose))


def add_missing_default_argparse_args(args: argparse.Namespace) -> None:
    _efault_values = (('max_pattern_lines', 0),
                      ('max_bad_pattern_lines', 0),
                      ('max_examples', 0),
                      ('max_examples_viz', 0),
                      ('max_cases', 0),
                      ('max_script_lines', 0),
                      ('max_non_canonical_lines', 0),
                      ('max_char_conflict_lines', 0),
                      ('max_notable_token_lines', 0),
                      ('summary', 0),
                      ('input', None),
                      ('legacy_text_output', None),
                      ('snt_index_to_ref_id', None),
                      ('json_legacy_out', None),
                      ('summary_file', None),
                      ('progress_bar', False),
                      ('ref_cross_snt_span_files', ()))
    d = vars(args)
    if 'max_pattern_lines' not in d.keys():
        args.max_pattern_lines = 0
    if 'max_bad_pattern_lines' not in d.keys():
        args.max_bad_pattern_lines = 0
    if 'max_examples' not in d.keys():
        args.max_examples = 0
    if 'max_examples_viz' not in d.keys():
        args.max_examples_viz = 0
    if 'max_cases' not in d.keys():
        args.max_cases = 0
    if 'max_script_lines' not in d.keys():
        args.max_script_lines = 0
    if 'max_non_canonical_lines' not in d.keys():
        args.max_non_canonical_lines = 0
    if 'max_char_conflict_lines' not in d.keys():
        args.max_char_conflict_lines = 0
    if 'max_notable_token_lines' not in d.keys():
        args.max_notable_token_lines = 0
    if 'summary' not in d.keys():
        args.summary = 0
    if 'input' not in d.keys():
        args.input = None
    if 'legacy_text_output' not in d.keys():
        args.legacy_text_output = None
    if 'snt_index_to_ref_id' not in d.keys():
        args.snt_index_to_ref_id = None
    if 'json_legacy_out' not in d.keys():
        args.json_legacy_out = None
    if 'summary_file' not in d.keys():
        args.summary_file = None
    if 'progress_bar' not in d.keys():
        args.progress_bar = False
    if 'ref_cross_snt_span_files' not in d.keys():
        args.ref_cross_snt_span_files = ()
    # HERE Surely the above can be done more elegantly


def main():
    """Wrapper around Wildebeest analysis that takes care of argument parsing and prints change stats to STDERR."""
    # parse arguments
    parser = argparse.ArgumentParser(description='Analyzes a given text for a wide range of anomalies', prog="wb-ana")
    parser.add_argument('-j', '--json', help='input dict, text or filename (alternative 1)')
    parser.add_argument('-i', '--input', type=Path,
                        default=None, metavar='INPUT-FILENAME', help='(alternative 2; default: None/STDIN)')
    parser.add_argument('-o', '--json_out_filename', type=argparse.FileType('w', encoding='utf-8', errors='ignore'),
                        default=None, help='output JSON filename')
    parser.add_argument('-H', '--html_out_filename_by_snt_id', type=argparse.FileType('w', encoding='utf-8', errors='ignore'),
                        default=None)
    parser.add_argument('-C', '--html_out_filename_by_check', type=argparse.FileType('w', encoding='utf-8', errors='ignore'),
                        default=None)
    parser.add_argument('--batch', type=Path, default=None, metavar='BATCH_DIR',
                        help='Directory with batch of input files (BATCH_DIR/*.txt)')
    parser.add_argument('-s', '--summary', action='count', default=0, help='single summary line per file')
    parser.add_argument('--summary_file', type=Path, default=None, help='file with single summary line')
    parser.add_argument('-O', '--legacy_text_output', type=argparse.FileType('w', encoding='utf-8', errors='ignore'),
                        default=None, metavar='LEGACY-OUTPUT-FILENAME', help='(default: None/STDOUT)')
    parser.add_argument('-J', '--json_legacy_out', type=argparse.FileType('w', encoding='utf-8', errors='ignore'),
                        default=None, metavar='JSON-LEGACY-OUTPUT-FILENAME', help='(default: None)')
    parser.add_argument('--html_output_filename', type=str, default=None)
    parser.add_argument('--html_example_dir', type=str, default=None)
    parser.add_argument('--file_id', type=str, default=None)
    parser.add_argument('--lc', type=str, default=None,
                        metavar='LANGUAGE-CODE', help="ISO 639-3, e.g. 'fas' for Persian")
    parser.add_argument('-v', '--verbose', action='count', default=0, help='write change log etc. to STDERR')
    parser.add_argument('-pb', '--progress_bar', action='store_true', default=False, help='Show progress bar')
    parser.add_argument('-n', '--max_cases', type=int, default=100, help='max number of cases per group')
    parser.add_argument('-x', '--max_examples_viz', type=int, default=5, help='max number of examples per viz line')
    parser.add_argument('--max_examples', type=int, default=100, help='max number of examples per line')
    parser.add_argument('--max_pattern_lines', type=int, default=200)
    parser.add_argument('--max_bad_pattern_lines', type=int, default=2000)
    parser.add_argument('--max_script_lines', type=int, default=200)
    parser.add_argument('--max_non_canonical_lines', type=int, default=100)
    parser.add_argument('--max_char_conflict_lines', type=int, default=100)
    parser.add_argument('--max_notable_token_lines', type=int, default=1000)
    parser.add_argument('-r', '--ref_id_file', type=Path, metavar='REF-FILENAME',
                        help='(optional file with sentence reference IDs)')
    parser.add_argument('--ref_cross_snt_span_files', type=Path, nargs='*', default=(),
                        help='optional; input; format: json; content: cross-sentence quotations, open quotation marks')
    parser.add_argument('--version', action='version',
                        version=f'%(prog)s {__wildebeestVersion__} last modified: {wildebeest_last_mod_date}')
    parser.add_argument('--snt_index_to_ref_id', default=None, help=argparse.SUPPRESS)
    parser.add_argument('--strings', default=None, help=argparse.SUPPRESS)
    parser.add_argument('--back_versification', type=str, default='vers/back_versification.json')
    parser.add_argument('-a', '--auto_correct_threshold', type=float, default=None, help='value between 0.0 and1.0')
    args = parser.parse_args()

    # legacy calls
    if args.json and isinstance(args.json, str) and regex.search(r'scorecard/wildebeest\.json$', args.json):
        args.json_legacy_out = io.StringIO(args.json)
        args.json_legacy_out.name = args.json
        args.json = None
    if args.json_out_filename and isinstance(args.json_out_filename, str) and not regex.search(r'\.json$', args.json_out_filename):
        args.legacy_text_output = args.out_filename
        args.json_out_filename = None
    # default input from stdin
    if args.json is None and args.input is None and args.batch is None:
        args.input = sys.stdin
    # default output to stdout
    if args.json_out_filename is None and args.json_legacy_out is None and args.legacy_text_output is None:
        args.legacy_text_output = sys.stdout

    start_time = datetime.datetime.now()
    if args.verbose:
        log.info('Script: wb-analysis.py')
        log.info(f'Start: {start_time}')
        if args.input is not sys.stdin:
            log.info(f'Text input: {args.input.name}')
        if args.json_out_filename and (args.json_out_filename is not sys.stdout):
            log.info(f'JSON output: {args.out_filename.name}')
        if args.json_legacy_out:
            log.info(f'Legacy JSON output: {args.json_legacy_out.name}')
        if args.legacy_text_output and (args.legacy_text_output is not sys.stdout):
            log.info(f'Legacy text output: {args.legacy_text_output.name}')
    bv = BackVersification(args.back_versification, False)
    if args.batch:
        directory_str = args.batch
        directory_path = Path(directory_str)
        args.batch = None
        if args.ref_id_file:
            sys.stderr.write(f'Load ref {args.ref_id_file}\n')
            args.snt_index_to_ref_id = {}
            WildebeestAnalysis.load_ref_ids(args.snt_index_to_ref_id, args.ref_id_file)
        files = list(Path(directory_path).glob('*.txt'))
        files.sort()
        n_files = 0
        for file in files:
            filename = file.name
            if file.is_file() and filename.endswith('.txt'):
                n_files += 1
                args.input = file
                args.file_id = filename
                sys.stderr.write(f'{args.file_id}\n')
                process_args(args)
        if args.verbose:
            log.info(f"Processed {count_plus_noun(n_files, 'file')}")
    else:
        wb_ana = process_args(args)
        if args.ref_id_file:
            wb_ana.load_ref_ids(wb_ana.snt_index_to_ref_id, args.ref_id_file)
        if args.html_output_filename:
            wb_pp.main_with_args(args, wb_ana)
    sys.stderr.write(bv.report_stats())
    if args.verbose:
        end_time = datetime.datetime.now()
        log.info(f'End: {end_time}')
        elapsed_time = end_time - start_time
        log.info(f'Time: {elapsed_time}')


def version():
    return WildebeestAnalysis.populate_version()


if __name__ == "__main__":
    main()

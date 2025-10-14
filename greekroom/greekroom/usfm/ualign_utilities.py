#!/usr/bin/env python3

# This file contains a few utilities, taken from script ualign.py
# Classes: BibleUtilities, DocumentConfiguration, ScriptDirection, BibleRefSpan, DataManager

from __future__ import annotations
from collections import defaultdict
import json
import math
import os
from pathlib import Path
import regex
import sys
from typing import List, Optional, Tuple
import unicodedata as ud


def guard_html(s, exceptions: List[str] | None = None):
    # for exception "/a", don't guard if string includes </a> etc.
    if exceptions:
        for exception in exceptions:
            if f"<{exception}>" in s:
                return s
    s = regex.sub('&', '&amp;', s)
    s = regex.sub('<', '&lt;', s)
    s = regex.sub('>', '&gt;', s)
    s = regex.sub('"', '&quot;', s)
    s = regex.sub("'", '&apos;', s)
    return s


def guard_html_rtl(s):
    if ScriptDirection.string_is_right_to_left(s):
        return '&#x2067' + guard_html(s) + '&#x2069'
    else:
        return guard_html(s)


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


def robust_round(x, n: int | None = None):
    try:
        return round(x, n)
    except TypeError:
        return x


def integers_are_consecutive(integer_list: List[int]) -> bool:
    prev_int = None
    for i in integer_list:
        if prev_int is None or i == prev_int + 1:
            prev_int = i
        else:
            return False
    return True


class DataManager:
    @staticmethod
    def html_title_guard(s: str) -> str:
        s = s.replace(' ', '&nbsp;')
        s = s.replace('-', '\u2011')
        s = s.replace('&#xA;', ' ')
        return s

    @staticmethod
    def html_title_unguard(s: str) -> str:
        s = s.replace(' ', '&#xA;')
        s = s.replace('\u2011', '-')
        s = s.replace('&nbsp;', ' ')
        return s

    @staticmethod
    def read_file(filename: str, d: dict, selectors: List[str] | None = None) -> None:
        n_entries = 0
        with open(filename) as f:
            for line in f:
                if line.startswith('#'):
                    continue
                if regex.match(r'^\s*$', line):   # blank line
                    continue
                line = regex.sub(r'\s{2,}#.*$', '', line)   # remove comments
                lang_code = slot_value_in_double_colon_del_list(line, 'lc')
                if lang_code and (selectors is None or ('owl' in selectors)):
                    legit_duplicate = slot_value_in_double_colon_del_list(line, 'legitimate-duplicate')
                    romanization = slot_value_in_double_colon_del_list(line, 'rom')
                    gloss_clause = slot_value_in_double_colon_del_list(line, 'gloss')
                    eng_gloss = slot_value_in_single_colon_del_list(gloss_clause, 'eng')
                    if legit_duplicate:
                        n_entries += 1
                        # d[('hin','legitimate-duplicate','जब जब')] == {'gloss': {'eng': 'whatever'}, 'rom': 'jab jab'}
                        gloss_dict = {}
                        if eng_gloss:
                            gloss_dict['eng'] = eng_gloss
                        ld_dict = {'gloss': gloss_dict}
                        if romanization:
                            ld_dict['rom'] = romanization
                        d[(lang_code, 'legitimate-duplicate', legit_duplicate)] = ld_dict
                        if d.get((lang_code, 'legitimate-duplicates')) is None:
                            d[(lang_code, 'legitimate-duplicates')] = []
                        d[(lang_code, 'legitimate-duplicates')].append(legit_duplicate)
        selector_clause = (" " + "/".join(selectors)) if selectors else ""
        sys.stderr.write(f'Read {n_entries}{selector_clause} entries from {filename}\n')


class BibleRef:
    def __init__(self, book_id: str | None = None, chapter: int | None = None, verse: int | None = None,
                 sub_verse: str | None = None, txt: str | None = None, ref_br: BibleRef | None = None):
        # print("BibleRef in:", book_id, chapter, verse, sub_verse, txt, ref_br)
        self.valid = True
        if txt:  # parse from "GEN 1:2"
            if m := regex.match(r'([1-4A-Z][A-Z][A-Z]|S3Y|PS2|)\s*(\d+|)([.:,]\d+|)([ab]|)$',
                                txt, flags=regex.IGNORECASE):
                book_id, chapter_s, verse_with_punct, sub_verse = m.group(1, 2, 3, 4)
                if book_id:
                    self.book_id = book_id
                elif ref_br:
                    self.book_id = ref_br.book_id
                if ref_br and regex.match(r'\s*\d+\s*$', txt):
                    self.sub_verse = None
                    if ref_br.chapter and ref_br.verse:
                        self.chapter = ref_br.chapter
                        self.verse = int(txt.strip())
                    elif ref_br.chapter:
                        self.chapter = int(txt.strip())
                        self.verse = None
                    else:
                        self.valid = False
                else:
                    self.chapter = int(chapter_s) if chapter_s else None
                    verse_s = regex.sub(r'\pP', '', verse_with_punct) if verse_with_punct else ''
                    self.verse = int(verse_s) if verse_s else None
                    self.sub_verse = sub_verse
            else:
                self.valid = False
        else:  # structured input
            self.book_id = book_id  # e.g. "GEN"
            self.chapter = chapter  # starting with 1
            self.verse = verse      # starting with 1
            self.sub_verse = sub_verse  # rare, e.g. "a"
        # print("BibleRef out:", self.valid, self.book_id, self.chapter, self.verse, self.sub_verse)

    def pprint(self, skip_book_id: bool = False, skip_chapter: bool = False) -> str:
        # return "JHN 3:16", "LUK 2" etc.
        result = ""
        if not self.valid:
            return "_INVALID_"
        if self.book_id and not skip_book_id:
            result = self.book_id
        if result and (self.chapter or self.verse):
            result += ' '
        if self.chapter and self.verse and not skip_chapter:
            result += f"{self.chapter}:{self.verse}"
        elif self.chapter and not skip_chapter:
            if result or skip_book_id:
                result += str(self.chapter)
            else:
                result = f"ch.{self.chapter}"
        elif self.verse:
            if not skip_chapter:
                result += 'v.'
            result += str(self.verse)
        if self.sub_verse:
            if self.verse:
                result += self.sub_verse
            else:
                result += (" " if result else "") + f"sv.{self.verse}"
        return result

    def __str__(self) -> str:
        return self.pprint()

    def __repr__(self) -> str:
        return self.pprint()


class BibleRefSpan:
    def __init__(self, txt: str | None = None, map_dict: dict[str] | None = None):
        self.spans: list[tuple[BibleRef, BibleRef]] = []
        self.valid = True
        if txt:
            if map_dict:
                for s in sorted(map_dict.keys(), key=lambda x: -len(x)):
                    txt = regex.sub(s, map_dict[s], txt)
            if m := regex.match(r'\s*(\S.*?)(\d+(?:,\d+)+)', txt):
                verse_numbers = [int(x) for x in regex.findall(r'\d+', m[2])]
                if integers_are_consecutive(verse_numbers):
                    # change GEN 1:2,3,4 -> GEN 1:2-4
                    txt = f"{m[1]}{verse_numbers[0]}-{verse_numbers[-1]}"
            if m1 := regex.match(r'\s*(\S.*\S|\S)\s*(-|–|—|_AND_|_TO_)\s*(\S.*\S|\S)\s*$', txt):
                br1_s, connector, br2_s = m1.group(1, 2, 3)
                br1 = BibleRef(txt=br1_s)
                br2 = BibleRef(txt=br2_s, ref_br=(br1 if br1.valid else None))
                if br1.valid and br2.valid:
                    if connector in ('_AND_', ):
                        self.spans.extend([(br1, br1), (br2, br2)])
                    else:
                        self.spans.append((br1, br2))
            else:
                br1 = BibleRef(txt=txt)
                if br1.valid:
                    self.spans.append((br1, br1))
                else:
                    self.valid = False
        else:
            self.valid = False

    def add(self, br1: BibleRef, br2: BibleRef | None = None) -> BibleRefSpan:
        self.spans.append((br1, br2 or br1))
        return self

    def contains(self, sub_br: BibleRefSpan) -> bool:
        max_int = 999
        if not self.valid:
            return False
        for span in self.spans:
            br1, br2 = span
            found_sub_span = False
            for sub_span in sub_br.spans:
                sub_br1, sub_br2 = sub_span
                if ((sub_br1.book_id in (br1.book_id, br2.book_id))
                        and (sub_br2.book_id in (br1.book_id, br2.book_id))
                        and ((br1.chapter or 1) <= (sub_br1.chapter or 1))
                        and ((sub_br2.chapter or max_int) <= (br2.chapter or max_int))
                        and (((br1.chapter or 1) < (sub_br1.chapter or 1))
                             or ((br1.verse or 1) <= (sub_br1.verse or 1)))
                        and (((sub_br2.chapter or max_int) < (br2.chapter or max_int))
                             or ((sub_br2.verse or max_int) <= (br2.verse or max_int)))):
                    found_sub_span = True
                    break
            if not found_sub_span:
                return False
        return True

    def __str__(self) -> str:
        result = ''
        prev_book_id, prev_chapter, prev_verse = None, None, None
        for span in self.spans:
            br1, br2 = span
            skip_book_id, skip_chapter = False, False
            if prev_book_id == br2.book_id:
                skip_book_id = True
                if prev_chapter == br2.chapter:
                    skip_chapter = True
            if result:
                if (prev_book_id == br2.book_id) and (prev_chapter == br2.chapter):
                    result += ','
                else:
                    result += '; '
            result += br1.pprint(skip_book_id=skip_book_id, skip_chapter=skip_chapter)
            if br1 != br2:
                if br1.book_id == br2.book_id:
                    if br1.chapter == br2.chapter:
                        if br1.verse == br2.verse:
                            pass
                        else:
                            skip_book_id, skip_chapter = True, True
                            result += "-" + br2.pprint(skip_book_id=skip_book_id, skip_chapter=skip_chapter)
                    else:
                        skip_book_id = True
                        result += "–" + br2.pprint(skip_book_id=skip_book_id)
                else:
                    result += "—" + str(br2)
            prev_book_id, prev_chapter, prev_verse = br1.book_id, br1.chapter, br1.verse
        return result


class BibleUtilities:
    # For books and their standard abbreviations, see doc at https://ubsicap.github.io/usfm/identification/books.html
    def __init__(self, config_dirs: list[str] | None = None):
        self.ot_books = ('GEN', 'EXO', 'LEV', 'NUM', 'DEU', 'JOS', 'JDG', 'RUT', '1SA', '2SA',
                         '1KI', '2KI', '1CH', '2CH', 'EZR', 'NEH', 'EST', 'JOB', 'PSA', 'PRO',
                         'ECC', 'SNG', 'ISA', 'JER', 'LAM', 'EZK', 'DAN', 'HOS', 'JOL', 'AMO',
                         'OBA', 'JON', 'MIC', 'NAM', 'HAB', 'ZEP', 'HAG', 'ZEC', 'MAL')
        self.nt_books = ('MAT', 'MRK', 'LUK', 'JHN', 'ACT', 'ROM', '1CO', '2CO', 'GAL', 'EPH',
                         'PHP', 'COL', '1TH', '2TH', '1TI', '2TI', 'TIT', 'PHM', 'HEB', 'JAS',
                         '1PE', '2PE', '1JN', '2JN', '3JN', 'JUD', 'REV')
        self.ap_books = ('TOB', 'JDT', 'ESG', 'WIS', 'SIR', 'BAR', 'LJE', 'S3Y', 'SUS', 'BEL',
                         '1MA', '2MA', '3MA', '4MA', '1ES', '2ES', 'MAN', 'PS2', 'ODA', 'PSS')
        self.other_texts = ('XXB', 'XXC', 'XXD', 'XXE', 'XXF', 'FRT', 'BAK', 'OTH', 'INT', 'GLO')
        self.all_books = self.ot_books + self.nt_books + self.ap_books
        self.all_books_by_section = (('Old Testament', self.ot_books),
                                     ('New Testament', self.nt_books),
                                     ('Apocrypha', self.ap_books))
        self.max_n = defaultdict(int)  # key: ('GEN') ir ('GEN', 3)
        # Often omitted verses
        # cf. https://en.wikipedia.org/wiki/List_of_New_Testament_verses_not_included_in_modern_English_translations
        self.often_omitted_verses = [
            "MAT 12:47", "MAT 17:21", "MAT 18:11", "MAT 23:14",
            "MRK 7:16", "MRK 9:44", "MRK 9:46", "MRK 11:26", "MRK 15:28",
            "LUK 17:36", "LUK 23:17",
            "JHN 5:4",
            "ACT 8:37", "ACT 15:34", "ACT 24:7", "ACT 28:29",
            "ROM 16:24"]
        self.often_omitted_verses_note = \
            (f"A certain few verses are absent from many modern Bible translations"
             f" as they are not part of some of the oldest Bible manuscripts."
             f"  Some Biblical scholars hold that such verses have been added later,"
             f" often drawing from other parts of the Bible.  ({', '.join(self.often_omitted_verses)})")
        self.book_to_book_number = {}
        for i in range(len(self.ot_books)):
            self.book_to_book_number[self.ot_books[i]] = i + 1  # GEN -> 1, MAL -> 39
        for i in range(len(self.nt_books)):
            self.book_to_book_number[self.nt_books[i]] = i + 41  # MAT -> 41, REV -> 67
        for i in range(len(self.ap_books)):
            self.book_to_book_number[self.ap_books[i]] = i + 68  # TOB -> 68, PSS -> 87
        self.verse_properties = defaultdict(dict)
        if config_dirs:
            self.build_bible_verse_props(config_dirs)

    @staticmethod
    def combine_vref_start_end(snt_id1: str, snt_id2: str, default: None | str = 'first-last') -> str | None:
        if snt_id1 == snt_id2:
            return snt_id1
        # Bible format: "GEN 1:10" + "GEN 1:20" -> "GEN 1:10-20"
        m1 = regex.search(r'([A-Z1-3][A-Z][A-Z])\s+(\d+):(\d+[ab]?)$', snt_id1)
        m2 = regex.search(r'([A-Z1-3][A-Z][A-Z])\s+(\d+):(\d+[ab]?)$', snt_id2)
        if m1 and m2:
            if m1.group(1) == m2.group(1):
                if m1.group(2) == m2.group(2):
                    return f'{m1.group(1)} {m1.group(2)}:{m1.group(3)}-{m2.group(3)}'
                else:
                    return f'{m1.group(1)} {m1.group(2)}:{m1.group(3)}-{m2.group(2)}:{m2.group(3)}'
            return f"{snt_id1}-{snt_id2}"
        if default == 'first-last':
            return f"{snt_id1}-{snt_id2}"
        else:
            return None

    @staticmethod
    def split_vref_start_end(snt_id_span: str) -> Tuple[str, str] | None:
        # Bible format "GEN 1:10-20" -> "GEN 1:10", "GEN 1:20"
        if m := regex.match(r'([A-Z1-3][A-Z][A-Z])\s+(\d+):(\d+[ab]?)-(\d+[ab]?)$', snt_id_span):
            return f'{m.group(1)} {m.group(2)}:{m.group(3)}', f'{m.group(1)} {m.group(2)}:{m.group(4)}'
        elif m := regex.match(r'([A-Z1-3][A-Z][A-Z])\s+(\d+):(\d+[ab]?)-(\d+):(\d+[ab]?)$', snt_id_span):
            return f'{m.group(1)} {m.group(2)}:{m.group(3)}', f'{m.group(1)} {m.group(4)}:{m.group(5)}'
        elif m := regex.match(r'([A-Z1-3][A-Z][A-Z])\s+(\d+):(\d+[ab]?)-([A-Z1-3][A-Z][A-Z])\s+(\d+):(\d+[ab]?)$',
                              snt_id_span):
            return f'{m.group(1)} {m.group(2)}:{m.group(3)}', f'{m.group(4)} {m.group(5)}:{m.group(6)}'
        else:
            return None

    def register_verse(self, side: str, book_id: str, chapter: int, verse: int | None, token_pos: int | None) -> None:
        if chapter:
            self.max_n[(side, book_id)] = max(self.max_n[(side, book_id)], chapter)
            if verse:
                self.max_n[(side, book_id, chapter)] = max(self.max_n[(side, book_id, chapter)], verse)
                if token_pos is not None:
                    self.max_n[(side, book_id, chapter, verse)] \
                        = max(self.max_n[(side, book_id, chapter, verse)], token_pos)

    @staticmethod
    def book_chapter_verse(snt_id) -> str | None:
        return m.group(1, 2, 3) \
            if (m := regex.search(r'([A-Z1-3][A-Z][A-Z])\s+(\d+):(\d+[ab]?(?:-\d+[ab]?)?)$', snt_id)) \
            else None

    @staticmethod
    def book(snt_id) -> str | None:
        return m.group(1) if (m := regex.search(r'([A-Z1-3][A-Z][A-Z])\s+(\d+):(\d+[ab]?)$', snt_id)) else None

    @staticmethod
    def chapter(snt_id) -> str | None:
        return m.group(2) if (m := regex.search(r'([A-Z1-3][A-Z][A-Z])\s+(\d+):(\d+[ab]?)$', snt_id)) else None

    @staticmethod
    def verse(snt_id) -> str | None:
        return m.group(3) if (m := regex.search(r'([A-Z1-3][A-Z][A-Z])\s+(\d+):(\d+[ab]?)$', snt_id)) else None

    def load_bible_verse_props(self, filename: str | Path) -> int:
        """Returns True for success"""
        try:
            f = open(filename)
        except FileNotFoundError:
            sys.stderr.write(f"Did not find Bible verse property file {filename}\n")
            return 0
        else:
            n_entries = 0
            for line in f:
                try:
                    load_d = json.loads(line)
                except json.decoder.JSONDecodeError:
                    sys.stderr.write(f"JSON could not decode {line.strip()}\n")
                    continue
                snt_id: str = load_d.get('verse')
                if snt_id:
                    verse_property = self.verse_properties[snt_id]
                    found_at_least_one_values = False
                    for key in ("absent-from-many-manuscripts", "eng", "cross-ref"):
                        if value := load_d.get(key):
                            verse_property[key] = value
                            found_at_least_one_values = True
                    if found_at_least_one_values:
                        n_entries += 1
            f.close()
            sys.stderr.write(f"Loaded {n_entries} entries from {filename}\n")
            # sys.stderr.write(f"  {self.verse_properties}\n")
            return n_entries

    def build_bible_verse_props(self, config_dirs: list[str] | None = None):
        if not config_dirs:
            cwd_path = Path(os.getcwd())
            config_dirs = [cwd_path, cwd_path.parent]
        success_reading_bible_verse_props = False
        for directory in config_dirs:
            filename = Path(os.path.join(directory, 'BibleVerseProps.jsonl'))
            if os.path.exists(filename):
                if self.load_bible_verse_props(filename):
                    success_reading_bible_verse_props = True
                    break
        if not success_reading_bible_verse_props:
            sys.stderr.write(f"Did not find 'BibleVerseProps.jsonl' in any of the directories: {config_dirs}\n")


class ScriptDirection:
    def __init__(self, lang_code: str | None = None, lang_name: str | None = None, text: str | None = None):
        self.lang_code = lang_code
        self.lang_name = lang_name
        self.bidirectional_class_counts = defaultdict(int)
        self.direction = None  # "left-to-right" or "right-to-left"
        self.monitor = False
        if text:
            self.add_stats(text)

    def add_stats(self, text: str, count: int = 1, loc: int | str | None = None) -> None:
        if text not in (None, 'NULL'):
            for c in text:
                bidirectional_class = ud.bidirectional(c)
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

    def report(self, details: bool = False) -> str:
        message = f"Determined script direction for {self.lang_name or self.lang_code} to be "
        message += self.determine_direction()  # "left-to-right" or "right-to-left"
        if details:
            message += " with character direction counts "
            n_ltr, n_rtl = self.direction_class_counts()
            message += (f"{n_rtl}:{n_ltr}" if self.is_right_to_left() else f"{n_ltr}:{n_rtl}") + " in favor."
        return message + "\n"

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


class DocumentConfiguration:
    def __init__(self, config_filename: Path | None = None, args=None):
        self.doc_dict = {}
        self.lang_name_to_code = {}
        self.lang_code_to_name = {}
        self.config_dirs = args.config_dirs if args else []
        self.ref_words = {}
        self.book_refs = {}
        if config_filename:
            self.read_config_file(config_filename)

    def read_config_file(self, config_filename: Path):
        with open(config_filename) as f:
            line_number = 0
            n_lang_code_entries, n_lang_name_entries, n_id_entries, n_ref_word_entries = 0, 0, 0, 0
            for line in f:
                line_number += 1
                if line.strip() == '':
                    continue  # ignore empty line
                try:
                    d = json.loads(line)
                except json.decoder.JSONDecodeError as error:
                    sys.stderr.write(f'Error: {config_filename} line {line_number}: {error}\n')
                    continue
                doc_conf_id = d.get('id')
                lang_code = d.get('lc')
                lang_name = d.get('lang')
                ref_words = d.get('ref-words')
                book_refs = d.get('book-refs')
                if lang_code and ref_words:
                    if self.ref_words.get(lang_code):
                        sys.stderr.write(f'Ignoring entry with duplicate ref-words for {lang_code} '
                                         f'in {config_filename} line {line_number}\n')
                    else:
                        self.ref_words[lang_code] = ref_words
                elif lang_code and book_refs:
                    if self.book_refs.get(lang_code):
                        sys.stderr.write(f'Ignoring entry with duplicate book-refs for {lang_code} '
                                         f'in {config_filename} line {line_number}\n')
                    else:
                        self.book_refs[lang_code] = book_refs
                elif doc_conf_id:
                    n_id_entries += 1
                    if self.doc_dict.get(doc_conf_id, None):
                        sys.stderr.write(f'Ignoring entry with duplicate ID {doc_conf_id} '
                                         f'in {config_filename} line {line_number}\n')
                    else:
                        self.doc_dict[doc_conf_id] = d
                elif n_id_entries:
                    sys.stderr.write(f'Ignoring entry with missing ID {doc_conf_id} '
                                     f'in {config_filename} line {line_number}\n')
                if lang_code and lang_name:
                    existing_code = self.lang_name_to_code.get(lang_name, None)
                    if existing_code and (existing_code != lang_code):
                        sys.stderr.write(f'Ignoring conflicting new mapping {lang_name} '
                                         f'to {lang_code} ({existing_code}) in {config_filename} line {line_number}\n')
                    else:
                        self.lang_name_to_code[lang_name] = lang_code
                        n_lang_name_entries += 1
                    existing_name = self.lang_code_to_name.get(lang_code, None)
                    if existing_name and (existing_name != lang_name):
                        sys.stderr.write(f'Ignoring conflicting new mapping {lang_code} to {lang_name}'
                                         f' ({existing_name}) in {config_filename} line {line_number}\n')
                    else:
                        self.lang_code_to_name[lang_code] = lang_name
                        n_lang_code_entries += 1
        sys.stderr.write(f'Loaded {n_lang_code_entries}/{n_lang_name_entries} '
                         f'lang code/name entries from {config_filename}\n')

    def read_config_files_in_dirs(self, directories: list[str]):
        for directory in directories:
            for file in os.listdir(directory):
                if file.endswith("Config.jsonl"):
                    self.read_config_file(Path(os.path.join(directory, file)))

    # noinspection SpellCheckingInspection
    def langname_to_langcode(self, lang_name) -> str | None:
        if lang_code := self.lang_name_to_code.get(lang_name):
            return lang_code
        lang_name2 = regex.sub(r'^\S+\s+', '', lang_name)  # skip 1st component (e.g. "OV Tamil" -> "Tamil")
        if lang_code := self.lang_name_to_code.get(lang_name2):
            return lang_code
        lang_name3 = regex.sub(r'\s+\S+$', '', lang_name)  # skip last component (e.g. "Tamil OV" -> "Tamil")
        if lang_code := self.lang_name_to_code.get(lang_name3):
            return lang_code
        return None

    # noinspection SpellCheckingInspection
    def langcode_to_langname(self, lang_code) -> str:
        return self.lang_code_to_name.get(lang_code)


def slot_value_in_double_colon_del_list(line: str, slot: str, default: Optional = None) -> str:
    """For a given slot, e.g. 'cost', get its value from a line such as '::s1 of course ::s2 ::cost 0.3' -> 0.3
    The value can be an empty string, as for ::s2 in the example above."""
    m = regex.match(fr'(?:.*\s)?::{slot}(|\s+\S.*?)(?:\s+::\S.*|\s*)$', line)
    return m.group(1).strip() if m else default


def slot_value_in_single_colon_del_list(line: str, slot: str, default: Optional = None) -> str:
    if line:
        m = regex.match(fr'(?:.*\s)?:{slot}(|\s+\S.*?)(?:\s+:\S.*|\s*)$', line)
        return m.group(1).strip() if m else default
    else:
        return default

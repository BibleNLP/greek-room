#!/usr/bin/env python3

from collections import defaultdict
import sys
import re
import regex
# from typing import IO, TextIO, Tuple, List
from typing import Optional
import unicodedata as ud
import unicodeblock.blocks


class UnicodeUtilities:
    def __init__(self):
        self.char_to_block_dict = defaultdict(str)
        self.unicode_block_to_script_dict = defaultdict(str)
        self.char_to_script_dict = defaultdict(str)
        self.suspicious_characters = set()
        self.populate_char_to_block_dict()
        self.invisible_characters = {'\u200B',   # ZERO WIDTH SPACE
                                     '\u200C',   # ZERO WIDTH NON JOINER
                                     '\u200D',   # ZERO WIDTH JOINER
                                     '\u200E',   # LEFT-TO-RIGHT MARK
                                     '\u200F',   # RIGHT-TO-LEFT MARK
                                     '\u200F',   # RIGHT-TO-LEFT MARK
                                     '\uFEFF'}   # ZERO WIDTH NO-BREAK SPACE/BYTE ORDER MARK
        self.char_to_name_dict = {
            '\0': 'NULL',
            '': 'START OF HEADING',
            '': 'START OF TEXT',
            '': 'END OF TEXT',
            '': 'END OF TRANSMISSION',
            '': 'ENQUIRY',
            '': 'ACKNOWLEDGE',
            '': 'BELL',
            '': 'BACKSPACE',
            '\t': 'TAB',
            '\n': 'LINE FEED',
            '\x0B': 'LINE TABULATION',
            '\x0C': 'FORM FEED',
            '\r': 'CARRIAGE RETURN',
            '': 'SHIFT OUT',
            '': 'SHIFT IN',
            '': 'DATA LINK ESCAPE',
            '': 'DEVICE CONTROL ONE',
            '': 'DEVICE CONTROL TWO',
            '': 'DEVICE CONTROL THREE',
            '': 'DEVICE CONTROL FOUR',
            '': 'NEGATIVE ACKNOWLEDGE',
            '': 'SYNCHRONOUS IDLE',
            '': 'END OF TRANSMISSION BLOCK',
            '': 'CANCEL',
            '': 'END OF MEDIUM',
            '': 'SUBSTITUTE',
            '': 'ESCAPE',
            '': 'INFORMATION SEPARATOR FOUR',
            '': 'INFORMATION SEPARATOR THREE',
            '': 'INFORMATION SEPARATOR TWO',
            '':  'INFORMATION SEPARATOR ONE',
            '': 'DELETE',
            '':   'PADDING CHARACTER (W1252: Euro Sign)',
            '': 'HIGH OCTET PRESET',
            '': 'BREAK PERMITTED HERE (W1252: Single Low-9 Quotation Mark)',
            '': 'NO BREAK HERE (W1252: Latin Small Letter F With Hook)',
            '': 'INDEX (W1252: Double Low-9 Quotation Mark)',
            '': 'NEXT LINE (W1252: Horizontal Ellipsis)',
            '': 'START OF SELECTED AREA (W1252: Dagger)',
            '': 'END OF SELECTED AREA (W1252: Double Dagger)',
            '': 'CHARACTER TABULATION SET (W1252: Modifier Letter Circumflex Accent)',
            '': 'CHARACTER TABULATION WITH JUSTIFICATION (W1252: Per Mille Sign)',
            '': 'LINE TABULATION SET (W1252: Latin Capital Letter S With Caron)',
            '': 'PARTIAL LINE FORWARD (W1252: Single Left-Pointing Angle Quotation Mark)',
            '': 'PARTIAL LINE BACKWARD (W1252: Latin Capital Ligature OE)',
            '': 'REVERSE LINE FEED',
            '': 'SINGLE SHIFT TWO (W1252: Latin Capital Letter Z With Caron)',
            '': 'SINGLE SHIFT THREE',
            '': 'DEVICE CONTROL STRING',
            '': 'PRIVATE USE ONE (W1252: Left Single Quotation Mark)',
            '': 'PRIVATE USE TWO (W1252: Right Single Quotation Mark)',
            '': 'SET TRANSMIT STATE (W1252: Left Double Quotation Mark)',
            '': 'CANCEL CHARACTER (W1252: Right Double Quotation Mark)',
            '': 'MESSAGE WAITING (W1252: Bullet)',
            '': 'START OF GUARDED AREA (W1252: En Dash)',
            '': 'END OF GUARDED AREA (W1252: Em Dash)',
            '': 'START OF STRING (W1252: Small Tilde)',
            '': 'SINGLE GRAPHIC CHARACTER INTRODUCER (W1252: Trade Mark Sign)',
            '': 'SINGLE CHARACTER INTRODUCER (W1252: Latin Small Letter S With Caron)',
            '': 'CONTROL SEQUENCE INTRODUCER (W1252: Single Right-Pointing Angle Quotation Mark)',
            '': 'STRING TERMINATOR (W1252: Latin Small Ligature OE)',
            '': 'OPERATING SYSTEM COMMAND',
            '': 'PRIVACY MESSAGE (W1252: Latin Small Letter Z With Caron)',
            '': 'APPLICATION PROGRAM COMMAND (W1252: Latin Capital Letter Y With Diaeresis)',
            '﻿': 'ZERO WIDTH NO-BREAK SPACE (BYTE ORDER MARK)'
        }
        self.char_to_block_dict = defaultdict(str)
        self.unicode_block_to_script_dict = defaultdict(str)
        self.char_to_script_dict = defaultdict(str)
        self.char_script_dict = {}
        self.build_char_to_script_dict()


    def set_new_char_to_block_dict_entry(self, c: str | int, block_name: str):
        """Set block_name for given character. Do not overwrite any previous value."""
        char = chr(c) if isinstance(c, int) else c
        if not self.char_to_block_dict.get(char):
            self.char_to_block_dict[char] = block_name

    def populate_char_to_block_dict(self):
        """Set block_name for characters (that differ from unicodedata block names)."""
        for char in '⁰¹²³⁴⁵⁶⁷⁸⁹':
            self.set_new_char_to_block_dict_entry(char, 'SUPERSCRIPT_DIGIT')
        for char in '₀₁₂₃₄₅₆₇₈₉':
            self.set_new_char_to_block_dict_entry(char, 'SUBSCRIPT_DIGIT')
        for char in 'ªº':
            self.set_new_char_to_block_dict_entry(char, 'SUPERSCRIPTS_AND_SUBSCRIPTS')
        for char in '               ፡':
            self.set_new_char_to_block_dict_entry(char, 'SPACE')
        for char in '­​‌‍﻿':
            self.set_new_char_to_block_dict_entry(char, 'ZERO_WIDTH')
        for char in '‏‎':
            self.set_new_char_to_block_dict_entry(char, 'DIRECTIONAL')
        for char in '$¢£¤¥':
            self.set_new_char_to_block_dict_entry(char, 'CURRENCY_SYMBOLS')
        # noinspection SpellCheckingInspection
        for char in "ʌɓɗɖɛəɡɠɨᵻɟᴋɫɲⁿɔɵᵽɹʃʉʋʊʒɣɩʔ":
            self.set_new_char_to_block_dict_entry(char, 'LATIN')
        self.set_new_char_to_block_dict_entry('ᵸ', 'CYRILLIC')
        # noinspection SpellCheckingInspection
        for char in "ᵉⁱᵏᵘ":
            self.set_new_char_to_block_dict_entry(char, 'LATIN_SUPERSCRIPT_LETTER')
        self.set_new_char_to_block_dict_entry('々', 'CJK')
        self.set_new_char_to_block_dict_entry('�', 'REPLACEMENT')
        for code_point in range(0x1D62, 0x1D66):
            self.set_new_char_to_block_dict_entry(code_point, 'LATIN_SUBSCRIPT_LETTER')
        for code_point in range(0x1C90, 0x1CC0):
            self.set_new_char_to_block_dict_entry(code_point, 'GEORGIAN')
        for code_point in range(0x2D00, 0x2D30):
            self.set_new_char_to_block_dict_entry(code_point, 'GEORGIAN')
        for code_point in range(0xFB00, 0xFB10):
            self.set_new_char_to_block_dict_entry(code_point, 'LATIN_ALPHABETIC_PRESENTATION_FORMS')
        for code_point in range(0xFB10, 0xFB20):
            self.set_new_char_to_block_dict_entry(code_point, 'ARMENIAN_ALPHABETIC_PRESENTATION_FORMS')
        for code_point in range(0xFB20, 0xFB4F):
            self.set_new_char_to_block_dict_entry(code_point, 'HEBREW_ALPHABETIC_PRESENTATION_FORMS')
        for code_point in range(0x00, 0x20):
            self.set_new_char_to_block_dict_entry(code_point, 'C0_CONTROL')
        self.set_new_char_to_block_dict_entry(0x7F, 'C0_CONTROL')
        for code_point in range(0x80, 0xA0):
            self.set_new_char_to_block_dict_entry(code_point, 'C1_CONTROL')
            self.suspicious_characters.add(chr(code_point))
        for code_point in range(0x21, 0x07F):
            if regex.match(r'(?:\pP|\pS)', chr(code_point)):
                self.set_new_char_to_block_dict_entry(code_point, 'ASCII_PUNCTUATION')
        for code_point in range(0x30, 0x03A):
            self.set_new_char_to_block_dict_entry(code_point, 'ASCII_DIGIT')
        for code_point in range(0x0660, 0x066A):
            self.set_new_char_to_block_dict_entry(code_point, 'ARABIC_INDIC_DIGIT')
        for code_point in range(0x06F0, 0x06FA):
            self.set_new_char_to_block_dict_entry(code_point, 'EXTENDED_ARABIC_INDIC_DIGIT')
        for code_point in range(0xBC, 0xBF):
            self.set_new_char_to_block_dict_entry(code_point, 'VULGAR_FRACTION')
        for code_point in range(0x2150, 0x2160):
            self.set_new_char_to_block_dict_entry(code_point, 'VULGAR_FRACTION')
        self.set_new_char_to_block_dict_entry('↉', 'VULGAR_FRACTION')
        for code_point in range(0x2160, 0x2180):
            self.set_new_char_to_block_dict_entry(code_point, 'ROMAN_NUMERAL')
        self.set_new_char_to_block_dict_entry('ↄ', 'ARCHAIC_CLAUDIAN_LETTER')
        for code_point in range(0x2180, 0x2189):
            self.set_new_char_to_block_dict_entry(code_point, 'ARCHAIC_ROMAN_NUMERAL')
        for code_point in range(0x218A, 0x218C):
            self.set_new_char_to_block_dict_entry(code_point, 'TURNED_DIGIT')
        for code_point in range(0xA1, 0x0100):
            if regex.match(r'(?:\pP|\pS)', chr(code_point)):
                self.set_new_char_to_block_dict_entry(code_point, 'GENERAL_PUNCTUATION')
        for code_point in range(0x16F00, 0x16FA0):
            self.set_new_char_to_block_dict_entry(code_point, 'MIAO')
        for char in '،؍؛؞؟٪٭٫٬۔':
            self.set_new_char_to_block_dict_entry(char, 'ARABIC_PUNCTUATION')
        for char in '።፣፤፥፦፧':
            self.set_new_char_to_block_dict_entry(char, 'ETHIOPIC_PUNCTUATION')
        for char in '。．、·，！？；：（）［］【】「」『』《》〈〉':
            self.set_new_char_to_block_dict_entry(char, 'CHINESE_PUNCTUATION')
        for char in '।॥':
            self.set_new_char_to_block_dict_entry(char, 'DEVANAGARI_PUNCTUATION')
        for char in '՜՝՞։՛':
            self.set_new_char_to_block_dict_entry(char, 'ARMENIAN_PUNCTUATION')
        self.set_new_char_to_block_dict_entry(0xB5, 'LETTERLIKE_SYMBOLS')  # micro sign

    @staticmethod
    def unicode_category(char) -> str:
        """Safe version of character to Unicode category. Example: 'a' -> 'Ll' (lowercase letter)"""
        try:
            unicode_cat = ud.category(char)
        except ValueError:
            unicode_cat = '_UNDEFINED_'
        return unicode_cat

    def unicode_name(self, char) -> str:
        """Safe version of character to Unicode name,
        which also includes locally defined names, e.g. for control characters.
        Example: 'a' -> 'LATIN SMALL LETTER A'"""
        if unicode_name := self.char_to_name_dict.get(char):
            return unicode_name
        try:
            unicode_name = ud.name(char)
        except ValueError:
            unicode_name = '_UNDEFINED_'
        return unicode_name

    def unicode_block(self, char) -> str:
        """Safe version of character to Unicode block, which also includes locally defined blocks.
        Example: 'a' -> 'BASIC_LATIN'"""
        if block_name := self.char_to_block_dict[char]:
            return block_name
        try:
            block_name = unicodeblock.blocks.of(char) or 'OTHER'
            if block_name == 'OTHER':
                code_point = ord(char)
                if 0x2B820 <= code_point <= 0x2CEA1:
                    block_name = 'CJK_UNIFIED_IDEOGRAPHS'
        except ValueError:
            block_name = '_UNDEFINED_'
        self.char_to_block_dict[char] = block_name
        return block_name

    def unicode_script(self, unicode_block: str, char: str) -> Optional[str]:
        """Maps character to script.
        Examples: 'a' -> 'LATIN', 'ä' -> 'LATIN' (collapses multiple Latin blocks to 'Latin')"""
        if unicode_block:
            if unicode_block == 'IPA_EXTENSIONS':
                if cached_unicode_script := self.char_to_script_dict[char]:
                    return cached_unicode_script
                unicode_name = self.unicode_name(char)
                if regex.match(r'LATIN (?:SMALL|CAPITAL) LETTER [A-Z] WITH (?:HOOK|STROKE)$',
                               unicode_name):
                    unicode_block = 'LATIN'
                    self.char_to_script_dict[char] = unicode_block
                    return unicode_block
            if cached_unicode_script := self.unicode_block_to_script_dict.get(unicode_block):
                return cached_unicode_script
            s = unicode_block
            s = re.sub(r'^Basic[-_ ]+', '', s, flags=re.IGNORECASE)
            s = re.sub(r'^Supplemental[-_ ]+', '', s, flags=re.IGNORECASE)
            s = re.sub(r'[-_ ]+Supplementary(?:[-_ ][A-Z])?$', '', s, flags=re.IGNORECASE)
            s = re.sub(r'[-_ ]+Additional(?:[-_ ][A-Z])?$', '', s, flags=re.IGNORECASE)
            s = re.sub(r'[-_ ]+Supplement(?:[-_ ][A-Z])?$', '', s, flags=re.IGNORECASE)
            s = re.sub(r'[-_ ]+Extended(?:[-_ ]Letter)?(?:[-_ ][A-Z])?$', '', s, flags=re.IGNORECASE)
            s = re.sub(r'[-_ ]+Extension(?:[-_ ][A-Z])?$', '', s, flags=re.IGNORECASE)
            s = re.sub(r'[-_ ]+(?:Alphabetic[-_ ]?)?Presentation[-_ ]?Forms(?:[-_ ][A-Z])?$',
                       '', s, flags=re.IGNORECASE)
            s = re.sub(r'(?:-[A-Z1-9])?$', '', s, flags=re.IGNORECASE)
            s = re.sub(r'^(ENCLOSED[-_ ]ALPHANUMERIC)$', r'\1S', s)
            s = re.sub(r'^([Ee]nclosed[-_ ][Aa]lphanumeric)$', r'\1s', s)
            if s in ('CJK_UNIFIED_IDEOGRAPHS', 'CJK_COMPATIBILITY_IDEOGRAPHS'):
                s = 'CJK'
            self.unicode_block_to_script_dict[unicode_block] = s
            return s
        else:
            return None

    def char_unicode_script(self, char: str) -> Optional[str]:
        if cached_result := self.char_script_dict.get(char):
            return cached_result
        unicode_block = self.unicode_block(char)
        unicode_script = self.unicode_script(unicode_block, char)
        self.char_script_dict[char] = unicode_script
        return unicode_script

    @staticmethod
    def unicode_form(s: str, default: Optional[str] = None) -> str:
        if ud.normalize('NFC', s) == s:
            return 'NFC'
        elif ud.normalize('NFD', s) == s:
            return 'NFD'
        elif ud.normalize('NFKC', s) == s:
            return 'NFKC'
        elif ud.normalize('NFKD', s) == s:
            return 'NFKD'
        else:
            return default

    @staticmethod
    def modified_unicode_script(unicode_cat: str, unicode_script: str) -> str:
        if unicode_script:
            if unicode_cat.startswith('M') and not regex.search(r'(?:MODIFIER|MARK|SELECTOR)',
                                                                unicode_script, regex.IGNORECASE):
                unicode_script += "_MODIFIERS"
            elif unicode_cat.startswith('P') and not regex.search(r'(?:PUNCT)', unicode_script):
                unicode_script += "_PUNCTUATION"
        return unicode_script

    def build_char_to_script_dict(self) -> None:
        for cp in range(0x20000):
            char = chr(cp)
            unicode_cat = self.unicode_category(char)
            unicode_block = self.unicode_block(char)
            unicode_script = self.unicode_script(unicode_block, char)
            unicode_script = self.modified_unicode_script(unicode_cat, unicode_script)
            if unicode_script:
                self.char_to_script_dict[char] = unicode_script


class TextCorpus:
    def __init__(self, snt_list: list[str] | None = None,
                 snt_id_list: list[str] | None = None,
                 unicode_util: UnicodeUtilities | None = None):
        self.unicode_util = unicode_util or UnicodeUtilities()
        self.snt_id_to_snt = {}
        self.counts = defaultdict(int)
        self.total_char_count = 0
        self.snt_count = 0
        if snt_list and snt_id_list:
            self.add_text_corpus(snt_list, snt_id_list)

    def __repr__(self):
        return f"<Object of type TextCorpus with sntCount={self.snt_count}>"

    def add_text_corpus(self, snt_list: list[str], snt_id_list: list[str]) -> None:
        for snt, snt_id in zip(snt_list, snt_id_list):
            self.new_line(snt, snt_id)
        # if self.total_char_count:
        #     sys.stderr.write(f'Loaded TextCorpus w/ {self.snt_count} lines and {self.total_char_count} chars\n')

    def update_stats(self, snt: str, _snt_id: str, weight: int = 1) -> None:
        for c in snt:
            self.counts[c] += weight
            self.total_char_count += weight
            if c.isdigit() and self.unicode_util:
                unicode_block = self.unicode_util.unicode_block(c)
                self.counts[unicode_block] += weight
        if snt:
            self.snt_count += weight

    def new_line(self, snt: str, snt_id: str | None) -> None:
        if snt_id:
            old_snt = self.snt_id_to_snt.get(snt_id)
            if snt != old_snt:
                if old_snt:
                    self.update_stats(old_snt, snt_id, -1)
                self.update_stats(snt, snt_id, 1)
                self.snt_id_to_snt[snt_id] = snt
        else:
            self.update_stats(snt, snt_id, 1)

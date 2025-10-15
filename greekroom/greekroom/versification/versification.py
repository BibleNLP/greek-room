#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# versification.py
# versification.py -i f_usfm.txt -j f_usfm_vref.txt
# versification.py -i f_usfm.txt -j f_usfm_vref.txt -o f_usfm_reversified.txt -t ../vref.txt

from __future__ import annotations
import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import regex
import sys
from typing import List, TextIO, Tuple
from greekroom.gr_utilities import general_util
from greekroom.usfm.ualign_utilities import BibleUtilities


class BibleStructure:
    """This class holds some Bible-specific data."""
    def __init__(self):
        self.books_by_section = {
            "Old Testament": ['GEN', 'EXO', 'LEV', 'NUM', 'DEU', 'JOS', 'JDG', 'RUT', '1SA', '2SA',
                              '1KI', '2KI', '1CH', '2CH', 'EZR', 'NEH', 'EST', 'JOB', 'PSA', 'PRO',
                              'ECC', 'SNG', 'ISA', 'JER', 'LAM', 'EZK', 'DAN', 'HOS', 'JOL', 'AMO',
                              'OBA', 'JON', 'MIC', 'NAM', 'HAB', 'ZEP', 'HAG', 'ZEC', 'MAL'],
            "New Testament": ['MAT', 'MRK', 'LUK', 'JHN', 'ACT', 'ROM', '1CO', '2CO', 'GAL', 'EPH',
                              'PHP', 'COL', '1TH', '2TH', '1TI', '2TI', 'TIT', 'PHM', 'HEB', 'JAS',
                              '1PE', '2PE', '1JN', '2JN', '3JN', 'JUD', 'REV'],
            "Apocrypha": ['TOB', 'JDT', 'ESG', 'WIS', 'SIR', 'BAR', 'LJE', 'S3Y', 'SUS', 'BEL',
                          '1MA', '2MA', '3MA', '4MA', '1ES', '2ES', 'MAN', 'PS2', 'ODA', 'PSS']
        }
        self.pseudo_books = ['XXA', 'XXB', 'XXC', 'XXD', 'XXE', 'XXF', 'FRT', 'BAK', 'OTH', 'INT', 'GLO']

        # concatenation of all books: ['GEN', 'EXO', ..., 'MAT', 'MRK', ..., 'TOB', 'JDT', ...]
        self.books = [book for sublist in self.books_by_section.values() for book in sublist]

        # Note that the Bible book sorting numbers skip 40 ('MAL' = 39; 'MAT' = 41)
        self.sorting_numbers = {}
        for bible_section, section_offset in (("Old Testament", 1), ("New Testament", 41), ("Apocrypha", 68)):
            for book_offset, book in enumerate(self.books_by_section[bible_section]):
                self.sorting_numbers[book] = section_offset + book_offset

        self.standard_versification_schemas = {
            "org": "Original",   # must be in first place as it is referenced by the others
            "eng": "English",
            "rsc": "Russian Protestant",
            "rso": "Russian Orthodox",
            "vul": "Vulgate",
            "lxx": "Septuagint"
        }

        # https://en.wikipedia.org/wiki/List_of_New_Testament_verses_not_included_in_modern_English_translations
        self.often_omitted_verses = [
            "MAT 12:47", "MAT 17:21", "MAT 18:11", "MAT 23:14",
            "MRK 7:16", "MRK 9:44", "MRK 9:46", "MRK 11:26", "MRK 15:28",
            "LUK 17:36", "LUK 23:17",
            "JHN 5:4",
            "ACT 8:37", "ACT 15:34", "ACT 24:7", "ACT 28:29",
            "ROM 16:24"
        ]
        self.often_omitted_verses_note = \
            (f"{len(self.often_omitted_verses)} verses are absent from many modern Bible translations"
             f" as they are not part of some of the oldest Bible manuscripts."
             f"  Some Biblical scholars hold that such verses have been added later,"
             f" often drawing from other parts of the Bible.  ({', '.join(self.often_omitted_verses)})")
        self.verses_sometimes_merged_into_neighboring_verses = [
            "REV 12:18"
        ]

        # The Bible contains 117 descriptive titles, thereof 116 at the beginning of a psalm, 1 following HAB 3:19.
        # Example: "For the director of music. With stringed instruments. A psalm of David." [Psalm 4]
        # In the "eng" schema, the 116 descriptive titles at the beginning of a psalm are denoted as "verse 0".
        # In the "org" schema, 63 out of the 116 psalm descriptive titles are denoted as "verse 1".
        self.psalms_without_descriptive_titles \
            = [1, 2, 10, 33, 43, 71, 91, 93, 94, 95, 96, 97, 99, 104, 105, 106, 107, 111, 112, 113, 114,
               115, 116, 117, 118, 119, 135, 136, 137, 146, 147, 148, 149, 150]
        self.psalms_with_descriptive_titles_in_org_schema \
            = [3, 4, 5, 6, 7, 8, 9, 12, 13, 18, 19, 20, 21, 22, 30, 31, 34, 36, 38, 39, 40, 41, 42, 44, 45,
               46, 47, 48, 49, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 67, 68, 69, 70,
               75, 76, 77, 80, 81, 83, 84, 85, 88, 89, 92, 102, 108, 140, 142]
        # In 4 psalms, the original Hebrew versification spreads the descriptive title over the first 2 verses.
        # All 4 of those descriptive titles are relatively long; they are split before "when" in English ESV, NIV.
        self.psalms_with_descriptive_titles_in_org_schema_as_verses_1_and_2 = [51, 52, 54, 60]
        self.psalms_with_descriptive_titles_in_org_schema_as_verse_1 \
            = sorted(set(self.psalms_with_descriptive_titles_in_org_schema)
                     - set(self.psalms_with_descriptive_titles_in_org_schema_as_verses_1_and_2))
        self.psalms_with_descriptive_titles_not_in_org_schema \
            = [11, 14, 15, 16, 17, 23, 24, 25, 26, 27, 28, 29, 32, 35, 37, 50, 66, 72, 73, 74, 78, 79, 82, 86,
               87, 90, 98, 100, 101, 103, 109, 110, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131,
               132, 133, 134, 138, 139, 141, 143, 144, 145]
        self.psalms_with_descriptive_titles \
            = sorted(self.psalms_with_descriptive_titles_in_org_schema
                     + self.psalms_with_descriptive_titles_not_in_org_schema)
        self.post_verse_descriptive_titles = [("HAB 3:19", "HAB 3:20")]  # (verse ID, pseudo verse ID for descr. title)
        self.post_verse_descriptive_titles_pseudo_verse_ids = [elem[1] for elem in self.post_verse_descriptive_titles]

    @staticmethod
    def pseudo_verse_id_for_descriptive_title(verse_id: str) -> bool:
        """Checks if a verse ID is an informal ID for a descriptive title such as 'PSA 23:0' ('A psalm of David.')
           or 'HAB 3:20' ('For the director of music. On my stringed instruments.')"""
        return regex.match(r'PSA \d+:0$', verse_id) or (verse_id == "HAB 3:20")

    def valid_pseudo_verse_id_for_descriptive_title(self, verse_id: str, schema: str | None) -> bool:
        """This excludes 'PSA 1:0' as Psalm 1 does NOT have a descriptive title"""
        if m := regex.match(r'PSA (\d+):0$', verse_id):
            return (schema in ('rsc', 'rso')) or (int(m.group(1)) in self.psalms_with_descriptive_titles)
        return verse_id in self.post_verse_descriptive_titles_pseudo_verse_ids

    def valid_pseudo_verse_id_for_descriptive_title_not_in_org_schema(self, verse_id: str) -> bool:
        m = regex.match(r'PSA (\d+):0$', verse_id)
        return m and (int(m.group(1)) in self.psalms_with_descriptive_titles_not_in_org_schema)


class Versification:
    """This class holds data of versification mappings between a specific schema (e.g. 'eng') and 'org'.
    Standard versification schemas (see data/standard_mappings/*json), incl. the following types of mappings:
     * 1-1 mappings
     * n-n mappings, which are a shorthand for n consecutive 1-1 mappings
     * n-1 mappings (merges)
     * 1-n mappings (splits)
    Verse IDs not listed are assumed to map onto themselves (1-1)."""
    versification_d = {}  # key: schema (str)  value: Versification
    org = None

    def __init__(self, versification_filename: str, schema: str, bible: BibleStructure, f_log: TextIO):
        self.schema = schema
        if schema in Versification.versification_d.keys():
            f_log.write(f'** Error: Duplicate versification schema "{schema}" (ignored)\n')
            return
        if schema == 'org':
            Versification.org = self
        Versification.versification_d[schema] = self
        self.book_ids = []
        self.chapter_max_verse = defaultdict(int)  # key: (book, chapter)  value: int
        self.verse_ids = set()                     # element: verse ID
        self.verse_id_list = []                    # element: verse ID
        self.verse_id_mapping_from_org = {}        # key: org verse ID  value: verse ID
        self.verse_id_mapping_to_org = {}
        self.verse_ids_for_descriptive_titles = []
        self.merge_objects = List[MergeObject]
        self.split_objects = List[MergeObject]
        self.n_books = 0
        self.n_chapters = 0
        self.n_verses = 0
        self.n_mappings = 0
        self.errors = defaultdict(list)
        self.infos = defaultdict(list)
        # self.target_verse_ids_to_be_monitored = ()
        self.target_verse_ids_to_be_monitored = ('PSA 86:1',)  # for testing
        self.n_max_verses_entries = 0
        self.n_mapped_verses_entries = 0
        with open(versification_filename) as f:
            data = json.load(f)
            if max_verses_d := data.get("maxVerses"):
                self.n_max_verses_entries += 1
                self.book_ids = max_verses_d.keys()
                for book_id in self.book_ids:
                    self.n_books += 1
                    for chapter_number, max_verse_s in enumerate(max_verses_d[book_id], 1):
                        self.n_chapters += 1
                        if regex.match(r'\d+$', max_verse_s):
                            max_verse = int(max_verse_s)
                            self.chapter_max_verse[(book_id, chapter_number)] = max_verse
                            self.n_verses += max_verse
                            for verse_number in range(1, max_verse+1):
                                verse_id = f"{book_id} {chapter_number}:{verse_number}"
                                self.verse_ids.add(verse_id)
                                self.verse_id_list.append(verse_id)
                        else:
                            f_log.write(f'  ** Error: Last verse number for {book_id} {chapter_number} '
                                        f'is not integer: {max_verse_s}\n')
            if mapped_verses_d := data.get("mappedVerses"):
                self.add_mapped_verses(mapped_verses_d, bible, f_log)
        if self.n_max_verses_entries == 0:
            f_log.write(f'  ** Error: Did not find "maxVerses" in {versification_filename}\n')
        if self.n_mapped_verses_entries == 0:
            f_log.write(f'  ** Error: Did not find "mappedVerses" in {versification_filename}\n')

    def add_mapped_verses(self, mapped_verses_d: dict, bible: BibleStructure, f_log: TextIO):
        self.n_mapped_verses_entries += 1
        schema = self.schema
        for from_verse_id_entry in mapped_verses_d.keys():
            ec = f'  ** Error: in schema "{schema}",'
            to_verse_id_entry = mapped_verses_d[from_verse_id_entry]
            book1, chapter1, from_verse1, to_verse1 = self.split_verse_id(from_verse_id_entry)
            book2, chapter2, from_verse2, to_verse2 = self.split_verse_id(to_verse_id_entry)
            if book1 and book2:
                # range of equal length on both sides (n-to-n mapping)
                if (isinstance(to_verse1, int) and isinstance(to_verse2, int)
                        and (from_verse1 < to_verse1) and (from_verse2 < to_verse2)
                        and ((to_verse1 - from_verse1) == (to_verse2 - from_verse2))):
                    for i in range(to_verse1 - from_verse1 + 1):
                        verse_id1 = f"{book1} {chapter1}:{from_verse1+i}"
                        verse_id2 = f"{book2} {chapter2}:{from_verse2+i}"
                        self.add_mapping(verse_id1, verse_id2, bible)
                # 1-to-1 mapping
                elif (to_verse1 is None) and (to_verse2 is None):
                    self.add_mapping(from_verse_id_entry, to_verse_id_entry, bible)
                # merge
                elif isinstance(to_verse1, int) and (from_verse1 < to_verse1) and (to_verse2 is None):
                    self.add_merge_range(book1, chapter1, from_verse1, to_verse1, to_verse_id_entry)
                    mapping = f"{from_verse_id_entry} -> {to_verse_id_entry}"
                    n_verses_to_be_merged = to_verse1 - from_verse1 + 1
                    if n_verses_to_be_merged >= 4:
                        self.errors["merges"].append(mapping)
                    else:
                        self.infos["merges"].append(mapping)
                # split
                elif isinstance(to_verse2, int) and (from_verse2 < to_verse2) and (to_verse1 is None):
                    self.add_split(from_verse_id_entry, book2, chapter2, from_verse2, to_verse2)
                    self.infos["splits"].append(f"{from_verse_id_entry} -> {to_verse_id_entry}")
                else:
                    reported_error = False
                    if isinstance(to_verse1, int) and isinstance(to_verse2, int):
                        if from_verse1 >= to_verse1:
                            f_log.write(f'{ec} bad source range {from_verse1}-{to_verse1}\n')
                            reported_error = True
                        if from_verse2 >= to_verse2:
                            f_log.write(f'{ec} bad target range {from_verse2}-{to_verse2}\n')
                            reported_error = True
                        if (to_verse1 - from_verse1) != (to_verse2 - from_verse2):
                            f_log.write(f'{ec} ranges have different lengths: '
                                        f'{from_verse_id_entry} -> {to_verse_id_entry}\n')
                            reported_error = True
                    if not reported_error:
                        f_log.write(f'{ec} bad mapping: {from_verse_id_entry} -> {to_verse_id_entry}\n')
            elif ((',' in from_verse_id_entry) and (source_verse_ids := from_verse_id_entry.split(','))
                    and all([self.valid_verse_id(source_verse_id, bible)
                             for source_verse_id in source_verse_ids])
                    and self.valid_verse_id(to_verse_id_entry, bible)):
                self.add_merge_list(source_verse_ids, to_verse_id_entry)
                mapping = f"{from_verse_id_entry} -> {to_verse_id_entry}"
                self.infos["merges"].append(mapping)
            else:
                if not book1:
                    f_log.write(f'{ec} unrecognized mapping source "{from_verse_id_entry}"\n')
                if not book2:
                    f_log.write(f'{ec} unrecognized mapping target "{to_verse_id_entry}"\n')

    @staticmethod
    def split_verse_id(verse_id: str) -> Tuple[str | None, int | None, int | str | None, int | None]:
        if (m := (regex.match(r'(\S+) (\d+):(\d+)-(\d+)$', verse_id)
                  or regex.match(r'(\S+)\s+(\d+):(\d+)([a-z]?)$', verse_id))):
            book, chapter1_s, from_verse_s, last_element = m.group(1, 2, 3, 4)
            chapter_number, from_verse_number = int(chapter1_s), int(from_verse_s)
            if regex.match(r'\d+$', last_element):
                to_verse_number = int(last_element)
            elif regex.match(r'[a-z]$', last_element):
                from_verse_number = f"{from_verse_s}{last_element}"
                to_verse_number = None
            else:
                to_verse_number = None
            return book, chapter_number, from_verse_number, to_verse_number
        else:
            return None, None, None, None

    def valid_verse_id(self, verse_id: str, bible: BibleStructure) -> bool:
        return (verse_id in self.verse_ids) or bible.pseudo_verse_id_for_descriptive_title(verse_id)

    def register_any_mapping_error(self, verse_id: str, valid: bool, side: str, bible: BibleStructure, verbose: bool):
        # side is "source" or "target"
        if valid:
            return
        if (not verbose) and bible.valid_pseudo_verse_id_for_descriptive_title(verse_id, self.schema):
            return
        if (side == "target") and (not verbose) and regex.match(r'(DAG 3:\d+|ESG \d+:\d+[a-z])$', verse_id):
            return
        self.errors[f"invalid-mapping-{side}s"].append(verse_id)

    def add_mapping(self, verse_id1: str, verse_id2: str, bible: BibleStructure, verbose: bool = False):
        verse_id1_valid = self.valid_verse_id(verse_id1, bible)
        verse_id2_valid = Versification.org.valid_verse_id(verse_id2, bible)
        if verse_id1_valid and verse_id2_valid:
            if self.verse_id_mapping_to_org.get(verse_id1):
                self.errors["duplicate-sources"].append(verse_id1)
            else:
                self.verse_id_mapping_to_org[verse_id1] = verse_id2
                self.verse_id_mapping_from_org[verse_id2] = verse_id1
                self.n_mappings += 1
        else:
            self.register_any_mapping_error(verse_id1, verse_id1_valid, "source", bible, verbose)
            self.register_any_mapping_error(verse_id2, verse_id2_valid, "target", bible, verbose)

    def add_merge_range(self, book: str, chapter: int, from_verse: int, to_verse: int, merged_verse_id: str):
        source_verse_ids = []
        for verse_number in range(from_verse, to_verse+1):
            source_verse_ids.append(f'{book} {chapter}:{verse_number}')
        self.add_merge_list(source_verse_ids, merged_verse_id)

    def add_merge_list(self, source_verse_ids: list, merged_verse_id: str):
        merge_object = MergeObject(source_verse_ids, merged_verse_id, self)
        for source_verse_id in source_verse_ids:
            if self.verse_id_mapping_to_org.get(source_verse_id):
                self.errors["duplicate-sources"].append(source_verse_id)
            else:
                self.verse_id_mapping_to_org[source_verse_id] = merge_object
        self.set_verse_id_mapping_to_org(merge_object, merged_verse_id)
        self.n_mappings += 1

    def add_split(self, source_verse_id: str, book: str, chapter: int, from_verse: int, to_verse: int):
        target_verse_ids = []
        for verse_number in range(from_verse, to_verse+1):
            target_verse_ids.append(f'{book} {chapter}:{verse_number}')
        split_object = SplitObject(source_verse_id, target_verse_ids, self)
        for target_verse_id in target_verse_ids:
            self.set_verse_id_mapping_to_org(split_object, target_verse_id)
        if self.verse_id_mapping_to_org.get(source_verse_id):
            self.errors["duplicate-sources"].append(source_verse_id)
        else:
            self.verse_id_mapping_to_org[source_verse_id] = split_object
        self.n_mappings += 1

    def set_verse_id_mapping_to_org(self, source_verse_id: str | MergeObject | SplitObject, target_verse_id: str):
        if self.verse_id_mapping_from_org.get(target_verse_id):
            self.errors["duplicate-targets"].append(target_verse_id)
        else:
            self.verse_id_mapping_from_org[target_verse_id] = source_verse_id

    @staticmethod
    def verse_list_pprint(verse_id_list: list, sep: str = "; ") -> str:
        verse_spans = []
        current_book, current_chapter, first_verse_number, last_verse_number = None, None, -1, -1
        for verse_id in verse_id_list:
            if m := regex.match(r'(\S+) (\d+):(\d+)$', verse_id):
                book, chapter, verse_number_s = m.group(1, 2, 3)
                verse_number = int(verse_number_s)
                if book == current_book and chapter == current_chapter and verse_number == (last_verse_number + 1):
                    last_verse_number = verse_number
                else:
                    if 0 <= first_verse_number < last_verse_number:
                        verse_spans.append(f"{current_book} {current_chapter}:{first_verse_number}-{last_verse_number}")
                    elif (first_verse_number >= 0) and (first_verse_number == last_verse_number):
                        verse_spans.append(f"{current_book} {current_chapter}:{first_verse_number}")
                    current_book, current_chapter = book, chapter
                    first_verse_number, last_verse_number = verse_number, verse_number
        if 0 <= first_verse_number < last_verse_number:
            verse_spans.append(f"{current_book} {current_chapter}:{first_verse_number}-{last_verse_number}")
        elif (first_verse_number >= 0) and (first_verse_number == last_verse_number):
            verse_spans.append(f"{current_book} {current_chapter}:{first_verse_number}")
        return sep.join(verse_spans)

    def dict_value_verse_list_pprint(self, d: dict, sep: str = '; ') -> str:
        flattened_verse_ids = []
        for verse_ids in d.values():
            flattened_verse_ids.extend(verse_ids)
        return self.verse_list_pprint(flattened_verse_ids, sep)

    def check_mappings(self, bible: BibleStructure):
        previous_target_verse_ids = set()
        for source_verse_id in self.verse_id_list:
            target = self.verse_id_mapping_to_org.get(source_verse_id)
            if isinstance(target, str):
                target_verse_ids = [target]
            elif isinstance(target, MergeObject):
                target_verse_ids = [] if target.target_checked else [target.target_verse_id]
                target.target_checked = True
            elif isinstance(target, SplitObject):
                target_verse_ids = target.target_verse_ids
            elif target is None:
                target_verse_ids = []
                if not Versification.org.valid_verse_id(source_verse_id, bible):
                    self.errors["dropped-sources"].append(source_verse_id)
            else:
                sys.stderr.write(f"  ** Error: unexpected type '{type(target)}' for {source_verse_id} mapping target\n")
                target_verse_ids = []
            for target_verse_id in target_verse_ids:
                if target_verse_id in previous_target_verse_ids:
                    self.errors["duplicate-targets"].append(target_verse_id)
                else:
                    previous_target_verse_ids.add(target_verse_id)

    @staticmethod
    def count_and_number_suffix(n: int | list, singular_form, plural_form) -> Tuple[int, str]:
        if isinstance(n, list):
            n = len(n)
        return n, (singular_form if n == 1 else plural_form)

    def report_issues(self, f_log: TextIO):
        if dropped_sources := self.errors.get("dropped-sources"):
            f_log.write(f"  Warning: Dropped verses: {self.verse_list_pprint(dropped_sources)}\n")
        if duplicate_sources := self.errors.get("duplicate-sources"):
            f_log.write(f"  Warning: Duplicate source verses: {self.verse_list_pprint(duplicate_sources)}\n")
        if duplicate_targets := self.errors.get("duplicate-targets"):
            f_log.write(f"  Warning: Duplicate target verses: {self.verse_list_pprint(duplicate_targets)}\n")
        if invalid_sources := self.errors.get("invalid-mapping-sources"):
            f_log.write(f"  Warning: Invalid mapping sources: {self.verse_list_pprint(invalid_sources)}\n")
        if invalid_targets := self.errors.get("invalid-mapping-targets"):
            f_log.write(f"  Warning: Invalid mapping targets: {self.verse_list_pprint(invalid_targets)}\n")
        if implausible_merges := self.errors.get("merges"):
            n, s = self.count_and_number_suffix(implausible_merges, "merge", "merges")
            f_log.write(f"  ** Warning: Found {n} implausibly large {s}: {'; '.join(implausible_merges)}\n")
        if merges := self.infos.get("merges"):
            n, s = self.count_and_number_suffix(merges, "merge", "merges")
            f_log.write(f"  Found {n} {s}: {'; '.join(merges)}\n")
        if splits := self.infos.get("splits"):
            n, s = self.count_and_number_suffix(splits, "split", "splits")
            f_log.write(f"  Found {n} {s}: {'; '.join(splits)}\n")

    @staticmethod
    def load_versifications(bible: BibleStructure, f_log: TextIO,
                            standard_mapping_dir: str | None = None,
                            supplementary_mapping_filename: str | None = None):
        versification_dir = os.path.dirname(os.path.realpath(__file__))
        if standard_mapping_dir is None:
            standard_mapping_dir = Path(versification_dir) / 'data' / 'standard_mappings'
        for schema in bible.standard_versification_schemas.keys():
            filename = f"{standard_mapping_dir}/{schema}.json"
            f_log.write(f"Loading versification from {filename} ...\n")
            v = Versification(filename, schema, bible, f_log)
            if supplementary_mapping_filename:
                with open(supplementary_mapping_filename) as f:
                    if mapped_verses_s := f.read():
                        if mapped_verses_d := json.loads(mapped_verses_s):
                            v.add_mapped_verses(mapped_verses_d, bible, f_log)
            v.check_mappings(bible)
            v.report_issues(f_log)
            f_log.write(f"  Loaded {v.n_books} books; {v.n_chapters:,d} chapters; {v.n_verses:,d} verses; "
                        f"{v.n_mappings:,d} mappings\n")

    @staticmethod
    def vref_filename() -> Path:
        versification_dir = os.path.dirname(os.path.realpath(__file__))
        return Path(versification_dir) / 'data' / 'vref.txt'

    @staticmethod
    def supplementary_mapping_filename() -> Path | None:
        cwd = Path(os.path.abspath(os.getcwd()))
        if ((info_dict := general_util.read_corpus_json_info("info.json"))
                and (project_id := info_dict.get('id'))):
            supplementary_mappings_filename = f'suppl_map_{project_id}.json'
        else:
            supplementary_mappings_filename = 'suppl_map.json'
        for d in (cwd, Path(os.path.dirname(cwd))):
            if os.path.isdir(sm_dir := d / 'supplementary-mappings'):
                full_supplementary_mappings_filename = sm_dir / supplementary_mappings_filename
                if os.path.isfile(full_supplementary_mappings_filename):
                    return full_supplementary_mappings_filename
            if os.path.isfile(full_supplementary_mappings_filename := (d / supplementary_mappings_filename)):
                if os.path.isfile(full_supplementary_mappings_filename):
                    return full_supplementary_mappings_filename
        return None


class MergeObject:
    """This class is for n-to-1 mappings (merges)."""
    def __init__(self, source_verse_ids: list, target_verse_id: str, versification: Versification):
        self.versification = versification
        self.source_verse_ids = source_verse_ids
        self.source_verse_pprint = versification.verse_list_pprint(source_verse_ids)
        self.target_verse_id = target_verse_id
        self.source_texts = None
        self.merged_target_text = None
        self.target_checked = False
        self.verses_mapped = False


class SplitObject:
    """This class is for 1-to-n mappings (splits)."""
    def __init__(self, source_verse_id: str, target_verse_ids: list, versification: Versification):
        self.versification = versification
        self.source_verse_id = source_verse_id
        self.target_verse_ids = target_verse_ids
        self.target_verse_pprint = versification.verse_list_pprint(target_verse_ids)
        self.source_text = None
        self.split_target_texts = None


class VersificationMatch:
    """This class measures how well a VersifiedCorpus matches a Versification (e.g. 'eng', 'rsc')."""
    def __init__(self, vc: VersifiedCorpus, v: Versification, bible: BibleStructure):
        self.chapter_overage_count = 0
        self.overage_chapters = defaultdict(list)
        self.verse_overage_count = 0
        self.chapter_shortage_count = 0
        self.shortage_chapters = defaultdict(list)
        self.verse_shortage_count = 0
        for verse_id in vc.vref2verse.keys():
            if verse_id not in v.verse_ids:
                book, chapter, verse, _to_verse = v.split_verse_id(verse_id)
                if book is None:
                    continue
                if book not in bible.books:
                    continue
                if ((book == "PSA") and (verse == 0)
                        and ((v.schema in ('rsc', 'rso')) or (chapter in bible.psalms_with_descriptive_titles))):
                    continue
                if verse_id in bible.post_verse_descriptive_titles_pseudo_verse_ids:
                    continue
                self.verse_overage_count += 1
                if not self.overage_chapters.get((book, chapter)):
                    self.chapter_overage_count += 1
                self.overage_chapters[(book, chapter)].append(verse_id)
        for verse_id in v.verse_id_list:
            if verse_id not in vc.vref2verse:
                if verse_id in bible.often_omitted_verses:
                    continue
                if verse_id in bible.verses_sometimes_merged_into_neighboring_verses:
                    continue
                book, chapter, verse, _to_verse = v.split_verse_id(verse_id)
                # Do not consider for shortage any chapters not covered by corpus at all.
                if vc.chapters.get((book, chapter)):
                    self.verse_shortage_count += 1
                    if not self.shortage_chapters.get((book, chapter)):
                        self.chapter_shortage_count += 1
                    self.shortage_chapters[(book, chapter)].append(verse_id)
        self.cost = self.chapter_overage_count + self.chapter_shortage_count
        self.cost += 10 * (self.verse_overage_count + self.verse_shortage_count)
        sys.stderr.write(f'For schema "{v.schema}", {self.chapter_overage_count}/{self.verse_overage_count} overage, '
                         f'{self.chapter_shortage_count}/{self.verse_shortage_count} shortage\n')
        if v.schema:  # == 'eng':
            if self.overage_chapters and (self.verse_overage_count <= 100):
                sys.stderr.write(f'   Overage:  {v.dict_value_verse_list_pprint(self.overage_chapters)}\n')
            if self.shortage_chapters and (self.verse_shortage_count <= 100):
                sys.stderr.write(f'   Shortage: {v.dict_value_verse_list_pprint(self.shortage_chapters)}\n')


class VersifiedCorpus:
    """This class represents a corpus with associated verse IDs.
    Methods include loading a corpus from a file, reversifying it to another versification schema,
    and writing out a reversified corpus."""
    def __init__(self, schema: str | None):
        self.vref2verse = {}
        self.schema = schema
        self.n_verses = 0
        self.n_range_lines = 0
        self.corpus_filename = None
        self.vref_filename = None
        self.back_versification = None
        self.errors = defaultdict(list)
        self.warnings = defaultdict(list)
        self.books = defaultdict(int)  # key: book  value: number of chapters in book
        self.chapters = defaultdict(int)  # key: (book, chapter)  value: number of verses in chapter

    def load_corpus(self, corpus_filename: str, vref_filename: str, _f_log: TextIO):
        self.corpus_filename = corpus_filename
        self.vref_filename = vref_filename
        with open(corpus_filename) as f_corpus, open(vref_filename) as f_vref:
            line_number = 0
            for line in f_corpus:
                line_number += 1
                verse = line.strip()
                if verse == "<range>":
                    self.n_range_lines += 1
                verse_id = f_vref.readline().rstrip()
                if self.vref2verse.get(verse_id):
                    self.errors["duplicate-verse-ids"].append(verse_id)
                    continue
                elif verse == "":
                    continue
                book, chapter, from_verse, _to_verse = Versification.split_verse_id(verse_id)
                if not self.books.get(book):
                    self.books[book] = 0
                if not self.chapters.get((book, chapter)):
                    self.books[book] += 1
                    self.chapters[(book, chapter)] = 0
                self.chapters[(book, chapter)] += 1
                self.vref2verse[verse_id] = verse
                self.n_verses += 1
            if self.errors:
                sys.stderr.write(f'Errors in {vref_filename}: {self.errors}\n')
            range_clause = f" (thereof {self.n_range_lines} <range>)" if self.n_range_lines else ""
            sys.stderr.write(f'Loaded {len(self.books)} books with {len(self.chapters):,d} chapters'
                             f' and {self.n_verses:,d} verses from {line_number:,d} lines{range_clause}'
                             f' in {corpus_filename} and {vref_filename}\n')

    def reversify(self, v: Versification, _f_log: TextIO) -> VersifiedCorpus:
        target_vc = VersifiedCorpus('org')
        target_vc.back_versification = {}
        for source_verse_id in self.vref2verse.keys():
            target = v.verse_id_mapping_to_org.get(source_verse_id)
            if isinstance(target, str):
                target_verse_id = target
                if source_verse := self.vref2verse.get(source_verse_id):
                    if target_vc.vref2verse.get(target_verse_id):
                        target_vc.errors["duplicate-target-verse-ids"].append(target_verse_id)
                        if target_verse_id in v.target_verse_ids_to_be_monitored:
                            sys.stderr.write(f" -*MONITOR1a*- {v.schema} t:{target_verse_id} s:{source_verse_id}\n")
                    else:
                        target_vc.vref2verse[target_verse_id] = source_verse
                        target_vc.back_versification[target_verse_id] = source_verse_id
            elif isinstance(target, MergeObject):
                merge_object = target
                if not merge_object.verses_mapped:
                    target_verse_id = merge_object.target_verse_id
                    target_verses = []
                    range_verse = None
                    for merge_source_verse_id in merge_object.source_verse_ids:
                        if source_verse := self.vref2verse.get(merge_source_verse_id):
                            if source_verse == '<range>':
                                range_verse = source_verse
                            else:
                                target_verses.append(source_verse)
                    if target_verse_s := ' '.join(target_verses) if target_verses else range_verse:
                        if target_vc.vref2verse.get(target_verse_id):
                            target_vc.errors["duplicate-target-verse-ids"].append(target_verse_id)
                        else:
                            target_vc.vref2verse[target_verse_id] = target_verse_s
                            target_vc.back_versification[target_verse_id] \
                                = v.verse_list_pprint(merge_object.source_verse_ids)
                    merge_object.verses_mapped = True
            elif isinstance(target, SplitObject):
                split_object = target
                split_source_verse_id = split_object.source_verse_id
                if source_verse := self.vref2verse.get(split_source_verse_id):
                    target_verse_ids = split_object.target_verse_ids
                    source_copied = False
                    letter_suffix_ord = ord('a') - 1  # add suffix 'a', 'b', 'c' to split_source_verse_id values
                    for target_verse_id in target_verse_ids:
                        if target_vc.vref2verse.get(target_verse_id):
                            target_vc.errors["duplicate-target-verse-ids"].append(target_verse_id)
                        else:
                            letter_suffix_ord += 1
                            letter_suffix = chr(letter_suffix_ord)
                            target_vc.vref2verse[target_verse_id] = "<range>" if source_copied else source_verse
                            target_vc.back_versification[target_verse_id] = split_source_verse_id + letter_suffix
                            source_copied = True
            elif target is None:
                target_verse_id = source_verse_id
                if source_verse := self.vref2verse.get(source_verse_id):
                    if target_vc.vref2verse.get(target_verse_id):
                        target_vc.errors["duplicate-target-verse-ids"].append(target_verse_id)
                        if target_verse_id in v.target_verse_ids_to_be_monitored:
                            sys.stderr.write(f" -*MONITOR1d*- {v.schema} t:{target_verse_id} s:{source_verse_id}\n")
                    else:
                        target_vc.vref2verse[target_verse_id] = source_verse
        return target_vc

    def write_corpus(self, corpus_filename: str, vref_filename: str, bible: BibleStructure, _f_log: TextIO):
        n_verses_writen = 0
        mapped_verse_ids = set()
        general_util.mkdirs_in_path(corpus_filename)
        with open(corpus_filename, "w") as f_out, open(vref_filename) as f_vref:
            for line in f_vref:
                verse_id = line.strip()
                mapped_verse_ids.add(verse_id)
                if verse := self.vref2verse.get(verse_id):
                    f_out.write(verse + '\n')
                    n_verses_writen += 1
                else:
                    f_out.write('\n')
        for verse_id in self.vref2verse.keys():
            if verse_id not in mapped_verse_ids:
                if bible.valid_pseudo_verse_id_for_descriptive_title_not_in_org_schema(verse_id):
                    self.warnings["dropped-non-org-descriptive-titles"].append(verse_id)
                else:
                    self.errors["dropped-target-verse-ids"].append(verse_id)

    def report_errors(self, vref_filename: str, f_log: TextIO):
        if self.errors:
            for error_type in self.errors.keys():
                if error_type == 'duplicate-target-verse-ids':
                    duplicate_target_verses = self.errors.get(error_type)
                    f_log.write(f'Reversification error: Ignored {len(duplicate_target_verses)} duplicate target'
                                f' verses: {Versification.verse_list_pprint(duplicate_target_verses)}\n')
                elif error_type == 'dropped-target-verse-ids':
                    dropped_target_verses = self.errors.get(error_type)
                    f_log.write(f"Reversification error: Dropped {len(dropped_target_verses)} verses outside the scope"
                                f" of '{vref_filename}': {Versification.verse_list_pprint(dropped_target_verses)}\n")
                else:
                    f_log.write(f'Reversification errors ({error_type}): {self.errors.get(error_type)}\n')
        if self.warnings:
            if dropped_non_org_descriptive_titles := self.warnings["dropped-non-org-descriptive-titles"]:
                f_log.write(f"Reversification info: Dropped {len(dropped_non_org_descriptive_titles)} pseudo verses "
                            f"for descriptive titles outside the scope of '{vref_filename}'\n")
            # sys.stderr.write(f'Reversification warnings: {self.warnings}\n')


class BackVersification:
    """This class supports scripts to back-versify verse IDs from 'org' to what the user submitted."""
    def __init__(self, filename: str | None):
        self.d = None
        self.log_d = defaultdict(int)
        if filename:
            if os.path.exists(filename):
                with open(filename) as f:
                    if dict_s := f.read():
                        self.d = json.loads(dict_s)
                        sys.stderr.write(f"Loaded {len(self.d):,d} back-versification entries from {filename}\n")
                    else:
                        sys.stderr.write(f"Could not read from {filename}\n")
            else:
                sys.stderr.write(f"Could not find back-versification file {filename}\n")
        else:
            sys.stderr.write(f"No file specified for back-versification.\n")

    def report_stats(self, calling_script: str | None = None, max_n_examples: int = 10) -> str:
        """Can be called by other tools after back-versification."""
        if self.log_d:
            n_verse_types = len(self.log_d.keys())
            n_verse_tokens = sum(self.log_d.values())
            bv_examples = dict([(v_id, self.d.get(v_id)) for v_id in list(self.log_d.keys())[:max_n_examples]])
            calling_script_clause = f" in {calling_script}" if calling_script else ""
            return (f"Back-versified {n_verse_types:,d}/{n_verse_tokens:,d} verse types/tokens{calling_script_clause},"
                    f" incl. {bv_examples}\n")
        else:
            return ""

    def back_verse_id(self, verse_id: str) -> str:
        return (self.d and self.d.get(verse_id)) or verse_id

    def m(self, verse_id: str | None, html: bool = False) -> str | None:
        """Map verse_id back to user's original versification (default: NOT in HTML-format)"""
        # Do this also for ranges such as "GEN 1:10-20"
        if from_to_verse_id_pair := BibleUtilities.split_vref_start_end(verse_id):
            if ((m_from := self.m(from_to_verse_id_pair[0], html))
                    and (m_to := self.m(from_to_verse_id_pair[1], html))):
                return BibleUtilities.combine_vref_start_end(m_from, m_to)
        if (back_verse_id := self.back_verse_id(verse_id)) and (back_verse_id != verse_id):
            self.log_d[verse_id] += 1
            # if (self.log_d[verse_id] == 1) and (len(self.log_d) <= 10):
            #     sys.stderr.write(f"bv.m.{verse_id} -> {back_verse_id}\n")
            if html:
                title = f"User versification: {back_verse_id}\n'org'  versification: {verse_id}"
                title = title.replace("'", '&apos;')
                title = title.replace('"', '&quot;')
                title = title.replace('\n', '&#xA;')
                title = title.replace(' ', '&nbsp;')
                # style = "font-style:italic;border-bottom:1px dotted;"
                style = "border-bottom:2px dotted;"
                return f"<span patitle='{title}' style='{style}'>{back_verse_id}</span>"
            else:
                return back_verse_id
        else:
            return verse_id

    def mh(self, verse_id: str) -> str:
        """Map verse_id back to user's original versification in HTML-format"""
        return self.m(verse_id, True)

    def diff(self, other: BackVersification) -> dict:
        result_d = {}
        for verse_id in (list(self.d.keys()) + list(other.d.keys())):
            back_verse_id1 = self.d.get(verse_id)
            back_verse_id2 = other.d.get(verse_id)
            if back_verse_id1 != back_verse_id2:
                result_d[verse_id] = (back_verse_id1, back_verse_id2)
        return result_d

    @staticmethod
    def diff_files(filename1: str, filename2: str, out: TextIO = sys.stderr):
        back_versification1 = BackVersification(filename1)
        back_versification2 = BackVersification(filename2)
        diff = back_versification1.diff(back_versification2)
        out.write(f"No. of diff. back versifications: {len(diff)}   {diff}\n")


def main():
    supplementary_mapping_filename = Versification.supplementary_mapping_filename()
    sys.stderr.write(f"SMF: {supplementary_mapping_filename}\n")
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--check')
    parser.add_argument('-i', '--input_corpus_filename')
    parser.add_argument('-j', '--input_verse_id_filename')
    parser.add_argument('-s', '--input_schema', default=None)
    parser.add_argument('-o', '--output_corpus_filename')
    parser.add_argument('-t', '--output_verse_id_filename', default=Versification.vref_filename())
    parser.add_argument('-d', '--data_log_filename', default='vers/versification_data_log.txt')
    parser.add_argument('-l', '--corpus_log_filename', default='vers/corpus_versification_log.txt')
    parser.add_argument('-b', '--back_versification_filename', default='vers/back_versification.json')
    parser.add_argument('-m', '--standard_mapping_dir')
    parser.add_argument('--back_versification_diff', nargs=2)
    parser.add_argument('--supplementary_verse_mapping', default=supplementary_mapping_filename)
    args = parser.parse_args()
    # sys.stderr.write(f"vref: {args.output_verse_id_filename}\n")
    f_corpus_log = sys.stderr  # default
    if bv_filenames := args.back_versification_diff:
        sys.stderr.write(f"back_versification_diff: {bv_filenames}\n")
        BackVersification.diff_files(bv_filenames[0], bv_filenames[1])
        return
    if args.corpus_log_filename:
        try:
            general_util.mkdirs_in_path(args.corpus_log_filename)
            f_corpus_log = open(args.corpus_log_filename, 'w')
        except IOError:
            sys.stderr.write(f"Cannot write to {args.corpus_log_filename}")
    f_data_log = sys.stderr  # default
    if args.data_log_filename:
        try:
            general_util.mkdirs_in_path(args.data_log_filename)
            f_data_log = open(args.data_log_filename, 'w')
        except IOError:
            sys.stderr.write(f"Cannot write to {args.data_log_filename}")
    bible = BibleStructure()
    Versification.load_versifications(bible, f_data_log, args.standard_mapping_dir)
    if args.input_corpus_filename and args.input_verse_id_filename:
        input_corpus = VersifiedCorpus(args.input_schema)
        input_corpus.load_corpus(args.input_corpus_filename, args.input_verse_id_filename, f_corpus_log)
        best_cost: float | None = None
        best_schema = None
        best_versification = None
        input_versification = None
        for schema in ('org', 'eng', 'rsc', 'rso', 'vul', 'lxx'):
            if v := Versification.versification_d[schema]:
                vm = VersificationMatch(input_corpus, v, bible)
                if best_cost is None or vm.cost < best_cost:
                    best_cost, best_schema, best_versification = vm.cost, v.schema, v
        if best_schema:
            best_schema_name = bible.standard_versification_schemas.get(best_schema)
            sys.stderr.write(f"Schema with lowest cost: {best_schema} ({best_schema_name})\n")
        if input_schema := args.input_schema:
            input_schema_name = bible.standard_versification_schemas.get(input_schema)
            input_versification = Versification.versification_d.get(input_schema)
            sys.stderr.write(f"Input schema: {input_schema} ({input_schema_name})\n")
        if source_versification := input_versification or best_versification:
            if input_versification and (input_versification != best_versification):
                sys.stderr.write(f"Proceeding with schema '{source_versification.schema}' as specified in arguments.\n")
            if args.output_corpus_filename and args.output_verse_id_filename:
                reversified_corpus = input_corpus.reversify(source_versification, f_corpus_log)
                reversified_corpus.write_corpus(args.output_corpus_filename, args.output_verse_id_filename,
                                                bible, f_corpus_log)
                reversified_corpus.report_errors(args.output_verse_id_filename, sys.stderr)
                if args.back_versification_filename:  # and reversified_corpus.back_versification:
                    try:
                        general_util.mkdirs_in_path(args.back_versification_filename)
                        with open(args.back_versification_filename, "w") as f_br:
                            f_br.write(json.dumps(reversified_corpus.back_versification) + '\n')
                            sys.stderr.write(f"Wrote {len(reversified_corpus.back_versification):,d} back "
                                             f"versification mappings to {args.back_versification_filename}\n")
                    except IOError:
                        sys.stderr.write(f'** Error: could not write back_versification '
                                         f'to {args.back_versification_filename}\n')
    if f_corpus_log not in (sys.stderr, None):
        f_corpus_log.close()
        sys.stderr.write(f"Corpus log file: {args.corpus_log_filename}\n")
    if f_data_log not in (sys.stderr, None):
        f_data_log.close()
        sys.stderr.write(f"Data log file: {args.data_log_filename}\n")


if __name__ == "__main__":
    main()

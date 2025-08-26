#!/usr/bin/env python

from __future__ import annotations
import json
from pathlib import Path
import os
import regex
import sys
from typing import List, Optional, Tuple


def slot_value_in_double_colon_del_list(line: str, slot: str, default: Optional = None) -> str:
    """For a given slot, e.g. 'cost', get its value from a line such as '::s1 of course ::s2 ::cost 0.3' -> 0.3
    The value can be an empty string, as for ::s2 in the example above."""
    m = regex.match(fr'(?:.*\s)?::{slot}(|\s+\S.*?)(?:\s+::\S.*|\s*)$', line)
    return m.group(1).strip() if m else default


# cwd_path = Path(os.getcwd())
# parent_dir = cwd_path.parent
def find_file(filename: str | Path, dirs: List[str | Path]) -> Path | None:
    if os.path.exists(filename):
        return filename if isinstance(filename, Path) else Path(filename)
    if not filename.startswith('/'):
        for dir1 in dirs:
            dir2 = dir1 if isinstance(filename, Path) else Path(dir1)
            full_filename = dir2 / filename
            if os.path.exists(full_filename):
                return full_filename
    return None


def standard_data_dirs() -> List[str]:
    result = []
    # https://wiki.archlinux.org/title/XDG_Base_Directory
    if xdg_data_home := os.getenv("XDG_DATA_HOME", None):
        if os.path.isdir(xdg_data_home):
            result.append(xdg_data_home)
    if home := os.getenv("HOME", None):
        local_share = os.path.join(home, ".local", "share")
        if os.path.isdir(local_share):
            result.append(local_share)
    if os.path.isdir("/usr/share"):
        result.append("/usr/share")
    return result


def findall3(match_regex: str, text: str) -> Tuple[List[str], List[int], List[str]]:
    """returns matches, inter-matches, start-positions, inter-matches (len(matches)+1)"""
    full_regex = '(.*?)(' + match_regex + ')(.*)$'
    matches, start_positions, inter_matches = [], [], []
    rest, position = text, 0
    while m := regex.match(full_regex, rest):
        pre, core, rest = m.group(1, 2, 3)
        position += len(pre)
        inter_matches.append(pre)
        matches.append(core)
        start_positions.append(position)
        position += len(core)
    inter_matches.append(rest)
    return matches, start_positions, inter_matches


def read_corpus_json_info(info_filename: str = "info.json") -> dict | None:
    """read in content such as '{"id": "tam-A2aO4fh5", "lc": "tam", "lang": "Tamil", "short": "Tamil IRV 202505",
                                 "full": "Tamil Indian Revised Version (IRV) 2025-05-05"}'"""
    if os.path.isfile(info_filename):
        try:
            f_info = open(info_filename)
        except IOError:
            sys.stderr.write(f"Cannot open file {info_filename}\n")
            return None
        try:
            s = f_info.read()
        except IOError:
            sys.stderr.write(f"Cannot read file {info_filename}\n")
            f_info.close()
            return None
        f_info.close()
        try:
            return json.loads(s)  # keys: id, lc, lang, short, full
        except ValueError as error:
            sys.stderr.write(f"JSON format error in file {info_filename}: {error}\n")
            return None
    else:
        # sys.stderr.write(f"Could not find file {info_filename}\n")
        return None


class Corpus:
    corpora = {}

    def __init__(self, corpus_id: str | None = None):
        self.snt_id2snt = dict()
        self.corpus_id = corpus_id
        if corpus_id:
            Corpus.corpora[corpus_id] = self

    def __repr__(self):
        result = f"Corpus {self.corpus_id or ''}"
        for snt_id in sorted(self.snt_id2snt.keys()):
            result += f"\n   {snt_id} {self.snt_id2snt.get(snt_id)}"
        return result

    @staticmethod
    def find_corpus(corpus_name: str) -> Corpus | None:
        return Corpus.corpora.get(corpus_name)

    def reset(self) -> None:
        self.snt_id2snt = dict()

    def load_corpus_with_vref(self, corpus_filename: str, vref_filename: str) -> Tuple[int, str]:
        """Loads corpus, vref, returning number of entries and any error-message (empty = ok)"""
        n_entries = 0
        try:
            f_in = open(corpus_filename)
        except IOError:
            return 0, "Could not read corpus {corpus_filename}"
        try:
            f_vref = open(vref_filename)
        except IOError:
            f_in.close()
            return 0, f"Could not read vref {vref_filename}"
        for line, vref_line in zip(f_in, f_vref):
            line = line.rstrip()
            snt_id = vref_line.rstrip()
            if regex.search(r'\S', line):
                n_entries += 1
                self.snt_id2snt[snt_id] = line
        f_in.close()
        f_vref.close()
        return n_entries, ""

    def load_corpus_from_in_dict(self, check_corpus_list: List[dict]) -> int:
        n_entries = 0
        for check_corpus_entry in check_corpus_list:
            snt_id = check_corpus_entry.get('snt-id', '').strip()
            snt = check_corpus_entry.get('text', '').strip()
            if snt and snt_id:
                self.snt_id2snt[snt_id] = snt
        return n_entries

    def get_snt_ids(self):
        return self.snt_id2snt.keys()

    def lookup_snt(self, snt_id: str) -> str:
        return self.snt_id2snt.get(snt_id)

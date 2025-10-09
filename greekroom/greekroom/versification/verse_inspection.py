#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# verse_inspection.py
# This development auxiliary tool prints out selected verses from selected corpora with a selected window size
#   as specified by the configuration file .../vers/versification-inspection-config.jsonl

from __future__ import annotations
import argparse
import json
import os
import regex
import sys


class Corpus:
    def __init__(self, corpus_filename: str, vref_filename: str, legend: str | None):
        self.corpus_filename = corpus_filename
        self.vref_filename = vref_filename
        self.legend = legend
        self.ref2verse = {}
        self.line_number2ref = {}
        self.ref2line_number = {}
        self.n_entries = 0
        with open(corpus_filename) as f_corpus, open(vref_filename) as f_vref:
            line_number = 0
            for line in f_corpus:
                line_number += 1
                vref = f_vref.readline().rstrip()
                line2 = line.rstrip()
                if vref and line2:
                    self.n_entries += 1
                    self.ref2verse[vref] = line.rstrip()
                    self.line_number2ref[line_number] = vref
                    self.ref2line_number[vref] = line_number

    def __repr__(self) -> str:
        return f"Corpus {self.legend or os.path.basename(self.corpus_filename)} with {self.n_entries} entries"


def full_filename(filename: str, default_dir: str) -> str:
    return filename if filename.startswith("/") else f"{default_dir}/{filename}"


def load_config(config_filename: str) -> dict:
    d = {"corpora": [], "default-dir": "."}
    with open(config_filename) as f_config:
        for line in f_config:
            if regex.match(r"\s*\{.*\}", line):
                load_d = json.loads(line)
                if load_d.get("default"):
                    if default_vref := load_d.get("vref"):
                        d["default-vref"] = default_vref
                    if default_dir := load_d.get("dir"):
                        d["default-dir"] = default_dir
                    if default_window := load_d.get("window"):
                        d["window-size"] = default_window
                elif corpus_filename := load_d.get("corpus"):
                    vref_filename = load_d.get("vref", d.get("default-vref"))
                    file_dir = load_d.get("dir", d.get("default-dir"))
                    legend = load_d.get("legend", corpus_filename)
                    corpus = Corpus(full_filename(corpus_filename, file_dir),
                                    full_filename(vref_filename, file_dir),
                                    legend)
                    d.get("corpora").append(corpus)
                elif verses := load_d.get("verses"):
                    d["verses"] = verses
    return d


def smart_verse_line_number(corpus: Corpus, verse_ref: str) -> int | None:
    if verse_line_number := corpus.ref2line_number.get(verse_ref):
        return verse_line_number
    if m := regex.match(r'(.*):(\d+)\s*$', verse_ref):
        book_chapter, verse_number_s = m.group(1, 2)
        verse_number = int(verse_number_s)
        for offset in (1, -1, 2, -2):
            if neighbor_verse_line_number := corpus.ref2line_number.get(f"{book_chapter}:{verse_number+offset}"):
                return neighbor_verse_line_number - offset
    return None


def show_verses_across_corpora(d: dict):
    for verse_ref in d.get("verses"):
        print(f"Verse {verse_ref}")
        for corpus in d.get("corpora"):
            print(f"  {corpus.legend}")
            verse_line_number = smart_verse_line_number(corpus, verse_ref)
            if verse_line_number:
                for line_number in range(verse_line_number - d.get('window-size'),
                                         verse_line_number + d.get('window-size') + 1):
                    vref = corpus.line_number2ref.get(line_number)
                    verse = corpus.ref2verse.get(vref)
                    symbol = ">" if line_number == verse_line_number else " "
                    if (vref is None) and (verse is None):
                        print(f"  {symbol} None")
                    else:
                        print(f"  {symbol} {vref}: {verse}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config_filename', type=str,
                        default="vers/versification-inspection-config.jsonl")
    args = parser.parse_args()
    d = load_config(args.config_filename)
    sys.stderr.write(f"C: {d}\n")
    show_verses_across_corpora(d)


if __name__ == "__main__":
    main()

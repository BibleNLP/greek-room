#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Written by Ulf Hermjakob, USC/ISI
This script checks a given text for a wide range of anomalies.
Many check results include an action menu with one or more possible actions (with confidence).
This Wildebeest interface has been designed to support external editors such as Fluent and Paratext.
"""
# -*- encoding: utf-8 -*-

from __future__ import annotations
import argparse
import json
import logging as log
import sys
import greekroom.wildebeest.wb_analysis as wb_a
from greekroom.gr_utilities import corpus
from greekroom.wildebeest import __version__ as __wildebeestVersion__
from greekroom.wildebeest import last_mod_date as wildebeest_last_mod_date


log.basicConfig(level=log.INFO)


def main():
    """Wrapper around Wildebeest analysis"""
    # parse arguments
    parser = argparse.ArgumentParser(description='Analyzes a given text for a wide range of anomalies', prog="wb-ana")
    parser.add_argument('-j', '--json', type=str, help='input json')
    parser.add_argument('-a', '--auto_correct_threshold', type=float, default=None,
                        help='value between 0.0 and 1.0; higher = more reliable')
    parser.add_argument('-o', '--json_out_filename', type=argparse.FileType('w', encoding='utf-8', errors='ignore'),
                        default=None, help='output JSON filename')
    parser.add_argument('-H', '--html_out_filename_by_snt_id',
                        type=argparse.FileType('w', encoding='utf-8', errors='ignore'),
                        default=None, help='to help development')
    parser.add_argument('-C', '--html_out_filename_by_check',
                        type=argparse.FileType('w', encoding='utf-8', errors='ignore'),
                        default=None, help='to help development')
    parser.add_argument('--version', action='version',
                        version=f'%(prog)s {__wildebeestVersion__} last modified: {wildebeest_last_mod_date}')
    parser.add_argument('--back_versification', type=str, default='vers/back_versification.json')
    args = parser.parse_args()
    wb_a.add_missing_default_argparse_args(args)
    json_dict = json.loads(args.json)
    lang_code = json_dict['params'][0]['corpus']['langCode']
    args.lc = lang_code
    wb = wb_a.WildebeestAnalysis(args)
    # _wb_ana = wb.check_w_args(args, None)
    _wb_ana = wb_a.process_args(args)


def version():
    return wb_a.WildebeestAnalysis.populate_version()


def init_text_corpus() -> corpus.TextCorpus:
    """The text_corpus includes corpus statistics and implements a state between calls to check."""
    return corpus.TextCorpus()


def check(json_check_request: dict, text_corpus: corpus.TextCorpus | None = None) -> dict:
    lang_code = json_check_request['params'][0]['corpus']['langCode']
    args = argparse.Namespace(json=json_check_request,
                              lc=lang_code)
    wb_a.add_missing_default_argparse_args(args)
    wb = wb_a.WildebeestAnalysis(args)
    return wb.check_w_args(args, text_corpus)


if __name__ == "__main__":
    main()

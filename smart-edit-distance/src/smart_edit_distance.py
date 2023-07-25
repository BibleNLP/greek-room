#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Written by Ulf Hermjakob, USC/ISI
Initial code: August 31, 2020

Smart edit distance (sed) script measures the difference between two strings.
Examples: sed('fat', 'cat') = 1.0            Levenshtein-distance('fat', 'cat') = 1
          sed('center', 'centre') = 0.1      Levenshtein-distance('centre', 'center') = 2
Unlike the classic Levenshtein distance, where every insertion, deletion and substitution of a character has the same
cost of 1, this metric allows lower costs for certain pairs of more similar substrings as specified by a cost table.
Assigning lower costs to substring pairs such as f/ph and n/nn helps identify the name pairs
'Josef Schumann'/'Joseph Schuman' and 'Muhammad'/'Mohamed' as more similar than 'Jim'/'Kim'.
Typical low-cost cases include vowel variation, diacritics, consonant doubling, voiced/unvoiced consonant pairs.

The cost file assigns costs to pairs of substrings, optionally with language code and left/right context restrictions.
Without a cost file, the edit distance defaults to the Levenshtein distance.
Cost table examples (slot names are marked by preceding double-colons):
::s1 f ::s2 ph ::cost 0.01
::s1 e ::s2 ::cost 0.3                                    # dropping letter 'e' (without considering context)
::s1 e ::s2 ::cost 0.2 ::left1 /[a-z]$/ ::left2 /[a-z]$/  # if preceded by a letter (i.e. not at beginning of word)
::s1 w ::s2 u ::cost 0.02 ::lc1 ara, fas, pas             # if 'w' is (romanized version of) Arabic waw/و
::s1 c ::s2 k ::cost 0.02 ::right1 [-,abcdfghklmnpoqrstuvwxz$ ]  # unless 'c' is followed by e/i/j/y
Left contexts are regular expressions.
Right contexts are sets of letters (with $ standing for end-of-string), as opposed to full regular expressions,
a legacy restriction in case the smart edit distance operates on lattices of letters as opposed to simple strings.
Valid slots: ::s1, ::s2, ::cost, ::lc1, ::lc2, ::left1, ::left2, ::right1, ::right2, ::comment
Language codes (::lc1 and ::lc2) should be specified according to ISO 639-3, e.g. 'fas' for Farsi/Persian.

Together with the universal romanization tool uroman (Hermjakob et al., 2018), this tool can be used to ascertain
string similarity across scripts. Consider the Hindi, Urdu and English names for Nepal, 'नेपाल', 'نیپال' and 'Nepal'
respectively. After romanization, which produces 'nepaal', 'nipal', 'Nepal', this smart edit distance tool can be
used to quantify the phonetic similarity.
"""
# -*- encoding: utf-8 -*-
import argparse
import logging as log
import re
import sys
from typing import List, Optional, Tuple, TextIO, Union

log.basicConfig(level=log.INFO)

__version__ = '0.1'
last_mod_date = 'September 5, 2020'


def slot_value_in_double_colon_del_list(line: str, slot: str, default: Optional[str] = None) -> str:
    """For a given slot, e.g. 'cost', get its value from a line such as '::s1 of course ::s2 ::cost 0.3' -> 0.3
    The value can be an empty string, as for ::s2 in the example above."""
    m = re.match(fr'(?:.*\s)?::{slot}(|\s+\S.*?)(?:\s+::\S.*|\s*)$', line)
    return m.group(1).strip() if m else default


def double_colon_del_list_validation(s: str, line_number: int, filename: str,
                                     valid_slots: List[str], required_slots: List[str] = None) -> bool:
    """Check whether a string (typically line in data file) is a well-formed double-colon expression"""
    valid = True
    prev_slots = []
    slots = re.findall(r'::([a-z]\S*)', s, re.IGNORECASE)
    # Check for duplicates and unexpected slots
    for slot in slots:
        if slot in valid_slots:
            if slot in prev_slots:
                valid = False
                log.warning(f'found duplicate slot ::{slot} in line {line_number} in {filename}')
            else:
                prev_slots.append(slot)
        else:
            valid = False
            log.warning(f'found unexpected slot ::{slot} in line {line_number} in {filename}')
    # Check for missing required slots
    if required_slots:
        for slot in required_slots:
            if slot not in prev_slots:
                valid = False
                log.warning(f'missing required slot ::{slot} in line {line_number} in {filename}')
    # Check for ::slot syntax problems
    m = re.match(r'.*?(\S+::[a-z]\S*)', s)
    if m:
        valid = False
        value = m.group(1)
        if re.match(r'.*:::', value):
            log.warning(f"suspected spurious colon in '{value}' in line {line_number} in {filename}")
        else:
            log.warning(f"# Warning: suspected missing space in '{value}' in line {line_number} in {filename}")
    m = re.match(r'(?:.*\s)?(:[a-z]\S*)', s)
    if m:
        valid = False
        log.warning(f"suspected missing colon in '{m.group(1)}' in line {line_number} in {filename}")
    return valid


def concat2(s1: str, s2: str, sep: str) -> str:
    """Concatenate two strings using separator ignoring any empty strings."""
    if s1 == '':
        return s2
    elif s2 == '':
        return s1
    else:
        return s1 + sep + s2


class SmartEditDistance:
    def __init__(self):
        self.ht = {}              # dictionary stores most of the cost file data
        self.max1 = 1             # max length of 's1', used for run-time optimization
        self.max2 = 1             # max length of 's2'
        self.n_cost_rules = 0
        self.n_entries = 0
        self.prev_line_number = 0

    def add_re_context_to_cost_rule(self, slot: str, value: str, cost_rule_id: str, line_number: int) -> None:
        """Adds optional compiled regular expression left context to cost rule"""
        if value.startswith('/') and value.endswith('/'):
            re_string = value[1:-1]
        else:
            re_string = value
        # In cost file, initial /^.../ indicates match must start at left
        if re_string.startswith('^'):
            re_string = re_string[1:]
        else:
            re_string = '.*' + re_string
        key1 = f'{slot.upper()}\t{cost_rule_id}'
        try:
            self.ht[key1] = re.compile(re_string)
        except re.error:
            log.warning(f'Cannot process ::{slot} {value} in line {line_number} of cost file')

    def add_letter_context_to_cost_rule(self, slot: str, value: str, cost_rule_id: str, line_number: int) -> None:
        """Adds optional set of letters as right context to cost rule"""
        if value.startswith('[') and value.endswith(']'):
            letter_string = value[1:-1]
        else:
            letter_string = value
        if value == '':
            log.warning(f'Cannot process ::{slot} with empty value in line {int(line_number)} of cost file')
        else:
            key1 = f'{slot.upper()}\t{cost_rule_id}'
            self.ht[key1] = letter_string

    def build_cost_rule(self, line: str, s1: str, s2: str, cost: float, line_number: int, swapped: bool = False) \
            -> None:
        """Builds cost rule, with core arguments s1, s2, core"""
        if line_number != self.prev_line_number:
            self.n_entries += 1  # A cost entry might yield two cost rules: (1) original and (2) swapped/inverted.
        self.n_cost_rules += 1
        cost_rule_id = str(self.n_cost_rules)
        key1 = fr'COST\t{s1}\t{s2}'
        if key1 not in self.ht:
            self.ht[key1] = {}
        # For a given pair of substrings, there might be multiple cost rules with the same substring pair,
        # but with different language code or left/right context restrictions.
        self.ht[key1][cost_rule_id] = cost
        self.prev_line_number = line_number
        # max1, max2 keep track of the longest substrings, for later optimization.
        if len(s1) > self.max1:
            self.max1 = len(s1)
        if len(s2) > self.max2:
            self.max2 = len(s2)
        self.ht[fr'LINE\t{cost_rule_id}'] = line_number  # Keep track of line number in cost file for cost-log.
        self.ht[fr's1\t{s1}'] = 1
        self.ht[fr's2\t{s2}'] = 1
        left1 = slot_value_in_double_colon_del_list(line, 'left1')
        left2 = slot_value_in_double_colon_del_list(line, 'left2')
        right1 = slot_value_in_double_colon_del_list(line, 'right1')
        right2 = slot_value_in_double_colon_del_list(line, 'right2')
        if swapped:
            left1, right1, left2, right2 = left2, right2, left1, right1
        if left1:
            self.add_re_context_to_cost_rule('left1', left1, cost_rule_id, line_number)
        if left2:
            self.add_re_context_to_cost_rule('left2', left2, cost_rule_id, line_number)
        if right1:
            self.add_letter_context_to_cost_rule('right1', right1, cost_rule_id, line_number)
        if right2:
            self.add_letter_context_to_cost_rule('right2', right2, cost_rule_id, line_number)

    def get_cost_rule_ids(self, s1: str, s2: str) -> List[str]:
        key1 = fr'COST\t{s1}\t{s2}'
        return self.ht.get(key1, ())

    def get_cost_rule_cost(self, s1: str, s2: str, cost_rule_id: str) -> float:
        key1 = fr'COST\t{s1}\t{s2}'
        return self.ht[key1][cost_rule_id]

    def cost_rules_include_string(self, side: str, s: str) -> bool:  # side is 's1' or 's2'
        return fr'{side}\t{s}' in self.ht

    def load_smart_edit_distance_data(self, raw_cost_file: TextIO, lang_code1: str, lang_code2: str) -> None:
        """Load cost file."""
        if isinstance(raw_cost_file, str):
            cost_file = open(raw_cost_file)
        else:
            cost_file = raw_cost_file
        filename = cost_file.name
        self.prev_line_number = 0
        line_number = 0
        n_warnings = 0
        for line in cost_file:
            line_number += 1
            if re.match(r'^\uFEFF?\s*(?:#.*)?$', line):  # ignore empty or comment line
                continue
            # Check whether cost file line is well-formed. Following call will output specific warnings.
            valid = double_colon_del_list_validation(line, line_number, filename,
                                                     valid_slots=['s1', 's2', 'cost', 'lc1', 'lc2',
                                                                  'left1', 'left2', 'right1', 'right2',
                                                                  'comment', 'example', 'suffix'],
                                                     required_slots=['s1', 's2', 'cost'])
            if not valid:
                n_warnings += 1
                continue
            s1 = slot_value_in_double_colon_del_list(line, 's1')
            s2 = slot_value_in_double_colon_del_list(line, 's2')
            cost = slot_value_in_double_colon_del_list(line, 'cost')
            if s1 is None or s2 is None or cost is None:
                continue
            try:
                cost = float(cost)
            except ValueError:
                log.warning(f'invalid non-float cost {cost} in line {line_number} in {filename}')
                continue
            # language codes, one for each side
            lc1 = slot_value_in_double_colon_del_list(line, 'lc1')
            lc2 = slot_value_in_double_colon_del_list(line, 'lc2')
            lang_codes1 = re.split(r',\s*', lc1) if lc1 else None
            lang_codes2 = re.split(r',\s*', lc2) if lc2 else None
            # Original order
            if ((lc1 is None) or (lang_code1 in lang_codes1)) \
                    and ((lc2 is None) or (lang_code2 in lang_codes2)):
                self.build_cost_rule(line, s1, s2, cost, line_number)
            # Swapped/inverted order. Similarity is symmetric,
            #    i.e. if 'ph' is similar to 'f', then 'f' is also similar to 'ph'.
            if ((lc1 is None) or (lang_code2 in lang_codes1)) \
                    and ((lc2 is None) or (lang_code1 in lang_codes2)):
                self.build_cost_rule(line, s2, s1, cost, line_number, swapped=True)
        lang_code1_clause = f' lc1: {lang_code1}' if lang_code1 else ''
        lang_code2_clause = f' lc2: {lang_code2}' if lang_code2 else ''
        log.info(f'Loaded {self.n_entries} entries from {line_number} lines '
                 f'in {filename}{lang_code1_clause}{lang_code2_clause}')
        if isinstance(raw_cost_file, str):
            cost_file.close()

    def cost_rule_left_context_failure(self, slot: str, s: str, start: int, end: int, cost_rule_id: str) -> bool:
        """At run-time, check if any left context requirement of a rule (regular expression) is satisfied or fails."""
        failure = False
        line_number = self.ht[fr'LINE\t{cost_rule_id}']
        key1 = f'{slot}\t{cost_rule_id}'  # slot if LEFT1 or LEFT2
        if key1 in self.ht:
            left_re = self.ht[key1]
            if left_re is not None:
                left_str = s[0:start]
                m = left_re.match(left_str)
                if m is None:
                    failure = True
                loc = f'line:{line_number} cr_id:{cost_rule_id}'
                log.debug(f' {loc} lr:{left_re} s:{s} [{start}-{end}] left:{left_str} failure:{failure}')
        return failure

    def cost_rule_right_context_failure(self, slot: str, s: str, start: int, end: int, cost_rule_id: str) -> bool:
        """At run-time, check if any right context requirement of a rule (set of letters) is satisfied or fails."""
        failure = False
        key1 = f'{slot}\t{cost_rule_id}'  # slot if RIGHT1 or RIGHT2
        line_number = self.ht[fr'LINE\t{cost_rule_id}']
        if key1 in self.ht:
            right_letters = self.ht[key1]
            if right_letters is not None:
                if end < len(s):
                    if s[end] not in right_letters:
                        failure = True
                else:  # at end of string
                    if '$' not in right_letters:
                        failure = True
                loc = f'line:{line_number} cr_id:{cost_rule_id}'
                log.debug(f' {loc} rl:{right_letters} s:{s} [{start}-{end}] failure:{failure}')
        return failure

    def cost_rule_context_failure(self, s1: str, s2: str, start1: int, start2: int, end1: int, end2: int,
                                  cost_rule_id: str) -> bool:
        """At run-time, check of context requirements are satisfied or fail."""
        return self.cost_rule_left_context_failure('LEFT1', s1, start1, end1, cost_rule_id) \
            or self.cost_rule_left_context_failure('LEFT2', s2, start2, end2, cost_rule_id) \
            or self.cost_rule_right_context_failure('RIGHT1', s1, start1, end1, cost_rule_id) \
            or self.cost_rule_right_context_failure('RIGHT2', s2, start2, end2, cost_rule_id)

    def string_distance_cost(self, s1: str, s2: str, max_cost: float = None, partial: bool = False, min_len: int = 4) \
            -> Union[Tuple[Optional[float], str], Tuple[Optional[float], str, Optional[int], Optional[int]]]:
        """The core function of the SmartEditDistance class.
        Returns a tuple of cost and cost-log (= cost explanation). Return cost of None marks failure.
        Optional: maximum allowable cost. The lower the maximum allowable cost, the more efficient the cost search."""
        log.debug(f'string_distance_cost({s1}, {s2})')
        len1 = len(s1)
        len2 = len(s2)
        cost_ij = {'0:0': 0}
        log_ij = {'0:0': ''}
        for start1 in range(len1+1):
            for end1 in range(start1, min(len1, start1+self.max1)+1):
                substr1 = s1[start1:end1]
                # Rule might be applicable if there is a matching rule with the corresponding substring
                # or the length is 0 or 1, in which case we want to allow deletion or substitution (default cost=1).
                if self.cost_rules_include_string('s1', substr1) or (len(substr1) <= 1):
                    log.debug(f'  sub1[{start1}:{end1}]:{substr1}')
                    for start2 in range(len2+1):
                        start_key = f'{start1}:{start2}'
                        if start_key in cost_ij:
                            preceding_cost = cost_ij[start_key]
                            preceding_log = log_ij[start_key]
                            for end2 in range(start2, min(len2, start2+self.max2)+1):
                                if (start1 != end1) or (start2 != end2):
                                    substr2 = s2[start2:end2]
                                    if self.cost_rules_include_string('s2', substr2) or (len(substr2) <= 1):
                                        failure_cost = 999999
                                        new_cost = failure_cost
                                        new_cost_rule_id = None
                                        if substr1 == substr2:
                                            new_cost = 0
                                        else:
                                            cost_rule_ids = self.get_cost_rule_ids(substr1, substr2)
                                            for cost_rule_id in cost_rule_ids:
                                                if self.cost_rule_context_failure(s1, s2, start1, start2,
                                                                                  end1, end2, cost_rule_id):
                                                    continue
                                                cost = self.get_cost_rule_cost(substr1, substr2, cost_rule_id)
                                                if cost < new_cost:
                                                    new_cost = cost
                                                    new_cost_rule_id = cost_rule_id
                                        if (new_cost > 1) and (len(substr1) <= 1) and (len(substr2) <= 1):
                                            new_cost = 1  # default cost for deletion, addition, substitution
                                        log.debug(f'    sub2[{start2}:{end2}]:{substr2}:{new_cost}')
                                        if new_cost <= failure_cost:
                                            total_cost = preceding_cost + new_cost
                                            if (max_cost is None) or (total_cost <= max_cost):
                                                end_key = f'{end1}:{end2}'
                                                if (end_key not in cost_ij) or (total_cost < cost_ij[end_key]):
                                                    cost_ij[end_key] = total_cost
                                                    if new_cost > 0:
                                                        log_elem = f'{substr1}:{substr2}:{new_cost}'
                                                        if new_cost_rule_id:
                                                            line_number = self.ht[fr'LINE\t{new_cost_rule_id}']
                                                            log_elem += ':l.' + str(line_number)
                                                    else:
                                                        log_elem = ''
                                                    log_ij[end_key] = concat2(preceding_log, log_elem, ';')
                                                    log.debug(f'      cost[{end_key}]:{total_cost}')
        if partial:
            best_l1, best_l2, best_length, best_cost, best_log = None, None, 0, 99, ''
            min_len1 = min(min_len, len1)
            min_len2 = min(min_len, len2)
            for l1 in range(min_len1, len1+1):
                for l2 in range(min_len2, len2+1):
                    combined_length = l1 + l2
                    key = f'{l1}:{l2}'
                    if key in cost_ij:
                        cost = cost_ij[key]
                        if (combined_length > best_length) or ((combined_length == best_length) and (cost < best_cost)):
                            best_l1, best_l2, best_length, best_cost, best_log = \
                                l1, l2, combined_length, cost, log_ij[key]
            if (best_l1 is not None) and (best_l2 is not None):
                return best_cost, best_log, best_l1, best_l2
            else:
                return None, '', None, None
        else:
            full_key = f'{len1}:{len2}'
            if full_key in cost_ij:
                total_cost = cost_ij[full_key]
                cost_log = log_ij[full_key]
                return total_cost, cost_log
            else:
                return None, ''


def main(argv) -> None:
    """Wrapper for processing arguments, handling files."""
    parser = argparse.ArgumentParser(description='Normalizes and cleans a given text')
    parser.add_argument('-c', '--cost', type=argparse.FileType('r', encoding='utf-8', errors='ignore'),
                        default=None, metavar='COST-FILENAME', help='(default: Levenshtein distance)')
    parser.add_argument('-i', '--input', type=argparse.FileType('r', encoding='utf-8', errors='ignore'),
                        default=sys.stdin, metavar='INPUT-FILENAME', help='(default: STDIN)')
    parser.add_argument('-o', '--output', type=argparse.FileType('w', encoding='utf-8', errors='ignore'),
                        default=sys.stdout, metavar='OUTPUT-FILENAME', help='(default: STDOUT)')
    parser.add_argument('--lc1', type=str, default='', metavar='LANGUAGE-CODE1',
                        help="of first string, e.g. 'hin' for Hindi (ISO 639-3), \
                        applies to any language-specific rules")
    parser.add_argument('--lc2', type=str, default='', metavar='LANGUAGE-CODE2', help="of second string ...")
    parser.add_argument('--maxcost', type=float, default=1.9, metavar='MAXIMUM-ALLOWABLE-COST',
                        help='to limit search and thus improve speed (default: 1.9)')
    # add program version; thanks to https://stackoverflow.com/a/15406624/1506477
    parser.add_argument('-v', '--version', action='version',
                        version=f'%(prog)s {__version__} last modified: {last_mod_date}')
    args = parser.parse_args(argv)
    # Initialize SmartEditDistance object.
    sd = SmartEditDistance()
    # Read in cost file.
    if args.cost:
        sd.load_smart_edit_distance_data(args.cost, args.lc1, args.lc2)

    # For testing purposes only. (Temporary code block.)
    # s1, s2 = 'क', 'ca'
    # s1, s2 = 'biark', 'birk'
    # cost, cost_log = sd.string_distance_cost(s1, s2, max_cost=2)
    # print(f'{s1}\t{s2}\t# cost: {cost}\t{cost_log}')
    # sys.exit("done")

    # Open any input or output files. Make sure utf-8 encoding is properly set (in older Python3 versions).
    if args.input is sys.stdin and not re.search('utf-8', sys.stdin.encoding, re.IGNORECASE):
        log.error(f"Bad STDIN encoding '{sys.stdin.encoding}' as opposed to 'utf-8'. \
                    Suggestion: 'export PYTHONIOENCODING=UTF-8' or use '--input FILENAME' option")
    if args.output is sys.stdout and not re.search('utf-8', sys.stdout.encoding, re.IGNORECASE):
        log.error(f"Error: Bad STDIN/STDOUT encoding '{sys.stdout.encoding}' as opposed to 'utf-8'. \
                    Suggestion: 'export PYTHONIOENCODING=UTF-8' or use use '--output FILENAME' option")

    # Input file has tab-separated lines, where first two fields contain the strings to be compared.
    # Optional third field is interpreted as a comment.
    for line in args.input:
        values = re.split(r'\t', line.rstrip(), 3)
        if len(values) >= 2:
            s1 = values[0]
            s2 = values[1]
            cost, cost_log = sd.string_distance_cost(s1.lower(), s2.lower(), max_cost=args.maxcost)
            if cost is None:  # string distance search failure (search cut short for cost > max-cost)
                cost = 99.99
            args.output.write(f'{s1}\t{s2}\t{str(round(cost,2))}\t# {cost_log}')
            if len(values) >= 3:
                args.output.write(f'\t{values[2]}')
            args.output.write('\n')


if __name__ == "__main__":
    main(sys.argv[1:])

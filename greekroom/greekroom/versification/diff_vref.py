#!/usr/bin/env python3

# This development auxiliary tool compares two different reversified corpora,
# allowing for a reference corpus (-r), corpus titles (-l); output in HTML format (-o)
# diff_vref.py file1.txt file2.txt -r file3.txt -l hbo-joel hbo-ulf ESV -v vref.txt -o diff_vref.html
# diff_vref.py ../hbo-8krPZAab.txt vers/f_usfm_reversified.txt -r ../en-ESVUS16.txt -l hbo-SIL hbo-GR ESV
#     -v ../vref.txt -o vref/diff_vref.html

import argparse
from collections import defaultdict
import datetime
from pathlib import Path
import regex
import sys
from typing import List
import uroman as ur


uroman = ur.Uroman()
uroman_dict = {}
n_uroman_elements = defaultdict(int)


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
        </style>
        <script type="text/javascript">
        <!--
        function toggle_uroman() {
            var i = 1;
            var s = null;
            if (s = document.getElementById('uroman')) {
                if (s.style.fontWeight == 'bold') {
                    s.style.fontWeight = 'normal';
                } else {
                    s.style.fontWeight = 'bold';
                }
            }
            while (s = document.getElementById('v' + i.toString())) {
                if (s.style.display == 'inline') {
                    s.style.display = 'none';
                } else {
                    s.style.display = 'inline';
                }
                i += 1;
            }
            i = 1;
            while (s = document.getElementById('d' + i.toString())) {
                if (s.dir == 'rtl') {
                    s.dir = 'ltr';
                } else {
                    s.dir = 'rtl';
                }
                i += 1;
            }
        }
        -->
        </script>
    </head>
    <body bgcolor="#FFFFEE">
        <table width="100%" border="0" cellpadding="0" cellspacing="0">
            <tr bgcolor="#BBCCFF">
                <td><table border="0" cellpadding="3" cellspacing="0">
                        <tr>
                            <td>&nbsp;&nbsp;&nbsp;</td>
                            <td><b><font class="large" size="+1">""" + title2 + """</font></b></td>
                            <td>&nbsp;&nbsp;<nobr>""" + date + """</nobr>&nbsp;&nbsp;</td>
                            <td style="color:#777777;font-size:80%;">Script by Ulf Hermjakob</td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table><p>
        <ul>
            <li> Color codes:
                    <span style='background-color:#BBDDFF;'>Shifted verse (head)</span> &nbsp;
                    <span style='background-color:#DDEEFF;'>Shifted verse (continuation)</span> &nbsp;
                    <span style='background-color:#FFE7E7;'>Merged verses (consecutive)</span> &nbsp;
                    <span style='background-color:#FFBBBB;'>Merged verses (non-consecutive)</span> &nbsp;
                    <span style='background-color:#FFAAFF;'>Partial match</span>
            <li> Click <span id='uroman' onclick='toggle_uroman();' 
                             style='text-decoration:underline;'>uroman</span> to romanize any foreign-script text.
        </ul>
"""


def print_html_foot(f_html) -> None:
    f_html.write('''
  </body>
</html>
''')


def guard_html(s: str):
    s = regex.sub('&', '&amp;', s)
    s = regex.sub('<', '&lt;', s)
    s = regex.sub('>', '&gt;', s)
    s = regex.sub('"', '&quot;', s)
    s = regex.sub("'", '&apos;', s)
    return s


def new_html_element_id(prefix: str) -> str:
    n_uroman_elements[prefix] += 1
    return f"{prefix}{n_uroman_elements[prefix]}"


def make_romanizable(s: str, lcode: str | None = None) -> str:
    letters = ''.join(regex.findall(r'\pL', s))
    n_letters = len(letters)
    n_latin = len(regex.findall(r'\p{Latin}', letters))
    if n_letters and (n_latin / n_letters < 0.2):
        rom_s = uroman_dict.get(s)
        if rom_s is None:
            rom_s = uroman.romanize_string(s, lcode)
            uroman_dict[s] = rom_s
        id1 = new_html_element_id("v")
        id2 = new_html_element_id("v")
        return (f"""<span id="{id1}" style="display:inline;">{guard_html(s)}</span>""" +
                f"""<span id="{id2}" style="display:none;">{guard_html(rom_s)}</span>""")
    else:
        return guard_html(s)


def string_is_right_to_left(s: str) -> bool:
    letters = ''.join(regex.findall(r'\pL', s))
    n_letters = len(letters)
    n_arabic = len(regex.findall(r'\p{Arabic}', letters))
    n_hebrew = len(regex.findall(r'\p{Hebrew}', letters))
    return n_arabic + n_hebrew > 0.5 * n_letters


def find_non_consecutive_matching_verses(s: str, line_number_to_verse_txt: dict, anchor_line_number_to_verse_txt: dict,
                                         center_line_number: int, prev_anchor_line_numbers: List[int]) \
        -> List[int | str]:
    for abs_line_diff in range(0, 21):
        for anchor_line_number in [center_line_number + abs_line_diff,
                                   center_line_number - abs_line_diff]:
            if ((anchor_line_number not in prev_anchor_line_numbers)
                    and (line_number_to_verse_txt[anchor_line_number]
                         != anchor_line_number_to_verse_txt[anchor_line_number])):
                anchor_verse_txt = anchor_line_number_to_verse_txt[anchor_line_number].rstrip()
                if s.startswith(anchor_verse_txt):
                    if remaining_text := s[len(anchor_verse_txt):].strip():
                        remaining_matches = find_non_consecutive_matching_verses(remaining_text,
                                                                                 line_number_to_verse_txt,
                                                                                 anchor_line_number_to_verse_txt,
                                                                                 anchor_line_number,
                                                                                 prev_anchor_line_numbers
                                                                                 + [anchor_line_number])
                        if remaining_matches:
                            return [anchor_line_number] + remaining_matches
                    else:
                        return [anchor_line_number]
    return []


def find_matching_verses(line_number: int, line_number_to_verse_txt: dict, anchor_line_number_to_verse_txt: dict,
                         verse_txt_to_anchor_line_numbers: dict, prev_line_number_diff: int | None = None) \
        -> List[int | str]:
    verse_text = line_number_to_verse_txt[line_number]
    if verse_text == '':
        return []
    anchor_verse_text = anchor_line_number_to_verse_txt[line_number]
    # match with same line_number
    if verse_text == anchor_verse_text:
        return [line_number]
    # match with some other (single) line
    if anchor_line_numbers := verse_txt_to_anchor_line_numbers[verse_text]:
        best_anchor_line_number = None
        best_line_number_diff = None
        for anchor_line_number in anchor_line_numbers:
            line_number_diff = line_number - anchor_line_number
            # same line_diff as for previous verse
            if (prev_line_number_diff is not None) and (line_number_diff == prev_line_number_diff):
                return [anchor_line_number]
            if (best_line_number_diff is None) or (abs(line_number_diff) < abs(best_line_number_diff)):
                best_anchor_line_number = anchor_line_number
                best_line_number_diff = line_number_diff
        if best_anchor_line_number is not None:
            return [best_anchor_line_number]
    # match with consecutive lines
    for abs_line_diff in range(0, 21):
        for anchor_start_line_number in [line_number - abs_line_diff, line_number + abs_line_diff]:
            anchor_line_number = anchor_start_line_number
            remaining_verse_text = verse_text.strip()
            while remaining_verse_text:
                anchor_verse_txt = anchor_line_number_to_verse_txt[anchor_line_number]
                if remaining_verse_text.startswith(anchor_verse_txt.strip()):
                    remaining_verse_text = remaining_verse_text[len(anchor_verse_txt.strip()):].strip()
                    anchor_line_number += 1
                else:
                    break
            if remaining_verse_text == '':
                return list(range(anchor_start_line_number, anchor_line_number))
    # match with non-consecutive lines
    if result := find_non_consecutive_matching_verses(verse_text.strip(),
                                                      line_number_to_verse_txt,
                                                      anchor_line_number_to_verse_txt,
                                                      line_number,
                                                      []):
        return result
    elif verse_text.startswith(anchor_verse_text):
        return [line_number, 'unknown']
    elif anchor_verse_text.startswith(verse_text):
        return [line_number, 'start']
    return []


def consecutive_integer_list(int_list: List[int]) -> bool:
    for i in range(1, len(int_list)):
        if int_list[i] != int_list[i-1] + 1:
            return False
    return True


def verse_id_pp(line_number_list: List[int], line_number_to_vref: dict) -> str:
    verse_ids = list(map(lambda line_number: line_number_to_vref.get(line_number) or line_number, line_number_list))
    return " + ".join(verse_ids)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input_filename', nargs='*', type=str)
    parser.add_argument('-r', '--reference_filename', nargs='*', type=str)
    parser.add_argument('-l', '--file_legend', nargs='*', type=str)
    parser.add_argument('-v', '--vref_filename', type=str, help='sentence IDs, e.g. GEN 1:1')
    parser.add_argument('-o', '--output_filename', type=Path, help="Diff visualization (html)")
    args = parser.parse_args()
    n_input_files = 0
    n_ref_files = 0
    line_number_to_vref = defaultdict(str)
    vref_to_line_number = defaultdict(int)
    line_number_to_verse_txt_list: List[dict] = []   # for each input and reference, defaultdict(str)
    verse_txt_to_line_numbers_list: List[dict] = []  # for each input, defaultdict(list)
    remap = defaultdict(int)
    with open(args.vref_filename) as f_vref:
        line_number = 0
        for line in f_vref:
            line = line.strip()
            line_number += 1
            line_number_to_vref[line_number] = line
            vref_to_line_number[line] = line_number
        n_vref_lines = line_number
    input_and_ref_filenames = args.input_filename + args.reference_filename
    n_input_and_ref_filenames = len(input_and_ref_filenames)
    for i, input_filename in enumerate(input_and_ref_filenames):
        input_p = (i < len(args.input_filename))
        if input_p:
            n_input_files += 1
        else:
            n_ref_files += 1
        with open(input_filename) as f_in:
            line_number = 0
            line_number_to_verse_txt = defaultdict(str)
            line_number_to_verse_txt_list.append(line_number_to_verse_txt)
            if input_p:
                verse_txt_to_line_numbers = defaultdict(list)
                verse_txt_to_line_numbers_list.append(verse_txt_to_line_numbers)
            for line in f_in:
                line = line.strip()
                line_number += 1
                line_number_to_verse_txt[line_number] = line
                if input_p:
                    verse_txt_to_line_numbers[line].append(line_number)
            if line_number != n_vref_lines:
                sys.stderr.write(f"Verse number mismatch: {n_vref_lines} ({args.vref_filename}) "
                                 f"!= {line_number} ({input_filename})\n")
    with open(args.output_filename, 'w') as f_html:
        date = f"{datetime.datetime.now():%B %-d, %Y at %-H:%M}"
        title = f"Greek Room Versification Diff"
        meta_title = 'VD'
        f_html.write(html_head(title, date, meta_title))
        f_html.write(f'  <table border="0" cellpadding="5" cellspacing="0">\n')
        f_html.write(f'     <tr><th>vref</th>')
        legends = []
        n_vref_diffs = 0
        for i in range(n_input_and_ref_filenames):
            input_p = (i < len(args.input_filename))
            if len(args.file_legend):
                legend = args.file_legend[i]
            elif input_p:
                legend = f"Input {i+1}"
            else:
                legend = f"Ref {i-n_input_files+1}"
            legends.append(legend)
            f_html.write(f"<th>{legend}</th>")
        f_html.write(f'</tr>\n')
        for line_number in range(1, n_vref_lines+1):
            found_diff = False
            anchor_index = n_input_files-1
            for i in range(anchor_index):
                if line_number_to_verse_txt_list[i][line_number] \
                        != line_number_to_verse_txt_list[anchor_index][line_number]:
                    found_diff = True
                    break
            if found_diff:
                n_vref_diffs += 1
                verse_id = line_number_to_vref[line_number]
                f_html.write(f"     <tr><td valign='top' patitle='{verse_id} at line {line_number}'>"
                             f"<nobr>{verse_id}</nobr></td>")
                anchor_index = n_input_files-1
                verse_txt_to_anchor_line_numbers = verse_txt_to_line_numbers_list[anchor_index]
                anchor_legend = legends[anchor_index]
                for i in range(n_input_and_ref_filenames):
                    # verbose = ((i == 0) and (1709 < line_number < 1714))
                    verse_text = line_number_to_verse_txt_list[i][line_number]
                    bgcolor = None
                    note = None
                    title = None
                    if i < anchor_index:
                        matching_anchor_line_numbers \
                            = find_matching_verses(line_number,
                                                   line_number_to_verse_txt_list[i],
                                                   line_number_to_verse_txt_list[anchor_index],
                                                   verse_txt_to_anchor_line_numbers,
                                                   remap.get((i, line_number-1)))
                        # if verbose: sys.stderr.write(f"  P.A {verse_id} {line_number} "
                        #                              f"{matching_anchor_line_numbers}\n")
                        if len(matching_anchor_line_numbers) == 1:
                            anchor_line_number = matching_anchor_line_numbers[0]
                            if anchor_line_number != line_number:
                                line_number_diff = line_number - anchor_line_number
                                prev_line_number_diff = remap.get((i, line_number - 1))
                                remap[(i, line_number)] = line_number_diff
                                anchor_verse_id_pp = verse_id_pp(matching_anchor_line_numbers, line_number_to_vref)
                                if line_number_diff == prev_line_number_diff:
                                    bgcolor = '#DDEEFF'
                                else:
                                    bgcolor = '#BBDDFF'
                                    # note = f" = {anchor_verse_id} of {legends[anchor_index]}"
                                title = f" = {anchor_verse_id_pp} of {anchor_legend}"
                        if len(matching_anchor_line_numbers) > 1:
                            anchor_verse_id_pp = verse_id_pp(matching_anchor_line_numbers, line_number_to_vref)
                            if any(map(lambda x: isinstance(x, str), matching_anchor_line_numbers)):
                                bgcolor = '#FFAAFF'
                            elif consecutive_integer_list(matching_anchor_line_numbers):
                                bgcolor = '#FFE7E7'
                            else:
                                bgcolor = "#FFBBBB"
                            title = f" = {anchor_verse_id_pp} of {anchor_legend}"
                            title = regex.sub(r'(.*?) \+ start', r'start(\1)', title)
                            title = regex.sub(r'(.*?) \+ unknown (of .*)', r'\1 \2 + unknown', title)
                    style_clause = ""
                    note_clause = ""
                    title_clause = ""
                    if bgcolor:
                        style_clause += " style='"
                        if bgcolor:
                            style_clause += f"background-color:{bgcolor};"
                        style_clause += "'"
                    if title:
                        title_clause = f" patitle='{title}'"
                    if note:
                        note_clause = f"<span style='color:red;'><nobr>{note}</nobr></span>"
                    if string_is_right_to_left(verse_text):
                        dir_clause = f''' dir="rtl"'''
                        td_id = new_html_element_id("d")
                        id_clause = f''' id="{td_id}"'''
                    else:
                        dir_clause, id_clause = "", ""
                    f_html.write(f"<td{id_clause} valign='top'{style_clause}{title_clause}{dir_clause}>"
                                 f"{make_romanizable(verse_text)}{note_clause}</td>")
                f_html.write(f"</tr>\n")
        f_html.write("  </table>\n")
        f_html.write(f"<p>\nNumber of vref diffs: {n_vref_diffs}\n")
        print_html_foot(f_html)
        sys.stderr.write(f"Number of vref diffs: {n_vref_diffs}\n")
        sys.stderr.write(f"Wrote diff viz to {args.output_filename}\n")


if __name__ == "__main__":
    main()

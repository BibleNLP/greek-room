#!/usr/bin/env python

# Import modules for CGI handling 
import argparse
import cgi
from collections import defaultdict
import datetime
import random
import re
import sys
# from typing import Optional, TextIO, Union


def print_html_head(f_html, date, e_lang_name, f_lang_name):
    f_html.write("""
<html>
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    <title>Alignments</title>
    <style>
      [patitle]:hover:after {opacity: 1; transition: all 0.05s ease 0.1s; visibility: visible;}
      [patitle]:after {
        content: attr(patitle);
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
        -moz-box-shadow: 0px 0px 4px #222;blue
        -webkit-box-shadow: 0px 0px 4px #222;
        box-shadow: 0px 0px 4px #222;
        font-size: 100%;
        background-color: #E0E7FF;
        opacity: 0;
        z-index: 99999;
        visibility: hidden;}
      [patitle] {position: relative; }
      [pbtitle]:hover:after {opacity: 1; transition: all 0.05s ease 0.1s; visibility: visible;}
      [pbtitle]:after {
        content: attr(pbtitle);
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
    </style>
    <script type="text/javascript">
    <!--
    function h(id, value) {
       if ((s = document.getElementById(id)) != null) {
          if (! s.origColor) {
             if (s.style.color) {
                s.origColor = s.style.color;
             } else {
                s.origColor = '#000000';
             }
          }
          if (! s.origFontWeight) {
             if (s.style.fontWeight) {
                s.origFontWeight = s.style.fontWeight;
             } else {
                s.origFontWeight = 'normal';
             }
          }
          if (value == '1') {
             s.style.color = '#0000FF';
             s.style.fontWeight = 'bold';
          } else if (value == '1+') {
             s.style.color = '#00AAFF';
             s.style.fontWeight = 'bold';
          } else if (value == '1-') {
             s.style.color = '#FF00FF';
             s.style.fontWeight = 'bold';
          } else {
             s.style.color = s.origColor;
             s.style.fontWeight = s.origFontWeight;
          }
       }
    }

    -->
    </script>
  </head>
  <body bgcolor="#FFFFEE">
      <table width="100%" border="0" cellpadding="0" cellspacing="0">
      <tr bgcolor="#BBCCFF">
        <td><table border="0" cellpadding="3" cellspacing="0"><tr>
          <td><b><font class="large2" size="+2">&nbsp; Alignment Visualization (Search Results)</font></b></td>
          <td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td>
          <td><table border="0" style="font-size:-1;">
                <tr><td>""" + e_lang_name + """ &ndash; """ + f_lang_name + """</td></tr>
                <tr><td>""" + date + """</td></tr></table></td>
          <td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td>
          <td><table border="0" style="color:#777777;font-size:-1;">
                <tr><td>Script filter-viz-snt-align.py version 0.0.7</td></tr>
                <tr><td>By Ulf Hermjakob, USC/ISI</td></tr></table></td>
      </tr>
    </table></td></tr></table><p>
""")


def print_html_foot(f_html):
    f_html.write("""
  </body>
</html>
""")


def highlight_search_term_tokens_in_text(text, search_term):
    """text is a string marked up with HTML tags; returns text with search_term highlighted in bold"""
    # Split text into text and tag tokens
    n_tokens = 0
    tag_dict = defaultdict(list)
    text_dict = defaultdict(str)
    highlight_dict = defaultdict(bool)
    text_without_tags = ''
    text_without_tags_to_token_index = defaultdict(int)
    text_position = 0
    rest1 = text
    while True:
        m2 = re.match(r'(<.*?>|\s+|[^<>\s]+|<|>)(.*)', rest1)
        if not m2:
            break
        element, rest1 = m2.group(1, 2)
        if element.startswith('<') or element.startswith('>'):
            tag_dict[n_tokens].append(element)
        else:
            text_dict[n_tokens] = element
            for pos in range(text_position, text_position + len(element)):
                text_without_tags_to_token_index[pos] = n_tokens
            text_without_tags += element
            text_position += len(element)
            n_tokens += 1
    # Identify text tokens to be highlighted
    text_position = 0
    rest2 = text_without_tags
    while True:
        m3 = re.match(r'(.*?)(' + re.escape(search_term) + ')(.*)$', rest2, re.IGNORECASE)
        if not m3:
            break
        pre, s, rest2 = m3.group(1, 2, 3)
        text_position += len(pre)
        for i in range(len(s)):
            token_index = text_without_tags_to_token_index[text_position]
            highlight_dict[token_index] = True
            text_position += 1
    # Build result
    result = ''
    for i in range(n_tokens):
        if highlight_dict[i]:
            updated_tag = None
            if tag_dict[i]:
                last_tag = tag_dict[i][-1]
                m3 = re.match(r'(.*? style=")([^"]*)(".*)$', last_tag)
                if m3:
                    pre, style, post = m3.group(1, 2, 3)
                    style = re.sub(r'font-weight:[-a-z]+;?', '', style)
                    style = re.sub(r'background-color:[-a-z]+;?', '', style)
                    if style and not style.endswith(';'):
                        style += ';'
                    style += 'font-weight:bold;background-color:yellow;'
                    updated_tag = pre + style + post
            if updated_tag:
                result += ''.join(tag_dict[i][:-1]) + updated_tag + text_dict[i]
            else:
                result += ''.join(tag_dict[i]) + '<span style="fontWeight:bold;">' + text_dict[i] + '</span>'
        else:
            result += ''.join(tag_dict[i]) + text_dict[i]
    result += ''.join(tag_dict[n_tokens]) + '\n'
    return result


def slot_value_in_double_colon_del_list(line, slot):
    """For a given slot, e.g. 'cost', get its value from a line such as '::s1 of course ::s2 ::cost 0.3' -> 0.3
    The value can be an empty string, as for ::s2 in the example above."""
    m = re.match(r'(?:.*\s)?::' + slot + r'(|\s+\S.*?)(?:\s+::\S.*|\s*)$', line)
    return m.group(1).strip() if m else None


def substring_of_any_in_list(s, class_list):
    return (class_list is not None) and (any(s in elem for elem in class_list))


def int_or_float(s, default):
    if isinstance(s, (int, float)):
        return s
    elif isinstance(s, str):
        try:
            x = float(s)
            return int(x) if x.is_integer() else x
        except ValueError or TypeError:
            return default
    else:
        return default


def log_message(fh, s):
    if fh:
        fh.write(s + '\n')


def is_in_line(sub_string, line, whole_word_p):
    if sub_string is None:
        return True
    elif whole_word_p:
        if re.search((r'\b' + sub_string + r'\b'), line):
            return True
    else:
        return (sub_string in line)
    return False


def main():
    date = datetime.datetime.now().strftime('%B %d, %Y at %H:%M')
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', '--e_search_term', type=str, help='can be regular expression', default=None)
    parser.add_argument('-f', '--f_search_term', type=str, help='can be regular expression', default=None)
    parser.add_argument('--e_search_terms', type=str, help=argparse.SUPPRESS, default=None)  # |-sep. list
    parser.add_argument('--f_search_terms', type=str, help=argparse.SUPPRESS, default=None)  # |-sep. list
    parser.add_argument('-t', '--text_filename', type=str, help='format: e ||| f ||| ref')
    parser.add_argument('-v', '--html_filename_dir', type=str, help='visualization input')
    parser.add_argument('-E', '--e_prop', type=str, help='can be regular expression', default=None)
    parser.add_argument('-F', '--f_prop', type=str, help='can be regular expression', default=None)
    parser.add_argument('-p', '--prop_filename', type=str, help='input, use alignment logfile')
    parser.add_argument('-l', '--log_filename', type=str, help='output')
    parser.add_argument('-n', '--max_number_output_snt', type=int, default=100)
    parser.add_argument('-s', '--sample_percentage', type=float, default=100)
    parser.add_argument('-a', '--auto_sample', type=bool, default=False)
    parser.add_argument('--e_lang_name', type=str, help='e.g. English', default='Source language')
    parser.add_argument('--f_lang_name', type=str, help='e.g. French', default='Target language')
    args = parser.parse_args()

    form = cgi.FieldStorage()
    log_filename = form.getvalue('log_filename') or args.log_filename
    try:
        f_log = open(log_filename, 'w')
    except FileNotFoundError:
        f_log = None

    log_message(f_log, 'Date: ' + date)

    e_search_term = form.getvalue('e_search_term') or args.e_search_term
    f_search_term = form.getvalue('f_search_term') or args.f_search_term
    e_search_term_s = form.getvalue('e_search_terms') or args.e_search_terms
    f_search_term_s = form.getvalue('f_search_terms') or args.f_search_terms
    e_search_terms = e_search_term_s.lower().split('|') if e_search_term_s else None
    f_search_terms = f_search_term_s.lower().split('|') if f_search_term_s else None
    e_whole_word_p = isinstance(e_search_terms, list) and len(e_search_terms) >= 2
    f_whole_word_p = isinstance(f_search_terms, list) and len(f_search_terms) >= 2
    text_filename = form.getvalue('text_filename') or args.text_filename
    html_filename_dir = form.getvalue('html_filename_dir') or args.html_filename_dir
    e_prop = form.getvalue('e_prop') or args.e_prop
    f_prop = form.getvalue('f_prop') or args.f_prop
    prop_filename = form.getvalue('prop_filename') or args.prop_filename
    max_number_output_snt = int_or_float(form.getvalue('max_number_output_snt'), 0) or args.max_number_output_snt or 100
    auto_sample_percentage = form.getvalue('auto_sample') or args.auto_sample
    sample_percentage = int_or_float(form.getvalue('sample_percentage'), 0) or args.sample_percentage or 100
    sample_fraction = sample_percentage * 0.01

    e_lang_name = form.getvalue('e_lang_name') or args.e_lang_name
    f_lang_name = form.getvalue('f_lang_name') or args.f_lang_name

    e_search_term = e_search_term.lower() if isinstance(e_search_term, str) else None
    f_search_term = f_search_term.lower() if isinstance(f_search_term, str) else None

    log_message(f_log, 'e_search_term: ' + str(e_search_term))
    log_message(f_log, 'f_search_term: ' + str(f_search_term))
    log_message(f_log, 'e_search_terms: ' + str(e_search_term_s))
    log_message(f_log, 'f_search_terms: ' + str(f_search_term_s))
    log_message(f_log, 'text_filename: ' + str(text_filename))
    log_message(f_log, 'html_filename_dir: ' + str(html_filename_dir))
    log_message(f_log, 'log_filename: ' + str(log_filename))
    log_message(f_log, 'e_prop: ' + str(e_prop))
    log_message(f_log, 'f_prop: ' + str(f_prop))
    log_message(f_log, 'prop_filename: ' + str(prop_filename))
    log_message(f_log, 'max_number_output_snt: ' + str(max_number_output_snt))
    log_message(f_log, 'auto_sample_percentage: ' + str(auto_sample_percentage))
    log_message(f_log, 'sample_percentage: ' + str(sample_percentage))
    log_message(f_log, 'sample_fraction: ' + str(sample_fraction))
    log_message(f_log, 'e_lang_name: ' + str(e_lang_name))
    log_message(f_log, 'f_lang_name: ' + str(f_lang_name))

    prop_dict = defaultdict(list)
    if prop_filename:
        with open(prop_filename) as f_in_prop:
            for line in f_in_prop:
                side = slot_value_in_double_colon_del_list(line, 'side')
                snt_id = slot_value_in_double_colon_del_list(line, 'snt-id')
                prop_class = slot_value_in_double_colon_del_list(line, 'class')
                prop_dict[(side, snt_id)].append(prop_class)

    print("Content-type:text/html\r\n\r\n")
    print_html_head(sys.stdout, date, e_lang_name, f_lang_name)
    e_search_term2 = e_search_term if e_search_term else "<i>None</i>"
    f_search_term2 = f_search_term if f_search_term else "<i>None</i>"
    e_prop2 = e_prop if e_prop else "<i>None</i>"
    f_prop2 = f_prop if f_prop else "<i>None</i>"
    if e_search_terms:
        sys.stdout.write(e_lang_name + ' search terms: ' + ', '.join(e_search_terms) + '<br>\n')
    elif e_search_term:
        sys.stdout.write(e_lang_name + ' search term: ' + e_search_term2 + '<br>\n')
    if f_search_terms:
        sys.stdout.write(f_lang_name + ' search terms: ' + ', '.join(f_search_terms) + '<br>\n')
    elif f_search_term:
        sys.stdout.write(f_lang_name + ' search term: ' + f_search_term2 + '<br>\n')
    if e_prop:
        sys.stdout.write(e_lang_name + ' meta info restriction: ' + e_prop2 + '<br>\n')
    if f_prop:
        sys.stdout.write(f_lang_name + ' meta info restriction: ' + f_prop2 + '<br>\n')
    if e_search_terms:
        primary_search_side = 'e'
        e_search_terms3 = e_search_terms
        f_search_terms3 = [f_search_term]
    elif f_search_terms:
        primary_search_side = 'f'
        e_search_terms3 = [e_search_term]
        f_search_terms3 = f_search_terms
    else:
        primary_search_side = None
        e_search_terms3 = [e_search_term]
        f_search_terms3 = [f_search_term]
    log_message(f_log, 'e_search_terms3: ' + ', '.join(map(str, e_search_terms3)))
    log_message(f_log, 'f_search_terms3: ' + ', '.join(map(str, f_search_terms3)))
    log_message(f_log, 'Point B0')
    # sys.stdout.write('<font color="#999999">Other input parameters &nbsp; '
    #                  't: %s &nbsp; dir: %s &nbsp; log: %s &nbsp; max: %d</font><br>\n'
    #                  % (text_filename, html_filename_dir, log_filename, max_number_output_snt))
    try:
        f_in = open(text_filename)
    except BaseException as error:
        sys.stdout.write('<span style="color:red;">Error: Cannot open ' + text_filename
                         + ' [' + str(error) + ']<span><br>\n')
    else:
        n_match_dict = defaultdict(int)
        viz_file_dict = defaultdict(list)  # a_name_ids per (viz_file, e_search_term|'')
        viz_file_list = []
        log_message(f_log, 'Point B1 ' + str(e_search_terms3) + ' :: ' + str(f_search_terms3))
        for line in f_in:
            m3a = re.match(r'(\S|\S.*?\S)\s+\|\|\|\s+(\S|\S.*?\S)\s+\|\|\|\s+(\S|\S.*?\S)\s*$', line)
            if m3a:
                e = m3a.group(1).lower()
                f = m3a.group(2).lower()
                ref = m3a.group(3)
                e_prop_dict_classes = prop_dict.get(('e', ref))
                f_prop_dict_classes = prop_dict.get(('f', ref))
                for e_search_term3 in e_search_terms3:
                    for f_search_term3 in f_search_terms3:
                        if primary_search_side == 'e':
                            k = e_search_term3
                        elif primary_search_side == "f":
                            k = f_search_term3
                        else:
                            k = ''
                        if is_in_line(e_search_term3, e, e_whole_word_p) \
                                and is_in_line(f_search_term3, f, f_whole_word_p) \
                                and (e_prop is None or substring_of_any_in_list(e_prop, e_prop_dict_classes)) \
                                and (f_prop is None or substring_of_any_in_list(f_prop, f_prop_dict_classes)):
                            n_match_dict[k] += 1
                            m3b = re.match(r'([A-Z1-9][A-Z][A-Z])\s*(\d+):(\d+)$', ref)
                            if m3b:
                                book, chapter_number, verse_number = m3b.group(1), int(m3b.group(2)), int(m3b.group(3))
                                viz_filename = '%s-%03d.html' % (book, chapter_number)
                                a_name_id = '%s_%d:%d' % (book, chapter_number, verse_number)
                                viz_file_dict[(viz_filename, k)].append(a_name_id)
                                if viz_filename not in viz_file_list:
                                    viz_file_list.append(viz_filename)
                                # sys.stdout.write(viz_filename + ' ' + a_name_id + '<br>\n')
        if primary_search_side is None:
            n_matches = n_match_dict['']
            plural_ending = '' if n_matches == 1 else 'es'
            sys.stdout.write('Found ' + str(n_matches) + ' match' + plural_ending)
            if n_matches > max_number_output_snt:
                if auto_sample_percentage:
                    sys.stdout.write(', random sample of ' + str(max_number_output_snt) + ' shown')
                elif sample_percentage < 100:
                    sys.stdout.write(', random ' + str(sample_percentage) + '% sample up to '
                                     + str(max_number_output_snt) + ' shown')
                else:
                    sys.stdout.write(', first ' + str(max_number_output_snt) + ' shown')
            elif sample_percentage < 100:
                sys.stdout.write(', random ' + str(sample_percentage) + '% sample shown')
            sys.stdout.write('<br><br>\n')
        f_in.close()
        log_message(f_log, 'Point C1 ' + str(n_match_dict))
        n_matches_shown = defaultdict(int)
        n_matches_remaining = defaultdict(int)
        n_matches_remaining_to_be_shown = defaultdict(int)
        output_dict = defaultdict(str)
        for k in n_match_dict:
            n_matches_shown[k] = 0
            n_matches_remaining[k] = n_match_dict[k]
            n_matches_remaining_to_be_shown[k] = max_number_output_snt
            if k != '':
                plural_ending = '' if n_match_dict[k] == 1 else 'es'
                output_dict[k] = '<p>\nFound ' + str(n_match_dict[k]) + ' match' + plural_ending \
                                 + ' for ' + k + ':<br>\n'
        log_message(f_log, 'Point C2 ' + str(viz_file_list))
        for viz_filename in viz_file_list:
            full_viz_filename = html_filename_dir + '/' + viz_filename
            try:
                with open(full_viz_filename) as f_in:
                    lines = f_in.readlines()
            except BaseException as error:
                sys.stdout.write('<span style="color:red;">Error: Cannot open ' + full_viz_filename
                                 + ' [' + str(error) + ']<span><br>\n')
            else:
                for e_search_term3 in e_search_terms3:
                    for f_search_term3 in f_search_terms3:
                        if primary_search_side == 'e':
                            k = e_search_term3
                            n_match_dict[e_search_term3] += 1
                        elif primary_search_side == 'f':
                            k = f_search_term3
                            n_match_dict[f_search_term3] += 1
                        else:
                            k = ''
                        log_message(f_log, 'Point K ' + str(e_search_term3) + ' :: ' + str(f_search_term3) + ' :: ' + str(viz_filename) + ' ::k ' + str(k) + ' ::c ' + str(n_matches_shown[k]))
                        active = False
                        selected = False
                        active_line_index = 0
                        a_name_ids = viz_file_dict[(viz_filename, k)]
                        log_message(f_log, 'Point L ' + str(a_name_ids))
                        next_a_name_id = a_name_ids.pop(0) if a_name_ids else None
                        for line in lines:
                            if active and '<a name="' in line:
                                if selected:
                                    if n_matches_remaining_to_be_shown[k]:
                                        n_matches_shown[k] += 1
                                        n_matches_remaining_to_be_shown[k] -= 1
                                n_matches_remaining[k] -= 1
                                active = False
                                if next_a_name_id is None:
                                    break
                                if n_matches_shown[k] >= max_number_output_snt:
                                    break
                            if next_a_name_id and '<a name="' + next_a_name_id + '">' in line:
                                active = True
                                active_line_index = 0
                                if auto_sample_percentage and n_matches_remaining[k] > 0:
                                    selected = (random.random()
                                                < float(n_matches_remaining_to_be_shown[k]) / n_matches_remaining[k])
                                elif sample_percentage < 100:
                                    r = random.random()
                                    selected = (r < sample_fraction)
                                else:
                                    selected = True
                                next_a_name_id = a_name_ids.pop(0) if a_name_ids else None
                            if active:
                                if selected:
                                    if active_line_index or re.match('<span id="', line):
                                        active_line_index += 1
                                    if e_search_term3 and active_line_index == 1:
                                        line = highlight_search_term_tokens_in_text(line, e_search_term3)
                                    elif f_search_term3 and active_line_index == 2:
                                        line = highlight_search_term_tokens_in_text(line, f_search_term3)
                                        log_message(f_log, 'Point O ' + re.sub(r'<.*?>', '', line.rstrip()))
                                    if n_matches_remaining_to_be_shown[k]:
                                        output_dict[k] += line
        for k in output_dict:
            sys.stdout.write(output_dict[k])
            sys.stdout.write(str(n_matches_shown[k]) + ' shown<br><br><br><br>\n')

    log_message(f_log, 'Point X')
    print_html_foot(sys.stdout)
    sys.stdout.flush()
    if f_log:
        f_log.close()


if __name__ == "__main__":
    main()

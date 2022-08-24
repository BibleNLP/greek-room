#!/usr/bin/env python

# Import modules for CGI handling
import argparse

import logging

# import cgi
import flask
from flask import request

from collections import defaultdict
import datetime
import random
import re
import sys

# from typing import Optional, TextIO, Union


_LOGGER = logging.getLogger(__name__)


def print_html_head(date, e_lang_name, f_lang_name):
    return (
        """
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
                <tr><td>"""
        + e_lang_name
        + """ &ndash; """
        + f_lang_name
        + """</td></tr>
                <tr><td>"""
        + date
        + """</td></tr></table></td>
          <td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td>
          <td><table border="0" style="color:#777777;font-size:-1;">
                <tr><td>Script filter-viz-snt-align.py version 0.0.5</td></tr>
                <tr><td>By Ulf Hermjakob, USC/ISI</td></tr></table></td>
      </tr>
    </table></td></tr></table><p>
"""
    )


def print_html_foot():
    return """
  </body>
</html>
"""


def highlight_search_term_tokens_in_text(text, search_term):
    """text is a string marked up with HTML tags; returns text with search_term highlighted in bold"""
    # Split text into text and tag tokens
    n_tokens = 0
    tag_dict = defaultdict(list)
    text_dict = defaultdict(str)
    highlight_dict = defaultdict(bool)
    text_without_tags = ""
    text_without_tags_to_token_index = defaultdict(int)
    text_position = 0
    rest1 = text
    while True:
        m2 = re.match(r"(<.*?>|\s+|[^<>\s]+|<|>)(.*)", rest1)
        if not m2:
            break
        element, rest1 = m2.group(1, 2)
        if element.startswith("<") or element.startswith(">"):
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
        m3 = re.match(
            r"(.*?)(" + re.escape(search_term) + ")(.*)$", rest2, re.IGNORECASE
        )
        if not m3:
            break
        pre, s, rest2 = m3.group(1, 2, 3)
        text_position += len(pre)
        for i in range(len(s)):
            token_index = text_without_tags_to_token_index[text_position]
            highlight_dict[token_index] = True
            text_position += 1
    # Build result
    result = ""
    for i in range(n_tokens):
        if highlight_dict[i]:
            updated_tag = None
            if tag_dict[i]:
                last_tag = tag_dict[i][-1]
                m3 = re.match(r'(.*? style=")([^"]*)(".*)$', last_tag)
                if m3:
                    pre, style, post = m3.group(1, 2, 3)
                    style = re.sub(r"font-weight:[-a-z]+;?", "", style)
                    style = re.sub(r"background-color:[-a-z]+;?", "", style)
                    if style and not style.endswith(";"):
                        style += ";"
                    style += "font-weight:bold;background-color:yellow;"
                    updated_tag = pre + style + post
            if updated_tag:
                result += "".join(tag_dict[i][:-1]) + updated_tag + text_dict[i]
            else:
                result += (
                    "".join(tag_dict[i])
                    + '<span style="fontWeight:bold;">'
                    + text_dict[i]
                    + "</span>"
                )
        else:
            result += "".join(tag_dict[i]) + text_dict[i]
    result += "".join(tag_dict[n_tokens]) + "\n"
    return result


def slot_value_in_double_colon_del_list(line, slot):
    """For a given slot, e.g. 'cost', get its value from a line such as '::s1 of course ::s2 ::cost 0.3' -> 0.3
    The value can be an empty string, as for ::s2 in the example above."""
    m = re.match(r"(?:.*\s)?::" + slot + r"(|\s+\S.*?)(?:\s+::\S.*|\s*)$", line)
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


def main(
    e_search_term=None,
    f_search_term=None,
    text_filename=None,
    html_filename_dir=None,
    log_filename=None,
    e_prop=None,
    f_prop=None,
    prop_filename=None,
    max_number_output_snt=None,
    auto_sample_percentage=None,
    sample_percentage=None,
    e_lang_name=None,
    f_lang_name=None,
):
    date = datetime.datetime.now().strftime("%B %d, %Y at %H:%M")

    # form = cgi.FieldStorage()
    # e_search_term = request.form.get("e_search_term") or args.e_search_term
    # f_search_term = request.form.get("f_search_term") or args.f_search_term

    # text_filename = request.form.get("text_filename") or args.text_filename

    text_filename = f'{flask.current_app.config["ENG_HIN_REF_FILE"]}'

    # html_filename_dir = request.form.get("html_filename_dir") or args.html_filename_dir
    # log_filename = request.form.get("log_filename") or args.log_filename
    # e_prop = request.form.get("e_prop") or args.e_prop
    # f_prop = request.form.get("f_prop") or args.f_prop
    # prop_filename = request.form.get("prop_filename") or args.prop_filename
    # max_number_output_snt = (
    #     int_or_float(request.form.get("max_number_output_snt"), 0)
    #     or args.max_number_output_snt
    #     or 100
    # )
    # auto_sample_percentage = request.form.get("auto_sample") or args.auto_sample
    # sample_percentage = (
    #     int_or_float(request.form.get("sample_percentage"), 0)
    #     or args.sample_percentage
    #     or 100
    # )
    sample_fraction = sample_percentage * 0.01

    # e_lang_name = request.form.get("e_lang_name") or args.e_lang_name
    # f_lang_name = request.form.get("f_lang_name") or args.f_lang_name

    # e_search_term = e_search_term.lower() if isinstance(e_search_term, str) else None
    # f_search_term = f_search_term.lower() if isinstance(f_search_term, str) else None

    if log_filename:
        f_log = open(log_filename, "w")
        f_log.write(date + "\n")
    else:
        f_log = None

    prop_dict = defaultdict(list)

    prop_filename = f'{flask.current_app.config["ENG_HIN_PROP_FILE"]}'

    if prop_filename:
        with open(prop_filename) as f_in_prop:
            for line in f_in_prop:
                side = slot_value_in_double_colon_del_list(line, "side")
                snt_id = slot_value_in_double_colon_del_list(line, "snt-id")
                prop_class = slot_value_in_double_colon_del_list(line, "class")
                prop_dict[(side, snt_id)].append(prop_class)

    generated_html = []
    generated_html.append("Content-type:text/html\r\n\r\n")
    generated_html.append(print_html_head(date, e_lang_name, f_lang_name))
    e_search_term2 = e_search_term if e_search_term else "<i>None</i>"
    f_search_term2 = f_search_term if f_search_term else "<i>None</i>"
    e_prop2 = e_prop if e_prop else "<i>None</i>"
    f_prop2 = f_prop if f_prop else "<i>None</i>"
    generated_html.append(f'{e_lang_name} " search term: "{e_search_term2}"<br>\n")')
    generated_html.append(f'{f_lang_name}" search term: "{f_search_term2}"<br>\n")')
    generated_html.append(f'{f_lang_name}" search term: "{f_search_term2}"<br>\n")')
    generated_html.append(f'{e_lang_name}" meta info restriction: "{e_prop2}"<br>\n")')
    generated_html.append(f'{f_lang_name}" meta info restriction: "{f_prop2}"<br>\n")')
    # sys.stdout.write('<font color="#999999">Other input parameters &nbsp; '
    #                  't: %s &nbsp; dir: %s &nbsp; log: %s &nbsp; max: %d</font><br>\n'
    #                  % (text_filename, html_filename_dir, log_filename, max_number_output_snt))
    try:
        f_in = open(text_filename)
    except BaseException as error:
        generated_html.append(
            f'<span style="color:red;">Error: Cannot open {text_filename} [{str(error)}]<span><br>\n"'
        )
    else:
        n_matches = 0
        viz_file_dict = defaultdict(list)
        viz_file_list = []
        for line in f_in:
            m3a = re.match(
                r"(\S|\S.*?\S)\s+\|\|\|\s+(\S|\S.*?\S)\s+\|\|\|\s+(\S|\S.*?\S)\s*$",
                line,
            )
            if m3a:
                e = m3a.group(1).lower()
                f = m3a.group(2).lower()
                ref = m3a.group(3)
                e_prop_dict_classes = prop_dict.get(("E", ref))
                f_prop_dict_classes = prop_dict.get(("F", ref))
                if (
                    (e_search_term is None or e_search_term in e)
                    and (f_search_term is None or f_search_term in f)
                    and (
                        e_prop is None
                        or substring_of_any_in_list(e_prop, e_prop_dict_classes)
                    )
                    and (
                        f_prop is None
                        or substring_of_any_in_list(f_prop, f_prop_dict_classes)
                    )
                ):
                    n_matches += 1
                    m3b = re.match(r"([A-Z1-9][A-Z][A-Z])\s*(\d+):(\d+)$", ref)
                    if m3b:
                        book, chapter_number, verse_number = (
                            m3b.group(1),
                            int(m3b.group(2)),
                            int(m3b.group(3)),
                        )
                        viz_filename = "%s-%03d.html" % (book, chapter_number)
                        a_name_id = "%s_%d:%d" % (book, chapter_number, verse_number)
                        viz_file_dict[viz_filename].append(a_name_id)
                        if viz_filename not in viz_file_list:
                            viz_file_list.append(viz_filename)
                        # sys.stdout.write(viz_filename + ' ' + a_name_id + '<br>\n')
                plural_ending = "" if n_matches == 1 else "es"
                generated_html.append(f"Found {str(n_matches)} match{plural_ending}")
        if n_matches > max_number_output_snt:
            if auto_sample_percentage:
                generated_html.append(
                    f", random sample of {str(max_number_output_snt)} shown"
                )
            elif sample_percentage < 100:
                generated_html.append(
                    f", random {str(sample_percentage)}% sample up to {str(max_number_output_snt)} shown"
                )
            else:
                generated_html.append(f", first {str(max_number_output_snt)} shown")
        elif sample_percentage < 100:
            generated_html.append(f", random {str(sample_percentage)}% sample shown")
        generated_html.append("<br><br>\n")
        f_in.close()
        n_matches_shown = 0
        n_matches_remaining = n_matches
        n_matches_remaining_to_be_shown = max_number_output_snt
        for viz_filename in viz_file_list:
            full_viz_filename = html_filename_dir + "/" + viz_filename
            try:
                f_in = open(full_viz_filename)
            except BaseException as error:
                sys.stdout.write(
                    '<span style="color:red;">Error: Cannot open '
                    + full_viz_filename
                    + " ["
                    + str(error)
                    + "]<span><br>\n"
                )
            else:
                active = False
                selected = False
                active_line_index = 0
                a_name_ids = viz_file_dict[viz_filename]
                next_a_name_id = a_name_ids.pop(0)
                for line in f_in:
                    if active and '<a name="' in line:
                        if selected:
                            n_matches_shown += 1
                            if n_matches_remaining_to_be_shown:
                                n_matches_remaining_to_be_shown -= 1
                        n_matches_remaining -= 1
                        active = False
                        if next_a_name_id is None:
                            break
                        if n_matches_shown >= max_number_output_snt:
                            break
                    if next_a_name_id and '<a name="' + next_a_name_id + '">' in line:
                        active = True
                        active_line_index = 0
                        if auto_sample_percentage and n_matches_remaining > 0:
                            selected = (
                                random.random()
                                < float(n_matches_remaining_to_be_shown)
                                / n_matches_remaining
                            )
                        elif sample_percentage < 100:
                            r = random.random()
                            selected = r < sample_fraction
                        else:
                            selected = True
                        next_a_name_id = a_name_ids.pop(0) if a_name_ids else None
                    if active:
                        if selected:
                            if active_line_index or re.match('<span id="', line):
                                active_line_index += 1
                            if e_search_term and active_line_index == 1:
                                line = highlight_search_term_tokens_in_text(
                                    line, e_search_term
                                )
                            elif f_search_term and active_line_index == 2:
                                line = highlight_search_term_tokens_in_text(
                                    line, f_search_term
                                )
                            generated_html.append(line)
                f_in.close()
            if n_matches_shown >= max_number_output_snt:
                break
        generated_html.append(f"{str(n_matches_shown)} shown<br><br><br><br>\n")
    generated_html.append(print_html_foot())
    return "\n".join(generated_html)

    # if f_log:
    #     sys.stderr.write("Log: %s\n" % log_filename)
    #     f_log.close()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# /Users/ulf2/jupyter/notebook
# color_diff.py tam-1RCipbPi.txt tam-A2aO4fh5.txt -l OV IRV -r en-ESVUS16.txt -s vref.txt -o tam-diff.html

from __future__ import annotations
import argparse
import datetime
import regex
import sys
from typing import Tuple


def html_head(title: str, date: str, meta_title: str) -> str:
    """
    Build the head of an output HTML file, including a title, date, and meta_title (shown in browser tab)
    """
    title2 = regex.sub(r' {2,}', '<br>', title)
    return f"""<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
        <title>{meta_title}</title>  
        <script type="text/javascript">
        <!--
        """ + """
        function toggle_info(j) {
            if ((s = document.getElementById(j)) != null) {
                if (s.style.display == 'inline') {
                    s.style.display = 'none';
                } else {
                    s.style.display = 'inline';
                }
            }
        }
        """ + f"""
        </script>
    </head>
    <body bgcolor="#FFFFEE">
        <table width="100%" border="0" cellpadding="0" cellspacing="0">
            <tr bgcolor="#BBCCFF">
                <td><table border="0" cellpadding="3" cellspacing="0">
                        <tr>
                            <td>&nbsp;&nbsp;&nbsp;</td>
                            <td><b><font class="large" size="+1">{title2}</font></b></td>
                            <td>&nbsp;&nbsp;&nbsp;</td>
                            <td>{date}</td>
                            <td>&nbsp;&nbsp;&nbsp;</td>
                            <td style="color:#777777;font-size:80%;">Script by Ulf Hermjakob</td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table><p>
"""


def print_html_foot(f_html):
    f_html.write('''
  </body>
</html>
''')


def guard_html(s: str, space: bool = False, diff: bool = False, output_var: bool = False) -> str:
    # escape HTML special characters
    s = regex.sub('&', '&amp;', s)
    s = regex.sub('<', '&lt;', s)
    s = regex.sub('>', '&gt;', s)
    s = regex.sub('"', '&quot;', s)
    s = regex.sub("'", '&apos;', s)
    if diff:
        s = s.replace('\n', '\n')
        s = regex.sub(r'_{8,}', '<hr>', s)
        # make the invisible visible, used in context of string comparison ("diff")
        # if s == '':
        #     s = '‸'
        if not output_var:
            s = regex.sub(r' {2,}', len(r'\1') * '␣', s)
            s = regex.sub(r' $', '␣', s)
            s = regex.sub(r'^ ', '␣', s)
    if space:
        # escape space character to show multiple spaces in HTML output
        s = regex.sub(" ", '&nbsp;', s)
    return s


class ColoredSpan:
    def __init__(self, s: str, start: int, end: int, col_diff: ColorDiff, full_s: str | None = None):
        self.s = s
        self.colored_s = s
        self.full_s = full_s or s
        self.score = None
        self.start = start
        self.end = end
        self.len = end - start
        self.left_color = None  # inside span
        self.right_color = None  # inside span
        self.col_diff = col_diff

    def __str__(self):
        result = f"Orig: {self.s} [{self.start}-{self.end}]<br>\n"
        result += f"Colored: {self.colored_s}<br>\n"
        if self.score:
            result += f"Score: {self.score}<br>\n"
        if self.left_color:
            result += f"Left: {self.left_color}<br>\n"
        if self.right_color:
            result += f"Right: {self.right_color}<br>\n"
        return result

    def span_split(self, core_start: int, core_end: int, color_code: str) \
            -> Tuple[ColoredSpan | None, ColoredSpan, ColoredSpan | None]:
        left = ColoredSpan(self.s[:core_start], self.start, self.start + core_start, self.col_diff,
                           self.full_s) if core_start > 0 else None
        core = ColoredSpan(self.s[core_start:core_end], self.start + core_start, self.start + core_end, self.col_diff,
                           self.full_s)
        right = ColoredSpan(self.s[core_end:], self.start + core_end, self.end, self.col_diff,
                            self.full_s) if core_end < self.len else None
        if color_code == "green":
            open_tag = self.col_diff.green_tag
        elif color_code == "red":
            open_tag = self.col_diff.red_tag
        elif color_code == "blue":
            open_tag = self.col_diff.blue_tag
        else:
            open_tag = None
        if open_tag:
            core.colored_s = open_tag + guard_html(core.s) + self.col_diff.close_tag
            core.left_color = color_code
            core.right_color = color_code
        return left, core, right

    def color_red(self) -> None:
        s = self.s
        len1 = len(s)
        s = s.lstrip(' ')
        len2 = len(s)
        s = s.rstrip(' ')
        len3 = len(s)
        s = ('␣' * (len1 - len2)) + s + ('␣' * (len2 - len3))
        # s = s.replace('\n', '\u21B5\n')
        s = s.replace('\t', '\u21E5')
        s = s.replace('\r', '\u240D')
        self.colored_s = (self.col_diff.red_tag
                          + guard_html(s, diff=True)
                          + self.col_diff.close_tag)

    @staticmethod
    def color_red_non_none(c1: ColoredSpan | None, c2: ColoredSpan | None) -> None:
        if c1:
            c1.color_red()
        if c2:
            c2.color_red()

    def span_concat(self, left: ColoredSpan | None, right: ColoredSpan | None) -> ColoredSpan:
        if left is None and right is None:
            return self
        else:
            concat = ColoredSpan(self.s, self.start, self.end, self.col_diff, self.full_s)
            concat.colored_s = self.colored_s
            concat.len = self.len
            concat.left_color = self.left_color
            concat.right_color = self.right_color
            if left:
                concat.s = left.s + concat.s
                sep = self.col_diff.sep_tag if (left.right_color == concat.left_color) else ''
                concat.colored_s = left.colored_s + sep + concat.colored_s
                concat.start = left.start
                concat.len += left.len
                concat.left_color = left.left_color
            if right:
                concat.s += right.s
                sep = self.col_diff.sep_tag if (concat.right_color == right.left_color) else ''
                concat.colored_s += sep + right.colored_s
                concat.end = right.end
                concat.len += right.len
                concat.right_color = right.right_color
            return concat

    def score_penalty(self, pos: int, lc: ColoredSpan | None, rc: ColoredSpan | None) -> float:
        # if verbose: print("TP", repr(self.s), pos, verbose)
        if pos:
            left = self.s[:pos]
        elif lc:
            left = lc.s or '\n'
        else:
            left = '\n'
        if pos < len(self.s):
            right = self.s[pos:]
        elif rc:
            right = rc.s or '\n'
        else:
            right = '\n'
        if left.endswith('\n') and right.startswith('\n'):
            return 0.0
        # splitting between letters
        if regex.search(r'\pL\pM*$', left) and regex.search(r'^\pM', right):
            return 1.0
        # splitting between digits
        elif regex.search(r'\d$', left) and regex.search(r'^\d', right):
            return 1.0
        else:
            return 0.0

    def diff(self, s2: ColoredSpan,
             # left/right context
             lc1: ColoredSpan | None, rc1: ColoredSpan | None, lc2: ColoredSpan | None, rc2: ColoredSpan | None) \
            -> Tuple[ColoredSpan, ColoredSpan]:
        best_score1, best_start1, best_end1 = 0, 0, 0
        for start1 in range(0, self.len):
            for end1 in range(start1 + 1, self.len + 1):
                sub = self.s[start1:end1]
                if not regex.search(r'\S', sub):
                    continue
                if sub in s2.s:
                    start2 = s2.s.find(sub)
                    end2 = start2 + len(sub)
                    score = (end1 - start1
                             - self.score_penalty(start1, lc1, rc1)
                             - self.score_penalty(end1, lc1, rc1)
                             - s2.score_penalty(start2, lc2, rc2)
                             - s2.score_penalty(end2, lc2, rc2))
                    if score > best_score1:
                        best_score1, best_start1, best_end1 = score, start1, end1
                else:
                    break
        if best_score1 > 0:
            sub = self.s[best_start1:best_end1]
            best_start2 = s2.s.find(sub)
            best_end2 = best_start2 + len(sub)
            # print(f"{best_score1} [{best_start1}-{best_end1}/{best_start2}-{best_end2}] {sub}\n")
            left1, core1, right1 = self.span_split(best_start1, best_end1, "green")
            left2, core2, right2 = s2.span_split(best_start2, best_end2, "green")
            if left1 and left2:
                left1, left2 = left1.diff(left2, lc1, core1, lc2, core2)
            else:
                core1.color_red_non_none(left1, left2)
            if right1 and right2:
                right1, right2 = right1.diff(right2, core1, rc1, core2, rc2)
            else:
                core1.color_red_non_none(right1, right2)
            new_s1 = core1.span_concat(left1, right1)
            new_s2 = core2.span_concat(left2, right2)
            return new_s1, new_s2
        else:
            self.color_red()
            s2.color_red()
            return self, s2


class ColorDiff:
    def __init__(self, s1: str, s2: str, style: dict | None = None):
        self.style = style or {}
        self.green_tag = "<span style='color:#009900;'>"
        self.red_tag = "<span style='color:#FF0000;'>"
        self.blue_tag = "<span style='color:#0000FF;'>"
        self.orange_tag = "<span style='color:#F9A602;'>"
        self.close_tag = "</span>"
        self.sep_tag = (self.orange_tag + "‸" + self.close_tag)
        # self.sep_tag = (self.orange_tag + "*" + self.close_tag)
        self.s1 = s1
        self.s2 = s2
        orig_span1 = ColoredSpan(s1, 0, len(s1), self)
        orig_span2 = ColoredSpan(s2, 0, len(s2), self)
        self.span1, self.span2 = orig_span1.diff(orig_span2, None, None, None, None)


def italicize(s: str, condition: bool = True):
    if condition:
        return "<i>" + s + "</i>"
    else:
        return s


def color_bitext_lines(s1: str, s2: str) -> Tuple[str, str]:
    col_diff = ColorDiff(str(s1), str(s2))
    span1, span2 = col_diff.span1, col_diff.span2
    colored_s1 = italicize(span1.colored_s, s1 is None)
    colored_s2 = italicize(span2.colored_s, s2 is None)
    return colored_s1, colored_s2


def shared_prefix(s1: str, s2: str) -> str:
    """
    Find the shared prefix of two strings.
    """
    i = 0
    while i < len(s1) and i < len(s2) and s1[i] == s2[i]:
        i += 1
    return s1[:i]


def shared_suffix(s1: str, s2: str) -> str:
    """
    Find the shared prefix of two strings.
    """
    i = 0
    while i < len(s1) and i < len(s2) and s1[-1-i] == s2[-1-i]:
        i += 1
    return s1[-i:] if i > 0 else ""


def blue_spans(s: str, ref_corpus: str) -> Tuple[str, str]:
    min_blue_span = 10
    new_s_left = ""
    prev_s = None
    while s != prev_s:
        prev_s = s
        for start in range(len(s)-min_blue_span):
            if not s[start].isspace():
                end = start
                while (end+1 <= len(s)) and s[start:end+1] in ref_corpus:
                    end += 1
                while (end > start) and s[end-1].isspace():
                    end -= 1
                if (end - start >= min_blue_span) and (ref_corpus.count(s[start:end]) == 1):
                    new_s_left += RED_TAG + guard_html(s[:start], diff=True) + CLOSE_TAG
                    new_s_left += BLUE_TAG + '⌞' + guard_html(s[start:end], diff=True) + '⌟' + CLOSE_TAG
                    s = s[end:]
                    break
    return s, new_s_left


def color_bitext_line(s1: str, s2: str, corpus1: str | None = None, corpus2: str | None = None) -> Tuple[str, str]:
    """
    Color two strings using HTML: green for matching parts, red for non-matching parts.
    Used to compare test and gold.
    """
    # Obsolete. This function can be further refined.
    new_s1_left, new_s1_right, new_s2_left, new_s2_right = "", "", "", ""
    s1_mem, s2_mem = None, None
    while (s1 or s2) and not (s1 == s1_mem and s2 == s2_mem):
        s1_mem, s2_mem = s1, s2
        # strings share same prefix
        if prefix := shared_prefix(s1, s2):
            new_s1_left += GREEN_TAG + guard_html(prefix, space=True) + CLOSE_TAG
            new_s2_left += GREEN_TAG + guard_html(prefix, space=True) + CLOSE_TAG
            s1 = s1[len(prefix):]
            s2 = s2[len(prefix):]
        # strings share same suffix
        if suffix := shared_suffix(s1, s2):
            new_s1_right = GREEN_TAG + guard_html(suffix, space=True) + CLOSE_TAG + new_s1_right
            new_s2_right = GREEN_TAG + guard_html(suffix, space=True) + CLOSE_TAG + new_s2_right
            s1 = s1[:-len(suffix)]
            s2 = s2[:-len(suffix)]
        # strings start/end with minor differences, but then continue with the same longer string
        min_post_skip = 7
        min_post_skip_until_end = 3
        for skip1, skip2 in ((1, 1), (1, 0), (0, 1), (2, 2), (2, 1), (1, 2), (2, 0), (0, 2)):
            if (len(s1) >= skip1 + min_post_skip_until_end) and (len(s2) >= skip2 + min_post_skip_until_end):
                if s1[skip1:skip1+min_post_skip] == s2[skip2:skip2+min_post_skip]:
                    new_s1_left += RED_TAG + guard_html(s1[:skip1], diff=True) + CLOSE_TAG
                    new_s2_left += RED_TAG + guard_html(s2[:skip2], diff=True) + CLOSE_TAG
                    s1 = s1[skip1:]
                    s2 = s2[skip2:]
            if (len(s1) >= skip1 + min_post_skip_until_end) and (len(s2) >= skip2 + min_post_skip_until_end):
                rest1, suffix1 = (s1, '') if skip1 == 0 else (s1[:-skip1], s1[-skip1:])
                rest2, suffix2 = (s2, '') if skip2 == 0 else (s2[:-skip2], s2[-skip2:])
                if rest1[-min_post_skip:] == rest2[-min_post_skip:]:
                    new_s1_right = RED_TAG + guard_html(suffix1, diff=True) + CLOSE_TAG + new_s1_right
                    new_s2_right = RED_TAG + guard_html(suffix2, diff=True) + CLOSE_TAG + new_s2_right
                    s1 = rest1
                    s2 = rest2
    # find substantial sub-strings in s that also uniquely occur in ref-corpus
    s1, additional_s1_left = blue_spans(s1, corpus2)
    new_s1_left += additional_s1_left
    s2, additional_s2_left = blue_spans(s2, corpus1)
    new_s2_left += additional_s2_left
    # more to be added
    if s1 or s2:
        new_s1_left += RED_TAG + guard_html(s1, diff=True) + CLOSE_TAG
        new_s2_left += RED_TAG + guard_html(s2, diff=True) + CLOSE_TAG
    return new_s1_left + new_s1_right, new_s2_left + new_s2_right


def str_w_eol(test) -> str:
    """
    Convert to string, and append end-of-line character if not already present
    """
    if isinstance(test, tuple) and test and isinstance(test[0], str):
        test = test[0]
    result = str(test)
    if not result.endswith('\n'):
        result += '\n'
    return result


GREEN_TAG = '<span style="color:green;">'
RED_TAG = '<span style="color:red;">'
BLUE_TAG = '<span style="color:blue;">'
PINK_TAG = '<span style="color:#FA86C4;">'
ORANGE_TAG = "<span style='color:#F9A602;'>"
GREY_TAG = "<span style='color:#AAAAAA;'>"
CLOSE_TAG = '</span>'


def pretty_time(datetime_object: datetime.datetime) -> str:
    return f"{datetime_object:%A, %B %d, %Y at %H:%M}"


def main() -> None:
    date = f"{datetime.datetime.now():%B %-d, %Y at %-H:%M}"
    parser = argparse.ArgumentParser()
    parser.add_argument('file1', type=str)
    parser.add_argument('file2', type=str)
    parser.add_argument('-l', '--legends', nargs='+', type=str)
    parser.add_argument('-r', '--refs', nargs='+', type=str)
    # parser.add_argument('-O', '--text_out_filename', type=str, default=None)
    parser.add_argument('-o', '--html_out_filename', type=str, default=None)
    parser.add_argument('-s', '--snt_id_filename', type=str, default=None)
    parser.add_argument('-a', '--all', action='store_true')
    parser.add_argument('-t', '--title', type=str)
    parser.add_argument('-n', '--max_n_entries', type=int, default=None)
    # parser.add_argument('-d', '--decode_unicode', action='count', default=0,
    #                     help='decodes Unicode escape notation, e.g. \\u03B4 to δ')
    # parser.add_argument('--log_filename', type=str, default=None)
    args = parser.parse_args()

    f1 = open(args.file1)
    f2 = open(args.file2)
    f_refs = []
    for ref in args.refs:
        f_refs.append(open(ref))
    f_id = open(args.snt_id_filename) if args.snt_id_filename else None
    f_html = open(args.html_out_filename, 'w') if args.html_out_filename else None
    if f_html:
        f_html.write(html_head(args.title or "color_diff", date, "color_diff"))
    legends = args.legends
    line_number = 0

    for line1r in f1:
        line1 = line1r.rstrip()
        if args.max_n_entries and (line_number >= args.max_n_entries):
            break
        line_number += 1
        if line_number % 100 == 0:
            if line_number % 1000 == 0:
                sys.stderr.write(f"{line_number}")
            else:
                sys.stderr.write(".")
            sys.stderr.flush()
        line2 = f2.readline().rstrip()
        same_clause = "&nbsp;&nbsp;(same)" if line1 == line2 else ""
        snt_id = f_id.readline() if f_id else f"l.{line_number}"
        if f_html:
            f_html.write("<table border='0' cellpadding='3' cellspacing='0'>")
            f_html.write(f"  <tr><td colspan='2'><b>{snt_id}{same_clause}</b></td></tr>\n")
            colored_line1, colored_line2 = color_bitext_lines(line1, line2)
            legend1, legend2 = legends
            # f_html.write(f"  <tr><td style='color:grey;'>ORIG1</td><td>{guard_html(line1)}</td></tr>\n")
            # f_html.write(f"  <tr><td style='color:grey;'>ORIG2</td><td>{guard_html(line2)}</td></tr>\n")
            f_html.write(f"  <tr><td style='color:grey;'>{legend1}</td><td>{colored_line1}</td></tr>\n")
            f_html.write(f"  <tr><td style='color:grey;'>{legend2}</td><td>{colored_line2}</td></tr>\n")
            f_html.write("</table>\n")
            f_html.write("<hr>\n")
    if f_html:
        print_html_foot(f_html)
        f_html.close()
    if f_id:
        f_id.close()
    for f_ref in f_refs:
        f_ref.close()
    f1.close()
    f2.close()
    sys.stderr.write("\n")


if __name__ == "__main__":
    main()

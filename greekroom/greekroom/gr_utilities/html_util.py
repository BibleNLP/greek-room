#!/usr/bin/env python

import regex


def guard_html(s):
    """escape characters inside HTML"""
    s = regex.sub('&', '&amp;', s)
    s = regex.sub('<', '&lt;', s)
    s = regex.sub('>', '&gt;', s)
    s = regex.sub('"', '&quot;', s)
    s = regex.sub("'", '&apos;', s)
    return s


def html_title_guard(s: str) -> str:
    """escape characters for titles inside HTML"""
    s = s.replace(' ', '&nbsp;')
    s = s.replace('-', '\u2011')
    s = s.replace('&#xA;', ' ')
    return s


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
"""


def print_html_foot(f_html) -> None:
    f_html.write('''
  </body>
</html>
''')

"""
Search for matches and generate results output
"""

import re
import flask
import random
import logging
from pathlib import Path
from collections import defaultdict

# from typing import Optional, TextIO, Union

_LOGGER = logging.getLogger(__name__)


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

    text_filename = f'{flask.current_app.config["ENG_HIN_REF_FILE"]}'

    sample_fraction = sample_percentage * 0.01

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

    try:
        f_in = open(text_filename)
    except Exception as error:
        return {"error_message": f"Error: Cannot open {text_filename} [{str(error)}]"}
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
        sample_results_message = ""
        if n_matches > max_number_output_snt:
            if auto_sample_percentage:
                sample_results_message = (
                    f", random sample of {str(max_number_output_snt)} shown"
                )
            elif sample_percentage < 100:
                sample_results_message = f", random {str(sample_percentage)}% sample up to {str(max_number_output_snt)} shown"
            else:
                sample_results_message = f", first {str(max_number_output_snt)} shown"
        elif sample_percentage < 100:
            sample_results_message = f", random {str(sample_percentage)}% sample shown"

        f_in.close()
        n_matches_shown = 0
        n_matches_remaining = n_matches
        n_matches_remaining_to_be_shown = max_number_output_snt

        chapter_html_dir = Path(flask.current_app.config["ENG_HIN_CHAPTER_HTML_DIR"])
        for viz_filename in viz_file_list:
            full_viz_filename = chapter_html_dir / viz_filename
            # full_viz_filename = html_filename_dir + "/" + viz_filename
            try:
                f_in = open(str(full_viz_filename))
            except Exception as error:
                generated_html.append(
                    """<span style="color:red;">Error: Cannot open """
                    + full_viz_filename
                    + """ ["""
                    + str(error)
                    + """]<span><br>\n"""
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
        generated_html.append(f"{str(n_matches_shown)} shown")
    return {
        "results": "\n".join(generated_html),
        "n_matches": n_matches,
        "sample_results_message": sample_results_message,
    }


if __name__ == "__main__":
    main()

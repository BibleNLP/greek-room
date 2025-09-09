# greekroom

_greekroom_ is a suite of tools to support Biblical natural language processing (in progress)

<!--
[![image alt >](http://img.shields.io/pypi/v/greekroom.svg)](https://pypi.python.org/pypi/greekroom/)

### Installation (stubs only, in early development, not ready for regular users yet)

```bash
pip install greekroom
```
or
```bash
git clone https://github.com/BibleNLP/greek-room.git
```
-->

When using the GitHub version, we recommend that your PYTHONPATH includes the outer *greekroom* directory, i.e. the one that includes this README.md;
additionally you might want to include in PATH the Greek Room's executable directories such as greekroom/greekroom/gr_utilities:greekroom/greekroom/owl .


## gr_utilities
_gr_utilities_ is a set of Greek Room utilities.

<details>
<summary> <b>wb_file_props.py</b>
A CLI Python script to analyze file properties such as script direction, quotations.</summary>

```
usage: wb_file_props.py [-h]
           [-i INPUT_FILENAME]
           [-s INPUT_STRING]
           [-j JSON_OUT_FILENAME]
           [-o HTML_OUT_FILENAME]
           [--lang_code LANG_CODE]
           [--lang_name LANG_NAME]

options:
  -h, --help            show this help message and exit
  -i INPUT_FILENAME, --input_filename INPUT_FILENAME
  -s INPUT_STRING, --input_string INPUT_STRING
  -j JSON_OUT_FILENAME, --json_out_filename JSON_OUT_FILENAME
  -o HTML_OUT_FILENAME, --html_out_filename HTML_OUT_FILENAME
  --lang_code LANG_CODE
  --lang_name LANG_NAME
```
Notes:
* Typically, either an INPUT_FILENAME or an INPUT_STRING is provided (but not both).
* Typically, a JSON_OUT_FILENAME or a HTML_OUT_FILENAME is provided (or both).

Sample calls
```
wb_file_props.py -h
wb_file_props.py -s """She asked: “Whatʼs a ‘PyPi’?”
He replied: “I don't know.”""" -j test.json
cat test.json

```
</details>

<details>
<summary> <b>gr_utilities.wb_file_props.script_punct</b>
A Python function to analyze file properties such as script direction, quotations.</summary>

```python
import json
from greekroom.gr_utilities import wb_file_props

## Apply script to string
text = """She asked: “Whatʼs a ‘PyPi’?”
He replied: “I don't know.”"""
result_dict = wb_file_props.script_punct(None, text, "eng", "English")
print(result_dict)

## Apply script to file content
# Write text to file
filename = "test.txt"
with open(filename, "w") as f_out:
    f_out.write(text)

# Apply script
result_dict2 = wb_file_props.script_punct(filename)
# Print result as JSON string
print(json.dumps(result_dict2))
# Write result to HTML file
html_output = "test.html"
with open(html_output, "w") as f_html:
    wb_file_props.print_to_html(result_dict2, f_html)

```
</details>

## owl
_owl_ is a battery of smaller Bible Translation checks.

<details>
<summary> <b>repeated_words.py</b>
A CLI Python script to check a file for repeated words, e.g. "the the".</summary>

```
usage: repeated_words.py [-h]
                         [-j JSON]
                         [-i IN_FILENAME]
                         [-r REF_FILENAME]
                         [-o OUT_FILENAME]
                         [--html HTML]
                         [--project_name PROJECT_NAME]
                         [--lang_code LANGUAGE-CODE]
                         [--lang_name LANG_NAME]
                         [--message_id MESSAGE_ID]
                         [-d DATA_FILENAMES]
                         [--verbose]

options:
  -h, --help            show this help message and exit
  -j JSON, --json JSON  input (alternative 1)
  -i IN_FILENAME, --in_filename IN_FILENAME
                        text file (alternative 2)
  -r REF_FILENAME, --ref_filename REF_FILENAME
                        ref file (alt. 2)
  -o OUT_FILENAME, --out_filename OUT_FILENAME
                        output JSON filename
  --html HTML           output HTML filename
  --project_name PROJECT_NAME
                        full name of Bible translation project
  --lang_code LANGUAGE-CODE
                        ISO 639-3, e.g. 'fas' for Persian
  --lang_name LANG_NAME
  --message_id MESSAGE_ID
  -d DATA_FILENAMES, --data_filenames DATA_FILENAMES
  --verbose
```
Notes:
* Typically, either a JSON INPUT_FILENAME or a JSON INPUT_STRING is provided (but not both).
* Typically, a JSON_OUT_FILENAME or a HTML_OUT_FILENAME is provided (or both).


Sample calls
```
repeated_words.py -h
repeated_words.py -j '{"jsonrpc": "2.0",
 "id": "eng-sample-01",
 "method": "BibleTranslationCheck",
 "params": [{"lang-code": "eng", "lang-name": "English",
             "project-id": "eng-sample",
             "project-name": "English Bible",
             "selectors": [{"tool": "GreekRoom", "checks": ["RepeatedWords"]}],
             "check-corpus": [{"snt-id": "GEN 1:1", "text": "In in the beginning ..."},
                              {"snt-id": "JHN 12:24", "text": "Truly truly, I say to you ..."}]}]}' -o test.json
cat test.json
```
</details>

<details>
<summary> <b>owl.repeated_words.check_mcp</b>
A Python function to check a file for repeated words, e.g. "the the".</summary>

```python
import json
from greekroom.owl import repeated_words

task_s = '''{"jsonrpc": "2.0",
 "id": "eng-sample-01",
 "method": "BibleTranslationCheck",
 "params": [{"lang-code": "eng", "lang-name": "English",
             "project-id": "eng-sample",
             "project-name": "English Bible",
             "selectors": [{"tool": "GreekRoom", "checks": ["RepeatedWords"]}],
             "check-corpus": [{"snt-id": "GEN 1:1", "text": "In in the beginning ..."},
                              {"snt-id": "JHN 12:24", "text": "Truly truly, I say to you ..."}]}]}'''

# load_data_filename() loads <i>legitimate_duplicates.jsonl</i> (see below); call this function only once, even for multiple checks.
data_filename_dict = repeated_words.load_data_filename()
corpus = repeated_words.new_corpus("eng-sample-01")
mcp_d, misc_data_dict, check_corpus_list = repeated_words.check_mcp(task_s, data_filename_dict, corpus)
print(json.dumps(mcp_d))
print(misc_data_dict)
print(check_corpus_list)

# print to HTML file
feedback = repeated_words.get_feedback(mcp_d, 'GreekRoom', 'RepeatedWords')
corpus = repeated_words.update_corpus_if_empty(corpus, check_corpus_list)
repeated_words.write_to_html(feedback, misc_data_dict, corpus, "test.html", "eng", "English", "English Bible")
# result will be in test.html

```
</details>

<details>
<summary> <b>legitimate_duplicates.jsonl</b>
Data files describing legitimate repeated words.</summary>

Samples:

```
{"lang-code": "eng", "text": "truly, truly"}
{"lang-code": "eng", "text": "her her", "snt-ids": ["HOS 2:17", "EST 2:9", "JDT 10:4"], "context-examples": ["give her her vineyards", "gave her her things for purification"]}
{"lang-code": "grc", "text": "ἀμὴν ἀμὴν", "rom": "amen amen", "gloss": {"eng": "truly truly [I say to you]"}}

{"lang-code": "hin", "text": "जब जब", "rom": "jab jab", "gloss": {"eng": "whenever"}}
{"lang-code": "hin", "text": "कुछ कुछ", "rom": "kuch kuch", "gloss": {"eng": "something, somewhat, some of, part of"}}
{"lang-code": "eng", "text": "they they", "delete": true}
```
Notes:
* Searches for files <i>owl/data/legitimate_duplicates.jsonl</i> in directories "greekroom", "$XDG_DATA_HOME", "/usr/share", "$HOME/.local/share"
* later entries overwrite prior entries
* <i>"delete": true</i> entries delete prior entries

</details>

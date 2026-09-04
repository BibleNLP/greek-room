# greekroom

_greekroom_ is a suite of tools to support Biblical natural language processing (in progress)

<!--
[![image alt >](http://img.shields.io/pypi/v/greekroom.svg)](https://pypi.python.org/pypi/greekroom/)
-->

### Installation

```bash
pip install greekroom
```
or
```bash
git clone https://github.com/BibleNLP/greek-room.git
```

When using the GitHub version, we recommend that your PYTHONPATH includes the outer *greekroom* directory, i.e. the one that includes this README.md;
additionally you might want to include in PATH the Greek Room's executable directories such as <tt>greekroom/greekroom/gr_utilities:greekroom/greekroom/gr_utilities:greekroom/greekroom/owl</tt> .


## gr_utilities
_gr_utilities_ is a set of Greek Room utilities.

<details>
<summary> <b>gr-wb-file-props</b>
A CLI Python script to analyze file properties such as script direction, quotations.</summary>

```
usage: gr-wb-file-props [-h]
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
gr-wb-file-props -h
gr-wb-file-props -s """She asked: “Whatʼs a ‘PyPi’?”
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
<summary> <b>gr-repeated-words</b>
A CLI Python script to check a file for repeated words, e.g. "the the".</summary>

```
usage: gr-repeated-words [-h]
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
gr-repeated-words -h
gr-repeated-words -j '{"jsonrpc": "2.0",
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

## Wildebeest
The _Wildbeest_ scripts investigate, repair and normalize text for a wide range of issues at the character level.
The <tt>gr-wb-check</tt> script supports external editors such as Fluent.

<details>
<summary><b>Highlights:</b> 
Interface; action menus, auto correct; speed; status</summary>           

* **Interface:** In the CLI scripts, main input and output are JSON strings. The Python function uses Python objects. See <i>examples</i> in the sections below.
* **Action menus:** For most issues that Wildebeest reports, Wildebeest also provides an action menu, with one or more action items, in most cases with one single recommended action item, often with high confidence.
* **Auto correct:** The action items have confidence numbers between 0.0 (no confidence) and 1.0 (top confidence). This allows translation editors to auto-correct text for high-confidence feedback. The optional HTML outputs (for developers of both Wildebeest and the tools using Wildebeest) show proposed auto-corrected text in green, uncorrected text in red.
* **Speed:** A Wildebeest check takes a few seconds for the whole Bible and is nearly instant for smaller passages such as chapters or verses.
* **Status:** Wildebeest's analysis script (output: HTML pages) and normalization script have been around for years. But this <tt>gr-wb-check</tt> interface to support translation editors is new and in its beta phase. Much of the Wildebeest code is legacy code for the analysis and normalization scripts.
</details>


<details>
<summary> <b>CLI Python script</b>
<tt>gr-wb-check</tt> (Greek Room Wildebeest Checker)</summary>

```
usage: gr-wb-check [-h]
                   [-j JSON]
                   [-a AUTO_CORRECT_THRESHOLD]
                   [-o JSON_OUT_FILENAME]
                   [-H HTML_OUT_FILENAME_BY_SNT_ID]
                   [-C HTML_OUT_FILENAME_BY_CHECK]
                   [--version]

options:
  -h, --help            show this help message and exit
  -j JSON, --json JSON  input json
  -a AUTO_CORRECT_THRESHOLD, --auto_correct_threshold AUTO_CORRECT_THRESHOLD
                        value between 0.0 and 1.0; higher = more reliable
  -o JSON_OUT_FILENAME, --json_out_filename JSON_OUT_FILENAME
                        output JSON filename
  -H HTML_OUT_FILENAME_BY_SNT_ID, --html_out_filename_by_snt_id HTML_OUT_FILENAME_BY_SNT_ID
                        to help development
  -C HTML_OUT_FILENAME_BY_CHECK, --html_out_filename_by_check HTML_OUT_FILENAME_BY_CHECK
                        to help development
  --version             show program's version number and exit
```


Example 1 (simple, with 10 issues in 3 of the 4 verses)
```
gr-wb-check -j '{"jsonrpc": "2.0",
  "id": "eng-test-02",
  "method": "BibleTranslationCheck",
  "params": [{"checks": ["GreekRoom:Wildebeest"],
              "corpus": {"langCode": "eng",
                         "body": [{"sntId": "GEN 1:1", "text": "In in the beginning,God created the heavens and the earth."},
                                  {"sntId": "GEN 1:3", "text": "And God said , `“Let there be light ,аnd there was light."},
                                  {"sntId": "NUM 1:21", "text": "those listed of the tribe of Reuben were 46,500."},
                                  {"sntId": "NUM 1:23", "text": "those listed of the tribe of Simeon were 59.300,. डे़|"}
                                 ]}}]}' -o test.json
cat test.json
```

Example 2 (same corpus body, but more fields)
```
gr-wb-check -j '{"jsonrpc": "2.0",
  "id": "eng-test-02",
  "method": "BibleTranslationCheck",
  "params": [{"checks": ["GreekRoom:Wildebeest"],
              "corpus": {"langCode": "eng", "langName": "English", "corpusId": "eng-sample", "corpusName": "English Bible",
                         "versificationSchema": "org",
                         "body": [{"sntId": "GEN 1:1", "text": "In in the beginning,God created the heavens and the earth."},
                                  {"sntId": "GEN 1:3", "text": "And God said , `“Let there be light ,аnd there was light."},
                                  {"sntId": "NUM 1:21", "text": "those listed of the tribe of Reuben were 46,500."},
                                  {"sntId": "NUM 1:23", "text": "those listed of the tribe of Simeon were 59.300,. डे़|"}]},
              "referenceCorpora": [
                        {"langCode": "deu", "langName": "German",
                         "body": [{"sntId": "GEN 1:1", "text": "Am Anfang schuf Gott Himmel und Erde."}]}]
             }]}' -o test.json -H out2.html -C out2c.html -a 0.3
cat test.json
```


##### Notes

* "id" is used to coordinate request and response.
* "checks" is a list of checks that allow for varying degrees of specificity, e.g. "GreekRoom", "GreekRoom:Wildebeest", "GreekRoom:Wildebeest:punctuation:space:comma"
* Option -a/--auto_correct_threshold sets the auto-repair threshold in the HTML outputs. 0.3 is very aggressive; 0.9 is conservative. With the default value, *None*, **no** auto corrections will be made.
* Option -H is for HTML output sorted by verse.
* Option -C is for HTML output sorted by Wildebeest check type.
* Reference corpora are important for other checks such as spell-checking.
* langName/corpusId/corpusName are used in HTML output for the human readers' benefit.
* Python file name for <tt>gr-wb-check</tt>: <tt> wb_check.py</tt> (inside <tt>greekroom.wildebeest</tt>)

</details>

<details>
<summary><b>Sample output</b> 
as of Sept. 4, 2026, reporting 10 issues in 3 out of 4 verses</summary>

```
{"jsonrpc": "2.0", "id": "eng-test-02", "resultTimestamp": "2026-09-04T18:22:12", "corpusLangCode": "eng", "result": [
  {"sntId": "GEN 1:1", "span": [[19, 20]], "orig": ",",
     "check": "GreekRoom:Wildebeest:punctuation:space:comma:detach-from-right", "severity": 0.6,
     "actionMenu": [{"substitute": ", ", "confidence": 0.9}]},
  {"sntId": "GEN 1:3", "span": [[12, 14]], "orig": " ,",
     "check": "GreekRoom:Wildebeest:punctuation:space:comma:attach-to-left", "severity": 0.6,
     "actionMenu": [{"substitute": ",", "confidence": 0.9}]},
  {"sntId": "GEN 1:3", "span": [[15, 16]], "orig": "`",
     "check": "GreekRoom:Wildebeest:punctuation:unexpected", "severity": 0.7},
  {"sntId": "GEN 1:3", "span": [[16, 17]], "orig": "\u201c",
     "check": "GreekRoom:Wildebeest:punctuation:unpaired-delimiter:open:left double quotation mark", "severity": 0.5},
  {"sntId": "GEN 1:3", "span": [[35, 37]], "orig": " ,",
     "check": "GreekRoom:Wildebeest:punctuation:space:comma:reattach-to-left", "severity": 0.6,
     "actionMenu": [{"substitute": ", ", "confidence": 0.9}]},
  {"sntId": "GEN 1:3", "span": [[37, 40]], "orig": "\u0430nd",
     "check": "GreekRoom:Wildebeest:script:token-with-multiple-scripts", "severity": 0.9,
       "scripts": ["CYRILLIC", "LATIN"], "minorityScriptLetters": ["\u0430"], "minorityScriptSpan": [[37, 38]],
     "actionMenu": [{"substitute": "and", "confidence": 0.9}]},
  {"sntId": "NUM 1:23", "span": [[47, 49]], "orig": ",.",
     "check": "GreekRoom:Wildebeest:punctuation:cluster", "severity": 0.7,
     "actionMenu": [{"substitute": ".", "confidence": 0.4},
                    {"substitute": ",", "confidence": 0.4}]},
  {"sntId": "NUM 1:23", "span": [[50, 53]], "orig": "\u0921\u0947\u093c",
     "check": "GreekRoom:Wildebeest:encoding:nukta-position", "severity": 0.9,
     "actionMenu": [{"substitute": "\u0921\u093c\u0947", "confidence": 0.99}]},
  {"sntId": "NUM 1:23", "span": [[50, 53]], "orig": "\u0921\u0947\u093c",
     "check": "GreekRoom:Wildebeest:script:token-in-minority-script", "minorityScript": "DEVANAGARI", "severity": 0.7},
  {"sntId": "NUM 1:23", "span": [[53, 54]], "orig": "|",
     "check": "GreekRoom:Wildebeest:punctuation:repair:vertical line:danda", "severity": 0.7,
     "actionMenu": [{"substitute": "\u0964", "confidence": 0.6}]}],
 "version": {"GreekRoom": "0.1.3", "GreekRoomFormat": "0.0.4", "GreekRoomWildebeest": "0.11.2"},
 "skippedChecks": []}
```

</details>

<details>
<summary> <b>Python function</b>
<tt>greekroom.wildebeest.wb_check.check()</tt></summary>

Example 1 (simple, stateless)
```python
import greekroom.wildebeest.wb_check as wb_c
check_request_2 = {"jsonrpc": "2.0",
  "id": "eng-test-02",
  "method": "BibleTranslationCheck",
  "params": [{"checks": ["GreekRoom:Wildebeest"],
              "corpus": {"langCode": "eng",
                         "body": [{"sntId": "GEN 1:1", "text": "In in the beginning,God created the heavens and the earth."},
                                  {"sntId": "GEN 1:3", "text": "And God said , `“Let there be light ,аnd there was light."},
                                  {"sntId": "NUM 1:21", "text": "those listed of the tribe of Reuben were 46,500."},
                                  {"sntId": "NUM 1:23", "text": "those listed of the tribe of Simeon were 59.300,. डे़|"}
                                 ]}}]}
check_response_2 = wb_c.check(check_request_2)
check_response_2
```

Example 2 (capturing a text_corpus along with statistics across calls)
* In this example there is a (1) corpus initialization call (with no checks) and (2) a regular call (with checks).
* Initialization calls often cover much or all of the Bible; subsequent check calls often cover only a few verses.
* The text corpus context helps to identify truly rare (and therefore suspicious) characters. See more in <i>text corpus</i> section below.

```python
init_request_1 = {"jsonrpc": "2.0",
  "id": "eng-init-03",
  "method": "BibleTranslationCheck",
  "params": [{"checks": [],
              "corpus": {"langCode": "eng",  "corpusId": "eng-bible-v01",
                         "body": [{"sntId": "GEN 1:1", "text": "In in the beginning,God created the heavens and the earth."},
                                  {"sntId": "GEN 1:2", "text": "Now the earth was formless and empty, darkness was over the surface of the deep, and the Spirit of God was hovering over the waters."},
                                  {"sntId": "GEN 1:3", "text": "And God said , `“Let there be light ,аnd there was light."}
                                 ]}}]}

text_corpus = wb_c.init_text_corpus()
check_response_1 = wb_c.check(init_request_1, text_corpus)
check_response_2 = wb_c.check(check_request_2, text_corpus)
```

</details>

<details>
<summary><b>Text corpus</b> 
used for non-local checks</summary>
           
* The <i>text corpus</i>, optional for Wildebeest, stores a larger text corpus along with statistics of that corpus.
* In Wildebeest, it can be used to identify characters that are rare (and therefore suspicious) in a larger corpus.
* This can be done by calling wb_c.check on the complete text corpus so far but without an actual check. This might take a few seconds but only has to be done once. This corpus initialization is followed by a number of actual check calls. The text corpus is updated automatically. The original initialization allows for checks that are not local to the verses being checked (such as the rare-character check).
* Alternatively, a text editor can make stateless calls on a verse or a chapter at a time. These are too short to meet the minimum number of characters (50,000) required for the rare-character test kicks in. Then, somewhat rarely, the text editor might call Wildebeest on a large text, but limiting the checks to \["GreekRoom:Wildebeest:character:rare"\]. Most raw Bible translation projects contain a modest number of rare characters (1-10). 

</details>

# Wildebeest

The Wildebeest scripts investigate, repair and normalize text for a wide range of issues at the character level.<br>
This document focuses on the interface that supports external editors such as Fluent.

<a name="cli"></a>
### Command Line Interface (CLI)
#### Examples

Example 1 (simple, with 10 issues in 3 of the 4 verses)
```bash
wb_check.py -j '{"jsonrpc": "2.0",
  "id": "eng-test-02",
  "method": "BibleTranslationCheck",
  "params": [{"checks": ["GreekRoom:Wildebeest"],
              "corpus": {"langCode": "eng",
                         "body": [{"sntId": "GEN 1:1", "text": "In in the beginning,God created the heavens and the earth."},
                                  {"sntId": "GEN 1:3", "text": "And God said , `“Let there be light ,аnd there was light."},
                                  {"sntId": "NUM 1:21", "text": "those listed of the tribe of Reuben were 46,500."},
                                  {"sntId": "NUM 1:23", "text": "those listed of the tribe of Simeon were 59.300,. डे़|"}
                                 ]}}]}' -o out2.json
```

Example 2 (same corpus body, but more fields)
```bash
wb_check.py -j '{"jsonrpc": "2.0",
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
             }]}' -o out2.json -H out2.html -C out2c.html -a 0.3

```
##### Notes

* "id" is used to coordinate request and response.
* "checks" is a list of checks that allow for varying degrees of specificity, e.g. "GreekRoom", "GreekRoom:Wildebeest", "GreekRoom:Wildebeest:punctuation:space:comma"
* Option -a/--auto_correct_threshold sets the auto-repair threshold in the HTML outputs. 0.3 is very aggressive; 0.9 is conservative. With the default value, *None*, **no** auto corrections will be made.
* Option -H is for HTML output sorted by verse.
* Option -C is for HTML output sorted by Wildebeest check type.
* Legacy option -O is for plain text output.
* Legacy option --html_output_filename is for traditional HTML output.
* Reference corpora are important for other checks such as spell-checking.
* langName/corpusId/corpusName are used in HTML output for the human readers' benefit.

##### Sample outputs

For examples 1 and 2:
```bash
{"jsonrpc": "2.0", "id": "eng-test-02", "resultTimestamp": "2026-08-07T18:45:10", "corpusLangCode": "eng", "result": [
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
 "version": {"GreekRoom": "0.0.21", "GreekRoomFormat": "0.0.4", "GreekRoomWildebeest": "0.11.1"},
 "skippedChecks": []}
```

### Using *Wildebeest* inside Python

```python 
import greekroom.wildebeest.wb_check as wb
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
check_response_2 = wb.check(check_request_2)
```

##### Return versions for Wildebeest, Greek Room in general etc.
```python
version_dict = wb.version()
```

* Initialize corpus with zero or more of the following, with no checks.
* A corpus initialization could be for the whole Bible, of in chunks such as a sequence of books (with same corpusId and langCode).
* For Wildebeest, the corpus statistics will support identifying characters that are rare/unusual/suspicious.
* For spell checking, the corpus statistics will be even more important.
* This initialization is typically done before Greek Room corpus checks.
* The initialization might take a little longer than a check (since it includes the available corpus, not just a chapter or so),
but it needs to be called only once per session for the whole corpus.
* Corpus statistics are automatically updated by Greek Room checks, but will benefit from any corpus updates (call with no checks) after editing changes.
* If calls have the same SntId, only the last one be used for the corpus statistics. 

#### Example with state (in the form of text_corpus): corpus initialization (with no checks), and actual check
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

text_corpus = wb.init_text_corpus()
check_response_1 = wb.check(init_request_1, text_corpus)
check_response_2 = wb.check(check_request_2, text_corpus)
```
After the two checks (one initialization only, one real check), the text_corpus will cover 5 sentences (from both check calls).

###  Corpus props

Corpus props are built based on an analysis of a large corpus, e.g. all available parts of a Bible.
Props useful for Wildebeest are of modest size; props for alignments/spell-checking are large.

```bash
cprops = {"langCode": "ukr",
          "nChars": 3498859,
          "letterScripts": {"CYRILLIC": 2755634, "LATIN": 2},
          "scriptDirection": {"direction": "left-to-right"},
          "punctStyle": {"quotationPairs": [["«", "»"], ["„", "“"]]},
          "numberStyle": {"style": {"decimalGrouping": "Western", "decimalSeparator": ",", "digitGroupSeparator": "\u00A0"}}}
}
```

Notes
* *script-direction* and *number-style* have sub-keys *direction* and *style* to allow for addition detailed information such as *counts*.
* *Western* decimal grouping is by groups of 3; Chinese by groups of 4; Indian by group of 3 and then groups of 2.


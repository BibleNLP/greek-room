## Greek Room's USFM checks

### usfm_check.py

This is the main script for checking uploaded SFM/USFM files and extracting a versified corpus.
(SFM/USFM is a formatting standard widely used for Bibles.)

The USFM Checker **identifies**, **visualizes** and **explains** a wide range of issues and offers **repair** for some. It provides tag **statistics**, including surface forms, parent tags, child tags. 

<details>
<summary>The USFM Checker searches for a wide range of issues, including ...</summary>
tag erros, missing open tags, spurious close tags, bad parent/child tag combinations, missing or spurious spaces/control characters between tags arguments, unexpected arguments, unexpected repetition of certain tags on the same line, empty verses; missing, duplicate, out-of-order chapter and verse numbers; footnote quotations that do not occur in corresponding verse texts; using both numbered and unnumbered versions; case errors; merge conflict markers; missing cross-reference tags; and more.
</details>

#### Typical usage

```
usfm_check.py [-d INPUT-DIRECTORY]
              [-x HTML-OUTPUT-FILENAME]
              [-o TXT-OUTPUT-FILENAME]
              [-s SUMMARY-OUTPUT-FILENAME]
              [-e JSONL-TEXT-EXTRACT-OUTPUT-FILENAME]
```

<details>
<summary>Argument notes</summary>

* The INPUT-DIRECTORY is a directory containing the *SFM/*USFM files to be checked.
* The HTML-OUTPUT-FILENAME is a file with the analysis in browsable HTML format.
* The TXT-OUTPUT-FILENAME is a file with the analysis in plain text.
* The SUMMARY-OUTPUT-FILENAME is a file with a summary, in JSON format, used by the Greek Room for its *scorecard*.
* The JSONL-TEXT-EXTRACT-OUTPUT-FILENAME is a JSONL file with the extracted versified corpus.
</details>

**Examples**
```
usfm_check.py -d upload_dir -o usfm_result.txt -x usfm_result.html -s summary.json -e extract.jsonl
usfm_check.py -h
```

<details>
<summary>Sample lines from extract.jsonl</summary>

```
{"bk": "PSA", "c": 23, "type": "o", "tag": "cl", "l": "1192", "txt": "Psalm 23\r\n"}
{"bk": "PSA", "c": 23, "type": "o", "tag": "d", "l": "1193", "txt": "A psalm of David.\r\n"}
{"bk": "PSA", "c": 23, "v": "1", "type": "v", "l": "1195", "txt": "The Lord is my shepherd, I lack nothing.\r\n"}
{"bk": "PSA", "c": 23, "v": "2", "type": "v", "l": "1197-1198", "txt": "He makes me lie down in green pastures,\r\nhe leads me beside quiet waters,\r\n"}
```
Abbreviations: bk = book; c = chapter, v = verse, o = other, l = line(s),
txt = text, d = descriptive title, cl = chapter label
</details>

Note: The usfm_check.py output file *extract.jsonl* serves as input to script [versification/extract_vref_txt_from_usfm_extract_jsonl.py](https://github.com/BibleNLP/greek-room/blob/main/greekroom/greekroom/versification/README.md)

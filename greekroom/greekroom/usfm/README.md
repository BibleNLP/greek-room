## USFM

### usfm_check.py

This is the main script for checking uploaded SFM/USFM files and extracting a versified corpus.

#### Typical Usage

```
usfm_check.py [-d INPUT-DIRECTORY]
              [-o TXT-OUTPUT-FILENAME] [-x HTML-OUTPUT-FILENAME] [-s SUMMARY-OUTPUT-FILENAME] [-e JSONL-TEXT-EXTRACT-OUTPUT-FILENAME]
```

Arguments:
* The INPUT-DIRECTORY is a directory containing the *SFM/*USFM files to be checked.
* The TXT-OUTPUT-FILENAME is a file with the analysis in plain text.
* The HTML-OUTPUT-FILENAME is a file with the analysis in browsable HTML format.
* The SUMMARY-OUTPUT-FILENAME is a file with a summary, in JSON format, used by the Greek Room for its scorecard.
* The JSONL-TEXT-EXTRACT-OUTPUT-FILENAME is a JSONL file with the extracted versified corpus.

Examples:
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

bk = book; c = chapter, v = verse, o = other, l = line(s), txt = text, d = descriptive title, cl = chapter label
</details>

The extract.json file serves as input to script versification/extract_vref_txt_from_usfm_extract_jsonl.py


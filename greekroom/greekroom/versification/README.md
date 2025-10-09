## Greek Room's Versification Tools

This directory hosts a number of versification scripts.
<details>
<summary>Background</summary>

There are multiple schemas to identify Bible verses.
For example, *"The Lord is my shepherd, I shall not want."* is identified as **PSA 23:1** in many Bibles,
but as **PSA 23:2** in the *original* schema (which uses PSA 23:1 for the descriptive title *"A psalm of David."*).

These are the most common schemas:
* Original Hebrew/Greek ('org')
* English, mainly Protestant ('eng')
* Russian Synodal Canonical, mainly Russian Protestant ('rsc')
* Russian Orthodox ('rso')
* Vulgate, mainly Catholic ('vul')
* Septuagint, mainly Orthodox ('lxx')

In order to compare and align Bible verses across different translation, many tools normalize the versification to *original* ('org'),
including, for example, the [eBible Corpus](https://github.com/BibleNLP/ebible). This process is called **reversification**.

These versification tools support such reversification. They also provide back-versification.
</details>

### extract_vref_txt_from_usfm_extract_jsonl.py

This auxiliary script extracts from *extract.jsonl* (1) a plain text corpus file and (2) a matching verse ID file.

#### Typical usage
```
extract_vref_txt_from_usfm_extract_jsonl.py  -i INPUT_FILENAME  -o OUTPUT_FILENAME \
                                             -v VREF_FILENAME
```

**Examples**
```
extract_vref_txt_from_usfm_extract_jsonl.py -i extract.jsonl -o f_usfm.txt -v f_usfm_vref.txt
extract_vref_txt_from_usfm_extract_jsonl.py -h
```

<details>
<summary>Argument notes</summary>

* *extract.jsonl* (input) is the file produced by script [usfm_check.py](https://github.com/BibleNLP/greek-room/edit/main/greekroom/greekroom/usfm/README.md).
* *f_usfm.txt* (output) is the Bible corpus in plain text, one verse per line.
* *f_usfm_vref.txt* (output) is a companion file of verse IDs, matching *f_usfm.txt* line by line.
</details>

### versification.py

This main reversification script:
1. Checks the standard versification schema files for any internal **inconsistencies** such as duplicate target verse IDs, verse IDs outside the scope as defined in the chapter length section. Results are written to the file specified by the -d option.
2. Identifies ("sniffs") and reports the **best-fitting** versification schema for the input, **reporting** how well the corpus fits with repect to each versification schema.
3. **Reversifies** the corpus from the schema identified in (2) to the 'org' schema.
4. **Reports problems** during reversification, such as verses being dropped due to duplicate target verse IDs or a source verse ID not being mapped to a valid target ID as specified by -t ORG_VERSE_ID_FILENAME
5. Provides a **back-versification** dictionary to the file specified by the -b option. 

#### Typical usage
```
versification.py -i INPUT_CORPUS_FILENAME  -j INPUT_VERSE_ID_FILENAME \
                 -t ORG_VERSE_ID_FILENAME -o OUTPUT_CORPUS_FILENAME \
                 -b BACK_VERSIFICATION_FILENAME  -d DATA_LOG_FILENAME
```

**Examples**
```
versification.py -i f_usfm.txt -j f_usfm_vref.txt -t vref.txt \
                 -o f_usfm_reversified.txt -b back_versification.json \
                 -d data_log.txt
versification.py -h
```

<details>
<summary>Argument notes</summary>

* *f_usfm.txt* (input) is the Bible corpus file produced by script *extract_vref_txt_from_usfm_extract_jsonl.py* (or by some other script)
* *f_usfm_vref.txt* (input) is the verse ID file produced by script *extract_vref_txt_from_usfm_extract_jsonl.py* (or by some other script)
* *vref.txt* (input) is the target verse ID order that the output file *f_usfm_reversified.txt* should be in (standard *vref.txt* file available at [data/vref.txt](data/vref.txt))
* *f_usfm_reversified.txt* (output) is the reversified Bible corpus (typically following the 'org' schema) matching *vref.txt* line by line.
* *back_versification.json* (optional output) contains a back versification dictionary that supports other tool to convert verse ID from the 'org' schema back to what the user submitted.
* *data_log.txt* reports any inconsistencies in the standard schema versification mapping files.
</details>


### versification_diff_html.py

This script visualizes the differences between two versions of a versified Bible corpus.

#### Typical usage
```
versification_diff_html.py INPUT_FILENAMES  -r REFERENCE_FILENAME  -l FILE_LEGENDS \
                           -v VREF_FILENAME  -o OUTPUT_FILENAME
```

**Examples**
```
versification_diff_html.py corpus-version1.txt corpus-version2.txt -r reference-corpus.txt -l version1 version2 reference -v vref.txt -o vers_diff.html
versification_diff_html.py -h
```

<details>
<summary>Argument notes</summary>

* *corpus-version1.txt* (input) is one version of a reversification.
* *corpus-version2.txt* (input) is another version of a reversification.
* *reference-corpus* (input) is a reference corpus.
* *version1, version2, reference* (input) are the *legends* (table head titles).
* *vref.txt* (input) is a file with the verse IDs, same number of lines as the corpus files.
* *vers_diff.html* (output) is the visualized difference between the 2 versification versions.
</details>

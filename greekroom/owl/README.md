# owl

The OWL directory hosts a range of smaller checks, such as for repeated words (e.g. "the the").

## repeated_words.py

This script checks for repeated words (e.g. "the the").

The data files legitimate_duplicates.jsonl list known legitimate repeated words for specific languages (e.g. Greek "ἀμὴν ἀμὴν" ("truly, truly")).
* https://github.com/BibleNLP/greek-room/blob/main/greekroom/owl/data/legitimate_duplicates.jsonl
* $XDG_DATA_HOME/greekroom/owl/data/legitimate_duplicates.jsonl
* $HOME/.local/share/greekroom/owl/data/legitimate_duplicates.jsonl
* /usr/share/greekroom/owl/data/legitimate_duplicates.jsonl


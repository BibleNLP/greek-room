---
title: Wildebeest

---
This tool checks a text for a wide range of character level problems such as encoding errors, characters in the wrong script, characters in non-canonical forms and spurious control characters. The Wildebeest analysis script provides feedback on likely issues in a text. The Wildebeest normalization script corrects problems that can be fixed with very high confidence.

## eBible Corpus
We applied the Wildebeest tools to the 1009 translations in the <a href="https://arxiv.org/abs/2304.09919">eBible corpus</a>. This was part of a project in collaboration with the Partnership for Applied Biblical Natural Language Processing (PAB-NLP) in 2022 and 2023. The Wildebeest normalization scripts made 3.3 million changes in 220 out of the 1009 eBible translations, with subsequent visualization and human review. The majority of changes are not or only barely visible to the human eye, but greatly facilitate further computational processing. See the results in the following links:

* <a href="https://greekroom.org/wildebeest/ebible/" target="_blank">Wildebeest analysis results as applied to the original eBible translations</a>
* <a href="https://greekroom.org/wildebeest/ebible-orig-plus-diff/" target="_blank">List of changes made to the eBible translations by the Wildebeest normalization scripts</a>
* <a href="https://greekroom.org/wildebeest/ebible-plus/" target="_blank">Wildebeest analysis results as applied to the updated eBible translations</a>

Some of the remaining issues flagged might be perfectly valid translations after all. (E.g. some English Bible translations deliberately contain Hebrew characters in the Psalms.) Other issues will need to be corrected by Bible translators with native speaker competence.

## Using *Wildebeest*
**Software installation:** <a target="_GITHUB" href="https://github.com/uhermjakob/wildebeest">Wildebeest on GitHub</a> (includes description, usage,  installation ``pip install wildebeest-nlp``, code)<br>
**For Bible translators:** see support info under **[Spell Checking]({{< ref "/spell" >}} "Spell Checking")**

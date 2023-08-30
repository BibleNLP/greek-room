---
title: Word Alignment Visualization

---
Word alignment supports applications such as spell-checking and learning word order and morphology. Even more directly, it indicates the strength of translation consistency. With its color-coded word alignment strengths, the Greek Room specifically helps to pinpoint words that are unusual translations, or missing or spurious words. Hovering with the mouse over a word in the source or target language will reveal additional information such as the glosses of a word.

## Examples from English-German and English-Hindi

* <a href="/align/data/eng-deu-sel.html" target="_blank">Word alignment visualization for English NRSV and German LU84NR06 (selection)</a>
* <a href="/align/data/eng-hin-sel.html" target="_blank">Word alignment visualization for English ESVUS16 and Hindi IRV (selection)</a>

## Color and text-decoration codes

* Red indicates an unreliable link. This might indicate a translation problem, but could also just reflect a rare word or an unusual translation.
* Copper rose indicates a link of mixed reliability.
* Green indicates a fairly reliable link.
* Orange indicates that Greek Room has determined a phrase to be spurious (with respect to the other translation).
* Blue indicates a link bolstered by phonetic string similarity (not used if the link is already highly reliable otherwise).
* Light blue indicates that a link was added (in mouse-over hover mode).
* Purple indicates that a link was deleted (in mouse-over hover mode).
* An underscore indicates that a word is not aligned.
* A green underscore indicates that a word is not aligned and that the word is often not aligned ("no worries").
* A double-underscore indicates that a word alignment was updated.
* A dashed-underscore indicates that a word is aligned to multiple non-contiguous words on the other side.
* The ⟡ symbol to mark spell-checking information (use mouse-over).

## Abbreviations

When you hover over a word, additional information becomes available. Below are abbreviations that occur in the pop-ups.

* gloss: a fairly literal translation of the word, without considering context
* NULL: this indicates that the word often does not correspond to a word in the other language
* c: count (not counting present word)
* p: probabilities (for both directions)
* jc: joint count (of word and its aligned word, not counting present link)
* fw: function word (e.g. *and* and *the*)
* sed: smart (phonetic) edit distance; the closer the sed is to 0, the closer the two words are phonetically
* s: score
* rom: romanization (conversion to Latin alphabet)
* []: number in square brackets indicates word position starting at 0: [0] = first word, [1] = second word etc.


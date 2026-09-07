# Wildebeest

The Wildebeest scripts investigate, repair and normalize text for a wide range of issues at the character level.<br>
This document focuses on the interface that supports external editors such as Fluent.

See Wildebeest section under [../../README.md](../../README.md#wb) for documentation.

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


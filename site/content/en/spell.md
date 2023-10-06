---
title: Spell Checking

---
The Greek Room offers a spell checker based on phonetic string similarity and word alignment, rather than relying on the need of laboriously curated lists of words and morphological rules used in traditional spell checkers. It allows to identify spelling inconsistencies early on in Bible translation projects. In the word alignment visualization tool, the Greek Room uses the ⟡ symbol to mark spell-checking information.

## Hindi IRV
The <a href="https://www.bible.com/bible/1980" target="_HinIRV">Hindi IRV</a> is a Bible translation that has undergone multiple rounds of checking over several years. 
Still, our spell checker has found a number of likely spelling inconsistencies for both names and non-names.

▶ <a href="/spell/data/spell-summary_hi-IRVHin_en-ESVUS16.html" target="_blank">Spell checker in summary view for Hindi IRV (using ESV 2016 US as pivot)</a>

Example: चरवाहों (caravaahom) vs.  चरावाहों (caraavaahom)
* IRV GEN 29:4  अतः याकूब ने **चरवाहों** से पूछा, “हे मेरे भाइयों, तुम कहाँ के हो?” उन्होंने कहा, “हम हारान के हैं।”
* IRV SNG 1:8  ... और **चरावाहों** के तम्बुओं के पास, अपनी बकरियों के बच्चों को चरा।
* NIV GEN 29:4  Jacob asked the **shepherds**, ‘My brothers, where are you from?’ ‘We’re from Harran,’ they replied.
* NIV SNG 1:8  ... and graze your young goats by the tents of the **shepherds**.

Example: यहोशापात	 (Yahoshaapaat) vs. यहोशाफात (Yahoshaaphaat)
* IRV 1KI 22:41  इस्राएल के राजा अहाब के राज्य के चौथे वर्ष में आसा का पुत्र **यहोशापात** यहूदा पर राज्य करने लगा।
* IRV MAT 1:8  आसा से **यहोशाफात** उत्पन्न हुआ, और यहोशाफात से योराम उत्पन्न हुआ, और योराम से उज्जियाह उत्पन्न हुआ।
* NIV 1KI 22:41  **Jehoshaphat** son of Asa became king of Judah in the fourth year of Ahab king of Israel.
* NIV MAT 1:8  Asa the father of **Jehoshaphat**, Jehoshaphat the father of Jehoram, Jehoram the father of Uzziah,
For reference, both English NIV and English ESVUS16 use **Jehoshaphat** for both 1KI 22:41 and MAT 1:8.

## English NRSV
The English NRSV is a highly curated translation. While our checker did not find any common word typos, it did find a number of potential spelling inconsistencies for Biblical names.

▶ <a href="/spell/data/spell-summary_en-NRSV_de-LU84NR06.html" target="_blank">Spell checker in summary view for English NRSV (using German LU84NR06 as pivot)</a>

Example: Addan vs. Addon
* NRSV EZR 2:59   The following were those who came up from Tel-melah, Tel-harsha, Cherub, **Addan**, and Immer, though they could not prove their families or their descent, whether they belonged to Israel:
* NRSV NEH 7:61   The following were those who came up from Tel-melah, Tel-harsha, Cherub, **Addon**, and Immer, but they could not prove their ancestral houses or their descent, whether they belonged to Israel:
* For reference, both English NIV and German LU84NR06 use **Addon** in both EZR 2:59 and NEH 7:61.

Example: Immanuel vs. Emmanuel
* NRSV ISA 7:14   Therefore the Lord himself will give you a sign. Look, the young woman is with child and shall bear a son, and shall name him **Immanuel**.
* NRSV MAT 1:23   “Look, the virgin shall conceive and bear a son, and they shall name him **Emmanuel**,” which means, “God is with us.”
* For reference, both English NIV and German LU84NR06 use **Immanuel** in both ISA 7:14 and MAT 1:23.

Example: Judas vs. Jude
* NRSV MAT 10:4   Simon the Cananaean, and **Judas** Iscariot, the one who betrayed him.
* NRSV JUD 1:1   **Jude**, a servant of Jesus Christ and brother of James, To those who are called, who are beloved in God the Father and kept safe for Jesus Christ:
* The New Testament refers to several people named *Ἰούδας* (*Judas*). Bible translations for most languages use the same name for the various Judas characters (as in the original Greek), but most English translations deliberately use a different name, **Jude**, for the Book of Jude.

Example: Abiasaph vs. Ebiasaph
* NRSV EXO 6:24   The sons of Korah: Assir, Elkanah, and **Abiasaph**; these are the families of the Korahites.
* NRSV 1CH 6:22   son of Tahath, son of Assir, son of **Ebiasaph**, son of Korah,
* For reference, while German LU84NR06 and a few English translation use the same name for both EXO 6:24 and 1CH 6:22 (**Abiasaf** (in German) or **Abiasaph** (in English)), most English translations differentiate between **Abiasaph** and **Ebiasaph**.

The final decision on whether or not names in different Bible verses should be spelled the same lies with the human translator and consultant.

The spell checker also flags a number of (legitimate) morpholocial variations such as *drink, drank, drunk* or *woman, women*. This information can be useful for other aspects of Biblical natural language processing.

## Other translations

For the German LU84NR06 translation, the spell checker also flagged a few pairs of archaic/modern forms.
* höret (archaic), hört (modern) ["listen", plural imperative form of "hören"]
* ward (archaic), wurde (modern)  ["became", singular third person past tense form of "werden"]

We have also successfully applied the Greek Room's spell checker on partial translations of the Bible in several Asian minority languages (not public).

## Using Spell Checking

**For Bible translators:** We currently offer spell checking support for Bible translation projects on servers running at USC. Please contact us at support@greekroom.org
<details><summary>Preferred format of spell checker input</summary>
<ul>
  <li>USFM files (as e.g. exported from Paratext)</li>
  <li>Preferably also the <tt>settings.xml</tt> file for more accurate versification in the Greek Room results</li>
  <li>You can also supply the entire Paratext folder that contains the above (and possibly other stuff).</li>
</ul>
You may attach the input data to the email you send us, or you can provide us with a location from where we can download the data.<br>
Spell checking and Wildebeest results will typically be provided on a password-protected server.
</details>

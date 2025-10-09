## Versification standard mapping data files

#### Errors/warnings reported by script
* **Invalid mapping sources** &nbsp; The source of mappedVerse is outside the scope of verses per maxVerses. Example: In vul.json, JON 1 has only 16 verses, but it the mapping includes "JON 1:17": "JON 2:1"
* **Invalid mapping targets** &nbsp; The target of mappedVerse is outside the scope of verses per maxVerses.
* **Dropped verses** &nbsp; Source verse IDs are not mapped to a valid target verse ID. Example: In eng.json, "2CO 13:14" is valid but unmapped; in 'org', "2CO 13" has only 13 verses, to the source's "2CO 13:14" is dropped and does not appear anywhere in the reversified Bible.
* **Duplicate target verses** &nbsp; More than one mapping goes to the same target verse ID. An explicit merge (e.g. "2CO 13:12-13": "2CO 13:12") counts as a single mapping to "2CO 13:12". What counts as a duplicate target verse ID is when more than 2 distinct mappings map to the same target verse ID, or, more commonly, there is an explicit mapping to a target verse ID, and there is an unmapped same verse ID on the source side that by default is mapped to itself.
* **ranges have different lengths** &nbsp; Example: "PSA 89:2-6": "PSA 90:1-6" with 5 and 6 verses respectively.
* **bad source range** &nbsp; Example: verse range "52-23" (23 is less than 52)
* **Found implausibly large merges** &nbsp; Example: "DAG 13:1-63": "SUS 1:63" (63 verses are mapped to 1 verse, probably not intended)

#### versification_data_log_orig_mappings.txt
* Error reports for mapping data initialized from [versification_utils/standard_mappings](https://github.com/jcuenod/versification_utils/tree/main/versification_utils/standard_mappings)
* Most errors in Apocrypha.

#### versification_data_log_v20251008.txt
* Some repair, mostly eng.json, rsc.json
* No more errors reported for Old and New Testament verses in org.json, eng.json, rsc.json
* eng.json: 
  Found 6 merges: NEH 7:68-69 -> NEH 7:68; PSA 13:5-6 -> PSA 13:6; ISA 64:1-2 -> ISA 64:1; HAB 3:19-20 -> HAB 3:19; ACT 19:40-41 -> ACT 19:40; 2CO 13:12-13 -> 2CO 13:12
  Found 4 splits: PSA 51:0 -> PSA 51:1-2; PSA 52:0 -> PSA 52:1-2; PSA 54:0 -> PSA 54:1-2; PSA 60:0 -> PSA 60:1-2
* rsc.json:
  Found 5 merges: 1SA 20:42-43 -> 1SA 21:1; NEH 7:68-69 -> NEH 7:68; PSA 89:0-1 -> PSA 90:0; ISA 64:1-2 -> ISA 64:1; HAB 3:19-20 -> HAB 3:19
  Found 5 splits: LEV 14:55 -> LEV 14:55-56; PSA 86:2 -> PSA 87:1-2; PSA 89:6 -> PSA 90:5-6; SNG 1:1 -> SNG 1:1-2; 2CO 11:32 -> 2CO 11:32-33


# greekroom  

_greekroom_ is a suite of tools to support Biblical natural language processing (in progress)

<!--
[![image alt >](http://img.shields.io/pypi/v/greekroom.svg)](https://pypi.python.org/pypi/greekroom/)

### Installation (stubs only, in early development, not ready for regular users yet)

```bash
pip install greekroom
```
or
```bash
git clone https://github.com/BibleNLP/greek-room.git
```
-->


## owl 
A battery of smaller Bible Translation checks

<details>
<summary> <b>wb_util.py</b>
A CLI Python script to analyze file properties such as script direction, quotations.</summary>

```
usage: wb_util.py [-h] [-i INPUT_FILENAME] [-s INPUT_STRING] [-j JSON_OUT_FILENAME] [-o HTML_OUT_FILENAME] [--lang_code LANG_CODE] [--lang_name LANG_NAME]

options:
  -h, --help            show this help message and exit
  -i INPUT_FILENAME, --input_filename INPUT_FILENAME
  -s INPUT_STRING, --input_string INPUT_STRING
  -j JSON_OUT_FILENAME, --json_out_filename JSON_OUT_FILENAME
  -o HTML_OUT_FILENAME, --html_out_filename HTML_OUT_FILENAME
  --lang_code LANG_CODE
  --lang_name LANG_NAME
```
Sample calls
```
wb_util.py -h
wb_util.py -s """She asked: “Whatʼs a ‘PyPi’?”\nHe replied: “I don't know.”\n""" -j test.json
cat test.json
```
</details>

<details>
<summary> <b>gr_utilities.wb_util</b>
A Python function to analyze file properties such as script direction, quotations.</summary>
```python 
import json
from gr_utilities import wb_util

# Apply script to string
text = """She asked: “Whatʼs a ‘PyPi’?”\nHe replied: “I don't know.”\n"""
result_dict = wb_util.script_punct(None, text, "eng", "English")
print(result_dict)

# Apply script to file content
# Write text to file
filename = "test.txt"
with open(filename, "w") as f_out:
    f_out.write(text)
# Apply script
result_dict2 = wb_util.script_punct(filename)
# Print result as JSON string
print(json.dumps(result_dict2))
# Write result to HTML file
html_output = "test.html"
with open(html_output, "w") as f_html:
    wb_util.print_to_html(result_dict2, f_html)
``` 
</details>

## gr_utilities


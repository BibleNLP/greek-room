#!/usr/bin/env python

import json
try:
    from gr_utilities import wb_file_props
except ImportError:
    from greekroom.gr_utilities import wb_file_props

# Apply script to string
text = """She asked: “Whatʼs a ‘PyPi’?”\nHe replied: “I don't know.”\n"""
result_dict = wb_file_props.script_punct(None, text, "eng", "English")
print(result_dict)

# Apply script to file content
# Write text to file
filename = "test.txt"
with open(filename, "w") as f_out:
    f_out.write(text)
# Apply script
result_dict2 = wb_file_props.script_punct(filename)
# Print result as JSON string
print(json.dumps(result_dict2))
# Write result to HTML file
html_output = "test.html"
with open(html_output, "w") as f_html:
    wb_file_props.print_to_html(result_dict2, f_html)

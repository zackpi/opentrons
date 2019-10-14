import os
import re
import difflib

from opentrons.drivers.smoothie_drivers.driver_3_0 import GCODES
from itertools import groupby
from pathlib import Path


GCODES = dict((y, x) for x, y in GCODES.items())


def make_string_list(path_str, substrings: list):
    with open(Path(path_str)) as file:
        content_str = file.readlines()
    filtered_contents = list(
        filter(lambda line: all(substr in line for substr in substrings),
               content_str))
    for line in filtered_contents:
        new_line = line.split('smoothie: Write -> b')[1].rstrip()
        formatted_line = new_line.strip("'").strip('\\r\\n\\r\\n')
        yield make_gcode_readable(formatted_line)


def make_gcode_readable(line):
    patterns = re.compile('|'.join(GCODES.keys()))
    for pattern in patterns.findall(line):
        line = re.sub(pattern, GCODES[pattern], line)
    return line


all_files = list(filter(lambda x: x.endswith('.txt'), sorted(os.listdir())))
grouped_logs = {
    key: list(group)
    for key, group in groupby(all_files, lambda y: y.split('_')[0])}

for key, value in grouped_logs.items():
    contents = list(make_string_list(value[0], ['smoothie: Write', 'opentrons-api-serial']))
    contents2 = list(make_string_list(value[1], ['smoothie: Write', 'opentrons-api-serial']))
    output_file = open(f"{key}.html", "w")
    hd = difflib.HtmlDiff()
    output_file.write(
        hd.make_file(contents, contents2, context=False))
    output_file.close()

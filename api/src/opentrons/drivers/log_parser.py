import argparse
import difflib
import re
import sys

from opentrons.drivers.smoothie_drivers.driver_3_0 import GCODES
from pathlib import Path
from typing import TextIO

GCODES = dict((y, x) for x, y in GCODES.items())

parser_args = {
    'serial': ['smoothie: Write', 'opentrons-api-serial'],
    'api': ['opentrons-api']
    }


def get_str_list(log_file, substrings: list):
    content_str = log_file.read().decode('utf-8')
    filtered_contents = list(
        filter(lambda line: all(substr in line for substr in substrings),
               content_str))
    print(filtered_contents)
    for line in filtered_contents:
        new_line = line.split('smoothie: Write -> b')[1].rstrip()
        formatted_line = new_line.strip("'").strip('\\r\\n\\r\\n')
        print(formatted_line)
        yield interpret_gcode(formatted_line)


def interpret_gcode(line):
    patterns = re.compile('|'.join(GCODES.keys()))
    for pattern in patterns.findall(line):
        line = re.sub(pattern, GCODES[pattern], line)
    return line


def compare(log_1: TextIO,
            log_2: TextIO,
            log_type: str):
    # print(log_1)
    contents_1 = list(get_str_list(log_1, parser_args[log_type]))
    contents_2 = list(get_str_list(log_2, parser_args[log_type]))
    print(contents_1)
    print(contents_2)
    # output_file = open(f"{log_type}.html", "w")
    # hd = difflib.HtmlDiff()
    # output_file.write(
    #     hd.make_file(contents_1, contents_2, context=False))
    # output_file.close()


def get_arguments(
        parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument(
        'log_1', type=argparse.FileType('rb'),
        help='The first log file to compare')
    parser.add_argument(
        'log_2', type=argparse.FileType('rb'),
        help='The second log file to compare')
    parser.add_argument(
        'log_type', action='store',
        choices=['serial', 'api'],
        help='Type of logs')
    return parser


def main() -> int:
    parser = argparse.ArgumentParser(prog='opentrons_compare_logs',
                                     description='Compare two OT-2 logs')
    parser = get_arguments(parser)
    args = parser.parse_args()

    compare(args.log_1,
            args.log_2,
            args.log_type)

    return 0


if __name__ == '__main__':
    sys.exit(main())

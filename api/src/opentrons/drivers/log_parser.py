import argparse
# import difflib
# import os
import re
import sys

from opentrons.drivers.smoothie_drivers.driver_3_0 import GCODES
# from itertools import groupby
from pathlib import Path


GCODES = dict((y, x) for x, y in GCODES.items())

parser_args = {
    'serial-log': ['smoothie: Write', 'opentrons-api-serial'],
    'api-log': ['help!']
    }


def get_str_list(path_str, substrings: list):
    with open(Path(path_str)) as file:
        content_str = file.readlines()
    filtered_contents = list(
        filter(lambda line: all(substr in line for substr in substrings),
               content_str))
    for line in filtered_contents:
        new_line = line.split('smoothie: Write -> b')[1].rstrip()
        formatted_line = new_line.strip("'").strip('\\r\\n\\r\\n')
        yield interpret_gcode(formatted_line)


def interpret_gcode(line):
    patterns = re.compile('|'.join(GCODES.keys()))
    for pattern in patterns.findall(line):
        line = re.sub(pattern, GCODES[pattern], line)
    return line


# all_files = list(filter(lambda x: x.endswith('.txt'), sorted(os.listdir())))
# grouped_logs = {
#     key: list(group)
#     for key, group in groupby(all_files, lambda y: y.split('_')[0])}
#
# for key, value in grouped_logs.items():
#     contents = list(get_str_list(value[0], ))
#     contents2 = list(get_str_list(value[1], ))
#     output_file = open(f"{key}.html", "w")
#     hd = difflib.HtmlDiff()
#     output_file.write(
#         hd.make_file(contents, contents2, context=False))
#     output_file.close()


def get_arguments(
        parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("path1")
    parser.add_argument("path2")
    # parser.add_argument(
    #     '-l', '--log-level',
    #     choices=['debug', 'info', 'warning', 'error', 'none'],
    #     default='warning',
    #     help=    #     'utility as part of an automated workflow.')
    # parser.add_argument(
    #     '-v', '--version', action='version',
    #     version=f'%(prog)s {opentrons.__version__}',
    #     help='Print the opentrons package version and exit')
    # parser.add_argument(
    #     '-o', '--output', action='store',
    #     help='What to output during simulations',
    #     choices=['runlog', 'nothing'],
    #     default='runlog')
    return parser


def main() -> int:
    parser = argparse.ArgumentParser(prog='opentrons_compare_logs',
                                     description='Compare two OT-2 logs')
    parser = get_arguments(parser)
    args = parser.parse_args()

    print(f'This is path 1: {args.path1}')
    print(f'This is path 2: {args.path2}')
    #
    # args = parser.parse_args()
    # runlog, maybe_bundle = simulate(
    #     args.protocol,
    #     args.protocol.name,
    #     getattr(args, 'custom_labware_path', []),
    #     getattr(args, 'custom_data_path', [])
    #     + getattr(args, 'custom_data_file', []),
    #     log_level=args.log_level)
    #
    # if maybe_bundle:
    #     bundle_name = getattr(args, 'bundle', None)
    #     if bundle_name == args.protocol.name:
    #         raise RuntimeError(
    #             'Bundle path and input path must be different')
    #     bundle_dest = _get_bundle_dest(
    #         bundle_name, 'PROTOCOL.ot2.zip', args.protocol.name)
    #     if bundle_dest:
    #         bundle.create_bundle(maybe_bundle, bundle_dest)
    #
    # if args.output == 'runlog':
    #     print(format_runlog(runlog))

    return 0


if __name__ == '__main__':
    sys.exit(main())

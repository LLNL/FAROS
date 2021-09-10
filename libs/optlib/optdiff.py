#!/usr/bin/env python3
#
# Based on LLVM tools opt-viewer under license
# SPDX-License-Identifier: "Apache-2.0 WITH LLVM-exception"
#
# Modified by: Giorgis Georgakoudis, georgakoudis1@llnl.gov
#


from __future__ import print_function

desc = '''Generate the difference of two YAML files into a new YAML file (works on
pair of directories too).  A new attribute 'Added' is set to True or False
depending whether the entry is added or removed from the first input to the
next.

The tools requires PyYAML.'''

import yaml
# Try to use the C parser.
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

from libs.optlib import optrecord
import argparse
from collections import defaultdict

def generate_diff(yaml_dir_or_file_1, yaml_dir_or_file_2, print_progress, jobs, filter_only, max_size, output):
    files1 = optrecord.find_opt_files(yaml_dir_or_file_1)
    files2 = optrecord.find_opt_files(yaml_dir_or_file_2)

    all_remarks1, _, _ = optrecord.gather_results(files1, jobs, print_progress)
    all_remarks2, _, _ = optrecord.gather_results(files2, jobs, print_progress)

    if filter_only:
        if filter_only.lower() == 'missed':
            all_remarks1 = { r:all_remarks1[r] for r in all_remarks1 if r[0] == optrecord.Missed }
            all_remarks2 = { r:all_remarks2[r] for r in all_remarks2 if r[0] == optrecord.Missed }
        elif filter_only.lower() == 'analysis':
            all_remarks1 = { r:all_remarks1[r] for r in all_remarks1 if r[0] == optrecord.Analysis }
            all_remarks2 = { r:all_remarks2[r] for r in all_remarks2 if r[0] == optrecord.Analysis }
        elif filter_only.lower() == 'passed':
            all_remarks1 = { r:all_remarks1[r] for r in all_remarks1 if r[0] == optrecord.Passed }
            all_remarks2 = { r:all_remarks2[r] for r in all_remarks2 if r[0] == optrecord.Passed }

    added = set(all_remarks2.values()) - set(all_remarks1.values())
    removed = set(all_remarks1.values()) - set(all_remarks2.values())

    for r in added:
        r.Added = True
    for r in removed:
        r.Added = False

    result = list(added | removed)
    for r in result:
        r.recover_yaml_structure()

    for i in range(0, len(result), max_size):
        with open(output.format(i / max_size), 'w') as stream:
            yaml.dump_all(result[i:i + max_size], stream)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument(
        'yaml_dir_or_file_1',
        help='An optimization record file or a directory searched for optimization '
             'record files that are used as the old version for the comparison')
    parser.add_argument(
        'yaml_dir_or_file_2',
        help='An optimization record file or a directory searched for optimization '
             'record files that are used as the new version for the comparison')
    parser.add_argument(
        '--jobs',
        '-j',
        default=None,
        type=int,
        help='Max job count (defaults to %(default)s, the current CPU count)')
    parser.add_argument(
        '--max-size',
        '-m',
        default=100000,
        type=int,
        help='Maximum number of remarks stored in an output file')
    parser.add_argument(
        '--no-progress-indicator',
        '-n',
        action='store_true',
        default=False,
        help='Do not display any indicator of how many YAML files were read.')
    parser.add_argument(
            '--filter-only',
            '-f',
            choices=['Missed', 'missed', 'Analysis', 'analysis', 'Passed', 'passed'],
            help='Filter out optimization remarks based on type')
    parser.add_argument('--output', '-o', default='diff{}.opt.yaml')
    args = parser.parse_args()

    generate_diff(
            args.yaml_dir_or_file_1,
            args.yaml_dir_or_file_2,
            not args.no_progress_indicator,
            args.jobs,
            args.filter,
            args.max_size,
            args.output)

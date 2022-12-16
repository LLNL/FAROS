#!/usr/bin/env python3
#
# Copyright 2020-2022 Lawrence Livermore National Security, LLC
# and project developers
#
# LLNL release number LLNL-CODE-813267
#
# Author: Giorgis Georgakoudis, georgakoudis1@lln.gov
#
# SPDX-License-Identifier: "Apache-2.0 WITH LLVM-exception"
#
# See top-level files LICENSE and NOTICE for details.
#

import argparse
import os
import sys
import json
import subprocess
from pathlib import Path

from libs.faros import faroslib as faros
from libs.optlib import optrecord
from libs.renderers import htmlviewer


def main():
    parser = argparse.ArgumentParser(
        description='Benchmark and analyze programs compiled with different compilation options.')
    parser.add_argument('-i', '--input', dest='input', type=str,
                        help='compilation database (compile_commands.json)')
    args = parser.parse_args()

    if args.input:
        compiledb_file = args.input
    else:
        compiledb_file = 'compile_commands.json'

    if not os.path.isfile(compiledb_file):
        sys.exit("Cannot fild compiledb file")

    with open(compiledb_file, 'r') as f:
        compiledb = json.load(f)

    try:
        os.mkdir('faros')
    except FileExistsError:
        # TODO: emit warning or ask user what to to?
        print('Warning: faros directory exists already')

    cwd = os.getcwd()
    fileinfo_list = []
    for entry in compiledb:
        directory = entry['directory']
        file = entry['file']
        arguments = None
        if 'command' in entry:
            arguments = entry['command'].split(' ')
            # Remove empty arguments.
            arguments = [a for a in arguments if a]
        else:
            arguments = entry['arguments']

        if arguments == None:
            sys.exit('Compiledb error: neither arguments nor command key is defined')

        ext_command = ' '.join(arguments) + ' -fsave-optimization-record'

        print('directory', directory)
        print('file', file)
        print('arguments', arguments)

        os.chdir(directory)

        # TODO: spawn shell or not?
        # TODO: what if there are two source files with the same name in different directories?
        # TODO: catch exceptions
        subprocess.run(ext_command, shell=True, check=True)

        basename = os.path.basename(file)
        remark_filename = basename + '.opt.yaml'
        p = list(Path('.').glob('**/'+remark_filename))
        assert len(p) == 1, 'Expect one remark file'
        all_remarks, file_remarks, should_display_hotness = \
            optrecord.gather_results(
                [p[0]],
                1,      # num jobs
                True    # print progress
            )
        fileinfo_list.append(
            {'file': file, 'all_remarks': all_remarks, 'file_remarks': file_remarks})
        #faros.invoke_optviewer('../', p, 'faros', 1, True)

    htmlviewer.render_html(fileinfo_list)
    os.chdir(cwd)


if __name__ == '__main__':
    main()

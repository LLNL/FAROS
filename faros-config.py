#!/usr/bin/env python3
#
# Copyright 2020 Lawrence Livermore National Security, LLC
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
import yaml

from libs.faros import faroslib as faros


def main():
    parser = argparse.ArgumentParser(
        description='Benchmark and analyze programs compiled with different compilation options.')
    parser.add_argument('-i', '--input', dest='input', type=str,
                        help='configuration YAML input file for programs', required=True)
    parser.add_argument('-f', '--fetch', dest='fetch', action='store_true',
                        help='fetch program repos (without building)')
    parser.add_argument('-b', '--build', dest='build',
                        action='store_true', help='build programs (will fetch too)')
    parser.add_argument('-r', '--run', dest='run',
                        type=int, help='run <repetitions>')
    parser.add_argument('-g', '--generate', dest='generate',
                        action='store_true', help='generate compilation reports')
    parser.add_argument('-p', '--programs', dest='programs',
                        type=str, nargs='+', help='programs to run from the config')
    parser.add_argument('-t', '--tags', dest='tags', type=str,
                        nargs='+', help='tagged program to use from the config')
    parser.add_argument('-s', '--stats', dest='stats',
                        action='store_true', help='show run statistics')
    parser.add_argument('-d', '--dry-run', dest='dry',
                        action='store_true', help='enable dry run')
    parser.add_argument('-v', '--verbose', dest='verbose',
                        action='store_true', help='verbose printing')
    args = parser.parse_args()

    with open(args.input, 'r') as f:
        config = yaml.load(f, Loader=CLoader)

    print('# apps: ', len(config), ' selected ', args.programs)
    if args.verbose:
        print('args.programs', args.programs)
        print('args.tags', args.tags)
        print('args.fetch', args.fetch)
        print('args.build', args.build)
        print('args.run', args.run)
        print('args.generate', args.generate)

    programs = []
    if args.programs:
        if args.programs == ['all']:
            programs += config.keys()
        else:
            programs += args.programs
    if args.tags:
        for t in args.tags:
            programs += [p for p in config.keys() if t in config[p]
                         ['tags'] and p not in programs]
    for p in programs:
        if args.fetch:
            repo_dir = './repos'
            fetch_cmd = config[p]['fetch']
            faros.fetch(repo_dir, fetch_cmd)
            print('Fetched', p, 'successfully under directory', repo_dir)
        if args.build:
            build_dict = config[p]['build']

            fetch_cmd = config[p]['fetch']
            repo_dir = './repos'
            report_dir = './reports/' + p
            build_dir = config[p]['build_dir']
            bin_output = config[p]['bin']
            clean_cmd = config[p]['clean']
            copy_list = config[p]['copy']
            for build_kind in build_dict:
                bin_dir = './bin/' + p + '/' + build_kind
                build_cmd = build_dict[build_kind]
                faros.build(fetch_cmd, repo_dir, build_dir, bin_dir, report_dir, bin_output,
                            build_kind, build_cmd, clean_cmd, copy_list, p)
        if args.run:
            run_cmd = config[p]['run']
            run_input = config[p]['input']
            build_list = config[p]['build'].keys()
            bin_output = config[p]['bin']
            metric_regex = config[p]['measure']
            faros.run(run_cmd, run_input, build_list, bin_output,
                      metric_regex, p, args.run, args.dry)
        if args.generate:
            report_dir = './reports/' + p
            build_dir = './repos/' + config[p]['build_dir']
            build_list = config[p]['build'].keys()
            faros.generate_remark_reports(report_dir, build_dir, build_list)
        if args.stats:
            build_list = config[p]['build'].keys()
            faros.show_stats(build_list, p)


if __name__ == '__main__':
    main()

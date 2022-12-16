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

import yaml
import subprocess
import os
import shutil
import time
import re
import numpy as np
from pathlib import Path
import itertools
import math
import sys

from libs.optlib import optrecord
from libs.optlib import optviewer
from libs.optlib import optdiff


def invoke_optviewer(source_dir, filelist, output_html_dir, num_jobs, print_progress):
    all_remarks, file_remarks, should_display_hotness = \
        optrecord.gather_results(
            filelist,           # filelist
            num_jobs,           # num jobs
            print_progress)     # print progress

    optviewer.map_remarks(all_remarks)

    print('source dir', source_dir)
    optviewer.generate_report(all_remarks,
                              file_remarks,
                              source_dir,                         # source dir
                              output_html_dir,                    # output dir
                              False,                              # no highlight
                              should_display_hotness,
                              100,                                # max hottest remarks in index
                              1,                                  # number of jobs
                              print_progress)                     # print progress


def invoke_optdiff(yaml_file_1, yaml_file_2, filter_only, out_yaml):
    optdiff.generate_diff(
        yaml_file_1,    # yaml file 1
        yaml_file_2,    # yaml file 2
        True,           # print progress
        1,              # num jobs
        filter_only,    # filter remarks
        100000,         # max remarks
        out_yaml)       # output yaml


def run(run_cmd, run_input, build_list, bin_output, metric_regex, program, reps, dry):
    print('Run program', program, 'with available builds', build_list)
    exe = run_cmd + ' ' + run_input
    os.makedirs('./results', exist_ok=True)
    results = {program: {}}
    try:
        with open('./results/results-%s.yaml' % (program), 'r') as f:
            results = yaml.load(f, Loader=CLoader)
    except FileNotFoundError as e:
        pass

    for build_kind in build_list:
        bin_dir = './bin/' + program + '/' + build_kind
        if not os.path.isfile(bin_dir + '/' + bin_output):
            print('ERROR: Missing binary %s' %
                  (bin_dir + '/' + bin_output))
            return
        try:
            if (not build_kind in results[program]) or (not results[program][build_kind]):
                start = 0
                results[program][build_kind] = []
            elif len(results[program][build_kind]) < reps:
                start = len(results[program][build_kind])
            else:
                print('FOUND', program, build_kind, 'runs',
                      len(results[program][build_kind]))
                continue
        except Exception as e:
            print('ERROR', e, 'running', program, 'build kind', build_kind)
            sys.exit(1)

        if dry:
            return

        print('RUN', program, build_kind, 'from', start, 'to', reps)

        for i in range(start, reps):
            print('path', bin_dir, 'exe', exe)
            t1 = time.perf_counter()
            try:
                p = subprocess.run(exe, capture_output=True,
                                   cwd=bin_dir, shell=True, check=True)
            except Exception as e:
                print('ERROR', e, 'running', exe)
                return
            out = str(p.stdout.decode('utf-8'))
            err = str(p.stderr.decode('utf-8'))
            output = out + err
            print(output)
            #print('Out', p.stdout.decode('utf-8') )
            #print('Err', p.stderr.decode('utf-8') )
            with open('%s/stdout-%d.txt' % (bin_dir, i), 'w') as f:
                f.write(p.stdout.decode('utf-8'))
            with open('%s/stderr-%d.txt' % (bin_dir, i), 'w') as f:
                f.write(p.stderr.decode('utf-8'))

            if p.returncode != 0:
                print('ERROR running', program, 'in', build_kind)
                sys.exit(p.returncode)

            t2 = time.perf_counter()

            print('Time elapsed', t2-t1, ' seconds')
            print('measure', metric_regex)
            if metric_regex:
                # try stdout
                try:
                    runtime = float(
                        re.search(metric_regex, output).group(1))
                    print('runtime:', runtime)
                except Exception as e:
                    print('ERROR', e, 'Invalid metric from regex')
                    runtime = math.inf
            else:
                runtime = t2 - t1

            results[program][build_kind].append(runtime)

            with open('./results/results-%s.yaml' % (program), 'w') as f:
                yaml.dump(results, f)


def show_stats(build_list, program):
    try:
        with open('./results/results-%s.yaml' % (program), 'r') as f:
            results = yaml.load(f, Loader=CLoader)
    except FileNotFoundError as e:
        print('ERROR', e, 'abort showing stats')
        return

    result_list = []
    num_runs = {}
    for b in build_list:
        if not results[program][b]:
            continue
        result_list.append((b, np.mean(results[program][b])))
        num_runs[b] = len(results[program][b])
    ranked = sorted(result_list, key=lambda x: x[1])
    print('=======')
    print(program, '# runs', num_runs, '\n')
    print('# Results\n')
    print('## Ranked by speed')
    fastest_build = ranked[0][0]
    fastest_xtime = ranked[0][1]
    for b in ranked:
        build = b[0]
        xtime = b[1]
        print(build, ':', '%8.3f' % (xtime), 's,', 'slowdown/%s: %8.3f' %
              (fastest_build, xtime/fastest_xtime))
    print('=======')


def merge_stats_reports(report_dir, build_dir, build_kind):
    # generate unified optimization report
    os.makedirs(report_dir, exist_ok=True)

    # merge reports
    filenames = Path(build_dir).rglob('*.opt.yaml')
    data = ''
    for filename in filenames:
        with open(filename, 'r') as f:
            fdata = f.read()

        # Fix file paths for HTML output.
        pathname, basename = os.path.split(filename)
        #print('pathname', pathname, 'basename', basename)
        # Remove .opt.yaml extension
        basename = basename.split('.')[0]
        print('filename', filename, 'basename', basename, 'pathname', pathname,
              'REPLACE', os.getcwd() + '/' + pathname + '/' + basename)
        #input('cont...')
        # Replace base filename in the repo with the full path.
        #fdata = fdata.replace( 'File: ' + basename, 'File: ' + os.getcwd() + '/' + pathname + '/' + basename)
        #fdata = fdata.replace( 'File: \'' + basename, 'File: \'' + os.getcwd() + '/' + pathname + '/' + basename)
        ## Replace other filenames with in the repo with the full path.
        #fdata = re.sub('File: ([\.])', 'File: ' + os.getcwd() + '/' + pathname  + r'/\1', fdata)
        #fdata = re.sub('File: \'([\.])', 'File: \'' + os.getcwd() + '/' + pathname  + r'/\1', fdata)
        #fdata = re.sub('File: \'([^\.\/])', 'File: \'' + os.path.expanduser('~') + r'/\1', fdata)

        data += fdata

    with open(report_dir + '/' + build_kind + '.opt.yaml', 'w') as f:
        f.write(data)

    # merge stats
    filenames = Path(build_dir).rglob('*.stats')
    data = {}
    for filename in filenames:
        with open(filename, 'r') as f:
            print('filename', filename)
            d = eval(f.read())
        data[str(filename)] = d

    with open(report_dir + '/' + build_kind + '.stats.yaml', 'w') as f:
        yaml.dump(data, f, default_flow_style=False)


def compile_and_install(build_dir, bin_dir, report_dir, bin_output, program, build_kind, clean_cmd, build_cmd, copy_list):
    exe_path = bin_dir + '/' + bin_output
    # File exists
    if os.path.isfile(exe_path):
        ans = input('Binary file ' + exe_path +
                    ' exists, recompile and install (y/n)?\n')
        if ans.lower() != 'y':
            return

    os.makedirs(bin_dir, exist_ok=True)
    print('Clean...')
    try:
        subprocess.run(clean_cmd, cwd=build_dir, shell=True, check=True)
    except Exception as e:
        print('ERROR', e, 'running the clean command')
        return
    print('===> Build...program %s build kind %s\n%s' %
          (program, build_kind, build_cmd))
    try:
        subprocess.run(build_cmd, cwd=build_dir, shell=True, check=True)
    except Exception as e:
        print('ERROR', e, 'building %s build kind %s failed' %
              (program, build_kind), e)
        sys.exit(1)

    print('Merge stats and reports...')
    merge_stats_reports(report_dir, build_dir, build_kind)

    print('Copy...')
    for copy in copy_list:
        if os.path.isdir(build_dir + '/' + copy):
            shutil.copytree(build_dir + '/' + copy, bin_dir + '/' + copy)
        else:
            shutil.copy(build_dir + '/' + copy, bin_dir)


def generate_diff_reports(build_dir, report_dir, builds, remark_kind):
    out_yaml = report_dir + '/' + \
        '%s-%s-%s.opt.yaml' % (builds[0], builds[1], remark_kind)
    output_html_dir = report_dir +'/' + \
        'html-%s-%s-%s' % (builds[0], builds[1], remark_kind)

    def generate_diff_yaml():
        print('Creating diff remark YAML files...')
        if remark_kind == 'all':
            filter_only = None
        else:
            filter_only = remark_kind

        try:
            invoke_optdiff(
                '%s/%s.opt.yaml' % (report_dir, builds[0]),
                '%s/%s.opt.yaml' % (report_dir, builds[1]),
                filter_only,
                out_yaml)
            print('Done generating YAML diff optimization report for builds %s|%s remark kind %s' % (
                builds[0], builds[1], remark_kind))
        except Exception as e:
            print('ERROR', e, 'Failed generating YAML diff optimization report for builds %s|%s remark kind %s' % (
                builds[0], builds[1], remark_kind))

    def generate_diff_html():
        print('Creating HTML report output diff for %s|%s...' %
              (builds[0], builds[1]))
        try:
            invoke_optviewer(
                os.getcwd() + '/' + build_dir,
                [out_yaml],
                output_html_dir,
                1, # num_jobs
                True # print_progress
            )
            print('Done generating compilation report for builds %s|%s remark kind %s' % (
                builds[0], builds[1], remark_kind))
        except Exception as e:
            print('ERROR', e, 'Failed generating compilation report for builds %s|%s remark kind %s' % (
                builds[0], builds[1], remark_kind))

    if os.path.exists(out_yaml):
        ans = input('Optimization remark diff YAML files for builds %s|%s remark_kind %s already found from previous build, regenerate (y/n)?\n' %
                    (builds[0], builds[1], remark_kind))
        if ans.lower() == 'y':
            generate_diff_yaml()
    else:
        generate_diff_yaml()

    if os.path.exists(output_html_dir):
        ans = input('HTML output for builds %s|%s remark_kind %s already exists, regenerate (y/n)?\n' %
                    (builds[0], builds[1], remark_kind))
        if ans.lower() == 'y':
            generate_diff_html()
    else:
        generate_diff_html()


def generate_remark_reports(report_dir, build_dir, build_list):
    def generate_html():
        print('Creating HTML report output for build %s ...' % (build))
        try:
            invoke_optviewer(
                os.getcwd() + '/' + build_dir,
                [in_yaml],
                output_html_dir,
                1,
                True)
            print('Done generating compilation reports!')
        except Exception as e:
            print('\n', 'ERROR', e, 'Failed generating compilation reports (expects build was '
                  'successful)', e)

    # Create reports for single build (no diff).
    for build in build_list:
        in_yaml = report_dir + '/%s.opt.yaml' % (build)
        output_html_dir = report_dir + '/html-%s' % (build)
        if os.path.exists(output_html_dir):
            ans = input(
                'HTML output for build %s exists, regenerate (y/n)?\n' % (build))
            if ans.lower() == 'y':
                generate_html()
        else:
            generate_html()

    # Create repors for 2-combinations of build options.
    if len(build_list) > 1:
        combos = itertools.combinations(build_list, 2)
        for build_pair in combos:
            generate_diff_reports(build_dir, report_dir, build_pair, 'all')
            generate_diff_reports(build_dir, report_dir,
                                  build_pair, 'analysis')
            generate_diff_reports(build_dir, report_dir, build_pair, 'missed')
            generate_diff_reports(build_dir, report_dir, build_pair, 'passed')


def fetch(repo_dir, fetch_cmd):
    os.makedirs(repo_dir, exist_ok=True)
    # clean and fetch (if needed)
    try:
        subprocess.run(fetch_cmd, cwd=repo_dir, shell=True, check=True)
    except Exception as e:
        print('ERROR', e, 'fetching')
        return


def build(fetch_cmd, repo_dir, build_dir, bin_dir, report_dir, bin_output, build_kind, build_cmd, clean_cmd, copy_list, program):
    build_dir = repo_dir + '/' + build_dir
    if not os.path.exists(build_dir):
        fetch(repo_dir, fetch_cmd)

    # build
    compile_and_install(build_dir, bin_dir, report_dir, bin_output, program,
                        build_kind, clean_cmd, build_cmd, copy_list)

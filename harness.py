#!/usr/bin/env python3
#
# Copyright 2020 Lawrence Livermore National Security, LLC
# and project developers
#
# LLNL release number LLNL-CODE-XXXXXX
#
# Author: Giorgis Georgakoudis, georgakoudis1@lln.gov
#
# SPDX-License-Identifier: "Apache-2.0 WITH LLVM-exception"
#
# See top-level files LICENSE and NOTICE for details.
#

import argparse
import yaml
from yaml import CLoader
import argparse
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

# Enable importing modules from opt-viewer
sys.path.append('./opt-viewer')
import optrecord
import optviewer
import optdiff

def invoke_optviewer(filelist, output_html_dir, jobs, print_progress):
    all_remarks, file_remarks, should_display_hotness = \
                optrecord.gather_results(
                        filelist,           # filelist
                        1,                  # num jobs
                        print_progress)     # print progress

    optviewer.map_remarks(all_remarks)

    optviewer.generate_report(all_remarks,
                file_remarks,
                '',                                 # source dir
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

def run(config, program, reps, dry):
    print('Launching program', program, 'with modes', config[program]['build'])
    exe = config[program]['run'] + ' ' + config[program]['input']
    os.makedirs( './results', exist_ok=True)
    results = { program: {} }
    try:
        with open('./results/results-%s.yaml'%(program), 'r') as f:
            results = yaml.load(f, Loader=CLoader)
    except FileNotFoundError as e:
        pass

    for mode in config[program]['build']:
        bin_dir = './bin/' + program + '/' + mode + '/'
        if not os.path.isfile( bin_dir + config[program]['bin'] ):
            print('ERROR: Missing binary %s'%( bin_dir + config[program]['bin'] ) )
            return
        try:
            if (not mode in results[program]) or (not results[program][mode]):
                start = 0
                results[program][mode] = []
            elif len(results[program][mode]) < reps:
                start = len(results[program][mode])
            else:
                print('FOUND', program, mode, 'runs', len(results[program][mode]) )
                continue
        except Exception as e:
            print('ERROR', e, 'running', program, 'mode', mode)
            sys.exit(1)

        print('RUN', program, mode, 'from', start, 'to', reps)

        if not dry:
            for i in range(start, reps):
                print('path', bin_dir, 'exe',exe)
                t1 = time.perf_counter()
                p = subprocess.run( exe, capture_output=True, cwd=bin_dir, shell=True )
                out = str(p.stdout.decode('utf-8'))
                err = str(p.stderr.decode('utf-8'))
                output = out + err
                print(output)
                #print('Out', p.stdout.decode('utf-8') )
                #print('Err', p.stderr.decode('utf-8') )
                with open('%s/stdout-%d.txt'%(bin_dir, i), 'w') as f:
                    f.write(p.stdout.decode('utf-8'));
                with open('%s/stderr-%d.txt'%(bin_dir, i), 'w') as f:
                    f.write(p.stderr.decode('utf-8'));

                if p.returncode != 0:
                    print('ERROR running', program, 'in', mode)
                    sys.exit(p.returncode)

                t2 = time.perf_counter()

                print('Time elapsed', t2-t1, ' seconds')
                print('measure', config[program]['measure'])
                if config[program]['measure']:
                    # try stdout
                    try:
                        runtime = float( re.search( config[program]['measure'], output).group(1) )
                        print('runtime:', runtime)
                    except AttributeError as e:
                        print('Invalid runtime', e)
                        runtime = math.inf
                else:
                    runtime = t2 - t1

                results[program][mode].append(runtime)

                with open('./results/results-%s.yaml'%(program), 'w') as f:
                    yaml.dump( results, f )

def show_stats(config, program):
    try:
        with open('./results/results-%s.yaml'%(program), 'r') as f:
            results = yaml.load(f, Loader=CLoader)
    except FileNotFoundError as e:
        return

    ranked = sorted( [ (b, np.mean( results[program][b]) ) for b in config[program]['build'] if results[program][b]], key=lambda x: x[1] )
    num_runs = { b : len( results[program][b])  for b in config[program]['build'] }
    print('=======')
    print(program, '# runs', num_runs, '\n')
    print('# Results\n')
    print('## Ranked by speed')
    for b in ranked:
        print(b[0], ':', '%8.3f'%(b[1]), 's,', 'slowdown/%s: %8.3f'%(ranked[0][0], b[1]/ranked[0][1]) )
    print('=======')
   
def merge_stats_reports( program, build_dir, mode ):
    # generate unified optimization report
    reports_dir = './reports/' + program + '/'
    os.makedirs( reports_dir, exist_ok=True )

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
        #print('filename', filename, 'basename', basename, 'pathname', pathname)
        # Replace base filename in the repo with the full path.
        fdata = fdata.replace( 'File: ' + basename, 'File: ' + os.getcwd() + '/' + pathname + '/' + basename)
        fdata = fdata.replace( 'File: \'' + basename, 'File: \'' + os.getcwd() + '/' + pathname + '/' + basename)
        # Replace other filenames with in the repo with the full path.
        fdata = re.sub('File: ([\.])', 'File: ' + os.getcwd() + '/' + pathname  + r'/\1', fdata)
        fdata = re.sub('File: \'([\.])', 'File: \'' + os.getcwd() + '/' + pathname  + r'/\1', fdata)
        fdata = re.sub('File: \'([^\.\/])', 'File: \'' + os.path.expanduser('~') + r'/\1', fdata)

        data += fdata

    with open(reports_dir + mode + '.opt.yaml', 'w') as f:
        f.write( data )

    with open(reports_dir + mode + '.opt.yaml', 'r') as f:
        data = yaml.load_all(f, Loader=CLoader)

    # merge stats
    filenames = Path(build_dir).rglob('*.stats')
    data = {}
    for filename in filenames:
        with open(filename, 'r') as f:
            print('filename', filename)
            d = eval( f.read() )
        data[ str(filename) ] = d

    with open(reports_dir + mode  + '.stats.yaml', 'w') as f:
        yaml.dump( data, f, default_flow_style=False )

def compile_and_install(config, program, repo_dir, mode):
    build_dir = repo_dir + '/' + config[program]['build_dir']
    bin_dir = './bin/' + program + '/' + mode + '/'
    exe = bin_dir + config[program]['bin']
    # File exists
    if os.path.isfile(exe):
        ans = input('Binary file ' + exe + ' exists, recompile and install (y/n)?\n')
        if ans.lower() != 'y':
            return

    os.makedirs(bin_dir, exist_ok=True)
    print('Clean...')
    subprocess.run( config[program]['clean'], cwd=build_dir, shell=True)
    print('===> Build...program %s mode %s\n%s' % (program, mode, config[program]['build'][mode]) )
    try:
        subprocess.run( config[program]['build'][mode], cwd=build_dir, shell=True )
    except Exception as e:
        print('building %s mode %s failed'%(program, mode), e)
        sys.exit(1)

    print('Merge stats and reports...')
    merge_stats_reports( program, build_dir, mode )

    print('Copy...')
    for copy in config[program]['copy']:
        if os.path.isdir( build_dir + '/' + copy ):
            shutil.copytree( build_dir + '/' + copy, bin_dir + copy)
        else:
            shutil.copy( build_dir + '/' + copy, bin_dir)


def generate_diff_reports( report_dir, builds, mode ):
    out_yaml = report_dir + '%s-%s-%s.opt.yaml'%( builds[0], builds[1], mode )
    output_html_dir = report_dir + 'html-%s-%s-%s'%( builds[0], builds[1], mode )

    def generate_diff_yaml():
        print('Creating diff remark YAML files...')
        if mode == 'all':
            filter_only = None
        else:
            filter_only = mode

        try:
            invoke_optdiff(
                    '%s/%s.opt.yaml'%(report_dir, builds[0]),
                    '%s/%s.opt.yaml'%(report_dir, builds[1]),
                    filter_only,
                    out_yaml)
            print('Done generating YAML diff optimization report for builds %s|%s mode %s'%( builds[0], builds[1], mode ))
        except:
            print('Failed generating YAML diff optimization report for builds %s|%s mode %s'%( builds[0], builds[1], mode ))

    def generate_diff_html():
        print('Creating HTML report output diff for %s|%s...' % ( builds[0], builds[1]) )
        try:
            invoke_optviewer(
                    [out_yaml],
                    output_html_dir,
                    1,
                    True)
            print('Done generating compilation report for builds %s|%s mode %s'%( builds[0], builds[1], mode ))
        except:
            print('Failed generating compilation report for builds %s|%s mode %s'%( builds[0], builds[1], mode ))

    if os.path.exists(out_yaml):
        ans = input('Optimization remark YAML files for builds %s|%s already found from previous build, regenerate (y/n)?\n'%(builds[0], builds[1]))
        if ans.lower() == 'y':
            generate_diff_yaml()
    else:
        generate_diff_yaml()

    if os.path.exists(output_html_dir):
        ans = input('HTML output for builds %s|%s mode %s already exists, regenerate (y/n)?\n'%( builds[0], builds[1], mode ))
        if ans.lower() == 'y':
            generate_diff_html()
    else:
        generate_diff_html()

def generate_remark_reports( config, program ):
    report_dir = './reports/' + program + '/'

    def generate_html():
        print('Creating HTML report output for build %s ...' % ( build ) )
        try:
            invoke_optviewer(
                    [in_yaml],
                    output_html_dir,
                    1,
                    True)
            print('Done generating compilation reports!')
        except:
            print('Failed generating compilation reports (expects build was '\
                    'successful)')

    # Create reports for single build (no diff).
    for build in config[program]['build']:
        in_yaml = report_dir + '%s.opt.yaml'%( build )
        output_html_dir = report_dir + 'html-%s'%( build )
        if os.path.exists(output_html_dir):
            ans = input('HTML output for build %s exists, regenerate (y/n)?\n'%(build))
            if ans.lower() == 'y':
                generate_html()
        else:
            generate_html()

    # Create repors for 2-combinations of build options.
    combos = itertools.combinations( config[program]['build'], 2 )
    for builds in combos:
        generate_diff_reports( report_dir, builds, 'all' )
        generate_diff_reports( report_dir, builds, 'analysis' )
        generate_diff_reports( report_dir, builds, 'missed' )
        generate_diff_reports( report_dir, builds, 'passed' )

def fetch(config, program):
    # directories
    repo_dir = './repos/'
    os.makedirs( repo_dir, exist_ok=True )

    # clean and fetch (if needed)
    subprocess.run( config[program]['fetch'], cwd=repo_dir, shell=True)

def build(config, program):
    repo_dir = './repos/'
    build_dir = repo_dir + '/' + config[program]['build_dir']
    if not os.path.exists(build_dir):
        fetch(config, program)

    # build
    for b in config[program]['build']:
        compile_and_install(config, program, repo_dir, b)

def main():
    print('main')
    parser = argparse.ArgumentParser(description='Benchmark and analyze programs compiled with different compilation options.')
    parser.add_argument('-i', '--input', dest='input', type=str, help='configuration YAML input file for programs', required=True)
    parser.add_argument('-f', '--fetch', dest='fetch', action='store_true', help='fetch program repos (without building)')
    parser.add_argument('-b', '--build', dest='build', action='store_true', help='build programs (will fetch too)')
    parser.add_argument('-r', '--run', dest='run', type=int, help='run <repetitions>')
    parser.add_argument('-g', '--generate', dest='generate', action='store_true', help='generate compilation reports')
    parser.add_argument('-p', '--programs', dest='programs', type=str, nargs='+', help='programs to run from the config')
    parser.add_argument('-t', '--tags', dest='tags', type=str, nargs='+', help='tagged program to use from the config')
    parser.add_argument('-s', '--stats', dest='stats', action='store_true', help='show run statistics')
    parser.add_argument('-d', '--dry-run', dest='dry', action='store_true', help='enable dry run')
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', help='verbose printing')
    args = parser.parse_args()

    with open(args.input, 'r') as f:
        config = yaml.load(f, Loader=CLoader)

    print( '# apps: ', len(config), ' selected ', args.programs )
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
            programs += [p for p in config.keys() if t in config[p]['tags'] and p not in programs]
    for p in programs:
        if args.fetch:
            fetch( config, p )
        if args.build:
            build( config, p )
        if args.run:
            run( config, p, args.run, args.dry )
        if args.generate:
            generate_remark_reports( config, p )
        if args.stats:
            show_stats( config, p)

if __name__ =='__main__':
    main()

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
import sys
import numpy as np
from pathlib import Path
import itertools
import math

# This is a "pretty" fix when we dump yaml files, mangled function names can be quite long. When yaml is using such names as keys, it adds a "?" by default
# which is not nice to read. This variable will define maximum width.

def write_compile_logs(output_directory, stdout, stderr):
    with open(("%s/build_log.out") % (output_directory), "w") as f:
        f.write(stdout)
    with open(("%s/build_log.err") % (output_directory), "w") as f:
        f.write(stderr)

def get_nvlink_info(error_str):
    gpu_compile_info = {}
    current_func = None
    global_info = 0
    function_name = 1
    function_stats = 2
    current_state = global_info
    for l in error_str.split("\n"):
        if "nvlink" in l:
            if current_state == global_info:
                gmem = re.findall('nvlink info\s+:\s+([0-9]+) bytes gmem',l)
                if len(gmem) != 0:
                    gpu_compile_info['global gmem bytes'] = int(gmem[0])
                    current_state = function_name
            elif current_state ==  function_name:
                func_name = re.findall('nvlink info\s+: Function properties for \'(.*?)\':',l)
                if len(func_name) != 0:
                    current_func = func_name[0]
                    current_state = function_stats
                    if current_func in gpu_compile_info:
                        print('Should never happen')
                        print('Same function name occurs more than once in object file...')
                        print('%s'%str(current_func))
                        print('Exit ...')
                        sys.exit(0)
                    gpu_compile_info[str(current_func)] = {}
            elif current_state == function_stats:
                current_state = function_name
                gpu_compile_info[current_func] = {}
                if 'registers' in l:
                    regs = re.findall('nvlink info\s+:\s+used ([0-9]+) registers,',l)
                    gpu_compile_info[current_func]['registers'] = int(regs[0])
                if 'stack' in l:
                    stack = re.findall('([0-9]+) stack,',l)
                    gpu_compile_info[current_func]["stack"] = int(stack[0])
                if 'bytes smem' in l:
                    smem = re.findall('([0-9]+) bytes smem,', l)
                    gpu_compile_info[current_func]["smem"] = int(smem[0])
                if 'bytes cmem' in l:
                    cmem = re.findall('([0-9]+) bytes cmem\[([0-9]+)\]',l)
                    for v in cmem:
                        key='cmem[%s]' % v[1]
                        gpu_compile_info[current_func][key] = int(v[0])
                if 'bytes lmem' in l:
                    lmem = re.findall('([0-9]+) bytes lmem', l)
                    gpu_compile_info[current_func]['lmem'] = int(lmem[0])
                current_func = None
    return gpu_compile_info

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
                results[program][mode] = {}
                results[program][mode]['exec_time'] = []
            elif len(results[program][mode]['exec_time']) < reps:
                start = len(results[program][mode]['exec_time'])
            else:
                print('FOUND', program, mode, 'runs', len(results[program][mode]['exec_time']) )
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

                results[program][mode]['exec_time'].append(runtime)

                with open('./results/results-%s.yaml'%(program), 'w') as f:
                    yaml.dump( results, f)

#def merge_nested_dict(d1, d2):
#    for k in d1:
#        if k in d2:
#            if isinstance(d1[k], dict):
#                merge_nested_dict(d1[k], d2[k])
#            else:
#                if d1[k]:
#                    d1[k] += d2[k]
#                else:
#                    d1[k] = d2[k]
#            d2.pop(k)
#    d1.update(d2)
            
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
        # Replace other filenames with in the repo with the full path.
        fdata = re.sub('File: ([\.])', 'File: ' + os.getcwd() + '/' + pathname  + r'/\1', fdata)

        data += fdata

    with open(reports_dir + mode + '.opt.yaml', 'w') as f:
        f.write( data )

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

def merge_omp_info( program, build_dir, mode ):
    # generate unified optimization report
    reports_dir = './reports/' + program + '/'
    os.makedirs( reports_dir, exist_ok=True )

    # merge reports
    filenames = Path(build_dir).rglob('*.omp.yaml')
    data = {}
    for filename in filenames:
        # Remove .opt.yaml extension
        with open(filename ,'r') as f:
            d = yaml.load( f, Loader=CLoader )
        fname = str(filename).split('.omp.yaml')[0]
        data[ fname ] = d

    with open(reports_dir + program + '.omp.yaml', 'w') as f:
        yaml.dump( data, f, default_flow_style=False )

def compile_and_install(config, program, repo_dir, mode):
    build_dir = repo_dir + '/' + config[program]['build_dir']
    bin_dir = './bin/' + program + '/' + mode + '/'
    exe = bin_dir + config[program]['bin']
    # File exists
    if os.path.isfile( exe ):
        print('file ' + exe + ' exists')
        return

    os.makedirs( bin_dir, exist_ok=True )

    #Create directory to store build logs 
    build_log_dir = 'build_logs/%s/%s/' % (program, mode)

    print('Making Build Log Directory...')
    os.makedirs( build_log_dir, exist_ok=True )

    print('Making Results Directory...')
    os.makedirs( './results', exist_ok=True)

    print('Clean...')
    subprocess.run( config[program]['clean'], cwd=build_dir, shell=True)
    print('===> Build...program %s mode %s\n%s' % (program, mode, config[program]['build'][mode]) )
    try:
        p = subprocess.run( config[program]['build'][mode], cwd=build_dir, shell=True, capture_output=True)
    except Exception as e:
        print('building %s mode %s failed'%(program, mode), e)
        write_compile_logs(build_log_dir, p.stdout.decode('utf-8'), p.stderr.decode('utf-8'))
        input('key...')
        sys.exit(1)

    print('Storing compilation outputs')
    write_compile_logs(build_log_dir, p.stdout.decode('utf-8'), p.stderr.decode('utf-8'))

    print('Getting compilation statistics from nvinfo')
    nv_info = get_nvlink_info(p.stderr.decode('utf-8'))

    print('Storing compilation statistis')
    results = { program: {} }
    try:
        with open('./results/results-%s.yaml'%(program), 'r') as f:
            results = yaml.load(f, Loader=CLoader)
    except FileNotFoundError as e:
        pass

    if (not mode in results[program]) or (not results[program][mode]):
        results[program][mode] = {}
        results[program][mode]['exec_time'] = []
        results[program][mode]['compile_stats'] = {}

    results[program][mode]['compile_stats'] = nv_info

    with open('./results/results-%s.yaml'%(program), 'w') as f:
        yaml.dump( results, f)

    print('Merge stats and reports...')
    merge_stats_reports( program, build_dir, mode )
    if mode == 'omp':
        print('Merge OpenMP info...')
        merge_omp_info( program, build_dir, mode )

    print('Copy...')
    for copy in config[program]['copy']:
        if os.path.isdir( build_dir + '/' + copy ):
            shutil.copytree( build_dir + '/' + copy, bin_dir + copy)
        else:
            shutil.copy( build_dir + '/' + copy, bin_dir)


def diff_reports( report_dir, builds, mode ):
    out_yaml = report_dir + '%s-%s-%s.opt.yaml'%( builds[0], builds[1], mode )
    out_html = report_dir + 'html-%s-%s-%s'%( builds[0], builds[1], mode )
    if mode == 'all':
        opt_diff = './opt-viewer/opt-diff.py '
    else:
        opt_diff = './opt-viewer/opt-diff.py --filter %s '%( mode )

    if not os.path.exists( out_yaml ):
        print('Creating diff remark YAML files...')
        p = subprocess.run( opt_diff  + '--output ' + out_yaml + ' %s/%s.opt.yaml %s/%s.opt.yaml'%\
                (report_dir, builds[0], report_dir, builds[1]), shell=True)
        if p.returncode == 0:
            print('Done generating YAML diff optimization report for builds %s|%s mode %s'%( builds[0], builds[1], mode ))
        else:
            print('Failed generating YAML diff optimization report for builds %s|%s mode %s'%( builds[0], builds[1], mode ))
    else:
        print('YAML diff optimization report for builds %s|%s mode %s exists'%( builds[0], builds[1], mode ))

    if not os.path.exists( out_html ):
        print('Creating HTML report output diff for %s %s...' % ( builds[0],
            builds[1]) )
        p = subprocess.run( './opt-viewer/opt-viewer.py --output-dir %s %s' %( out_html, out_yaml), shell=True)
        if p.returncode == 0:
            print('Done generating compilation report for builds %s|%s mode %s'%( builds[0], builds[1], mode ))
        else:
            print('Failed generating compilation report for builds %s|%s mode %s'%( builds[0], builds[1], mode ))
    else:
        print('HTML output for builds %s|%s mode %s exists'%( builds[0], builds[1], mode ))


def generate_remark_reports( config, program ):
    report_dir = './reports/' + program + '/'

    # Create reports for single build (no diff).
    for build in config[program]['build']:
        in_yaml = report_dir + '%s.opt.yaml'%( build )
        out_html = report_dir + 'html-%s'%( build )
        if not os.path.exists( out_html ):
            print('Creating HTML report output for build %s ...' % ( build ) )
            p = subprocess.run( './opt-viewer/opt-viewer.py --output-dir %s %s' %(
                out_html, in_yaml), shell=True)
            if p.returncode == 0:
                print('Done generating compilation reports!')
            else:
                print('Failed generating compilation reports (expects build was '\
                        'successful)')
        else:
            print('HTML output for build %s exists'%( build ))

    # Create repors for 2-combinations of build options.
    combos = itertools.combinations( config[program]['build'], 2 )
    for builds in combos:
        diff_reports( report_dir, builds, 'all' )
        diff_reports( report_dir, builds, 'analysis' )
        diff_reports( report_dir, builds, 'missed' )
        diff_reports( report_dir, builds, 'passed' )

def fetch(config, program):
    # directories
    repo_dir = './repos/'
    os.makedirs( repo_dir, exist_ok=True )

    # clean and fetch (if needed)
    subprocess.run( config[program]['fetch'], cwd=repo_dir, shell=True)

def build(config, program):
    fetch(config, program)
    repo_dir = './repos/'

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

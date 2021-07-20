#!/usr/bin/env python3
# 
# Based on LLVM tools opt-viewer under license
# SPDX-License-Identifier: "Apache-2.0 WITH LLVM-exception"
#
# Modified by: Giorgis Georgakoudis, georgakoudis1@llnl.gov
#

from __future__ import print_function

import argparse
import html
import codecs
import errno
import functools
from multiprocessing import cpu_count
import os.path
import re
import shutil
import sys

from pygments import highlight
from pygments.lexers.c_cpp import CppLexer
from pygments.formatters import HtmlFormatter

import optpmap
import optrecord

import yaml
from yaml import CLoader

desc = '''Generate HTML output to visualize optimization records from the YAML files
generated with -fsave-optimization-record and -fdiagnostics-show-hotness.

The tools requires PyYAML and Pygments Python packages.'''


# This allows passing the global context to the child processes.
class Context:
    def __init__(self, caller_loc = dict()):
       # Map function names to their source location for function where inlining happened
       self.caller_loc = caller_loc

context = Context()

def suppress(remark):
    if remark.Name == 'sil.Specialized':
        return remark.getArgDict()['Function'][0].startswith('\"Swift.')
    elif remark.Name == 'sil.Inlined':
        return remark.getArgDict()['Callee'][0].startswith(('\"Swift.', '\"specialized Swift.'))
    return False


def get_hotness_lines(output_dir, builds):
    perf_hotness = {}
    for build in builds:
        perf_hotness_path = os.path.join(output_dir, '..', "{}.lines_hotness.yaml".format(build))
        f = open(perf_hotness_path)
        try:
            hotness_dict = yaml.load(f, Loader=CLoader)
        except Exception as e:
            print(e)
        perf_hotness[build] = hotness_dict
        f.close()
    return perf_hotness


class SourceFileRenderer:
    def __init__(self, source_dir, output_dir, filename, no_highlight, builds=[]):
        self.filename = filename
        existing_filename = None
        #print('filename', filename) #ggout
        if os.path.exists(filename):
            existing_filename = filename
        else:
            fn = os.path.join(source_dir, filename)
            if os.path.exists(fn):
                existing_filename = fn

        self.no_highlight = no_highlight
        self.stream = codecs.open(os.path.join(output_dir, optrecord.html_file_name(filename)), 'w', encoding='utf-8')
        if existing_filename:
            self.source_stream = open(existing_filename)
        else:
            print('Find file %s %s failed!'%(filename, existing_filename))
            self.source_stream = None
            print('''
<html>
<h1>Unable to locate file {}</h1>
</html>
            '''.format(filename), file=self.stream)

        self.html_formatter = HtmlFormatter(encoding='utf-8')
        self.cpp_lexer = CppLexer(stripnl=False)
        self.builds = builds
        # We assume that we comparison is between each pair of builds
        self.perf_hotness = get_hotness_lines(output_dir, builds)

    def render_source_lines(self, stream, line_remarks):
        file_text = stream.read()

        if self.no_highlight:
            if sys.version_info.major >= 3:
                html_highlighted = file_text
            else:
                html_highlighted = file_text.decode('utf-8')
        else:
            html_highlighted = highlight(
            file_text,
                self.cpp_lexer,
                self.html_formatter)

            # Note that the API is different between Python 2 and 3.  On
            # Python 3, pygments.highlight() returns a bytes object, so we
            # have to decode.  On Python 2, the output is str but since we
            # support unicode characters and the output streams is unicode we
            # decode too.
            html_highlighted = html_highlighted.decode('utf-8')

            # Take off the header and footer, these must be
            #   reapplied line-wise, within the page structure
            html_highlighted = html_highlighted.replace('<div class="highlight"><pre>', '')
            html_highlighted = html_highlighted.replace('</pre></div>', '')

        for (linenum, html_line) in enumerate(html_highlighted.split('\n'), start=1):
            html_src_line = u'''
<tr>
<td><a name=\"L{linenum}\">{linenum}</a></td>
<td></td>'''.format(**locals())
            # add place holder for every hotness
            for _ in range(len(self.builds)):
                html_src_line += u'''
<td></td>'''
            html_src_line += u'''
<td><div class="highlight"><pre>{html_line}</pre></div></td>
</tr>'''.format(**locals())
            print(html_src_line, file=self.stream)


            for remark in line_remarks.get(linenum, []):
                if not suppress(remark):
                    self.render_inline_remarks(remark, html_line)

    def render_inline_remarks(self, r, line):
        inlining_context = r.DemangledFunctionName
        dl = context.caller_loc.get(r.Function)
        if dl:
            dl_dict = dict(list(dl))
            link = optrecord.make_link(dl_dict['File'], dl_dict['Line'] - 2)
            inlining_context = "<a href={link}>{r.DemangledFunctionName}</a>".format(**locals())

        # Column is the number of characters *including* tabs, keep those and
        # replace everything else with spaces.
        indent = line[:max(r.Column, 1) - 1]
        indent = re.sub('\S', ' ', indent)

        entery = u'''
<tr>
<td></td>'''
        for build in self.perf_hotness:
            file_name, line_num, column = r.DebugLocString.split(':')
            file_and_line = file_name + ':' + line_num
            entery_hotness = 0 if file_and_line not in self.perf_hotness[build] else self.perf_hotness[build][
                file_and_line]
            entery_hotness = "{:.3f}%".format(entery_hotness)
            entery += u'''
<td>{entery_hotness}</td>'''.format(**locals())
        entery += u'''
<td class=\"column-entry-{r.color}\">{r.PassWithDiffPrefix}</td>
<td><pre style="display:inline">{indent}</pre><span class=\"column-entry-yellow\"> {r.message}&nbsp;</span></td>
<td class=\"column-entry-yellow\">{inlining_context}</td>
</tr>'''.format(**locals())
        print(entery, file=self.stream)

    def render(self, line_remarks):
        if not self.source_stream:
            return
        header1 = u'''
<html>
<title>{}</title>
<meta charset="utf-8" />
<head>
<link rel='stylesheet' type='text/css' href='style.css'>
</head>
<body>
<div class="centered">
<table class="source">
<thead>
<tr>
<th>Line</td>'''.format(os.path.basename(self.filename))
        for build in self.perf_hotness:
            header1 += u'''
<th>{} Perf Hotness</td>'''.format(build)
        header1 += u'''
<th>Optimization</td>
<th>Source</td>
<th>Inline Context</td>
</tr>
</thead>
<tbody>'''
        print(header1, file=self.stream)
        self.render_source_lines(self.source_stream, line_remarks)

        print('''
</tbody>
</table>
</body>
</html>''', file=self.stream)


class IndexRenderer:
    def __init__(self, output_dir, should_display_hotness, max_hottest_remarks_on_index, builds=[]):
        self.stream = codecs.open(os.path.join(output_dir, 'index.html'), 'w', encoding='utf-8')
        self.should_display_hotness = should_display_hotness
        self.max_hottest_remarks_on_index = max_hottest_remarks_on_index

        self.builds = builds
        # We assume that we comparison is between each pair of builds
        self.perf_hotness = get_hotness_lines(output_dir, builds)

    def render_entry(self, r, odd):
        escaped_name = html.escape(r.DemangledFunctionName)
        # we assume that omp has +ve sign before
        # file_name,line_num,column=r.DebugLocString.split(':')
        # print(file_name,line_num,column)
        # file_and_line=file_name+':'+line_num
        # if perf_render_mode is None:
        #    perf_hotness=''
        # elif perf_render_mode == "omp" or (perf_render_mode == "all" and r.PassWithDiffPrefix[0] == "+"):
        #    perf_hotness = self.perf_hotness_omp
        entery = u'''
<tr>
<td class=\"column-entry-{odd}\"><a href={r.Link}>{r.DebugLocString}</a></td>'''.format(**locals())

        # add perf hotness for each build
        for build in self.perf_hotness:
            file_name, line_num, column = r.DebugLocString.split(':')
            file_and_line = file_name + ':' + line_num
            entery_hotness = 0 if file_and_line not in self.perf_hotness[build] else self.perf_hotness[build][
                file_and_line]
            entery_hotness = "{:.3f}%".format(entery_hotness)
            entery += u'''
<td class=\"column-entry-{odd}\">{entery_hotness}</td>'''.format(**locals())

        # continue entery
        entery += u'''
<td class=\"column-entry-{odd}\">{escaped_name}</td>
<td class=\"column-entry-{r.color}\">{r.PassWithDiffPrefix}</td>
</tr>'''.format(**locals())
        # print('entery in render entery:',entery)
        print(entery, file=self.stream)

    def render(self, all_remarks):
        header = u'''
<html>
<meta charset="utf-8" />
<head>
<link rel='stylesheet' type='text/css' href='style.css'>
</head>
<body>
<div class="centered">
<table>
<tr>
<td>Source Location</td>'''
        # print('header is now: ',header)
        for build in self.perf_hotness:
            header += u'''
<td>{} perf Hotness</td>'''.format(build)
            # print('header is now: ',header)
        header += u'''<td>Function</td>
<td>Pass</td>
</tr>'''
        # print('header in index rendered:',header)
        print(header, file=self.stream)

        max_entries = None
        if self.should_display_hotness:
            max_entries = self.max_hottest_remarks_on_index

        for i, remark in enumerate(all_remarks[:max_entries]):
            if not suppress(remark):
                self.render_entry(remark, i % 2)
        print('''
</table>
</body>
</html>''', file=self.stream)


def _render_file(source_dir, output_dir, ctx, no_highlight, builds, entry):
    global context
    context = ctx
    filename, remarks = entry
    SourceFileRenderer(source_dir, output_dir, filename, no_highlight, builds).render(remarks)


def map_remarks(all_remarks):
    # Set up a map between function names and their source location for
    # function where inlining happened
    for remark in optrecord.itervalues(all_remarks):
        if isinstance(remark, optrecord.Passed) and remark.Pass == "inline" and remark.Name == "Inlined":
            for arg in remark.Args:
                arg_dict = dict(list(arg))
                caller = arg_dict.get('Caller')
                if caller:
                    try:
                        context.caller_loc[caller] = arg_dict['DebugLoc']
                    except KeyError:
                        pass


def generate_report(all_remarks,
                    file_remarks,
                    source_dir,
                    output_dir,
                    no_highlight,
                    should_display_hotness,
                    max_hottest_remarks_on_index,
                    num_jobs,
                    should_print_progress,
                    builds=[]):
    try:
        os.makedirs(output_dir)
    except OSError as e:
        if e.errno == errno.EEXIST and os.path.isdir(output_dir):
            pass
        else:
            raise

    if should_print_progress:
        print('Rendering index page...')
    if should_display_hotness:
        sorted_remarks = sorted(optrecord.itervalues(all_remarks), key=lambda r: (r.Hotness, r.File, r.Line, r.Column, r.PassWithDiffPrefix, r.yaml_tag, r.Function), reverse=True)
    else:
        sorted_remarks = sorted(optrecord.itervalues(all_remarks), key=lambda r: (r.File, r.Line, r.Column, r.PassWithDiffPrefix, r.yaml_tag, r.Function))
    IndexRenderer(output_dir, should_display_hotness, max_hottest_remarks_on_index, builds).render(sorted_remarks)

    shutil.copy(os.path.join(os.path.dirname(os.path.realpath(__file__)),
            "style.css"), output_dir)

    _render_file_bound = functools.partial(_render_file, source_dir, output_dir, context, no_highlight, builds)
    if should_print_progress:
        print('Rendering HTML files...')
    optpmap.pmap(_render_file_bound,
                 file_remarks.items(),
                 num_jobs,
                 should_print_progress)


def main():
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument(
        'yaml_dirs_or_files',
        nargs='+',
        help='List of optimization record files or directories searched '
             'for optimization record files.')
    parser.add_argument(
        '--output-dir',
        '-o',
        default='html',
        help='Path to a directory where generated HTML files will be output. '
             'If the directory does not already exist, it will be created. '
             '"%(default)s" by default.')
    parser.add_argument(
        '--jobs',
        '-j',
        default=None,
        type=int,
        help='Max job count (defaults to %(default)s, the current CPU count)')
    parser.add_argument(
        '--source-dir',
        '-s',
        default='',
        help='set source directory')
    parser.add_argument(
        '--no-progress-indicator',
        '-n',
        action='store_true',
        default=False,
        help='Do not display any indicator of how many YAML files were read '
             'or rendered into HTML.')
    parser.add_argument(
        '--max-hottest-remarks-on-index',
        default=1000,
        type=int,
        help='Maximum number of the hottest remarks to appear on the index page')
    parser.add_argument(
        '--no-highlight',
        action='store_true',
        default=False,
        help='Do not use a syntax highlighter when rendering the source code')
    parser.add_argument(
        '--demangler',
        help='Set the demangler to be used (defaults to %s)' % optrecord.Remark.default_demangler)

    # Do not make this a global variable.  Values needed to be propagated through
    # to individual classes and functions to be portable with multiprocessing across
    # Windows and non-Windows.
    args = parser.parse_args()

    print_progress = not args.no_progress_indicator
    if args.demangler:
        optrecord.Remark.set_demangler(args.demangler)

    files = optrecord.find_opt_files(*args.yaml_dirs_or_files)
    if not files:
        parser.error("No *.opt.yaml files found")
        sys.exit(1)

    all_remarks, file_remarks, should_display_hotness = \
        optrecord.gather_results(files, args.jobs, print_progress)

    map_remarks(all_remarks)

    generate_report(all_remarks,
                    file_remarks,
                    args.source_dir,
                    args.output_dir,
                    args.no_highlight,
                    should_display_hotness,
                    args.max_hottest_remarks_on_index,
                    args.jobs,
                    print_progress)

if __name__ == '__main__':
    main()

import subprocess
from subprocess import PIPE
import os


# reads a perf report that is a product of the following command:
# perf report -b --sort symbol
# this report contains the symbols sorted by their % of usage
# it outputs a dict that has keys as symbols and vals as % of usage
def get_hot_symbols(report_path):
    symbols_usage = {}
    with open(report_path) as report_file:
        for line in report_file:
            if line[0] == '#':  # skip the header
                continue

            if line.strip() == '':  # skip empty lines
                continue
            # print(line)
            words = line.strip().split()
            percentage = words[0]
            symbol = ' '.join(words[3:])

            percentage = float(percentage[:-1])  # remove % and convert to float
            symbols_usage[symbol] = percentage

    return symbols_usage


# read perf annotate -P -l symbol and get hot lines in src file
# hot lines are lines that have more than 0.5%(0.005) of execution time of the function
# the function outputs a dict with key "srcfile:line" and value of percentage of time
def get_hotness_from_anno_file(anno_path, hotlines={}, symbol_percentage=100):
    skip_keywords = ['Sorted summary for file', '----------------------------']
    with open(anno_path) as anno_file:
        for line in anno_file:
            if line[0] == '#':  # skip the header
                continue

            if line.strip() == '':  # skip empty lines
                continue

            if 'Percent |	Source code & Disassembly of' in line:  # we only capture src code and terminate before disassembly code
                break

            # skip predefined lines
            skip_line = False
            for skip in skip_keywords:
                if skip in line:
                    skip_line = True
            # we cant use continue above because it will escape the inner loop
            if skip_line:
                continue

            # print(line)
            words = line.strip().split()
            percentage = float(words[0])
            srccode = ' '.join(words[1:])
            line_hotness = round(percentage * symbol_percentage / 100, 3)
            if srccode in hotlines:
                hotlines[srccode] += line_hotness
            else:
                hotlines[srccode] = line_hotness

    return hotlines


# @TODO add cwd as a , ALSO ADD relative and absolute percentages
# return the hotlines in the secfile of a symbol. Return only lines with usage time 0.5% or more
def get_symbol_hotness_in_srcfiles(symbol, symbol_percentage, hotlines={}, cwd=''):
    # create annotation file of the symbol
    annotation_file_name = "perf-annotate.tmp"
    exe = "perf annotate {} -P -l > {}".format(symbol, annotation_file_name)
    print("executing command: {}".format(exe))
    p = subprocess.run(exe, cwd=cwd, shell=True, stdout=PIPE, stderr=PIPE)
    out = str(p.stdout.decode('utf-8', errors='ignore'))
    err = str(p.stderr.decode('utf-8', errors='ignore'))
    print(out, '\n\n', err)
    annotation_file_name = os.path.join(cwd, annotation_file_name)
    hotlines = get_hotness_from_anno_file(annotation_file_name, hotlines=hotlines, symbol_percentage=symbol_percentage)
    return hotlines


# generate report from perf data and return the hot symbols with their percentages
def get_hot_symbols_from_perf_data(binfile, perf_data_file='perf.data', cwd=''):
    report_file_name = "perf-report.tmp"
    exe = 'perf report --no-child -d {} -i {} --percentage "relative"  > {}'.format(binfile, perf_data_file,
                                                                                    report_file_name)
    print("executing command: {}".format(exe))
    p = subprocess.run(exe, cwd=cwd, shell=True, stdout=PIPE, stderr=PIPE)
    out = str(p.stdout.decode('utf-8', errors='ignore'))
    err = str(p.stderr.decode('utf-8', errors='ignore'))
    print(out, '\n\n', err)
    report_file_name = os.path.join(cwd, report_file_name)
    hot_symbols = get_hot_symbols(report_file_name)
    return hot_symbols


def get_hot_lines_percentage(binfile, cwd):
    symbols = get_hot_symbols_from_perf_data(binfile, cwd=cwd)
    print(symbols)
    print('\n\n\n\n\n\n\n')
    hotlines = {}
    for symbol in symbols:
        # hotlines=get_hotness_from_anno_file('trial')
        # skip symbols that are not in the main app
        if '@' in symbol:
            continue
        symbol_percentage = symbols[symbol]
        hotlines = get_symbol_hotness_in_srcfiles(symbol, symbol_percentage, hotlines=hotlines, cwd=cwd)

    return hotlines


if __name__ == "__main__":
    '''hotlines=get_hot_lines_percentage('lulesh2.0')
    for key in hotlines:
        print("FILE PATH:{}\tPERCENTAGE:{}%".format(key,round(hotlines[key],3)))'''

#!/usr/bin/env python

import subprocess
import os
import sys

def setup_module(module):
    THIS_DIR = os.path.dirname(os.path.abspath(__file__))
    os.chdir(THIS_DIR)

def teardown_module(module):
    cmd = ["make clean"]
    cmdOutput = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)

def run_command(cmd):
    try:
        cmdOutput = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError as e:
        print(e.output)
        exit()

def test_1():
    # --- compile code ---
    cmd = ["../../faros make"]
    run_command(cmd)

    # --- run code ---
    cmd = ["./main"]
    run_command(cmd)

    assert os.path.isfile('./main.opt.yaml')
    assert os.path.isfile('./report/html-output/index.html')

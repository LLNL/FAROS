#!/usr/bin/env python

import subprocess
import os
import sys
import glob

def setup_module(module):
    THIS_DIR = os.path.dirname(os.path.abspath(__file__))
    os.chdir(THIS_DIR)

def teardown_module(module):
    cmd = ["rm -rf build"]
    cmdOutput = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)

def run_command(cmd):
    try:
        cmdOutput = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError as e:
        print(e.output)
        exit()

def test_1():
  # --- compile code ---
  cmd = ['mkdir -p build && cd build && CXX=clang++ CC=clang cmake ..']
  run_command(cmd)

  cmd = ['cd build && ../../../faros make -j']
  run_command(cmd)

  count = 0 # number of yaml files
  for root, dirs, files in os.walk("./"):
    for file in files:
      if file.endswith(".yaml"):
        count +=1

  assert count==3

if __name__ == '__main__':
  test_1()

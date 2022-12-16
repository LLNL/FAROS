#!/usr/bin/env python3

import subprocess
import sys
import os
from colors import *

FAROS_PATH = os.path.dirname(os.path.abspath(__file__)) + '/../'
sys.path.append(FAROS_PATH)
from libs.faros import faroslib as faros

INTERCEPT_LIB = os.path.dirname(os.path.abspath(__file__))+"/intercept.so"

def runBuildCommand(params):
  prGreen('*** FAROS ***')
  prGreen('Intercepting commands in: ' + ' '.join(params))
  params.insert(0, 'LD_PRELOAD='+INTERCEPT_LIB)
  env_path = os.getenv('PATH')
  params.insert(0, 'PATH='+FAROS_PATH+'interception'+':'+env_path)
  params.insert(0, 'FAROS_SAVEDPATH='+env_path)

  try:
    cmdOutput = subprocess.run(' '.join(params), shell=True, check=True)
  except Exception as e:
    print(e)
    raise RuntimeError('Error when running FAROS input')

  faros.merge_stats_reports('./report/', './', 'output')
  faros.generate_remark_reports('./report/', './', ['output'])

if __name__ == '__main__':
  params = sys.argv
  params.pop(0)
  runBuildCommand(params)

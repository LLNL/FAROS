#!/usr/bin/env python3

import subprocess
import sys
import os
import pathlib
from colors import *

FILE_PATH = str(pathlib.Path(__file__).parent.absolute())
#sys.path.append('../../..')
sys.path.append(FILE_PATH+'/../')
from libs.faros import faroslib as faros

INTERCEPT_LIB = os.path.dirname(os.path.abspath(__file__))+"/intercept.so"

def runBuildCommand(params):
  prGreen('*** FAROS ***')
  prGreen('Intercepting commands in: ' + ' '.join(params))
  params.insert(0,'LD_PRELOAD='+INTERCEPT_LIB)  

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

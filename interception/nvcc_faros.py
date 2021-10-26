#!/usr/bin/env python3

import os
import pathlib
import subprocess
import platform
import sys
from colors import prGreen, prCyan, prRed
from exceptions import CommandException, CompileException 

# --------------------------------------------------------------------------- #
# --- Classes --------------------------------------------------------------- #
# --------------------------------------------------------------------------- #

class Command:
  def __init__(self, cmd):
    self.name = 'nvcc'
    self.parameters = cmd[1:]

  def executeOriginalCommand(self):
    try:
      cmd = [self.name] + self.parameters
      subprocess.run(' '.join(cmd), shell=True, check=True)
    except subprocess.CalledProcessError as e:
      prRed(e)

if __name__ == '__main__':
  cmd = Command(sys.argv)
  cmd.executeOriginalCommand()

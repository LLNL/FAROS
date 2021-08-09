#!/usr/bin/env python3

import os
import pathlib
import subprocess
import platform
import sys
from colors import prGreen, prCyan, prRed
from exceptions import CommandException, CompileException 

# --------------------------------------------------------------------------- #
# --- Installation Paths ---------------------------------------------------- #
# --------------------------------------------------------------------------- #

# Main installation path
FAROS_PATH      = str(pathlib.Path(__file__).parent.absolute())
ADDED_FLAGS = '-fsave-optimization-record'

# --------------------------------------------------------------------------- #
# --- Classes --------------------------------------------------------------- #
# --------------------------------------------------------------------------- #

class Command:
  def __init__(self, cmd):
    if os.path.split(cmd[0])[1].split('-')[0].endswith('clang++'):
      self.name = 'clang++'
    else:
      self.name = 'clang'
    self.parameters = cmd[1:]

  def executeOriginalCommand(self):
    try:
      cmd = [self.name] + self.parameters
      subprocess.run(' '.join(cmd), shell=True, check=True)
    except subprocess.CalledProcessError as e:
      prRed(e)

  def getOriginalCommand(self):
    return ' '.join([self.name] + self.parameters[1:])

  # It it a compilation command?
  def isCompileCommand(self) -> bool:
    if ('-c' in self.parameters):
      return True
    return False

  # Is the command a link command?
  def isLinkCommand(self) -> bool:
    if ('-c' not in self.parameters and 
        '--compile' not in self.parameters and
        ('-o' in self.parameters or '--output-file' in self.parameters)):
      return True
    return False

  def runCommandWithFlags(self):
    new_cmd = [self.name] + ADDED_FLAGS.split() + self.parameters
    try:
      cmdOutput = subprocess.run(' '.join(new_cmd), shell=True, check=True)
    except Exception as e:
      prRed(e)
      raise CompileException(new_cmd) from e

if __name__ == '__main__':
  cmd = Command(sys.argv)

  # Link command
  if cmd.isLinkCommand():
    cmd.executeOriginalCommand()
  else:
    # Compilation command
    try:
      cmd.runCommandWithFlags()
    except Exception as e: # Fall back to original command
      prRed(e)     
      cmd.executeOriginalCommand()


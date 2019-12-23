#
# Copyright (c) 2015 Nutanix Inc. All rights reserved.
#
# Author: saurabh.wagh@nutanix.com
#
# This module provides common utility components that are used by other
# Nutanix Guest Agent Service modules.
#

import logging
import subprocess
import sys

def run_shell_command(argsList):
  """
  Runs a shell command in a separate process, pipes its output & errors to a
  variable & returns the output. This method raises an exception upon failure
  to run the command.
  """
  kws = dict(stdout=subprocess.PIPE,
             stderr=subprocess.PIPE,
             stdin=subprocess.PIPE)

  command = ""
  for arg in argsList:
    command = command + arg + " ";

  if (sys.version_info > (3, 0)):
    # Use this with Python 3 so subprocess output will be str, not bytes.
    kws['universal_newlines'] = True

  try:
    p = subprocess.Popen(argsList, **kws)
    (output, err) = p.communicate()

  except Exception as exc:
    raise exc

  if p.returncode != 0:
    raise Exception("%s failed, Status code:%s, Output:%r, Error:%r"
      % (command, p.returncode, output, err))

  return output

def exit_installer(status):
  logging.shutdown()
  sys.exit(status)

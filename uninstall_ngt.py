#!/usr/bin/env python
#
# Copyright (c) 2015 Nutanix Inc. All rights reserved.
#
# Author: saurabh.wagh@nutanix.com (Saurabh Wagh)
#
# This script is run to uninstall NGT Guest Agent.
#

import datetime
import logging
import os
import platform
import shutil
import subprocess
import sys

# Destination folders for NGT installer.
NGT_ROOT = "/usr/local/nutanix"
NGT_DAEMON_NAME = "ngt_guest_agent"
NGT_DST_DAEMON_PATH = "/etc/init.d/" + NGT_DAEMON_NAME

src_path = os.path.abspath(
  os.path.join(NGT_ROOT, "bin"))
sys.path.insert(0, src_path)

from installer_utils import *

def run_shell_command(argsList):
  """
  Runs a shell command in a separate process & exits upon failure.
  """
  command = ""
  for arg in argsList:
    command = command + arg + " "

  try:
    # Run the command and pipe its output to the variables.
    p = subprocess.Popen(argsList, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, err = p.communicate()

  except Exception as exc:
    raise exc

  if p.returncode != 0:
    raise Exception("%s failed, Status code:%s, Output:%r, Error:%r" % (
      command, p.returncode, output, err))

def confirm_uninstall():
  """
  Prompt the user to confirm the NGT Guest Agent uninstallation.
  """
  prompt = "This script will uninstall NGT Guest Agent. Do you want to proceed? (Y/[N]): "
  while True:
    if hasattr(__builtins__, 'raw_input'):
      ans = raw_input(prompt)
    else:
      ans = input(prompt)
    if not ans:
      # Enter is considered as default - No.
      return False
    if ans not in ['y', 'Y', 'n', 'N']:
      print('please enter Y or N.')
      continue
    if ans == 'y' or ans == 'Y':
      return True
    if ans == 'n' or ans == 'N':
      return False

def uninstall_ngt_daemon_redhat():
  """
  This function stops & removes the NGT Guest Agent daemon from Red Hat
  distributions.
  """
  # Only attempt uninstall if the daemon was installed.
  if not os.path.exists(NGT_DST_DAEMON_PATH):
    return

  logging.info("Stopping and removing Nutanix Guest Agent Service.")

  # Stop the daemon if currently running.
  try:
    run_shell_command([NGT_DST_DAEMON_PATH, "stop"])
  except:
    pass

  # Turn the autostart on boot to off.
  try:
    run_shell_command(["/sbin/chkconfig", NGT_DAEMON_NAME, "off"])
  except:
    pass

  # Remove the daemon from the chkconfig services list.
  try:
    run_shell_command(["/sbin/chkconfig", "--del", NGT_DAEMON_NAME])
  except:
    pass

  # Remove the daemon configuration from the init.d folder.
  os.remove(NGT_DST_DAEMON_PATH)

def uninstall_ngt_daemon_ubuntu():
  """
  This function stops & removes the NGT Guest Agent daemon in an Ubuntu
  distribution.
  """
  # Only attempt uninstall if the daemon was installed.
  if not os.path.exists(NGT_DST_DAEMON_PATH):
    return

  logging.info("Stopping and removing Nutanix Guest Agent Service.")

  # Stop the daemon if currently running.
  try:
    run_shell_command([NGT_DST_DAEMON_PATH, "stop"])
  except:
    pass

  # Turn the autostart on boot to off.
  try:
    run_shell_command(["update-rc.d", "-f", NGT_DAEMON_NAME, "remove"])
  except:
    pass

  # Remove the daemon configuration from the init.d folder.
  os.remove(NGT_DST_DAEMON_PATH)

if __name__ == "__main__":
  logfilename = "/tmp/ngt_uninstall_log_" +\
    datetime.datetime.now().strftime("%Y%m%d%H%M%S") + ".txt"
  logging.basicConfig(filename=logfilename, level=logging.NOTSET, format=\
    '[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')
  logger = logging.getLogger()
  consoleHandler = logging.StreamHandler()
  logger.addHandler(consoleHandler)

  # Only allow execution of this script as root user.
  if os.geteuid() != 0:
    logging.error("Script must be run as root.")
    exit_installer(1)

  if not confirm_uninstall():
    logging.info("Uninstalling Nutanix Guest Tools.")
    exit_installer(1)

  logging.info("Uninstalling Nutanix Guest Tools.")

# Uninstall the NGT Guest Agent daemon if installed.
  try:
    distribution = platform.linux_distribution()[0].lower()

    if ("centos" in distribution or
        "red hat" in distribution or
        "oracle linux server" in distribution or
        "suse" in distribution):
      uninstall_ngt_daemon_redhat()

    elif "ubuntu" in distribution:
      uninstall_ngt_daemon_ubuntu()

    else:
      logging.info("Unsupported distribution. Skipping Nutanix Guest " \
        "Tools uninstall.")

  except:
    # Ignore exceptions during cleanup as we call cleanup in scenarios such
    # as first install as well - just in case some partial state is left behind.
    pass

  # Remove NGT Guest Agent folder
  shutil.rmtree(NGT_ROOT, ignore_errors=True)
  logging.info("Successfully uninstalled Nutanix Guest Tools.")

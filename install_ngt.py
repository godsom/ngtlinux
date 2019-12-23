#!/usr/bin/env python
#
# Copyright (c) 2015 Nutanix Inc. All rights reserved.
#
# Author: saurabh.wagh@nutanix.com (Saurabh Wagh)
#
# This script is run to install NGT Guest Agent & set up the VM for mobility.
# Here are the key tasks it performs:
#  - Load VirtIO / mptsas drivers in the initramfs file to enable VM mobility.
#  - Copy the NGT Guest Agent & required config files to the desired location.
#  - Set up NGT Guest Agent as an init.d daemon.
#
# Notes on script behavior:
# Each time the script is run, it removes any existing NGT Guest Agent
# installation and reinstalls it. This behavior enables the user to update
# the NGT Guest Agent & also ensures predictable behavior if an earlier
# execution of the script unexpectedly terminated after partial execution.
# If for some reason, the execution fails, the script does a cleanup of
# any partial state.
#
# Usage:
# "python install_ngt.py" - Install NGT Guest Agent & mobility drivers.
#

import datetime
import logging
import os
import sys
import time

NGT_START_WAIT_INTERVAL = 3
NGT_START_RETRY_COUNT = 5
ORION_CONFIG_FILE = "/usr/local/nutanix/config/containers.config"

src_path = os.path.abspath(
  os.path.join(os.path.dirname(__file__), "src"))
sys.path.insert(0, src_path)

from installer_factory import *

def install_ngt():
  """
  Install the NGT Guest Agent and mobility drivers. Cleanup any stale state
  left behind from a previous install.
  """

  logfilename = "/tmp/ngt_install_log_" +\
    datetime.datetime.now().strftime("%Y%m%d%H%M%S") + ".txt"
  logging.basicConfig(filename=logfilename, level=logging.NOTSET, format=\
    '[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')
  logger = logging.getLogger()
  consoleHandler = logging.StreamHandler()
  logger.addHandler(consoleHandler)

  # Fetch the appropriate installer for the current distribution.
  linux_installer = get_linux_installer()

  # Check if NGT is already installed.
  is_ngt_installed = linux_installer.is_ngt_installed()

  # Check if NGT installation is required.
  if is_ngt_installed:
    is_installation_required = linux_installer.check_installation_required()
    if not is_installation_required:
      exit_installer(1)
      return

  # Clean up a previous installation or any partial state on each run.
  linux_installer.do_cleanup()

  # Check if the conditions required for execution are met. No need to
  # cleanup if validation fails since no changes have been made yet.
  if not linux_installer.do_validate():
    exit_installer(1)
    return
  try:
    # Set up the folder structure required for the NGT Guest Agent setup.
    linux_installer.do_pre_process()

    # Install the NGT Guest Agent & Set up the VM Mobility drivers.
    linux_installer.do_setup()

    # Clean up any temporary state & start the NGT Guest Agent daemon.
    linux_installer.do_post_process()

    retry_count = NGT_START_RETRY_COUNT
    nga_service_running = False
    for _ in range(retry_count):
      logging.info("Waiting for Nutanix Guest Agent Service to start...")
      time.sleep(NGT_START_WAIT_INTERVAL)
      if linux_installer.is_ngt_running():
        nga_service_running = True
        break

    if nga_service_running:
      logging.info("Nutanix Guest Agent Service successfully started in " +
        "the background.")
    else:
      logging.error("Nutanix Guest Agent Service failed to start.")
      logging.error("Check /usr/local/nutanix/logs/guest_agent_stdout.log "
        "for info.")

  except:
    # If we fail the installation, cleanup any partial state and exit.
    logging.error("Failed to install Nutanix Guest Tools.")
    linux_installer.do_cleanup()
    exit_installer(1)
    return

if __name__ == "__main__":

  # Check if python2.6 or python2.7 is installed or not.
  version = sys.version_info
  if version[0] != 2 or version[1] < 6:
    logging.error("One of python version 2.6 or 2.7 is needed for installing "
      "Nutanix Guest Tools")
    exit_installer(1)

  if os.path.isfile(ORION_CONFIG_FILE):
    lines = [line.rstrip() for line in open(ORION_CONFIG_FILE)]
    for line in lines:
      if line == "container_host=True":
        logging.error("This is a Nutanix Container Host. "
                      "NGT cannot be installed on this host.")
        exit_installer(1)

  install_ngt()

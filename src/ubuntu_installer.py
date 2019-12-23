#!/usr/bin/env python
#
# Copyright (c) 2015 Nutanix Inc. All rights reserved.
#
# Author: saurabh.wagh@nutanix.com (Saurabh Wagh)
#
# This method provides an implementation of the Linux installer for Ubuntu.
#

import os
import platform

from distutils.version import LooseVersion

from installer_utils import *
from base_installer import *

class UbuntuInstaller(LinuxInstaller):
  """
  Implementation of the Linux installer for Ubuntu
  """
  UBUNTU_MIN_VERSION = "14.04"

  def do_validate(self):
    """
    This function ensures that pre-conditions required for a successful execution
    of this script on Ubuntu are satisfied.
    """
    if not super(UbuntuInstaller, self).do_validate():
      return False

    version = platform.linux_distribution()[1]

    if LooseVersion(version) < LooseVersion(self.UBUNTU_MIN_VERSION):
      logging.error("Ubuntu Version %s is not supported. MinVersion %s."\
        %(version, self.UBUNTU_MIN_VERSION))
      return False

    return True

  def install_ngt_daemon(self):
    """
    This function installs the NGT Guest Agent as an init.d daemon.
    """
    super(UbuntuInstaller, self).install_ngt_daemon()

    # Add the daemon as a chkconfig service.
    try:
      run_shell_command(["update-rc.d",
                         self.NGT_DAEMON_NAME,
                         "start", "90", "2", "3", "4", "5", ".",
                         "stop", "10", "0", "1", "6", "."])
    except:
      logging.error("Failed to add Nutanix Guest Agent Service to the " \
        "service configuration.")
      raise

    logging.info("Successfully installed Nutanix Guest Agent Service.")

  def uninstall_ngt_daemon(self):
    """
    This function stops the NGT Guest Agent daemon and removes it.
    """
    # Only attempt uninstall if the daemon was installed.
    if not os.path.exists(self.NGT_DST_DAEMON_PATH):
      return

    # Stop the daemon if currently running.
    try:
      run_shell_command([self.NGT_DST_DAEMON_PATH, "stop"])
    except:
      pass

    # Turn the autostart on boot to off.
    try:
      run_shell_command(["update-rc.d", "-f", self.NGT_DAEMON_NAME, "remove"])
    except:
      pass

    # Remove the daemon configuration from the init.d folder.
    os.remove(self.NGT_DST_DAEMON_PATH)

  def setup_mobility_drivers(self):
    """
    This function loads the VirtIO and mptsas drivers into the initramfs file
    for the current OS kernel.
    """
    # Ubuntu has the drivers already loaded in the kernel ram file.
    # We do not need to take explicit steps to install the drivers.
    pass

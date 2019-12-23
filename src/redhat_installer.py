#!/usr/bin/env python
#
# Copyright (c) 2015 Nutanix Inc. All rights reserved.
#
# Author: saurabh.wagh@nutanix.com (Saurabh Wagh)
#
# This method provides an implementation of the Linux installer for the Red Hat
# distributions.
#

import os
import platform
import re
import shutil
import tempfile

from distutils.version import LooseVersion

from installer_utils import *
from base_installer import *

class RedhatInstaller(LinuxInstaller):
  """
  Implementation of the Linux installer for Red Hat distributions
  """
  NGT_DRACUT_PATH = "/etc/dracut.conf"
  REDHAT_MIN_VERSION = "6.4"

  def do_validate(self):
    """
    This function ensures that pre-conditions required for a successful execution
    of this script on Red Hat distributions are satisfied.
    """
    if not super(RedhatInstaller, self).do_validate():
      return False

    version = platform.linux_distribution()[1]

    if LooseVersion(version) < LooseVersion(self.REDHAT_MIN_VERSION):
      logging.error("Version %s is not supported. MinVersion %s." \
        %(version, self.REDHAT_MIN_VERSION))
      return False

    return True

  def install_ngt_daemon(self):
    """
    This function installs the NGT Guest Agent as an init.d daemon.
    """
    super(RedhatInstaller, self).install_ngt_daemon()

    # Add the daemon as a chkconfig service.
    try:
      run_shell_command(["/sbin/chkconfig", "--add", self.NGT_DAEMON_NAME])
    except:
      logging.error("Failed to add Nutanix Guest Agent Service to the " \
        "service configuration.")
      raise

    # Set daemon to autostart on boot.
    try:
      run_shell_command(["/sbin/chkconfig", self.NGT_DAEMON_NAME, "on"])
    except:
      logging.error("Failed to set Nutanix Guest Agent Service property " \
        "autostart on boot.")
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
      run_shell_command(["/sbin/chkconfig", self.NGT_DAEMON_NAME, "off"])
    except:
      pass

    # Remove the daemon from the chkconfig services list.
    try:
      run_shell_command(["/sbin/chkconfig", "--del", self.NGT_DAEMON_NAME])
    except:
      pass

    # Remove the daemon configuration from the init.d folder.
    os.remove(self.NGT_DST_DAEMON_PATH)

  def is_kernel_module_present(self, module_name):
    """
    Check if specified kernel module is present in the system. 
    """
    try:
      run_shell_command(["/sbin/modinfo", module_name])
    except:
      logging.warning("Kernel module %s does not exist." %module_name)
      return False
    return True

  def update_dracut_conf(self):
    """
    This function updates the dracut.conf file and adds the virtio_scsi and
    the virtio_net drivers to it. This is called prior to running the dracut
    tool to generate the initramfs file. Dracut will pull in all necessary
    dependencies that are needed by the specified drivers.
    """
    # Create a temporary file to store the modified dracut.conf
    temp_fd, temp_path = tempfile.mkstemp()
    temp_file = open(temp_path, 'w')

    # virtio_scsi, virtio_net, virtio_blk, virtio_pci are required for AHV,
    # vmw_pvscsi, vmxnet3, e1000, mptsas, mptspi are required for ESX.
    drivers = ["virtio_scsi", "virtio_net", "virtio_blk", "virtio_pci",
               "vmw_pvscsi", "vmxnet3", "e1000", "mptsas", "mptspi"]
    with open(self.NGT_DRACUT_PATH, 'r') as file:
      data = file.readlines()
      for line in data:
        match = re.match(r'#?add_drivers\+\="(.*)"', line)
        if match:
          modified = False
          current_drivers = match.group(1)
          # Add the drivers needed for ESX and AHV if not already present.
          for driver in drivers:
            if (not driver in current_drivers) and \
               self.is_kernel_module_present(driver):
              current_drivers = current_drivers + " " + driver
              modified = True

          # If new drivers are needed, update the conf with the new drivers.
          if modified:
            updated_line = 'add_drivers+=\"%s \"' % (current_drivers.strip())
            temp_file.write(updated_line)
            temp_file.write('\n')
          else:
            temp_file.write(line)
        else:
          temp_file.write(line)

    temp_file.close()
    os.close(temp_fd)

    # Overwrite the existing dracut.conf file with the new one.
    shutil.copy2(temp_path, self.NGT_DRACUT_PATH)
    os.remove(temp_path)

  def setup_mobility_drivers(self):
    """
    This function loads the VirtIO and mptsas drivers into the initramfs file
    for the current OS kernel.
    """
    logging.info("Setting up Nutanix Guest Tools - VM mobility drivers.")

    self.update_dracut_conf()

    # Run dracut to update the initramfs file based on the updated config.
    try:
      run_shell_command(["dracut", "-f"])
    except:
      logging.error("Failed to setup Nutanix Guest Tools - VM mobility " \
        "drivers.")
      raise

    logging.info("Successfully set up Nutanix Guest Tools - VM mobility " \
      "drivers.")

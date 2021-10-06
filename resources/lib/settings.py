# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: © 2016 Rob Webset
# SPDX-FileCopyrightText:  2020-2021 Peter J. Mello <admin@petermello.net>
#
# SPDX-License-Identifier: MPL-2.0
"""Read and store add-on configuration under userdata."""

from __future__ import absolute_import
import os
import xbmc
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon(id="service.addonsync")
ADDON_ID = ADDON.getAddonInfo("id")


def log(txt, loglevel=xbmc.LOGDEBUG):
    """Control logging AddonSync messages to the Kodi system log."""
    if (ADDON.getSetting("logEnabled") == "true") or (
            loglevel != xbmc.LOGDEBUG):
        if isinstance(txt, str):
            txt = txt.decode("utf-8")
        message = f"{ADDON_ID}: {txt}"
        xbmc.log(msg=message.encode("utf-8"), level=loglevel)


def dir_exists(dirpath):
    """Check if a directory exists."""
    # There is an issue with password protected smb shares, in that they seem
    # to always return false for a directory exists call, so if we have a smb
    # with a password and user name, then we return true
    if "@" in dirpath:
        return True

    dir_path = dirpath
    # The xbmcvfs exists interface require that directories end in a slash
    # It used to be OK not to have the slash in Gotham, but it is now required
    if (not dir_path.endswith("/")) and (
            not dir_path.endswith("\\")):
        dir_sep = "/"
        if "\\" in dir_path:
            dir_sep = "\\"
        dir_path = "%s%s" % (dir_path, dir_sep)
    return xbmcvfs.exists(dir_path)


def os_path_join(folder, file):
    """Construct canonical filepaths from directory tree file lists."""
    # Check if it ends in a slash
    if folder.endswith("/") or folder.endswith("\\"):
        # Remove the slash character
        folder = folder[:-1]

    return os.path.join(folder, file)


def nested_copy(root_src_dir, root_target_dir):
    """Perform a nested (recursive) copy of one directory tree to another."""
    log("nested_copy: Copy %s to %s" % (root_src_dir, root_target_dir))

    # Make sure the target directory exists
    xbmcvfs.mkdirs(root_target_dir)

    dirs, files = xbmcvfs.listdir(root_src_dir)

    for file in files:
        try:
            file = file.decode("utf-8")
        except (SyntaxError, UnicodeDecodeError):
            pass
        src_file = "%s%s" % (root_src_dir, file)
        target_file = "%s%s" % (root_target_dir, file)
        log("nested_copy: Copy file %s to %s" % (src_file, target_file))
        xbmcvfs.copy(src_file, target_file)

    for adir in dirs:
        try:
            adir = adir.decode("utf-8")
        except (SyntaxError, UnicodeDecodeError):
            pass
        src_dir = "%s%s/" % (root_src_dir, adir)
        target_dir = "%s%s/" % (root_target_dir, adir)
        log("nested_copy: Copy directory %s to %s" % (src_dir, target_dir))
        nested_copy(src_dir, target_dir)


def nested_delete(root_dir):
    """Remove a directory recursively if it is no longer needed."""
    # If the file already exists, delete it
    if dir_exists(root_dir):
        # Remove the png files in the directory first
        dirs, files = xbmcvfs.listdir(root_dir)
        # Remove nested directories first
        for adir in dirs:
            nested_delete(os_path_join(root_dir, adir))
        # If there are any nested files remove them
        for a_file in files:
            xbmcvfs.delete(os_path_join(root_dir, a_file))
        # Now remove the actual directory
        xbmcvfs.rmdir(root_dir)
    else:
        log("nested_delete: Directory %s does not exist" % root_dir)


##############################
# Stores Various Settings
##############################
class Settings:
    """Map names and store config variables from settings.xml to Python."""

    FILTER_ALL = 0
    FILTER_INCLUDE = 1
    FILTER_EXCLUDE = 2

    @staticmethod
    def is_first_use():
        """Remember if AddonSync has created the central store already."""
        return ADDON.getSetting("isFirstUse") == "true"

    @staticmethod
    def set_first_use(use_value="false"):
        """Set to true on installation to trigger central store creation."""
        ADDON.setSetting("isFirstUse", use_value)

    @staticmethod
    def get_central_store_loc():
        """Read filepath of the central store."""
        central_store_loc = ADDON.getSetting("centralStoreLocation")
        # Make sure the location ends with a slash
        if ("/" in central_store_loc) and (
                not central_store_loc.endswith("/")):
            central_store_loc = "%s/" % central_store_loc
        elif ("\\" in central_store_loc) and (
                not central_store_loc.endswith("\\")):
            central_store_loc = "%s\\" % central_store_loc
        return central_store_loc

    @staticmethod
    def is_master():
        """Check whether we are running as a Master or Slave instance."""
        # Safer to check for slave type, as master will not overwrite
        if int(ADDON.getSetting("installationType")) == 1:
            return False
        return True

    @staticmethod
    def is_run_at_launch():
        """Check for 'service' config (run whenever Kodi is launched)."""
        return ADDON.getSetting('runOnStartup') == "true"

    @staticmethod
    def get_sync_interval():
        """Get the scheduled interval at which to synchronize add-ons."""
        # If we do not want to run on startup, then the interval is
        # just the once
        if not Settings.is_run_at_launch():
            return 0
        return int(float(ADDON.getSetting("checkInterval")))

    @staticmethod
    def is_restart_synced_services():
        """Check if we need to restart service add-ons following syncs."""
        return ADDON.getSetting("restartUpdatedServiceAddons") == "true"

    @staticmethod
    def is_force_version_match():
        """Check if we only sync when add-ons have matching versions."""
        return ADDON.getSetting("forceVersionMatch") == "true"

    @staticmethod
    def get_filter_type():
        """Check if filtering is enabled and if it's inclusive or exclusive."""
        index = int(ADDON.getSetting("filterType"))
        filter_type = Settings.FILTER_ALL
        if index == 1:
            filter_type = Settings.FILTER_INCLUDE
        elif index == 2:
            filter_type = Settings.FILTER_EXCLUDE

        return filter_type

    @staticmethod
    def get_excluded_addons():
        """Return id strings of any add-ons to exclude from syncs."""
        return ADDON.getSetting("excludedAddons")

    @staticmethod
    def get_included_addons():
        """Get id strings of the only add-ons we are supposed to sync."""
        return ADDON.getSetting("includedAddons")

    @staticmethod
    def set_excluded_addons(value=""):
        """Write the id strings of excluded add-ons to AddonSync config."""
        ADDON.setSetting("excludedAddons", value)

    @staticmethod
    def set_included_addons(value=""):
        """Write the id strings of the add-ons we restrict syncing to."""
        ADDON.setSetting("includedAddons", value)

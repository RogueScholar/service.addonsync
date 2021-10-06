# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: © 2016 Rob Webset
# SPDX-FileCopyrightText:  2020-2021 Peter J. Mello <admin@petermello.net>
#
# SPDX-License-Identifier: MPL-2.0

"""This module generates all the hash values for the installed addons."""

import hashlib
import json
import os
import re
import traceback
import xml.etree.ElementTree as ElemenTree  # nosec
from defusedxml import defuse_stdlib

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from .settings import log, nested_copy, nested_delete, os_path_join, Settings

ID = "service.addonsync"
ADDON = xbmcaddon.Addon(ID)
ICON = ADDON.getAddonInfo("icon")


class Hash:
    """Class that will generate hash values for each plugin data section."""

    HASH_FUNCS = {
        "md5": hashlib.md5,
        "sha1": hashlib.sha1,
        "sha256": hashlib.sha256,
        "sha512": hashlib.sha512,
    }

    def get_dir_hash(self, profile_name, hashfunc="md5", excluded_files=None):
        """Generate a hash for a given directory."""
        # Make sure a supported format is requested
        hash_func = Hash.HASH_FUNCS.get(hashfunc)
        if not hash_func:
            log(f"Hash: Invalid hash type requested {hashfunc}")
            return None

        if not excluded_files:
            excluded_files = []

        dirname = xbmcvfs.translatePath(profile_name)

        # Make sure the location is a directory
        if not xbmcvfs.exists(dirname):
            log(f"Hash: {dirname} is not a directory")
            return None

        hashvalues = []
        for root, _, files in os.walk(dirname, topdown=True):
            if not re.search(r"/\.", root):
                hashvalues.extend([
                    self._filehash(os.path.join(root, f), hash_func)
                    for f in files if not f.startswith(".")
                    and not re.search(r"/\.", f) and f not in excluded_files
                ])
        return self._reduce_hash(hashvalues, hash_func)

    # Generates a hash value for a given file
    def _filehash(self, filepath, hashfunc):
        hasher = hashfunc()
        blocksize = 64 * 1024
        try:
            with open(filepath, "rb") as file_pth:
                while True:
                    data = file_pth.read(blocksize)
                    if not data:
                        break
                    hasher.update(data)
        except (OSError, ValueError):
            log(f"Hash: Failed to create hash for {filepath}", xbmc.LOGERROR)
        return hasher.hexdigest()

    # Converts a list of hash values into a single value
    def _reduce_hash(self, hashlist, hashfunc):
        hasher = hashfunc()
        for hashvalue in sorted(hashlist):
            if hashvalue not in [None, ""]:
                hasher.update(hashvalue.encode("utf-8"))
        return hasher.hexdigest()


class AddonData:
    """Class that provides utility methods to lookup Addon information."""

    def get_addons_to_sync(self):
        """Get the details of all the addons required for a sync."""
        # Start by getting all the addons installed
        active_addons = self._get_installed_addons()

        # Now check for any filter that is applied
        active_addons = self._filter_addons(active_addons)

        addon_details = {}

        # Now loop each of the addons to get the details required
        for addon_name in list(active_addons.keys()):
            settings_dir = self._get_addon_settings_directory(addon_name)

            # If there are no settings available then we have it installed
            # but no configuration available
            if settings_dir in [None, ""]:
                addon_details[addon_name] = None
            else:
                addon_detail = {}
                addon_detail["dir"] = settings_dir
                # Generate the hash
                hashsum = Hash()
                hash_value = hashsum.get_dir_hash(settings_dir)
                del hashsum

                log(f"AddonData: addon: {addon_name} "
                    f"path: {settings_dir} "
                    f"hash: {hash_value}")
                addon_detail["hash"] = hash_value
                addon_details[addon_name] = addon_detail
                addon_detail["version"] = active_addons[addon_name]
        return addon_details

    # Perform and filter the user has set up
    def _filter_addons(self, installed_addons):
        filtered_addons = {}
        # Find out what the setting for filtering is
        filter_type = Settings.get_filter_type()

        if filter_type == Settings.FILTER_INCLUDE:
            # Add the included addons as they are just the id's split by spaces
            include_value = Settings.get_included_addons()
            log(f"AddonData: Include filter is {include_value}")
            if include_value not in [None, ""]:
                for incval in include_value.split(" "):
                    # Make sure the addon is still installed
                    if incval in list(installed_addons.keys()):
                        filtered_addons[incval] = installed_addons[incval]
        elif filter_type == Settings.FILTER_EXCLUDE:
            exclude_value = Settings.get_excluded_addons()
            log(f"AddonData: Exclude filter is {exclude_value}")
            if exclude_value not in [None, ""]:
                excluded_addons = exclude_value.split(" ")
                for addon_name in list(installed_addons.keys()):
                    if addon_name not in excluded_addons:
                        filtered_addons[addon_name] = installed_addons[
                            addon_name
                        ]
                    else:
                        log(f"AddonData: Skipping excluded addon {addon_name}")
            else:
                filtered_addons = installed_addons
        else:
            log("AddonData: Filter includes all addons")
            filtered_addons = installed_addons

        return filtered_addons

    # Method to get all the addons that are installed and not marked as broken
    def _get_installed_addons(self):
        # Make the call to find out all the addons that are installed
        json_query = xbmc.executeJSONRPC(
            '{ "jsonrpc": "2.0", "method": "Addons.GetAddons", "params": {"enabled": true, "properties": [ "broken", "version" ] }, "id": 1 }'
        )
        json_response = json.loads(json_query)

        addons = {}

        if ("result" in json_response) and ("addons"
                                            in json_response["result"]):
            # Check each of the screensavers that are installed on the system
            for addon_item in json_response["result"]["addons"]:
                addon_name = addon_item["addonid"]
                # Need to skip the two built-in screensavers as they can not be
                # triggered and are a bit dull, thus should not be in the mix
                if addon_name in [
                    "screensaver.xbmc.builtin.black",
                    "screensaver.xbmc.builtin.dim",
                    "service.xbmc.versioncheck",
                ]:
                    log(f"AddonData: Skipping built-in addons: {addon_name}")
                    continue

                if addon_name.startswith("metadata"):
                    log(f"AddonData: Skipping metadata addon: {addon_name}")
                    continue
                if addon_name.startswith("resource.language"):
                    log(f"AddonData: Skipping l10n addon: {addon_name}")
                    continue
                if addon_name.startswith("repository"):
                    log(f"AddonData: Skipping repository addon: {addon_name}")
                    continue
                if addon_name.startswith("skin"):
                    log(f"AddonData: Skipping skin addon: {addon_name}")
                    continue

                # Skip ourselves so we don't update a slave with a master
                if addon_name in [ID]:
                    log(f"AddonData: Detected ourself: {addon_name}")
                    continue

                # Need to ensure we skip any addons that are flagged as broken
                if addon_item["broken"]:
                    log(f"AddonData: Skipping broken addon: {addon_name}")
                    continue

                # Now we are left with only the working addons
                log(f"AddonData: Detected Addon: {addon_name}")
                addons[addon_name] = addon_item["version"]

        return addons

    def _get_addon_settings_directory(self, addon_name):
        log(f"AddonData: Get addon settings directory for {addon_name}")

        addon_info = xbmcaddon.Addon(addon_name)
        if addon_info in [None, ""]:
            log(f"AddonData: Failed to get addon data for {addon_name}")
            return None

        addon_profile = addon_info.getAddonInfo("profile")
        if addon_profile in [None, ""]:
            log(f"AddonData: Failed to get addon profile for {addon_name}")
            return None

        config_path = xbmcvfs.translatePath(addon_profile)

        # Check if the directory exists
        if xbmcvfs.exists(config_path):
            log(f"AddonData: addon: {addon_name} path: {config_path}")
            config_path = addon_profile
        else:
            # If the path does not exist then we will not need to copy this one
            log(f"AddonData: addon: {addon_name} "
                f"path: {config_path} doesn't exist")
            config_path = None

        return config_path

    def _generate_hash_record(self, addon_details, central_store_location):
        log(f"AddonData: Generating hash record {central_store_location}")

        hash_file = os_path_join(central_store_location, "hashdata.xml")

        defuse_stdlib()

        # <addonsync>
        #  <addon name='service.addonsync' version ='1.0.0'>hash_value</addon>
        # </addonsync>
        try:
            root = ElemenTree.Element("addonsync")
            for addon_name in list(addon_details.keys()):
                addon_detail = addon_details[addon_name]
                # If there are no settings, there is nothing to copy
                if addon_detail in [None, ""]:
                    continue
                hashsum = addon_detail["hash"]
                # Miss items that have no hash
                if hashsum in [None, ""]:
                    continue

                addon_elem = ElemenTree.SubElement(root, "addon")
                addon_elem.attrib["name"] = addon_name
                addon_elem.attrib["version"] = addon_detail["version"]
                addon_elem.text = addon_detail["hash"]

            # Save the XML file to disk
            record_file = xbmcvfs.File(hash_file, "w")
            try:
                file_content = ElemenTree.tostring(root, encoding="UTF-8")
                record_file.write(file_content)
            except (ElemenTree.ParseError, OSError, ValueError):
                log(
                    f"AddonData: Failed to write file: {record_file}",
                    xbmc.LOGERROR,
                )
                log(f"AddonData: {traceback.format_exc()}", xbmc.LOGERROR)
            record_file.close()

        except (ElemenTree.ParseError, ValueError):
            log(
                f"AddonData: Failed to create {traceback.format_exc()}",
                xbmc.LOGERROR,
            )

    # Reads an existing XML file with Hash values in it
    def _load_hash_record(self, record_location):
        log(f"AddonData: Loading hash record {record_location}")

        hash_file = os_path_join(record_location, "hashdata.xml")

        addon_list = {}
        if not xbmcvfs.exists(hash_file):
            log(f"AddonData: Unable to load non-existent file {hash_file}")
            return addon_list

        defuse_stdlib()

        try:
            record_file = xbmcvfs.File(hash_file, "r")
            record_file_str = record_file.read()
            record_file.close()

            hash_record = ElemenTree.ElementTree(
                ElemenTree.fromstring(record_file_str)
            )

            for element_item in hash_record.findall("addon"):
                hash_details = {}
                addon_name = element_item.attrib["name"]
                hash_details["name"] = addon_name
                hash_details["version"] = element_item.attrib["version"]
                hash_details["hash"] = element_item.text
                log("AddonData: Processing entry %s (%s) with hash %s" % (
                    hash_details["name"],
                    hash_details["version"],
                    hash_details["hash"],
                ))
                addon_list[addon_name] = hash_details
        except (ElemenTree.ParseError, OSError, ValueError):
            log(f"AddonData: Failed to read in file {hash_file}",
                xbmc.LOGERROR)
            log(f"AddonData: {traceback.format_exc()}", xbmc.LOGERROR)

        return addon_list

    def backup_from_master(self, target_location):
        """Perform backup operation from master instance to remote location."""
        log(f"AddonSync: Backing Up from Master to {target_location}")
        # Get all the items that require syncing
        addon_details = self.get_addons_to_sync()

        # Compare the hash of backup location to the hash of the current values
        stored_hashsums = self._load_hash_record(target_location)

        for addon_name in list(addon_details.keys()):
            addon_detail = addon_details[addon_name]
            # If there is no settings there is nothing to copy
            if addon_detail in [None, ""]:
                log(f"AddonSync: No settings for {addon_name}")
                continue

            src_dir = addon_detail["dir"]
            # Miss items that have no configuration
            if src_dir in [None, ""]:
                log(f"AddonSync: No configuration settings for {addon_name}")
                continue

            # Check if this addon already exists on the target location, if it
            # doesn't, then we need to copy it
            if addon_name in list(stored_hashsums.keys()):
                # Only copy the items with different hash values
                if (
                    addon_detail["hash"]
                    == stored_hashsums[addon_name]["hash"]
                ):
                    log(f"AddonSync: Backup for addon {addon_name} "
                        "already up to date with hash %s" %
                        addon_detail["hash"])
                continue

            log(f"AddonSync: Performing copy for {addon_name}")

            # Perform the copy of the addons settings
            target_dir = f"{target_location}{addon_name}/"

            # Start by removing the existing version
            try:
                nested_delete(target_dir)
            except OSError:
                log(f"AddonSync: Failed to delete {target_dir}", xbmc.LOGERROR)
                log(f"AddonSync: {traceback.format_exc()}", xbmc.LOGERROR)

            try:
                nested_copy(addon_detail["dir"], target_dir)
            except OSError:
                log(
                    "AddonSync: Failed to copy from %s to %s" %
                    (addon_detail["dir"], target_dir),
                    xbmc.LOGERROR,
                )
                log(f"AddonSync: {traceback.format_exc()}", xbmc.LOGERROR)

        # Save the new set of hash values
        self._generate_hash_record(addon_details, target_location)

    def copy_to_slave(self, source_location):
        """Copy configs from the central store to the local installation."""
        log(f"AddonSync: Restore from {source_location}")

        # Get all the hash values of the local installation
        local_addon_details = self.get_addons_to_sync()

        # Load the hash values from the central storage location
        stored_hashsums = self._load_hash_record(source_location)

        # Get the set of service addons, we will need to restart them if the
        # user has that option enabled
        restart_addons = []
        if Settings.is_restart_synced_services():
            restart_addons = self._get_service_addons()

        for addon_name in list(local_addon_details.keys()):
            # Check if this addon already exists on the source location
            if addon_name not in list(stored_hashsums.keys()):
                log(f"AddonSync: Local addon {addon_name} not in master data")
                continue

            # Only copy the items with different hash values
            addon_detail = local_addon_details[addon_name]
            backed_up_details = stored_hashsums[addon_name]
            if addon_detail["hash"] == backed_up_details["hash"]:
                log("AddonSync: Backup for addon %s already has matching hash %s"
                    % (addon_name, addon_detail["hash"]))
                continue

            # Make sure the version number is the same
            if Settings.is_force_version_match(
            ) and addon_detail["version"] != backed_up_details["version"]:
                log("AddonSync: Version numbers of addon %s are different (%s, %s)"
                    % (
                        addon_name,
                        addon_detail["version"],
                        backed_up_details["version"],
                    ))
                continue

            log(f"AddonSync: Performing copy for {addon_name}")

            # Perform the copy of the addons settings
            source_dir = f"{source_location}{addon_name}/"

            # Start by removing the existing version
            try:
                nested_copy(source_dir, addon_detail["dir"])
            except OSError:
                log(
                    "AddonSync: Failed to copy from %s to %s" %
                    (source_dir, addon_detail["dir"]),
                    xbmc.LOGERROR,
                )
                log(f"AddonSync: {traceback.format_exc()}", xbmc.LOGERROR)

            # Check if we need to restart the addon.
            if addon_name in restart_addons:
                self._restart_addon(addon_name)

    def _get_service_addons(self):
        # Make the call to find out all the service addons that are installed
        json_query = xbmc.executeJSONRPC(
            '{"jsonrpc": "2.0", "method": "Addons.GetAddons", "params": { "type": "xbmc.service", "enabled": true, "properties": ["broken"] }, "id": 1}'
        )

        json_response = json.loads(json_query)

        service_addons = []

        if ("result" in json_response) and ("addons"
                                            in json_response["result"]):
            # Check each of the service addons that are installed on the system
            for addon_item in json_response["result"]["addons"]:
                addon_name = addon_item["addonid"]

                # Skip ourselves
                if addon_name in [ID]:
                    log(f"AddonSync: Detected ourself: {addon_name}")
                    continue

                # Need to ensure we skip any addon that are flagged as broken
                if addon_item["broken"]:
                    log(f"AddonSync: Skipping broken addon: {addon_name}")
                    continue

                # Now we are left with only the addon screensavers
                log(f"AddonSync: Detected Service Addon: {addon_name}")
                service_addons.append(addon_name)

        return service_addons

    def _restart_addon(self, addon_name):
        log(f"AddonSync: Restarting addon {addon_name}")

        # To restart the addon, first disable it, then enable it
        xbmc.executeJSONRPC(
            '{"jsonrpc": "2.0", "method": "Addons.SetAddonEnabled", "params": { "addonid": "%s", "enabled": "toggle" }, "id": 1}'
            % addon_name)

        # Wait until the operation has completed (wait at most 10 seconds)
        monitor = xbmc.Monitor()
        max_wait_time = 10
        while max_wait_time > 0:
            max_wait_time = max_wait_time - 1
            if monitor.waitForAbort(1):
                # Abort was requested while waiting
                max_wait_time = 0
                break

            # Get the current state of the addon
            log(f"AddonSync: Disabling addon {addon_name}")
            json_query = xbmc.executeJSONRPC(
                '{"jsonrpc": "2.0", "method": "Addons.GetAddonDetails", "params": { "addonid": "%s", "properties": ["enabled"] }, "id": 1}'
                % addon_name)

            json_response = json.loads(json_query)

            if ("result" in json_response) and ("addon"
                                                in json_response["result"]):
                addon_detail = json_response["result"]["addon"]
                is_enabled = addon_detail["enabled"]

                if not is_enabled:
                    log(f"AddonSync: {addon_name} stopped, ready to restart")
                    max_wait_time = 0
                    break

        # Now enable the addon
        log(f"AddonSync: Enabling addon {addon_name}")
        xbmc.executeJSONRPC(
            '{"jsonrpc": "2.0", "method": "Addons.SetAddonEnabled", "params": { "addonid": "%s", "enabled": "toggle" }, "id": 1}'
            % addon_name)


class AddonSync:
    """Main class to perform the sync."""

    @staticmethod
    def start_sync():
        """Perform main add-on function, commit data to/from central store."""
        log("AddonSync: Sync Started")

        # On the first use we need to inform the user what the addon does
        if Settings.is_first_use():
            xbmcgui.Dialog().ok(
                ADDON.getLocalizedString(32001),
                ADDON.getLocalizedString(32005).encode("utf-8"),
            )
            Settings.set_first_use()

            # On first use we open the settings so the user can configure them
            ADDON.openSettings()

        # Get the location that the addons are to be synced with
        central_store_location = Settings.get_central_store_loc()

        if central_store_location not in [None, ""]:
            log(f"AddonSync: Central store is: {central_store_location}")

            addon_data = AddonData()
            monitor = xbmc.Monitor()

            # Check how often we need to check to sync up the settings
            check_interval = Settings.get_sync_interval()

            while not monitor.abortRequested():
                # Check if we are behaving like a master or slave
                if Settings.is_master():
                    # As the master we copy data from the local installation to
                    # a set location
                    addon_data.backup_from_master(central_store_location)
                else:
                    # This is the slave so we will copy from the external
                    # location to our local installation
                    addon_data.copy_to_slave(central_store_location)

                # Check for the case where we only want to check on startup
                if check_interval < 1:
                    break

                # Sleep/wait for abort for the correct interval
                if monitor.waitForAbort(check_interval * 60 * 60):
                    # Abort was requested while waiting
                    break

            del monitor
            del addon_data
        else:
            log("AddonSync: Central store not set")
            xbmcgui.Dialog().notification(
                ADDON.getLocalizedString(32001).encode("utf-8"),
                ADDON.getLocalizedString(32006).encode("utf-8"),
                ICON,
                5000,
                False,
            )
            return False

        log("AddonSync: Sync Ended")
        return True

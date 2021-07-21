# -*- coding: utf-8 -*-
"""This module generates all the hash values for the installed addons."""

import hashlib
import json
import os
import re
import traceback
import xml.etree.ElementTree as ET

import xbmc  # pylint: disable=import-error
import xbmcaddon  # pylint: disable=import-error
import xbmcgui  # pylint: disable=import-error
import xbmcvfs  # pylint: disable=import-error

# Import the common settings
from .settings import log, nestedCopy, nestedDelete, os_path_join, Settings

ADDON = xbmcaddon.Addon("service.addonsync")
ICON = ADDON.getAddonInfo("icon")


class Hash:
    """Class that will generate hash values for each plugin data section."""
    HASH_FUNCS = {
        "md5": hashlib.md5,
        "sha1": hashlib.sha1,
        "sha256": hashlib.sha256,
        "sha512": hashlib.sha512
    }

    def get_dir_hash(self, profile_name, hashfunc="md5", excluded_files=None):
        """Generates a hash for a given directory."""
        # Make sure a supported format is requested
        hash_func = Hash.HASH_FUNCS.get(hashfunc)
        if not hash_func:
            log("Hash: Invalid hash type requested %s" % hashfunc)
            return None

        if not excluded_files:
            excluded_files = []

        dirname = xbmc.translatePath(profile_name)

        # Make sure the location is a directory
        if not xbmcvfs.exists(dirname):
            log("Hash: %s is not a directory" % dirname)
            return None

        hashvalues = []
        for root, dirs, files in os.walk(dirname, topdown=True):
            if not re.search(r"/\.", root):
                hashvalues.extend(
                    [
                        self._filehash(os.path.join(root, f), hash_func)
                        for f in files
                        if not f.startswith(".")
                        and not re.search(r"/\.", f)
                        and f not in excluded_files
                    ]
                )
        return self._reduce_hash(hashvalues, hash_func)

    # Generates a hash value for a given file
    def _filehash(self, filepath, hashfunc):
        hasher = hashfunc()
        blocksize = 64 * 1024
        try:
            with open(filepath, "rb") as fp:
                while True:
                    data = fp.read(blocksize)
                    if not data:
                        break
                    hasher.update(data)
        except:
            log("Hash: Failed to create hash for %s" % filepath, xbmc.LOGERROR)
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

        addonDetails = {}

        # Now loop each of the addons to get the details required
        for addonName in list(active_addons.keys()):
            settingsDir = self._get_addon_settings_directory(addonName)

            # If there are no settings available then we have it installed
            # but no configuration available
            if settingsDir in [None, ""]:
                addonDetails[addonName] = None
            else:
                addonDetail = {}
                addonDetail["dir"] = settingsDir
                # Generate the hash
                hash = Hash()
                hash_value = hash.get_dir_hash(settingsDir)
                del hash

                log(
                    "AddonData: addon: %s path: %s hash: %s"
                    % (addonName, settingsDir, str(hash_value))
                )
                addonDetail["hash"] = hash_value
                addonDetails[addonName] = addonDetail
                addonDetail["version"] = active_addons[addonName]
        return addonDetails

    # Perform and filter the user has set up
    def _filter_addons(self, installed_addons):
        filtered_addons = {}
        # Find out what the setting for filtering is
        filterType = Settings.getFilterType()

        if filterType == Settings.FILTER_INCLUDE:
            # Add the included addons as they are just the id's split by spaces
            include_value = Settings.getIncludedAddons()
            log("AddonData: Include filter is %s" % include_value)
            if include_value not in [None, ""]:
                for incValue in include_value.split(" "):
                    # Make sure the addon is still installed
                    if incValue in list(installed_addons.keys()):
                        filtered_addons[incValue] = installed_addons[incValue]
        elif filterType == Settings.FILTER_EXCLUDE:
            exclude_value = Settings.getExcludedAddons()
            log("AddonData: Exclude filter is %s" % exclude_value)
            if exclude_value not in [None, ""]:
                excludedAddons = exclude_value.split(" ")
                for addonName in list(installed_addons.keys()):
                    if addonName not in excludedAddons:
                        filtered_addons[addonName] = installed_addons[addonName]
                    else:
                        log("AddonData: Skipping excluded addon %s" % addonName)
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
            '{"jsonrpc": "2.0", "method": "Addons.GetAddons", "params": { "enabled": true, "properties": ["version", "broken"] }, "id": 1}'
        )
        json_response = json.loads(json_query)

        addons = {}

        if ("result" in json_response) and (
            "addons" in json_response["result"]
        ):
            # Check each of the screensavers that are installed on the system
            for addonItem in json_response["result"]["addons"]:
                addonName = addonItem["addonid"]
                # Need to skip the two built-in screensavers as they can not be
                # triggered and are a bit dull, thus should not be in the mix
                if addonName in [
                    "screensaver.xbmc.builtin.black",
                    "screensaver.xbmc.builtin.dim",
                    "service.xbmc.versioncheck"
                ]:
                    log("AddonData: Skipping built-in addons: %s" % addonName)
                    continue

                if addonName.startswith("metadata"):
                    log("AddonData: Skipping metadata addon: %s" % addonName)
                    continue
                if addonName.startswith("resource.language"):
                    log(
                        "AddonData: Skipping resource.language addon: %s"
                        % addonName
                    )
                    continue
                if addonName.startswith("repository"):
                    log("AddonData: Skipping repository addon: %s" % addonName)
                    continue
                if addonName.startswith("skin"):
                    log("AddonData: Skipping skin addon: %s" % addonName)
                    continue

                # Skip ourselves so we don't update a slave with a master
                if addonName in ["service.addonsync"]:
                    log("AddonData: Detected ourself: %s" % addonName)
                    continue

                # Need to ensure we skip any addons that are flagged as broken
                if addonItem['broken']:
                    log("AddonData: Skipping broken addon: %s" % addonName)
                    continue

                # Now we are left with only the working addons
                log("AddonData: Detected Addon: %s" % addonName)
                addons[addonName] = addonItem["version"]

        return addons

    def _get_addon_settings_directory(self, addonName):
        log("AddonData: Get addon settings directory for %s" % addonName)

        addonInfo = xbmcaddon.Addon(addonName)
        if addonInfo in [None, ""]:
            log("AddonData: Failed to get addon data for %s" % addonName)
            return None

        addonProfile = addonInfo.getAddonInfo("profile")
        if addonProfile in [None, ""]:
            log("AddonData: Failed to get addon profile for %s" % addonName)
            return None

        configPath = xbmc.translatePath(addonProfile)

        # Check if the directory exists
        if xbmcvfs.exists(configPath):
            log("AddonData: addon: %s path: %s" % (addonName, configPath))
            configPath = addonProfile
        else:
            # If the path does not exist then we will not need to copy this one
            log(
                "AddonData: addon: %s path: %s does not exist"
                % (addonName, configPath)
            )
            configPath = None

        return configPath

    def _generateHashRecord(self, addonDetails, centralStoreLocation):
        log("AddonData: Generating hash record %s" % centralStoreLocation)

        hashFile = os_path_join(centralStoreLocation, "hashdata.xml")

        # <addonsync>
        #    <addon name='service.addonsync' version ='1.0.0'>hash_value</addon>
        # </addonsync>
        try:
            root = ET.Element("addonsync")
            for addonName in list(addonDetails.keys()):
                addonDetail = addonDetails[addonName]
                # If there are no settings, there is nothing to copy
                if addonDetail in [None, ""]:
                    continue
                hash = addonDetail["hash"]
                # Miss items that have no hash
                if hash in [None, ""]:
                    continue

                addonElem = ET.SubElement(root, "addon")
                addonElem.attrib["name"] = addonName
                addonElem.attrib["version"] = addonDetail["version"]
                addonElem.text = addonDetail["hash"]

            # Save the XML file to disk
            recordFile = xbmcvfs.File(hashFile, "w")
            try:
                fileContent = ET.tostring(root, encoding="UTF-8")
                recordFile.write(fileContent)
            except:
                log(
                    "AddonData: Failed to write file: %s" % recordFile,
                    xbmc.LOGERROR
                )
                log("AddonData: %s" % traceback.format_exc(), xbmc.LOGERROR)
            recordFile.close()

        except:
            log(
                "AddonData: Failed to create XML Content %s"
                % traceback.format_exc(),
                xbmc.LOGERROR
            )

    # Reads an existing XML file with Hash values in it
    def _loadHashRecord(self, recordLocation):
        log("AddonData: Loading hash record %s" % recordLocation)

        hashFile = os_path_join(recordLocation, "hashdata.xml")

        addonList = {}
        if not xbmcvfs.exists(hashFile):
            log(
                "AddonData: Unable to load as file does not exist %s" % hashFile
            )
            return addonList

        try:
            recordFile = xbmcvfs.File(hashFile, "r")
            recordFileStr = recordFile.read()
            recordFile.close()

            hashRecord = ET.ElementTree(ET.fromstring(recordFileStr))

            for elemItem in hashRecord.findall("addon"):
                hashDetails = {}
                addonName = elemItem.attrib["name"]
                hashDetails["name"] = addonName
                hashDetails["version"] = elemItem.attrib["version"]
                hashDetails["hash"] = elemItem.text
                log(
                    "AddonData: Processing entry %s (%s) with hash %s"
                    % (
                        hashDetails["name"],
                        hashDetails["version"],
                        hashDetails["hash"]
                    )
                )
                addonList[addonName] = hashDetails
        except:
            log(
                "AddonData: Failed to read in file %s" % hashFile, xbmc.LOGERROR
            )
            log("AddonData: %s" % traceback.format_exc(), xbmc.LOGERROR)

        return addonList

    def backupFromMaster(self, targetLocation):
        """
        Performs the backup operation from a master installation to a remote
        location.
        """
        log("AddonSync: Backing Up from Master to %s" % targetLocation)
        # Get all the items that require syncing
        addonDetails = self.get_addons_to_sync()

        # Compare the hash of backup location to the hash of the current values
        backedUpHashValues = self._loadHashRecord(targetLocation)

        for addonName in list(addonDetails.keys()):
            addonDetail = addonDetails[addonName]
            # If there is no settings there is nothing to copy
            if addonDetail in [None, ""]:
                log("AddonSync: No settings for %s" % addonName)
                continue

            sourcDir = addonDetail["dir"]
            # Miss items that have no configuration
            if sourcDir in [None, ""]:
                log("AddonSync: No configuration settings for %s" % addonName)
                continue

            # Check if this addon already exists on the target location, if it
            # doesn't, then we need to copy it
            if addonName in list(backedUpHashValues.keys()):
                # Only copy the items with different hash values
                if addonDetail["hash"] == backedUpHashValues[addonName]["hash"]:
                    log(
                        "AddonSync: Backup for addon %s already up to date with hash %s"
                        % (addonName, addonDetail["hash"])
                    )
                    continue

            log("AddonSync: Performing copy for %s" % addonName)

            # Perform the copy of the addons settings
            targetDir = "%s%s/" % (targetLocation, addonName)

            # Start by removing the existing version
            try:
                nestedDelete(targetDir)
            except:
                log("AddonSync: Failed to delete %s" % targetDir, xbmc.LOGERROR)
                log("AddonSync: %s" % traceback.format_exc(), xbmc.LOGERROR)

            try:
                nestedCopy(addonDetail["dir"], targetDir)
            except:
                log(
                    "AddonSync: Failed to copy from %s to %s"
                    % (addonDetail["dir"], targetDir),
                    xbmc.LOGERROR
                )
                log("AddonSync: %s" % traceback.format_exc(), xbmc.LOGERROR)

        # Save the new set of hash values
        self._generateHashRecord(addonDetails, targetLocation)

    def copyToSlave(self, sourceLocation):
        """Copies from the backup location to the local installation."""
        log("AddonSync: Restore from %s" % sourceLocation)

        # Get all the hash values of the local installation
        localAddonDetails = self.get_addons_to_sync()

        # Load the hash values from the central storage location
        backedUpHashValues = self._loadHashRecord(sourceLocation)

        # Get the set of service addons, these are the ones that will need to be
        # restarted if the user has that option enabled
        restartAddons = []
        if Settings.isRestartUpdatedServiceAddons():
            restartAddons = self._getServiceAddons()

        for addonName in list(localAddonDetails.keys()):
            # Check if this addon already exists on the source location
            if addonName not in list(backedUpHashValues.keys()):
                log(
                    "AddonSync: Local addon %s not in remote location"
                    % addonName
                )
                continue

            # Only copy the items with different hash values
            addonDetail = localAddonDetails[addonName]
            backedUpDetails = backedUpHashValues[addonName]
            if addonDetail["hash"] == backedUpDetails["hash"]:
                log(
                    "AddonSync: Backup for addon %s already has matching hash %s"
                    % (addonName, addonDetail["hash"])
                )
                continue

            # Make sure the verson number is the same
            if Settings.isForceVersionMatch():
                if addonDetail["version"] != backedUpDetails["version"]:
                    log(
                        "AddonSync: Version numbers of addon %s are different (%s, %s)"
                        % (
                            addonName,
                            addonDetail["version"],
                            backedUpDetails["version"]
                        )
                    )
                    continue

            log("AddonSync: Performing copy for %s" % addonName)

            # Perform the copy of the addons settings
            sourceDir = "%s%s/" % (sourceLocation, addonName)

            # Start by removing the existing version
            try:
                nestedCopy(sourceDir, addonDetail["dir"])
            except:
                log(
                    "AddonSync: Failed to copy from %s to %s"
                    % (sourceDir, addonDetail["dir"]),
                    xbmc.LOGERROR
                )
                log("AddonSync: %s" % traceback.format_exc(), xbmc.LOGERROR)

            # Check if we need to restart the addon.
            if addonName in restartAddons:
                self._restartAddon(addonName)

    def _getServiceAddons(self):
        # Make the call to find out all the service addons that are installed
        json_query = xbmc.executeJSONRPC(
            '{"jsonrpc": "2.0", "method": "Addons.GetAddons", "params": { "type": "xbmc.service", "enabled": true, "properties": ["broken"] }, "id": 1}'
        )

        json_response = json.loads(json_query)

        serviceAddons = []

        if ("result" in json_response) and (
            "addons" in json_response["result"]
        ):
            # Check each of the service addons that are installed on the system
            for addonItem in json_response["result"]["addons"]:
                addonName = addonItem["addonid"]

                # Skip ourselves
                if addonName in ["service.addonsync"]:
                    log("AddonSync: Detected ourself: %s" % addonName)
                    continue

                # Need to ensure we skip any addon that are flagged as broken
                if addonItem["broken"]:
                    log(
                        "AddonSync: Skipping broken service addon: %s"
                        % addonName
                    )
                    continue

                # Now we are left with only the addon screensavers
                log("AddonSync: Detected Service Addon: %s" % addonName)
                serviceAddons.append(addonName)

        return serviceAddons

    def _restartAddon(self, addonName):
        log("AddonSync: Restarting addon %s" % addonName)

        # To restart the addon, first disable it, then enable it
        xbmc.executeJSONRPC(
            '{"jsonrpc": "2.0", "method": "Addons.SetAddonEnabled", "params": { "addonid": "%s", "enabled": "toggle" }, "id": 1}'
            % addonName
        )

        # Wait until the operation has completed (wait at most 10 seconds)
        monitor = xbmc.Monitor()
        maxWaitTime = 10
        while maxWaitTime > 0:
            maxWaitTime = maxWaitTime - 1
            if monitor.waitForAbort(1):
                # Abort was requested while waiting
                maxWaitTime = 0
                break

            # Get the current state of the addon
            log("AddonSync: Disabling addon %s" % addonName)
            json_query = xbmc.executeJSONRPC(
                '{"jsonrpc": "2.0", "method": "Addons.GetAddonDetails", "params": { "addonid": "%s", "properties": ["enabled"] }, "id": 1}'
                % addonName
            )

            json_response = json.loads(json_query)

            if ("result" in json_response) and (
                "addon" in json_response["result"]
            ):
                addonDetail = json_response["result"]["addon"]
                isEnabled = addonDetail["enabled"]

                if not isEnabled:
                    log(
                        "AddonSync: Addon %s stopped, ready to restart"
                        % addonName
                    )
                    maxWaitTime = 0
                    break

        # Now enable the addon
        log("AddonSync: Enabling addon %s" % addonName)
        xbmc.executeJSONRPC(
            '{"jsonrpc": "2.0", "method": "Addons.SetAddonEnabled", "params": { "addonid": "%s", "enabled": "toggle" }, "id": 1}'
            % addonName
        )


class AddonSync:
    """Main class to perform the sync."""
    @staticmethod
    def startSync():
        log("AddonSync: Sync Started")

        # On the first use we need to inform the user what the addon does
        if Settings.isFirstUse():
            xbmcgui.Dialog().ok(
                ADDON.getLocalizedString(32001),
                ADDON.getLocalizedString(32005).encode("utf-8")
            )
            Settings.setFirstUse()

            # On first use we open the settings so the user can configure them
            ADDON.openSettings()

        # Get the location that the addons are to be synced with
        centralStoreLocation = Settings.getCentralStoreLocation()

        if centralStoreLocation not in [None, ""]:
            log("AddonSync: Central store is: %s" % centralStoreLocation)

            addon_data = AddonData()
            monitor = xbmc.Monitor()

            # Check how often we need to check to sync up the settings
            checkInterval = Settings.getCheckInterval()

            while not monitor.abortRequested():
                # Check if we are behaving like a master or slave
                if Settings.isMasterInstallation():
                    # As the master we copy data from the local installation to
                    # a set location
                    addon_data.backupFromMaster(centralStoreLocation)
                else:
                    # This is the slave so we will copy from the external
                    # location to our local installation
                    addon_data.copyToSlave(centralStoreLocation)

                # Check for the case where we only want to check on startup
                if checkInterval < 1:
                    break

                # Sleep/wait for abort for the correct interval
                if monitor.waitForAbort(checkInterval * 60 * 60):
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
                False
            )
            return False

        log("AddonSync: Sync Ended")
        return True

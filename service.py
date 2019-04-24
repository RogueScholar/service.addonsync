# -*- coding: utf-8 -*-
import sys
import xbmc
import xbmcaddon

if sys.version_info >= (2, 7):
    import json
else:
    import simplejson as json

# Import the common settings
from resources.lib.settings import log
from resources.lib.settings import Settings
from resources.lib.core import AddonSync

ADDON = xbmcaddon.Addon(id='service.addonsync')


##################################
# Main of the Addon Sync Service
##################################
if __name__ == '__main__':
    log("AddonSync: Service Started (version %s)" % ADDON.getAddonInfo('version'))

    # Check if we should be running sync when the system starts
    if Settings.isRunOnStartup():
        addonSync = AddonSync()
        addonSync.startSync()
        del addonSync
    else:
        log("AddonSync: Not running at startup")

    log("AddonSync: Service Ended")

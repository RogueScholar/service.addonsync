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

    json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Addons.GetAddonDetails", "params": { "addonid": "repository.robwebset", "properties": ["enabled", "broken", "name", "author"]  }, "id": 1}')
    json_response = json.loads(json_query)

    displayNotice = True
    if ("result" in json_response) and ('addon' in json_response['result']):
        addonItem = json_response['result']['addon']
        if (addonItem['enabled'] is True) and (addonItem['broken'] is False) and (addonItem['type'] == 'xbmc.addon.repository') and (addonItem['addonid'] == 'repository.robwebset') and (addonItem['author'] == 'robwebset'):
            displayNotice = False

            # Check if we should be running sync when the system starts
            if Settings.isRunOnStartup():
                addonSync = AddonSync()
                addonSync.startSync()
                del addonSync
            else:
                log("AddonSync: Not running at startup")

    if displayNotice:
        xbmc.executebuiltin('Notification("robwebset Repository Required","github.com/robwebset/repository.robwebset",10000,%s)' % ADDON.getAddonInfo('icon'))

    log("AddonSync: Service Ended")

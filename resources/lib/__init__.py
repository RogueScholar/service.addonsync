# -*- coding: utf-8; python-indent-offset: 2; python-guess-indent: nil; -*-
"""AddonSync service add-on for Kodi v19 'Matrix'.

This file is part of service.addonsync.

SPDX-FileCopyrightText:  2020-2021 Peter J. Mello <admin@petermello.net>

SPDX-License-Identifier: MPL-2.0

See LICENSES/MPL-2.0.txt for more information.
"""

from __future__ import annotations, generator_stop
import os  # noqa
import xbmc  # noqa
import xbmcvfs  # noqa
from xbmcaddon import Addon  # noqa


if __name__ == "__main__" and __package__ is None:
  __package__ = "addonsync"

__all__ = ["addonsync", "core", "filter", "service", "settings"]

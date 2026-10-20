# -*- coding: utf-8 -*-
import os
import sys

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _pkg_sub in ["Lib/site-packages", "python-embed/Lib/site-packages"]:
    _p = os.path.join(_root, _pkg_sub.replace("/", os.sep))
    if os.path.exists(_p) and _p not in sys.path:
        sys.path.append(_p)

from .base_view import BaseView
from .cockpit_view import CockpitView
from .activity_hub_view import ActivityHubView
from .excel_aktarim_view import ExcelAktarimView
from .rpa_station_view import RPAStationView
from .master_kontrol_view import MasterKontrolView
from .gtb_view import GTBView
from .kantar_view import KantarView
from .eta_view import ETAView
from .evrim_view import EvrimView
from .shield_chat_view import ShieldChatView
from .portals_view import QNBPortalView, GLPPortalView, DogruerPortalView, TalepPortalView
from .summary_view import SummaryView
from .settings_view import SettingsView
from .users_view import UsersView
from .apex_view import ApexView
from .horizon_view import HorizonView
from .ai_assistant_view import AIAssistantView

__all__ = [
    "BaseView", "CockpitView", "ActivityHubView", "ExcelAktarimView",
    "RPAStationView", "MasterKontrolView", "GTBView", "KantarView",
    "ETAView", "EvrimView", "ShieldChatView", "QNBPortalView",
    "GLPPortalView", "DogruerPortalView", "TalepPortalView",
    "SummaryView", "SettingsView", "UsersView",
    "ApexView", "HorizonView", "AIAssistantView"
]

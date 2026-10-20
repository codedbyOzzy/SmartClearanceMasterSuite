# -*- coding: utf-8 -*-
"""
views package — Doğruer MasterSuite Modüler Görünümleri
"""
from .base_view import BaseView

# Modül 1 & 2 & Diğerleri
try:
    from .cockpit_view import CockpitView
except ImportError:
    CockpitView = None

try:
    from .activity_hub_view import ActivityHubView
except ImportError:
    ActivityHubView = None

try:
    from .gtb_view import GTBView
except ImportError:
    GTBView = None

try:
    from .kantar_view import KantarView
except ImportError:
    KantarView = None

try:
    from .eta_view import ETAView
except ImportError:
    ETAView = None

try:
    from .evrim_view import EvrimView
except ImportError:
    EvrimView = None

try:
    from .shield_view import ShieldView
except ImportError:
    ShieldView = None

try:
    from .portals_view import (
        PortalsView,
        QNBPortalView,
        GLPPortalView,
        DogruerPortalView,
        TalepPortalView
    )
except ImportError:
    PortalsView = None
    QNBPortalView = None
    GLPPortalView = None
    DogruerPortalView = None
    TalepPortalView = None

try:
    from .summary_view import SummaryView
except ImportError:
    SummaryView = None

try:
    from .settings_view import SettingsView
except ImportError:
    SettingsView = None

try:
    from .users_view import UsersView
except ImportError:
    UsersView = None

try:
    from .rpa_station_view import RPAStationView
except ImportError:
    RPAStationView = None

try:
    from .ai_assistant_view import AIAssistantView
except ImportError:
    AIAssistantView = None

__all__ = [
    "BaseView",
    "CockpitView",
    "ActivityHubView",
    "RPAStationView",
    "AIAssistantView",
    "GTBView",
    "KantarView",
    "ETAView",
    "EvrimView",
    "ShieldView",
    "PortalsView",
    "QNBPortalView",
    "GLPPortalView",
    "DogruerPortalView",
    "TalepPortalView",
    "SummaryView",
    "SettingsView",
    "UsersView",
]

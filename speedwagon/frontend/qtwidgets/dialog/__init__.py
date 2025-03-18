"""Subpackage: Common elements for creating UI dialog box."""
from .dialogs import about_dialog_box, SystemInfoDialog
from .settings import GlobalSettingsTab, TabsConfigurationTab, TabEditor

__all__ = [
    "GlobalSettingsTab",
    "SystemInfoDialog",
    "TabEditor",
    "TabsConfigurationTab",
    "about_dialog_box",
]

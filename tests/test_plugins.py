from unittest.mock import Mock
import pluggy
from speedwagon import plugins

def test_register_whitelisted_plugins(monkeypatch):

    monkeypatch.setattr(plugins, "get_whitelisted_plugins", lambda: [
        ("root", 'plugin 1')])
    plugin_manager = Mock(
        pluggy.PluginManager,
        unregister=Mock(),
        list_name_plugin=Mock(
            return_value=[
                ('plugin 1', Mock())
            ]
        )
    )
    plugins.register_whitelisted_plugins(plugin_manager)
    plugin_manager.unregister.assert_not_called()
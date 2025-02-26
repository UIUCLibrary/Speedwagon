from importlib.metadata import entry_points
from unittest.mock import Mock
import pluggy
import pytest

from speedwagon import plugins
from speedwagon.exceptions import SpeedwagonException

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

def test_get_workflows_from_plugin_with_no_workflows_produces_warning(caplog):
    plugin = Mock(registered_workflows=Mock(return_value={}))
    entry_point = Mock(load=Mock(return_value=plugin))
    plugins.get_workflows_from_plugin(entry_point)
    assert \
        len(caplog.records) == 1, \
        f'Expected 1 logged message. Actual: {len(caplog.records)}'

    assert \
        caplog.records[0].levelname == "WARNING", \
        f'Expected log level: "WARNING". Actual "{caplog.records[0].levelname}"'

    assert "No workflows were registered" in caplog.text

def test_get_workflows_from_plugin():
    entry_point = Mock(
        load=Mock(
            return_value=Mock(
                registered_workflows=Mock(
                    return_value={
                        "spam": Mock()
                    }
                )
            )
        )
    )
    assert "spam" in plugins.get_workflows_from_plugin(entry_point)

def test_get_workflows_from_plugin_with_invalid_plugin_raises():
    # simulate that the plugin does not have a registered_workflows function
    entry_point = Mock(
        load=Mock(
            return_value=Mock(
                registered_workflows=Mock(
                    side_effect=AttributeError
                )
            )
        )
    )
    with pytest.raises(SpeedwagonException) as error:
        plugins.get_workflows_from_plugin(entry_point)
    assert "Unable to load plugin" in str(error.value)

def test_get_workflows_from_plugin_inclusion_filter():
    spam_workflow = Mock()
    spam_workflow.name = "spam"

    bacon_workflow = Mock()
    bacon_workflow.name = "bacon"

    entry_point = Mock(
        load=Mock(
            return_value=Mock(
                registered_workflows=Mock(
                    return_value={
                        "spam": spam_workflow,
                        "bacon": bacon_workflow
                    }
                )
            )
        )
    )
    workflows =\
        plugins.get_workflows_from_plugin(
            entry_point,
            inclusion_filter=lambda workflow: workflow.name == "spam"
        )
    assert "spam" in workflows and "bacon" not in workflows

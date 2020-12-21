from unittest.mock import Mock

import speedwagon.job


def test_all_required_workflow_keys(monkeypatch):
    def mocked_workflows():
        return {
            "spam": Mock(required_settings_keys={"spam_setting"}),
            "bacon": Mock(required_settings_keys={"bacon_setting"}),
            "eggs": Mock(required_settings_keys=set()),
        }

    monkeypatch.setattr(
        speedwagon.job, "available_workflows", mocked_workflows
    )

    assert speedwagon.job.all_required_workflow_keys() == {
        "spam_setting", "bacon_setting"
    }

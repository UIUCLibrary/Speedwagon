from speedwagon.workflows.workflow_make_checksum import \
    MakeChecksumBatchSingleWorkflow, MakeChecksumBatchMultipleWorkflow


def test_singleChecksum_has_options():
    workflow = MakeChecksumBatchSingleWorkflow()
    user_options = workflow.get_user_options()
    assert len(user_options) > 0


def test_multipleChecksum_has_options():
    workflow = MakeChecksumBatchMultipleWorkflow()
    user_options = workflow.get_user_options()
    assert len(user_options) > 0

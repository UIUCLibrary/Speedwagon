import typing
import speedwagon.models
from speedwagon import worker
import speedwagon.tools.tool_verify_checksum
from speedwagon.job import AbsTool
from speedwagon.tools import options


class EchoTool(AbsTool):
    name = "Echo"
    description = "Sed odio sem, vestibulum a lacus sed, posuere porta " \
                  "neque. Ut urna arcu, dignissim a dolor ac, sollicitudin " \
                  "pellentesque mi. Curabitur feugiat interdum mauris nec " \
                  "venenatis. In arcu elit, scelerisque et bibendum id, " \
                  "faucibus id enim. Proin dui mi, imperdiet eget varius " \
                  "ut, faucibus at lectus. Sed accumsan quis turpis id " \
                  "bibendum. Mauris in ligula nec tortor vulputate " \
                  "vulputate. Nullam tincidunt leo nec odio tincidunt " \
                  "malesuada. Integer ut massa dictum, scelerisque turpis " \
                  "eget, auctor nibh. Vestibulum sollicitudin sem eget enim " \
                  "congue tristique. Cras sed purus ac diam pulvinar " \
                  "scelerisque et efficitur justo. Duis eu nunc arcu"

    def new_job(self) -> typing.Type[worker.ProcessJobWorker]:
        return EchoJob

    @staticmethod
    def discover_task_metadata(**user_args) -> typing.List[dict]:
        alt = user_args.copy()
        alt["message"] = "nope"
        return [
            user_args,
            alt
        ]

    @staticmethod
    def get_user_options() -> typing.List[options.UserOption2]:
        return [
            options.UserOptionPythonDataType2("message")
        ]


class EchoJob(worker.ProcessJobWorker):

    def process(self, *args, **kwargs):
        self.result = {
            "success": "yes",
            "message": kwargs['message']
        }


def test_tool_options_model():
    tool = EchoTool
    user_options = tool.get_user_options()

    assert isinstance(user_options, list)
    model = speedwagon.models.ToolOptionsModel3(user_options)
    index = model.index(0, 0)
    model.setData(index, "hello world")
    d = model.get()
    assert d["message"] == "hello world"

#
# @pytest.mark.notFromSetupPy
# def test_work_runner(qtbot):
#
#     # results in two jobs,
#     # the first job's task_result is the same message as the user settings
#     # the second is the message "nope"
#     tool = EchoTool()
#
#     user_settings = {'message': 'hello world'}
#
#     test_worker = worker.WorkerManager(title="test runner",
#                                        tool=tool,
#                                        logger=logging.getLogger(__name__))
#
#     with test_worker.open(settings=user_settings) as work_runner:
#         assert isinstance(work_runner, worker.WorkRunnerExternal)
#
#         assert work_runner.dialog.isVisible() is False
#
#         assert work_runner.jobs.qsize() == 2
#         assert work_runner.dialog.windowTitle() == "test runner"
#         work_runner._start_tool()
#         work_runner.finish()
#         assert work_runner.dialog.minimum() == 0
#         assert work_runner.dialog.maximum() == 2
#     assert work_runner.dialog.isVisible() is False
#
#     assert isinstance(test_worker.results, list)
#     assert len(test_worker.results) == 2
#     assert isinstance(test_worker.results[0], dict)
#     results = sorted(test_worker.results, key=lambda x: x["message"])
#
#     assert results[0]["success"] == "yes"
#     assert results[0]["message"] == "hello world"
#
#     assert results[1]["success"] == "yes"
#     assert results[1]["message"] == "nope"
#
#
# @pytest.mark.skip("Local test only")
# def test_runner(qtbot):
#     tool = speedwagon.tools.tool_verify_checksum.VerifyChecksumBatchSingle()
#
#     user_settings = {
#         'Input':
#             '/Users/hborcher/test_images/'
#             'Brittle Books - Good/1251150/checksum.md5'
#     }
#
#     test_worker = worker.WorkerManager(title="test runner", tool=tool)
#
#     with test_worker.open(settings=user_settings) as work_runner:
#         assert isinstance(work_runner, worker.WorkRunner)
#
#         assert work_runner.dialog.isVisible() is False
#
#         assert work_runner.jobs.qsize() == 1118
#         assert work_runner.dialog.windowTitle() == "test runner"
#
#         work_runner.finish()
#         assert work_runner.dialog.minimum() == 0
#         assert work_runner.dialog.maximum() == 1118
#         assert work_runner.dialog.isVisible() is True
#     assert work_runner.dialog.isVisible() is False
#     # assert work_runner.dialog.value() == 1118
#     assert len(test_worker.results) == 1118
#     pass

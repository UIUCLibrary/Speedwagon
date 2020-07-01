import sys
from typing import List, Any

from speedwagon.job import Workflow
from . import shared_custom_widgets as options
from uiucprescon import packager

from .. import tasks


class HathiLimitedToDLWorkflow(Workflow):
    name = "Convert HathiTrust limited view to Digital library"
    description = 'This tool converts HathiTrust limited view packages to ' \
                  'Digital library'

    active = True

    def discover_task_metadata(self, initial_results: List[Any],
                               additional_data, **user_args) -> List[dict]:
        hathi_limited_view_packager = packager.PackageFactory(
            packager.packages.HathiLimitedView())
        tasks = []

        for p in hathi_limited_view_packager.locate_packages(
                user_args['Input']):
            tasks.append({
                "package": p,
                "destination": user_args['Output']
            })

        return tasks

    def create_new_task(self, task_builder: tasks.TaskBuilder, **job_args):
        n = PackageConverter(src=job_args['package'],
                             dst=job_args['destination'])
        task_builder.add_subtask(n)

    def user_options(self):
        return [
            options.UserOptionCustomDataType("Input", options.FolderData),
            options.UserOptionCustomDataType("Output", options.FolderData)
        ]


class PackageConverter(tasks.Subtask):

    def work(self) -> bool:
        output_packager = packager.PackageFactory(
            packager.packages.DigitalLibraryCompound())
        output_packager.transform(self.src, self.dst)
        return True

    def __init__(self, src, dst) -> None:

        super().__init__()
        self.src = src
        self.dst = dst

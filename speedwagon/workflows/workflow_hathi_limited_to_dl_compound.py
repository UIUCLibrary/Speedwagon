from typing import List, Any

from speedwagon.job import Workflow
from . import shared_custom_widgets as options


class HathiLimitedToDLWorkflow(Workflow):
    name = "Convert HathiTrust limited view to Digital library"
    description = '''This tool converts HathiTrust limited view packages to 
    Digital library'''

    active = True

    def discover_task_metadata(self, initial_results: List[Any],
                               additional_data, **user_args) -> List[dict]:
        pass

    def user_options(self):
        return [
            options.UserOptionCustomDataType("Input", options.FolderData),
            options.UserOptionCustomDataType("Output", options.FolderData)
        ]

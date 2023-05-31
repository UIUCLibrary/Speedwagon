from typing import List, Any, Dict
import speedwagon
from speedwagon.plugins import Plugin

class MyWorkflow(speedwagon.Workflow):
    name = "My Workflow"

    def discover_task_metadata(
        self,
        initial_results: List[Any],
        additional_data: Dict[str, Any],
        **user_args
    ) -> List[dict]:
        return []

plugin = Plugin()
plugin.register_workflow(MyWorkflow)

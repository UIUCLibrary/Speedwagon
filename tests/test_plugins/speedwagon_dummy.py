from typing import List, Any, Dict
import speedwagon
class MyWorkflow(speedwagon.Workflow):
    name = 'My Workflow'

    def discover_task_metadata(self, initial_results: List[Any],
                               additional_data: Dict[str, Any], **user_args) -> \
    List[dict]:
        return []


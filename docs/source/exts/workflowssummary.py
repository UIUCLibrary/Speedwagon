"""workflowssummary

Sphinx extension that adds the ability to generate documentation for each
workflow.

Example:
    ```.. workflowlist::```

Notes:
    Leading and trailing whitespace is ignored when generating descriptions.

"""

from docutils.parsers.rst import Directive
from docutils import nodes
from speedwagon import job

all_workflows = job.available_workflows()


class WorkflowMetadataListDirective(Directive):

    workflows_entries = dict()

    def run(self):

        sections = []
        for workflow in all_workflows.values():

            workflow_item = self.new_workflow_entry_section(workflow)
            sections.append(workflow_item)
        return sections

    def new_workflow_entry_section(self, workflow) -> nodes.section:
        env = self.state.document.settings.env

        # if entry is already generated reuse it
        if workflow.name in self.workflows_entries:
            return self.workflows_entries[workflow.name]

        print("Generating entry for {}".format(workflow.name))
        targetid = "workflow-%{}".format(env.new_serialno('workflow'))
        workflow_item = nodes.section(ids=[targetid])
        workflow_item.append(nodes.title(text=workflow.name, ids=[targetid]))
        if workflow.description:
            description_block = nodes.line_block()
            for line in workflow.description.split("\n"):
                new_line = nodes.line(text=line)
                description_block += new_line
            workflow_item.append(description_block)

        # Cache entries already existing so no need to generate them
        self.workflows_entries[workflow.name] = workflow_item
        return workflow_item


def setup(app):
    app.add_directive("workflowlist", WorkflowMetadataListDirective)
    return {
        'version': '0.1',
    }

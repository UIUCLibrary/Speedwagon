"""workflowssummary

Sphinx extension that adds the ability to generate documentation for each
workflow.

By default, a description is added. To not include this,
add ``:nodescription:`` option

Example:
    ```.. workflowlist::```



Notes:
    Leading and trailing whitespace is ignored when generating descriptions.

"""

from docutils.parsers.rst import Directive, directives
from docutils import nodes
import speedwagon
from sphinx.util import logging
from sphinx import addnodes

all_workflows = speedwagon.available_workflows()


class AutoWorkflowDirective(Directive):
    required_arguments = 1
    optional_arguments = 0
    has_content = True
    final_argument_whitespace = True
    option_spec = {
        'notitle': directives.flag,
        'description': directives.flag
    }
    add_index = True

    def run(self):
        workflow = all_workflows.get(self.arguments[0])
        if not workflow:

            valid_workflows = [w for w in all_workflows.keys()]
            self.warning(f"Unable to add {self.arguments[0]}, "
                         f"Only known ones are {','.join(valid_workflows)}")
            return []
        indexnode = addnodes.index(entries=[])

        targetid = nodes.make_id("workflow-{}".format(workflow.name))

        targetname = nodes.fully_normalize_name(workflow.name)

        section = nodes.section(names=[targetname], ids=[targetid])

        if "notitle" not in self.options:
            new_title = nodes.title(
                workflow.name,
                text=workflow.name,
                ids=[targetid]
            )
            section.append(new_title)

        if "description" in self.options and workflow.description:
            description_block = nodes.line_block()
            for line in workflow.description.split("\n"):
                new_line = nodes.line(text=line)
                description_block += new_line
            section += description_block
        par = nodes.paragraph()
        self.state.nested_parse(self.content, self.content_offset, par)
        section += par
        self.add_name(section)
        indexnode['entries'].append(
            ('single', workflow.name, targetid, '', workflow.name[0]))

        section.append(indexnode)
        return [section]


class WorkflowMetadataListDirective(Directive):

    entries = dict()
    has_content = False
    logger = logging.getLogger(__name__)
    option_spec = {
        'nodescription': directives.flag
    }

    def run(self):

        sections = []
        entries_generated = 0
        env = self.state.document.settings.env
        indexnode = addnodes.index(entries=[])
        sections.append(indexnode)

        for workflow in all_workflows.values():
            targetid = "workflow-%{}".format(env.new_serialno('workflow'))

            # Add an entry for the workflow into documentation's index page
            indexnode['entries'].append(
                ('single', workflow.name, targetid, '', workflow.name[0]))

            # if entry is already generated reuse it
            if workflow.name in self.entries:
                workflow_item = self.entries[workflow.name]
            else:
                workflow_item = \
                    self.new_workflow_entry_section(workflow, targetid)

                entries_generated += 1

                # Cache entries already existing so no need to generate them
                WorkflowMetadataListDirective.entries[workflow.name] = \
                    workflow_item

            sections.append(workflow_item)

        print("[workflowsummary] generated "
              "{} workflow summaries".format(entries_generated))

        return sections

    def new_workflow_entry_section(self, workflow, ids) -> nodes.section:

        self.logger.verbose("Generating entry for {}".format(workflow.name))

        targetname = nodes.fully_normalize_name(workflow.name)
        workflow_item = nodes.section(ids=[ids], names=[targetname])
        workflow_item.append(nodes.title(text=workflow.name, ids=[ids]))
        if "nodescription" not in self.options and workflow.description:
            description_block = nodes.line_block()
            for line in workflow.description.split("\n"):
                new_line = nodes.line(text=line)
                description_block += new_line
            workflow_item.append(description_block)

        return workflow_item


def setup(app):

    app.add_directive("workflowlist", WorkflowMetadataListDirective)
    app.add_directive("autoworkflow", AutoWorkflowDirective)
    return {
        'version': '0.1',
    }

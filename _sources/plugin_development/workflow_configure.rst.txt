======================
Workflow Configuration
======================

Speedwagon Workflows can provide a configuration at the workflow level that a
user can configure in the application settings. This is useful if the workflow
requires access to a directory on the hard drive, such as the path to training
data or a url that the workflow has to access.

When a workflow has a workflow configuration, a configuration section shows up
in the Workflows settings in Settings as seen below.

.. figure:: ../configure/workflow_configure.png

    As seen on MacOS in Settings Window

Register Settings
=================

To add Workflow settings to a workflow, override the
:py:meth:`workflow_options() <speedwagon.Workflow.workflow_options>` method
within the derived speedwagon.Workflow class.

    .. code:: python

        class GenerateMarcXMLFilesWorkflow(speedwagon.Workflow):
            name = "Generate MARC.XML Files"
            ...

            def workflow_options(self):
                return [
                    speedwagon.workflow.TextLineEditData(
                        label="Getmarc server url",
                        required=True
                    ),
                ]

To access the data in the workflow setting, use the
:py:meth:`get_workflow_configuration_value(key) <speedwagon.Workflow.get_workflow_configuration_value>`
method.

    .. code:: python

        class GenerateMarcXMLFilesWorkflow(speedwagon.Workflow):
            name = "Generate MARC.XML Files"
            ...

            def discover_task_metadata(self, initial_results,
                                       additional_data, user_args):

                server_url =\
                    self.get_workflow_configuration_value(
                        key="Getmarc server url"
                    )
                ...
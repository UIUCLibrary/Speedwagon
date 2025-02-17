=====
Tasks
=====

A Speedwagon job contains one or more tasks that do some kind of work.

To perform work as part of a job, the :py:class:`Workflow
<speedwagon.Workflow>` needs to take input provided by the user and turn it
into tasks. This is done in two steps. First with
:py:meth:`discover_task_metadata()
<speedwagon.Workflow.discover_task_metadata>` method and then with the
:py:meth:`create_new_task() <speedwagon.Workflow.create_new_task>` method.

The :py:meth:`discover_task_metadata()
<speedwagon.Workflow.discover_task_metadata>` method is for generating a list
of serializable metadata that could be used to generate a task.

The :py:meth:`create_new_task() <speedwagon.Workflow.create_new_task>` method
uses the information generate by :py:meth:`discover_task_metadata()
<speedwagon.Workflow.discover_task_metadata>` to generate tasks.

The :py:meth:`initial_task() <speedwagon.Workflow.initial_task>` method
is simular to :py:meth:`create_new_task()
<speedwagon.Workflow.create_new_task>` but the execution of these tasks
after the job is submitted but before :py:meth:`get_additional_info()
<speedwagon.Workflow.get_additional_info>` and
:py:meth:`discover_task_metadata() <speedwagon.Workflow.discover_task_metadata>`
methods. It is useful for gathering information about potential tasks will be
run. For example: This could run a task that is traversing a path with many
items.
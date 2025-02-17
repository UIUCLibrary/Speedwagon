===========================================
Getting User Input After Submitting the Job
===========================================

Jobs in Speedwagon are a limited to user interaction once a job has been
submitted. As of version 0.4.0, there is no way to inquire feedback from a
user once the tasks have started to run.

However, there is a single time in the lifespan of a job that a user can be
asked for additional information after the job has been submitted.

If the :py:class:`Workflow <speedwagon.Workflow>` derived class implements
the :py:meth:`get_additional_info()
<speedwagon.Workflow.get_additional_info>` method, the user can be asked to
provide additional information to configure the job already started but
before :py:meth:`discover_task_metadata()
<speedwagon.Workflow.discover_task_metadata>` and starting the
main tasks of the job.

It is intended to be used with the :py:meth:`initial_task()
<speedwagon.Workflow.initial_task>` method of the derived
:py:class:`Workflow <speedwagon.Workflow>` because
:py:class:`Results <speedwagon.tasks.Result>` from these tasks
are available to :py:meth:`discover_task_metadata()
<speedwagon.Workflow.discover_task_metadata>`


.. code-block:: python

    class LocateBadFiles(speedwagon.tasks.Subtask):
        def work(self) -> bool:
            self.set_results(["file1.txt", "file2.txt"])
            return True

    class WorkflowRemoveBadFiles(speedwagon.Workflow):
        name = "Remove Bad Files"

        def initial_task(
            self,
            task_builder: TaskBuilder, **user_args
        ) -> None:
            # Contrived task that locates "bad files"
            task_builder.add_subtask(LocateBadFiles())

        def get_additional_info(
            self,
            user_request_factory: UserRequestFactory,
            options: dict, pretask_results: list
        ) -> dict:
            # From the list of possible bad files, ask the user
            # to approve which files are okay to delete.
            requester = user_request_factory.confirm_removal()
            return requester.get_user_response(
                options,
                pretask_results
            )

        def discover_task_metadata(
            self,
            initial_results: List[speedwagon.tasks.Result[List[str]]],
            additional_data: Dict[str, Any],
            **user_args
        ) -> List[dict]:

            # Use the initial_results collected from
            # get_additional_info to only create task information for
            # the files approved by the user.
            files_to_remove = []
            for initial_result in initial_results:
                if initial_result.source == LocateBadFiles:
                    files_to_remove.extend(
                        {"file_name": file_to_delete}
                        for file_to_delete in initial_result.data
                    )
            return files_to_remove

        def create_new_task(
            self,
            task_builder: TaskBuilder,
            **job_args
        ) -> None:
            task_builder.add_subtask(
                speedwagon.tasks.filesystem.DeleteFile(
                    path=job_args["file_name"]
                )
            )



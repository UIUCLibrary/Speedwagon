=====================
Reporting Job Results
=====================

After a job is completed, it is often helpful to provide the user a report of
what happened. This might be a summary of all the items processed or the
results of a validation.

To include a report with your Speedwagon Workflow, override the
:py:meth:`generate_report() <speedwagon.Workflow.generate_report>` method in
your derived :py:class:`sptoxeedwagon.Workflow <speedwagon.Workflow>` class.

This method has the results of the tasks and returns a report as a string.

.. code-block:: python

    ConvertFileTaskResult = TypedDict(
        "ConvertFileTaskResult", {
            "file_created": str
        }
    )


    class MakeJp2Workflow(job.Workflow):
        ...
        @classmethod
        def generate_report(
            cls,
            results: List[
                speedwagon.tasks.Result[ConvertFileTaskResult]
            ],
            **user_args: str
        ) -> Optional[str]:
            files_generated: List[str] = [
                result.data["file_created"]
                for result in results
            ]
            files_generated_list = "\n".join(files_generated)
            return "Results:" \
                   "\n" \
                   "\nCreated the following files:" \
                   f"\n{files_generated_list}"


    class ConvertFileTask(
        speedwagon.tasks.Subtask[ConvertFileTaskResult]
    ):
        ...
        def work(self) -> bool:
            images.convert_image(
                self.source_file,
                self.destination_file
            )

            # This will be the same data made available in the
            # list of Results in the generate_report method.
            self.set_results({
                "file_created": self.destination_file,
            })
            return os.path.exists(self.destination_file)

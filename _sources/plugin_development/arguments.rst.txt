=========
Arguments
=========

Most Workflows are going to have parameters provided by the user to configure a job. These parameters could be in the
form of an input directory or file. They could also be a toggle to provide additional task to a job.

Adding user arguments a Workflow to specialize a job can be done within by overriding the
:py:meth:`job_options() <speedwagon.Workflow.job_options>` method.

:py:meth:`job_options() <speedwagon.Workflow.job_options>` returns a Python list of objects that are subclasses of
:py:class:`speedwagon.workflow.AbsOutputOptionDataType <speedwagon.workflow.AbsOutputOptionDataType>`.
This includes the following.

* :py:class:`DirectorySelect <speedwagon.workflow.DirectorySelect>` for selecting a folder.
* :py:class:`FileSelectData <speedwagon.workflow.FileSelectData>` for selecting a file.
* :py:class:`ChoiceSelection <speedwagon.workflow.ChoiceSelection>` for selecting a value with a pre-determined set
  of possible values.
* :py:class:`BooleanSelect <speedwagon.workflow.BooleanSelect>` for selecting a value that is True or False.
* :py:class:`ChoiceSelection <speedwagon.workflow.TextLineEditData>` for selecting a string.




.. code-block:: python

    class MakeChecksums(speedwagon.Workflow):
        name = "Generate Checksums"

        def job_options(self) -> List[speedwagon.workflow.AbsOutputOptionDataType]:
            selected_hash_algorithm = speedwagon.workflow.DirectorySelect(label="Algorithm")
            selected_hash_algorithm.add_selection("MD5")
            selected_hash_algorithm.add_selection("SHA-1")
            selected_hash_algorithm.add_selection("SHA-256")

            return [
                speedwagon.workflow.DirectorySelect(label="Source Path"),
                selected_hash_algorithm,
            ]


Validation
==========

To sanitize inputs provided by a user, validations can be added to any
:py:class:`AbsOutputOptionDataType <speedwagon.workflow.AbsOutputOptionDataType>`. object using the
:py:meth:`add_validation <speedwagon.workflow.AbsOutputOptionDataType.add_validation>` method.

The following validation classes are included as a part of speedwagon in the
:py:mod:`speedwagon.validators <speedwagon.validators>` module.

* :py:class:`ExistsOnFileSystem <speedwagon.validators.ExistsOnFileSystem>`
* :py:class:`IsDirectory <speedwagon.validators.IsDirectory>`
* :py:class:`IsFile <speedwagon.validators.IsFile>`
* :py:class:`CustomValidation <speedwagon.validators.CustomValidation>`


.. code-block:: python

    class MakeChecksums(speedwagon.Workflow):
       def job_options(self) -> List[speedwagon.workflow.AbsOutputOptionDataType]:
            input_path = speedwagon.workflow.DirectorySelect(label="Source Path")
            input_path.add_validation(speedwagon.validators.ExistsOnFileSystem())

            # The IsDirectory validation below only runs if the condition evaluates
            #  os.path.exists to True.
            input_path.add_validation(
                speedwagon.validators.IsDirectory(),
                condition=lambda candidate, _: os.path.exists(candidate)
            )

            return [
                input_path
            ]

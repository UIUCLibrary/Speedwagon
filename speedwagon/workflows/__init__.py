r"""Subpackage:  Contains the bundled workflows in Speedwagon.

During startup, this package is scanned for python modules that start with
"workflow\\_" in the filename. These files are then scanned to see if they
contain for any classes which implements speedwagon.job.AbsWorkflow base
class. As these classes are located, they made available to Speedwagon.

Example:
    The CompletenessWorkflow() class in the file,
    speedwagon/workflows/workflow_completeness.py will be made available as
    "Verify HathiTrust Package Completeness". However, the class in the same
    file, ValidateOCRFilesTask() implements Subtask instead, so it will not be.


Changes:
++++++++

    .. versionadded:: 0.1.3
       Generate OCR Files Workflow

    .. versionadded:: 0.1.4
       Convert CaptureOne TIFF to Digital Library Compound Object and
           HathiTrust

    .. versionchanged:: 0.1.4
       Migrated existing tools to use workflow

       This includes the following tools:

            * Convert CaptureOne TIFF to Digital Library Compound Object
            * Convert CaptureOne TIFF to Hathi TIFF package
            * Convert CaptureOne Preservation TIFF to Digital Library
              Access JP2
            * Convert TIFF to HathiTrust JP2
            * Generate MARC.XML Files
            * Make Checksum Batch [Multiple]
            * Make Checksum Batch [Single]
            * Update Checksum Batch [Multiple]
            * Update Checksum Batch [Single]
            * Validate Tiff Image Metadata for HathiTrust
            * Verify Checksum Batch [Single]
            * Zip Packages

    .. versionchanged:: 0.1.5
       Generate MARC.XML Files uses getmarc_server_url instead of \
            quest.library.illinois.edu/GetMARC.

    .. versionadded:: 0.1.5
       Generate MARC.XML Files supports MMSID and bibid id type

    .. versionchanged:: 0.4.0
        Removed all built in workflows

"""

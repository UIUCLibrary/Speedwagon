.. :changelog:

----------
Change Log
----------


v0.4.0b5 (2024-05-30)
=====================

BREAKING CHANGE
---------------

- Workflow class has job_args and user_args arguments

v0.4.0b4 (2024-05-24)
=====================

BREAKING CHANGE
---------------

- removed Convert CaptureOne TIFF to Digital Library Compound Object, Convert CaptureOne TIFF to Digital Library Compound Object and HathiTrust, Convert HathiTrust limited view to Digital library, & Hathi prep

Feat
----

- AbsOutputOptionDataType gains add_validation() and get_findings()
- AbsOutputOptionDataType gains add_validation() and get_findings()
- remove internal workflows

v0.4.0a2 (2024-03-21)
=====================

v0.3.1 (2024-03-19)
===================

Feat
----

- Added table_data_editor to UserRequestFactory

Fix
---

- Uninstalling from Chocolatey removes shortcut
- Fixed Internal C++ object (Signals) already deleted on exit.

v0.3.0 (2024-02-19)
===================

Fix
---

- help url crashing when missing package metadata

0.2.2
=====

- New Feature
    - Import and export job configuration settings as a json file.
    - Job options using files & folders can be dragged & dropped from system file browser

0.1.5
=====

- General
    - Windows versions are available with a private Chocolatey repository.

- New Workflows
    - Convert HathiTrust limited view to Digital library

- Workflow improvements
    - CaptureOne Batch to HathiTrust TIFF Complete Package
    - Support for MMSID and bibid identifiers.
    - Support for new marc data server.
    - Convert CaptureOne TIFF to Digital Library Compound Object
    - Support file names using a dash delimiter
    - Convert CaptureOne TIFF to Digital Library Compound Object and HathiTrust
    - Support for MMSID and bibid identifiers.
    - When an output format is not set in the settings, no output format
      will for that format will be generated. As long as one output
      format is set, the workflow will run. Previously, speedwagon  would
      present the user with an error.
    - Generate MARC.XML Files
    - Support MMSID identifiers
    - Support adding 955 field
    - getmarc stops and present an error message if connectivity problems with server

0.1.4
=====

- General
    - Splash screen while loading UI
    - Tabs can be configured
    - Global settings can be configured

- OCR
    - Use Tesseract 4.0
    - Selecting languages use full language names instead of language codes

- Documentation
    - User documentation

- New Tools:
    - Make JP2

0.1.3
=====

- General:
    - Text from the console can be exported to a log file
- New Workflows:
    - Generate OCR Files
- Fixes:
    - Verify HathiTrust Package Completeness workflow no longer fails on hidden system directories.
    - DPI is updated when creating access files for hathi


0.1.2
=====

- New Tools:
    - Validate Tiff Image Metadata for HathiTrust
- New Workflows:
    - Validate Metadata
- Improvements:
    - Generated MARC records are now enhanced with a 955 field
    - Jp2 files can be selected for title page in HathiPrep
- API Changes:
    - Combobox UI widget added to options
- Distribution:
    - Use CMake to generate standalone distribution installer packages.
    - Able to support the following Windows distribution packages:
        - msi installer
        - exe installer
        - zip portable (Not an installer. Program runs without installing)

- Bug fixes:
- Creating jp2 files no longer opens a command shell window during processing
- Error message returned by jp2 converter are decoded correctly
- Compatibility with white spaces in file path no longer breaks jp2 conversion

0.1.1
=====
- General:
    - Added Workflow tab
    - Add Worflow API
- Changes:
    - Changed name to Speedwagon
    - Verify HathiTrust Package Completeness is now a Workflow (instead of a tool)
- New Tools:
    - Convert TIFF to HathiTrust JP2
    - Convert CaptureOne Preservation TIFF to Digital Library Access JP2
    - Convert CaptureOne Preservation TIFF to Digital Library Compound Objects
- New Workflows:
    - CaptureOne Batch to HathiTrust TIFF Complete Package


0.0.3
=====

- Improved performance and responsiveness
- New Tools:
    - Convert CaptureOne TIFF to Hathi TIFF package
    - Generate MARC.XML Files
    - Zip Packages
- Tool Changes:
    - * Verify HathiTrust Package Completeness optionally checks if the OCR files contain any characters that are not in UTF-8


0.0.2
=====

- General:
    - Report more verbose detail on the processes working. This is done by piping the log information used by the dependent tools into the information presented to the user.
- User Interface:
    - Display version number on main window
- New Tools:
    - Update Checksum Batch [Multiple]
    - Update Checksum Batch [Single]
- Tool Changes:
    - Split Make Checksum Batch into multiple and single versions
    - Split Verify Checksum Batch into multiple and single versions
    - Verify HathiTrust Package Completeness generates a file manifest report as well as an error report


0.0.1
=====
- Named Forseti
    - Working Tools:
        - Verify HathiTrust Package Completeness
        - Zip Packages
        - Verify Checksum Batch
        - Make Checksum Batch

- Fixes:
    - Verify HathiTrust Package Completeness optionally checks for OCR files
    - Verify HathiTrust Package Completeness issue when dealing with paths that include spaces
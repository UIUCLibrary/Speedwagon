.. :changelog:

Release History
---------------

0.1.1
+++++
* General:
   * Added Workflow tab
   * Add Worflow API
* Changes:
   * Changed name to Speedwagon
   * Verify HathiTrust Package Completeness is now a Workflow (instead of a tool)
* New Tools:
   * Convert TIFF to HathiTrust JP2
   * Convert CaptureOne Preservation TIFF to Digital Library Access JP2
   * Convert CaptureOne Preservation TIFF to Digital Library Compound Objects
* New Workflows:
   * CaptureOne Batch to HathiTrust TIFF Complete Package


0.0.3
+++++
* Improved performance and responsiveness
* New Tools:
   * Convert CaptureOne TIFF to Hathi TIFF package
   * Generate MARC.XML Files
   * Zip Packages
* Tool Changes:
   * * Verify HathiTrust Package Completeness optionally checks if the OCR files contain any characters that are not in UTF-8


0.0.2
+++++
* General:
   * Report more verbose detail on the processes working. This is done by piping the log information used by the dependent tools into the information presented to the user.
* User Interface:
   * Display version number on main window
* New Tools:
   * Update Checksum Batch [Multiple]
   * Update Checksum Batch [Single]
* Tool Changes:
   * Split Make Checksum Batch into multiple and single versions
   * Split Verify Checksum Batch into multiple and single versions
   * Verify HathiTrust Package Completeness generates a file manifest report as well as an error report


0.0.1
+++++
* Named Forseti
* Working Tools:
   * Verify HathiTrust Package Completeness
   * Zip Packages
   * Verify Checksum Batch
   * Make Checksum Batch
* Fixes:
   * Verify HathiTrust Package Completeness optionally checks for OCR files
   * Verify HathiTrust Package Completeness issue when dealing with paths that include spaces


Dev
+++

* New Tools:
   * Validate Tiff Image Metadata for HathiTrust
* New Workflows:
   * Validate Metadata
* Improvements:
   * Generated MARC records are now enhanced with a 955 field
   * Jp2 files can be selected for title page in HathiPrep
* API Changes:
    * Combobox UI widget added to options
* Distribution:
   * Use CMake to generate standalone distribution installer packages.
   * Able to support the following Windows distribution packages:
       * msi installer
       * exe installer
       * zip portable (Not an installer. Program runs without installing)

* Bug fixes:
    * Creating jp2 files no longer opens a command shell window during processing
    * Error message returned by jp2 converter are decoded correctly
    * Compatibility with white spaces in file path no longer breaks jp2 conversion
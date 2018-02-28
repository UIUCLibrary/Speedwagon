.. :changelog:

Release History
---------------

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
* Improved performance and responsiveness
* New Tools:
   * Convert CaptureOne TIFF to Hathi TIFF package
   * Generate MARC.XML Files
   * Zip Packages
* Tool Changes:
   * * Verify HathiTrust Package Completeness optionally checks if the OCR files contain any characters that are not in UTF-8

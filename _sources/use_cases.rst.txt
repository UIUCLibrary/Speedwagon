=========
Use Cases
=========

Simplified Directory Structure Diagram (Vendor generated package)
=================================================================

- The Simplified Workflow described below requires a specific directory
  structure.  Files must be structured properly with correct labels for
  Speedwagon to process the files.

- For all vendored content HathiTrust serves as the final preservation
  repository.

- Deliverables from the U of I vendor include JP2000, text, marc.xml, MD5 and
  yml files for each book.  See the diagram below to see an example of the
  directory structure for this workflow. See figure below:

batch folder

+--------------------+-----------------------+
| uniqueID1          | uniqueID2             |
|                    |                       |
|   - 00000001.jp2   |      - 00000001.xml   |
|   - 00000001.xml   |      - 00000002.jp2   |
|   - 00000001.xml   |      - 00000002.txt   |
|   - 00000002.jp2   |      - 00000002.xml   |
|   - 00000002.txt   |      - checksum.md5   |
|   - 00000002.xml   |      - marc           |
|   - checksum.md5   |      - meta.yml       |
|   - marc           |                       |
|   - meta.yml       |                       |
+--------------------+-----------------------+




Internal Workflow Diagram (Locally generated package)
=====================================================

- The U of I digitizes content on site.  Files generated in the digitization
  lab are packaged in large batches with preservation and access derivatives.
  Each package will contain an access folder with TIFFS and a preservation
  folder with TIFFS.  Each package contains several books.

- Tiff files are first converted to JP2000 files with the "Convert TIFF to
  HathiTrustJP2."  However, the program will work with JP2000 or TIFF files.
  The U of I prefers to create JP2000 files for it packages.

- Files are named with a preceding unique identifier followed by an
  underscore and 8 digit padded number. The U of I prepares files for
  HathiTrust Digital Library as well as the local preservation repository,
  Medusa.  This requires 2 output directories. Speedwagon will package the
  batch of files for both repositories.

- Use the "Convert CaptureOne TIFF to Hathi to Digital Library Compound
  Object and HathiTrust." This will create a directory of folders split up
  by book, named with the unique identifier.

- For HT, a copy of the JP2000 files are organized into separate folder
  named with the unique identifier.

- For the local preservation repository, both preservation TIFFs and access
  JP2000 files are organized into a package profile, named by unique
  identifier.

- The unique identifier and underscore are removed from the file names.  The
  TIFFS or JP2000 files contain only the 8 digit padded number. See the
  figure below:


Input - Batch Folder

    - Preservation

      + uniqueID1_00000001.jp2
      + uniqueID1_00000002.jp2
      + uniqueID2_00000001.jp2
      + uniqueID2_00000002.jp2

    - access

     + uniqueID1_00000001.tif
     + uniqueID1_00000002.tif
     + uniqueID2_00000001.tif
     + uniqueID2_00000002.tif

    Output HT Package

    Split into individual book packages

    - access (folder)

     + uniqueID1_00000001.jp2
     + uniqueID1_00000002.jp2

    - access (folder)

     + uniqueID2_00000001.jp2
     + uniqueID2_00000002.jp2

Output for Local Preservation Repository Package
(NB: this content not packaged for Hathi)

Split into individual book packages

    - uniqueID1 (folder)

     + preservation (folder)

        * uniqueID1_00000001.tif
        * uniqueID1_00000002.tif

     + access (folder)

        * uniqueID1_00000001.jp2
        * uniqueID1_00000002.jp2

    - uniqueID2 (folder)

     + preservation (folder)

        * uniqueID2_00000001.tif
        * uniqueID2_00000002.tif

     + access (folder)

        * uniqueID2_00000001.jp2
        * uniqueID2_00000002.jp2

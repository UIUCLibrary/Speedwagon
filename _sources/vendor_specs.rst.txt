======================================
Vendor File & Technical Specifications
======================================

The following may be helpful for institutions seeking to ingest content into
HathitTust using a vendor to carry out the digitization. The
"Simplified Workflow" in Speedwagon is designed with these specifications in
mind.

.. note:: This is a truncated version of the U of I workflow for the purpose
          of communicating essential file specifications needed for HathiTrust
          ingest, please contact the U of I Digital Reformatting Coordinator
          if you would like the complete specifications


Scanning Specification
======================

- Bit-Depth/Resolution

  - Bitone: scan each page at 600dpi, saved as a JPEG2000 image.
  - Grayscale: scan each page with half tone images at 300dpi, saved as a
    JPEG2000 image.
  - Color: scan each page with color at 300dpi, saved as a JPEG2000 image.

- All images will be cropped and deskewed as necessary.
- The first four pages for each title will consist of the production note
  (front only), copyright statement (front only) and the front cover (outside
  and inside).

  - The appropriate copyright statement will be indicated by UIUC in the
    provided spreadsheet.
  - Copies of the current copyright statements and production note are
    appended at the end of this document.

- Do NOT scan/print the page [front + back] with the attached circulation
  slip (unless the page has printed front matter).
- A ‘Missing Page’ target/image [front + back] will be inserted to indicate
  that volume has known missing pages and UIUC will be unable to provide
  replacement pages. Please refer to page 6 for Guidelines for Requesting
  Missing Pages.
- Foldouts and 2-page spreads will be captured as a single image, unless
  otherwise noted.
- All metadata will be embedded in the appropriate XML box of the JPEG2000
  file.
- Create a checksum.md5 file with MD5 checksums for all files.
- Create UTF-8 text files for each page. Please refer to the project Excel
  master spreadsheet (provided by UIUC) for the appropriate OCR language to be
  used for each title.
- Create an ALTO file for each page containing text and text location
  information. If ALTO files cannot be generated for a certain language, NM
  will generate a multi-page PDF Image + Text file for that title. The PDF
  file will be stored at the root of the delivery media. The PDF file will
  be named according the items ObjectID.

- A yaml file including the follow data

    #. capture_date: the date the meta.yml file is created.
    #. capture_agent: "IU".
    #. pagedata: page labels and order_labels (printed page names). The
       following page labels will be used:

        - BLANK - pages with no printed or written content
        - CHAPTER_END - end of a major content block.
        - CHAPTER_START - beginning of a major content block.  Book chapters not ordinarily marked.
        - COPYRIGHT - ordinarily the second page of an object
        - COLOPHON - ordinarily the second to last page of an object
        - COVER - front or back outside cover
        - FIRST_CONTENT_CHAPTER_START - first content page after front matter
        - FOLDOUT
        - INDEX
        - LAST_CONTENT - last content page before back matter
        - PREFACE
        - PRODUCTION_NOTE - ordinarily the first page of an object
        - REFERENCES
        - TABLE_OF_CONTENTS
        - TITLE

Metadata
========

HathiTrust requirements for embedded technical metadata:

.. list-table:: JP2 Metadata
   :widths: 10 20
   :header-rows: 1

   * - Tag
     - Value
   * - CompressionScheme
     - JPEG-2000
   * - Format
     - JPEG-2000
   * - MIMETYPE
     - image/jp2
   * - Brand (or "MajorBrand")
     - jp2
   * - MinorVersion
     - 0
   * - Compatibility (or "CompatibleBrands")
     - jp2
   * - Xsize (or "ImageWidth")
     - matches XMP/tiff:imageWidth
   * - Ysize (or "ImageHeight")
     - matches XMP/tiff:imageHeight
   * - NumberOfLayers
     - mandatory, but no required value
   * - NumberDecompositionLevels
     - mandatory, but no required value
   * - BitsPerSample
     - 8 for Grayscale, (8,8,8  [24-bit]) for sRGB
   * - XSamplingFrequency
     - generally between 300/1 and 600/1, matches XMP/tiff:Xresolution
   * - YSamplingFrequency
     - generally between 300/1 and 600/1, matches XMP/tiff:Yresolution
   * - SamplingFrequencyUnit
     - mandatory, matches XMP/SamplingFrequencyUnit


.. list-table:: XMP Metadata
   :widths: 10 20
   :header-rows: 1

   * - Tag
     - Value
   * - xpacket field
     - W5M0MpCehiHzreSzNTczkc9d
   * - tiff:imageWidth
     - matches JP2/Xsize
   * - tiff:imageHeight
     - matches JP2/Ysize
   * - tiff:BitsPerSample
     - 8 for Grayscale, (8,8,8 [24-bit]) for sRGB
   * - tiff:Compression
     - 34712 (=JPEG2000)
   * - tiff:PhotometricInterpretation
     - 2 for sRGG, 1 for Grayscale
   * - tiff:Orientation
     - 1 (Horizontal/Normal)
   * - tiff:SamplesPerPixel
     - 3 for sRGB, 1 for Grayscale
   * - tiff:Xresolution
     - generally between 300/1 and 600/1, matches XMP/tiff:Xresolution
   * - tiff:Yresolution
     - generally between 300/1 and 600/1, matches XMP/tiff:Yresolution
   * - SamplingFrequencyUnit
     - mandatory, matches XMP/SamplingFrequencyUnit
   * - tiff:ResolutionUnit
     - 2 (inches)
   * - dc:source
     - object $id/$filename
   * - tiff:DateTime
     - formatted YYYY:mm:ddTHH:MM:SS, for example 2010:05:24T13:45:30
   * - tiff:Artist
     - University of Illinois at Urbana-Champaign Library
   * - tiff:Make
     - make of camera/scanner
   * - tiff:Model
     - model of camera/scanner

UIUC will provide XML files with the metadata for each item named {objectID}.xml or  {objectID}{volume}.xml
Directory Structure/File Naming
Directory: objectID

::

    File: 00000001.jp2
    File: 00000001.txt
    File: 00000001.xml
    File: 00000002.jp2
    File: 00000002.txt
    File: 00000002.xml
    File: meta.yml
    File: marc.xml
    File: checksum.md5

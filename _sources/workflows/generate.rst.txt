Generate Files
==============

.. autoworkflow:: Generate MARC.XML Files
    :description:

.. autoworkflow:: Generate OCR Files

    Uses :term:`Google Tesseract` to create :term:`OCR <Optical Character Recognition>` text files for images.


    Settings:
        Path: Path containing tiff or jp2 files.
        Image File Type: The type of Image file to use.


    Adding Additional Languages:
        To modify the available languages, place Tesseract traineddata files for current version in to the data directory

    Note:
        It's important to use the correct version of the traineddata files. Using incorrect versions won't crash the program but they may produce unexpected results.

    For more information about these files, go to https://github.com/tesseract-ocr/tesseract/wiki/Data-Files


.. autoworkflow:: Make Checksum Batch [Single]
    :description:

.. autoworkflow:: Make Checksum Batch [Multiple]
    :description:

.. autoworkflow:: Make JP2
    :description:


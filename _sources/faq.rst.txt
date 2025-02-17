===
FAQ
===

How Do I Add Languages to the Generate OCR Files Workflow?
==========================================================

    The Generate OCR Files workflow uses :term:`Google Tesseract` to perform OCR.
    In order, for Tesseract to do that, it needs the Tesseract language data
    files. These files can be found on the internet
    `here for individual languages <https://github.com/tesseract-ocr/tesseract/wiki/Data-Files>`_
    or `here for the full language set <https://github.com/tesseract-ocr/tessdata/releases>`_.

    These language data files must be extracted to your :term:`Tessdata Directory`.

Generate OCR Files Workflow Has No Languages
============================================

    Speedwagon cannot find the required language data files on your computer.
    See `How Do I Add Languages to the Generate OCR Files Workflow?`_

What Tools Are You Using in Speedwagon?
=======================================

    * :term:`Python 3 <Python>`
    * PySide for generating the GUI
    * :term:`CMake` to generate standalone installable packages
    * :term:`Google Tesseract` for producing OCR
    * :term:`Exiv2` for inspecting embedded image metadata
    * :term:`Kakadu <Kakadu Encoder>` for creating JPEG2000 images

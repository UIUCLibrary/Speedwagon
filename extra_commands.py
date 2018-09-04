import sys
import urllib.request
from tempfile import TemporaryDirectory
from distutils.command.clean import clean as _clean
from distutils.command.build_py import build_py
import setuptools.command
import os
import glob
try:
    from pyqt_distutils.config import Config
except ModuleNotFoundError as e:
    print("pyqt_distutils not installed. Unable to run special commands", file=sys.stderr)

TESSERACT_DATA_URL = "https://github.com/tesseract-ocr/tessdata/raw/3.04.00/"


class TesseractData(setuptools.Command):
    description = "Download Tesseract data"
    user_options = [
        ("tessdata-url=", "u", "base url for downloading tesseract data"),
        ("inplace", None, "install tesseract data in source"),
        ('build-lib=', 'd', "directory to \"build\" (copy) to"),
    ]

    def initialize_options(self):
        self.tessdata_url = None
        self.inplace = False
        self.build_lib = None


    def finalize_options(self):
        self.set_undefined_options('build',
                                   ('build_lib', 'build_lib'),
                                   ('force', 'force'))

        self.package_data = self.distribution.package_data
        self.inplace = bool(self.inplace)
        if self.tessdata_url is None:
            self.tessdata_url = TESSERACT_DATA_URL

    def run(self):
        self.add_tesseract_data()

    def add_tesseract_data(self):

        tessdata_path = os.path.join("speedwagon", "workflows", "tessdata")
        if self.inplace:
            destination = tessdata_path
        else:
            destination = os.path.join(self.build_lib, tessdata_path)

        if not os.path.exists(destination):
            self.mkpath(destination)

        english_data_url = "{}{}".format(self.tessdata_url, "eng.traineddata")
        self.download_data(english_data_url, destination)

        osd_data_url = "{}{}".format(self.tessdata_url, "osd.traineddata")
        self.download_data(osd_data_url, destination)

    def download_data(self, url, destination):
        with TemporaryDirectory() as download_path:
            base_name = os.path.basename(url)
            destination_file = os.path.join(destination, base_name)

            if os.path.exists(destination_file):
                return

            print("Downloading {}".format(url))
            test_file_path = os.path.join(download_path, base_name)

            urllib.request.urlretrieve(url, filename=test_file_path)
            if not os.path.exists(test_file_path):
                raise FileNotFoundError(
                    "Failure to download file from {}".format(url))
            self.move_file(test_file_path, destination)


class CustomBuildPy(build_py):
    def run(self):
        self.run_command("build_ui")
        self.run_command("dl_tessdata")
        super().run()


class Clean(_clean):
    def run(self):
        super().run()
        self.clean_ui()
        self.clean_tesseract_data()

    @staticmethod
    def clean_tesseract_data():
        base = os.path.abspath(os.path.dirname(__file__))
        tessdata_path = os.path.join(
            base, "speedwagon", "workflows", "tessdata"
        )

        glob_exp = os.path.join(tessdata_path, "*.traineddata")
        for tesseract_data_file in glob.glob(glob_exp):
            print("Removing {}".format(tesseract_data_file))
            os.remove(tesseract_data_file)

    @staticmethod
    def clean_ui():
        config = Config()
        config.load()
        for glob_exp, dest in config.files:
            for src in glob.glob(glob_exp):

                if src.endswith(".ui"):
                    gen_file = "{}_ui.py".format(os.path.splitext(src)[0])
                    if os.path.exists(gen_file):
                        print("Removing {}".format(gen_file))
                        os.remove(gen_file)

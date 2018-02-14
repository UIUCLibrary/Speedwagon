import enum
import typing

import os

from forseti import worker
from forseti.tools import tool_options
from forseti.tools.abstool import AbsTool
from forseti.worker import ProcessJob
from uiucprescon import pygetmarc


class UserArgs(enum.Enum):
    INPUT = "Input"


class JobValues(enum.Enum):
    BIB_ID = "bib_id"
    PATH = "path"


class ResultsValues(enum.Enum):
    BIB_ID = "bib_id"
    SUCCESS = "success"


class GenerateMarcXMLFilesTool(AbsTool):
    name = "Generate MARC.XML Files"
    description = "For input, this tool takes a path to a directory of files, each of which is a digitized volume, " \
                  "and is named for that volume’s bibid. The program then retrieves MARC.XML files for these bibIDs " \
                  "and writes them into the folder for each corresponding bibID. It uses the UIUC Library’s GetMARC " \
                  "service (http://quest.library.illinois.edu/GetMARC/) to retrieve these MARC.XML files from the " \
                  "Library’s catalog. "

    @staticmethod
    def new_job() -> typing.Type[worker.ProcessJob]:
        return MarcGenerator

    @staticmethod
    def validate_args(**user_args):
        if not os.path.exists(user_args[UserArgs.INPUT.value]) or not os.path.isdir(user_args[UserArgs.INPUT.value]):
            raise ValueError("Invalid value in input ")

    @staticmethod
    def discover_jobs(**user_args) -> typing.List[dict]:
        jobs = []

        def filter_bib_id_folders(item: os.DirEntry):

            if not item.is_dir():
                return False

            if not isinstance(eval(item.name), int):
                return False

            return True

        for folder in filter(filter_bib_id_folders, os.scandir(user_args[UserArgs.INPUT.value])):
            jobs.append({
                JobValues.BIB_ID.value: folder.name,
                JobValues.PATH.value: folder.path
            })
        return jobs

    @staticmethod
    def get_user_options() -> typing.List[tool_options.UserOption2]:
        return [
            tool_options.UserOptionCustomDataType(UserArgs.INPUT.value, tool_options.FolderData),
        ]

    @classmethod
    def generate_report(cls, *args, **kwargs):
        user_args = kwargs['user_args']
        results = kwargs['results']
        failed = []

        for result in results:
            if not result[ResultsValues.SUCCESS.value] is True:
                failed.append(result)

        if failed:
            status = f"Warning! [{len(failed)}] packages experienced errors retrieving MARC.XML files:"
            failed_list = "\n".join([f"  * {i[ResultsValues.BIB_ID.value]}" for i in failed])

            message = f"{status}" \
                      f"\n" \
                      f"\n{failed_list}"
        else:
            message = f"Success! [{len(results)}] MARC.XML files were retrieved and written to their named folders"

        return message


class MarcGenerator(ProcessJob):

    def process(self, *args, **kwargs):
        out_file_name = "MARC.XML"
        bib_id = kwargs[JobValues.BIB_ID.value]
        folder = kwargs[JobValues.PATH.value]
        dst = os.path.normpath(os.path.join(folder, out_file_name))

        self.log(f"Retrieving {out_file_name} for {bib_id}")
        try:
            marc = pygetmarc.get_marc(int(bib_id))

            with open(dst, "w", encoding="utf-8-sig") as f:
                f.write(f"{marc}\n")
            self.log(f"Generated {dst}")
            success = True
        except ValueError as e:
            self.log(f"Error! Could not retrieve {out_file_name} for {bib_id}")
            success = False

        self.result = {
            ResultsValues.BIB_ID.value: bib_id,
            ResultsValues.SUCCESS.value: success
        }

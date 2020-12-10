import abc
import os
import re
from typing import List, Any, Optional

import requests

from speedwagon import tasks, reports
from speedwagon.job import AbsWorkflow

from uiucprescon import pygetmarc
from . import shared_custom_widgets as options


class GenerateMarcXMLFilesWorkflow(AbsWorkflow):
    name = "Generate MARC.XML Files"
    description = "For input, this tool takes a path to a directory of " \
                  "files, each of which is a digitized volume, and is named " \
                  "for that volume’s bibid. The program then retrieves " \
                  "MARC.XML files for these bibId's and writes them into " \
                  "the folder for each corresponding bibid. It uses the " \
                  "UIUC Library’s GetMARC service " \
                  "(http://quest.library.illinois.edu/GetMARC/) to " \
                  "retrieve these MARC.XML files from the Library’s catalog."

    def user_options(self):

        workflow_options = [
            options.UserOptionCustomDataType("Input", options.FolderData)
        ]
        id_type_option = options.ListSelection("Identifier type")
        for id_type in SUPPORTED_IDENTIFIERS.keys():
            id_type_option.add_selection(id_type)
        return workflow_options

    @classmethod
    def filter_bib_id_folders(cls, item: os.DirEntry):

        if not item.is_dir():
            return False

        if "v" not in item.name and not isinstance(eval(item.name), int):
            return False

        return True

    def discover_task_metadata(self, initial_results: List[Any],
                               additional_data, **user_args) -> List[dict]:
        jobs = []

        for folder in filter(self.filter_bib_id_folders,
                             os.scandir(user_args["Input"])):

            jobs.append({
                "identifier": {
                    "value": folder.name,
                    "type": user_args['Identifier type'],
                },
                "path": folder.path
            })
        return jobs

    @staticmethod
    def validate_user_options(**user_args):
        if not os.path.exists(user_args["Input"]) \
                or not os.path.isdir(user_args["Input"]):

            raise ValueError("Invalid value in input ")

    def create_new_task(self, task_builder: tasks.TaskBuilder, **job_args):
        identifier = job_args['identifier']["value"]
        identifier_type = job_args['identifier']["type"]

        folder = job_args["path"]
        new_task = MarcGenerator2Task(
            identifier=identifier,
            identifier_type=identifier_type,
            output_name=os.path.join(folder, "MARC.XML")
        )

        task_builder.add_subtask(new_task)

    @classmethod
    @reports.add_report_borders
    def generate_report(cls, results: List[tasks.Result],
                        **user_args) -> Optional[str]:
        all_results = [i.data for i in results]
        failed = []

        for result in all_results:
            if not result["Input"] is True:
                failed.append(result)

        if failed:

            status = f"Warning! [{len(failed)}] packages experienced errors " \
                     f"retrieving MARC.XML files:"

            failed_list = "\n".join(
                [f"  * {i['bib_id']}" for i in failed])

            message = f"{status}" \
                      f"\n" \
                      f"\n{failed_list}"
        else:

            message = f"Success! [{len(all_results)}] MARC.XML files were " \
                      f"retrieved and written to their named folders"

        return message


class AbsMarcFileStrategy(abc.ABC):
    @abc.abstractmethod
    def get_record(self, ident) -> str:
        pass


class GetMarcBibId(AbsMarcFileStrategy):
    def get_record(self, ident) -> str:
        # todo: get a marc record from the new server using bibid
        pass


class GetMarcMMSID(AbsMarcFileStrategy):
    def get_record(self, ident) -> str:
        r = requests.get(
            f"https://getmarc.library.illinois.edu/api/record?mms_id={ident}"
        )
        r.raise_for_status()
        return r.text

#
# class OldStyleMarc(AbsMarcFileStrategy):
#
#     def get_record(self, ident) -> str:
#         marc = pygetmarc.get_marc(int(ident))
#
#         field_adder = pygetmarc.modifiers.Add955()
#         field_adder.bib_id = ident
#         if "v" in ident:
#             field_adder.contains_v = True
#
#         enriched_marc = field_adder.enrich(src=marc)
#
#         reflow_modifier = pygetmarc.modifiers.Reflow()
#         return reflow_modifier.enrich(enriched_marc)
#

def strip_volume(full_bib_id: str) -> int:
    # Only pull the base bib id
    volume_regex = re.compile("^[0-9]{7}(?=((v[0-9]*)((i[0-9])?)?)?$)")
    result = volume_regex.match(full_bib_id)
    if not result:
        raise ValueError("{} is not a valid bib_id".format(full_bib_id))
    return int(result.group(0))


SUPPORTED_IDENTIFIERS = {
    "MMS ID": GetMarcMMSID(),
    "Bibid": GetMarcBibId()
}


class MarcGenerator2Task(tasks.Subtask):

    def __init__(self, identifier, identifier_type, output_name):
        super().__init__()
        self._identifier = identifier
        self._identifier_type = identifier_type
        self._output_name = output_name

    def work(self) -> bool:
        strat = SUPPORTED_IDENTIFIERS[self._identifier_type]
        r = strat.get_record(self._identifier)

        with open(self._output_name, "w") as wf:
            wf.write(r)
        self.set_results({
            "Input": "d",
            "bib_id": "d",
            "output": self._output_name
        })
        return True

#
# class MarcGeneratorTask(tasks.Subtask):
#
#     def __init__(self, bib_id, folder) -> None:
#         super().__init__()
#         self._bib_id = bib_id
#         self._folder = folder
#
#     def work(self) -> bool:
#         out_file_name = "MARC.XML"
#
#         dst = os.path.normpath(os.path.join(self._folder, out_file_name))
#
#         self.log(f"Retrieving {out_file_name} for {self._bib_id}")
#         try:
#             marc_retriever = OldStyleMarc()
#
#             # short_bibid = strip_volume(self._bib_id)
#             # marc = pygetmarc.get_marc(int(short_bibid))
#             #
#             # field_adder = pygetmarc.modifiers.Add955()
#             # field_adder.bib_id = self._bib_id
#             # if "v" in self._bib_id:
#             #     field_adder.contains_v = True
#             #
#             # enriched_marc = field_adder.enrich(src=marc)
#             #
#             # reflow_modifier = pygetmarc.modifiers.Reflow()
#             # cleaned_up_marc = reflow_modifier.enrich(enriched_marc)
#             cleaned_up_marc = marc_retriever.get_record(self._bib_id)
#             with open(dst, "w", encoding="utf-8-sig") as f:
#                 f.write(f"{cleaned_up_marc}\n")
#             self.log(f"Generated {dst}")
#             success = True
#         except ValueError:
#             self.log(f"Error! Could not retrieve "
#                      f"{out_file_name} for {self._bib_id}")
#
#             success = False
#
#         result = {
#             "bib_id": self._bib_id,
#             "Input": success
#         }
#         self.set_results(result)
#
#         return True

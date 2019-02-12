import os
from typing import List, Any, Optional

from speedwagon import tasks, reports
from speedwagon.tools import options
from speedwagon.job import AbsWorkflow

from uiucprescon import pygetmarc


class GenerateMarcXMLFilesWorkflow(AbsWorkflow):
    name = "0 EXPERIMENTAL " \
           "Generate MARC.XML Files"
    description = "For input, this tool takes a path to a directory of " \
                  "files, each of which is a digitized volume, and is named " \
                  "for that volume’s bibid. The program then retrieves " \
                  "MARC.XML files for these bibIDs and writes them into the " \
                  "folder for each corresponding bibID. It uses the UIUC " \
                  "Library’s GetMARC service " \
                  "(http://quest.library.illinois.edu/GetMARC/) to retrieve " \
                  "these MARC.XML files from the Library’s catalog. "

    def user_options(self):
        return [
            options.UserOptionCustomDataType("Input",
                                             options.FolderData),
        ]

    def discover_task_metadata(self, initial_results: List[Any],
                               additional_data, **user_args) -> List[dict]:
        jobs = []

        def filter_bib_id_folders(item: os.DirEntry):

            if not item.is_dir():
                return False

            if not isinstance(eval(item.name), int):
                return False

            return True

        for folder in filter(filter_bib_id_folders,
                             os.scandir(user_args["Input"])):

            jobs.append({
                "bib_id": folder.name,
                "path": folder.path
            })
        return jobs

    @staticmethod
    def validate_user_options(**user_args):
        if not os.path.exists(user_args["Input"]) \
                or not os.path.isdir(user_args["Input"]):

            raise ValueError("Invalid value in input ")

    def create_new_task(self, task_builder: tasks.TaskBuilder, **job_args):
        bib_id = job_args["bib_id"]
        folder = job_args["path"]
        new_task = MarcGeneratorTask(bib_id, folder)

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


class MarcGeneratorTask(tasks.Subtask):

    def __init__(self, bib_id, folder) -> None:
        super().__init__()
        self._bib_id = bib_id
        self._folder = folder

    def work(self) -> bool:
        out_file_name = "MARC.XML"

        dst = os.path.normpath(os.path.join(self._folder, out_file_name))

        self.log(f"Retrieving {out_file_name} for {self._bib_id}")
        try:
            marc = pygetmarc.get_marc(int(self._bib_id))

            field_adder = pygetmarc.modifiers.Add955()
            field_adder.bib_id = self._bib_id

            enriched_marc = field_adder.enrich(src=marc)

            reflow_modifier = pygetmarc.modifiers.Reflow()
            cleaned_up_marc = reflow_modifier.enrich(enriched_marc)

            with open(dst, "w", encoding="utf-8-sig") as f:
                f.write(f"{cleaned_up_marc}\n")
            self.log(f"Generated {dst}")
            success = True
        except ValueError:
            self.log(f"Error! Could not retrieve "
                     f"{out_file_name} for {self._bib_id}")

            success = False

        result = {
            "bib_id": self._bib_id,
            "Input": success
        }
        self.set_results(result)

        return True

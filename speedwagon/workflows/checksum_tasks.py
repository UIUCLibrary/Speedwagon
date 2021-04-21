import os

from pyhathiprep import checksum

import speedwagon
from speedwagon import tasks
from .checksum_shared import ResultsValues


class MakeChecksumTask(tasks.Subtask):

    def __init__(
            self,
            source_path: str,
            filename: str,
            checksum_report: str
    ) -> None:
        super().__init__()
        self._source_path = source_path
        self._filename = filename
        self._checksum_report = checksum_report

    def work(self) -> bool:
        item_path = self._source_path
        item_file_name = self._filename
        report_path_to_save_to = self._checksum_report
        self.log(f"Calculated the checksum for {item_file_name}")

        file_to_calculate = os.path.join(item_path, item_file_name)
        result = {
            ResultsValues.SOURCE_FILE: item_file_name,
            ResultsValues.SOURCE_HASH: checksum.calculate_md5_hash(
                file_to_calculate),
            ResultsValues.CHECKSUM_FILE: report_path_to_save_to

        }
        self.set_results(result)

        return True


class MakeCheckSumReportTask(speedwagon.tasks.Subtask):

    def __init__(
            self,
            output_filename: str,
            checksum_calculations
    ) -> None:
        super().__init__()
        self._output_filename = output_filename
        self._checksum_calculations = checksum_calculations

    def work(self) -> bool:

        report_builder = checksum.HathiChecksumReport()
        for item in self._checksum_calculations:
            filename = item[ResultsValues.SOURCE_FILE]
            hash_value = item[ResultsValues.SOURCE_HASH]
            report_builder.add_entry(filename, hash_value)
        report = report_builder.build()

        with open(self._output_filename, "w", encoding="utf-8") as write_file:
            write_file.write(report)
        self.log("Wrote {}".format(self._output_filename))

        return True

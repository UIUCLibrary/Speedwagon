import io
import os

from typing import List, Any, Optional, Iterator
import contextlib
import speedwagon
from speedwagon import tasks
from speedwagon.tools import options as tool_options

from uiucprescon import ocr


def locate_tessdata() -> str:
    path = os.path.join(os.path.dirname(__file__), "tessdata")
    return os.path.normpath(path)


class OCRWorkflow(speedwagon.Workflow):
    name = "Generate OCR Files"
    description = \
        "Create OCR text files for images. \n" \
        "\n" \
        "Settings: \n" \
        "    Path: Path containing tiff or jp2 files. \n" \
        "    Image File Type: The type of Image file to use.\n" \
        "\n" \
        "\n" \
        "Adding Additional Languages:\n" \
        "    To modify the available languages, place Tesseract traineddata " \
        f"files for version {ocr.Engine(locate_tessdata()).get_version()} " \
        "into the following directory:\n" \
        "\n" \
        f"{locate_tessdata()}.\n" \
        "\n" \
        "Note:\n" \
        "    It's important to use the correct version of the traineddata " \
        "files. Using incorrect versions won't crash the program but they " \
        "may produce unexpected results.\n"\
        "\n" \
        "For more information about these files, go to " \
        "https://github.com/tesseract-ocr/tesseract/wiki/Data-Files\n"

    SUPPORTED_IMAGE_TYPES = {
        "JPEG 2000": ".jp2",
        "TIFF": ".tif"
    }

    def discover_task_metadata(self, initial_results: List[Any],
                               additional_data, **user_args) -> List[dict]:

        new_tasks = []

        for result in initial_results:
            for image_file in result.data:
                image_path = os.path.dirname(image_file)
                base_name = os.path.splitext(os.path.basename(image_file))[0]
                ocr_file_name = "{}.txt".format(base_name)

                new_task = {
                    "source_file_path": image_file,
                    "destination_path": image_path,
                    "output_file_name": ocr_file_name,
                    "lang_code": user_args["Language"]
                }
                new_tasks.append(new_task)
        return new_tasks

    def create_new_task(self, task_builder: tasks.TaskBuilder, **job_args):
        image_file = job_args["source_file_path"]
        destination_path = job_args["destination_path"]
        ocr_file_name = job_args["output_file_name"]
        lang_code = job_args["lang_code"]

        task_builder.add_subtask(
            GenerateOCRFileTask(
                source_image=image_file,
                out_text_file=os.path.join(destination_path, ocr_file_name),
                lang=lang_code
            )
        )

    def initial_task(self, task_builder: tasks.TaskBuilder,
                     **user_args) -> None:

        root = user_args['Path']
        file_type = user_args["Image File Type"]
        file_extension = self.get_file_extension(file_type)

        task_builder.add_subtask(
            FindImagesTask(root, file_extension=file_extension)
        )

    @classmethod
    def get_file_extension(cls, file_type: str) -> str:
        return cls.SUPPORTED_IMAGE_TYPES[file_type]

    def user_options(self):
        options = []

        package_type = tool_options.ListSelection("Image File Type")
        for file_type in OCRWorkflow.SUPPORTED_IMAGE_TYPES.keys():
            package_type.add_selection(file_type)
        options.append(package_type)

        language_type = tool_options.ListSelection("Language")

        for lang in self.get_available_languages(path=locate_tessdata()):

            language_type.add_selection(lang)
        options.append(language_type)

        package_root_option = tool_options.UserOptionCustomDataType(
            "Path", tool_options.FolderData)

        options.append(package_root_option)

        return options

    @staticmethod
    def get_available_languages(path) -> Iterator[str]:

        def filter_only_trainingdata(item: os.DirEntry)->bool:
            if not item.is_file():
                return False

            base, ext = os.path.splitext(item.name)

            if ext != ".traineddata":
                return False

            if base == "osd":
                return False

            return True

        for f in filter(filter_only_trainingdata, os.scandir(path)):
            yield(os.path.splitext(f.name)[0])

    @staticmethod
    def validate_user_options(**user_args):
        path = user_args["Path"]
        if path is None:
            raise ValueError("No path selected")
        if not os.path.exists(path):
            raise ValueError("Unable to locate {}.".format(path))

        if not os.path.isdir(path):
            raise ValueError(
                "Input not a valid directory {}.".format(path))

    @classmethod
    def generate_report(cls, results: List[tasks.Result],
                        **user_args) -> Optional[str]:
        amount = len(cls._get_ocr_tasks(results))

        report = \
            "*************************************\n" \
            "Report\n" \
            "*************************************\n" \
            "Completed generating OCR {} files.\n" \
            "\n" \
            "*************************************\n" \
            "Done\n".format(amount)
        return report

    @staticmethod
    def _get_ocr_tasks(results: List[tasks.Result]) -> List[tasks.Result]:

        def filter_ocr_gen_tasks(result: tasks.Result) -> bool:
            if result.source != GenerateOCRFileTask:
                return False
            return True

        return [r for r in filter(filter_ocr_gen_tasks, results)]


class FindImagesTask(speedwagon.tasks.Subtask):

    def __init__(self, root, file_extension) -> None:
        super().__init__()
        self._root = root
        self._extension = file_extension

    def work(self) -> bool:
        self.log("Locating {} files in {}".format(self._extension, self._root))

        def find_images(file_located: str):

            if os.path.isdir(file_located):
                return False

            base, ext = os.path.splitext(file_located)
            if ext.lower() != self._extension:
                return False

            return True

        directories = []

        for root, dirs, files in os.walk(self._root):
            for file_name in filter(find_images, files):
                file_path = os.path.join(root, file_name)
                self.log(f"Located {file_path}")
                directories.append(file_path)
        self.set_results(directories)

        return True


class GenerateOCRFileTask(speedwagon.tasks.Subtask):
    engine = ocr.Engine(locate_tessdata())

    def __init__(self, source_image, out_text_file, lang="eng") -> None:
        super().__init__()
        # print(self.engine.get_version())
        self._source = source_image
        self._output_text_file = out_text_file
        # Use the english language file for now
        self._lang = lang

    def work(self) -> bool:
        # Get the ocr text reader for the proper language
        reader = GenerateOCRFileTask.engine.get_reader(self._lang)
        self.log("Reading {}".format(self._source))

        f = io.StringIO()

        with contextlib.redirect_stderr(f):
            # Capture the warning messages
            resulting_text = reader.read(self._source)

        stderr_messages = f.getvalue()
        if stderr_messages:
            # Log any error messages
            self.log(stderr_messages.strip())

        # Generate a text file from the text data extracted from the image
        self.log("Writing to {}".format(self._output_text_file))
        with open(self._output_text_file, "w", encoding="utf8") as wf:
            wf.write(resulting_text)

        result = {
            "text": resulting_text,
            "source": self._source
        }
        self.set_results(result)
        return True

"""Generating MARC XML files by retrieving from a server."""

# pylint: disable=too-few-public-methods
import abc
import os
import re
from copy import deepcopy
from typing import List, Any, Optional, Union, Sequence, Dict, Set, Tuple, \
    Iterator
from xml.dom import minidom
import xml.etree.ElementTree as ET
import requests


from speedwagon.exceptions import MissingConfiguration, SpeedwagonException
from speedwagon import tasks, reports, validators
from speedwagon.job import AbsWorkflow
from . import shared_custom_widgets as options

UserOptions = Union[options.UserOptionCustomDataType, options.ListSelection]
MMSID_PATTERN = \
    re.compile(r"^(?P<identifier>99[0-9]*(122)?05899)(_(?P<volume>[0-1]*))?")

BIBID_PATTERN = re.compile(r"^(?P<identifier>[0-9]*)")


class GenerateMarcXMLFilesWorkflow(AbsWorkflow):
    """Generate Marc XML files.

    .. versionchanged:: 0.1.5
        No longer use http://quest.library.illinois.edu/GetMARC. Instead uses a
        getmarc api server that is configured with getmarc_server_url global
        setting.

        Identifier type is selected by the user

    .. versionadded:: 0.1.5
        Supports MMSID id type
        Supports adding 955 field
    """

    name = "Generate MARC.XML Files"
    description = "For input, this tool takes a path to a directory of " \
                  "files, each of which is a digitized volume, and is named " \
                  "for that volume’s bibid. The program then retrieves " \
                  "MARC.XML files for these bibId's and writes them into " \
                  "the folder for each corresponding bibid or mmsid. It " \
                  "uses the GetMARC service to retrieve these MARC.XML " \
                  "files from the Library."
    required_settings_keys: Set[str] = {"getmarc_server_url"}

    def __init__(
            self,
            global_settings: Optional[Dict[str, str]] = None
    ) -> None:
        """Generate Marc XML files.

        Args:
            global_settings:
                Settings that could affect the way the workflow runs.
        """
        super().__init__()

        if global_settings is not None:
            self.global_settings = global_settings
        for k in GenerateMarcXMLFilesWorkflow.required_settings_keys:
            value = self.global_settings.get(k)
            if value is None:
                raise MissingConfiguration("Missing value for {}".format(k))

    def user_options(self) -> List[UserOptions]:
        """Get the settings presented to the user."""
        workflow_options: List[UserOptions] = [
            options.UserOptionCustomDataType("Input", options.FolderData)
        ]
        id_type_option = options.ListSelection("Identifier type")
        for id_type in SUPPORTED_IDENTIFIERS:
            id_type_option.add_selection(id_type)
        workflow_options.append(id_type_option)

        # These options will all default to True
        enhancement_field_options = [
            'Add 955 field',
            'Add 035 field',
        ]
        for enhancement_field in enhancement_field_options:
            field_option = \
                options.UserOptionPythonDataType2(enhancement_field, bool)
            field_option.data = True
            workflow_options.append(field_option)

        return workflow_options

    @classmethod
    def filter_bib_id_folders(cls, item: os.DirEntry):

        if not item.is_dir():
            return False

        if "v" not in item.name and not isinstance(eval(item.name), int):
            return False

        return True

    def discover_task_metadata(self,
                               initial_results: Sequence[Any],
                               additional_data, **user_args
                               ) -> List[Dict[Any, Any]]:
        """Create a list of metadata that the jobs will need in order to work.

        Args:
            initial_results:
            additional_data:
            **user_args:

        Returns:
            list of dictionaries of job metadata

        """
        jobs = []
        server_url = self.global_settings.get("getmarc_server_url")
        if server_url is None:
            raise MissingConfiguration("getmarc_server_url")

        for folder in filter(self.filter_bib_id_folders,
                             os.scandir(user_args["Input"])):
            jobs.append({
                "directory": {
                    "value": folder.name,
                    "type": user_args['Identifier type'],
                },
                "enhancements": {
                    "955": user_args.get("Add 955 field", False)
                },
                "api_server": server_url,
                "path": folder.path
            })
        return jobs

    @staticmethod
    def validate_user_options(**user_args: Dict[str, str]) -> None:
        """Make sure that the options the user provided is valid.

        Args:
            **user_args:

        """
        option_validators = validators.OptionValidator()
        option_validators.register_validator(
            key='Input',
            validator=validators.DirectoryValidation(key="Input")
        )
        option_validators.register_validator(
            key="Input Required",
            validator=RequiredValueValidation(key="Input")
        )
        option_validators.register_validator(
            key="Identifier type Required",
            validator=RequiredValueValidation(key="Identifier type")
        )
        option_validators.register_validator(
            key="Match 035 and 955",
            validator=DependentTruthyValueValidation(
                key='Add 035 field',
                required_true_keys=[
                    'Add 955 field'
                ]
            )
        )

        invalid_messages = []
        for validation in [
            option_validators.get("Input"),
            option_validators.get("Input Required"),
            option_validators.get("Identifier type Required"),
            option_validators.get('Match 035 and 955')
        ]:
            if not validation.is_valid(**user_args):
                invalid_messages.append(validation.explanation(**user_args))

        if len(invalid_messages) > 0:
            raise ValueError("\n".join(invalid_messages))

    def create_new_task(
            self,
            task_builder: tasks.TaskBuilder,
            **job_args
    ) -> None:
        """Create the task to be run.

        Args:
            task_builder:
            **job_args:

        """
        identifier_type = job_args['directory']["type"]
        subdirectory = job_args['directory']["value"]
        identifier, _ = self._get_identifier_volume(job_args)

        folder = job_args["path"]
        marc_file = os.path.join(folder, "MARC.XML")
        task_builder.add_subtask(
            MarcGeneratorTask(
                identifier=identifier,
                identifier_type=identifier_type,
                output_name=marc_file,
                server_url=job_args['api_server']
            )
        )

        enhancements = job_args.get('enhancements')
        if enhancements is not None:
            add_955 = enhancements.get('955')
            if add_955:
                task_builder.add_subtask(
                    MarcEnhancement955Task(
                        added_value=subdirectory,
                        xml_file=marc_file
                    )
                )
            add_035 = enhancements.get('035')
            if add_035:
                task_builder.add_subtask(
                    MarcEnhancement035Task(
                        xml_file=marc_file
                    )
                )

    @classmethod
    @reports.add_report_borders
    def generate_report(cls, results: List[tasks.Result],
                        **user_args) -> Optional[str]:
        """Generate a simple home-readable report from the job results.

        Args:
            results:
            **user_args:

        Returns:
            str: optional report as a string

        """
        all_results = [i.data for i in results]
        failed = []

        for result in all_results:
            if not result["success"] is True:
                failed.append(result)

        if failed:

            status = f"Warning! [{len(failed)}] packages experienced errors " \
                     f"retrieving MARC.XML files:"

            failed_list = "\n".join([
                f"  * {i['identifier']}. Reason: {i['output']}" for i in failed
            ])

            message = f"{status}" \
                      f"\n" \
                      f"\n{failed_list}"
        else:

            message = f"Success! [{len(all_results)}] MARC.XML files were " \
                      f"retrieved and written to their named folders"

        return message

    @staticmethod
    def _get_identifier_volume(job_args) -> Tuple[str, Union[str, None]]:
        directory = job_args['directory']
        subdirectory = directory['value']
        regex_patterns: Dict[str, re.Pattern] = {
            "MMS ID": MMSID_PATTERN,
            "Bibid": BIBID_PATTERN
        }
        regex_pattern = regex_patterns.get(directory['type'])
        if regex_pattern is None:
            raise SpeedwagonException(
                f"No identifier pattern for {directory['type']}"
            )
        match = regex_pattern.match(subdirectory)
        if match is None:
            raise SpeedwagonException(
                f"Directory does not match expected format for "
                f"{directory['type']}: {subdirectory}"
            )
        results = match.groupdict()
        return results['identifier'], results.get('volume')


class AbsMarcFileStrategy(abc.ABC):
    """Base class for retrieving MARC records from a server."""

    def __init__(self, server_url: str) -> None:
        """Use as the base class for retrieving MARC records from a server.

        Args:
            server_url: url to server

        """
        self.url = server_url

    @abc.abstractmethod
    def get_record(self, ident: str) -> str:
        """Retrieve a record type.

        Args:
            ident: Identifier uses for the record

        Returns:
            str: Record requested as a string

        """


class DependentTruthyValueValidation(validators.AbsOptionValidator):

    def __init__(self, key: str, required_true_keys: List[str]) -> None:
        super().__init__()
        self.key = key
        self.required_true_keys = required_true_keys

    @staticmethod
    def _has_required_key(user_data, key) -> bool:
        return key not in user_data

    @staticmethod
    def _requirement_is_also_true(key: bool, dependents: List[bool]) -> bool:
        # If the first part is false, there is no reason to check the rest
        if key is False:
            return True

        if not all(dependents):
            return False
        return True

    def is_valid(self, **user_data: Any) -> bool:
        for required_key in ['Add 955 field', 'Add 035 field']:
            if self._has_required_key(user_data, required_key):
                return False
        if self._requirement_is_also_true(user_data['Add 035 field'], [
            user_data['Add 955 field']
        ]) is False:
            return False
        return True

    def explanation(self, **user_data: Any) -> str:
        if self._requirement_is_also_true(
                user_data['Add 035 field'],
                [
                    user_data['Add 955 field']
                ]
        ) is False:
            return "Add 035 field requires Add 955 field"
        return "ok"


class RequiredValueValidation(validators.AbsOptionValidator):

    def __init__(self, key) -> None:
        super().__init__()
        self.key = key

    @staticmethod
    def _has_key(user_data, key) -> bool:
        return key in user_data.keys()

    @staticmethod
    def _is_not_none(user_data, key) -> bool:
        return user_data[key] is not None

    @staticmethod
    def _not_empty_str(user_data, key) -> bool:
        return str(user_data[key]).strip() != ""

    def is_valid(self, **user_data: Any) -> bool:
        return all(
            [
                self._has_key(user_data, self.key),
                self._is_not_none(user_data, self.key),
                self._not_empty_str(user_data, self.key),
            ]
        )

    def explanation(self, **user_data: Any) -> str:
        if self._has_key(user_data, self.key) is False:
            return f"Missing key {self.key}"

        if any([
            self._is_not_none(user_data, self.key) is False,
            self._not_empty_str(user_data, self.key) is False
        ]):
            return f"Missing {self.key}"

        return "ok"


class GetMarcBibId(AbsMarcFileStrategy):
    """Retrieve an record based on bibid."""

    def get_record(self, ident: str) -> str:
        """Retrieve an record based on bibid.

        Args:
            ident: bibid

        Returns:
            str: Record requested as a string

        """
        record = requests.get(
            f"{self.url}/api/record?bib_id={ident}"
        )
        record.raise_for_status()
        return record.text


class GetMarcMMSID(AbsMarcFileStrategy):
    """Retrieve an record based on MMSID."""

    def get_record(self, ident: str) -> str:
        """Retrieve an record based on MMSID.

        Args:
            ident: MMSID

        Returns:
            str: Record requested as a string

        """
        record = requests.get(
            f"{self.url}/api/record?mms_id={ident}"
        )
        record.raise_for_status()
        return record.text


def strip_volume(full_bib_id: str) -> int:
    # Only pull the base bib id
    volume_regex = re.compile("^[0-9]{7}(?=((v[0-9]*)((i[0-9])?)?)?$)")
    result = volume_regex.match(full_bib_id)
    if not result:
        raise ValueError("{} is not a valid bib_id".format(full_bib_id))
    return int(result.group(0))


SUPPORTED_IDENTIFIERS = {
    "MMS ID": GetMarcMMSID,
    "Bibid": GetMarcBibId
}


class MarcGeneratorTask(tasks.Subtask):
    """Task for generating the MARC xml file."""

    def __init__(self,
                 identifier: str,
                 identifier_type: str,
                 output_name: str,
                 server_url: str) -> None:
        """Task for retrieving the data from the server and saving as a file.

        Args:
            identifier: id of the record
            identifier_type: type of identifier used
            output_name: file name to save the data to
            server_url: getmarc server url
        """
        super().__init__()
        self._identifier = identifier
        self._identifier_type = identifier_type
        self._output_name = output_name
        self._server_url = server_url

    @property
    def identifier_type(self):
        return self._identifier_type

    @property
    def identifier(self):
        return self._identifier

    @staticmethod
    def reflow_xml(data: str) -> str:
        """Redraw the xml data to make it more human readable.

        This includes adding newline characters

        Args:
            data: xml data as a string

        Returns:
            str: Reformatted xml data.

        """
        xml = minidom.parseString(data)
        return xml.toprettyxml()

    def work(self) -> bool:
        """Run the task.

        Returns:
            bool: True on success, False otherwise.

        Notes:
            Connection errors to the getmarc server will throw a
                SpeedwagonException.
        """
        strategy = \
            SUPPORTED_IDENTIFIERS[self._identifier_type](self._server_url)
        try:
            self.log(f"Accessing MARC record for {self._identifier}")
            record = strategy.get_record(self._identifier)
            pretty_xml = self.reflow_xml(record)
            self.write_file(data=pretty_xml)

            self.log(f"Wrote file {self._output_name}")
            self.set_results({
                "success": True,
                "identifier": self._identifier,
                "output": self._output_name
            })
            return True

        except (requests.ConnectionError, requests.HTTPError) as exception:
            self.set_results({
                "success": False,
                "identifier": self._identifier,
                "output": str(exception)
            })
            raise SpeedwagonException(
                "Trouble connecting to server getmarc"
            ) from exception

    def write_file(self, data: str) -> None:
        """Write the data to a file.

        Args:
            data: Raw string data to save

        """
        with open(self._output_name, "w") as write_file:
            write_file.write(data)


class EnhancementTask(tasks.Subtask):
    def __init__(self, xml_file) -> None:
        super().__init__()
        self.xml_file = xml_file

    def to_prety_string(self, root: ET.Element) -> str:
        ET.register_namespace('', 'http://www.loc.gov/MARC21/slim')
        flat_xml_string = \
            "\n".join([line.strip() for line in ET.tostring(
                root, encoding="unicode")
                      .split("\n")]).replace("\n", "")
        xmlstr = minidom.parseString(flat_xml_string).toprettyxml()
        return xmlstr

    def redraw_tree(
            self,
            tree: ET.ElementTree,
            *new_datafields: ET.Element
    ) -> ET.Element:

        root = tree.getroot()
        namespaces = {"marc": "http://www.loc.gov/MARC21/slim"}
        fields = list(new_datafields)
        for datafield in tree.findall(".//marc:datafield", namespaces):
            fields.append(datafield)
            root.remove(datafield)
        for field in sorted(fields, key=lambda x: int(x.attrib['tag'])):
            root.append(field)
        return root


class MarcEnhancement035Task(EnhancementTask):
    namespaces = {"marc": "http://www.loc.gov/MARC21/slim"}

    @classmethod
    def find_959_field_with_uiudb(
            cls,
            tree: ET.ElementTree
    ) -> Iterator[ET.Element]:

        for datafield in tree.findall(".//marc:datafield/[@tag='959']",
                                      cls.namespaces):
            for subfield in datafield:
                if "UIUdb" in subfield.text:
                    yield subfield

    @classmethod
    def has_959_field_with_uiudb(cls, tree: ET.ElementTree) -> bool:
        try:
            next(cls.find_959_field_with_uiudb(tree))
        except StopIteration:
            return False
        return True

    def new_035_field(self, data: ET.Element):

        new_datafield = ET.Element(
            '{http://www.loc.gov/MARC21/slim}datafield',
            attrib={
                'tag': "035",
                'ind1': ' ',
                'ind2': ' '
            }
        )
        new_subfield = deepcopy(data)

        new_subfield.text = \
            new_subfield.text.replace("(UIUdb)", "(UIU)Voyager")

        new_datafield.append(new_subfield)
        return new_datafield

    def work(self) -> bool:
        """Add 035 field to the file.


        if there is a 959 field, check if there is a subfield that contains
            "UIUdb".
        if not, ignore and move on.
        If there is, add a new 035 field with the same value as that 959 field
            but replace  (UIUdb) with "(UIU)Voyager"

        Returns:
            Returns True on success else returns False

        """
        tree = ET.parse(self.xml_file)
        uiudb_subfields = list(self.find_959_field_with_uiudb(tree))
        if len(uiudb_subfields) > 1:
            message = f"Not sure what to do. {self.xml_file} has " \
                      f"{len(uiudb_subfields)} 959 fields with subfields " \
                      "containing with UIUdb. Expected only one."
            raise SpeedwagonException(message)

        if len(uiudb_subfields) == 0:
            return True
        root = self.redraw_tree(tree, self.new_035_field(uiudb_subfields[0]))
        s = self.to_prety_string(root)
        with open(self.xml_file, "w") as write_file:
            write_file.write(s)
        return True


class MarcEnhancement955Task(EnhancementTask):
    def __init__(self, added_value, xml_file) -> None:
        super().__init__(xml_file)
        self.added_value = added_value

    def work(self) -> bool:
        tree = ET.parse(self.xml_file)
        root = self.enhance_tree_with_955(tree)
        with open(self.xml_file, "w") as write_file:
            write_file.write(self.to_prety_string(root))
        return True

    def enhance_tree_with_955(self, tree: ET.ElementTree) -> ET.Element:
        new_datafield = self.create_new_955_element(self.added_value)

        root = self.redraw_tree(tree, new_datafield)
        return root

    @staticmethod
    def create_new_955_element(added_value: str) -> ET.Element:
        new_datafield = ET.Element(
            '{http://www.loc.gov/MARC21/slim}datafield',
            attrib={
                'tag': "955",
                'ind1': ' ',
                'ind2': ' '
            }
        )
        new_subfield = ET.Element(
            '{http://www.loc.gov/MARC21/slim}subfield',
            attrib={"code": "b"},
        )
        new_subfield.text = added_value
        new_datafield.append(new_subfield)
        return new_datafield

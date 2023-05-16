"""Generating MARC XML files by retrieving from a server."""
from __future__ import annotations
import abc
import functools
import os
import re
import typing
from copy import deepcopy

try:  # pragma: no cover
    from typing import Final
except ImportError:  # pragma: no cover
    from typing_extensions import Final  # type: ignore


from typing import List, Any, Optional, Union, Sequence, Dict, Tuple, \
    Iterator, Collection, TYPE_CHECKING

from xml.dom import minidom
import xml.etree.ElementTree as ET
import traceback
import sys
import requests

import speedwagon
from speedwagon.exceptions import MissingConfiguration, SpeedwagonException
from speedwagon import reports, validators, workflow

if TYPE_CHECKING:
    from speedwagon.workflow import AbsOutputOptionDataType

__all__ = ['GenerateMarcXMLFilesWorkflow']


# =========================== USER OPTIONS CONSTANTS ======================== #
OPTION_955_FIELD: Final[str] = "Add 955 field"
OPTION_035_FIELD: Final[str] = "Add 035 field"
OPTION_USER_INPUT: Final[str] = "Input"
IDENTIFIER_TYPE: Final[str] = 'Identifier type'
# =========================================================================== #

MMSID_PATTERN = \
    re.compile(r"^(?P<identifier>99[0-9]*(122)?05899)(_(?P<volume>[0-1]*))?")

BIBID_PATTERN = re.compile(r"^(?P<identifier>[0-9]*)")


class GenerateMarcXMLFilesWorkflow(speedwagon.Workflow):
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

    def job_options(self) -> List[AbsOutputOptionDataType]:
        """Request user options.

        User Options include:
            * Input - path directory containing files
            * Identifier type - ID type used in file name
            * Add 955 field - Add additional 955 field to metadata
            * Add 035 field - Add additional 035 field to metadata
        """
        user_input = workflow.DirectorySelect(OPTION_USER_INPUT)

        id_type_option = workflow.ChoiceSelection(IDENTIFIER_TYPE)
        id_type_option.placeholder_text = "Select an ID Type"
        for id_type in SUPPORTED_IDENTIFIERS:
            id_type_option.add_selection(id_type)

        add_field_955 = workflow.BooleanSelect(OPTION_955_FIELD)
        add_field_955.value = True

        add_field_035 = workflow.BooleanSelect(OPTION_035_FIELD)
        add_field_035.value = True

        return [
            user_input,
            id_type_option,
            add_field_955,
            add_field_035
        ]

    @classmethod
    def filter_bib_id_folders(cls, item: os.DirEntry) -> bool:
        """Filter only folders with bibids.

        Args:
            item:

        Returns:
            True is the item is a folder with a bibid, else returns false

        """
        if not item.is_dir():
            return False

        if "v" not in item.name and not isinstance(eval(item.name), int):
            return False

        return True

    def get_marc_server(self) -> Optional[str]:
        return typing.cast(
            Optional[str],
            self.get_workflow_configuration_value('Getmarc server url')
        )

    def discover_task_metadata(
            self,
            initial_results: Sequence[Any],
            additional_data,
            **user_args: Union[str, bool]
    ) -> List[Dict[str, Union[str, Collection[str]]]]:
        """Create a list of metadata that the jobs will need in order to work.

        Args:
            initial_results:
            additional_data:
            **user_args:

        Returns:
            list of dictionaries of job metadata

        """
        server_url = self.get_marc_server()
        if server_url is None:
            raise MissingConfiguration("Getmarc server url is not set")

        return [{
            "directory": {
                "value": folder.name,
                "type": user_args[IDENTIFIER_TYPE],
            },
            "enhancements": {
                "955": user_args.get(OPTION_955_FIELD, False),
                "035": user_args.get(OPTION_035_FIELD, False)
            },
            "api_server": server_url,
            "path": folder.path
        } for folder in filter(self.filter_bib_id_folders,
                               os.scandir(user_args[OPTION_USER_INPUT]))]

    @staticmethod
    def validate_user_options(**user_args: Dict[str, str]) -> bool:
        """Make sure that the options the user provided is valid.

        Args:
            **user_args:

        """
        option_validators = validators.OptionValidator()
        option_validators.register_validator(
            key=OPTION_USER_INPUT,
            validator=validators.DirectoryValidation(key=OPTION_USER_INPUT)
        )
        option_validators.register_validator(
            key="Input Required",
            validator=RequiredValueValidation(key=OPTION_USER_INPUT)
        )
        option_validators.register_validator(
            key="Identifier type Required",
            validator=RequiredValueValidation(key=IDENTIFIER_TYPE)
        )
        option_validators.register_validator(
            key="Match 035 and 955",
            validator=DependentTruthyValueValidation(
                key=OPTION_035_FIELD,
                required_true_keys=[
                    OPTION_955_FIELD
                ]
            )
        )

        invalid_messages = [
            validation.explanation(**user_args) for validation in [
                option_validators.get(OPTION_USER_INPUT),
                option_validators.get("Input Required"),
                option_validators.get("Identifier type Required"),
                option_validators.get('Match 035 and 955')
            ] if not validation.is_valid(**user_args)]
        if invalid_messages:
            raise ValueError("\n".join(invalid_messages))
        return True

    def create_new_task(
            self,
            task_builder: "speedwagon.tasks.TaskBuilder",
            **job_args: Union[str, Dict[str, Union[str, bool]]]
    ) -> None:
        """Create the task to be run.

        Args:
            task_builder:
            **job_args:

        """
        if 'directory' not in job_args.keys():
            raise KeyError("Missing directory")
        directory = job_args.get('directory', {})
        if not isinstance(directory, dict):
            raise TypeError()
        identifier_type = str(directory["type"])
        subdirectory = str(directory["value"])
        identifier, _ = self._get_identifier_volume(job_args)

        folder = str(job_args["path"])
        marc_file = os.path.join(folder, "MARC.XML")
        task_builder.add_subtask(
            MarcGeneratorTask(
                identifier=identifier,
                identifier_type=identifier_type,
                output_name=marc_file,
                server_url=str(job_args['api_server'])
            )
        )
        enhancements = job_args.get('enhancements', {})
        if not isinstance(enhancements, dict):
            raise TypeError()

        add_955 = enhancements.get('955', False)
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
    def generate_report(cls, results: List[speedwagon.tasks.Result],
                        **user_args) -> Optional[str]:
        """Generate a simple home-readable report from the job results.

        Args:
            results:
            **user_args:

        Returns:
            str: optional report as a string

        """
        all_results = [i.data for i in results]
        failed = [
            result for result in all_results if result["success"] is not True
        ]

        if not failed:

            return f"Success! [{len(all_results)}] MARC.XML files were " \
                      f"retrieved and written to their named folders"

        status = f"Warning! [{len(failed)}] packages experienced errors " \
                 f"retrieving MARC.XML files:"

        failed_list = "\n".join(
            f"  * {i['identifier']}. Reason: {i['output']}" for i in failed
        )

        return f"{status}" \
               f"\n" \
               f"\n{failed_list}"

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

    def workflow_options(self) -> List[AbsOutputOptionDataType]:
        """Set the settings for get marc workflow.

        This needs the getmarc server url.
        """
        return [
            speedwagon.workflow.TextLineEditData(
                'Getmarc server url',
                required=True
            ),
        ]


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

    @staticmethod
    def download_record(url: str):
        """Download a marc record from the url."""
        record = requests.get(url)
        record.raise_for_status()
        return record.text


class DependentTruthyValueValidation(validators.AbsOptionValidator):
    """Validate depending optional values are checked in right order."""

    def __init__(self, key: str, required_true_keys: List[str]) -> None:
        """Create a new validation object.

        Args:
            key: Optional value, that requires the other conditions to be true.
            required_true_keys:
                Keys that also have to be true for the key argument to be also
                    true and valid.
        """
        super().__init__()
        self.key = key
        self.required_true_keys = required_true_keys

    @staticmethod
    def _has_required_key(user_data: Dict[str, Union[str, bool]],
                          key: str) -> bool:

        return key not in user_data

    @staticmethod
    def _requirement_is_also_true(key: bool, dependents: List[bool]) -> bool:
        # If the first part is false, there is no reason to check the rest
        if not key:
            return True

        if not all(dependents):
            return False
        return True

    def is_valid(self, **user_data: Union[str, bool]) -> bool:
        """Check if the user data is valid."""
        for required_key in [OPTION_955_FIELD, OPTION_035_FIELD]:
            if self._has_required_key(user_data, required_key):
                return False

        return self._requirement_is_also_true(
            bool(user_data[OPTION_035_FIELD]),
            [bool(user_data[OPTION_955_FIELD])]
        ) is not False

    def explanation(self, **user_data: Union[str, bool]) -> str:
        """Get reason for is_valid.

        Args:
            **user_data:

        Returns:
            returns a message explaining why something isn't valid, otherwise
                produce the message "ok"
        """
        if self._requirement_is_also_true(
                bool(user_data[OPTION_035_FIELD]),
                [
                    bool(user_data[OPTION_955_FIELD])
                ]
        ) is False:
            return "Add 035 field requires Add 955 field"
        return "ok"


class RequiredValueValidation(validators.AbsOptionValidator):
    """Make sure the value is ignored."""

    def __init__(self, key: str) -> None:
        """Check if the key is not empty.

        Args:
            key: Key to check is being used
        """
        super().__init__()
        self.key = key

    @staticmethod
    def _has_key(user_data: Dict[str, Union[str, bool]], key: str) -> bool:
        return key in user_data

    @staticmethod
    def _is_not_none(user_data: Dict[str, Union[str, bool]], key: str) -> bool:
        return user_data[key] is not None

    @staticmethod
    def _not_empty_str(user_data: Dict[str, Union[str, bool]],
                       key: str) -> bool:
        return str(user_data[key]).strip() != ""

    def is_valid(self, **user_data: Union[str, bool]) -> bool:
        """Check if the user data is valid."""
        return all(
            [
                self._has_key(user_data, self.key),
                self._is_not_none(user_data, self.key),
                self._not_empty_str(user_data, self.key),
            ]
        )

    def explanation(self, **user_data: Union[str, bool]) -> str:
        """Get reason for is_valid.

        Args:
            **user_data:

        Returns:
            returns a message explaining why something isn't valid, otherwise
                produce the message "ok"
        """
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
        return self.download_record(f"{self.url}/api/record?bib_id={ident}")


class GetMarcMMSID(AbsMarcFileStrategy):
    """Retrieve an record based on MMSID."""

    def get_record(self, ident: str) -> str:
        """Retrieve an record based on MMSID.

        Args:
            ident: MMSID

        Returns:
            str: Record requested as a string

        """
        return self.download_record(f"{self.url}/api/record?mms_id={ident}")


def strip_volume(full_bib_id: str) -> int:
    # Only pull the base bib id
    volume_regex = re.compile("^[0-9]{7}(?=((v[0-9]*)((i[0-9])?)?)?$)")
    result = volume_regex.match(full_bib_id)
    if not result:
        raise ValueError(f"{full_bib_id} is not a valid bib_id")
    return int(result.group(0))


SUPPORTED_IDENTIFIERS = {
    "MMS ID": GetMarcMMSID,
    "Bibid": GetMarcBibId
}


class MarcGeneratorTask(speedwagon.tasks.Subtask):
    """Task for generating the MARC xml file."""

    name = "Generate MARC File"

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

    def task_description(self) -> Optional[str]:
        return f"Retrieving MARC record for {self._identifier}"

    @property
    def identifier_type(self) -> str:
        """Type of identifier.

        Such as MMS ID or BIBID
        """
        return self._identifier_type

    @property
    def identifier(self) -> str:
        """Record id."""
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
        return minidom.parseString(data).toprettyxml()

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
        except UnicodeError as error:
            raise SpeedwagonException(
                f"Error with {self._identifier}"
            ) from error
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
        try:
            with open(self._output_name, "w", encoding="utf-8") as write_file:
                write_file.write(data)
        except UnicodeError as error:
            traceback.print_exc(file=sys.stderr)
            raise SpeedwagonException from error


class EnhancementTask(speedwagon.tasks.Subtask):
    """Base class for enhancing xml file."""

    def __init__(self, xml_file: str) -> None:
        """Create a new Enchancement object for processing the xml file.

        Args:
            xml_file: Path to an XML file to process.

        """
        super().__init__()
        self.xml_file = xml_file

    def work(self) -> bool:
        raise NotImplementedError()

    def task_description(self) -> Optional[str]:
        return f"Enhancing {self.xml_file}"

    @staticmethod
    def to_pretty_string(root: ET.Element) -> str:
        """Convert lxml Element into a pretty formatted string."""
        ET.register_namespace('', 'http://www.loc.gov/MARC21/slim')
        flat_xml_string = \
            "\n".join(line.strip() for line in ET.tostring(
                    root, encoding="unicode")
                          .split("\n")).replace("\n", "")
        return str(minidom.parseString(flat_xml_string).toprettyxml())

    @staticmethod
    def redraw_tree(
            tree: ET.ElementTree,
            *new_datafields: ET.Element
    ) -> ET.Element:
        """Redraw the tree so that everything is in order."""
        root = tree.getroot()
        namespaces = {"marc": "http://www.loc.gov/MARC21/slim"}
        fields = list(new_datafields)
        for datafield in tree.findall(".//marc:datafield", namespaces):
            fields.append(datafield)
            root.remove(datafield)
        for field in sorted(fields, key=lambda x: int(x.attrib['tag'])):
            root.append(field)
        return root


def provide_info(func):
    @functools.wraps(func)
    def wrapped(task: EnhancementTask):
        try:
            return func(task)
        except Exception as error:
            raise SpeedwagonException(
                f"Problem enhancing {task.xml_file}"
            ) from error

    return wrapped


class MarcEnhancement035Task(EnhancementTask):
    """Enhancement for Marc xml by adding a 035 field."""

    namespaces = {"marc": "http://www.loc.gov/MARC21/slim"}

    @classmethod
    def find_959_field_with_uiudb(
            cls,
            tree: ET.ElementTree
    ) -> Iterator[ET.Element]:
        """Locate any 959 fields containing the text UIUdb.

        Args:
            tree:

        Yields:
            Yields subelements if found.

        """
        for datafield in tree.findall(".//marc:datafield/[@tag='959']",
                                      cls.namespaces):
            for subfield in datafield:
                if subfield.text is not None and "UIUdb" in subfield.text:
                    yield subfield

    @classmethod
    def has_959_field_with_uiudb(cls, tree: ET.ElementTree) -> bool:
        """Check if tree contains an 955 element with UIUdb.

        Args:
            tree:

        Returns:
            Returns True is found one, False if none have been found.

        """
        try:
            next(cls.find_959_field_with_uiudb(tree))
        except StopIteration:
            return False
        return True

    @staticmethod
    def new_035_field(data: ET.Element) -> ET.Element:
        """Create a new 035 Element based on the data element.

        Args:
            data: subfield of a 959 element

        Returns:
            Returns a New 035 Element.

        """
        new_datafield = ET.Element(
            '{http://www.loc.gov/MARC21/slim}datafield',
            attrib={
                'tag': "035",
                'ind1': ' ',
                'ind2': ' '
            }
        )
        new_subfield = deepcopy(data)
        if new_subfield.text is not None:
            new_subfield.text = \
                new_subfield.text.replace("(UIUdb)", "(UIU)Voyager")

        new_datafield.append(new_subfield)
        return new_datafield

    @provide_info
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

        if uiudb_subfields:
            root = self.redraw_tree(
                tree,
                self.new_035_field(uiudb_subfields[0])
            )

            with open(self.xml_file, "w", encoding="utf-8") as write_file:
                write_file.write(self.to_pretty_string(root))

        return True


class MarcEnhancement955Task(EnhancementTask):
    """Enhancement for Marc xml by adding a 955 field."""

    def __init__(self, added_value: str, xml_file: str) -> None:
        """Create a new EnhancementTask object.

        Args:
            added_value: The value added to the 955 field
            xml_file: File applied to.
        """
        super().__init__(xml_file)
        self.added_value = added_value

    @provide_info
    def work(self) -> bool:
        """Perform the enhancement.

        Returns:
            Returns True on success, False on failure

        """
        tree = ET.parse(self.xml_file)
        root = self.enhance_tree_with_955(tree)
        with open(self.xml_file, "w", encoding="utf-8") as write_file:
            write_file.write(self.to_pretty_string(root))

        return True

    def enhance_tree_with_955(self, tree: ET.ElementTree) -> ET.Element:
        """Enhance the current tree by adding a new 955 field,.

        Args:
            tree:
                XML tree

        Returns:
            Returns a new Element with the 955 field added.

        """
        new_datafield = self.create_new_955_element(self.added_value)

        return self.redraw_tree(tree, new_datafield)

    @staticmethod
    def create_new_955_element(added_value: str) -> ET.Element:
        """Create aa new 955 element.

        Args:
            added_value:
                Text to be added to the 955 subfield

        Returns:
            Returns a new 955 Elements

        """
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

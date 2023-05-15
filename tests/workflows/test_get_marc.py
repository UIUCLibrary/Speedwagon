import pytest
import os
from io import StringIO
from unittest.mock import MagicMock, Mock, mock_open, patch

import requests

import speedwagon
import speedwagon.exceptions
import xml.etree.ElementTree as ET
from speedwagon.workflows import workflow_get_marc


@pytest.fixture
def unconfigured_workflow():
    workflow = workflow_get_marc.GenerateMarcXMLFilesWorkflow()
    options_backend = Mock(get=lambda key: {"Getmarc server url": "http://fake.com"}.get(key))
    workflow.set_options_backend(options_backend)
    user_options = {i.label: i.value for i in workflow.job_options()}
    user_options['Identifier type'] = "Bibid"
    return workflow, user_options


def test_input_dir_is_valid(tmp_path, unconfigured_workflow):
    workflow, user_options = unconfigured_workflow
    test_pkg = tmp_path / "4717"
    test_pkg.mkdir()

    user_options["Input"] = str(test_pkg.resolve())
    user_options["Identifier type"] = "MMS ID"
    user_options["Add 955 field"] = False
    user_options["Add 035 field"] = False
    workflow.validate_user_options(**user_options)


def test_invalid_input_dir_raises(monkeypatch, unconfigured_workflow):
    workflow, user_options = unconfigured_workflow

    def mock_exists(path):
        return False

    def mock_isdir(path):
        return path in user_options.values()

    with monkeypatch.context() as mp:
        mp.setattr(os.path, "exists", mock_exists)
        options = {
            "Input": "./invalid_path",
            "Identifier type": "MMS ID",
            'Add 955 field': False,
            'Add 035 field': False

        }
        with pytest.raises(ValueError) as exception_info:
            workflow.validate_user_options(**options)
        assert '"./invalid_path" does not exist' in str(exception_info.value)


def test_discover_metadata(unconfigured_workflow, monkeypatch):

    workflow, user_options = unconfigured_workflow
    user_options["Identifier type"] = "MMS ID"
    workflow.filter_bib_id_folders = Mock(return_value=True)

    def get_data(*args, **kwargs):
        # name attribute can't be mocked in the constructor for Mock
        first = Mock(path="/fakepath/99101026212205899")
        first.name = "99101026212205899"

        second = Mock(path="/fakepath/99954806053105899")
        second.name = "99954806053105899"

        return [first, second]

    monkeypatch.setattr(os, 'scandir', get_data)
    workflow.global_settings["getmarc_server_url"] = "http://fake.com"
    user_options["Input"] = "/fakepath"
    jobs = workflow.discover_task_metadata([], None, **user_options)
    assert len(jobs) == 2
    assert jobs[0]['path'] == "/fakepath/99101026212205899"
    assert jobs[0]['directory']['value'] == "99101026212205899"


subdirectories = [
    ("MMS ID", "99954806053105899"),
    ("MMS ID", "99101026212205899"),
    ("MMS ID", "99101026212205899_1"),
    ("Bibid", "100")
]


@pytest.mark.parametrize("identifier_type,subdirectory", subdirectories)
def test_task_creates_file(tmp_path, monkeypatch, identifier_type,
                           subdirectory):
    expected_file = str(tmp_path / "MARC.XML")

    task = workflow_get_marc.MarcGeneratorTask(
        identifier=subdirectory,
        identifier_type=identifier_type,
        output_name=expected_file,
        server_url="fake.com"

    )

    def mock_get(*args, **kwargs):
        result = Mock(text=f"/fakepath/{subdirectory}")
        result.raise_for_status = MagicMock(return_value=None)
        return result
    monkeypatch.setattr(requests, 'get', mock_get)

    def mock_log(message):
        """Empty log"""

    monkeypatch.setattr(task, 'log', mock_log)

    task.reflow_xml = Mock(return_value="")
    task.work()
    assert os.path.exists(task.results["output"]) is True


identifier_dirs = [
    ("MMS ID", "99101026212205899", "99101026212205899", None),
    ("MMS ID", "99954806053105899", "99954806053105899", None),
    ("MMS ID", "99101026212205899_1", "99101026212205899", "1"),
    ("Bibid", "100", "100", None)
]


@pytest.mark.parametrize("identifier_type, directory, identifier, volume",
                         identifier_dirs)
def test_split_id_volumes(identifier_type, directory, identifier, volume):
    if identifier_type == "MMS ID":
        groups = workflow_get_marc.MMSID_PATTERN.match(directory).groupdict()

        assert groups.get('volume') == volume and \
               groups['identifier'] == identifier, f"Got {groups}"

    if identifier_type == "Bibid":
        groups = workflow_get_marc.BIBID_PATTERN.match(directory).groupdict()

        assert groups.get('volume') == volume and \
               groups['identifier'] == identifier


@pytest.mark.parametrize(
    "identifier_type, subdirectory, expected_identifier, expected_volume",
    identifier_dirs)
def test_identifier_splits(identifier_type, subdirectory, expected_identifier,
                           expected_volume):
    job_args = {
        'directory': {
            'value': subdirectory,
            'type': identifier_type,
        },
        'api_server': "https://www.fake.com",
        'path': "/fake/path/to/item"
    }

    actual_id, actual_volume = \
        workflow_get_marc.GenerateMarcXMLFilesWorkflow._get_identifier_volume(
            job_args=job_args)

    assert expected_identifier == actual_id
    assert expected_volume == actual_volume


def test_generate_report_success(unconfigured_workflow):
    workflow, user_options = unconfigured_workflow
    report = workflow.generate_report(
        results=[
            speedwagon.tasks.Result(None, data={
                "success": True,
                "identifier": "097"
            })
        ]
    )

    assert "Success" in report


def test_generate_report_failure(unconfigured_workflow):
    workflow, user_options = unconfigured_workflow
    report = workflow.generate_report(
        results=[
            speedwagon.tasks.Result(None, data={
                "success": False,
                "identifier": "097",
                "output": "Something bad happened"
            })
        ]
    )

    assert "Warning" in report


@pytest.mark.parametrize("identifier_type,subdirectory", subdirectories)
def test_task_logging_mentions_identifer(monkeypatch, identifier_type,
                                         subdirectory):

    task = workflow_get_marc.MarcGeneratorTask(
        identifier=subdirectory,
        identifier_type=identifier_type,
        output_name="sample_record/MARC.xml",
        server_url="fake.com"

    )

    def mock_get(*args, **kwargs):
        result = Mock(text=f"/fakepath/{subdirectory}")
        result.raise_for_status = MagicMock(return_value=None)
        return result

    monkeypatch.setattr(requests, 'get', mock_get)

    logs = []

    def mock_log(message):
        logs.append(message)
    monkeypatch.setattr(task, 'log', mock_log)

    def mock_write_file(data):
        """Stub for writing files"""
    monkeypatch.setattr(task, 'write_file', mock_write_file)

    task.reflow_xml = Mock(return_value="")
    task.work()

    for log in logs:
        if subdirectory in log:
            break
    else:
        assert False, "Expected identifier \"{}\" mentioned in log, " \
                      "found [{}]".format(subdirectory, "] [".join(logs))


@pytest.mark.parametrize("identifier_type, subdirectory, identifier, volume",
                         identifier_dirs)
def test_create_new_task(unconfigured_workflow, identifier_type,
                         subdirectory, identifier, volume):
    workflow, user_options = unconfigured_workflow
    job_args = {
        'directory': {
            'value': subdirectory,
            'type': identifier_type,
        },
        'api_server': "https://www.fake.com",
        'path': "/fake/path/to/item"
    }
    mock_task_builder = Mock()
    workflow.create_new_task(
        task_builder=mock_task_builder,
        **job_args
    )
    mock_task_builder.add_subtask.assert_called()
    assert mock_task_builder.add_subtask.call_count == 1
    call_args = mock_task_builder.add_subtask.call_args[0]
    task_generated = call_args[0]
    assert isinstance(task_generated, workflow_get_marc.MarcGeneratorTask)

    assert task_generated.identifier_type == identifier_type and \
           task_generated.identifier == identifier


def test_955_field_defaults_to_true(unconfigured_workflow):
    workflow, user_options = unconfigured_workflow
    assert user_options['Add 955 field'] is True


@pytest.mark.parametrize(
    "identifier_type, subdirectory, expected_identifier, volume",
    identifier_dirs)
def test_955_added_to_tasks(unconfigured_workflow, identifier_type,
                            subdirectory, expected_identifier, volume):

    workflow, user_options = unconfigured_workflow
    job_args = {
        'directory': {
            'value': subdirectory,
            'type': identifier_type,
        },
        "enhancements": {"955": True},
        'api_server': "https://www.fake.com",
        'path': "/fake/path/to/item"
    }
    mock_task_builder = Mock()
    workflow.create_new_task(
        task_builder=mock_task_builder,
        **job_args
    )
    mock_task_builder.add_subtask.assert_called()
    assert mock_task_builder.add_subtask.call_count == 2
    tasks_generated = mock_task_builder.add_subtask.call_args_list
    retrieval_task = tasks_generated[0][0][0]

    assert \
        isinstance(
            retrieval_task,
            workflow_get_marc.MarcGeneratorTask
        ), f"tasks_generated = {retrieval_task}"

    assert retrieval_task.identifier_type == identifier_type and \
           retrieval_task.identifier == expected_identifier

    enhancement_task = tasks_generated[1][0][0]
    assert enhancement_task.added_value == subdirectory


SAMPLE_RECORD = """<record xmlns="http://www.loc.gov/MARC21/slim" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.loc.gov/MARC21/slim http://www.loc.gov/standards/marcxml/schema/MARC21slim.xsd">
  <leader>02608cam a2200505   4500</leader>
  <controlfield tag="001">9917042712205899</controlfield>
  <controlfield tag="005">20200409221000.0</controlfield>
  <controlfield tag="008">730518s1973    nyua     b    001 0 eng  </controlfield>
  <datafield ind1=" " ind2=" " tag="010">
    <subfield code="a">73008765</subfield>
  </datafield>
  <datafield ind1=" " ind2=" " tag="019">
    <subfield code="a">976679054</subfield>
  </datafield>
  <datafield ind1=" " ind2=" " tag="020">
    <subfield code="a">0815621574</subfield>
  </datafield>
  <datafield ind1=" " ind2=" " tag="020">
    <subfield code="a">9780815621577</subfield>
  </datafield>
  <datafield ind1=" " ind2=" " tag="035">
    <subfield code="a">1703930-01carli_network</subfield>
  </datafield>
  <datafield ind1=" " ind2=" " tag="035">
    <subfield code="a">(OCoLC)ocm00640854</subfield>
    <subfield code="z">(OCoLC)976679054</subfield>
  </datafield>
  <datafield ind1=" " ind2=" " tag="035">
    <subfield code="a">(LLCdb)26116</subfield>
  </datafield>
  <datafield ind1=" " ind2=" " tag="035">
    <subfield code="a">(EXLNZ-01CARLI_NETWORK)991084484299705816</subfield>
  </datafield>
  <datafield ind1=" " ind2=" " tag="040">
    <subfield code="a">DLC</subfield>
    <subfield code="b">eng</subfield>
    <subfield code="c">DLC</subfield>
    <subfield code="d">BTCTA</subfield>
    <subfield code="d">LVB</subfield>
    <subfield code="d">OCLCG</subfield>
    <subfield code="d">CRU</subfield>
    <subfield code="d">UBY</subfield>
    <subfield code="d">NIALS</subfield>
    <subfield code="d">SAP</subfield>
    <subfield code="d">OCLCO</subfield>
    <subfield code="d">OCLCF</subfield>
    <subfield code="d">ICW</subfield>
    <subfield code="d">OCLCQ</subfield>
    <subfield code="d">OCL</subfield>
    <subfield code="d">CUC</subfield>
    <subfield code="d">MTU</subfield>
    <subfield code="d">OCLCQ</subfield>
    <subfield code="d">LLCdb</subfield>
  </datafield>
  <datafield ind1=" " ind2=" " tag="049">
    <subfield code="a">JBGA</subfield>
  </datafield>
  <datafield ind1="0" ind2="0" tag="050">
    <subfield code="a">ML960</subfield>
    <subfield code="b">.S63</subfield>
  </datafield>
  <datafield ind1="0" ind2="0" tag="082">
    <subfield code="a">788/.1/09</subfield>
  </datafield>
  <datafield ind1="1" ind2=" " tag="100">
    <subfield code="a">Smithers, Don L.,</subfield>
    <subfield code="d">1933-</subfield>
  </datafield>
  <datafield ind1="1" ind2="4" tag="245">
    <subfield code="a">The music and history of the baroque trumpet before 1721</subfield>
    <subfield code="c">[by] Don L. Smithers.</subfield>
  </datafield>
  <datafield ind1=" " ind2=" " tag="250">
    <subfield code="a">[1st ed.</subfield>
  </datafield>
  <datafield ind1=" " ind2=" " tag="260">
    <subfield code="a">Syracuse, N.Y.]</subfield>
    <subfield code="b">Syracuse University Press,</subfield>
    <subfield code="c">1973.</subfield>
  </datafield>
  <datafield ind1=" " ind2=" " tag="300">
    <subfield code="a">323 pages</subfield>
    <subfield code="b">illustrations</subfield>
    <subfield code="c">24 cm</subfield>
  </datafield>
  <datafield ind1=" " ind2=" " tag="336">
    <subfield code="a">text</subfield>
    <subfield code="b">txt</subfield>
    <subfield code="2">rdacontent</subfield>
  </datafield>
  <datafield ind1=" " ind2=" " tag="337">
    <subfield code="a">unmediated</subfield>
    <subfield code="b">n</subfield>
    <subfield code="2">rdamedia</subfield>
  </datafield>
  <datafield ind1=" " ind2=" " tag="338">
    <subfield code="a">volume</subfield>
    <subfield code="b">nc</subfield>
    <subfield code="2">rdacarrier</subfield>
  </datafield>
  <datafield ind1=" " ind2=" " tag="504">
    <subfield code="a">"An inventory of musical sources for baroque trumpet": pages 245-289.</subfield>
  </datafield>
  <datafield ind1=" " ind2=" " tag="504">
    <subfield code="a">Includes bibliographical references (pages 291-306).</subfield>
  </datafield>
  <datafield ind1="0" ind2=" " tag="505">
    <subfield code="a">Foreword / by Dr. Percy Young -- Author's preface -- The trumpet defined -- Renaissance precursors of the baroque trumpet -- Baroque European trumpet-makers and their instruments -- Trumpets and music in Italy. First developments ; The Bolognese "school" -- The trumpet "guilds" -- The trumpet music of Germany -- Trumpets and music in the Austro-Bohemian empire -- English trumpet music by contemporaries of Henry Purcell -- The trumpet music of Henry Purcell -- The baroque trumpet in France -- Post scriptum -- Appendix : an inventory of musical sources for baroque trumpet.</subfield>
  </datafield>
  <datafield ind1="0" ind2=" " tag="520">
    <subfield code="a">"An inventory of musical sources for baroque trumpet": pages 245-289.</subfield>
  </datafield>
  <datafield ind1=" " ind2=" " tag="590">
    <subfield code="a">OCLC</subfield>
    <subfield code="b">WorldCat Holdings</subfield>
  </datafield>
  <datafield ind1=" " ind2="0" tag="650">
    <subfield code="a">Trumpet</subfield>
    <subfield code="y">17th century.</subfield>
  </datafield>
  <datafield ind1=" " ind2="0" tag="650">
    <subfield code="a">Trumpet</subfield>
    <subfield code="y">18th century.</subfield>
  </datafield>
  <datafield ind1=" " ind2="0" tag="650">
    <subfield code="a">Trumpet music</subfield>
    <subfield code="x">History and criticism</subfield>
    <subfield code="y">17th century.</subfield>
  </datafield>
  <datafield ind1=" " ind2="0" tag="650">
    <subfield code="a">Trumpet music</subfield>
    <subfield code="x">History and criticism</subfield>
    <subfield code="y">18th century.</subfield>
  </datafield>
  <datafield ind1=" " ind2="6" tag="650">
    <subfield code="a">Trompette.</subfield>
  </datafield>
  <datafield ind1=" " ind2="6" tag="650">
    <subfield code="a">Trompette, Musique de</subfield>
    <subfield code="x">Histoire et critique.</subfield>
  </datafield>
  <datafield ind1=" " ind2="7" tag="650">
    <subfield code="a">Trumpet.</subfield>
    <subfield code="2">fast</subfield>
    <subfield code="0">(OCoLC)fst01158055</subfield>
  </datafield>
  <datafield ind1=" " ind2="7" tag="650">
    <subfield code="a">Trumpet music.</subfield>
    <subfield code="2">fast</subfield>
    <subfield code="0">(OCoLC)fst01158104</subfield>
  </datafield>
  <datafield ind1=" " ind2="7" tag="648">
    <subfield code="a">1600-1799</subfield>
    <subfield code="2">fast</subfield>
  </datafield>
  <datafield ind1=" " ind2="7" tag="655">
    <subfield code="a">Criticism, interpretation, etc.</subfield>
    <subfield code="2">fast</subfield>
    <subfield code="0">(OCoLC)fst01411635</subfield>
  </datafield>
  <datafield ind1="0" ind2="8" tag="776">
    <subfield code="i">Online version:</subfield>
    <subfield code="a">Smithers, Don L., 1933-</subfield>
    <subfield code="t">Music and history of the baroque trumpet before 1721.</subfield>
    <subfield code="b">[1st ed.</subfield>
    <subfield code="d">Syracuse, N.Y.] Syracuse University Press, 1973</subfield>
    <subfield code="w">(OCoLC)654544248</subfield>
  </datafield>
  <datafield ind1=" " ind2=" " tag="938">
    <subfield code="a">Baker and Taylor</subfield>
    <subfield code="b">BTCP</subfield>
    <subfield code="n">73008765 /MN/r892</subfield>
  </datafield>
  <datafield ind1=" " ind2=" " tag="959">
    <subfield code="a">(LLCdb)26116</subfield>
  </datafield>
  <datafield ind1=" " ind2=" " tag="959">
    <subfield code="a">(UIUdb)170427</subfield>
    <subfield code="9">LOCAL</subfield>
  </datafield>
  <datafield ind1=" " ind2=" " tag="994">
    <subfield code="a">92</subfield>
    <subfield code="b">JBG</subfield>
  </datafield>
</record>
"""


@pytest.mark.parametrize("identifier_type, subdirectory, identifier, volume",
                         identifier_dirs)
def test_995_enhancement_task_adds_955(identifier_type, subdirectory,
                                       identifier, volume):

    with patch('builtins.open', mock_open(read_data=SAMPLE_RECORD)) as m:
        task = workflow_get_marc.MarcEnhancement955Task(
            added_value=subdirectory,
            xml_file="dummy"
        )

        assert task.work() is True
        tree = ET.fromstring(m().write.call_args[0][0])

    ns = {"marc": "http://www.loc.gov/MARC21/slim"}
    fields = tree.findall(".//marc:datafield/[@tag='955']", ns)
    assert len(fields) == 1, "No 955 datafields found"
    subfields = fields[0].findall("marc:subfield", ns)
    assert len(subfields) == 1, "Missing subfield"
    assert subfields[0].text == subdirectory


@pytest.mark.parametrize("identifier_type, subdirectory, identifier, volume",
                         identifier_dirs)
def test_995_enhancement_task_formats_without_namespace_tags(
        tmpdir, identifier_type, subdirectory, identifier, volume):
    # dummy_xml = tmpdir / "MARC.xml"
    # with open(dummy_xml, "w") as wf:
    #     wf.write(SAMPLE_RECORD)
    with patch('builtins.open', mock_open(read_data=SAMPLE_RECORD)) as m:
        task = workflow_get_marc.MarcEnhancement955Task(
            added_value=subdirectory,
            xml_file="dummy"
        )

        assert task.work() is True
        file_text = m().write.call_args.args[0]
        file_text.startswith(
            "<ns0:"), f"File starts with <ns:0: \"{file_text[0:10]}...\""


def test_fail_on_server_connection(monkeypatch):
    task = workflow_get_marc.MarcGeneratorTask(
        identifier="99101026212205899",
        identifier_type="MMS ID",
        output_name="dummy.xml",
        server_url="http://fake.com",
    )
    task.parent_task_log_q = []

    def mock_request(*args, **kwargs):
        raise requests.exceptions.ConnectionError()

    monkeypatch.setattr(requests.sessions.Session, "request", mock_request)
    with pytest.raises(speedwagon.exceptions.SpeedwagonException):
        task.work()


def test_955_and_035_is_valid(monkeypatch, unconfigured_workflow):
    workflow, user_options = unconfigured_workflow
    user_options['Input'] = "/valid"
    user_options['Add 955 field'] = True
    user_options['Add 035 field'] = True

    def mock_exists(path):
        return path in user_options.values()

    def mock_isdir(path):
        return path in user_options.values()

    with monkeypatch.context() as mp:
        mp.setattr(os.path, "exists", mock_exists)
        mp.setattr(os.path, "isdir", mock_isdir)

        workflow.validate_user_options(**user_options)


def test_missing_Identifier_type_invalid(monkeypatch, unconfigured_workflow):
    workflow, user_options = unconfigured_workflow
    user_options['Input'] = "/valid"
    user_options['Add 955 field'] = True
    user_options['Add 035 field'] = True
    user_options["Identifier type"] = ""

    def mock_exists(path):
        return path in user_options.values()

    def mock_isdir(path):
        return path in user_options.values()

    with monkeypatch.context() as mp:
        mp.setattr(os.path, "exists", mock_exists)
        mp.setattr(os.path, "isdir", mock_isdir)

        with pytest.raises(ValueError) as exception_info:
            workflow.validate_user_options(**user_options)
        assert "Missing Identifier type" in str(exception_info.value)


def test_955_false_and_035_True_is_invalid(monkeypatch, unconfigured_workflow):
    workflow, user_options = unconfigured_workflow
    user_options['Input'] = "/valid"
    user_options['Add 955 field'] = False
    user_options['Add 035 field'] = True

    def mock_exists(path):
        return path in user_options.values()

    def mock_isdir(path):
        return path in user_options.values()

    with monkeypatch.context() as mp:
        mp.setattr(os.path, "exists", mock_exists)
        mp.setattr(os.path, "isdir", mock_isdir)
        with pytest.raises(ValueError) as exception_info:
            workflow.validate_user_options(**user_options)

        assert \
            "Add 035 field requires Add 955 field" in str(exception_info.value)


field_combos = [
    (True, False, True),
    (False, True, False),
    (False, False, True),
    (True, True, True)
]


@pytest.mark.parametrize("f955, f035, expected_valid", field_combos)
def test_955_and035(f955, f035, expected_valid,
                    monkeypatch, unconfigured_workflow):

    workflow, user_options = unconfigured_workflow
    user_options['Input'] = "/valid"
    user_options['Add 955 field'] = f955
    user_options['Add 035 field'] = f035

    def mock_exists(path):
        return path in user_options.values()

    def mock_isdir(path):
        return path in user_options.values()

    with monkeypatch.context() as mp:
        mp.setattr(os.path, "exists", mock_exists)
        mp.setattr(os.path, "isdir", mock_isdir)
        if expected_valid is False:
            with pytest.raises(ValueError):
                workflow.validate_user_options(**user_options)
        else:
            workflow.validate_user_options(**user_options)


def test_035_task_has_959():

    root = ET.parse(StringIO(SAMPLE_RECORD))
    assert \
        workflow_get_marc.MarcEnhancement035Task.has_959_field_with_uiudb(
            root
        ) is True


@pytest.mark.parametrize("identifier_type, subdirectory, identifier, volume",
                         identifier_dirs)
def test_035_enhancement_task_adds_035(monkeypatch, identifier_type,
                                       subdirectory, identifier, volume):

    with patch('builtins.open',
               mock_open(read_data=SAMPLE_RECORD)) as mock_955:

        workflow_get_marc.MarcEnhancement955Task(
            added_value=subdirectory,
            xml_file="dummy"
        ).work()

        xml_data_with_955 = mock_955().write.call_args[0][0]

    with patch('builtins.open',
               mock_open(read_data=xml_data_with_955)) as mock_035:

        task = workflow_get_marc.MarcEnhancement035Task(
            xml_file="dummy"
        )
        assert task.work() is True
        with_035_data = mock_035().write.call_args[0][0]
        tree = ET.fromstring(with_035_data)

    ns = {"marc": "http://www.loc.gov/MARC21/slim"}

    def sub_only(x) -> bool:
        return any("(UIU)Voyager" in t.text for t in x)

    fields = list(
        filter(sub_only, tree.findall(".//marc:datafield/[@tag='035']", ns))
    )

    assert len(fields) == 1, "No 035 datafields found"
    assert fields[0][0].text == '(UIU)Voyager170427'


enhancement_tasks = [
    (False, False, 1),
    (True, False, 2),
    (True, True, 3)
]


@pytest.mark.parametrize("e955, e035, expected_number_tasks_created",
                         enhancement_tasks)
def test_create_task_enhancements(
        unconfigured_workflow,
        e955: bool,
        e035: bool,
        expected_number_tasks_created: int
):

    workflow, user_options = unconfigured_workflow
    subdirectory = "99101026212205899"
    identifier_type = "MMS ID"
    job_args = {
        'directory': {
            'value': subdirectory,
            'type': identifier_type,
        },
        'api_server': "https://www.fake.com",
        'path': "/fake/path/to/item",
        "enhancements": {
            "955": e955,
            "035": e035,
        },
    }
    mock_task_builder = Mock()
    workflow.create_new_task(
        task_builder=mock_task_builder,
        **job_args
    )
    mock_task_builder.add_subtask.assert_called()
    assert mock_task_builder.add_subtask.call_count == \
           expected_number_tasks_created


sample_user_args = [
    (
        "12345", True, False,
        {
            'path': './fake/12345',
            "directory":
                {
                    'type': 'MMS ID', 'value': '12345'
                },
            'enhancements':
                {
                    '955': True
                }
        }
     ),
    (
        "12345", True, True,
        {
            'path': './fake/12345',
            "directory":
                {
                    'type': 'MMS ID', 'value': '12345'
                },
            'enhancements':
                {
                    '955': True,
                    '035': True
                }
        }
     )
]


@pytest.mark.parametrize("arg_subdir, add_955, add_035, expected",
                         sample_user_args)
def test_discover_task_metadata(monkeypatch, unconfigured_workflow, arg_subdir,
                                add_955, add_035, expected):
    workflow, user_options = unconfigured_workflow
    user_args = {
        "Input": "./fake/",
        "Add 955 field": add_955,
        "Add 035 field": add_035,
        "Identifier type": 'MMS ID'
    }

    def mock_scan_dir(root_path):
        mock_dir = Mock()
        mock_dir.name = arg_subdir
        mock_dir.path = os.path.join(root_path, arg_subdir)
        return [
            mock_dir
        ]
    with monkeypatch.context() as mp:
        mp.setattr(os, "scandir", mock_scan_dir)
        t_md = workflow.discover_task_metadata(
            initial_results=[],
            additional_data=None,
            **user_args
        )
    assert len(t_md) == 1
    actual = t_md[0]
    top_level_keys = [
        k for k, v in expected.items() if not isinstance(v, dict)
    ]
    enhancement_keys = [
        k for k, v in expected['enhancements'].items() if not isinstance(v,
                                                                         dict)
    ]
    assert \
        all([actual[x] == expected[x] for x in top_level_keys]) and \
        all([
                actual['enhancements'][x] == expected['enhancements'][x]
                for x in enhancement_keys
            ]), \
        f"Expected {expected}, Got {actual}"


def test_failing_to_parse_provides_input(monkeypatch):

    def mock_parse(filename):
        raise ET.ParseError(
            "not well-formed (invalid token): line 1, column 33"
        )

    task = workflow_get_marc.MarcEnhancement955Task(
        added_value="xxx", xml_file="dummyfile.xml"
    )
    monkeypatch.setattr(ET, "parse", mock_parse)
    with pytest.raises(speedwagon.exceptions.SpeedwagonException) as ex:
        task.work()

    assert "dummyfile.xml" in str(ex.value)


def test_reflow(monkeypatch):
    task = workflow_get_marc.MarcGeneratorTask(
        "12345",
        "MMS ID",
        "sample.xml",
        "fake.com"
    )
    workflow_get_marc.MarcGeneratorTask.log = Mock()
    task.write_file = Mock()

    def mock_get(*args, **kwargs):
        sample_requests = Mock()
        sample_requests.raise_for_status = Mock()
        sample_requests.text = SAMPLE_RECORD
        return sample_requests

    monkeypatch.setattr(requests, "get", mock_get)
    task.work()
    data = task.write_file.call_args[1]['data']
    ET.fromstring(data)


def test_catching_unicode_error(monkeypatch):
    task = workflow_get_marc.MarcGeneratorTask(
        "12345",
        "MMS ID",
        "sample.xml",
        "fake.com"
    )
    workflow_get_marc.MarcGeneratorTask.log = Mock()

    def mock_get(*args, **kwargs):
        sample_requests = Mock()
        sample_requests.raise_for_status = Mock()
        sample_requests.text = SAMPLE_RECORD
        return sample_requests

    monkeypatch.setattr(requests, "get", mock_get)
    with patch('builtins.open', Mock(side_effect=UnicodeError)):
        with pytest.raises(speedwagon.exceptions.SpeedwagonException):
            task.work()


@pytest.mark.parametrize(
    "task",
    [
        workflow_get_marc.MarcGeneratorTask(
            identifier="identifier",
            identifier_type="identifier_type",
            output_name="output_name",
            server_url="server_url"
        ),
        workflow_get_marc.EnhancementTask(xml_file="xml_file"),
        workflow_get_marc.MarcEnhancement035Task(xml_file="xml_file"),
        workflow_get_marc.MarcEnhancement955Task(
            added_value="added_value",
            xml_file="xml_file"
        )
    ]
)
def test_tasks_have_description(task):
    assert task.task_description() is not None

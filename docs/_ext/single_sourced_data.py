#! /usr/bin/env python3
# Requires Python 3.6+
# fmt: off
"""Sphinx extension for generating the rules table document."""

from copy import copy
from pathlib import Path
from re import match
from typing import Any
from typing import Dict
from typing import List
from typing import Tuple
from typing import Union

from sphinx.application import Sphinx
from sphinx.util import logging
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import nested_parse_with_titles
from sphinx.util.nodes import nodes


from docutils import statemachine  # isort: skip


# isort: split

import yaml

from ansible_navigator._version import version as __version__
from ansible_navigator.configuration_subsystem import Constants as C
from ansible_navigator.configuration_subsystem import NavigatorConfiguration
from ansible_navigator.configuration_subsystem.definitions import SettingsEntry
from ansible_navigator.utils.functions import oxfordcomma


APP = "ansible-navigator"

PARAM_HEADER = ("Name", "Description", "Settings")
PARAM_TABLE_HEADER = [
    ".. list-table:: {}",
    "  :widths: 2 3 5",
    "  :header-rows: 1",
]
RST_FIRST_ROW_ENTRY = "  * - {}"
RST_ADDITIONAL_ROW_ENTRY = "    - {}"
RST_NL_CELL_FIRST = "    - | {}"
RST_NL_IN_CELL = "      | {}"
SUBCOMMAND_TABLE_HEADER = [
    ".. list-table:: {}",
    "  :widths: 1 3 3 1",
    "  :header-rows: 1",
]


DOCS_DIR = Path(__file__).parents[1].resolve()
PROJECT_DIR = DOCS_DIR.parent

PARAMS_SCHEMA_PATH = DOCS_DIR / "param_details.yml"
TEST_SETTINGS_FIXTURE = (
    PROJECT_DIR
    / "tests"
    / "fixtures"
    / "unit"
    / "configuration_subsystem"
    / "ansible-navigator.yml"
)


logger = logging.getLogger(__name__)


def _nodes_from_rst(
    state: statemachine.State,
    rst_source: str,
) -> List[nodes.Node]:
    """Turn an RST string into a list of nodes.

    These nodes can be used in the document.

    :param state: The superclass for a docutils statemachine which contains a list or transitions
        and transition methods
    :param rst_source: The source of the RST content from which nodes will be extracted
    :returns: A list of nodes extracted from the RST content
    """
    node = nodes.Element()
    node.document = state.document
    nested_parse_with_titles(
        state=state,
        content=statemachine.ViewList(
            statemachine.string2lines(rst_source),
            source="[ansible-navigator autogenerated]",
        ),
        node=node,
    )
    return node.children


def _rst_generate_row(row: Tuple) -> List:
    """Generate a row for an RST list table.

    :param row: A tuple containing the text for the row
    :return: A list of columns containing the formatted text
    """
    data = []
    data.append(RST_FIRST_ROW_ENTRY.format(row[0]))
    for row_part in row[1:]:
        if isinstance(row_part, str):
            data.append(RST_ADDITIONAL_ROW_ENTRY.format(row_part))
        elif isinstance(row_part, tuple):
            data.append(RST_NL_CELL_FIRST.format(row_part[0]))
            for nl_cell in row_part[1:]:
                if isinstance(nl_cell, str):
                    data.append(RST_NL_IN_CELL.format(nl_cell))
                elif isinstance(nl_cell, list):
                    data.extend(nl_cell)
    return data


def _params_generate_tables(param_details: Dict) -> List:
    """Generate a table for each subcommand's settings parameters.

    :param param_details: A dictionary of the settings parameters details
    :returns: A list of tables, one each for each subcommand
    """
    tables = []
    table = copy(PARAM_TABLE_HEADER)
    table[0] = table[0].format("**General parameters**")
    table.append("")
    table.extend(_rst_generate_row(PARAM_HEADER))

    for entry in NavigatorConfiguration.entries:
        if not isinstance(entry.subcommands, list):
            row = _params_row_for_entry(
                entry=entry,
                param_details=param_details,
            )
            table.extend(_rst_generate_row(row))
    tables.extend(table)
    tables.extend(["", "|", "|", ""])
    for subcommand in NavigatorConfiguration.subcommands:
        logger.debug("Processing subcommand: %s", subcommand.name)
        entries = [
            entry
            for entry in NavigatorConfiguration.entries
            if isinstance(entry.subcommands, list)
            and subcommand.name in entry.subcommands
        ]
        logger.debug("  params %s", tuple(entry.name for entry in entries))
        if entries:
            table = copy(PARAM_TABLE_HEADER)
            table[0] = table[0].format(f"**Subcommand: {subcommand.name}**")
            table.append("")
            table.extend(_rst_generate_row(PARAM_HEADER))
            for entry in entries:
                row = _params_row_for_entry(
                    entry=entry,
                    param_details=param_details,
                )
                table.extend(_rst_generate_row(row))
            tables.extend(table)
            tables.extend(["", "|", ""])
    return tables


def _params_get_param_file_entry(
        param_details: Dict, path: str,
) -> Union[None, Dict[Any, Any]]:
    """Retrieve one settings parameter's details from settings data.

    :param param_details: The full settings data
    :param path: The dot delimited path for the settings parameter to retrieve
    :returns: The settings parameter's details if present in the data
    """
    path_parts = path.split(".")
    data = param_details
    try:
        for key in path_parts:
            data = data[key]
        return data
    except KeyError:
        return None


def _params_retrieve_details(filename: str) -> Dict:
    """Load the settings file.

    :param filename: The path to the settings file to load
    :return: The deserialized contents of the file
    """
    with open(filename, encoding="utf-8") as fh:
        return yaml.load(fh, Loader=yaml.SafeLoader)


def _params_row_for_entry(entry: SettingsEntry, param_details: Dict) -> Tuple:
    # pylint: disable=too-many-branches
    """Create a row entry for one settings parameter.

    :param entry: The settings entry for which the row will be generated
    :param param_details: The details for the settings parameter
    :return: A tuple describing the settings parameter
    """
    if entry.cli_parameters is None:
        cli_parameters = "positional"
    else:
        if entry.cli_parameters.short:
            if entry.cli_parameters.long_override:
                long = entry.cli_parameters.long_override
            else:
                long = f"--{entry.name_dashed}"
            cli_parameters = f"``{entry.cli_parameters.short}`` or ``{long}``"
        else:
            cli_parameters = "positional"

    path = entry.settings_file_path("ansible-navigator")
    yaml_like = ["", "      .. code-block:: yaml", ""]
    for idx, path_part in enumerate(path.split(".")):
        yaml_like.append(f"{(2*idx+12) * ' '}{path_part}:")
    yaml_like.append("")

    path = entry.settings_file_path(APP) + ".default-value-override"
    default_override = _params_get_param_file_entry(
        param_details=param_details,
        path=path,
    )
    logger.debug(
        "%s: default_value_override: %s",
        entry.name,
        default_override,
    )
    if isinstance(default_override, str):
        default = default_override
    else:
        if entry.value.default is C.NOT_SET:
            default = "No default value set"
        else:
            default = entry.value.default

    choices = oxfordcomma(entry.choices, "or")
    env_var = entry.environment_variable(APP.replace("-", "_"))

    settings = []
    if choices:
        settings.append(f"**Choices:** {choices}")
    if default is not None:
        settings.append(f"**Default:** {default}")
    if cli_parameters is not None:
        settings.append(f"**CLI:** {cli_parameters}")
    if env_var is not None:
        settings.append(f"**ENV:** {env_var}")

    settings.extend(["**Settings file:**", *yaml_like])

    row = (entry.name_dashed, entry.short_description, tuple(settings))
    return row


def _subcommands_generate_tables() -> List:
    """Generate the subcommand table.

    :returns: A list of available subcommands
    """
    table = SUBCOMMAND_TABLE_HEADER
    table[0] = table[0].format("Available subcommands")
    table.append("")
    table.extend(
        _rst_generate_row(
            ("Name", "Description", "CLI Example", "Colon command"),
        ),
    )
    for subcommand in NavigatorConfiguration.subcommands:
        subcommand_details = (
            subcommand.name,
            subcommand.description,
            f"ansible-navigator {subcommand.name} --help",
            f":{subcommand.name}",
        )
        table.extend(_rst_generate_row(subcommand_details))
    return table


class AnsibleNavigatorSubcommandsTableDirective(SphinxDirective):
    """Directive ``ansible-navigator-subcommands-table`` definition."""

    has_content = False

    def run(self) -> List[nodes.Node]:
        """Generate a node tree in place of the directive.

        :returns: A list of nodes generated from the RST content for the subcommands table
        """
        self.env.note_reread()  # rebuild the current RST doc unconditionally

        rst_table = "\n".join(_subcommands_generate_tables())

        return _nodes_from_rst(state=self.state, rst_source=rst_table)


class AnsibleNavigatorSettingsSampleDirective(SphinxDirective):
    """Directive ``ansible-navigator-settings-sample`` definition."""

    has_content = False

    def run(self) -> List[nodes.Node]:
        """Generate a node tree in place of the directive.

        :returns: A list of nodes generated from the RST content for the settings parameters sample
        """
        # make sphinx discard doctree cache on file changes
        self.env.note_dependency(str(TEST_SETTINGS_FIXTURE))

        sample_settings = [".. code-block:: yaml", ""]
        settings = TEST_SETTINGS_FIXTURE.read_text().splitlines()
        not_commented = ["---", "ansible-navigator:", "logging:", "level:"]
        for idx, line in enumerate(settings):
            if idx != 2 and match(r"\s{2}\S", line):
                sample_settings.append("    #")
            if not any(nc in line for nc in not_commented):
                sample_settings.append("    # " + line)
            else:
                sample_settings.append("    " + line)
        rst_yaml_block = "\n".join(sample_settings)

        return _nodes_from_rst(state=self.state, rst_source=rst_yaml_block)


class AnsibleNavigatorParametersTablesDirective(SphinxDirective):
    """Directive ``ansible-navigator-parameters-tables`` definition."""

    has_content = False

    def run(self) -> List[nodes.Node]:
        """Generate a node tree in place of the directive.

        :returns: A list of nodes generated from the RST content for all settings parameter tables
        """
        params_schema_path_str = str(PARAMS_SCHEMA_PATH)

        # make sphinx discard doctree cache on file changes
        self.env.note_dependency(params_schema_path_str)

        param_details = _params_retrieve_details(params_schema_path_str)
        tables = _params_generate_tables(param_details)
        rst_tables = "\n".join(tables)

        return _nodes_from_rst(state=self.state, rst_source=rst_tables)


def setup(app: Sphinx) -> Dict[str, Union[bool, str]]:
    """Initialize the Sphinx extension.

    :param app: An instance of sphinx
    :return: A dictionary describing the extension after populating it with directives
    """
    app.add_directive(
        "ansible-navigator-subcommands-table",
        AnsibleNavigatorSubcommandsTableDirective,
    )
    app.add_directive(
        "ansible-navigator-settings-sample",
        AnsibleNavigatorSettingsSampleDirective,
    )
    app.add_directive(
        "ansible-navigator-parameters-tables",
        AnsibleNavigatorParametersTablesDirective,
    )

    return {
        "parallel_read_safe": True,
        "parallel_write_safe": True,
        "version": f"In-tree extension in {APP} v{__version__}",
    }

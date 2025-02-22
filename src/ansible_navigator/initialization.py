"""initialization helpers that are used early in application
initialization and are specific to ansible_navigator
"""
import logging
import os
import sys

from typing import List
from typing import NoReturn
from typing import Optional
from typing import Tuple
from typing import Union

from ._version_doc_cache import __version_collection_doc_cache__ as VERSION_CDC
from .configuration_subsystem import ApplicationConfiguration
from .configuration_subsystem import Configurator
from .configuration_subsystem import Constants as C
from .utils.functions import ExitMessage
from .utils.functions import ExitPrefix
from .utils.functions import LogMessage
from .utils.functions import environment_variable_is_file_path
from .utils.functions import find_settings_file
from .utils.key_value_store import KeyValueStore


def error_and_exit_early(exit_messages: List[ExitMessage]) -> NoReturn:
    """get out of here fast"""
    for exit_msg in exit_messages:
        print(exit_msg)
    sys.exit(1)


def find_config() -> Tuple[List[LogMessage], List[ExitMessage], Optional[str], C]:
    """
    Find a configuration file, logging each step.
    Return (log messages, path).
    If the config can't be found/loaded, use default settings.
    If it's found but empty or not well formed, bail out.
    """
    messages: List[LogMessage] = []
    exit_messages: List[ExitMessage] = []
    config_path = None
    settings_source = C.NONE

    # Check if the configuration file path is set via an environment var
    cfg_env_var = "ANSIBLE_NAVIGATOR_CONFIG"
    new_messages, new_exit_messages, env_config_path = environment_variable_is_file_path(
        env_var=cfg_env_var,
        kind="config",
    )
    messages.extend(new_messages)
    exit_messages.extend(new_exit_messages)
    if exit_messages:
        return messages, exit_messages, config_path, settings_source

    # Find the setting file
    new_messages, new_exit_messages, found_config_path = find_settings_file()

    messages.extend(new_messages)
    exit_messages.extend(new_exit_messages)
    if exit_messages:
        return messages, exit_messages, config_path, settings_source

    # Pick the environment variable set first, followed by found, followed by leave as none
    if env_config_path is not None:
        config_path = env_config_path
        settings_source = C.ENVIRONMENT_VARIABLE
        message = f"Using settings file at {config_path} set by {cfg_env_var}"
        messages.append(LogMessage(level=logging.DEBUG, message=message))
    elif found_config_path is not None:
        config_path = found_config_path
        settings_source = C.SEARCH_PATH
        message = f"Using settings file at {config_path} in search path"
        messages.append(LogMessage(level=logging.DEBUG, message=message))
    else:
        message = "No valid settings file found, using all default values for settings."
        messages.append(LogMessage(level=logging.DEBUG, message=message))
    return messages, exit_messages, config_path, settings_source


def get_and_check_collection_doc_cache(
    collection_doc_cache_path: str,
) -> Tuple[List[LogMessage], List[ExitMessage], Optional[KeyValueStore]]:
    """ensure the collection doc cache
    has the current version of the application
    as a safeguard, always delete and rebuild if not
    """
    messages: List[LogMessage] = []
    exit_messages: List[ExitMessage] = []
    message = f"Collection doc cache: 'path' is '{collection_doc_cache_path}'"
    messages.append(LogMessage(level=logging.DEBUG, message=message))

    path_errors = []
    doc_cache_dir = os.path.dirname(collection_doc_cache_path)
    try:
        os.makedirs(doc_cache_dir, exist_ok=True)
    except OSError as exc:
        path_errors.append(f"Problem making directory: {doc_cache_dir}")
        path_errors.append(f"Error was: {str(exc)}")

    if not os.access(os.path.dirname(collection_doc_cache_path), os.W_OK):
        path_errors.append("Directory not writable")

    if not os.access(os.path.dirname(collection_doc_cache_path), os.R_OK):
        path_errors.append("Directory not readable")

    if path_errors:
        exit_msgs = ["Problem while building the collection doc cache."]
        exit_msgs.extend(path_errors)
        exit_messages.extend([ExitMessage(message=exit_msg) for exit_msg in exit_msgs])
        exit_msg = "Try again without '--cdcp' or try '--cdcp ~/collection_doc_cache.db"
        exit_messages.append(ExitMessage(message=exit_msg, prefix=ExitPrefix.HINT))
        return messages, exit_messages, None

    collection_cache: KeyValueStore = KeyValueStore(collection_doc_cache_path)
    if "version" in collection_cache:
        cache_version = collection_cache["version"]
    else:
        cache_version = None
    message = f"Collection doc cache: 'current version' is '{cache_version}'"
    messages.append(LogMessage(level=logging.DEBUG, message=message))
    if cache_version is None or cache_version != VERSION_CDC:
        message = "Collection doc cache: version was empty or incorrect, rebuilding"
        messages.append(LogMessage(level=logging.INFO, message=message))
        collection_cache.close()
        os.remove(collection_doc_cache_path)
        collection_cache = KeyValueStore(collection_doc_cache_path)
        collection_cache["version"] = VERSION_CDC
        cache_version = collection_cache["version"]
        message = f"Collection doc cache: 'current version' is '{cache_version}'"
        messages.append(LogMessage(level=logging.INFO, message=message))
    collection_cache.close()
    return messages, exit_messages, collection_cache


def parse_and_update(
    params: List,
    args: ApplicationConfiguration,
    apply_previous_cli_entries: Union[C, List[str]] = C.NONE,
    initial: bool = False,
    attach_cdc=False,
) -> Tuple[List[LogMessage], List[ExitMessage]]:
    """Build a configuration

    :param args: The application args
    :param apply_previous_cli_entries: Should previous params from the CLI be applied
    :param initial: Is this the initial (first) configuration
    :param attach_cdc: Should the collection doc cache be attached to the args.internals

    """

    messages: List[LogMessage] = []
    exit_messages: List[ExitMessage] = []

    (
        new_messages,
        new_exit_messages,
        args.internals.settings_file_path,
        args.internals.settings_source,
    ) = find_config()
    messages.extend(new_messages)
    exit_messages.extend(new_exit_messages)
    if exit_messages:
        return messages, exit_messages

    configurator = Configurator(
        params=params,
        application_configuration=args,
        apply_previous_cli_entries=apply_previous_cli_entries,
        initial=initial,
    )

    new_messages, new_exit_messages = configurator.configure()
    messages.extend(new_messages)
    exit_messages.extend(new_exit_messages)
    if exit_messages:
        return messages, exit_messages

    if args.internals.collection_doc_cache is C.NOT_SET:
        mount_collection_cache = True
        message = "Collection doc cache not mounted"
        messages.append(LogMessage(level=logging.DEBUG, message=message))
    elif args.initial.collection_doc_cache_path != args.collection_doc_cache_path:
        mount_collection_cache = True
        message = "Collection doc cache path changed"
        messages.append(LogMessage(level=logging.DEBUG, message=message))
    else:
        mount_collection_cache = False

    if mount_collection_cache:
        new_messages, new_exit_messages, cache = get_and_check_collection_doc_cache(
            args.collection_doc_cache_path,
        )
        messages.extend(new_messages)
        exit_messages.extend(new_exit_messages)
        if exit_messages or cache is None:
            return messages, exit_messages
        if attach_cdc:
            args.internals.collection_doc_cache = cache
            message = "Collection doc cache attached to args.internals"
            messages.append(LogMessage(level=logging.DEBUG, message=message))
        else:
            message = "Collection doc cache not attached to args.internals"
            messages.append(LogMessage(level=logging.DEBUG, message=message))

    for entry in args.entries:
        message = f"Running with {entry.name} as '{entry.value.current}'"
        message += f" ({type(entry.value.current).__name__}/{entry.value.source.value})"
        messages.append(LogMessage(level=logging.DEBUG, message=message))

    return messages, exit_messages

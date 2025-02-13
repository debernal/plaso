# -*- coding: utf-8 -*-
"""File containing a Windows Registry plugin to parse the AMCache.hve file."""

import pyregf

from dfdatetime import filetime as dfdatetime_filetime
from dfdatetime import posix_time as dfdatetime_posix_time

from dfwinreg import definitions as dfwinreg_definitions

from plaso.containers import events
from plaso.containers import time_events
from plaso.containers import windows_events
from plaso.lib import definitions
from plaso.parsers import interface
from plaso.parsers import manager


class AMCacheFileEventData(events.EventData):
  """AMCache file event data.

  Attributes:
    company_name (str): company name that created product file belongs to.
    file_description (str): description of file.
    file_reference (str): file system file reference, for example 9-1 (MFT
        entry - sequence number).
    file_size (int): size of file in bytes.
    file_version (str): version of file.
    full_path (str): full path of file.
    language_code (int): language code of file.
    product_name (str): product name file belongs to.
    program_identifier (str): GUID of entry under Root/Program key file belongs
        to.
    sha1 (str): SHA-1 of file.
  """

  DATA_TYPE = 'windows:registry:amcache'

  def __init__(self):
    """Initializes event data."""
    super(AMCacheFileEventData, self).__init__(data_type=self.DATA_TYPE)
    self.company_name = None
    self.file_description = None
    self.file_reference = None
    self.file_size = None
    self.file_version = None
    self.full_path = None
    self.language_code = None
    self.product_name = None
    self.program_identifier = None
    self.sha1 = None


class AMCacheProgramEventData(events.EventData):
  """AMCache programs event data.

  Attributes:
    entry_type (str): type of entry (usually AddRemoveProgram).
    file_paths (str): file paths of installed program.
    files (str): list of files belonging to program.
    language_code (int): language_code of program.
    msi_package_code (str): MSI package code of program.
    msi_product_code (str): MSI product code of program.
    name (str): name of installed program.
    package_code (str): package code of program.
    product_code (str): product code of program.
    publisher (str): publisher of program.
    uninstall_key (str): unicode string of uninstall registry key for program.
    version (str): version of program.
  """

  DATA_TYPE = 'windows:registry:amcache:programs'

  def __init__(self):
    """Initializes event data."""
    super(AMCacheProgramEventData, self).__init__(data_type=self.DATA_TYPE)
    self.entry_type = None
    self.file_paths = None
    self.files = None
    self.language_code = None
    self.msi_package_code = None
    self.msi_product_code = None
    self.name = None
    self.package_code = None
    self.product_code = None
    self.publisher = None
    self.uninstall_key = None
    self.version = None


class AMCacheParser(interface.FileObjectParser):
  """AMCache Registry plugin for recently run programs."""

  NAME = 'amcache'
  DATA_FORMAT = 'AMCache Windows NT Registry (AMCache.hve) file'

  # Contains: {value name: attribute name}
  _FILE_REFERENCE_KEY_VALUES = {
      '0': 'product_name',
      '1': 'company_name',
      '3': 'language_code',
      '5': 'file_version',
      '6': 'file_size',
      'c': 'file_description',
      '15': 'full_path',
      '100': 'program_identifier',
      '101': 'sha1'}

  _AMCACHE_COMPILATION_TIME = 'f'
  _AMCACHE_FILE_MODIFICATION_TIME = '11'
  _AMCACHE_FILE_CREATION_TIME = '12'
  _AMCACHE_ENTRY_WRITE_TIME = '17'

  _AMCACHE_P_INSTALLATION_TIME = 'a'

  _AMCACHE_P_FILES = 'Files'

  _PRODUCT_KEY_VALUES = {
      '0': 'name',
      '1': 'version',
      '2': 'publisher',
      '3': 'language_code',
      '6': 'entry_type',
      '7': 'uninstall_key',
      'd': 'file_paths',
      'f': 'product_code',
      '10': 'package_code',
      '11': 'msi_product_code',
      '12': 'msi_package_code',
  }

  def _GetValueDataAsObject(self, parser_mediator, regf_value):
    """Retrieves the value data as an object.

    Args:
      parser_mediator (ParserMediator): mediates interactions between parsers
          and other components, such as storage and dfvfs.
      regf_value (pyregf_value): value.

    Returns:
      object: data as a Python type or None if the value cannot be read.
    """
    try:
      if regf_value.type in (
          dfwinreg_definitions.REG_SZ,
          dfwinreg_definitions.REG_EXPAND_SZ,
          dfwinreg_definitions.REG_LINK):
        value_data = regf_value.get_data_as_string()

      elif regf_value.type in (
          dfwinreg_definitions.REG_DWORD,
          dfwinreg_definitions.REG_DWORD_BIG_ENDIAN,
          dfwinreg_definitions.REG_QWORD):
        value_data = regf_value.get_data_as_integer()

      elif regf_value.type == dfwinreg_definitions.REG_MULTI_SZ:
        value_data = list(regf_value.get_data_as_multi_string())

      else:
        value_data = regf_value.data

    except (IOError, OverflowError) as exception:
      parser_mediator.ProduceExtractionWarning(
          'Unable to read data from value: {0:s} with error: {1!s}'.format(
              regf_value.name, exception))
      return None

    return value_data

  def _GetValuesFromKey(
      self, parser_mediator, regf_key, names_to_skip=None):
    """Retrieves the values from a Windows Registry key.

    Where:
    * the default value is represented as "(default)";
    * binary data values are represented as "(# bytes)", where # contains
          the number of bytes of the data;
    * empty values are represented as "(empty)".
    * empty multi value string values are represented as "[]".

    Args:
      parser_mediator (ParserMediator): mediates interactions between parsers
          and other components, such as storage and dfvfs.
      regf_key (pyregf_key): key.
      names_to_skip (Optional[list[str]]): names of values that should
          be skipped.

    Returns:
      dict[str, object]: names and data of the values in the key.
    """
    names_to_skip = [name.lower() for name in names_to_skip or []]

    values_dict = {}
    for regf_value in regf_key.values:
      value_name = regf_value.name or '(default)'
      if value_name.lower() in names_to_skip:
        continue

      if regf_value.data is None:
        value_string = '(empty)'
      else:
        value_object = self._GetValueDataAsObject(parser_mediator, regf_value)

        if regf_value.type == dfwinreg_definitions.REG_MULTI_SZ:
          value_string = '[{0:s}]'.format(', '.join(value_object or []))

        elif regf_value.type in (
            dfwinreg_definitions.REG_DWORD,
            dfwinreg_definitions.REG_DWORD_BIG_ENDIAN,
            dfwinreg_definitions.REG_EXPAND_SZ,
            dfwinreg_definitions.REG_LINK,
            dfwinreg_definitions.REG_QWORD,
            dfwinreg_definitions.REG_SZ):
          value_string = '{0!s}'.format(value_object)

        else:
          # Represent remaining types like REG_BINARY and
          # REG_RESOURCE_REQUIREMENT_LIST.
          value_string = '({0:d} bytes)'.format(len(value_object))

      values_dict[value_name] = value_string

    return values_dict

  def _ParseFileKey(self, parser_mediator, file_key):
    """Parses a Root\\File key.

    Args:
      parser_mediator (ParserMediator): mediates interactions between parsers
          and other components, such as storage and dfvfs.
      file_key (pyregf.key): the File key.
    """
    for volume_key in file_key.sub_keys:
      for file_reference_key in volume_key.sub_keys:
        self._ParseFileReferenceKey(parser_mediator, file_reference_key)

  def _ParseFileReferenceKey(self, parser_mediator, file_reference_key):
    """Parses a file reference key (sub key of Root\\File\\%VOLUME%) for events.

    Args:
      parser_mediator (ParserMediator): mediates interactions between parsers
          and other components, such as storage and dfvfs.
      file_reference_key (pyregf.key): file reference key.
    """
    event_data = AMCacheFileEventData()

    try:
      if '0000' in file_reference_key.name:
        # A NTFS file is a combination of MFT entry and sequence number.
        sequence_number, mft_entry = file_reference_key.name.split('0000')
        mft_entry = int(mft_entry, 16)
        sequence_number = int(sequence_number, 16)
        event_data.file_reference = '{0:d}-{1:d}'.format(
            mft_entry, sequence_number)
      else:
        # A FAT file is a single number.
        file_reference = int(file_reference_key.name, 16)
        event_data.file_reference = '{0:d}'.format(file_reference)

    except (ValueError, TypeError):
      pass

    for value_name, attribute_name in self._FILE_REFERENCE_KEY_VALUES.items():
      value = file_reference_key.get_value_by_name(value_name)
      if not value:
        continue

      value_data = self._GetValueDataAsObject(parser_mediator, value)
      if attribute_name == 'sha1' and value_data.startswith('0000'):
        # Strip off the 4 leading zero's from the sha1 hash.
        value_data = value_data[4:]

      setattr(event_data, attribute_name, value_data)

    amcache_time_value = file_reference_key.get_value_by_name(
        self._AMCACHE_ENTRY_WRITE_TIME)
    if amcache_time_value:
      timestamp = amcache_time_value.get_data_as_integer()
      amcache_time = dfdatetime_filetime.Filetime(timestamp=timestamp)
      event = time_events.DateTimeValuesEvent(
          amcache_time, definitions.TIME_DESCRIPTION_MODIFICATION)
      parser_mediator.ProduceEventWithEventData(event, event_data)

    creation_time_value = file_reference_key.get_value_by_name(
        self._AMCACHE_FILE_CREATION_TIME)
    if creation_time_value:
      timestamp = creation_time_value.get_data_as_integer()
      creation_time = dfdatetime_filetime.Filetime(timestamp=timestamp)
      event = time_events.DateTimeValuesEvent(
          creation_time, definitions.TIME_DESCRIPTION_CREATION)
      parser_mediator.ProduceEventWithEventData(event, event_data)

    modification_time_value = file_reference_key.get_value_by_name(
        self._AMCACHE_FILE_MODIFICATION_TIME)
    if modification_time_value:
      timestamp = modification_time_value.get_data_as_integer()
      modification_time = dfdatetime_filetime.Filetime(timestamp=timestamp)
      event = time_events.DateTimeValuesEvent(
          modification_time, definitions.TIME_DESCRIPTION_MODIFICATION)
      parser_mediator.ProduceEventWithEventData(event, event_data)

    compilation_time_value = file_reference_key.get_value_by_name(
        self._AMCACHE_COMPILATION_TIME)
    if compilation_time_value:
      timestamp = compilation_time_value.get_data_as_integer()
      link_time = dfdatetime_posix_time.PosixTime(timestamp=timestamp)
      event = time_events.DateTimeValuesEvent(
          link_time, definitions.TIME_DESCRIPTION_CHANGE)
      parser_mediator.ProduceEventWithEventData(event, event_data)

  def _ParseProgramKey(self, parser_mediator, program_key):
    """Parses a program key (a sub key of Root\\Programs) for events.

    Args:
      parser_mediator (ParserMediator): mediates interactions between parsers
          and other components, such as storage and dfvfs.
      program_key (pyregf_key): program key.
    """
    event_data = AMCacheProgramEventData()

    for value_name, attribute_name in self._PRODUCT_KEY_VALUES.items():
      value = program_key.get_value_by_name(value_name)
      if not value:
        continue

      value_data = self._GetValueDataAsObject(parser_mediator, value)
      setattr(event_data, attribute_name, value_data)

    installation_time_value = program_key.get_value_by_name(
        self._AMCACHE_P_INSTALLATION_TIME)
    if installation_time_value:
      timestamp = installation_time_value.get_data_as_integer()
      installation_time = dfdatetime_posix_time.PosixTime(timestamp=timestamp)
      event = time_events.DateTimeValuesEvent(
          installation_time, definitions.TIME_DESCRIPTION_INSTALLATION)
      parser_mediator.ProduceEventWithEventData(event, event_data)

  def _ParseProgramsKey(self, parser_mediator, programs_key):
    """Parses a Root\\Programs key.

    Args:
      parser_mediator (ParserMediator): mediates interactions between parsers
          and other components, such as storage and dfvfs.
      programs_key (pyregf.key): the Programs key.
    """
    for program_key in programs_key.sub_keys:
      self._ParseProgramKey(parser_mediator, program_key)

  def _ParseRootKey(self, parser_mediator, root_key):
    """Parses a Root key.

    Args:
      parser_mediator (ParserMediator): mediates interactions between parsers
          and other components, such as storage and dfvfs.
      root_key (pyregf.key): the Root key.
    """
    self._ProduceDefaultWindowsRegistryEvent(
        parser_mediator, root_key, '\\Root')

    key_path_segments = ['', 'Root']
    for sub_key in root_key.sub_keys:
      key_path_segments.append(sub_key.name)
      self._ParseSubKey(parser_mediator, sub_key, key_path_segments)
      key_path_segments.pop()

      if sub_key.name == 'File':
        self._ParseFileKey(parser_mediator, sub_key)

      elif sub_key.name == 'Programs':
        self._ParseProgramsKey(parser_mediator, sub_key)

  def _ParseSubKey(self, parser_mediator, regf_key, key_path_segments):
    """Parses a sub key.

    Args:
      parser_mediator (ParserMediator): mediates interactions between parsers
          and other components, such as storage and dfvfs.
      regf_key (pyregf.key): the key.
      key_path_segments (list[str]): key path segments.
    """
    key_path = '\\'.join(key_path_segments)
    self._ProduceDefaultWindowsRegistryEvent(
        parser_mediator, regf_key, key_path)

    for sub_key in regf_key.sub_keys:
      key_path_segments.append(sub_key.name)
      self._ParseSubKey(parser_mediator, sub_key, key_path_segments)
      key_path_segments.pop()

  def _ProduceDefaultWindowsRegistryEvent(
      self, parser_mediator, regf_key, key_path, names_to_skip=None):
    """Produces a default Windows Registry event.

    Args:
      parser_mediator (ParserMediator): mediates interactions between parsers
          and other components, such as storage and dfvfs.
      regf_key (pyregf_key): key.
      key_path (str): key path.
      names_to_skip (Optional[list[str]]): names of values that should
          be skipped.
    """
    values_dict = self._GetValuesFromKey(
        parser_mediator, regf_key, names_to_skip=names_to_skip)

    event_data = windows_events.WindowsRegistryEventData()
    event_data.key_path = key_path
    event_data.values = ' '.join([
        '{0:s}: {1!s}'.format(name, value)
        for name, value in sorted(values_dict.items())]) or None

    timestamp = regf_key.get_last_written_time_as_integer()
    last_written_time = dfdatetime_filetime.Filetime(timestamp=timestamp)
    event = time_events.DateTimeValuesEvent(
        last_written_time, definitions.TIME_DESCRIPTION_WRITTEN)
    parser_mediator.ProduceEventWithEventData(event, event_data)

  def ParseFileObject(self, parser_mediator, file_object):
    """Parses an AMCache.hve file-like object for events.

    Args:
      parser_mediator (ParserMediator): mediates interactions between parsers
          and other components, such as storage and dfvfs.
      file_object (dfvfs.FileIO): file-like object.
    """
    regf_file = pyregf.file()
    try:
      regf_file.open_file_object(file_object)
    except IOError:
      # The error is currently ignored -> see TODO above related to the
      # fixing of handling multiple parsers for the same file format.
      return

    root_key = regf_file.get_key_by_path('Root')
    if root_key:
      self._ParseRootKey(parser_mediator, root_key)
    else:
      parser_mediator.ProduceExtractionWarning(
          'Root key missing from AMCache.hve file.')

    regf_file.close()


manager.ParsersManager.RegisterParser(AMCacheParser)

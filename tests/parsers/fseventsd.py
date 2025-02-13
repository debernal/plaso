#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for fseventsd file parser."""

import unittest

from dfvfs.lib import definitions as dfvfs_definitions
from dfvfs.path import factory as path_spec_factory
from dfvfs.resolver import resolver as path_spec_resolver

from plaso.parsers import fseventsd

from tests.parsers import test_lib


class FSEventsdParserTest(test_lib.ParserTestCase):
  """Tests for the fseventsd parser."""

  def testParseV1(self):
    """Tests the Parse function on a version 1 file."""
    parser = fseventsd.FseventsdParser()

    path = self._GetTestFilePath(['fsevents-0000000002d89b58'])
    os_path_spec = path_spec_factory.Factory.NewPathSpec(
        dfvfs_definitions.TYPE_INDICATOR_OS, location=path)

    gzip_path_spec = path_spec_factory.Factory.NewPathSpec(
        dfvfs_definitions.TYPE_INDICATOR_GZIP, parent=os_path_spec)

    storage_writer = self._ParseFileByPathSpec(gzip_path_spec, parser)

    self.assertEqual(storage_writer.number_of_warnings, 0)
    self.assertEqual(storage_writer.number_of_events, 12)

    events = list(storage_writer.GetEvents())

    # The timestamp since it is derived from the file entry.
    os_file_entry = path_spec_resolver.Resolver.OpenFileEntry(os_path_spec)
    expected_time = os_file_entry.modification_time
    expected_timestamp = expected_time.GetPlasoTimestamp()

    expected_event_values = {
        'data_type': 'macos:fseventsd:record',
        'event_identifier': 47747061,
        'flags': 0x01000080,
        'path': '.Spotlight-V100/Store-V1',
        'timestamp': expected_timestamp}

    self.CheckEventValues(storage_writer, events[3], expected_event_values)

  def testParseV2(self):
    """Tests the Parse function on a version 2 file."""
    parser = fseventsd.FseventsdParser()

    path = self._GetTestFilePath(['fsevents-00000000001a0b79'])
    os_path_spec = path_spec_factory.Factory.NewPathSpec(
        dfvfs_definitions.TYPE_INDICATOR_OS, location=path)

    gzip_path_spec = path_spec_factory.Factory.NewPathSpec(
        dfvfs_definitions.TYPE_INDICATOR_GZIP, parent=os_path_spec)

    storage_writer = self._ParseFileByPathSpec(gzip_path_spec, parser)

    self.assertEqual(storage_writer.number_of_warnings, 0)
    self.assertEqual(storage_writer.number_of_events, 6)

    events = list(storage_writer.GetEvents())

    # The timestamp since it is derived from the file entry.
    os_file_entry = path_spec_resolver.Resolver.OpenFileEntry(os_path_spec)
    expected_time = os_file_entry.modification_time
    expected_timestamp = expected_time.GetPlasoTimestamp()

    expected_event_values = {
        'data_type': 'macos:fseventsd:record',
        'event_identifier': 1706838,
        'flags': 0x01000008,
        'path': 'Hi, Sierra',
        'timestamp': expected_timestamp}

    self.CheckEventValues(storage_writer, events[2], expected_event_values)


if __name__ == '__main__':
  unittest.main()

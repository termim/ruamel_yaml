
from __future__ import print_function

"""
various test cases for string scalars in YAML files
'|' for preserved newlines
'>' for folded (newlines become spaces)

and the chomping modifiers:
'-' for stripping: final line break and any trailing empty lines are excluded
'+' for keeping: final line break and empty lines are preserved
''  for clipping: final line break preserved, empty lines at end not
    included in content (no modifier)

"""

import pytest

import ruamel.yaml
from ruamel.yaml.compat import ordereddict
from roundtrip import round_trip, dedent, round_trip_load, round_trip_dump


class TestYAML:
    def test_basic_string(self):
        round_trip("""
        a: abcdefg
        """, )

    def test_quoted_string(self):
        round_trip("""
        a: '12345'
        """)

    def test_preserve_string(self):
        round_trip("""
            a: |
              abc
              def
            """, intermediate=dict(a='abc\ndef\n'))

    def test_preserve_string_strip(self):
        s = """
            a: |-
              abc
              def

            """
        o = dedent(s).rstrip() + '\n'
        round_trip(s, outp=o, intermediate=dict(a='abc\ndef'))

    def test_preserve_string_keep(self):
            # with pytest.raises(AssertionError) as excinfo:
            round_trip("""
            a: |+
              ghi
              jkl


            b: x
            """, intermediate=dict(a='ghi\njkl\n\n\n', b='x'))

    def test_preserve_string_keep_at_end(self):
        # at EOF you have to specify the ... to get proper "closure"
        # of the multiline scalar
        round_trip("""
            a: |+
              ghi
              jkl

            ...
            """, intermediate=dict(a='ghi\njkl\n\n'))

    def test_fold_string(self):
        with pytest.raises(AssertionError) as excinfo:
            round_trip("""
            a: >
              abc
              def

            """, intermediate=dict(a='abc def\n'))

    def test_fold_string_strip(self):
        with pytest.raises(AssertionError) as excinfo:
            round_trip("""
            a: >-
              abc
              def

            """, intermediate=dict(a='abc def'))

    def test_fold_string_keep(self):
        with pytest.raises(AssertionError) as excinfo:
            round_trip("""
            a: >+
              abc
              def

            """, intermediate=dict(a='abc def\n\n'))

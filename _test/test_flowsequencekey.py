# coding: utf-8

"""
test flow style sequences as keys roundtrip

"""

# import pytest
# import ruamel.yaml

from roundtrip import round_trip  # , dedent, round_trip_load, round_trip_dump


class TestFlowStyleSequenceKey:
    def test_so_39595807(self):
        round_trip("""
        %YAML 1.2
        ---
        [2, 3, 4]:
          a:
          - 1
          - 2
          b: Hello World!
          c: 'Voilà!'
        """, preserve_quotes=True, explicit_start=True, version=(1, 2))

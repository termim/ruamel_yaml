# coding: utf-8

import pytest                        # NOQA

import ruamel.yaml
from roundtrip import dedent, round_trip


def load(s, version=None):
    return ruamel.yaml.round_trip_load(dedent(s), version)


class TestVersions:
    def test_explicit_1_2(self):
        l = load("""\
        %YAML 1.2
        ---
        - 12:34:56
        - 012
        - 012345678
        - 0o12
        - on
        - off
        - yes
        - no
        - true
        """)
        assert l[0] == '12:34:56'
        assert l[1] == 12
        assert l[2] == '012345678'
        assert l[3] == 10
        assert l[4] == 'on'
        assert l[5] == 'off'
        assert l[6] == 'yes'
        assert l[7] == 'no'
        assert l[8] is True

    def test_explicit_1_1(self):
        l = load("""\
        %YAML 1.1
        ---
        - 12:34:56
        - 012
        - 012345678
        - 0o12
        - on
        - off
        - yes
        - no
        - true
        """)
        assert l[0] == 45296
        assert l[1] == 10
        assert l[2] == '012345678'
        assert l[3] == '0o12'
        assert l[4] is True
        assert l[5] is False
        assert l[6] is True
        assert l[7] is False
        assert l[8] is True

    def test_implicit_1_2(self):
        l = load("""\
        - 12:34:56
        - 12:34:56.78
        - 012
        - 012345678
        - 0o12
        - on
        - off
        - yes
        - no
        - true
        """)
        assert l[0] == '12:34:56'
        assert l[1] == '12:34:56.78'
        assert l[2] == 12
        assert l[3] == '012345678'
        assert l[4] == 10
        assert l[5] == 'on'
        assert l[6] == 'off'
        assert l[7] == 'yes'
        assert l[8] == 'no'
        assert l[9] is True

    def test_load_version_1_1(self):
        l = load("""\
        - 12:34:56
        - 12:34:56.78
        - 012
        - 012345678
        - 0o12
        - on
        - off
        - yes
        - no
        - true
        """, version="1.1")
        assert l[0] == 45296
        assert l[1] == 45296.78
        assert l[2] == 10
        assert l[3] == '012345678'
        assert l[4] == '0o12'
        assert l[5] is True
        assert l[6] is False
        assert l[7] is True
        assert l[8] is False
        assert l[9] is True


class TestIssue62:
    # bitbucket issue 62, issue_62
    def test_00(self):
        s = dedent("""\
        {}# Outside flow collection:
        - ::vector
        - ": - ()"
        - Up, up, and away!
        - -123
        - http://example.com/foo#bar
        # Inside flow collection:
        - [::vector, ": - ()", "Down, down and away!", -456, http://example.com/foo#bar]
        """)
        with pytest.raises(ruamel.yaml.parser.ParserError):
            round_trip(s.format('%YAML 1.1\n---\n'), preserve_quotes=True)
        round_trip(s.format(''), preserve_quotes=True)

    def test_00_single_comment(self):
        s = dedent("""\
        {}# Outside flow collection:
        - ::vector
        - ": - ()"
        - Up, up, and away!
        - -123
        - http://example.com/foo#bar
        - [::vector, ": - ()", "Down, down and away!", -456, http://example.com/foo#bar]
        """)
        with pytest.raises(ruamel.yaml.parser.ParserError):
            round_trip(s.format('%YAML 1.1\n---\n'), preserve_quotes=True)
        round_trip(s.format(''), preserve_quotes=True)
        # round_trip(s.format('%YAML 1.2\n---\n'), preserve_quotes=True, version=(1, 2))

    def test_01(self):
        s = dedent("""\
        {}[random plain value that contains a ? character]
        """)
        with pytest.raises(ruamel.yaml.parser.ParserError):
            round_trip(s.format('%YAML 1.1\n---\n'), preserve_quotes=True)
        round_trip(s.format(''), preserve_quotes=True)
        # note the flow seq on the --- line!
        round_trip(s.format('%YAML 1.2\n--- '), preserve_quotes=True, version="1.2")

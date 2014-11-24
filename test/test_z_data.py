
from __future__ import print_function

import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(__file__) + '/lib')

import ruamel.yaml
import test_appliance

args = []


def test_data():
    collections = []
    import test_yaml
    collections.append(test_yaml)
    test_appliance.run(collections, args)


# @pytest.mark.skipif(not ruamel.yaml.__with_libyaml__,
#                     reason="no libyaml")
def test_data_ext():
    collections = []
    if ruamel.yaml.__with_libyaml__:
        import test_yaml_ext
        collections.append(test_yaml_ext)
        test_appliance.run(collections, args)

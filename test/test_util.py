
from __future__ import print_function

import io
import sys
import subprocess
try:
    _ = subprocess.check_output
    def check_output(*args, **kw):
        try:
            res = subprocess.check_output(*args, **kw)
        except subprocess.CalledProcessError as e:
            print("subprocess.CalledProcessError\n", e.output, sep='')
            res = e.output
        if PY3:
            res = res.decode('utf-8')
        return res
except AttributeError:
    # https://gist.github.com/edufelipe/1027906
    def check_output(*args, **kw):
        process = subprocess.Popen(stdout=subprocess.PIPE, *args, **kw)
        output, unused_err = process.communicate()
        if PY3:
            output = output.decode('utf-8')
        return output
        # retcode = process.poll()
        # if retcode:
            # cmd = kw.get("args")
            # if cmd is None:
            #     cmd = args[0]
            # error = subprocess.CalledProcessError(retcode, cmd)
            # error.output = output
            # raise error
        # return output

import ruamel.yaml
from ruamel.yaml.compat import PY3
from roundtrip import dedent


def call_util(s, file_name, cmd, mp, td):
    """call the utilitiy yaml. if exit != 0 or if somethhing goes wrong
    return error output"""
    mp.chdir(td)
    with io.open(file_name, 'w') as fp:
        fp.write(dedent(s))
    res = check_output(cmd, stderr=subprocess.STDOUT)
    return res

def rt_test(s, file_name, mp, td):
    return call_util(s, file_name, ['yaml', 'rt', "-v", file_name], mp, td)

class TestUtil:

    def test_version(self, capsys):
        res = check_output(
            ['yaml', '--version'], stderr=subprocess.STDOUT)
        assert res == u"version: {0}\n".format(ruamel.yaml.__version__)

    def test_ok(self, tmpdir, monkeypatch):
        file_name = "00_ok.yaml"
        res = rt_test(u"""
        - abc
        - ghi  # some comment
        - klm
        """, file_name, mp=monkeypatch, td=tmpdir)
        assert res == "{0}: ok\n".format(file_name)

    def test_not_ok(self, tmpdir, monkeypatch):
        file_name = "01_second_rt_ok.yaml"
        res = rt_test(u"""
        - abc
        -  ghi # some comment
        - klm
        """, file_name, mp=monkeypatch, td=tmpdir)
        #print(res)
        assert res == dedent("""
        {file_name}:
             stabelizes on second round trip, ok without comments
        --- 01_second_rt_ok.yaml
        +++ round trip YAML
        @@ -1,3 +1,3 @@
         - abc
        --  ghi # some comment
        +- ghi  # some comment
         - klm
        """).format(**dict(file_name=file_name))


#! /usr/bin/env python
# coding: utf-8

from __future__ import print_function

import sys
import os
from textwrap import dedent

name_space = 'ruamel'
package_name = 'yaml'
full_package_name = name_space + '.' + package_name

exclude_files = [
    'setup.py',
]


def get_version():
    v_i = 'version_info = '
    for line in open('py/__init__.py'):
        if not line.startswith(v_i):
            continue
        s_e = line[len(v_i):].strip()[1:-1].split(', ')
        els = [x.strip()[1:-1] if x[0] in '\'"' else int(x) for x in s_e]
        return els


def _check_convert_version(tup):
    """create a PEP 386 pseudo-format conformant string from tuple tup"""
    ret_val = str(tup[0])  # first is always digit
    next_sep = "."  # separator for next extension, can be "" or "."
    nr_digits = 0  # nr of adjacent digits in rest, to verify
    post_dev = False  # are we processig post/dev
    for x in tup[1:]:
        if isinstance(x, int):
            nr_digits += 1
            if nr_digits > 2:
                raise ValueError("to many consecutive digits " + ret_val)
            ret_val += next_sep + str(x)
            next_sep = '.'
            continue
        first_letter = x[0].lower()
        next_sep = ''
        if first_letter in 'abcr':
            if post_dev:
                raise ValueError("release level specified after "
                                 "post/dev:" + x)
            nr_digits = 0
            ret_val += 'rc' if first_letter == 'r' else first_letter
        elif first_letter in 'pd':
            nr_digits = 1  # only one can follow
            post_dev = True
            ret_val += '.post' if first_letter == 'p' else '.dev'
        else:
            raise ValueError('First letter of "' + x + '" not recognised')
    return ret_val


version_info = get_version()
version_str = _check_convert_version(version_info)

if __name__ == '__main__':
    # put here so setup.py can be imported more easily
    from setuptools import setup, find_packages, Extension
    from setuptools.command import install_lib


class MyInstallLib(install_lib.install_lib):
    "create __init__.py on the fly"
    def run(self):
        install_lib.install_lib.run(self)

    def install(self):
        fpp = full_package_name.split('.')  # full package path
        full_exclude_files = [os.path.join(*(fpp + [x]))
                              for x in exclude_files]
        alt_files = []
        outfiles = install_lib.install_lib.install(self)
        for x in outfiles:
            for full_exclude_file in full_exclude_files:
                if full_exclude_file in x:
                    os.remove(x)
                    break
            else:
                alt_files.append(x)
        return alt_files


def check_extensions():
    import tempfile
    import shutil
    import subprocess

    c_code = dedent("""
    #include <yaml.h>

    int main(int argc, char* argv[])
    {
        yaml_parser_t parser;
        return 0;
    }
    """)
    tmp_dir = tempfile.mkdtemp(prefix = 'tmp_ruamel_yaml_')
    bin_file_name = os.path.join(tmp_dir, 'test_yaml')
    file_name = bin_file_name + '.c'
    with open(file_name, 'w') as fp:
        fp.write(c_code)
    try:
        res = subprocess.check_call(
            ['cc', '-o', bin_file_name, file_name],
            stderr = subprocess.STDOUT,
        )
        # print(res)
    except subprocess.CalledProcessError:
        print('libyaml not found')
        ret_val = None
    else:
        ret_val = [
            Extension(
                '_yaml',
                sources=['ext/_yaml.c'],
                libraries=['yaml'],
                ),
        ]
    shutil.rmtree(tmp_dir)
    return ret_val

def main():
    install_requires = [
        "ruamel.base",
        "ruamel.std.argparse>=0.5.1",
    ]
    # use fast ordereddict for !!omap
    if sys.version_info[0] == 2:
        install_requires.extend(['ruamel.ordereddict'])
    # if sys.version_info < (3, 4):
    #     install_requires.append("")
    packages = [full_package_name] + [
        (full_package_name + '.' + x)
        for x in find_packages('py', exclude=['test'])]
    setup(
        name=full_package_name,
        version=version_str,
        description=full_package_name + " is a YAML parser/emitter that "
        "supports roundtrip comment preservation",
        install_requires=install_requires,
        long_description=open('README.rst').read(),
        url='https://bitbucket.org/ruamel/' + package_name,
        author='Anthon van der Neut',
        author_email='a.van.der.neut@ruamel.eu',
        license="MIT license",
        package_dir={full_package_name: 'py'},
        namespace_packages=[name_space],
        packages=packages,
        ext_modules=check_extensions(),
        entry_points=mk_entry_points(full_package_name),
        cmdclass={'install_lib': MyInstallLib},
        classifiers=[
            'Development Status :: 4 - Beta',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: MIT License',
            'Operating System :: OS Independent',
            'Programming Language :: Python',
            "Programming Language :: Python :: 2.6",
            "Programming Language :: Python :: 2.7",
            "Programming Language :: Python :: 3.3",
            "Programming Language :: Python :: 3.4",
            "Topic :: Software Development :: Libraries :: Python Modules",
            "Topic :: Text Processing :: Markup",
        ]
    )


def mk_entry_points(full_package_name):
    script_name = full_package_name.rsplit('.', 1)[-1]
    return {'console_scripts': [
        '{0} = {1}:main'.format(script_name, full_package_name),
    ]}

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'sdist':
        assert full_package_name == os.path.abspath(os.path.dirname(
            __file__)).split('site-packages' + os.path.sep)[1].replace(
            os.path.sep, '.')
    main()


ruamel.yaml
===========

``ruamel.yaml`` is a YAML 1.2 loader/dumper package for Python.

* `Overview <http://yaml.readthedocs.org/en/latest/overview.html>`_
* `Installing <http://yaml.readthedocs.org/en/latest/install.html>`_
* `Details <http://yaml.readthedocs.org/en/latest/detail.html>`_
* `Examples <http://yaml.readthedocs.org/en/latest/example.html>`_
* `Differences with PyYAML <http://yaml.readthedocs.org/en/latest/pyyaml.html>`_

.. image:: https://readthedocs.org/projects/yaml/badge/?version=stable
   :target: https://yaml.readthedocs.org/en/stable

ChangeLog
=========

.. should insert NEXT: at the beginning of line for next key

0.14.3 (2017-03-31):
  - fix for 0o52 not being a string in YAML 1.1 (reported on
    `StackOverflow Q&A 43138503><http://stackoverflow.com/a/43138503/1307905>`_ by
    `Frank D <http://stackoverflow.com/users/7796630/frank-d>`_

0.14.2 (2017-03-23):
  - fix for old default pip on Ubuntu 14.04 (reported by Sébastien Maccagnoni-Munch)

0.14.1 (2017-03-22):
  - fix Text not available on 3.5.0 and 3.5.1 (reported by Charles Bouchard-Légaré)

0.14.0 (2017-03-21):
  - updates for mypy --strict
  - preparation for moving away from inheritance in Loader and Dumper, calls from e.g.
    the Representer to the Serializer.serialize() are now done via the attribute
    .serializer.serialize(). Usage of .serialize() outside of Serializer will be
    deprecated soon
  - some extra tests on main.py functions

0.13.14 (2017-02-12):
  - fix for issue 97: clipped block scalar followed by empty lines and comment
    would result in two CommentTokens of which the first was dropped.
    (reported by Colm O'Connor)

0.13.13 (2017-01-28):
  - fix for issue 96: prevent insertion of extra empty line if indented mapping entries
    are separated by an empty line (reported by Derrick Sawyer)

0.13.11 (2017-01-23):
  - allow ':' in flow style scalars if not followed by space. Also don't
    quote such scalar as this is no longer necessary.
  - add python 3.6 manylinux wheel to PyPI

0.13.10 (2017-01-22):
  - fix for issue 93, insert spurious blank line before single line comment
    between indented sequence elements (reported by Alex)

0.13.9 (2017-01-18):
  - fix for issue 92, wrong import name reported by the-corinthian

0.13.8 (2017-01-18):
  - fix for issue 91, when a compiler is unavailable reported by Maximilian Hils
  - fix for deepcopy issue with TimeStamps not preserving 'T', reported on
    `StackOverflow Q&A <http://stackoverflow.com/a/41577841/1307905>`_ by
    `Quuxplusone <http://stackoverflow.com/users/1424877/quuxplusone>`_


0.13.7 (2016-12-27):
  - fix for issue 85, constructor.py importing unicode_literals caused mypy to fail
    on 2.7 (reported by Peter Amstutz)

0.13.6 (2016-12-27):
  - fix for issue 83, collections.OrderedDict not representable by SafeRepresenter
    (reported by Frazer McLean)

0.13.5 (2016-12-25):
  - fix for issue 84, deepcopy not properly working (reported by Peter Amstutz)

0.13.4 (2016-12-05):
  - another fix for issue 82, change to non-global resolver data broke implicit type
    specification

0.13.3 (2016-12-05):
  - fix for issue 82, deepcopy not working (reported by code monk)

0.13.2 (2016-11-28):
  - fix for comments after empty (null) values  (reported by dsw2127 and cokelaer)

0.13.1 (2016-11-22):
  - optimisations on memory usage when loading YAML from large files (py3: -50%, py2: -85%)

0.13.0 (2016-11-20):
  - if ``load()`` or ``load_all()`` is called with only a single argument
    (stream or string)
    a UnsafeLoaderWarning will be issued once. If appropriate you can surpress this
    warning by filtering it. Explicitly supplying the ``Loader=ruamel.yaml.Loader``
    argument, will also prevent it from being issued. You should however consider
    using ``safe_load()``, ``safe_load_all()`` if your YAML input does not use tags.
  - allow adding comments before and after keys (based on
    `StackOveflow Q&A <http://stackoverflow.com/a/40705671/1307905>`_  by
    `msinn <http://stackoverflow.com/users/7185467/msinn>`_)

0.12.18 (2016-11-16):
  - another fix for numpy (re-reported independently by PaulG & Nathanial Burdic)

0.12.17 (2016-11-15):
  - only the RoundTripLoader included the Resolver that supports YAML 1.2
    now all loaders do (reported by mixmastamyk)

0.12.16 (2016-11-13):
  - allow dot char (and many others) in anchor name
    Fix issue 72 (reported by Shalon Wood)
  - Slightly smarter behaviour dumping strings when no style is
    specified. Single string scalars that start with single quotes
    or have newlines now are dumped double quoted: "'abc\nklm'" instead of::

      '''abc

        klm'''

0.12.14 (2016-09-21):
 - preserve round-trip sequences that are mapping keys
   (prompted by stackoverflow question 39595807 from Nowox)

0.12.13 (2016-09-15):
 - Fix for issue #60 representation of CommentedMap with merge
   keys incorrect (reported by Tal Liron)

0.12.11 (2016-09-06):
 - Fix issue 58 endless loop in scanning tokens (reported by
   Christopher Lambert)

0.12.10 (2016-09-05):
 - Make previous fix depend on unicode char width (32 bit unicode support
   is a problem on MacOS reported by David Tagatac)

0.12.8 (2016-09-05):
   - To be ignored Unicode characters were not properly regex matched
     (no specific tests, PR by Haraguroicha Hsu)

0.12.7 (2016-09-03):
   - fixing issue 54 empty lines with spaces (reported by Alex Harvey)

0.12.6 (2016-09-03):
   - fixing issue 46 empty lines between top-level keys were gobbled (but
     not between sequence elements, nor between keys in netsted mappings
     (reported by Alex Harvey)

0.12.5 (2016-08-20):
  - fixing issue 45 preserving datetime formatting (submitted by altuin)
    Several formatting parameters are preserved with some normalisation:
  - preserve 'T', 't' is replaced by 'T', multiple spaces between date
    and time reduced to one.
  - optional space before timezone is removed
  - still using microseconds, but now rounded (.1234567 -> .123457)
  - Z/-5/+01:00 preserved

0.12.4 (2016-08-19):
  - Fix for issue 44: missing preserve_quotes keyword argument (reported
    by M. Crusoe)

0.12.3 (2016-08-17):
  - correct 'in' operation for merged CommentedMaps in round-trip mode
    (implementation inspired by J.Ngo, but original not working for merges)
  - iteration over round-trip loaded mappings, that contain merges. Also
    keys(), items(), values() (Py3/Py2) and iterkeys(), iteritems(),
    itervalues(), viewkeys(), viewitems(), viewvalues() (Py2)
  - reuse of anchor name now generates warning, not an error. Round-tripping such
    anchors works correctly. This inherited PyYAML issue was brought to attention
    by G. Coddut (and was long standing https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=515634)
    suppressing the warning::

        import warnings
        from ruamel.yaml.error import ReusedAnchorWarning
        warnings.simplefilter("ignore", ReusedAnchorWarning)

0.12.2 (2016-08-16):
  - minor improvements based on feedback from M. Crusoe
    https://bitbucket.org/ruamel/yaml/issues/42/

0.12.0 (2016-08-16):
  - drop support for Python 2.6
  - include initial Type information (inspired by M. Crusoe)

0.11.15 (2016-08-07):
  - Change to prevent FutureWarning in NumPy, as reported by tgehring
    ("comparison to None will result in an elementwise object comparison in the future")

0.11.14 (2016-07-06):
  - fix preserve_quotes missing on original Loaders (as reported
    by Leynos, bitbucket issue 38)

0.11.13 (2016-07-06):
  - documentation only, automated linux wheels

0.11.12 (2016-07-06):
  - added support for roundtrip of single/double quoted scalars using:
    ruamel.yaml.round_trip_load(stream, preserve_quotes=True)

0.11.0 (2016-02-18):
  - RoundTripLoader loads 1.2 by default (no sexagesimals, 012 octals nor
    yes/no/on/off booleans

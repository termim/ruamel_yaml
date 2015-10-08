from __future__ import absolute_import
from __future__ import print_function

__all__ = ['BaseConstructor', 'SafeConstructor', 'Constructor',
           'ConstructorError', 'RoundTripConstructor']

import collections
import datetime
import base64
import binascii
import re
import sys
import types

try:
    from .error import *
    from .nodes import *
    from .compat import (utf8, builtins_module, to_str, PY2, PY3, ordereddict,
                         text_type)
    from .comments import *
    from .scalarstring import *
except (ImportError, ValueError):  # for Jython
    from ruamel.yaml.error import *
    from ruamel.yaml.nodes import *
    from ruamel.yaml.compat import (utf8, builtins_module, to_str, PY2, PY3, 
                                    ordereddict, text_type)
    from ruamel.yaml.comments import *
    from ruamel.yaml.scalarstring import *


class ConstructorError(MarkedYAMLError):
    pass


class BaseConstructor(object):

    yaml_constructors = {}
    yaml_multi_constructors = {}

    def __init__(self):
        self.constructed_objects = {}
        self.recursive_objects = {}
        self.state_generators = []
        self.deep_construct = False

    def check_data(self):
        # If there are more documents available?
        return self.check_node()

    def get_data(self):
        # Construct and return the next document.
        if self.check_node():
            return self.construct_document(self.get_node())

    def get_single_data(self):
        # Ensure that the stream contains a single document and construct it.
        node = self.get_single_node()
        if node is not None:
            return self.construct_document(node)
        return None

    def construct_document(self, node):
        data = self.construct_object(node)
        while self.state_generators:
            state_generators = self.state_generators
            self.state_generators = []
            for generator in state_generators:
                for dummy in generator:
                    pass
        self.constructed_objects = {}
        self.recursive_objects = {}
        self.deep_construct = False
        return data

    def construct_object(self, node, deep=False):
        if node in self.constructed_objects:
            return self.constructed_objects[node]
        if deep:
            old_deep = self.deep_construct
            self.deep_construct = True
        if node in self.recursive_objects:
            raise ConstructorError(
                None, None,
                "found unconstructable recursive node", node.start_mark)
        self.recursive_objects[node] = None
        constructor = None
        tag_suffix = None
        if node.tag in self.yaml_constructors:
            constructor = self.yaml_constructors[node.tag]
        else:
            for tag_prefix in self.yaml_multi_constructors:
                if node.tag.startswith(tag_prefix):
                    tag_suffix = node.tag[len(tag_prefix):]
                    constructor = self.yaml_multi_constructors[tag_prefix]
                    break
            else:
                if None in self.yaml_multi_constructors:
                    tag_suffix = node.tag
                    constructor = self.yaml_multi_constructors[None]
                elif None in self.yaml_constructors:
                    constructor = self.yaml_constructors[None]
                elif isinstance(node, ScalarNode):
                    constructor = self.__class__.construct_scalar
                elif isinstance(node, SequenceNode):
                    constructor = self.__class__.construct_sequence
                elif isinstance(node, MappingNode):
                    constructor = self.__class__.construct_mapping
        if tag_suffix is None:
            data = constructor(self, node)
        else:
            data = constructor(self, tag_suffix, node)
        if isinstance(data, types.GeneratorType):
            generator = data
            data = next(generator)
            if self.deep_construct:
                for dummy in generator:
                    pass
            else:
                self.state_generators.append(generator)
        self.constructed_objects[node] = data
        del self.recursive_objects[node]
        if deep:
            self.deep_construct = old_deep
        return data

    def construct_scalar(self, node):
        if not isinstance(node, ScalarNode):
            raise ConstructorError(
                None, None,
                "expected a scalar node, but found %s" % node.id,
                node.start_mark)
        return node.value

    def construct_sequence(self, node, deep=False):
        if not isinstance(node, SequenceNode):
            raise ConstructorError(
                None, None,
                "expected a sequence node, but found %s" % node.id,
                node.start_mark)
        return [self.construct_object(child, deep=deep)
                for child in node.value]

    def construct_mapping(self, node, deep=False):
        if not isinstance(node, MappingNode):
            raise ConstructorError(
                None, None,
                "expected a mapping node, but found %s" % node.id,
                node.start_mark)
        mapping = {}
        for key_node, value_node in node.value:
            # keys can be list -> deep
            key = self.construct_object(key_node, deep=True)
            # lists are not hashable, but tuples are
            if not isinstance(key, collections.Hashable):
                if isinstance(key, list):
                    key = tuple(key)
            if PY2:
                try:
                    hash(key)
                except TypeError as exc:
                    raise ConstructorError(
                        "while constructing a mapping", node.start_mark,
                        "found unacceptable key (%s)" %
                        exc, key_node.start_mark)
            else:
                if not isinstance(key, collections.Hashable):
                    raise ConstructorError(
                        "while constructing a mapping", node.start_mark,
                        "found unhashable key", key_node.start_mark)

            value = self.construct_object(value_node, deep=deep)
            mapping[key] = value
        return mapping

    def construct_pairs(self, node, deep=False):
        if not isinstance(node, MappingNode):
            raise ConstructorError(
                None, None,
                "expected a mapping node, but found %s" % node.id,
                node.start_mark)
        pairs = []
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            value = self.construct_object(value_node, deep=deep)
            pairs.append((key, value))
        return pairs

    @classmethod
    def add_constructor(cls, tag, constructor):
        if 'yaml_constructors' not in cls.__dict__:
            cls.yaml_constructors = cls.yaml_constructors.copy()
        cls.yaml_constructors[tag] = constructor

    @classmethod
    def add_multi_constructor(cls, tag_prefix, multi_constructor):
        if 'yaml_multi_constructors' not in cls.__dict__:
            cls.yaml_multi_constructors = cls.yaml_multi_constructors.copy()
        cls.yaml_multi_constructors[tag_prefix] = multi_constructor


class SafeConstructor(BaseConstructor):
    def construct_scalar(self, node):
        if isinstance(node, MappingNode):
            for key_node, value_node in node.value:
                if key_node.tag == u'tag:yaml.org,2002:value':
                    return self.construct_scalar(value_node)
        return BaseConstructor.construct_scalar(self, node)

    def flatten_mapping(self, node):
        """
        This implements the merge key feature http://yaml.org/type/merge.html
        by inserting keys from the merge dict/list of dicts if not yet
        available in this node
        """
        merge = []
        index = 0
        while index < len(node.value):
            key_node, value_node = node.value[index]
            if key_node.tag == u'tag:yaml.org,2002:merge':
                del node.value[index]
                if isinstance(value_node, MappingNode):
                    self.flatten_mapping(value_node)
                    merge.extend(value_node.value)
                elif isinstance(value_node, SequenceNode):
                    submerge = []
                    for subnode in value_node.value:
                        if not isinstance(subnode, MappingNode):
                            raise ConstructorError(
                                "while constructing a mapping",
                                node.start_mark,
                                "expected a mapping for merging, but found %s"
                                % subnode.id, subnode.start_mark)
                        self.flatten_mapping(subnode)
                        submerge.append(subnode.value)
                    submerge.reverse()
                    for value in submerge:
                        merge.extend(value)
                else:
                    raise ConstructorError(
                        "while constructing a mapping", node.start_mark,
                        "expected a mapping or list of mappings for merging, "
                        "but found %s"
                        % value_node.id, value_node.start_mark)
            elif key_node.tag == u'tag:yaml.org,2002:value':
                key_node.tag = u'tag:yaml.org,2002:str'
                index += 1
            else:
                index += 1
        if merge:
            node.value = merge + node.value

    def construct_mapping(self, node, deep=False):
        if isinstance(node, MappingNode):
            self.flatten_mapping(node)
        return BaseConstructor.construct_mapping(self, node, deep=deep)

    def construct_yaml_null(self, node):
        self.construct_scalar(node)
        return None

    # YAML 1.2 spec doesn't mention yes/no etc any more, 1.1 does
    bool_values = {
        u'yes':     True,
        u'no':      False,
        u'true':    True,
        u'false':   False,
        u'on':      True,
        u'off':     False,
    }

    def construct_yaml_bool(self, node):
        value = self.construct_scalar(node)
        return self.bool_values[value.lower()]

    def construct_yaml_int(self, node):
        value = to_str(self.construct_scalar(node))
        value = value.replace('_', '')
        sign = +1
        if value[0] == '-':
            sign = -1
        if value[0] in '+-':
            value = value[1:]
        if value == '0':
            return 0
        elif value.startswith('0b'):
            return sign*int(value[2:], 2)
        elif value.startswith('0x'):
            return sign*int(value[2:], 16)
        elif value.startswith('0o'):
            return sign*int(value[2:], 8)
        elif value[0] == '0':
            return sign*int(value, 8)
        elif ':' in value:
            digits = [int(part) for part in value.split(':')]
            digits.reverse()
            base = 1
            value = 0
            for digit in digits:
                value += digit*base
                base *= 60
            return sign*value
        else:
            return sign*int(value)

    inf_value = 1e300
    while inf_value != inf_value*inf_value:
        inf_value *= inf_value
    nan_value = -inf_value/inf_value   # Trying to make a quiet NaN (like C99).

    def construct_yaml_float(self, node):
        value = to_str(self.construct_scalar(node))
        value = value.replace('_', '').lower()
        sign = +1
        if value[0] == '-':
            sign = -1
        if value[0] in '+-':
            value = value[1:]
        if value == '.inf':
            return sign*self.inf_value
        elif value == '.nan':
            return self.nan_value
        elif ':' in value:
            digits = [float(part) for part in value.split(':')]
            digits.reverse()
            base = 1
            value = 0.0
            for digit in digits:
                value += digit*base
                base *= 60
            return sign*value
        else:
            return sign*float(value)

    if PY3:
        def construct_yaml_binary(self, node):
            try:
                value = self.construct_scalar(node).encode('ascii')
            except UnicodeEncodeError as exc:
                raise ConstructorError(
                    None, None,
                    "failed to convert base64 data into ascii: %s" % exc,
                    node.start_mark)
            try:
                if hasattr(base64, 'decodebytes'):
                    return base64.decodebytes(value)
                else:
                    return base64.decodestring(value)
            except binascii.Error as exc:
                raise ConstructorError(
                    None, None,
                    "failed to decode base64 data: %s" % exc, node.start_mark)
    else:
        def construct_yaml_binary(self, node):
            value = self.construct_scalar(node)
            try:
                return to_str(value).decode('base64')
            except (binascii.Error, UnicodeEncodeError) as exc:
                raise ConstructorError(
                    None, None,
                    "failed to decode base64 data: %s" % exc, node.start_mark)

    timestamp_regexp = re.compile(
        u'''^(?P<year>[0-9][0-9][0-9][0-9])
          -(?P<month>[0-9][0-9]?)
          -(?P<day>[0-9][0-9]?)
          (?:(?:[Tt]|[ \\t]+)
          (?P<hour>[0-9][0-9]?)
          :(?P<minute>[0-9][0-9])
          :(?P<second>[0-9][0-9])
          (?:\\.(?P<fraction>[0-9]*))?
          (?:[ \\t]*(?P<tz>Z|(?P<tz_sign>[-+])(?P<tz_hour>[0-9][0-9]?)
          (?::(?P<tz_minute>[0-9][0-9]))?))?)?$''', re.X)

    def construct_yaml_timestamp(self, node):
        value = self.construct_scalar(node)
        match = self.timestamp_regexp.match(node.value)
        values = match.groupdict()
        year = int(values['year'])
        month = int(values['month'])
        day = int(values['day'])
        if not values['hour']:
            return datetime.date(year, month, day)
        hour = int(values['hour'])
        minute = int(values['minute'])
        second = int(values['second'])
        fraction = 0
        if values['fraction']:
            fraction = values['fraction'][:6]
            while len(fraction) < 6:
                fraction += '0'
            fraction = int(fraction)
        delta = None
        if values['tz_sign']:
            tz_hour = int(values['tz_hour'])
            tz_minute = int(values['tz_minute'] or 0)
            delta = datetime.timedelta(hours=tz_hour, minutes=tz_minute)
            if values['tz_sign'] == '-':
                delta = -delta
        data = datetime.datetime(year, month, day, hour, minute, second,
                                 fraction)
        if delta:
            data -= delta
        return data

    def construct_yaml_omap(self, node):
        # Note: we do now check for duplicate keys
        omap = ordereddict()
        yield omap
        if not isinstance(node, SequenceNode):
            raise ConstructorError(
                "while constructing an ordered map", node.start_mark,
                "expected a sequence, but found %s" % node.id, node.start_mark)
        for subnode in node.value:
            if not isinstance(subnode, MappingNode):
                raise ConstructorError(
                    "while constructing an ordered map", node.start_mark,
                    "expected a mapping of length 1, but found %s" %
                    subnode.id,
                    subnode.start_mark)
            if len(subnode.value) != 1:
                raise ConstructorError(
                    "while constructing an ordered map", node.start_mark,
                    "expected a single mapping item, but found %d items" %
                    len(subnode.value),
                    subnode.start_mark)
            key_node, value_node = subnode.value[0]
            key = self.construct_object(key_node)
            assert key not in omap
            value = self.construct_object(value_node)
            omap[key] = value

    def construct_yaml_pairs(self, node):
        # Note: the same code as `construct_yaml_omap`.
        pairs = []
        yield pairs
        if not isinstance(node, SequenceNode):
            raise ConstructorError(
                "while constructing pairs", node.start_mark,
                "expected a sequence, but found %s" % node.id, node.start_mark)
        for subnode in node.value:
            if not isinstance(subnode, MappingNode):
                raise ConstructorError(
                    "while constructing pairs", node.start_mark,
                    "expected a mapping of length 1, but found %s" %
                    subnode.id,
                    subnode.start_mark)
            if len(subnode.value) != 1:
                raise ConstructorError(
                    "while constructing pairs", node.start_mark,
                    "expected a single mapping item, but found %d items" %
                    len(subnode.value),
                    subnode.start_mark)
            key_node, value_node = subnode.value[0]
            key = self.construct_object(key_node)
            value = self.construct_object(value_node)
            pairs.append((key, value))

    def construct_yaml_set(self, node):
        data = set()
        yield data
        value = self.construct_mapping(node)
        data.update(value)

    def construct_yaml_str(self, node):
        value = self.construct_scalar(node)
        if PY3:
            return value
        try:
            return value.encode('ascii')
        except UnicodeEncodeError:
            return value

    def construct_yaml_seq(self, node):
        data = []
        yield data
        data.extend(self.construct_sequence(node))

    def construct_yaml_map(self, node):
        data = {}
        yield data
        value = self.construct_mapping(node)
        data.update(value)

    def construct_yaml_object(self, node, cls):
        data = cls.__new__(cls)
        yield data
        if hasattr(data, '__setstate__'):
            state = self.construct_mapping(node, deep=True)
            data.__setstate__(state)
        else:
            state = self.construct_mapping(node)
            data.__dict__.update(state)

    def construct_undefined(self, node):
        raise ConstructorError(
            None, None,
            "could not determine a constructor for the tag %r" %
            utf8(node.tag),
            node.start_mark)

SafeConstructor.add_constructor(
    u'tag:yaml.org,2002:null',
    SafeConstructor.construct_yaml_null)

SafeConstructor.add_constructor(
    u'tag:yaml.org,2002:bool',
    SafeConstructor.construct_yaml_bool)

SafeConstructor.add_constructor(
    u'tag:yaml.org,2002:int',
    SafeConstructor.construct_yaml_int)

SafeConstructor.add_constructor(
    u'tag:yaml.org,2002:float',
    SafeConstructor.construct_yaml_float)

SafeConstructor.add_constructor(
    u'tag:yaml.org,2002:binary',
    SafeConstructor.construct_yaml_binary)

SafeConstructor.add_constructor(
    u'tag:yaml.org,2002:timestamp',
    SafeConstructor.construct_yaml_timestamp)

SafeConstructor.add_constructor(
    u'tag:yaml.org,2002:omap',
    SafeConstructor.construct_yaml_omap)

SafeConstructor.add_constructor(
    u'tag:yaml.org,2002:pairs',
    SafeConstructor.construct_yaml_pairs)

SafeConstructor.add_constructor(
    u'tag:yaml.org,2002:set',
    SafeConstructor.construct_yaml_set)

SafeConstructor.add_constructor(
    u'tag:yaml.org,2002:str',
    SafeConstructor.construct_yaml_str)

SafeConstructor.add_constructor(
    u'tag:yaml.org,2002:seq',
    SafeConstructor.construct_yaml_seq)

SafeConstructor.add_constructor(
    u'tag:yaml.org,2002:map',
    SafeConstructor.construct_yaml_map)

SafeConstructor.add_constructor(
    None, SafeConstructor.construct_undefined)


class Constructor(SafeConstructor):

    def construct_python_str(self, node):
        return utf8(self.construct_scalar(node))

    def construct_python_unicode(self, node):
        return self.construct_scalar(node)

    if PY3:
        def construct_python_bytes(self, node):
            try:
                value = self.construct_scalar(node).encode('ascii')
            except UnicodeEncodeError as exc:
                raise ConstructorError(
                    None, None,
                    "failed to convert base64 data into ascii: %s" % exc,
                    node.start_mark)
            try:
                if hasattr(base64, 'decodebytes'):
                    return base64.decodebytes(value)
                else:
                    return base64.decodestring(value)
            except binascii.Error as exc:
                raise ConstructorError(
                    None, None,
                    "failed to decode base64 data: %s" % exc, node.start_mark)

    def construct_python_long(self, node):
        val = self.construct_yaml_int(node)
        if PY3:
            return val
        return int(val)

    def construct_python_complex(self, node):
        return complex(self.construct_scalar(node))

    def construct_python_tuple(self, node):
        return tuple(self.construct_sequence(node))

    def find_python_module(self, name, mark):
        if not name:
            raise ConstructorError(
                "while constructing a Python module", mark,
                "expected non-empty name appended to the tag", mark)
        try:
            __import__(name)
        except ImportError as exc:
            raise ConstructorError(
                "while constructing a Python module", mark,
                "cannot find module %r (%s)" % (utf8(name), exc), mark)
        return sys.modules[name]

    def find_python_name(self, name, mark):
        if not name:
            raise ConstructorError(
                "while constructing a Python object", mark,
                "expected non-empty name appended to the tag", mark)
        if u'.' in name:
            module_name, object_name = name.rsplit('.', 1)
        else:
            module_name = builtins_module
            object_name = name
        try:
            __import__(module_name)
        except ImportError as exc:
            raise ConstructorError(
                "while constructing a Python object", mark,
                "cannot find module %r (%s)" % (utf8(module_name), exc), mark)
        module = sys.modules[module_name]
        if not hasattr(module, object_name):
            raise ConstructorError(
                "while constructing a Python object", mark,
                "cannot find %r in the module %r" % (utf8(object_name),
                                                     module.__name__), mark)
        return getattr(module, object_name)

    def construct_python_name(self, suffix, node):
        value = self.construct_scalar(node)
        if value:
            raise ConstructorError(
                "while constructing a Python name", node.start_mark,
                "expected the empty value, but found %r" % utf8(value),
                node.start_mark)
        return self.find_python_name(suffix, node.start_mark)

    def construct_python_module(self, suffix, node):
        value = self.construct_scalar(node)
        if value:
            raise ConstructorError(
                "while constructing a Python module", node.start_mark,
                "expected the empty value, but found %r" % utf8(value),
                node.start_mark)
        return self.find_python_module(suffix, node.start_mark)

    if PY2:
        class classobj:
            pass

    def make_python_instance(self, suffix, node,
                             args=None, kwds=None, newobj=False):
        if not args:
            args = []
        if not kwds:
            kwds = {}
        cls = self.find_python_name(suffix, node.start_mark)
        if PY3:
            if newobj and isinstance(cls, type):
                return cls.__new__(cls, *args, **kwds)
            else:
                return cls(*args, **kwds)
        else:
            if newobj and isinstance(cls, type(self.classobj))  \
                    and not args and not kwds:
                instance = self.classobj()
                instance.__class__ = cls
                return instance
            elif newobj and isinstance(cls, type):
                return cls.__new__(cls, *args, **kwds)
            else:
                return cls(*args, **kwds)

    def set_python_instance_state(self, instance, state):
        if hasattr(instance, '__setstate__'):
            instance.__setstate__(state)
        else:
            slotstate = {}
            if isinstance(state, tuple) and len(state) == 2:
                state, slotstate = state
            if hasattr(instance, '__dict__'):
                instance.__dict__.update(state)
            elif state:
                slotstate.update(state)
            for key, value in slotstate.items():
                setattr(object, key, value)

    def construct_python_object(self, suffix, node):
        # Format:
        #   !!python/object:module.name { ... state ... }
        instance = self.make_python_instance(suffix, node, newobj=True)
        yield instance
        deep = hasattr(instance, '__setstate__')
        state = self.construct_mapping(node, deep=deep)
        self.set_python_instance_state(instance, state)

    def construct_python_object_apply(self, suffix, node, newobj=False):
        # Format:
        #   !!python/object/apply       # (or !!python/object/new)
        #   args: [ ... arguments ... ]
        #   kwds: { ... keywords ... }
        #   state: ... state ...
        #   listitems: [ ... listitems ... ]
        #   dictitems: { ... dictitems ... }
        # or short format:
        #   !!python/object/apply [ ... arguments ... ]
        # The difference between !!python/object/apply and !!python/object/new
        # is how an object is created, check make_python_instance for details.
        if isinstance(node, SequenceNode):
            args = self.construct_sequence(node, deep=True)
            kwds = {}
            state = {}
            listitems = []
            dictitems = {}
        else:
            value = self.construct_mapping(node, deep=True)
            args = value.get('args', [])
            kwds = value.get('kwds', {})
            state = value.get('state', {})
            listitems = value.get('listitems', [])
            dictitems = value.get('dictitems', {})
        instance = self.make_python_instance(suffix, node, args, kwds, newobj)
        if state:
            self.set_python_instance_state(instance, state)
        if listitems:
            instance.extend(listitems)
        if dictitems:
            for key in dictitems:
                instance[key] = dictitems[key]
        return instance

    def construct_python_object_new(self, suffix, node):
        return self.construct_python_object_apply(suffix, node, newobj=True)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/none',
    Constructor.construct_yaml_null)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/bool',
    Constructor.construct_yaml_bool)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/str',
    Constructor.construct_python_str)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/unicode',
    Constructor.construct_python_unicode)

if PY3:
    Constructor.add_constructor(
        u'tag:yaml.org,2002:python/bytes',
        Constructor.construct_python_bytes)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/int',
    Constructor.construct_yaml_int)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/long',
    Constructor.construct_python_long)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/float',
    Constructor.construct_yaml_float)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/complex',
    Constructor.construct_python_complex)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/list',
    Constructor.construct_yaml_seq)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/tuple',
    Constructor.construct_python_tuple)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/dict',
    Constructor.construct_yaml_map)

Constructor.add_multi_constructor(
    u'tag:yaml.org,2002:python/name:',
    Constructor.construct_python_name)

Constructor.add_multi_constructor(
    u'tag:yaml.org,2002:python/module:',
    Constructor.construct_python_module)

Constructor.add_multi_constructor(
    u'tag:yaml.org,2002:python/object:',
    Constructor.construct_python_object)

Constructor.add_multi_constructor(
    u'tag:yaml.org,2002:python/object/apply:',
    Constructor.construct_python_object_apply)

Constructor.add_multi_constructor(
    u'tag:yaml.org,2002:python/object/new:',
    Constructor.construct_python_object_new)


class RoundTripConstructor(SafeConstructor):
    """need to store the comments on the node itself,
    as well as on the items
    """

    def construct_scalar(self, node):
        if not isinstance(node, ScalarNode):
            raise ConstructorError(
                None, None,
                "expected a scalar node, but found %s" % node.id,
                node.start_mark)

        if node.style == '|' and isinstance(node.value, text_type):
            return PreservedScalarString(node.value)
        return node.value

    def construct_yaml_str(self, node):
        value = self.construct_scalar(node)
        if isinstance(value, ScalarString):
            return value
        if PY3:
            return value
        try:
            return value.encode('ascii')
        except AttributeError:
            # in case you replace the node dynamically e.g. with a dict
            return value
        except UnicodeEncodeError:
            return value

    def construct_sequence(self, node, seqtyp, deep=False):
        if not isinstance(node, SequenceNode):
            raise ConstructorError(
                None, None,
                "expected a sequence node, but found %s" % node.id,
                node.start_mark)
        ret_val = []
        if node.comment:
            seqtyp._yaml_add_comment(node.comment[:2])
            if len(node.comment) > 2:
                seqtyp.yaml_end_comment_extend(node.comment[2], clear=True)
        if node.anchor:
            from ruamel.yaml.serializer import templated_id
            if not templated_id(node.anchor):
                seqtyp.yaml_set_anchor(node.anchor)
        for idx, child in enumerate(node.value):
            ret_val.append(self.construct_object(child, deep=deep))
            if child.comment:
                seqtyp._yaml_add_comment(child.comment, key=idx)
            seqtyp._yaml_set_idx_line_col(
                idx, [child.start_mark.line, child.start_mark.column])
        return ret_val

    def flatten_mapping(self, node):
        """
        This implements the merge key feature http://yaml.org/type/merge.html
        by inserting keys from the merge dict/list of dicts if not yet
        available in this node
        """

        def constructed(value_node):
            # If the contents of a merge are defined within the
            # merge marker, then they won't have been constructed
            # yet. But if they were already constructed, we need to use
            # the existing object.
            if value_node in self.constructed_objects:
                value = self.constructed_objects[value_node]
            else:
                value = self.construct_object(value_node, deep=False)
            return value

        #merge = []
        merge_map_list = []
        index = 0
        while index < len(node.value):
            key_node, value_node = node.value[index]
            if key_node.tag == u'tag:yaml.org,2002:merge':
                del node.value[index]
                if isinstance(value_node, MappingNode):
                    merge_map_list.append(
                        (index, constructed(value_node)))
                    #self.flatten_mapping(value_node)
                    #merge.extend(value_node.value)
                elif isinstance(value_node, SequenceNode):
                    #submerge = []
                    for subnode in value_node.value:
                        if not isinstance(subnode, MappingNode):
                            raise ConstructorError(
                                "while constructing a mapping",
                                node.start_mark,
                                "expected a mapping for merging, but found %s"
                                % subnode.id, subnode.start_mark)
                        merge_map_list.append(
                            (index, constructed(subnode)))
                    #    self.flatten_mapping(subnode)
                    #    submerge.append(subnode.value)
                    #submerge.reverse()
                    #for value in submerge:
                    #    merge.extend(value)
                else:
                    raise ConstructorError(
                        "while constructing a mapping", node.start_mark,
                        "expected a mapping or list of mappings for merging, "
                        "but found %s"
                        % value_node.id, value_node.start_mark)
            elif key_node.tag == u'tag:yaml.org,2002:value':
                key_node.tag = u'tag:yaml.org,2002:str'
                index += 1
            else:
                index += 1
        #print ('merge_map_list', merge_map_list)
        return merge_map_list
        #if merge:
        #    node.value = merge + node.value

    def construct_mapping(self, node, maptyp, deep=False):
        if not isinstance(node, MappingNode):
            raise ConstructorError(
                None, None,
                "expected a mapping node, but found %s" % node.id,
                node.start_mark)
        if isinstance(node, MappingNode):
            merge_map = self.flatten_mapping(node)
            if merge_map:
                maptyp.add_yaml_merge(merge_map)
        # mapping = {}
        if node.comment:
            maptyp._yaml_add_comment(node.comment[:2])
            if len(node.comment) > 2:
                maptyp.yaml_end_comment_extend(node.comment[2], clear=True)
        if node.anchor:
            from ruamel.yaml.serializer import templated_id
            if not templated_id(node.anchor):
                maptyp.yaml_set_anchor(node.anchor)
        for key_node, value_node in node.value:
            # keys can be list -> deep
            key = self.construct_object(key_node, deep=True)
            # lists are not hashable, but tuples are
            if not isinstance(key, collections.Hashable):
                if isinstance(key, list):
                    key = tuple(key)
            if PY2:
                try:
                    hash(key)
                except TypeError as exc:
                    raise ConstructorError(
                        "while constructing a mapping", node.start_mark,
                        "found unacceptable key (%s)" %
                        exc, key_node.start_mark)
            else:
                if not isinstance(key, collections.Hashable):
                    raise ConstructorError(
                        "while constructing a mapping", node.start_mark,
                        "found unhashable key", key_node.start_mark)
            value = self.construct_object(value_node, deep=deep)
            if key_node.comment:
                maptyp._yaml_add_comment(key_node.comment, key=key)
            if value_node.comment:
                maptyp._yaml_add_comment(value_node.comment, value=key)
            maptyp._yaml_set_kv_line_col(
                key, [key_node.start_mark.line, key_node.start_mark.column,
                value_node.start_mark.line, value_node.start_mark.column])
            maptyp[key] = value

    def construct_setting(self, node, typ, deep=False):
        if not isinstance(node, MappingNode):
            raise ConstructorError(
                None, None,
                "expected a mapping node, but found %s" % node.id,
                node.start_mark)
        if node.comment:
            typ._yaml_add_comment(node.comment[:2])
            if len(node.comment) > 2:
                typ.yaml_end_comment_extend(node.comment[2], clear=True)
        if node.anchor:
            from ruamel.yaml.serializer import templated_id
            if not templated_id(node.anchor):
                typ.yaml_set_anchor(node.anchor)
        for key_node, value_node in node.value:
            # keys can be list -> deep
            key = self.construct_object(key_node, deep=True)
            # lists are not hashable, but tuples are
            if not isinstance(key, collections.Hashable):
                if isinstance(key, list):
                    key = tuple(key)
            if PY2:
                try:
                    hash(key)
                except TypeError as exc:
                    raise ConstructorError(
                        "while constructing a mapping", node.start_mark,
                        "found unacceptable key (%s)" %
                        exc, key_node.start_mark)
            else:
                if not isinstance(key, collections.Hashable):
                    raise ConstructorError(
                        "while constructing a mapping", node.start_mark,
                        "found unhashable key", key_node.start_mark)
            value = self.construct_object(value_node, deep=deep)
            if key_node.comment:
                typ._yaml_add_comment(key_node.comment, key=key)
            if value_node.comment:
                typ._yaml_add_comment(value_node.comment, value=key)
            typ.add(key)

    def construct_yaml_seq(self, node):
        data = CommentedSeq()
        data._yaml_set_line_col(node.start_mark.line, node.start_mark.column)
        if node.flow_style is True:
            data.fa.set_flow_style()
        elif node.flow_style is False:
            data.fa.set_block_style()
        if node.comment:
            data._yaml_add_comment(node.comment)
        yield data
        data.extend(self.construct_sequence(node, data))

    def construct_yaml_map(self, node):
        data = CommentedMap()
        data._yaml_set_line_col(node.start_mark.line, node.start_mark.column)
        if node.flow_style is True:
            data.fa.set_flow_style()
        elif node.flow_style is False:
            data.fa.set_block_style()
        yield data
        self.construct_mapping(node, data)

    def construct_yaml_omap(self, node):
        # Note: we do now check for duplicate keys
        omap = CommentedOrderedMap()
        omap._yaml_set_line_col(node.start_mark.line, node.start_mark.column)
        if node.flow_style is True:
            omap.fa.set_flow_style()
        elif node.flow_style is False:
            omap.fa.set_block_style()
        yield omap
        if node.comment:
            omap._yaml_add_comment(node.comment[:2])
            if len(node.comment) > 2:
                omap.yaml_end_comment_extend(node.comment[2], clear=True)
        if not isinstance(node, SequenceNode):
            raise ConstructorError(
                "while constructing an ordered map", node.start_mark,
                "expected a sequence, but found %s" % node.id, node.start_mark)
        for subnode in node.value:
            if not isinstance(subnode, MappingNode):
                raise ConstructorError(
                    "while constructing an ordered map", node.start_mark,
                    "expected a mapping of length 1, but found %s" %
                    subnode.id,
                    subnode.start_mark)
            if len(subnode.value) != 1:
                raise ConstructorError(
                    "while constructing an ordered map", node.start_mark,
                    "expected a single mapping item, but found %d items" %
                    len(subnode.value),
                    subnode.start_mark)
            key_node, value_node = subnode.value[0]
            key = self.construct_object(key_node)
            assert key not in omap
            value = self.construct_object(value_node)
            if key_node.comment:
                omap._yaml_add_comment(key_node.comment, key=key)
            if subnode.comment:
                omap._yaml_add_comment(subnode.comment, key=key)
            if value_node.comment:
                omap._yaml_add_comment(value_node.comment, value=key)
            omap[key] = value

    def construct_yaml_set(self, node):
        data = CommentedSet()
        data._yaml_set_line_col(node.start_mark.line, node.start_mark.column)
        yield data
        self.construct_setting(node, data)

RoundTripConstructor.add_constructor(
    u'tag:yaml.org,2002:null',
    RoundTripConstructor.construct_yaml_null)

RoundTripConstructor.add_constructor(
    u'tag:yaml.org,2002:bool',
    RoundTripConstructor.construct_yaml_bool)

RoundTripConstructor.add_constructor(
    u'tag:yaml.org,2002:int',
    RoundTripConstructor.construct_yaml_int)

RoundTripConstructor.add_constructor(
    u'tag:yaml.org,2002:float',
    RoundTripConstructor.construct_yaml_float)

RoundTripConstructor.add_constructor(
    u'tag:yaml.org,2002:binary',
    RoundTripConstructor.construct_yaml_binary)

RoundTripConstructor.add_constructor(
    u'tag:yaml.org,2002:timestamp',
    RoundTripConstructor.construct_yaml_timestamp)

RoundTripConstructor.add_constructor(
    u'tag:yaml.org,2002:omap',
    RoundTripConstructor.construct_yaml_omap)

RoundTripConstructor.add_constructor(
    u'tag:yaml.org,2002:pairs',
    RoundTripConstructor.construct_yaml_pairs)

RoundTripConstructor.add_constructor(
    u'tag:yaml.org,2002:set',
    RoundTripConstructor.construct_yaml_set)

RoundTripConstructor.add_constructor(
    u'tag:yaml.org,2002:str',
    RoundTripConstructor.construct_yaml_str)

RoundTripConstructor.add_constructor(
    u'tag:yaml.org,2002:seq',
    RoundTripConstructor.construct_yaml_seq)

RoundTripConstructor.add_constructor(
    u'tag:yaml.org,2002:map',
    RoundTripConstructor.construct_yaml_map)

RoundTripConstructor.add_constructor(
    None, RoundTripConstructor.construct_undefined)

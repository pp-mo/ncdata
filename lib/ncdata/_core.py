"""
Our main classes for representing netCDF data.

These structures support groups, variables, attributes.
Both data and attributes are stored as numpy-compatible array-like values (though this
may include dask.array.Array), and hence their types are modelled as np.dtype's.

Current limitations :
(1) we are *not* supporting user-defined or variable-length types.
(2) there is no built-in consistency checking -- e.g. for correct length or existence
of dimensions referenced by variables.

"""
from functools import wraps
from typing import \
    Any, Dict, Iterable, Mapping, Optional, Tuple, Union, MutableMapping

import numpy
import numpy as np


class NameMap(dict):
    """
    A specialised dictionary type for data manipulation convenience.

    All values (aka 'content items') are expected to have a ".name" property which is a
    string, and we aim to ensure that "value.name == key" for each key, value pair.

    This "item key relation" is *not* rigorously enforced, but we provide convenience
    methods which make use of it and help to maintain it :
    See :meth:`NameMap.add`, :meth:`NameMap.addall` :meth:`NameMap.from_items` and
    :meth:`NameMap.rename`.

    ..
    """

    def __init__(self, *args, item_type=None, **kwargs):
        """
        Create a NameMap with dict-style constructor behaviour.

        For example, from key/value pairs.

        Notes
        -----
        A keyword-only 'item_type' arg sets the 'item_type' property.

        Creation using :meth:`NameMap.from_items` is generally more convenient.
        """
        super().__init__(*args, **kwargs)
        #: expected type of all content items (if not None)
        self.item_type = item_type

    def copy(self) -> "NameMap":
        """Produce a new NameMap with same content and item_type."""
        # NOTE: dict.copy() produces a dict, and will not duplicate 'item_type'.
        return NameMap.from_items(self.values(), item_type=self.item_type)

    def add(self, item):
        """
        Enter a content item under its '.name'.

        If the NameMap has a non-None 'item_type', the added item is type checked.
        """
        if self.item_type is not None:
            if not isinstance(item, self.item_type):
                raise TypeError(
                    f'Item expected to be of type {self.item_type} : got {item}."'
                )
        if not hasattr(item, "name"):
            raise TypeError(f"Item has no '.name' property : {item}.")
        self[item.name] = item

    def addall(self, items):
        """Add a number of content items with self.add()."""
        for item in items:
            self.add(item)

    def rename(self, name: str, new_name: str):
        """
        Rename a content item.

        Parameters
        ----------
        name
            name of an existing item.  If not, a KeyError will occur.

        new_name
            new name for the selected item.  Both the container key and its ".name"
            will be changed.

        Notes
        -----
        The order of items is preserved.

        If "new_name == name", has no effect.  Otherwise, if `new_name` already exists,
        the old item of that name is removed, but the renamed item remains in its
        original order place.

        Examples
        --------
        >>> mymap = NameMap.from_items([NcAttribute(x, x.upper()) for x in "abcd"])
        >>> mymap
        {'a': NcAttribute('a', 'A'), 'b': NcAttribute('b', 'B'), 'c': NcAttribute('c', 'C'), 'd': NcAttribute('d', 'D')}
        >>> mymap.rename('b', 'qqq')
        >>> mymap
        {'a': NcAttribute('a', 'A'), 'qqq': NcAttribute('qqq', 'B'), 'c': NcAttribute('c', 'C'), 'd': NcAttribute('d', 'D')}
        >>> mymap.rename('a', 'c')
        >>> mymap
        {'c': NcAttribute('c', 'A'), 'qqq': NcAttribute('qqq', 'B'), 'd': NcAttribute('d', 'D')}
        """
        if new_name == name:
            # skip this case, to avoid removing the item because it matches 'new_name'.
            pass
        else:
            # Since keys are immutable, we can't change a key in-place. So to preserve
            # item order within the container, we extract all items + re-insert them.
            # Get all items in original order, except an existing item of the new name
            items = [item for key, item in self.items() if key != new_name]
            # rename the selected item object (meaning it no longer matches its key)
            self[name].name = new_name
            # clear content and re-insert items in the original order.
            self.clear()
            self.addall(items)

    @classmethod
    def from_items(
        cls, arg: Union[Iterable, Mapping], item_type=None
    ) -> "NameMap":
        """
        Convert an iterable or mapping of items to a NameMap.

        Parameters
        ----------
        arg
            an iterable or mapping of 'content items'.

        item_type
            if not None, we expect all contents to be of this type.

        Returns
        -------
        map
            a NameMap with the given 'item_type'

        Notes
        -----
        All content items must have a ".name" property.  If 'item_type' is not None,
        all items must be of the given type.

        If 'arg' is an iterable, its contents are added.

        If 'arg' is a mapping, it normally must have (key == arg[key].name)
        for all keys.  As a special case, only if `item_type` ==
        :class:`NcAttribute`, a plain name: value map can be provided, which
        is converted to name: NcAttribute(name, value).

        If 'arg'' is a NameMap of the same 'item_type' (including None), then 'arg'
        is returned unchanged as the result.

        If the input is a NameMap of a different 'item_type', it is converted to a new
        NameMap of the required 'item_type' (assuming contents match the requirement).
        """
        if isinstance(arg, cls):
            if arg.item_type == item_type:
                # If input is of required type, this is a no-copy operation.
                result = arg
            else:
                # Replace with a map of of the required type.
                result = cls(item_type=item_type)
                result.addall(arg.values())
        else:
            # Start with an empty map of the required type.
            result = cls(item_type=item_type)
            if arg is not None:
                # We expect either another type of dictionary, or a list of items.
                if isinstance(arg, Mapping):
                    if (
                        item_type == NcAttribute
                        and len(arg) > 0
                        and not isinstance(
                            next(iter(arg.values())), NcAttribute
                        )
                    ):
                        # for attributes only, also allow simple name=value map
                        # for which, convert each value to an NcAttribute
                        arg = {
                            name: NcAttribute(name, value)
                            for name, value in arg.items()
                        }
                    # existing mapping of NameMap type
                    # ignore mapping keys, and set [name]=item.name for each value.
                    result.addall(arg.values())
                elif isinstance(arg, Iterable):
                    result.addall(arg)
                else:
                    msg = (
                        f"Argument must be an iterable or mapping: got {arg}."
                    )
                    raise TypeError(msg)

        return result


# A convenient name alias for :meth:`NameMap.from_items`.
as_namemap = NameMap.from_items


class AttributesDict(MutableMapping):
    """
    A container for the attribute values of an NcData or NcVariable object.

    Its values are actually stored in the ._attributes of the parent object, which is a
    :class:`NameMap` of :class:`NcAttribute` objects.
    This means that all attribute values are cast to/from valid NcAttribute values,
    i.e. numpy arrays of selected dtypes and <=1 dimensions.

    This allows "data.attributes" to provide the easy-access form {name: value},
    while "data._attributes" is the NameMap {name: NcAttribute}.

    """
    def __init__(self, attrs: NameMap):
        self._attrs = attrs

    def __getitem__(self, key):
        return self._attrs[key].as_python_value()

    def __setitem__(self, key, value):
        self._attrs[key] = NcAttribute(key, value)

    #
    # Provide the minimal set of methods required for a MutableMapping
    #
    def __len__(self):
        return len(self._attrs)

    def __iter__(self):
        return iter(self._attrs)

    def __delitem__(self, key):
        self._attrs.__delitem__(key)

    #
    # Provide a convenient string representation, somewhat consistent with how we print
    #  the attributes in the printout of an NcData / NcVariable
    #
    def __str__(self):
        text = "AttributesDict("
        if not self._attrs:
            text += ")"
        else:
            for attr in self._attrs.values():
                text += f"\n    {attr.name}: {attr._print_value()}"
            text += "\n)"

        return text

    # Also really nice-to-have : the "rename" operation, as implemented by NameMap
    @wraps(NameMap.rename)
    def rename(self, name: str, new_name: str):
        self._attrs.rename(name, new_name)


class _AttributeAccessMixin:
    """
    A mixin with attribute access conveniences for NcData and NcVariable.

    This assists in assigning and extracting attributes as python values.
    See :meth:`NcAttribute.get_python_value()` for how different types are handled.
    """
    @property
    def attributes(self):
        """
        A dictionary of an NcData or NcVariable's attribute values.

        This is used for the ``data.attributes`` property, which is a simple
        {keyname: value} map.  Numeric values are presented as numpy scalars, i.e.
        integers or strings.  The advantage of this is that they retain an exact dtype,
        e.g. np.int16 or np.float32.  These are almost entirely interchangeable with
        Python ints and floats.
        Multiple values are represented as 1-D numpy arrays.  These are iterable, so
        largely interchangeable with lists.
        String attributes are simply given as Python strings.
        See :ref:`attribute-dtypes`.

        The attributes of an NcData or NcVariable are actually always **stored** in a
        private ``data._attributes`` property, which is a :class:`NameMap` of
        :class:`NcAttribute` objects, whose values are numpy arrays.
        So, this is **not** that map, but is a view onto it, with the contents converted
        to simple values for convenience -- see :meth:`NcAttribute.as_python_value`.
        """
        if not hasattr(self, "_attrmap"):
            self._attrmap = AttributesDict(self._attributes)
        return self._attrmap

    def get_attrval(self, name: str) -> Any:
        """
        Get the Python value of a named attribute in self.attributes.

        If no such attribute exists, returns None.

        .. warning::
            This legacy method is now deprecated, and will be removed in a future release.

        """
        return self.attributes.get(name, None)

    def set_attrval(self, name: str, value) -> "NcAttribute":
        """
        Set the Python value of a named attribute in self.attributes.

        .. warning::
            This legacy method is now deprecated, and will be removed in a future release.

        """
        self.attributes[name] = value
        attr = self.attributes[name]
        return attr


#
# A relatively simple and naive representation of netCDF data.
#


def _addlines_indent(text, indent=""):
    # Routine to indent each line within a newline-joined string.
    return [indent + line for line in text.split("\n")]


# common indent spacing
_indent = " " * 4


class NcData(_AttributeAccessMixin):
    """
    An object representing a netcdf group- or dataset-level container.

    Containing dimensions, variables, attributes and sub-groups.
    """

    def __init__(
        self,
        name: Optional[str] = None,
        dimensions: Union[Mapping, Iterable] = None,
        variables: Union[Mapping, Iterable] = None,
        attributes: Union[Mapping, Iterable] = None,
        groups: Union[Mapping, Iterable] = None,
    ):  # noqa: D107
        #: a group/dataset name (optional)
        self.name: str = name
        #: group/dataset dimensions
        self.dimensions: Dict[str, "NcDimension"] = as_namemap(
            dimensions, NcDimension
        )
        #: group/dataset variables
        self.variables: Dict[str, "NcVariable"] = as_namemap(
            variables, NcVariable
        )
        #: group/dataset global attributes
        self._attributes: Dict[str, "NcAttribute"] = as_namemap(
            attributes, NcAttribute
        )
        #: sub-groups
        self.groups: Dict[str, "NcData"] = as_namemap(groups, NcData)

    def _print_content(self) -> str:
        """
        Construct a string printout.

        NcData classes all define '_print_content' (though they have no common base
        class, so it isn't technically an abstract method).
        This "NcData._print_content()" is called recursively for groups.
        """
        global _indent
        # Define a header line (always a separate line).
        noname = "<'no-name'>"
        lines = [f"<NcData: {self.name or noname}"]

        # Add internal sections in order, indenting everything.
        for eltype in ("dimensions", "variables", "groups", "attributes"):
            els = getattr(self, eltype)
            if len(els):
                if eltype == "attributes":
                    # Attributes a bit different: #1 add 'globol' to section title.
                    lines += [f"{_indent}global attributes:"]
                    # NOTE: #2 show like variable attributes, but *no parent name*.
                    attrs_lines = [
                        f":{attr._print_content()}"
                        for attr in self._attributes.values()
                    ]
                    lines += _addlines_indent(
                        "\n".join(attrs_lines), _indent * 2
                    )
                else:
                    lines += [f"{_indent}{eltype}:"]
                    for el in els.values():
                        lines += _addlines_indent(
                            el._print_content(), _indent * 2
                        )
                lines.append("")

        # Strip off final blank lines (tidier for Groups as well as main dataset).
        while len(lines[-1]) == 0:
            lines = lines[:-1]

        # Add closing line.
        lines += [">"]
        # Join with linefeeds for a simple string result.
        return "\n".join(lines)

    def __str__(self):  # noqa: D105
        return self._print_content()

    # NOTE: for 'repr', an interpretable literal string is too complex.
    # So just retain the default "object" address-based representation.

    def copy(self):
        """
        Copy self.

        This duplicates structure with all-new ncdata core objects, but does not
        duplicate variable data arrays.  See :func:`ncdata.utils.ncdata_copy`.
        """
        from ncdata.utils import ncdata_copy

        return ncdata_copy(self)


class NcDimension:
    """
    An object representing a netcdf dimension.

    Associates a name with a length, and also an 'unlimited' flag.
    """

    def __init__(
        self, name: str, size: int, unlimited: Optional[bool] = None
    ):  # noqa: D107
        #: dimension name
        self.name: str = name
        #: dimension size (current size, if unlimited)
        self.size: int = size  # N.B. we retain the 'zero size means unlimited'
        if size == 0:
            unlimited = True
        else:
            unlimited = bool(unlimited)
        #: whether dimension is unlimited
        self.unlimited: bool = unlimited

    def _print_content(self) -> str:  # noqa: D105
        str_unlim = "  **UNLIMITED**" if self.unlimited else ""
        return f"{self.name} = {self.size}{str_unlim}"

    def __repr__(self):  # noqa: D105
        str_unlim = ", unlimited=True" if self.unlimited else ""
        return f"NcDimension({self.name!r}, {self.size}{str_unlim})"

    def __str__(self):  # noqa: D105
        return repr(self)

    def copy(self):
        """Copy self."""
        return NcDimension(self.name, size=self.size, unlimited=self.unlimited)

    def __eq__(self, other):
        """Support simply equality testing."""
        return (
            self.name == other.name
            and self.size == other.size
            and self.unlimited == other.unlimited
        )


class NcVariable(_AttributeAccessMixin):
    """
    An object representing a netcdf variable.

    With dimensions, dtype and data, and attributes.

    'data' may be None, but if not is expected to be an array : either numpy (real) or
    Dask (lazy).

    The 'dtype' will presumably match the data, if any.

    It has no 'shape' property, in practice this might be inferred from either the
    data or dimensions.  If the dims are empty, it is a scalar.

    A variable makes no effort to ensure that its dimensions, dtype + data are
    consistent.  This is to be managed by the creator.
    """

    def __init__(
        self,
        name: str,
        dimensions: Iterable[str] = (),
        # NOTE: flake8 objects to type checking against an unimported package, even in
        # a quoted reference when it's not otherwise needed (and we don't want to
        # import it).
        # TODO: remove the flake8 annotation if this gets fixed.
        data: Optional[
            Union[np.ndarray, "dask.array.array"]  # noqa: F821
        ] = None,
        dtype: np.dtype = None,
        attributes: Union[Mapping, Iterable] = None,
        group: "NcData" = None,
    ):
        """
        Create a variable.

        The 'dtype' arg is relevant only when no data is provided :
        If 'data' is provided, it is converted to an array if needed, and its dtype
        replaces any provided 'dtype'.
        """
        #: variable name
        self.name: str = name
        #: variable dimension names (a list of strings, *not* a dict of objects)
        self.dimensions: Tuple[str] = tuple(dimensions)
        if data is not None:
            if not hasattr(data, "dtype"):
                data = np.asanyarray(data)
            dtype = data.dtype
        #: variable datatype, as a numpy :class:`numpy.dtype`
        if dtype is not None and not isinstance(dtype, np.dtype):
            dtype = np.dtype(dtype)
        self.dtype: numpy.dtype = dtype
        #: variable data (an array-like, typically a dask or numpy array)
        self.data = data  # Supports lazy, and normally provides a dtype
        #: variable attributes
        self._attributes: NameMap = as_namemap(attributes, NcAttribute)
        #: parent group
        self.group: Optional[NcData] = group

    # # Provide some array-like readonly properties reflected from the data.
    # @property
    # def dtype(self):
    #     return self.data.dtype
    #
    # @property
    # def shape(self):
    #     return self.data.shape

    def _print_content(self):
        global _indent
        dimstr = ", ".join(self.dimensions)
        typestr = str(self.dtype) if self.dtype else "<no-dtype>"
        hdr = f"<NcVariable({typestr}): {self.name}({dimstr})"
        if not self.attributes:
            hdr += ">"
            lines = [hdr]
        else:
            lines = [hdr]
            attrs_lines = [
                f"{self.name}:{attr._print_content()}"
                for attr in self._attributes.values()
            ]
            lines += _addlines_indent("\n".join(attrs_lines), _indent)
            lines += [">"]
        return "\n".join(lines)

    def __str__(self):  # noqa: D105
        return self._print_content()

    # NOTE: as for NcData, an interpretable 'repr' string is too complex.
    # So just retain the default "object" address-based representation.

    def copy(self):
        """
        Copy self.

        Does not duplicate arrays in data content.
        See :func:`ncdata.utils.ncdata_copy`.
        """
        from ncdata.utils._copy import _attributes_copy

        var = NcVariable(
            name=self.name,
            dimensions=self.dimensions,
            dtype=self.dtype,
            data=self.data,
            attributes=_attributes_copy(self._attributes),
            group=self.group,
        )
        return var


class NcAttribute:
    """
    An object representing a netcdf variable, group or dataset attribute.

    Associates a name to a value which is always a numpy scalar or 1-D array, of an
    allowed dtype.  See :ref:`attribute-dtypes`.

    In an actual netcdf dataset, a "scalar" is actually just an array of length 1.
    """

    def __init__(self, name: str, value):  # noqa: D107
        #: attribute name
        self.name: str = name
        # Attribute values are arraylike, have dtype
        #: attribute value, constrained to a suitable numpy array object.
        self.value: np.ndarray = value

    @property
    def value(self):  # noqa: D102
        return self._value

    @value.setter
    def value(self, value):
        if not hasattr(value, "dtype"):
            value = np.asanyarray(value)
        if value.ndim > 1:
            raise ValueError(
                "Attribute value should only be 0- or 1-dimensional."
            )
        self._value = value

    def as_python_value(self):
        """
        Return the content, but converting any character data to Python strings.

        An array of 1 value returns as a single scalar value, since this is how
        attributes behave in actual netcdf data.

        We don't bother converting numeric data, since numpy scalars are generally
        interchangeable in use with Python ints or floats.
        """
        result = self.value
        # Attributes are either scalar or 1-D
        if result.ndim >= 2:
            raise ValueError(
                "Attribute value should only be 0- or 1-dimensional."
            )

        if result.shape == (1,):
            # Reduce the dimension, but *always* return an array scalar.
            # This is useful for consistency of handling non-numpy content
            result = result[0]
            result = np.asanyarray(result)

        if result.dtype.kind in ("U", "S"):
            if result.ndim == 0:
                result = str(result)
            elif result.ndim == 1:
                result = [str(x) for x in result]

        # TODO: is this a possibiliity ?
        # if isinstance(result, bytes):
        #     result = result.decode()
        return result

    def _print_value(self):
        value = self.as_python_value()

        # Convert numpy non-string scalars to simple Python values, in string output.
        if getattr(value, "shape", None) in ((0,), (1,), ()):
            op = {"i": int, "u": int, "f": float}.get(value.dtype.kind)
            if op:
                value = op(value.flatten()[0])

        return repr(value)

    def _print_content(self):
        return f"{self.name} = {self._print_value()}"

    def __repr__(self):  # noqa: D105
        return f"NcAttribute({self.name!r}, {self._print_value()})"

    def __str__(self):  # noqa: D105
        return repr(self)

    def copy(self):
        """Copy self, including any array value content."""
        return NcAttribute(self.name, self.value.copy())

    def __eq__(self, other):
        """Support simple equality testing."""
        if not isinstance(other, NcAttribute):
            result = NotImplemented
        else:
            result = self.name == other.name
            if result:
                v1 = self.value
                v2 = other.value
                result = (
                    v1.shape == v2.shape
                    and v1.dtype == v2.dtype
                    and np.all(v1 == v2)
                )
        return result

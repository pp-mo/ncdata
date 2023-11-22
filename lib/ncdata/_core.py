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
from typing import Dict, List, Optional, Tuple, Union

import numpy
import numpy as np

#
# A totally basic and naive representation of netCDF data.
#


def _addlines_indent(text, indent=""):
    # Routine to indent each line within a newline-joined string.
    return [indent + line for line in text.split("\n")]


# common indent spacing
_indent = " " * 4


class NcData:
    """
    An object representing a netcdf group- or dataset-level container.

    Containing dimensions, variables, attributes and sub-groups.
    """

    def __init__(
        self,
        name: Optional[str] = None,
        dimensions: Dict[str, "NcDimension"] = None,
        variables: Dict[str, "NcVariable"] = None,
        attributes: Dict[str, "NcAttribute"] = None,
        groups: Dict[str, "NcData"] = None,
    ):  # noqa: D107
        #: a group/dataset name (optional)
        self.name: str = name
        #: group/dataset dimensions
        self.dimensions: Dict[str, "NcDimension"] = dimensions or {}
        #: group/dataset variables
        self.variables: Dict[str, "NcVariable"] = variables or {}
        #: group/dataset global attributes
        self.attributes: Dict[str, "NcAttribute"] = attributes or {}
        #: sub-groups
        self.groups: Dict[str, "NcData"] = groups or {}

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
                        for attr in self.attributes.values()
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


class NcDimension:
    """
    An object representing a netcdf dimension.

    Associates a length with a name.
    A length of 0 indicates an "unlimited" dimension, though that is essentially a
    file-specific concept.
    """

    # TODO : I think the unlimited interpretation is limiting, since we will want to
    #  represent "current length" too.
    #  ? Change this by adopting a boolean "is_unlimited" property ?

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


class NcVariable:
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
        dimensions: Tuple[str] = (),
        # NOTE: flake8 objects to type checking against an unimported package, even in
        # a quoted reference when it's not otherwise needed (and we don't want to
        # import it).
        # TODO: remove the flake8 annotation if this gets fixed.
        data: Optional[
            Union[np.ndarray, "dask.array.array"]  # noqa: F821
        ] = None,
        dtype: np.dtype = None,
        attributes: Dict[str, "NcAttribute"] = None,
        group: "NcData" = None,
    ):
        """
        Create a variable.

        The 'dtype' arg relevant only when no data is provided :
        If 'data' is provided, it is converted to an array if needed, and its dtype
        replaces any provided 'dtype'.
        """
        #: variable name
        self.name: str = name
        #: variable dimension names (a list of strings, *not* a dict of objects)
        self.dimensions: List[str] = tuple(dimensions)
        if data is not None:
            if not hasattr(data, "dtype"):
                data = np.asanyarray(data)
            dtype = data.dtype
        #: variable datatype, as a numpy :class:`numpy.dtype`
        self.dtype: numpy.dtype = dtype
        #: variable data (an array-like, typically a dask or numpy array)
        self.data = data  # Supports lazy, and normally provides a dtype
        #: variable attributes
        self.attributes: Dict[str, NcAttribute] = attributes or {}
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
                for attr in self.attributes.values()
            ]
            lines += _addlines_indent("\n".join(attrs_lines), _indent)
            lines += [">"]
        return "\n".join(lines)

    def __str__(self):  # noqa: D105
        return self._print_content()

    # NOTE: as for NcData, an interpretable 'repr' string is too complex.
    # So just retain the default "object" address-based representation.


class NcAttribute:
    """
    An object representing a netcdf variable or dataset attribute.

    Associates a name to a value which is a numpy scalar or 1-D array.

    We expect the value to be 0- or 1-dimensional, and an allowed dtype.
    However none of this is checked.

    In an actual netcdf dataset, a "scalar" is actually just an array of length 1.
    """

    def __init__(self, name: str, value):  # noqa: D107
        #: attribute name
        self.name: str = name
        # Attribute values are arraylike, have dtype
        # TODO: may need to regularise string representations?
        if not hasattr(value, "dtype"):
            value = np.asanyarray(value)
        #: attribute value
        self.value: np.ndarray = value

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
            result = result[0]

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
            op = {"i": int, "u": int, "f": float}[value.dtype.kind]
            value = op(value.flatten()[0])

        return repr(value)

    def _print_content(self):
        return f"{self.name} = {self._print_value()}"

    def __repr__(self):  # noqa: D105
        return f"NcAttribute({self.name!r}, {self._print_value()})"

    def __str__(self):  # noqa: D105
        return repr(self)

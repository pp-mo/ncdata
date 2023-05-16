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
from typing import Dict, Optional, Tuple, Union

import numpy as np

#
# A totally basic and naive representation of netCDF data.
#


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
    ):
        #: a group/dataset name : optional
        self.name: str = name
        self.dimensions: Dict[str, "NcDimension"] = dimensions or {}
        self.variables: Dict[str, "NcVariable"] = variables or {}
        self.attributes: Dict[str, "NcAttribute"] = attributes or {}
        self.groups: Dict[str, "NcData"] = groups or {}


class NcDimension:
    """
    An object representing a netcdf dimension.

    Associates a length with a name.
    A length of 0 indicates an "unlimited" dimension, though that is essentially a
    file-specific concept.

    TODO: I think the unlimited interpretation is limiting, since we will want to
     represent "current length" too :  Change this by defining a boolean with
     'is_unlimited' meaning.
    """

    def __init__(self, name: str, size: int = 0):
        self.name: str = name
        self.size: int = size  # N.B. we retain the 'zero size means unlimited'


class NcVariable:
    """
    An object representing a netcdf variable.

    With dimensions, dtype and data, and attributes.

    'data' may be None, but if not is expected to be an array : either numpy (real) or
    Dask (lazy).

    The 'dtype' will presumably should match the data, if any.

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
        self.name = name
        self.dimensions = tuple(dimensions)
        if data is not None:
            if not hasattr(data, "dtype"):
                data = np.asanyarray(data)
            dtype = data.dtype
        self.dtype = dtype
        self.data = data  # Supports lazy, and normally provides a dtype
        self.attributes = attributes or {}
        self.group = group

    # # Provide some array-like readonly properties reflected from the data.
    # @property
    # def dtype(self):
    #     return self.data.dtype
    #
    # @property
    # def shape(self):
    #     return self.data.shape


class NcAttribute:
    """
    An object representing a netcdf variable or dataset attribute.

    Associates a name to a value which is either a numpy 1-D array or scalar.

    We expect the value to be 0- or 1-dimensional, and an allowed dtype.
    However none of this is checked.

    In an actual netcdf dataset, a "scalar" is actually just an array of length 1.
    """

    def __init__(self, name: str, value):
        self.name: str = name
        # Attribute values are arraylike, have dtype
        # TODO: may need to regularise string representations?
        if not hasattr(value, "dtype"):
            value = np.asanyarray(value)
        self.value: np.ndarray = value

    def _as_python_value(self):
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

# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""
Our basic representation classes for netCDF4 data.

These structures support groups, variables, attributes.
Both data and attributes are stored as numpy-compatible array-like values (though this
may include dask.array.Array), and hence their types are modelled as np.dtype's.

Current limitations :
(1) we are *not* supporting user-defined or variable-length types.
(2) there is no built-in consistency checking -- e.g. for correct length or existence
of dimensions referenced by variables.

"""
from typing import Dict, Optional, Tuple

import numpy as np

#
# A totally basic and naive representation of netCDF data.
#


class NcData:
    def __init__(
        self,
        name: Optional[str] = None,
        dimensions: Dict[str, "NcDimension"] = None,
        variables: Dict[str, "NcVariable"] = None,
        attributes: Dict[str, "NcAttribute"] = None,
        groups: Dict[str, "NcData"] = None,
    ):
        self.name: str = name
        self.dimensions: Dict[str, "NcDimension"] = dimensions or {}
        self.variables: Dict[str, "NcVariable"] = variables or {}
        self.attributes: Dict[str, "NcAttribute"] = attributes or {}
        self.groups: Dict[str, "NcData"] = groups or {}


class NcDimension:
    def __init__(self, name: str, size: int = 0):
        self.name: str = name
        self.size: int = size  # N.B. we retain the 'zero size means unlimited'


class NcVariable:
    def __init__(
        self,
        name: str,
        dimensions: Tuple[str] = None,
        data: np.ndarray = None,
        dtype: np.dtype = None,
        attributes: Dict[str, "NcAttribute"] = None,
        group: "NcData" = None,
    ):
        self.name = name
        self.dimensions = tuple(dimensions or ())
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
    def __init__(self, name: str, value):
        self.name: str = name
        # Attribute values are arraylike, have dtype
        # TODO: may need to regularise string representations?
        if not hasattr(value, "dtype"):
            value = np.asanyarray(value)
        self.value: np.ndarray = value

    def _as_python_value(self):
        result = self.value
        if result.dtype.kind in ("U", "S"):
            result = str(result)
            if isinstance(result, bytes):
                result = result.decode()
        return result

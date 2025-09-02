"""Unit tests for :mod:`ncdata.utils._dim_indexing`."""

import numpy as np
from ncdata import NcData, NcDimension, NcVariable


def dims_test_data(x, y):
    """
    Generate a test dataset that we can slice in various ways.

    If 'x' or 'y' are lists (~arrays) then make an X/Y dimension with thesee values,
    otherwise if they are a scalar value then not, mimicking numpy indexing away of a
    dimension.

    Also add a separate Z dimension, plus variables mapping every combination of
    X,Y,Z and no dimension.

    Also include some Groups and Attributes to ensure preservation of all structure and
    metadata.
    """
    data = NcData(
        dimensions=[NcDimension("Z", 2)],
        variables=[
            NcVariable("var_0", [], data=np.array(1.2)),
            NcVariable(
                "var_Z",
                ["Z"],
                data=np.linspace(1.3, 2.3, 2),
                attributes={"role": "Z dim var"},
            ),
        ],
        attributes={"global": "common_value"},
    )

    x, y = [np.asarray(key) for key in (x, y)]

    data.variables.add(
        NcVariable(
            "yvals",
            ["Y"] if y.ndim else [],
            data=2.2 * np.ones(y.shape),
            attributes={"role": "y values", "units": "ft"},
        )
    )
    if y.ndim:
        data.dimensions.add(NcDimension("Y", len(y)))
        ydims = ["Y"]
    else:
        ydims = []

    data.variables.add(
        NcVariable("Y", ydims, data=y, attributes={"role": "Y dim var"})
    )

    data.variables.add(
        NcVariable(
            "xvals",
            ["X"] if x.ndim else [],
            data=3.3 * np.ones(x.shape),
            attributes={"role": "x values", "units": "m"},
        )
    )
    if x.ndim:
        data.dimensions.add(NcDimension("X", len(x)))
        xdims = ["X"]
    else:
        xdims = []

    data.variables.add(
        NcVariable("X", xdims, data=x, attributes={"role": "X dim var"})
    )
    xydims = ["Z"] + (["Y"] if y.ndim else []) + (["X"] if x.ndim else [])
    shape = [2] + ([len(y)] if y.ndim else []) + ([len(x)] if x.ndim else [])
    data.variables.add(
        NcVariable(
            "zyx_vals",
            xydims,
            data=np.ones(shape),
            attributes={"role": "data"},
        )
    )

    return data

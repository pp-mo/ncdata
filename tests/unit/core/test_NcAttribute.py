"""
Tests for class :class:`ncdata.NcAttribute`.

Very simple for now, but we may add more behaviour in future.
"""
import numpy as np
import pytest

from ncdata import NcAttribute

# Support for building testcases
_data_types = [
    "int",
    "float",
    "string",
    "numpyint",
    "numpyfloat",
    "numpystring",
]
_container_types = ["scalar", "vectorof1", "vectorofN"]
_attribute_testdata = {
    "int": [1, 2, 3, 4],
    "float": [1.2, 3.4, 5.6],
    "string": ["xx", "yyy", "z"],
}


@pytest.fixture(params=_data_types)
def datatype(request):
    return request.param


@pytest.fixture(params=_container_types)
def structuretype(request):
    return request.param


def attrvalue(datatype, structuretype):
    # get basic type = 'int', 'float', 'string'
    (datatype,) = (
        key for key in _attribute_testdata.keys() if key in datatype
    )

    # fetch a set of values
    values = _attribute_testdata[datatype]

    # pass as an array if specified
    if "numpy" in datatype:
        values = np.array(values)

    # pass a single value, or a list of 1, or a list of N
    if structuretype == "scalar":
        result = values[0]
    elif structuretype == "vectorof1":
        result = values[:1]
    else:
        assert structuretype == "vectorofN"
        result = values
    return result


class Test_NcAttribute__init__:
    def test_value(self, datatype, structuretype):
        value = attrvalue(datatype, structuretype)

        attr = NcAttribute("x", value=value)
        expected_array = np.asanyarray(value)

        assert isinstance(attr.value, np.ndarray)
        assert np.all(attr.value == expected_array)
        if hasattr(value, "dtype"):
            # An actual array is stored directly, i.e. without copying
            assert attr.value is value


class Test_NcAttribute__as_python_value:
    def test_value(self, datatype, structuretype):
        value = attrvalue(datatype, structuretype)
        attr = NcAttribute("x", value)

        result = attr.as_python_value()

        # Note: "vectorof1" data should appear as *scalar*.
        is_vector = "vectorofN" in structuretype
        is_string = "string" in datatype
        if is_string:
            # String data is returned as (lists of) strings
            if is_vector:
                assert isinstance(result, list)
                assert all(isinstance(x, str) for x in result)
            else:
                assert isinstance(result, str)
        else:
            # Numeric data is returned as arrays or array scalars.
            if is_vector:
                assert isinstance(result, np.ndarray)
                assert result.ndim == 1
            else:
                # array scalar
                assert result.shape == ()


class Test_NcAttribute__str_repr:
    def test_str(self, datatype, structuretype):
        value = attrvalue(datatype, structuretype)
        attr = NcAttribute("x", value)

        result = str(attr)
        if structuretype == "vectorofN":
            value_repr = repr(value)
            if "string" not in datatype:
                value_repr = f"array({value_repr})"
        else:
            value_single = np.array(value).flatten()[0]
            if "string" in datatype:
                value_repr = repr(value_single)
            else:
                value_repr = str(value_single)

        expect = f"NcAttribute('x', {value_repr})"
        assert result == expect

    def test_repr_same(self, datatype, structuretype):
        value = attrvalue(datatype, structuretype)
        attr = NcAttribute("x", value)
        result = str(attr)
        expected = repr(attr)
        assert result == expected

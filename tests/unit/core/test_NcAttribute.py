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
    "none",
    "custom",
    "numpyint",
    "numpyfloat",
    "numpystring",
    "numpynone",
    "numpycustom",
]
_container_types = ["scalar", "vectorof1", "vectorofN"]


class _OddObj:
    def __init__(self, x):
        self.x = x

    def __repr__(self):
        return f"<OddObj: {self.x!r}>"


_attribute_testdata = {
    "int": [1, 2, 3, 4],
    "float": [1.2, 3.4, 5.6],
    "string": ["xx", "yyy", "z"],
    "none": [None, None, None],
    "custom": [_OddObj(1), _OddObj("a"), _OddObj(None)],
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
                # scalar : result is *always* an array scalar (e.g. np.float64)
                assert result.shape == ()


class Test_NcAttribute__str_repr:
    def test_str(self, datatype, structuretype):
        value = attrvalue(datatype, structuretype)
        attr = NcAttribute("x", value)

        result = str(attr)

        # Work out what we expect/intend the value string to look like.
        is_multiple = structuretype == "vectorofN"
        if not is_multiple:
            assert structuretype in ("scalar", "vectorof1")
            # All single values appear as scalars.
            value = np.array(value).flatten()[0]

        value_repr = repr(value)

        is_non_numpy = "custom" in datatype or "none" in datatype
        if is_non_numpy or (is_multiple and "string" not in datatype):
            # Non-numpy data, and all *non-string* vectors appearnumpy 'array(...)'.
            # N.B. but *string vectors* print just as a list of Python strings.
            value_repr = repr(np.asanyarray(value))

        expect = f"NcAttribute('x', {value_repr})"
        assert result == expect

    def test_repr_same(self, datatype, structuretype):
        value = attrvalue(datatype, structuretype)
        attr = NcAttribute("x", value)
        result = str(attr)
        expected = repr(attr)
        assert result == expected

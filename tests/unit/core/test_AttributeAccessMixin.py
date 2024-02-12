"""
Tests for class :class:`ncdata._core._AttributeAccessMixin`.

Note: actually tested via the inheriting classes NcData and NcVariable.
All tests are run for both of those.
"""
import numpy as np
import pytest

from ncdata import NcAttribute, NcData, NcVariable


@pytest.fixture(params=["ncdata", "ncvariable"])
def sample_object(request):
    obj_class = {"ncdata": NcData, "ncvariable": NcVariable}[request.param]
    result = obj_class(name="sample")
    return result


class Test_AttributeAccesses:
    def test_gettattr(self, sample_object):
        content = np.array([1, 2])
        sample_object.attributes.add(NcAttribute("x", content))
        assert sample_object.get_attrval("x") is content

    def test_getattr_absent(self, sample_object):
        # Check that fetching a non-existent attribute returns None.
        sample_object.get_attrval("q") is None

    def test_setattr(self, sample_object):
        content = np.array([1, 2])
        sample_object.set_attrval("x", content)
        assert sample_object.attributes["x"].value is content

    def test_setattr__overwrite(self, sample_object):
        content = np.array([1, 2])
        sample_object.set_attrval("x", content)
        assert sample_object.attributes["x"].value is content
        sample_object.set_attrval("x", "replaced")
        assert list(sample_object.attributes.keys()) == ["x"]
        assert sample_object.attributes["x"].value == "replaced"

    def test_setattr_getattr_none(self, sample_object):
        # Check behaviour when an attribute is given a Python value of 'None'.
        # This is treated as array(None), so not like a missing attribute.
        sample_object.set_attrval("x", None)
        assert "x" in sample_object.attributes
        assert sample_object.attributes["x"].value == np.array(None)
        assert sample_object.get_attrval("x") == np.array(None)

    # Note: it makes sense to see what a Python value of "None" does, since it has a
    # particular meaning in the API here.
    # We don't test with other data types, since that is just the behaviours of
    # NcAttribute "__init__" and "as_python_value()", which are tested elsewhere.

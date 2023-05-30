"""Tests for class :class:`ncdata.NcData`.

There is almost no behaviour, but we can test some constructor usages.
"""
from ncdata import NcData


class Test_NcData__init__:
    def test_noargs(self):
        sample = NcData()
        assert sample.name is None
        assert sample.dimensions == {}
        assert sample.variables == {}
        assert sample.groups == {}
        assert sample.attributes == {}

    def test_allargs(self):
        # Since there is no type checking, you can put what you like in the "slots".
        name = "data_name"
        dims = {f"dimname_{i}": f"dim_{i}" for i in range(3)}
        vars = {f"varname_{i}": f"var_{i}" for i in range(5)}
        attrs = {f"varname_{i}": f"var_{i}" for i in range(6)}
        grps = {f"groupname_{i}": f"group_{i}" for i in range(3)}
        sample1 = NcData(
            name=name,
            dimensions=dims,
            variables=vars,
            attributes=attrs,
            groups=grps,
        )
        # Nothing is copied : all contents are simply references to the inputs
        assert sample1.name is name
        assert sample1.dimensions is dims
        assert sample1.variables is vars
        assert sample1.groups is grps
        assert sample1.attributes is attrs

        # Also check construction with arguments alone (no keywords).
        sample2 = NcData(name, dims, vars, attrs, grps)
        # result is a new object, but contents are references identical to the other
        assert sample2 is not sample1
        for name in dir(sample1):
            if not name.startswith("_"):
                assert getattr(sample2, name) is getattr(sample1, name)


# Note: str() and repr() of NcData are too complex to test unit-wise.
# See integration tests for some sample results.

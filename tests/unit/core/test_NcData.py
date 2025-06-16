"""Tests for class :class:`ncdata.NcData`.

There is almost no behaviour, but we can test some constructor usages.
"""
from ncdata import NcAttribute, NcData, NcDimension, NcVariable


class Test_NcData__init__:
    def test_noargs(self):
        sample = NcData()
        assert sample.name is None
        assert sample.dimensions == {}
        assert sample.variables == {}
        assert sample.groups == {}
        assert sample.attributes == {}

    def test_allargs(self):
        name = "data_name"
        dims = [NcDimension(f"dimname_{i}", i) for i in range(3)]
        vars = [NcVariable(f"varname_{i}", (), int) for i in range(5)]
        attrs = {f"attrname_{i}":  i for i in range(6)}
        grps = [NcData(f"groupname_{i}") for i in range(3)]
        sample1 = NcData(
            name=name,
            dimensions=dims,
            variables=vars,
            attributes=attrs,
            groups=grps,
        )
        # Nothing is copied : all contents are simply references to the inputs
        assert sample1.name is name
        assert list(sample1.dimensions.values()) == dims
        assert sample1.dimensions.item_type == NcDimension
        assert list(sample1.variables.values()) == vars
        assert sample1.variables.item_type == NcVariable
        assert list(sample1.groups.values()) == grps
        assert sample1.groups.item_type == NcData
        assert sample1.attributes == attrs

        # Also check construction with arguments alone (no keywords).
        sample2 = NcData(name, dims, vars, attrs, grps)
        # result is a new object, but contents are references identical to the other
        assert sample2 is not sample1
        for name in ("dimensions", "variables", "attributes", "groups"):
            assert getattr(sample2, name) == getattr(sample1, name)


# Note: str() and repr() of NcData are too complex to test unit-wise.
# See integration tests for some sample results.


class Test_NcData_copy:
    # We only need to check that this calls "ncdata_copy", which is tested elsewhere.
    def test(self, mocker):
        mock_copied_ncdata = mocker.sentinel.copied_result
        mock_copycall = mocker.Mock(return_value=mock_copied_ncdata)
        mocker.patch("ncdata.utils.ncdata_copy", mock_copycall)
        ncdata = NcData()
        result = ncdata.copy()
        assert mock_copycall.called_once_witk(mocker.call(ncdata))
        assert result == mock_copied_ncdata

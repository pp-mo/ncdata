import numpy as np
import pytest

from ncdata import NcAttribute, NcData, NcDimension, NcVariable
from tests._compare_nc_datasets import compare_nc_datasets

# from tests.data_testcase_schemas import data_types
# data_types  # avoid 'unused' warning


@pytest.fixture(
    params=["in_named", "in_unnamed", "in_namedgroup", "in_unnamedgroup"]
)
def group_context(request):
    """
    The different contexts of locations in a dataset

    In which an element (dimension, group or variable) might be found, and which might
    appear different in the mismatch-error messages.
    """
    return request.param


@pytest.fixture(params=["on_group", "on_variable"])
def attr_context(request):
    """The different contexts for an attribute in a dataset."""
    return request.param


@pytest.fixture(params=["ordered", "unordered"])
def order_checking(request):
    """Whether to test with order checking or not."""
    return request.param


def location_prefix(group_context, attr_context="on_group"):
    prefix = "Dataset"
    if "namedgroup" in group_context:
        prefix += "/inner_group"
    if "variable" in attr_context:
        prefix += ' variable "vx"'
    return prefix


class TestCompareDimensions:
    def dimension_testdata(self, group_context):
        testdata = NcData(
            name="dataset_1",
            dimensions=[
                NcDimension("x", 2, unlimited=True),
                NcDimension("y", 3, unlimited=False),
            ],
        )

        if group_context == "in_named":
            pass
        elif group_context == "in_unnamed":
            testdata.name = None
        elif "group" in group_context:
            testdata.name = "inner_group"
            testdata = NcData(name="outer_dataset", groups=[testdata])
            if group_context == "in_namedgroup":
                pass
            elif group_context == "in_unnamedgroup":
                testdata.name = None
            else:
                raise ValueError(f"unknown group_context: {group_context!r}")
        else:
            raise ValueError(f"unknown group_context: {group_context!r}")

        return testdata

    def _datas_and_dims(self, group_context):
        data1, data2 = [
            self.dimension_testdata(group_context) for _ in range(2)
        ]
        location = data2
        if "group" in group_context:
            location = location.groups["inner_group"]
        return data1, data2, location.dimensions

    def test_name(self, group_context):
        data1, data2, dims = self._datas_and_dims(group_context=group_context)
        dims.rename("x", "q")
        errs = compare_nc_datasets(data1, data2)
        # TODO: this is wrong -- should be getting a message
        location_string = location_prefix(group_context)
        expected = [
            f"{location_string} dimension lists do not match: "
            "['x', 'y'] != ['q', 'y']"
        ]
        assert errs == expected

    def test_size(self, group_context):
        data1, data2, dims = self._datas_and_dims(group_context=group_context)
        dims["x"].size = 77

        errs = compare_nc_datasets(data1, data2)

        location_string = location_prefix(group_context)
        expected = [
            f'{location_string} "x" dimensions have different sizes: 2 != 77'
        ]
        # TODO: messages are possibly not ideal, should include dataset name ??
        assert errs == expected

    def test_unlimited(self, group_context):
        data1, data2, dims = self._datas_and_dims(group_context=group_context)
        dims["y"].unlimited = True

        errs = compare_nc_datasets(data1, data2)

        location_string = location_prefix(group_context)
        expected = [
            f'{location_string} "y" dimension has different "unlimited" status : '
            "False != True"
        ]
        # TODO: this is wrong -- should be getting a message
        assert errs == expected

    def test_ordering(self, group_context, order_checking):
        data1, data2, dims = self._datas_and_dims(group_context=group_context)
        all_dims = list(dims.values())
        dims.clear()
        dims.addall(all_dims[::-1])

        do_ordercheck = {"ordered": True, "unordered": False}[order_checking]
        errs = compare_nc_datasets(
            data1, data2, check_dims_order=do_ordercheck
        )

        if do_ordercheck:
            groupname = "/inner_group" if "group" in group_context else ""
            expected = [
                f"Dataset{groupname} dimension lists do not match: "
                "['x', 'y'] != ['y', 'x']"
            ]
        else:
            expected = []

        assert errs == expected


class TestCompareAttributes:
    def attribute_testdata(self, group_context):
        testdata = NcData(
            name="dataset_1",
            variables=[
                NcVariable(
                    "vx",
                    dimensions=[],
                    data=np.array(1.0),
                    attributes=[
                        NcAttribute("att1", 1),
                        NcAttribute("att2", 2),
                    ],
                )
            ],
            attributes=[
                NcAttribute("att1", 11),
                NcAttribute("att2", 12),
            ],
        )

        if group_context == "in_named":
            pass
        elif group_context == "in_unnamed":
            testdata.name = None
        elif "group" in group_context:
            testdata.name = "inner_group"
            testdata = NcData(name="outer_dataset", groups=[testdata])
            if group_context == "in_namedgroup":
                pass
            elif group_context == "in_unnamedgroup":
                testdata.name = None
            else:
                raise ValueError(f"unknown group_context: {group_context!r}")
        else:
            raise ValueError(f"unknown group_context: {group_context!r}")

        return testdata

    def _datas_and_attrs(self, group_context, attr_context):
        data1, data2 = [
            self.attribute_testdata(group_context) for _ in range(2)
        ]

        location = data2
        if "group" in group_context:
            location = location.groups["inner_group"]
        is_on_var = {"on_group": False, "on_variable": True}[attr_context]
        if is_on_var:
            location = location.variables["vx"]

        return data1, data2, location.attributes

    def test_name(self, group_context, attr_context):
        data1, data2, attrs = self._datas_and_attrs(
            group_context, attr_context
        )

        attrs.rename("att1", "changed")
        errs = compare_nc_datasets(data1, data2)

        expected = [
            "Dataset attribute lists do not match: "
            "['att1', 'att2'] != ['changed', 'att2']"
        ]
        assert errs == expected

    def test_value(self, group_context, attr_context):
        data1, data2, attrs = self._datas_and_attrs(
            group_context, attr_context
        )

        attrs["att1"].value = np.array(999)
        errs = compare_nc_datasets(data1, data2)

        path_string = "Dataset"
        if "namedgroup" in group_context:
            path_string += "/inner_group"
        if "variable" in attr_context:
            path_string += ' variable "vx"'
            value_string = "1"
        else:
            value_string = "11"
        expected = [
            f'{path_string} "att1" attribute values differ : '
            f"array({value_string}) != array(999)"
        ]
        assert errs == expected

    def test_order(self, group_context, attr_context, order_checking):
        data1, data2, attrs = self._datas_and_attrs(
            group_context, attr_context
        )
        do_ordercheck = {"ordered": True, "unordered": False}[order_checking]
        all_attrs = list(attrs.values())
        attrs.clear()
        attrs.addall(all_attrs[::-1])

        errs = compare_nc_datasets(
            data1, data2, check_attrs_order=do_ordercheck
        )

        path_string = "Dataset"
        if "namedgroup" in group_context:
            path_string += "/inner_group"
        if "variable" in attr_context:
            path_string += ' variable "vx"'
        if do_ordercheck:
            expected = [
                f"{path_string} attribute lists do not match: "
                "['att1', 'att2'] != ['att2', 'att1']"
            ]
        else:
            expected = []

        assert errs == expected

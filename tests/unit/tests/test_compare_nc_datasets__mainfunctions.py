from dataclasses import dataclass

import numpy as np
import pytest

from ncdata import NameMap, NcAttribute, NcData, NcDimension, NcVariable
from tests._compare_nc_datasets import compare_nc_datasets

# from tests.data_testcase_schemas import _Datatype_Sample_Values, data_types
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


def decode_ordercheck(order_checking):
    return {"ordered": True, "unordered": False}[order_checking]


def location_prefix(group_context, attr_context="on_group"):
    prefix = "Dataset"
    if "namedgroup" in group_context:
        prefix += "/inner_group"
    if "variable" in attr_context:
        prefix += ' variable "vx"'
    return prefix


def put_group_into_context(testdata, group_context):
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


_DEBUG_RESULTS = True
# _DEBUG_RESULTS = True


def check(results, expected):
    if _DEBUG_RESULTS:
        print("\nResult messages:")
        for msg in results:
            print("  ", msg)
    assert results == expected


class TestCompareDatasets:
    @pytest.mark.parametrize("namecheck", ["withnames", "withoutnames"])
    @pytest.mark.parametrize("altname", ["named_y", "named_none"])
    def test_names(self, namecheck, altname):
        do_namecheck = namecheck == "withnames"
        altname = {"named_y": "y", "named_none": None}[altname]
        data1, data2 = NcData(name="x"), NcData(name=altname)

        # Use kwargs just to confirm that the default for name-checking is 'off'
        kwargs = dict(check_names=True) if do_namecheck else {}
        errs = compare_nc_datasets(data1, data2, **kwargs)

        if do_namecheck:
            expected = [f"Datasets have different names: 'x' != {altname!r}."]
        else:
            expected = []
        check(errs, expected)


class TestCompareDimensions:
    def dimension_testdata(self, group_context):
        testdata = NcData(
            name="dataset_1",
            dimensions=[
                NcDimension("x", 2, unlimited=True),
                NcDimension("y", 3, unlimited=False),
            ],
        )
        testdata = put_group_into_context(testdata, group_context)
        return testdata

    @dataclass
    class DimsData:
        data1: NcData = None
        data2: NcData = None
        location_string: str = ""
        dims: NameMap = None

    @pytest.fixture()
    def dimsdata(self, group_context):
        data1, data2 = [
            self.dimension_testdata(group_context) for _ in range(2)
        ]
        location = data2
        if "group" in group_context:
            location = location.groups["inner_group"]

        dimsdata = self.DimsData(
            data1=data1,
            data2=data2,
            location_string=location_prefix(group_context),
            dims=location.dimensions,
        )
        return dimsdata

    def test_name(self, dimsdata):
        dimsdata.dims.rename("x", "q")
        errs = compare_nc_datasets(dimsdata.data1, dimsdata.data2)
        expected = [
            f"{dimsdata.location_string} dimension lists do not match: "
            "['x', 'y'] != ['q', 'y']"
        ]
        check(errs, expected)

    def test_size(self, dimsdata):
        dimsdata.dims["x"].size = 77

        errs = compare_nc_datasets(dimsdata.data1, dimsdata.data2)

        expected = [
            f'{dimsdata.location_string} "x" dimensions have different sizes: 2 != 77'
        ]
        check(errs, expected)

    @pytest.mark.parametrize(
        "check_unlim", ["unlims_checked", "unlims_unchecked"]
    )
    def test_unlimited(self, dimsdata, check_unlim):
        dimsdata.dims["y"].unlimited = True

        do_check_unlims = {"unlims_checked": True, "unlims_unchecked": False}[
            check_unlim
        ]
        errs = compare_nc_datasets(
            dimsdata.data1, dimsdata.data2, check_unlimited=do_check_unlims
        )

        if do_check_unlims:
            expected = [
                f'{dimsdata.location_string} "y" dimension has different "unlimited" status : '
                "False != True"
            ]
        else:
            expected = []

        check(errs, expected)

    def test_ordering(self, dimsdata, order_checking):
        all_dims = list(dimsdata.dims.values())
        dimsdata.dims.clear()
        dimsdata.dims.addall(all_dims[::-1])

        do_ordercheck = decode_ordercheck(order_checking)
        errs = compare_nc_datasets(
            dimsdata.data1, dimsdata.data2, check_dims_order=do_ordercheck
        )

        if do_ordercheck:
            expected = [
                f"{dimsdata.location_string} dimension lists do not match: "
                "['x', 'y'] != ['y', 'x']"
            ]
        else:
            expected = []

        check(errs, expected)

    def test_extra_or_missing(self, dimsdata):
        all_dims = list(dimsdata.dims.values())
        # Remove the last dimension, so data1 has a dim not present in data2
        dimsdata.dims.clear()
        dimsdata.dims.addall(all_dims[:-1])

        errs = compare_nc_datasets(dimsdata.data1, dimsdata.data2)

        expected = [
            f"{dimsdata.location_string} dimension lists do not match: "
            "['x', 'y'] != ['x']"
        ]
        check(errs, expected)


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
        testdata = put_group_into_context(testdata, group_context)
        return testdata

    @dataclass
    class AttrsData:
        data1: NcData = None
        data2: NcData = None
        location_string: str = ""
        attrs: NameMap = None

    @pytest.fixture()
    def attrsdata(self, group_context, attr_context):
        data1, data2 = [
            self.attribute_testdata(group_context) for _ in range(2)
        ]
        location = data2
        if "group" in group_context:
            location = location.groups["inner_group"]
        is_on_var = {"on_group": False, "on_variable": True}[attr_context]
        if is_on_var:
            location = location.variables["vx"]

        attrsdata = self.AttrsData(
            data1=data1,
            data2=data2,
            location_string=location_prefix(group_context, attr_context),
            attrs=location.attributes,
        )
        return attrsdata

    def test_name(self, attrsdata):
        attrsdata.attrs.rename("att1", "changed")

        errs = compare_nc_datasets(attrsdata.data1, attrsdata.data2)

        expected = [
            f"{attrsdata.location_string} attribute lists do not match: "
            "['att1', 'att2'] != ['changed', 'att2']"
        ]
        check(errs, expected)

    def test_value(self, attrsdata, attr_context):
        attrsdata.attrs["att1"].value = np.array(999)

        errs = compare_nc_datasets(attrsdata.data1, attrsdata.data2)

        if "variable" in attr_context:
            value_string = "1"
        else:
            value_string = "11"
        expected = [
            f'{attrsdata.location_string} "att1" attribute values differ : '
            f"array({value_string}) != array(999)"
        ]
        check(errs, expected)

    def test_dtype(self):
        # TODO: check over various datatype for dtype difference
        #  N.B. strings behave differently.
        assert 0
        # attrsdata.attrs["att1"].value = np.array(999)
        #
        # errs = compare_nc_datasets(attrsdata.data1, attrsdata.data2)
        #
        # if "variable" in attr_context:
        #     value_string = "1"
        # else:
        #     value_string = "11"
        # expected = [
        #     f'{attrsdata.location_string} "att1" attribute values differ : '
        #     f"array({value_string}) != array(999)"
        # ]
        # check(errs, expected)

    def test_ordering(self, attrsdata, order_checking):
        do_ordercheck = decode_ordercheck(order_checking)
        all_attrs = list(attrsdata.attrs.values())
        attrsdata.attrs.clear()
        attrsdata.attrs.addall(all_attrs[::-1])

        errs = compare_nc_datasets(
            attrsdata.data1, attrsdata.data2, check_attrs_order=do_ordercheck
        )

        if do_ordercheck:
            expected = [
                f"{attrsdata.location_string} attribute lists do not match: "
                "['att1', 'att2'] != ['att2', 'att1']"
            ]
        else:
            expected = []
        check(errs, expected)

    def test_extra_or_missing(self, attrsdata, order_checking):
        do_ordercheck = decode_ordercheck(order_checking)
        del attrsdata.attrs["att1"]

        errs = compare_nc_datasets(
            attrsdata.data1, attrsdata.data2, check_attrs_order=do_ordercheck
        )

        expected = [
            f"{attrsdata.location_string} attribute lists do not match: "
            "['att1', 'att2'] != ['att2']"
        ]
        check(errs, expected)

    @pytest.mark.parametrize("attname", ["fillvalue", "generic"])
    def test_fillvalue_anyorder(self, attname):
        """The order of "_FillValue" attributes is specially ignored."""
        name = {"fillvalue": "_FillValue", "generic": "anyold"}[attname]
        # data1, data2 have attrs in the other order
        attr_pair = [NcAttribute(name, 1), NcAttribute("x", 1)]
        data1, data2 = [
            NcData(
                variables=[
                    NcVariable("vx", (), data=np.array(0.0), attributes=attrs)
                ]
            )
            for attrs in (attr_pair, attr_pair[::-1])
        ]

        errs = compare_nc_datasets(data1, data2)

        if "generic" in attname:
            expected = [
                'Dataset variable "vx" attribute lists do not match: '
                "['anyold', 'x'] != ['x', 'anyold']"
            ]
        else:
            expected = []
        check(errs, expected)


class TestCompareVariables__metadata:
    def vars_testdata(self, group_context):
        def data():
            return np.zeros((2, 3))

        testdata = NcData(
            name="dataset_1",
            dimensions=[NcDimension("y", 2), NcDimension("x", 3)],
            variables=[
                NcVariable("v1", ("y", "x"), data=data()),
                NcVariable("v2", ("y", "x"), data=data()),
            ],
        )
        testdata = put_group_into_context(testdata, group_context)
        return testdata

    @dataclass
    class VarsData:
        data1: NcData = None
        data2: NcData = None
        location_string: str = ""
        vars: NameMap = None

    @pytest.fixture()
    def varsdata(self, group_context):
        data1, data2 = [self.vars_testdata(group_context) for _ in range(2)]
        location = data2
        if "group" in group_context:
            location = location.groups["inner_group"]

        varsdata = self.VarsData(
            data1=data1,
            data2=data2,
            location_string=location_prefix(group_context),
            vars=location.variables,
        )
        return varsdata

    def test_name(self, varsdata):
        varsdata.vars.rename("v2", "q")

        errs = compare_nc_datasets(varsdata.data1, varsdata.data2)

        expected = [
            f"{varsdata.location_string} variable lists do not match: "
            "['v1', 'v2'] != ['v1', 'q']"
        ]
        check(errs, expected)

    def test_order(self, varsdata, order_checking):
        all_vars = list(varsdata.vars.values())
        varsdata.vars.clear()
        varsdata.vars.addall(all_vars[::-1])

        do_ordercheck = decode_ordercheck(order_checking)
        errs = compare_nc_datasets(
            varsdata.data1, varsdata.data2, check_vars_order=do_ordercheck
        )

        if do_ordercheck:
            expected = [
                f"{varsdata.location_string} variable lists do not match: "
                "['v1', 'v2'] != ['v2', 'v1']"
            ]
        else:
            expected = []
        check(errs, expected)

    def test_extra_or_missing(self, varsdata, order_checking):
        do_ordercheck = decode_ordercheck(order_checking)
        del varsdata.vars["v1"]

        do_ordercheck = decode_ordercheck(order_checking)
        errs = compare_nc_datasets(
            varsdata.data1, varsdata.data2, check_vars_order=do_ordercheck
        )

        expected = [
            f"{varsdata.location_string} variable lists do not match: "
            "['v1', 'v2'] != ['v2']"
        ]
        check(errs, expected)

    def test_dims__reorder(self, varsdata, order_checking):
        # N.B. here we check behaviour of the DIMENSIONS order control, but this does
        # *not* apply to dimensions order in a variable,which is always significant.
        varsdata.vars["v1"].dimensions = varsdata.vars["v1"].dimensions[::-1]
        # N.B. the data shape doesn't now correspond, but that won't matter as, with
        #  mismatched dimensions, the data won't be checked.

        do_orderchecks = decode_ordercheck(order_checking)
        errs = compare_nc_datasets(
            varsdata.data1, varsdata.data2, check_dims_order=do_orderchecks
        )

        expected = [
            f'{varsdata.location_string} variable "v1" dimensions differ : '
            "('y', 'x') != ('x', 'y')"
        ]
        check(errs, expected)

    def test_dims__extra_or_missing(self, varsdata, order_checking):
        # N.B. here we check for DIMENSIONS order check control.
        varsdata.vars["v1"].dimensions = varsdata.vars["v1"].dimensions[:-1]
        # N.B. the data shape doesn't now correspond, but that won't matter as, with
        #  mismatched dimensions, the data won't be checked.

        do_orderchecks = decode_ordercheck(order_checking)
        errs = compare_nc_datasets(
            varsdata.data1, varsdata.data2, check_dims_order=do_orderchecks
        )

        expected = [
            f'{varsdata.location_string} variable "v1" dimensions differ : '
            "('y', 'x') != ('y',)"
        ]
        check(errs, expected)


class TestCompareVariables__data:
    """
    TODO: tests for data equivalence checking.

    Check with various dtypes etc.
    To consider ...
        * masks
        * NaNs
        * real+lazy
        * int/float/string datatypes
        * 0/1/N-dimensional
    """


class TestCompareGroups:
    def test_names(self):
        pass

    def test_order(self):
        pass

    def test_extra_or_missing(self):
        pass

"""
Tests for :mod:`tests.unit.netcdf._compare_nc_files`
Split in two files ...
    * HERE: "mainfunctions" cover the core functionality
        -- which elements are compared and what errors this constructs.
    * ( ALSO: "additional" tests (q.v.) cover subsidiary routines and the
        main API usage modes. )
"""
import dask.array as da
import numpy as np
import pytest

from ncdata import NcAttribute, NcData, NcDimension, NcVariable
from tests._compare_nc_datasets import compare_nc_datasets

# from tests.data_testcase_schemas import _Datatype_Sample_Values, data_types
# data_types  # avoid 'unused' warning


@pytest.fixture(
    params=["in_named", "in_unnamed", "in_namedgroup", "in_unnamedgroup"]
)
def group_context(request):
    """
    The different contexts of locations in a dataset

    In which an element (dimension, group or variable) might be found, and
    which might appear different in the mismatch-error messages.
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

    @pytest.fixture(autouse=True)
    def _dims_data(self, group_context):
        data1, data2 = [
            self.dimension_testdata(group_context) for _ in range(2)
        ]
        location = data2
        if "group" in group_context:
            location = location.groups["inner_group"]

        self.data1 = data1
        self.data2 = data2
        self.location_string = location_prefix(group_context)
        self.dims = location.dimensions

    def test_name(self):
        self.dims.rename("x", "q")
        errs = compare_nc_datasets(self.data1, self.data2)
        expected = [
            f"{self.location_string} dimension lists do not match: "
            "['x', 'y'] != ['q', 'y']"
        ]
        check(errs, expected)

    def test_size(self):
        self.dims["x"].size = 77

        errs = compare_nc_datasets(self.data1, self.data2)

        expected = [
            f'{self.location_string} "x" dimensions have different sizes: 2 != 77'
        ]
        check(errs, expected)

    @pytest.mark.parametrize(
        "check_unlim", ["unlims_checked", "unlims_unchecked"]
    )
    def test_unlimited(self, check_unlim):
        self.dims["y"].unlimited = True

        do_check_unlims = {"unlims_checked": True, "unlims_unchecked": False}[
            check_unlim
        ]
        errs = compare_nc_datasets(
            self.data1, self.data2, check_unlimited=do_check_unlims
        )

        if do_check_unlims:
            expected = [
                f'{self.location_string} "y" dimension has different "unlimited" status : '
                "False != True"
            ]
        else:
            expected = []

        check(errs, expected)

    def test_ordering(self, order_checking):
        all_dims = list(self.dims.values())
        self.dims.clear()
        self.dims.addall(all_dims[::-1])

        do_ordercheck = decode_ordercheck(order_checking)
        errs = compare_nc_datasets(
            self.data1, self.data2, check_dims_order=do_ordercheck
        )

        if do_ordercheck:
            expected = [
                f"{self.location_string} dimension lists do not match: "
                "['x', 'y'] != ['y', 'x']"
            ]
        else:
            expected = []

        check(errs, expected)

    def test_extra_or_missing(self):
        all_dims = list(self.dims.values())
        # Remove the last dimension, so data1 has a dim not present in data2
        self.dims.clear()
        self.dims.addall(all_dims[:-1])

        errs = compare_nc_datasets(self.data1, self.data2)

        expected = [
            f"{self.location_string} dimension lists do not match: "
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

    @pytest.fixture(autouse=True)
    def _attrs_data(self, group_context, attr_context):
        data1, data2 = [
            self.attribute_testdata(group_context) for _ in range(2)
        ]
        location = data2
        if "group" in group_context:
            location = location.groups["inner_group"]
        is_on_var = {"on_group": False, "on_variable": True}[attr_context]
        if is_on_var:
            location = location.variables["vx"]

        self.data1 = data1
        self.data2 = data2
        self.location_string = location_prefix(group_context, attr_context)
        self.attrs = location.attributes

    def test_name(self):
        self.attrs.rename("att1", "changed")

        errs = compare_nc_datasets(self.data1, self.data2)

        expected = [
            f"{self.location_string} attribute lists do not match: "
            "['att1', 'att2'] != ['changed', 'att2']"
        ]
        check(errs, expected)

    def test_value(self, attr_context):
        self.attrs["att1"].value = np.array(999)

        errs = compare_nc_datasets(self.data1, self.data2)

        if "variable" in attr_context:
            value_string = "1"
        else:
            value_string = "11"
        expected = [
            f'{self.location_string} "att1" attribute values differ : '
            f"array({value_string}) != array(999)"
        ]
        check(errs, expected)

    def test_ordering(self, order_checking):
        do_ordercheck = decode_ordercheck(order_checking)
        all_attrs = list(self.attrs.values())
        self.attrs.clear()
        self.attrs.addall(all_attrs[::-1])

        errs = compare_nc_datasets(
            self.data1, self.data2, check_attrs_order=do_ordercheck
        )

        if do_ordercheck:
            expected = [
                f"{self.location_string} attribute lists do not match: "
                "['att1', 'att2'] != ['att2', 'att1']"
            ]
        else:
            expected = []
        check(errs, expected)

    def test_extra_or_missing(self, order_checking):
        do_ordercheck = decode_ordercheck(order_checking)
        del self.attrs["att1"]

        errs = compare_nc_datasets(
            self.data1, self.data2, check_attrs_order=do_ordercheck
        )

        expected = [
            f"{self.location_string} attribute lists do not match: "
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
    @staticmethod
    def _vars_testdata(group_context):
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

    @pytest.fixture(autouse=True)
    def _vars_data(self, group_context):
        data1, data2 = [self._vars_testdata(group_context) for _ in range(2)]
        location = data2
        if "group" in group_context:
            location = location.groups["inner_group"]

        self.data1 = data1
        self.data2 = data2
        self.location_string = location_prefix(group_context)
        self.vars = location.variables

    def test_var_names(self):
        self.vars.rename("v2", "q")

        errs = compare_nc_datasets(self.data1, self.data2)

        expected = [
            f"{self.location_string} variable lists do not match: "
            "['v1', 'v2'] != ['v1', 'q']"
        ]
        check(errs, expected)

    def test_var_order(self, order_checking):
        all_vars = list(self.vars.values())
        self.vars.clear()
        self.vars.addall(all_vars[::-1])

        do_ordercheck = decode_ordercheck(order_checking)
        errs = compare_nc_datasets(
            self.data1, self.data2, check_vars_order=do_ordercheck
        )

        if do_ordercheck:
            expected = [
                f"{self.location_string} variable lists do not match: "
                "['v1', 'v2'] != ['v2', 'v1']"
            ]
        else:
            expected = []
        check(errs, expected)

    def test_vars_extra_or_missing(self, order_checking):
        del self.vars["v1"]

        do_ordercheck = decode_ordercheck(order_checking)
        errs = compare_nc_datasets(
            self.data1, self.data2, check_vars_order=do_ordercheck
        )

        expected = [
            f"{self.location_string} variable lists do not match: "
            "['v1', 'v2'] != ['v2']"
        ]
        check(errs, expected)

    def test_var_dims__reorder(self, order_checking):
        # N.B. here we check behaviour of the DIMENSIONS order control, but this does
        # not apply to dimensions order in a variable,which is *always* significant.
        self.vars["v1"].dimensions = self.vars["v1"].dimensions[::-1]
        # N.B. the data shape doesn't now correspond, but that won't matter as, with
        #  mismatched dimensions, the data won't be checked.

        do_orderchecks = decode_ordercheck(order_checking)
        errs = compare_nc_datasets(
            self.data1, self.data2, check_dims_order=do_orderchecks
        )

        expected = [
            f'{self.location_string} variable "v1" dimensions differ : '
            "('y', 'x') != ('x', 'y')"
        ]
        check(errs, expected)

    def test_var_dims__extra_or_missing(self, order_checking):
        # N.B. here we check for DIMENSIONS order check control.
        self.vars["v1"].dimensions = self.vars["v1"].dimensions[:-1]
        # N.B. the data shape doesn't now correspond, but that won't matter as, with
        #  mismatched dimensions, the data won't be checked.

        do_orderchecks = decode_ordercheck(order_checking)
        errs = compare_nc_datasets(
            self.data1, self.data2, check_dims_order=do_orderchecks
        )

        expected = [
            f'{self.location_string} variable "v1" dimensions differ : '
            "('y', 'x') != ('y',)"
        ]
        check(errs, expected)


class TestCompareVariables__dtype:
    # Note: testing variable comparison via the 'main' public API instead of
    #  via '_compare_variables'.  This makes sense because it is only called
    #  in one way, from one place.
    @staticmethod
    def _vars_testdata():
        def data():
            return np.zeros(3)

        testdata = NcData(
            name="dataset_1",
            dimensions=[NcDimension("x", 3)],
            variables=[
                NcVariable("v1", ("x"), data=data()),
            ],
        )
        return testdata

    @pytest.fixture(autouse=True)
    def _vars_data(self):
        self.data1, self.data2 = [self._vars_testdata() for _ in range(2)]
        self.testvar = self.data2.variables["v1"]

    def test_numbers_v_strings(self):
        # Set a different dtype
        # NB this is different from the actual data array, but that doesn't
        #  matter, as it won't attempt to compare strings with numbers
        self.testvar.dtype = np.dtype("S5")

        # Test the comparison
        errs = compare_nc_datasets(self.data1, self.data2)
        expected = [
            'Dataset variable "v1" datatypes differ : '
            "dtype('float64') != dtype('S5')"
        ]
        check(errs, expected)

    @pytest.mark.parametrize("equaldata", [False, True])
    def test_ints_v_floats(self, equaldata):
        # In this case, there is also a data comparison to check.
        v1 = self.testvar

        new_dtype = np.dtype(np.int32)
        v1.data = v1.data.astype(new_dtype)
        if not equaldata:
            v1.data.flat[0] += 1
        v1.dtype = new_dtype

        # Test the comparison
        errs = compare_nc_datasets(self.data1, self.data2)

        expected = [
            'Dataset variable "v1" datatypes differ : '
            "dtype('float64') != dtype('int32')"
        ]
        if not equaldata:
            expected.append(
                'Dataset variable "v1" data contents differ, at 1 points: '
                "@INDICES[(0,)] : LHS=[0.0], RHS=[1]"
            )
        check(errs, expected)

    @pytest.mark.parametrize("equaldata", [False, True])
    def test_wordlengths(self, equaldata):
        # Test floats with wordlength difference -- assume ints are the same
        # In this case, there is also a data comparison to check.
        v1 = self.testvar

        new_dtype = np.dtype(np.float32)
        v1.data = v1.data.astype(new_dtype)
        if not equaldata:
            v1.data.flat[0] += 1
        v1.dtype = new_dtype

        # Test the comparison
        errs = compare_nc_datasets(self.data1, self.data2)

        expected = [
            'Dataset variable "v1" datatypes differ : '
            "dtype('float64') != dtype('float32')"
        ]
        if not equaldata:
            expected.append(
                'Dataset variable "v1" data contents differ, at 1 points: '
                "@INDICES[(0,)] : LHS=[0.0], RHS=[1.0]"
            )
        check(errs, expected)


class TestCompareVariables__data__checkcontrols:
    # Note: testing variable comparison via the 'main' public API instead of
    #  via '_compare_variables'.  This makes sense because it is only called
    #  in one way, from one place.
    @staticmethod
    def _vars_testdata():
        def data():
            return np.arange(6.0).reshape((2, 3))

        testdata = NcData(
            name="dataset_1",
            dimensions=[NcDimension("y", 2), NcDimension("x", 3)],
            variables=[
                NcVariable("v1", ("x"), data=data()),
            ],
        )
        return testdata

    @pytest.fixture(autouse=True)
    def _vars_data(self):
        self.data1, self.data2 = [self._vars_testdata() for _ in range(2)]
        self.reference_var = self.data1.variables["v1"]
        self.testvar = self.data2.variables["v1"]

    def test_no_values_check(self):
        self.testvar.data += 1
        errs = compare_nc_datasets(
            self.data1, self.data2, check_var_data=False
        )
        check(errs, [])

    def test_print_bad_nprint(self):
        msg = "'show_n_diffs' must be >=1 : got 0."
        with pytest.raises(ValueError, match=msg):
            compare_nc_datasets(
                self.data1, self.data2, show_n_first_different=0
            )

    @pytest.mark.parametrize("ndiffs", [1, 2, 3])
    def test_ndiffs(self, ndiffs):
        self.testvar.data.flat[1 : ndiffs + 1] += 1
        errs = compare_nc_datasets(self.data1, self.data2)
        detail = {
            1: "[(0, 1)] : LHS=[1.0], RHS=[2.0]",
            2: "[(0, 1), (0, 2)] : LHS=[1.0, 2.0], RHS=[2.0, 3.0]",
            3: (
                "[(0, 1), (0, 2), ...] : "
                "LHS=[1.0, 2.0, ...], RHS=[2.0, 3.0, ...]"
            ),
        }[ndiffs]
        expected = [
            f'Dataset variable "v1" data contents differ, at {ndiffs} points: '
            f"@INDICES{detail}"
        ]
        check(errs, expected)

    @pytest.mark.parametrize("nprint", [1, 2, 3])
    def test_show_n_first_different(self, nprint):
        self.testvar.data.flat[1:3] += 1
        errs = compare_nc_datasets(
            self.data1, self.data2, show_n_first_different=nprint
        )
        detail = {
            1: "[(0, 1), ...] : LHS=[1.0, ...], RHS=[2.0, ...]",
            2: "[(0, 1), (0, 2)] : LHS=[1.0, 2.0], RHS=[2.0, 3.0]",
            3: "[(0, 1), (0, 2)] : LHS=[1.0, 2.0], RHS=[2.0, 3.0]",
        }[nprint]
        expected = [
            f'Dataset variable "v1" data contents differ, at 2 points: '
            f"@INDICES{detail}"
        ]
        check(errs, expected)


class TestCompareVariables__data__diffreports:
    # Note: testing variable comparison via the 'main' public API instead of
    #  via '_compare_variables'.  This makes sense because it is only called
    #  in one way, from one place.
    @staticmethod
    def _vars_testdata():
        def data():
            return np.arange(4.0)

        testdata = NcData(
            name="dataset_1",
            dimensions=[NcDimension("x", 4)],
            variables=[
                NcVariable("v1", ("x"), data=data()),
            ],
        )
        return testdata

    @pytest.fixture(autouse=True)
    def _vars_data(self):
        self.data1, self.data2 = [self._vars_testdata() for _ in range(2)]
        self.reference_var = self.data1.variables["v1"]
        self.testvar = self.data2.variables["v1"]

    @pytest.mark.parametrize("datavalues", ["same", "different"])
    @pytest.mark.parametrize("masks", ["onemasked", "bothmasked"])
    def test_masked(self, datavalues, masks):
        different = datavalues == "different"
        bothmasked = masks == "bothmasked"
        testvar = self.testvar
        testvar.data = np.ma.masked_array(testvar.data)
        if different:
            testvar.data[1:2] += 1
        testvar.data[1:2] = np.ma.masked
        if bothmasked:
            self.reference_var.data = np.ma.masked_array(
                self.reference_var.data
            )
            self.reference_var.data[1:2] = np.ma.masked
        errs = compare_nc_datasets(self.data1, self.data2)
        if bothmasked:
            expected = []
        else:
            expected = [
                'Dataset variable "v1" data contents differ, at 1 points: '
                "@INDICES[(1,)] : LHS=[1.0], RHS=[masked]"
            ]
        check(errs, expected)

    @pytest.mark.parametrize("nans", ["onenans", "bothnans"])
    def test_nans(self, nans):
        bothnans = nans == "bothnans"
        self.testvar.data[1:2] = np.nan
        if bothnans:
            self.reference_var.data[1:2] = np.nan
        errs = compare_nc_datasets(self.data1, self.data2)
        if bothnans:
            expected = []
        else:
            expected = [
                'Dataset variable "v1" data contents differ, at 1 points: '
                "@INDICES[(1,)] : LHS=[1.0], RHS=[nan]"
            ]
        check(errs, expected)

    def test_scalar(self):
        # Check how a difference of scalar arrays is reported
        for value, var in enumerate([self.reference_var, self.testvar]):
            var.dimensions = ()
            var.data = np.array(value, dtype=var.dtype)
        errs = compare_nc_datasets(self.data1, self.data2)
        expected = [
            'Dataset variable "v1" data contents differ, at 1 points: '
            "@INDICES[(0,)] : LHS=[0.0], RHS=[1.0]"
        ]
        check(errs, expected)

    @pytest.mark.parametrize(
        "argtypes", ["real_real", "real_lazy", "lazy_lazy"]
    )
    def test_real_and_lazy(self, argtypes):
        type1, type2 = argtypes[:4], argtypes[-4:]
        # fix the testvar to create a difference
        self.testvar.data[1:2] += 1
        # setup vars with lazy/real data arrays
        for arraytype, var in zip(
            [type1, type2], [self.reference_var, self.testvar]
        ):
            if arraytype == "lazy":
                var.data = da.from_array(var.data, chunks=-1)
        # compare + check results
        errs = compare_nc_datasets(self.data1, self.data2)
        # N.B. the result should be the same in all cases
        expected = [
            'Dataset variable "v1" data contents differ, at 1 points: '
            "@INDICES[(1,)] : LHS=[1.0], RHS=[2.0]"
        ]
        check(errs, expected)


class TestCompareGroups:
    @staticmethod
    def _groups_testdata():
        testdata = NcData(
            name="dataset_1",
            groups=[
                NcData(name=name, attributes=[NcAttribute("attr_1", 1)])
                for name in ("g1", "g2")
            ],
        )
        return testdata

    @pytest.fixture(autouse=True)
    def _groups_data(self):
        self.data1, self.data2 = [self._groups_testdata() for _ in range(2)]
        self.groups = self.data2.groups

    def test_group_names(self):
        self.groups.rename("g2", "q")

        errs = compare_nc_datasets(self.data1, self.data2)

        expected = [
            "Dataset subgroup lists do not match: ['g1', 'g2'] != ['g1', 'q']"
        ]
        check(errs, expected)

    def test_group_order(self, order_checking):
        all_groups = list(self.groups.values())
        self.groups.clear()
        self.groups.addall(all_groups[::-1])

        do_ordercheck = decode_ordercheck(order_checking)
        errs = compare_nc_datasets(
            self.data1, self.data2, check_groups_order=do_ordercheck
        )

        if do_ordercheck:
            expected = [
                "Dataset subgroup lists do not match: "
                "['g1', 'g2'] != ['g2', 'g1']"
            ]
        else:
            expected = []
        check(errs, expected)

    def test_groups_extra_or_missing(self, order_checking):
        del self.groups["g1"]

        do_ordercheck = decode_ordercheck(order_checking)
        errs = compare_nc_datasets(
            self.data1, self.data2, check_groups_order=do_ordercheck
        )

        # NB since the sets are different, the ordering control has no effect
        expected = [
            "Dataset subgroup lists do not match: ['g1', 'g2'] != ['g2']"
        ]
        check(errs, expected)

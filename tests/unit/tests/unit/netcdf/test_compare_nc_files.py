"""
Tests for :mod:`tests.unit.netcdf._compare_nc_files`

Yes I know, tests of tests.  But it seems necessary.
"""
import os
import shutil
import subprocess
import warnings
from pathlib import Path
from typing import AnyStr, Optional
from unittest import mock

import netCDF4 as nc
import numpy as np
import pytest
from test_samplecode_cdlgen_comparablecdl import ncgen_from_cdl

from tests.unit.netcdf._compare_nc_files import (
    _compare_attributes,
    _compare_name_lists,
    compare_nc_files,
)

# CDL to create a reference file with "all" features included.
_base_cdl = """
netcdf everything {
dimensions:
	x = 2 ;
	y = 3 ;
	strlen = 5 ;
variables:
	int x(x) ;
		x:name = "var_x" ;
	int var_2d(x, y) ;
	uint var_u8(x) ;
	float var_f4(x) ;
	double var_f8(x) ;
	char var_str(x, strlen) ;
	int other(x) ;
	    other:attr_int = 1 ;
	    other:attr_float = 2.0f ;
	    other:attr_double = 2.0 ;
	    other:attr_string = "this" ;
    int masked_int(y) ;
        masked_int:_FillValue = -3 ;
    int masked_float(y) ;
        masked_float:_FillValue = -4.0 ;
        
// global attributes:
		:global_attr_1 = "one" ;
		:global_attr_2 = 2 ;

// groups:
group: grp_1 {
    dimensions:
        y = 7 ;
    variables:
        int parent_dim(x) ;
        int own_dim(y) ;
}
group: grp_2 {
    variables:
        int grp2_x(x) ;
}
}
"""

_simple_cdl = """
netcdf test {
dimensions:
	x = 2 ;
variables:
	int x(x) ;
}
"""


@pytest.fixture(autouse=True, scope="module")
def temp_ncfiles_dir(tmp_path_factory):
    tmp_dirpath = tmp_path_factory.mktemp("samencfiles")
    return tmp_dirpath


@pytest.fixture
def samefiles(temp_ncfiles_dir):
    file1_nc = temp_ncfiles_dir / "tmp1.nc"
    file1_cdl = temp_ncfiles_dir / "tmp1.cdl"
    file2_nc = temp_ncfiles_dir / "tmp2.nc"
    file2_cdl = temp_ncfiles_dir / "tmp2.cdl"
    ncgen_from_cdl(cdl_str=_simple_cdl, nc_path=file1_nc, cdl_path=file1_cdl)
    ncgen_from_cdl(cdl_str=_simple_cdl, nc_path=file2_nc, cdl_path=file2_cdl)
    return file1_nc, file2_nc


class Test__compare_name_lists:
    # Test subsidiary routine for checking a list of names
    def test_empty(self):
        errs = []
        _compare_name_lists(errs, [], [], "named-elements")
        assert errs == []

    def test_same(self):
        tst = ["a", "b"]
        errs = []
        _compare_name_lists(errs, tst, tst, "named-elements")
        assert errs == []

    def test_diff(self):
        errs = []
        _compare_name_lists(errs, ["a"], [], "named-elements")
        assert errs == ["named-elements do not match: ['a'] != []"]

    def test_difforder(self):
        errs = []
        _compare_name_lists(errs, ["a", "b"], ["b", "a"], "named-elements")
        assert errs == [
            "named-elements do not match: ['a', 'b'] != ['b', 'a']"
        ]

    def test_difforder_tolerant_warns(self):
        errs = []
        with pytest.warns(
            UserWarning, match="Ignoring: named-elements do not match"
        ):
            _compare_name_lists(
                errs,
                ["a", "b"],
                ["b", "a"],
                "named-elements",
                order_strict=False,
            )
        assert errs == []

    def test_difforder_tolerant_nowarn(self):
        errs = []
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            _compare_name_lists(
                errs,
                ["a", "b"],
                ["b", "a"],
                "named-elements",
                order_strict=False,
                suppress_warnings=True,
            )
        assert errs == []


class Test__compare_attributes:
    def test_compare_attributes_namelists(self):
        # Check that it calls the generic _compare_name_lists routine, passing all the
        # correct controls
        # Mimic 2 objects with NO attributes.
        attrs1 = mock.MagicMock()
        attrs2 = mock.MagicMock()
        obj1 = mock.Mock(ncattrs=mock.Mock(return_value=attrs1))
        obj2 = mock.Mock(ncattrs=mock.Mock(return_value=attrs2))
        errs = mock.sentinel.errors_list
        elemname = "<elem_types>"
        order = mock.sentinel.attrs_order
        suppress = mock.sentinel.suppress_warnings
        tgt = "tests.unit.netcdf._compare_nc_files._compare_name_lists"
        with mock.patch(tgt) as patch_tgt:
            _compare_attributes(
                errs=errs,
                obj1=obj1,
                obj2=obj2,
                elemname=elemname,
                attrs_order=order,
                suppress_warnings=suppress,
            )
        assert patch_tgt.call_args_list == [
            mock.call(
                errs,
                attrs1,
                attrs2,
                "<elem_types> attribute lists",
                order_strict=order,
                suppress_warnings=suppress,
            )
        ]

    class Nc4ObjectWithAttrsMimic:
        def __init__(self, **attrs):
            self._attrs = attrs or {}

        def ncattrs(self):
            return self._attrs.keys()

        def getncattr(self, item):
            # Mimic how netCDF4 returns attribute values
            #  numeric arrays --> numpy ndarray
            #  numeric scalars --> Python int / float
            #  strings --> strings
            #  char arrays --> list of string
            # AND IN ALL CASES : [x] --> x
            value = np.array(self._attrs[item], ndmin=1)
            is_scalar = value.size == 1
            if value.dtype.kind in ("S", "U"):
                # strings are returned in lists, not arrays
                value = [str(x) for x in value]
            if is_scalar:
                # single values are always returned as scalars
                value = value[0]
            return value

    def test_compare_attributes_empty(self):
        # Test two objects with no attributes
        obj1 = self.Nc4ObjectWithAttrsMimic()
        obj2 = self.Nc4ObjectWithAttrsMimic()
        errs = []
        _compare_attributes(errs, obj1, obj2, "<object attributes>")
        assert errs == []

    def test_compare_attributes_values__allok(self):
        # Objects with matching attributes
        obj1 = self.Nc4ObjectWithAttrsMimic(a=1, b=2)
        obj2 = self.Nc4ObjectWithAttrsMimic(a=1, b=2)
        errs = []
        _compare_attributes(errs, obj1, obj2, "<object attributes>")
        assert errs == []

    def test_compare_attributes_values__data_mismatch(self):
        # Attributes of different value (but matching dtype)
        obj1 = self.Nc4ObjectWithAttrsMimic(a=1, b=2, c=3)
        obj2 = self.Nc4ObjectWithAttrsMimic(a=1, b=-77, c=3)
        errs = []
        _compare_attributes(errs, obj1, obj2, "<object attributes>")
        assert errs == [
            '<object attributes> "b" attribute values differ : 2 != -77'
        ]

    def test_compare_attributes_values__dtype_mismatch(self):
        # Attributes of different dtypes, even though values ==
        obj1 = self.Nc4ObjectWithAttrsMimic(a=np.float32(0))
        obj2 = self.Nc4ObjectWithAttrsMimic(a=np.float64(0))
        errs = []
        _compare_attributes(errs, obj1, obj2, "<object attributes>")
        assert errs == [
            (
                '<object attributes> "a" attribute datatypes differ : '
                "dtype('float32') != dtype('float64')"
            )
        ]

    def test_compare_attributes_values__dtype_and_data_mismatch(self):
        # Attributes of different dtypes, but values !=
        obj1 = self.Nc4ObjectWithAttrsMimic(a=np.float32(0))
        obj2 = self.Nc4ObjectWithAttrsMimic(a=np.float64(1))
        errs = []
        _compare_attributes(errs, obj1, obj2, "<object attributes>")
        assert errs == [
            '<object attributes> "a" attribute values differ : 0.0 != 1.0'
        ]

    def test_compare_attributes_values__string_nonstring(self):
        # Attributes of string and non-string types, since we handle that differently
        obj1 = self.Nc4ObjectWithAttrsMimic(a=1)
        obj2 = self.Nc4ObjectWithAttrsMimic(a="1")
        errs = []
        _compare_attributes(errs, obj1, obj2, "<object attributes>")
        assert errs == [
            "<object attributes> \"a\" attribute values differ : 1 != '1'"
        ]

    def test_compare_attributes_values__string_match(self):
        # Attributes of string type (since netCDF4 returns char attributes as string)
        obj1 = self.Nc4ObjectWithAttrsMimic(S="this")
        obj2 = self.Nc4ObjectWithAttrsMimic(S="this")
        errs = []
        _compare_attributes(errs, obj1, obj2, "<object attributes>")
        assert errs == []

    def test_compare_attributes_values__string_mismatch(self):
        # Attributes of string type (since netCDF4 returns char attributes as string)
        obj1 = self.Nc4ObjectWithAttrsMimic(S="this")
        obj2 = self.Nc4ObjectWithAttrsMimic(S="that")
        errs = []
        _compare_attributes(errs, obj1, obj2, "<object attributes>")
        assert errs == [
            "<object attributes> \"S\" attribute values differ : 'this' != 'that'"
        ]

    def test_compare_attributes_values__string_array_match(self):
        # Attributes of string type (since netCDF4 returns char attributes as string)
        obj1 = self.Nc4ObjectWithAttrsMimic(S=["a", "b"])
        obj2 = self.Nc4ObjectWithAttrsMimic(S=["a", "b"])
        errs = []
        _compare_attributes(errs, obj1, obj2, "<object attributes>")
        assert errs == []

    def test_compare_attributes_values__string_array_mismatch(self):
        # Attributes of string type (since netCDF4 returns char attributes as string)
        obj1 = self.Nc4ObjectWithAttrsMimic(S=["a", "b"])
        obj2 = self.Nc4ObjectWithAttrsMimic(S=["a", "c"])
        errs = []
        _compare_attributes(errs, obj1, obj2, "<object attributes>")
        assert errs == [
            '<object attributes> "S" attribute values differ : '
            "['a', 'b'] != ['a', 'c']"
        ]


class Test_compare_nc_files__api:
    def test_identical_paths(self, samefiles):
        path1, path2 = samefiles
        result = compare_nc_files(path1, path2)
        assert result == []

    def test_identical_stringpaths(self, samefiles):
        path1, path2 = samefiles
        result = compare_nc_files(str(path1), str(path2))
        assert result == []

    def test_identical_datasets(self, samefiles):
        path1, path2 = samefiles
        ds1, ds2 = None, None
        try:
            ds1 = nc.Dataset(path1)
            ds2 = nc.Dataset(path2)
            result = compare_nc_files(ds1, ds2)
            assert result == []
        finally:
            for ds in (ds1, ds2):
                if ds:
                    ds.close()

    def test_smalldiff(self, samefiles, temp_ncfiles_dir):
        path1, _ = samefiles
        path2 = path1.parent / "smalldiff.nc"
        shutil.copy(path1, path2)
        ds = nc.Dataset(path2, "r+")
        ds.extra_global_attr = 1
        ds.close()
        result = compare_nc_files(path1, path2)
        assert result == [
            "Dataset attribute lists do not match: [] != ['extra_global_attr']"
        ]

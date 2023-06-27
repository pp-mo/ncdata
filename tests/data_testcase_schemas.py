"""
Define a set of "standard" testcases, built as actual netcdf files.

The main product is a pytest fixture that is parametrised over testcase names, and
returns info on the testcase, its defining spec and a filepath it can be loaded from.
"""
import shutil
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable, Union, Tuple, Dict

import netCDF4
import netCDF4 as nc
import numpy as np
import pytest

import iris.tests


def data_types():
    """
    Produce a sequence of valid netCDF4 datatypes.

    All possible datatypes for variable data or attributes.
    Not yet supporting variable or user-defined (structured) types.

    Results are strings for all valid numeric dtypes, plus 'string'.
    The strings are our choice, chosen to suit inclusion in pytest parameter naming.
    """
    # unsigned int types
    for n in (1, 2, 4, 8):
        yield f"u{n}"
    # signed int types
    for n in (1, 2, 4, 8):
        yield f"i{n}"
    # float types
    for n in (4, 8):
        yield f"f{n}"
    # .. and strings
    # NB we use 'string' instead of 'S1', as strings always need handling differently.
    yield "string"


# Just confirm that the above list of types matches those used by netCDF4, except for
# 'string' replacing 'S1'.
assert set(data_types()) == (
    set(nc.default_fillvals.keys()) - set(["S1"]) | set(["string"])
)


# Suitable test values for each attribute/data type.
_INT_Approx_2x31 = int(2**31 - 1)
_INT_Approx_2x32 = int(2**32 - 2)
_INT_Approx_2x63 = int(2**63 - 3)
_INT_Approx_2x64 = int(2**64 - 4)

_Datatype_Sample_Values = {
    "u1": np.array([3, 250], dtype="u1"),
    "i1": np.array([-120, 120], dtype="i1"),
    "u2": np.array([4, 65001], dtype="u2"),
    "i2": np.array([-30001, 30002], dtype="i2"),
    "u4": np.array([5, _INT_Approx_2x32], dtype="u4"),
    "i4": np.array([-_INT_Approx_2x31, _INT_Approx_2x31], dtype="i4"),
    "u8": np.array([6, _INT_Approx_2x64], dtype="u8"),
    "i8": np.array([-_INT_Approx_2x63, _INT_Approx_2x63], dtype="i8"),
    "f4": np.array([1.23e-9, -34.0e12], dtype="f4"),
    "f8": np.array([1.23e-34, -34.0e52], dtype="f8"),
    "string": ["one", "three"],
}
# Just confirm that the list of sample-value types matches 'data_types'.
assert set(_Datatype_Sample_Values.keys()) == set(data_types())


# Define the possible multiplicities of attributes,
# i.e. value / [1D] / [2D@1, 2D@2, ...]
Attr_Multiples = ["Single", "Multi"]


def attr_schemas():
    # Produce a sequence of lists of definitions for attribute-sets.
    for attr_multiple in Attr_Multiples:
        if attr_multiple == "empty":
            yield {"attributes": []}
        for single_attr in (False, True):
            if single_attr:
                yield {"attributes": [("test", 1)]}
            for datatype in data_types():
                values = _Datatype_Sample_Values[datatype]
                if attr_multiple == "scalar":
                    pass


def dataset_schemas_iter():
    """Yield a succession of netcdf test data specifications."""
    # Empty dataset
    yield {"dataset": "empty"}
    # Dataset with only dimensions (simple unvarying choice).
    yield {"dataset": "dimensions_only"}
    # Dataset with only attributes - test against all attribute options
    for attr_schema in attr_schemas():
        yield {"dataset": "attrs_only", "global-attrs": attr_schema}

    # Ideas
    for attr_spec in attr_specs():
        yield {"attrs": attr_spec}
    for dim_spec in dim_specs():
        yield {"dims": dim_spec}
    for var_spec in var_specs():
        dims = get_all_dims(var_spec)
        yield {"vars": var_spec}
    for group_spec in group_specs():
        yield {"groups": group_spec}


def _write_nc4_dataset(
    spec: dict,
    ds: nc.Dataset,  # or an inner Group
    parent_spec: dict = None,
):
    """
    Inner routine for ``make_testcase_dataset``.

    Separated for recursion and to keep dataset open/close in separate wrapper routine.
    """

    # Convenience function
    def objmap(objs):
        """Create a map from a list of dim-specs, indexing by their names."""
        return {obj["name"]: obj for obj in objs}

    # Get sub-components of the spec.
    # NB most elements are lists of dicts which all have a 'name' item ..
    var_dims = objmap(spec.get("dims", []))
    var_specs = objmap(spec.get("vars", []))
    group_specs = objmap(spec.get("groups", []))
    # .. but attr specs are a simple dict
    attr_specs = spec.get("attrs", {})

    # Assign actual file attrs (group or global)
    for name, value in attr_specs.items():
        ds.setncattr(name, value)

    # Create actual file dims
    for dim_name, dim in var_dims.items():
        # Dims are a simple list, containing names as a dict entry
        size, unlimited = dim["size"], dim.get("unlimited", False)
        if unlimited:
            size = 0
        ds.createDimension(dim_name, size)

    # Create and configure actual file variables
    for var_name, var_spec in var_specs.items():
        var_dims = var_spec["dims"]  # this is just a list of names
        data = var_spec.get("data", None)
        if data is not None:
            data = np.array(data)
            dtype = data.dtype
        else:
            dtype = np.dtype(var_spec["dtype"])
        attrs = var_spec.get("attrs", {})
        fill_value = attrs.pop("_FillValue", None)

        # Create the actual data variable
        nc_var = ds.createVariable(
            varname=var_name,
            dimensions=var_dims,
            datatype=dtype,
            fill_value=fill_value,
        )

        # Add attributes
        for name, value in attrs.items():
            nc_var.setncattr(name, value)

        # Add data, provided or default-constructed
        if data is None:
            shape = nc_var.shape
            n_points = int(np.product(shape))
            if nc_var.dtype.kind == 'S':
                data = np.array(
                    'abcdefghijklmnopqrstuvwxyz'[:n_points],
                    dtype='S1'
                )
            else:
                data = np.arange(1, n_points + 1)
            data = data.astype(dtype)
            i_miss = var_spec.get("missing_inds", [])
            if i_miss:
                data = np.ma.masked_array(data)
                data[i_miss] = np.ma.masked
            data = data.reshape(shape)
        nc_var[:] = data

    # Finally, recurse over sub-groups
    for group_name, group_spec in group_specs.items():
        nc_group = ds.createGroup(group_name)
        _write_nc4_dataset(
            spec=group_spec,
            ds=nc_group,
            parent_spec=parent_spec,
        )


def make_testcase_dataset(filepath, spec):
    """
    Generic routine for converting a test dataset 'spec' into an actual netcdf file.

    Rather frustratingly similar to ncdata.to_nc4, but it needs to remain separate as
    we use it to test that code (!)

    specs are just a structure of dicts and lists...
    group_spec = {
        'name': str
        'dims': [ *{'name':str, size:int [, 'unlim':True]} ]
        'attrs': {'name':str, 'value':array}
        'vars': [ *{
                        'name':str, 'dims':list[str],
                        [, 'attrs': {'name':str, 'value':array}]
                        [, 'dtype':dtype]
                        [, 'data':array]
                        [, 'missing_inds': list(int)]  # NB flat indexes
                    }
                ]
        'groups': list of group_spec
    }

    From this we populate dims + vars, all filling data content according to certain
    default rules (or the provided 'data' item).
    """
    ds = nc.Dataset(filepath, "w")
    try:
        if 'ds__dtype__string' in filepath:
            pass
        _write_nc4_dataset(spec, ds)
    finally:
        ds.close()


_minimal_variable_test_spec = {
    "vars": [dict(name="var_0", dims=[], dtype=int)]
}


_simple_test_spec = {
    "name": "",
    "dims": [dict(name="x", size=3), dict(name="y", size=2)],
    "attrs": {"ga1": 2.3, "gas2": "this"},
    "vars": [dict(name="vx", dims=["x"], dtype=np.int32)],
    "groups": [
        {
            "name": "g_inner",
            "dims": [dict(name="dim_i1", size=4)],
            "vars": [
                dict(
                    name="vix1",
                    dims=["dim_i1", "y"],
                    dtype="u1",
                    missing_inds=[2, 5],
                    attrs={"_FillValue": 100},
                )
            ],
            "attrs": {"ia1": 777},
        }
    ],
}

# Define a sequence of standard testfile specs, with suitable param-names.


def _build_all_testcases():
    testcases = {
        "ds_Empty": {},
        "ds_Minimal": _minimal_variable_test_spec,
        "ds_Basic": _simple_test_spec,
        "testdata1": (
            Path(__file__).parent / "testdata" / "toa_brightness_temperature.nc"
        ),
    }

    ADD_IRIS_FILES = True
    ADD_IRIS_FILES = False
    if ADD_IRIS_FILES:
        # TEMPORARY: add all the Iris testdata paths
        _testdirpath = Path(iris.tests.get_data_path("NetCDF"))
        _netcdf_testfile_paths = _testdirpath.rglob("**/*.nc")
        for filepath in _netcdf_testfile_paths:
            # TEMPORARY: skip unstructured ones, just for now, as it makes the run faster
            if 'unstructured' not in str(filepath):
                pathname = str(filepath).replace(str(_testdirpath), '').replace('/', '__')
                testcases[f"testdata__{pathname}"] = filepath

    #
    # TODO: add files from xarray/tests/data AND xarray-data (separate repo)
    #

    ADD_UNIT_TESTS = True
    # ADD_UNIT_TESTS = False
    if ADD_UNIT_TESTS:
        # Add selected targetted test datasets.

        # dataset with a single attribute
        testcases['ds__singleattr'] = {
            "attrs": {'attr1': 1}
        }

        # dataset with a single variable
        testcases['ds__singlevar'] = {
            "vars": [dict(name="vx", dims=[], dtype=np.int32)]
        }

        # dataset with a single variable
        testcases['ds__dimonly'] = {
            "dims": [dict(name="x", size=2)],
        }

        # dataset with attrs and vars of all possible types
        # TODO: .. and missing-data testcases ???
        for dtype_name in data_types():
            dtype = 'S1' if dtype_name == 'string' else dtype_name
            if dtype_name == 'string':
                # Not working for now
                # TODO: fix !
                # continue
                pass

            testcases[f'ds__dtype__{dtype_name}'] = {
                "attrs": {
                    f"tstatt_type__{dtype_name}__single": _Datatype_Sample_Values[dtype_name][0],
                    f"tstatt_type__{dtype_name}__multi": _Datatype_Sample_Values[dtype_name],
                },
                "vars": [dict(name="vx", dims=[], dtype=dtype)],
            }

        testcases['ds__stringvar__singlepoint'] = {
            "dims": [dict(name='strlen', size=3)],
            "vars": [dict(
                        name="vx", dims=['strlen'], dtype='S1',
                        data=np.array('abc', dtype='S1')
                     )],
        }

        testcases['ds__stringvar__multipoint'] = {
            "dims": [dict(name='x', size=2),
                     dict(name='strlen', size=3),
                     ],
            "vars": [dict(
                name="vx", dims=['x', 'strlen'], dtype='S1',
                data=np.array([list('abc'), list('def')], dtype='S1')
            )],
        }

    return testcases

_Standard_Testcases: Dict[str, Union[Path, dict]] = _build_all_testcases()

@pytest.fixture(scope="session")
def session_testdir(tmp_path_factory):
    tmp_dir = tmp_path_factory.mktemp("standard_schema_testfiles")
    return tmp_dir


_SESSION_TESTFILES_DIR = Path('/var/tmp/ncdata_pytest')
if not _SESSION_TESTFILES_DIR.exists():
    _SESSION_TESTFILES_DIR.mkdir()


@dataclass
class Schema:
    name: str = ""
    spec: dict = None
    filepath: Path = None


_TESTCASE_BUILT_FILES = []


@pytest.fixture(params=list(_Standard_Testcases.keys()), scope='function')
def standard_testcase(request):  #, session_testdir):
    """
    A fixture which iterates over a set of "standard" dataset testcases.

    For each one, build the testfile and return a Schema tuple (name, spec, filepath).
    Since scope="session", each file gets built only once per session.
    """
    name = request.param
    spec = _Standard_Testcases[name]
    if isinstance(spec, dict):
        # Build a temporary testfile from the spec, and pass that out.
        # filepath = session_testdir / f"sampledata_{name}.nc"
        filepath = str(_SESSION_TESTFILES_DIR / f"sampledata_{name}.nc")
        if filepath not in _TESTCASE_BUILT_FILES:
            make_testcase_dataset(filepath, spec)
            _TESTCASE_BUILT_FILES.append(filepath)
        else:
            pass
    else:
        # Otherwise 'spec' is a test filepath: pass that, plus spec={}
        filepath = spec
        spec = {}
    return Schema(name=name, spec=spec, filepath=filepath)

"""
An iteration that produces a sequence of possible file specifications.
"""
import netCDF4
import netCDF4 as nc
import numpy as np


def data_types():
    """
    Produce a sequence of valid netCDF4 datatypes.

    All possible datatypes for variable data or attributes.
    Not yet supporting variable or user-defined (structured) types.

    Results are strings for all valid numeric dtypes, plus 'string'.
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
    ds: netCDF4.Dataset,  # or an inner Group
    parent_spec: dict = None,
    in_group_path: str = "",
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
    attr_specs = spec.get("attrs", [])

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
        if data:
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
            n_points = np.product(shape)
            # if nc_var.dtype.kind == 'S':
            #     data = np.array(
            #         'abcdefghijklmnopqrstuvwxyz'[:n_points],
            #         dype='S1'
            #     )
            # else:
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
            in_group_path=f"{in_group_path}/{group_name}",
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
        _write_nc4_dataset(spec, ds)
    finally:
        ds.close()


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


def check_create_simple_data():
    # Create a somewhat minimal file spec.
    test_filepath = "tmp.nc"
    make_testcase_dataset(test_filepath, _simple_test_spec)
    from os import system as ss

    ss("ncdump tmp.nc")


if __name__ == "__main__":
    # test create
    check_create_simple_data()

"""
NOTES:

Name coding for dataset sample params + their associated test-files

ds_Empty

ds_AttrF1Multi
ds_AttrI2Single

ds_VarNodims  (special-case)
ds_VarAttr
ds_VarType * types

var
  types * miss(Nomiss,Nmiss) * fill(user,default,userdefault)

ds_VarNodims
ds_Var1D * Fixed/Unlim
ds_Var2d * (Unlime0 / Unlim1 / Unlim2)

ds_GroupEmpty
ds_GroupAttr
# check that this is possible ??
ds_GroupDimonly * Unlim0/Unlim1/Unlim2

# original non-group check for unlim dims
# test for different dims including single+multiplle unlimited dims
# need to control dims to suit the vars under test
ds_VarDims0
ds_VarDims1Unlim0
ds_VarDims1Unlim1
ds_VarDims2Unlim0
ds_VarDims2Unlim1
ds_VarDims2Unlim2

# beyond 'VarDims', also need to check for fill behaviour
# treat this as a separate set of tests ?
ds_Var(type)(missing0/MissingN)(Filldefault/Filluser/Filluserdefault)
    (Defaultfill/Userfill/Userdefaultfill)
E.G. ds_Var:typeString:missingN:fillUserdefault
E.G. ds_Var:typeF4:missing0:fillUser
  - these are all 1D vars, of some greater size.
  - the given values and 'user' fill-values are taken from dicts

# group-vars and dims testing
# need to control parentvars, groupvars, parentdims, groupdims
ds_GroupvarDims0
ds_GroupvarDims1Local1Fixed1
ds_GroupvarDims1Local1Unlim1
ds_GroupvarDims1Parent1Fixed1
ds_GroupvarDims1Parent1Unlim1
ds_GroupvarDims2Local2Fixed2
ds_GroupvarDims2Local2Fixed1Unlim1
ds_GroupvarDims2Local1Fixed1Parent1Fixed1
ds_GroupvarDims2Local1Unlim1Parent1Fixed1
ds_GroupvarDims2Local1Fixed1Parent1Unlim1
ds_GroupvarDims2Local1Unlim1Parent1Unlim1
ds_GroupvarDims2Parent2Fixed2
ds_GroupvarDims2Parent2Fixed1Unlim1
ds_GroupvarDims2Parent2Unlim2

# rethink with above style..
ds_Groupvar:Dims2:Local2:(Fixed/Unlim/Fixed1Unlim1)
ds_Groupvar:Dims2:Local1:Fixed:Parent1:Unlim
ds_Groupvar:Dims2:Parent2:Unlim


ds_Groupvar:Dims2:Local1:Fixed:Parent1:Unlim
==> controls ...
  parent-dims: [('dim1', 3, True)]
  group-dims: [('gdim1', 4)]
  group-vars: ['gv1', ('dim1', 'gdim1')]



"""

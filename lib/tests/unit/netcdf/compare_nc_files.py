"""
Utility for comparing 2 netcdf files,
for purposes of testing ncdata.netcdf4 behaviour.

"""

from pathlib import Path
from typing import AnyStr, List, Union
from warnings import warn

import netCDF4 as nc
import numpy as np


def compare_nc_files(
    dataset_or_path_1: Union[Path, AnyStr, nc.Dataset],
    dataset_or_path_2: Union[Path, AnyStr, nc.Dataset],
    check_dims_order: bool = True,
    check_vars_order: bool = True,
    check_attrs_order: bool = True,
    check_groups_order: bool = True,
    check_var_data: bool = True,
    suppress_warnings: bool = False,
) -> List[str]:
    """
    Compare 2 netcdf files, given as paths or open :class:`netCDF4.Dataset`\\s

    Parameters
    ----------
    dataset_or_path_1, dataset_or_path_2 : str or Path or :class:`netCDF4.Dataset`
        two files to compare
    check_dims_order, check_vars_order, check_attrs_order, check_groups_order : bool, default True
        If False, no error results from the same contents in a different order,
        however unless `suppress_warnings` the error string is issued as a warning.
    check_var_data
        If True, all variable data is also checked for equality.
        If False, only dtype and shape are compared.

    Returns
    -------
    errs : list of str
        a list of error strings.
        If empty, no differences were found.

    """
    ds1_was_path = not hasattr(dataset_or_path_1, "variables")
    ds2_was_path = not hasattr(dataset_or_path_2, "variables")
    ds1, ds2 = None, None
    try:
        if ds1_was_path:
            ds1 = nc.Dataset(dataset_or_path_1)
        else:
            ds1 = dataset_or_path_1

        if ds2_was_path:
            ds2 = nc.Dataset(dataset_or_path_2)
        else:
            ds2 = dataset_or_path_2

        errs = []
        _compare_nc_groups(
            errs,
            ds1,
            ds2,
            group_id_string="Dataset",
            dims_order=check_dims_order,
            vars_order=check_vars_order,
            attrs_order=check_attrs_order,
            groups_order=check_groups_order,
            data_values=check_var_data,
            suppress_warnings=suppress_warnings,
        )
    finally:
        if ds1_was_path and ds1:
            ds1.close()
        if ds2_was_path and ds2:
            ds2.close()

    return errs


def _compare_nc_groups(
    errs,
    g1,
    g2,
    group_id_string,
    dims_order=True,
    vars_order=True,
    attrs_order=True,
    groups_order=True,
    data_values=True,
    suppress_warnings=False,
):
    # Compare lists of dimension names
    dimnames, dimnames2 = [list(grp.dimensions.keys()) for grp in (g1, g2)]

    def compare_strlists(l1, l2, elemname, order_strict=True):
        msg = f"{elemname} do not match: {l1} != {l2}"
        ok = l1 == l2
        ok_except_order = ok
        if not ok:
            ok_except_order = sorted(l1) == sorted(l2)

        if not ok:
            if not ok_except_order or order_strict:
                errs.append(msg)
            elif ok_except_order and not suppress_warnings:
                warn("(Ignoring: " + msg + " )", category=UserWarning)

    compare_strlists(
        dimnames,
        dimnames2,
        f"{group_id_string} dimension lists",
        order_strict=dims_order,
    )

    # Compare the dimensions themselves
    for dimname in dimnames:
        if dimname not in dimnames2:
            continue
        d1, d2 = [grp.dimensions[dimname] for grp in (g1, g2)]
        dimlen, dimlen2 = [dim.size for dim in (d1, d2)]
        if dimlen != dimlen2:
            msg = (
                f'{group_id_string} "{dimname}" dimensions '
                f"have different sizes: {dimlen} != {dimlen2}"
            )
            errs.append(msg)

    def compare_attributes(obj1, obj2, elemname):
        # Compare attribute name lists
        attrnames, attrnames2 = [obj.ncattrs() for obj in (obj1, obj2)]
        compare_strlists(
            attrnames,
            attrnames2,
            f"{elemname} attribute lists",
            order_strict=attrs_order,
        )

        # Compare the attributes themselves (dtypes and values)
        for attrname in attrnames:
            if attrname not in attrnames2:
                continue
            attr, attr2 = [obj.getncattr(attrname) for obj in (obj1, obj2)]
            dtype, dtype2 = [
                # Get x.dtype, or fallback on type(x) -- basically, for strings.
                getattr(attr, "dtype", type(attr))
                for attr in (attr, attr2)
            ]
            if dtype != dtype2:
                msg = (
                    f'{elemname} "{attrname}" attribute datatypes differ : '
                    f"{dtype!r} != {dtype2!r}"
                )
                errs.append(msg)

            # Cast attrs, which might be strings, to arrays for comparison
            arr, arr2 = [np.array(attr) for attr in (attr, attr2)]
            if arr.shape != arr2.shape or not np.all(arr == arr2):
                msg = (
                    f'{elemname} "{attrname}" attribute values differ : '
                    f"{attr!r} != {attr2!r}"
                )
                errs.append(msg)

    # Compare file attribute lists
    compare_attributes(g1, g2, group_id_string)

    # Compare file attributes

    # Compare lists of variables
    varnames, varnames2 = [list(grp.variables.keys()) for grp in (g1, g2)]
    compare_strlists(
        varnames,
        varnames2,
        f"{group_id_string} variable lists",
        order_strict=dims_order,
    )

    # Compare the variables themselves
    for varname in varnames:
        if varname not in varnames2:
            continue
        v1, v2 = [grp.variables[varname] for grp in (g1, g2)]

        var_id_string = f'{group_id_string} variable "{varname}"'

        # dimensions
        dims, dims2 = [v.dimensions for v in (v1, v2)]
        if dims != dims2:
            msg = f"{var_id_string} dimensions differ : {dims!r} != {dims2!r}"

        # attributes
        compare_attributes(v1, v2, var_id_string)

        # dtypes
        dtype, dtype2 = [v.datatype for v in (v1, v2)]
        if dtype != dtype2:
            msg = f"{var_id_string} datatypes differ : {dtype!r} != {dtype2!r}"
            errs.append(msg)

        # data values
        data, data2 = [v[:] for v in (v1, v2)]
        n_diffs = np.count_nonzero(data != data2)
        if n_diffs:
            msg = f"{var_id_string} data values differ, at {n_diffs} points."

    # Finally, recurse over groups
    grpnames, grpnames2 = [list(grp.groups.keys()) for grp in (g1, g2)]
    compare_strlists(
        grpnames, grpnames2, f"{group_id_string} subgroup lists", groups_order
    )
    for grpname in grpnames:
        if grpname not in grpnames2:
            continue
        grp1, grp2 = [grp.groups[grpname] for grp in (g1, g2)]
        _compare_nc_groups(
            errs,
            grp1,
            grp2,
            group_id_string=f"{group_id_string}/{grpname}",
            dims_order=dims_order,
            vars_order=vars_order,
            attrs_order=attrs_order,
            groups_order=groups_order,
            data_values=data_values,
        )


if __name__ == "__main__":
    fps = [
        "/home/h05/itpp/tmp.nc",
        "/home/h05/itpp/tmp2.nc",
        "/home/h05/itpp/mask.nc",
        "/home/h05/itpp/tmps.nc",
        "/home/h05/itpp/tmps2.nc",
    ]
    fp1, fp2, fp3, fp4, fp5 = fps
    pairs = [
        [fp1, fp1],
        [fp1, fp2],
        [fp1, fp3],
        [fp4, fp5],
    ]
    for p1, p2 in pairs:
        errs = compare_nc_files(p1, p2, check_attrs_order=False)
        print("")
        print(f"Compare {p1} with {p2} : {len(errs)} errors ")
        for err in errs:
            print("  ", err)
        print("-ends-")

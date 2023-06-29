"""
Utility for comparing 2 netcdf datasets.

Works with file-specs, netCDF4.Datasets *or* NcData.

For purposes of testing ncdata.netcdf4 behaviour.
TODO: one day might be public ?
"""

from pathlib import Path
from typing import AnyStr, List, Union
from warnings import warn

import netCDF4
import netCDF4 as nc
import numpy as np

from ncdata import NcData


def compare_nc_datasets(
    dataset_or_path_1: Union[Path, AnyStr, nc.Dataset, NcData],
    dataset_or_path_2: Union[Path, AnyStr, nc.Dataset, NcData],
    check_dims_order: bool = True,
    check_vars_order: bool = True,
    check_attrs_order: bool = True,
    check_groups_order: bool = True,
    check_var_data: bool = True,
    suppress_warnings: bool = False,
) -> List[str]:
    r"""
    Compare netcdf data.

    Accepts paths, pathstrings, open :class:`netCDF4.Dataset`\\s or :class:`NcData` objects.

    Parameters
    ----------
    dataset_or_path_1, dataset_or_path_2 : str or Path or netCDF4.Dataset or NcData
        two datasets to compare, either NcData or netCDF4
    check_dims_order, check_vars_order, check_attrs_order, check_groups_order : bool, default True
        If False, no error results from the same contents in a different order,
        however unless `suppress_warnings` is True, the error string is issued as a warning.
    check_var_data : bool, default True
        If True, all variable data is also checked for equality.
        If False, only dtype and shape are compared.
    suppress_warnings : bool, default False
        When False (the default), report changes in content order as Warnings.
        When True, ignore changes in ordering.

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
            data_equality=check_var_data,
            suppress_warnings=suppress_warnings,
        )
    finally:
        if ds1_was_path and ds1:
            ds1.close()
        if ds2_was_path and ds2:
            ds2.close()

    return errs


def _compare_name_lists(
    errslist, l1, l2, elemname, order_strict=True, suppress_warnings=False
):
    msg = f"{elemname} do not match: {list(l1)} != {list(l2)}"
    ok = l1 == l2
    ok_except_order = ok
    if not ok:
        ok_except_order = sorted(l1) == sorted(l2)

    if not ok:
        if not ok_except_order or order_strict:
            errslist.append(msg)
        elif ok_except_order and not suppress_warnings:
            warn("(Ignoring: " + msg + " )", category=UserWarning)


def _isncdata(obj):
    """
    A crude test to distinguish NcData objects from similar netCDF4 ones.

    Used to support comparisons on either type of data.
    """
    return hasattr(obj, "_print_content")

def _array_eq(a1, a2):
    """
    A suitable local definition of precise array equality.

    Assumes values (attributes) presented as numpy arrays.
    Matches any NaNs.
    Does *NOT* handle masked data -- which does not occur in attributes.
    """
    result = True
    result &= a1.shape == a2.shape
    result &= a1.dtype == a2.dtype
    if result:
        if a1.dtype.kind in ('S', 'U', 'b'):
            result = np.all(a1 == a2)
        else:
            # array_equal handles possible NaN cases
            result = np.array_equal(a1, a2, equal_nan=True)
    return result

def _compare_attributes(
    errs,
    obj1,
    obj2,
    elemname,
    attrs_order=True,
    suppress_warnings=False,
    force_first_attrnames=None,
):
    """
    Compare attribute name lists.

    Does not return results, but appends error messages to 'errs'.
    """
    attrnames, attrnames2 = [
        obj.attributes.keys() if _isncdata(obj) else obj.ncattrs()
        for obj in (obj1, obj2)
    ]
    if attrs_order and force_first_attrnames:

        def fix_orders(attrlist):
            for name in force_first_attrnames[::-1]:
                if name in attrlist:
                    attrlist = [name] + [n for n in attrlist if n != name]
            return attrlist

        attrnames = fix_orders(attrnames)
        attrnames2 = fix_orders(attrnames2)

    _compare_name_lists(
        errs,
        attrnames,
        attrnames2,
        f"{elemname} attribute lists",
        order_strict=attrs_order,
        suppress_warnings=suppress_warnings,
    )

    # Compare the attributes themselves (dtypes and values)
    for attrname in attrnames:
        if attrname not in attrnames2:
            # Only compare attributes existing on both inputs.
            continue

        attr, attr2 = [
            (
                obj.attributes[attrname].value
                if _isncdata(obj)
                else obj.getncattr(attrname)
            )
            for obj in (obj1, obj2)
        ]

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
        else:
            # If datatypes match (only then), compare values
            # Cast attrs, which might be strings, to arrays for comparison
            arr, arr2 = [np.asarray(attr) for attr in (attr, attr2)]
            if not _array_eq(arr, arr2):
                # N.B. special comparison to handle strings and NaNs
                msg = (
                    f'{elemname} "{attrname}" attribute values differ : '
                    f"{attr!r} != {attr2!r}"
                )
                errs.append(msg)


def _compare_nc_groups(
    errs: List[str],
    g1: Union[netCDF4.Dataset, netCDF4.Group],
    g2: Union[netCDF4.Dataset, netCDF4.Group],
    group_id_string: str,
    dims_order: bool = True,
    vars_order: bool = True,
    attrs_order: bool = True,
    groups_order: bool = True,
    data_equality: bool = True,
    suppress_warnings: bool = False,
):
    """
    Inner routine to compare either whole datasets or subgroups.

    Note that, rather than returning a list of error strings, it appends them to the
    passed arg `errs`.  This just makes recursive calling easier.
    """
    # Compare lists of dimension names
    dimnames, dimnames2 = [list(grp.dimensions.keys()) for grp in (g1, g2)]
    _compare_name_lists(
        errs,
        dimnames,
        dimnames2,
        f"{group_id_string} dimension lists",
        order_strict=dims_order,
        suppress_warnings=suppress_warnings,
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

    # Compare file attributes
    _compare_attributes(
        errs,
        g1,
        g2,
        group_id_string,
        attrs_order=attrs_order,
        suppress_warnings=suppress_warnings,
    )

    # Compare lists of variables
    varnames, varnames2 = [list(grp.variables.keys()) for grp in (g1, g2)]
    _compare_name_lists(
        errs,
        varnames,
        varnames2,
        f"{group_id_string} variable lists",
        order_strict=dims_order,
        suppress_warnings=suppress_warnings,
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
        _compare_attributes(
            errs,
            v1,
            v2,
            var_id_string,
            attrs_order=attrs_order,
            suppress_warnings=suppress_warnings,
            force_first_attrnames=[
                "_FillValue"
            ],  # for some reason, this doesn't always list consistently
        )

        # dtypes
        dtype, dtype2 = [
            v.dtype if _isncdata(v) else v.datatype for v in (v1, v2)
        ]
        if dtype != dtype2:
            msg = f"{var_id_string} datatypes differ : {dtype!r} != {dtype2!r}"
            errs.append(msg)

        # data values
        is_str, is_str2 = (dt.kind in ("U", "S") for dt in (dtype, dtype2))
        # TODO: is this correct check to allow compare between different dtypes?
        if data_equality and dims == dims2 and is_str == is_str2:
            # N.B. don't check shapes here: we already checked dimensions.
            # NOTE: no attempt to use laziness here.  Could be improved.
            def getdata(var):
                if _isncdata(var):
                    data = var.data
                    if hasattr(data, "compute"):
                        data = data.compute()
                else:
                    # expect var to be an actual netCDF4.Variable
                    # (check for obscure property NOT provided by mimics)
                    assert hasattr(var, "use_nc_get_vars")
                    data = var[:]
                # Return 0D as 1D, as this makes results simpler to interpret.
                if data.ndim == 0:
                    data = data.flatten()
                    assert data.shape == (1,)
                return data

            data, data2 = (getdata(v) for v in (v1, v2))
            flatdata, flatdata2 = (
                np.asanyarray(arr).flatten() for arr in (data, data2)
            )

            # For simpler checking, use flat versions
            flat_diff_inds = (
                []
            )  # NB *don't* make this an array, it causes problems
            if any(np.ma.is_masked(arr) for arr in (data, data2)):
                # If data is masked, count mask mismatches and skip those points
                mask, mask2 = (
                    np.ma.getmaskarray(array)
                    for array in (flatdata, flatdata2)
                )
                flat_diff_inds = list(np.where(mask != mask2)[0])
                # Replace all masked points to exclude them from unmasked-point checks.
                either_masked = mask | mask2
                dtype = flatdata.dtype
                if dtype.kind in ("S", "U"):
                    safe_fill_const = ""
                else:
                    safe_fill_const = np.zeros((1,), dtype=flatdata.dtype)[0]
                flatdata[either_masked] = safe_fill_const
                flatdata2[either_masked] = safe_fill_const

            flat_diff_inds += list(np.where(flatdata != flatdata2)[0])
            n_diffs = len(flat_diff_inds)
            if n_diffs:
                msg = f"{var_id_string} data contents differ, at {n_diffs} points: "
                ellps = ", ..." if n_diffs > 2 else ""
                diffinds = flat_diff_inds[:2]
                diffinds = [
                    np.unravel_index(ind, shape=data.shape) for ind in diffinds
                ]
                diffinds_str = ", ".join(repr(tuple(x)) for x in diffinds)
                inds_str = f"[{diffinds_str}{ellps}]"
                points_lhs_str = ", ".join(repr(data[ind]) for ind in diffinds)
                points_rhs_str = ", ".join(
                    repr(data2[ind]) for ind in diffinds
                )
                points_lhs_str = f"[{points_lhs_str}{ellps}]"
                points_rhs_str = f"[{points_rhs_str}{ellps}]"
                msg += (
                    f"@INDICES{inds_str}"
                    f" : LHS={points_lhs_str}, RHS={points_rhs_str}"
                )
                errs.append(msg)

    # Finally, recurse over groups
    grpnames, grpnames2 = [list(grp.groups.keys()) for grp in (g1, g2)]
    _compare_name_lists(
        errs,
        grpnames,
        grpnames2,
        f"{group_id_string} subgroup lists",
        order_strict=groups_order,
        suppress_warnings=suppress_warnings,
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
            data_equality=data_equality,
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
        errs = compare_nc_datasets(p1, p2, check_attrs_order=False)
        print("")
        print(f"Compare {p1} with {p2} : {len(errs)} errors ")
        for err in errs:
            print("  ", err)
        print("-ends-")

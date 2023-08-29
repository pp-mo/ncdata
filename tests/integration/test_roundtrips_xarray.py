"""
Test ncdata.xarray by checking roundtrips for standard testcases.

Testcases start as netcdf files.
(1) check equivalence of cubes : xarray.load(file) VS xarray.load(ncdata(file))
(2) check equivalence of files : xarray -> file VS xarray->ncdata->file
"""
from subprocess import check_output

import dask.array as da
import numpy as np
import pytest
import xarray

from ncdata.netcdf4 import from_nc4, to_nc4
from tests._compare_nc_datasets import compare_nc_datasets
from tests.data_testcase_schemas import (
    session_testdir,
    standard_testcase,
    BAD_LOADSAVE_TESTCASES,
)
from tests.integration.roundtrips_utils import (
    adjust_chunks,
    cubes_equal__corrected,
    set_tiny_chunks,
)

# Avoid complaints that imported fixtures are "unused"
standard_testcase, session_testdir, adjust_chunks

from ncdata.threadlock_sharing import lockshare_context
from ncdata.xarray import from_xarray, to_xarray

# _FIX_LOCKS = True
_FIX_LOCKS = False


@pytest.fixture(scope="session")
def use_xarraylock():
    if _FIX_LOCKS:
        with lockshare_context(xarray=True):
            yield
    else:
        yield


# _USE_TINY_CHUNKS = True
_USE_TINY_CHUNKS = False
set_tiny_chunks(_USE_TINY_CHUNKS)


def test_load_direct_vs_viancdata(
    standard_testcase, use_xarraylock, adjust_chunks, tmp_path
):
    source_filepath = standard_testcase.filepath
    ncdata = from_nc4(source_filepath)

    if standard_testcase.name in BAD_LOADSAVE_TESTCASES["xarray"]["load"]:
        pytest.skip("excluded testcase (xarray cannot load)")

    if any(
        key in standard_testcase.name
        for key in [
            # masked coord values problems
            # TODO: could fix this to get Dataset == to work  ??
            "testdata____transverse_mercator__projection_origin_attributes",
            # # masking in regular data variables
            "testdata____testing__cell_methods",
            "testdata____testing__test_monotonic_coordinate",
            "testdata____global__xyz_t__GEMS_CO2_Apr2006",
            "testdata____global__xyt__SMALL_total_column_co2",
            # string data length handling
            "testdata____label_and_climate__A1B__99999a__river__sep__2070__2099",
        ]
    ):
        pytest.skip("excluded testcase (xarray cannot load)")

    # _Debug = True
    _Debug = False
    if _Debug:
        print(f"\ntestcase: {standard_testcase.name}")
        print("spec =")
        print(standard_testcase.spec)
        print("\nncdata =")
        print(ncdata)
        print("\nncdump =")
        txt = check_output([f"ncdump {source_filepath}"], shell=True).decode()
        print(txt)

    # Load the testcase with Xarray.
    xr_ds = xarray.open_dataset(
        source_filepath,
        # decode_coords='all',
        chunks="auto",
    )

    # Load same, via ncdata
    xr_ncdata_ds = to_xarray(ncdata)

    def fix_dask_scalars(darray):
        # replace a dask array with one "safe" to compare, since there are bugs
        # causing exceptions when comparing np.ma.masked/np.nan scalars in dask.
        # In those cases, replace the array with the computed numpy value instead.
        if (
            # hasattr(darray, 'compute')
            1
            and darray.ndim == 0
            # and darray.compute() in (np.ma.masked, np.nan)
        ):
            # x
            # # Simply replace with the computed numpy array.

            # Replace with a numpy 0 scalar, of the correct dtype.
            darray = np.array(0, dtype=darray.dtype)
        return darray

    def fix_xarray_scalar_data(xrds):
        for varname, var in xrds.variables.items():
            if var.ndim == 0:
                data = var.data
                newdata = fix_dask_scalars(data)
                if newdata is not data:
                    # Replace the variable with a new one based on the new data.
                    # For some reason, "var.data = newdata" does not do this.
                    newvar = xarray.Variable(
                        dims=var.dims,
                        data=newdata,
                        attrs=var.attrs,
                        encoding=var.encoding,
                    )
                    xrds[varname] = newvar

    for ds in (xr_ds, xr_ncdata_ds):
        fix_xarray_scalar_data(ds)

    # # Fix converted result for extra entries in the 'coordinates' attributes.
    # for varname in xr_ncdata_ds.variables.keys():
    #     var, var_orig = (ds.variables[varname] for ds in (xr_ncdata_ds, xr_ds))
    #     newattrs, orig_attrs = (v.attrs.copy() for v in (var, var_orig))
    #     if newattrs != orig_attrs:
    #         # Does not work : del var.attrs['coordinates']
    #         # Demonstrate that change consists of extra names in 'coordinates'
    #         attrs1, attrs2 = (aa.copy() for aa in (newattrs, orig_attrs))
    #         for aa in (attrs1, attrs2):
    #             aa.pop("coordinates", None)
    #         assert attrs1 == attrs2
    #         # Demonstrate that coords got extended + fix it.
    #         coords, orig_coords = (
    #             aa.get("coordinates", None) for aa in (newattrs, orig_attrs)
    #         )
    #         coords, orig_coords = [
    #             [] if cc is None else cc.split(" ")
    #             for cc in (coords, orig_coords)
    #         ]
    #         assert set(coords) > set(orig_coords)
    #         newcoords = [co for co in coords if co in orig_coords]
    #         if len(newcoords) == 0:
    #             newattrs.pop("coordinates", None)
    #         else:
    #             newattrs["coordinates"] = " ".join(newcoords)
    #         newvar = xarray.Variable(
    #             dims=var.dims,
    #             data=var.data,
    #             attrs=newattrs,
    #             encoding=var.encoding,
    #         )
    #         xr_ncdata_ds[varname] = newvar
    #
    #     attrs, orig_attrs = (
    #         ds.variables[varname].attrs for ds in (xr_ncdata_ds, xr_ds)
    #     )
    #     assert attrs == orig_attrs

    xr_compare = xr_ds.identical(xr_ncdata_ds)

    # Debug what is different when datasets don't match.
    # Since using 'from_xarray' is rather circular, for now at least save to
    # disk files, and compare that way.
    temp_xr_path = tmp_path / "tmp_out_xr.nc"
    temp_xr_ncdata_path = tmp_path / "tmp_out_xr_ncdata.nc"
    xr_ds.to_netcdf(temp_xr_path)
    xr_ncdata_ds.to_netcdf(temp_xr_ncdata_path)
    ds_diffs = compare_nc_datasets(
        temp_xr_path,
        temp_xr_ncdata_path,
        check_dims_order=False,
        # check_var_data=False
    )
    print("\nDATASET COMPARE RESULTS:\n" + "\n".join(ds_diffs))
    print("\n\nXR NATIVE-LOADED DATASET:\n", xr_ds)
    # Even if so, they ought both to say "ok".
    assert (xr_compare, ds_diffs) == (True, [])


def test_save_direct_vs_viancdata(standard_testcase, tmp_path):
    source_filepath = standard_testcase.filepath
    ncdata = from_nc4(source_filepath)

    excluded_testcases = BAD_LOADSAVE_TESTCASES["xarray"]["load"]
    excluded_testcases += [
        # string data length handling
        "testdata____label_and_climate__A1B__99999a__river__sep__2070__2099",

        # Here there's a problem with the type.
        # "ds__stringvar__multipoint",
    ]
    if any(key in standard_testcase.name for key in excluded_testcases):
        pytest.skip("excluded testcase")

    # Load the testcase into xarray.
    xrds = xarray.load_dataset(source_filepath, chunks="auto")


    # Re-save from Xarray
    temp_direct_savepath = tmp_path / "temp_save_xarray.nc"
    xrds.to_netcdf(temp_direct_savepath)
    # Save same, via ncdata
    temp_ncdata_savepath = tmp_path / "temp_save_xarray_via_ncdata.nc"
    to_nc4(from_xarray(xrds), temp_ncdata_savepath)

    # _Debug = True
    _Debug = False
    if _Debug:
        print(f"\ntestcase: {standard_testcase.name}")
        print("spec =")
        print(standard_testcase.spec)
        print("\nncdata =")
        print(ncdata)
        print("\nncdump ORIGINAL TESTCASE SOURCEFILE =")
        txt = check_output([f"ncdump {source_filepath}"], shell=True).decode()
        print(txt)
        print("\nncdump DIRECT FROM XARRAY =")
        txt = check_output(
            [f"ncdump {temp_direct_savepath}"], shell=True
        ).decode()
        print(txt)
        print("\nncdump VIA NCDATA =")
        txt = check_output(
            [f"ncdump {temp_ncdata_savepath}"], shell=True
        ).decode()
        print(txt)

    # Check equivalence
    results = compare_nc_datasets(
        temp_direct_savepath, temp_ncdata_savepath, check_dims_order=False
    )
    assert results == []

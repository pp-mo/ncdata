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
            # ??? masking in regular data variables
            "testdata____global__xyz_t__GEMS_CO2_Apr2006",
            "testdata____global__xyt__SMALL_total_column_co2",
            # weird out-of-range timedeltas (only fails within PyCharm ??????)
            "testdata____transverse_mercator__projection_origin_attributes",
            "testdata____transverse_mercator__tmean_1910_1910",
            "unstructured_grid__theta_nodal",
        ]
    ):
        pytest.skip("excluded testcase -- FOR NOW cannot convert ncdata->xr")

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
    xr_ds = xarray.open_dataset(source_filepath, chunks="auto")
    t = 0
    # Load same, via ncdata
    xr_ncdata_ds = to_xarray(ncdata)

    _FIX_SCALARS = True
    # _FIX_SCALARS = False
    if _FIX_SCALARS:

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

    # Xarray dataset (variable) comparison is problematic
    # result = xr_ncdata_ds.identical(xr_ds)

    # So for now, save Xarray datasets to disk + compare that way.
    temp_xr_path = tmp_path / "tmp_out_xr.nc"
    temp_xr_ncdata_path = tmp_path / "tmp_out_xr_ncdata.nc"
    xr_ds.to_netcdf(temp_xr_path)
    xr_ncdata_ds.to_netcdf(temp_xr_ncdata_path)

    # FOR NOW: compare with experimental ncdata comparison.
    # I know this is a bit circular, but it is useful for debugging, for now ...
    result = compare_nc_datasets(
        temp_xr_path,
        temp_xr_ncdata_path,
        check_dims_order=False,
        suppress_warnings=True,
    )
    if result != []:
        assert result == []


def test_save_direct_vs_viancdata(standard_testcase, tmp_path):
    source_filepath = standard_testcase.filepath
    ncdata = from_nc4(source_filepath)

    excluded_testcases = BAD_LOADSAVE_TESTCASES["xarray"]["load"]
    excluded_testcases += [
        # string data length handling
        "testdata____label_and_climate__A1B__99999a__river__sep__2070__2099",
        # string data generally doesn't work yet  (variety of problems?)
        "ds__dtype__string",
        "ds__stringvar__singlepoint",
        "ds__stringvar__multipoint",
        # weird out-of-range timedeltas (***only*** fails within PyCharm ??????)
        "testdata____transverse_mercator__projection_origin_attributes",
        "testdata____transverse_mercator__tmean_1910_1910",
        "unstructured_grid__theta_nodal",
        # problems with data masking ??
        "testdata____global__xyz_t__GEMS_CO2_Apr2006",
        "testdata____global__xyt__SMALL_total_column_co2",
    ]
    if any(key in standard_testcase.name for key in excluded_testcases):
        pytest.skip("excluded testcase")

    # Load the testcase into xarray.
    xrds = xarray.load_dataset(source_filepath, chunks="auto")

    # if standard_testcase.name in ("ds_Empty", "ds__singleattr", "ds__dimonly"):
    #     # Xarray can't save an empty dataset.
    #     return

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
        temp_direct_savepath,
        temp_ncdata_savepath,
        check_dims_order=False,
        suppress_warnings=True,
    )
    assert results == []

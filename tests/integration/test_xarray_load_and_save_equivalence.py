"""
Test ncdata.xarray by checking roundtrips for standard testcases.

Testcases start as netcdf files.
(1) check equivalence of cubes : xarray.load(file) VS xarray.load(ncdata(file))
(2) check equivalence of files : xarray -> file VS xarray->ncdata->file
"""
import numpy as np
from subprocess import check_output

import pytest
import xarray

from ncdata.netcdf4 import from_nc4, to_nc4
from tests._compare_nc_datasets import compare_nc_datasets
from tests.data_testcase_schemas import (
    BAD_LOADSAVE_TESTCASES,
    session_testdir,
    standard_testcase,
)
from tests.integration.equivalence_testing_utils import (
    adjust_chunks,
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

    excluded_cases = BAD_LOADSAVE_TESTCASES["xarray"]["load"]
    excluded_cases.extend(BAD_LOADSAVE_TESTCASES["xarray"]["save"])
    if standard_testcase.name in excluded_cases:
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
    xr_ds = xarray.open_dataset(source_filepath, chunks=-1)

    # Load same, via ncdata
    xr_ncdata_ds = to_xarray(ncdata)

    testvar_names = None
    if (standard_testcase.name == "ds_testdata1") or ("toa_brightness" in standard_testcase.name):
        testvar_names = ['time']
    elif standard_testcase.name == r"testdata__\lambert_azimuthal_equal_area\euro_air_temp":
        testvar_names = ["time", "forecast_reference_time"]
        # testvar_names = ["time"]
        # testvar_names = ["forecast_reference_time"]
    elif "theta_nodal" in standard_testcase.name:
        testvar_names = ["Mesh0"]

    if testvar_names:
        # print("XR ds")
        # print(xr_ds)
        #
        # print("")
        # print("xrds == xrncds ?", xr_ds.identical(xr_ncdata_ds))

        for testvar_name in testvar_names:
            print(f"\nxr_ds['{testvar_name}']:\n", xr_ds[testvar_name])
            print(f"xr_ncdata_ds['{testvar_name}']:\n", xr_ncdata_ds[testvar_name])
            print(f"xr_ds['{testvar_name}'].encoding['units']:\n", xr_ds[testvar_name].encoding.get('units'))
            print(f"xr_ncdata_ds['{testvar_name}'].encoding['units']:\n", xr_ncdata_ds[testvar_name].encoding.get('units'))
            # Xarray dataset (variable) comparison is problematic
            # result = xr_ncdata_ds.identical(xr_ds)

            # do_fix = "none"
            # do_fix = "fix_xrds"
            # do_fix = "fix_xrncds"
            do_fix = "fix_origshape"
            if do_fix == "fix_xrncds":
                print('\nOLD xrncds data:\n', xr_ncdata_ds[testvar_name].data)
                xr_ncdata_ds[testvar_name].data = xr_ncdata_ds[testvar_name].data.compute()
                print('NEW xrncds data:\n', xr_ncdata_ds[testvar_name].data)
            elif do_fix == "fix_xrds":
                import dask.array as da
                print('\nOLD xrds data:\n', xr_ds[testvar_name].data)
                data = xr_ds[testvar_name].data
                xr_ds[testvar_name].data = da.from_array(data, meta=np.ndarray((), dtype=data.dtype), chunks=-1)
                print('NEW xrds data:\n', xr_ds[testvar_name].data)
            elif do_fix == "fix_origshape":
                xr_ncdata_ds[testvar_name].encoding['original_shape'] = ()

    # So for now, save Xarray datasets to disk + compare that way.
    temp_xr_path = tmp_path / "tmp_out_xr.nc"
    temp_xr_ncdata_path = tmp_path / "tmp_out_xr_ncdata.nc"

    xr_ds.to_netcdf(temp_xr_path)
    xr_ncdata_ds.to_netcdf(temp_xr_ncdata_path)

    if _Debug:
        print("\n\n-----\nResult ncdump : 'DIRECT' nc4 -> xr -> nc4 ... ")
        txt = check_output([f"ncdump {temp_xr_path}"], shell=True).decode()
        print(txt)
        print(
            "\n\n-----\nResult ncdump : 'INDIRECT'' nc4 -> ncdata-> xr -> nc4 ... "
        )
        txt = check_output(
            [f"ncdump {temp_xr_ncdata_path}"], shell=True
        ).decode()
        print(txt)

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
    excluded_testcases.extend(BAD_LOADSAVE_TESTCASES["xarray"]["save"])
    for excl in excluded_testcases:
        print('  ', excl)
    if any(key in standard_testcase.name for key in excluded_testcases):
        pytest.skip("excluded testcase")

    # Load the testcase into xarray.
    xrds = xarray.load_dataset(source_filepath, chunks=-1)

    # Re-save from Xarray
    temp_direct_savepath = tmp_path / "temp_save_xarray.nc"
    xrds.to_netcdf(temp_direct_savepath)
    # Save same, via ncdata
    temp_ncdata_savepath = tmp_path / "temp_save_xarray_via_ncdata.nc"
    ncds_fromxr = from_xarray(xrds)
    to_nc4(ncds_fromxr, temp_ncdata_savepath)

    # _Debug = True
    _Debug = False
    if _Debug:
        ncdump_opts = "-h"
        # ncdump_opts = ""
        txt = f"""
        testcase: {standard_testcase.name}
        spec = {standard_testcase.spec}
        ncdata = ...
        {ncdata}
        ncdump ORIGINAL TESTCASE SOURCEFILE =
        """
        txt += check_output(
            [f"ncdump {ncdump_opts} {source_filepath}"], shell=True
        ).decode()
        txt += "\nncdump DIRECT FROM XARRAY ="
        txt += check_output(
            [f"ncdump {ncdump_opts} {temp_direct_savepath}"], shell=True
        ).decode()
        txt += "\nncdump VIA NCDATA ="
        txt += check_output(
            [f"ncdump {ncdump_opts} {temp_ncdata_savepath}"], shell=True
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

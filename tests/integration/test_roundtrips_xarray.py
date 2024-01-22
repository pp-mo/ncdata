"""
Test ncdata.xarray by checking roundtrips for standard testcases.

Testcases start as netcdf files.
(1) check equivalence of cubes : xarray.load(file) VS xarray.load(ncdata(file))
(2) check equivalence of files : xarray -> file VS xarray->ncdata->file
"""
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
from tests.integration.roundtrips_utils import (
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

    if standard_testcase.name in BAD_LOADSAVE_TESTCASES["xarray"]["load"]:
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

    # Xarray dataset (variable) comparison is problematic
    # result = xr_ncdata_ds.identical(xr_ds)

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

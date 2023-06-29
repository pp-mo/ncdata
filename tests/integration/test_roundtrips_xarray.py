"""
Test ncdata.xarray by checking roundtrips for standard standard_testcases_func.

Testcases start as netcdf files.
(1) check equivalence of cubes : xarray.load(file) VS xarray.load(ncdata(file))
(2) check equivalence of files : xarray -> file VS xarray->ncdata->file
"""
from subprocess import check_output

import dask.array as da
import xarray
import pytest

from ncdata.netcdf4 import from_nc4, to_nc4
from tests._compare_nc_datasets import compare_nc_datasets
from tests.data_testcase_schemas import standard_testcase, session_testdir
from tests.integration.roundtrips_utils import (
    cubes_equal__corrected, set_tiny_chunks, adjust_chunks
)

# Avoid complaints that imported fixtures are "unused"
standard_testcase, session_testdir, adjust_chunks

from ncdata.xarray import from_xarray, to_xarray
from ncdata.threadlock_sharing import sharing_context

_FIX_LOCKS = True
# _FIX_LOCKS = False
if _FIX_LOCKS:

    @pytest.fixture(scope="session")
    def use_xarraylock():
        with sharing_context(xarray=True):
            yield


# _USE_TINY_CHUNKS = True
_USE_TINY_CHUNKS = False
set_tiny_chunks(_USE_TINY_CHUNKS)


def test_load_direct_vs_viancdata(standard_testcase, use_xarraylock, adjust_chunks):
    source_filepath = standard_testcase.filepath
    ncdata = from_nc4(source_filepath)

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
    xr_ds = xarray.load_dataset(source_filepath, chunks="auto")
    # Load same, via ncdata
    xr_ncdata_ds = to_xarray(ncdata)

    result = xr_ncdata_ds == xr_ds

    if not result:
        # FOR NOW: compare with experimental ncdata comparison.
        # I know this is a bit circular, but it is useful for debugging, for now ...
        result = compare_nc_datasets(
            from_xarray(xr_ds), from_xarray(xr_ncdata_ds)
        )
        assert result == []

    # assert xr_ds == xr_ncdata_ds
    assert result


def test_save_direct_vs_viancdata(standard_testcase, tmp_path):
    source_filepath = standard_testcase.filepath
    ncdata = from_nc4(source_filepath)

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
    results = compare_nc_datasets(temp_direct_savepath, temp_ncdata_savepath)
    assert results == []

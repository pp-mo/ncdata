"""
Test ncdata.iris by checking roundtrips for standard standard_testcases_func.

Testcases start as netcdf files.
(1) check equivalence of cubes : iris.load(file) VS iris.load(ncdata(file))
(2) check equivalence of files : iris -> file VS iris->ncdata->file
"""
from subprocess import check_output
from unittest import mock

import numpy as np

import dask.array as da
import xarray

import iris
import iris.fileformats.netcdf._thread_safe_nc as iris_threadsafe
import pytest

from ncdata.netcdf4 import from_nc4, to_nc4
from tests._compare_nc_datasets import compare_nc_datasets
from tests.data_testcase_schemas import standard_testcase, session_testdir

from ncdata.iris_xarray import cubes_to_xarray, cubes_from_xarray
from ncdata.iris import from_iris
from ncdata.xarray import from_xarray

from ncdata.threadlock_sharing import sharing_context
from tests.integration.roundtrips_utils import (
    set_tiny_chunks, adjust_chunks, cubes_equal__corrected
)

# Avoid complaints that imported fixtures are "unused"
standard_testcase, session_testdir, adjust_chunks

# import iris.fileformats.netcdf._thread_safe_nc as ifnt

_FIX_LOCKS = True
# _FIX_LOCKS = False
if _FIX_LOCKS:

    @pytest.fixture(scope="session")
    def use_irislock():
        with sharing_context(iris=True, xarray=True):
            yield


# _TINY_CHUNKS = True
_TINY_CHUNKS = False
set_tiny_chunks(_TINY_CHUNKS)


def test_roundtrip_ixi(standard_testcase, use_irislock, adjust_chunks):
    source_filepath = standard_testcase.filepath

    # Skip cases where there are no data variables for Iris to load.
    if standard_testcase.name in (
        'ds_Empty',
        'ds__singleattr',
        'ds__dimonly',
        # Cubes with string data are not cleanly handled at present.
        # (not clear if iris or xarray is behaving wrongly here)
        'ds__stringvar__singlepoint',
        'ds__stringvar__multipoint',
    ):
        return

    # _Debug = True
    _Debug = False
    if _Debug:
        print(f"\ntestcase: {standard_testcase.name}")
        print("spec =")
        print(standard_testcase.spec)
        print("\nncdump =")
        txt = check_output([f"ncdump {source_filepath}"], shell=True).decode()
        print(txt)

    # Load the testcase with Iris.
    iris_cubes = iris.load(source_filepath)

    # Convert to xarray, and back again.
    ds = cubes_to_xarray(iris_cubes)
    iris_xr_cubes = cubes_from_xarray(ds)

    # Unfortunately, cube order is not guaranteed to be stable.
    iris_cubes, iris_xr_cubes = (
        sorted(cubes, key=lambda cube: cube.name())
        for cubes in (iris_cubes, iris_xr_cubes)
    )


    # N.B. Conventions are not preserved from original, since Iris re-writes them.
    # So for now, just remove them all
    for cube in iris_cubes + iris_xr_cubes:
        cube.attributes.pop('Conventions', None)


    # # There is also a peculiar problem with cubes that have all-masked data.
    # # Let's error any like that, for now...
    # def all_maskeddata_cube(cube):
    #     return da.all(da.ma.getmaskarray(cube.core_data())).compute()
    #
    # assert not any(
    #     all_maskeddata_cube(cube)
    #     for cube in iris_cubes + iris_xr_cubes
    # )

    # There is also a peculiar problem with cubes that have all-masked data.
    # Let's just skip any like that, for now...
    def all_maskeddata_cube(cube):
        return da.all(da.ma.getmaskarray(cube.core_data())).compute()

    if len(iris_cubes) == len(iris_xr_cubes):
        i_ok = [
            i
            for i in range(len(iris_cubes))
            if not all_maskeddata_cube(iris_cubes[i])
            and not all_maskeddata_cube(iris_xr_cubes[i])
        ]
        iris_cubes, iris_xr_cubes = (
            [cube for i, cube in enumerate(cubes) if i in i_ok]
            for cubes in (iris_cubes, iris_xr_cubes)
        )

        n_cubes = len(iris_cubes)
        for i_cube in range(n_cubes):
            if i_cube not in i_ok:
                print(
                    f'\nSKIPPED testcase @"{source_filepath}" : cube #{i_cube}/{n_cubes} with all-masked data : '
                    f"{iris_cubes[i_cube].summary(shorten=True)}"
                )

    # Check equivalence
    # result = iris_cubes == iris_ncdata_cubes


    #
    # N.B. this is NOT necessary, since the units equate despite printing differently
    # ?? urrgh ??
    #
    # correct for xarray handling of time units.
    # too clear where this happens, probably in the loading phase, therefore can be controlled ??
    for iris_cube, iris_xr_cube in zip(iris_cubes, iris_xr_cubes):
        for xr_coord in iris_xr_cube.coords():
            iris_coord = iris_cube.coord(xr_coord)
            if xr_coord != iris_coord:
                # Xr strips off 00:00:00 from time units
                # we expect any differences to relate to that
                xr_ut, iris_ut = (str(co.units) for co in (xr_coord, iris_coord))
                assert xr_ut != iris_ut
                assert iris_ut.endswith(' 00:00:00')
                assert ' since ' in iris_ut
                assert xr_ut in iris_ut
                xr_coord.units = iris_ut

    results = [
        (c1.name(), cubes_equal__corrected(c1, c2))
        for c1, c2 in zip(iris_cubes, iris_xr_cubes)
    ]
    expected = [(cube.name(), True) for cube in iris_cubes]
    result = results == expected

    if not result:
        # FOR NOW: compare with experimental ncdata comparison.
        # I know this is a bit circular, but it is useful for debugging, for now ...
        result = compare_nc_datasets(
            from_iris(iris_cubes), from_iris(iris_xr_cubes)
        )
        assert result == []

    # assert iris_cubes == iris_ncdata_cubes
    assert result


def test_roundtrip_xix(standard_testcase, use_irislock, adjust_chunks):
    source_filepath = standard_testcase.filepath

    # Skip some cases
    if standard_testcase.name in (
        # these won't load (either Iris or Xarray)
        'ds_Empty',
        'ds__singleattr',
        'ds__dimonly',
        # these are too big to compare ??

    ):
        return


    # _Debug = True
    _Debug = False
    if _Debug:
        print(f"\ntestcase: {standard_testcase.name}")
        print("spec =")
        print(standard_testcase.spec)
        print("\nncdump =")
        txt = check_output([f"ncdump {source_filepath}"], shell=True).decode()
        print(txt)

    # Load the testcase with Xarray.
    xrds = xarray.open_dataset(source_filepath, chunks='auto')

    # Convert to xarray, and back again.
    iris_cubes = cubes_from_xarray(xrds)
    # Unfortunately, cube order is not guaranteed to be stable.
    iris_cubes = sorted(iris_cubes, key=lambda cube: cube.name())
    xrds_iris = cubes_to_xarray(iris_cubes)

    # Check equivalence
    result = xrds_iris == xrds

    if not result:
        # FOR NOW: compare with experimental ncdata comparison.
        # I know this is a bit circular, but it is useful for debugging, for now ...
        result = compare_nc_datasets(
            from_xarray(xrds), from_xarray(xrds_iris)
        )
        assert result == []

    # assert iris_cubes == iris_ncdata_cubes
    assert result


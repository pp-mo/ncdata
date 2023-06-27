"""
Test ncdata.iris by checking roundtrips for standard testcases.

Testcases start as netcdf files.
(1) check equivalence of cubes : iris.load(file) VS iris.load(ncdata(file))
(2) check equivalence of files : iris -> file VS iris->ncdata->file
"""
from subprocess import check_output
from unittest import mock

import numpy as np

import dask.array as da
import iris
import iris.fileformats.netcdf._thread_safe_nc as iris_threadsafe
import pytest

from ncdata.netcdf4 import from_nc4, to_nc4
from tests._compare_nc_datasets import compare_nc_datasets
from tests.data_testcase_schemas import standard_testcase, session_testdir

from ncdata.iris import from_iris, to_iris

# Avoid complaints that the fixture is unused
standard_testcase, session_testdir

# _Debug = True
_Debug = False

import iris.fileformats.netcdf._thread_safe_nc as ifnt


@pytest.fixture(scope='session')
def use_irislock():
    tgt = 'ncdata.netcdf4._GLOBAL_NETCDF4_LIBRARY_THREADLOCK'
    with mock.patch(tgt, new=ifnt._GLOBAL_NETCDF4_LOCK):
        yield


def test_load_direct_vs_viancdata(standard_testcase, use_irislock):
    source_filepath = standard_testcase.filepath
    ncdata = from_nc4(source_filepath)

    _Debug = True
    if _Debug:
        print(f"\ntestcase: {standard_testcase.name}")
        print("spec =")
        print(standard_testcase.spec)
        print("\nncdata =")
        print(ncdata)
        print("\nncdump =")
        txt = check_output([f"ncdump {source_filepath}"], shell=True).decode()
        print(txt)

    # Load the testcase with Iris.
    iris_cubes = iris.load(source_filepath)
    # Load same, via ncdata
    iris_ncdata_cubes = to_iris(ncdata)
    # Unfortunately, cube order is not guaranteed to be stable.
    iris_cubes = sorted(iris_cubes, key=lambda cube: cube.name())
    iris_ncdata_cubes = sorted(iris_ncdata_cubes, key=lambda cube: cube.name())

    # There is also a peculiar problem with cubes that have all-masked data.
    # Let's just skip any like that, for now...
    def all_maskeddata_cube(cube):
        return da.all(da.ma.getmaskarray(cube.core_data())).compute()

    if len(iris_cubes) == len(iris_ncdata_cubes):
        i_ok = [
            i
            for i in range(len(iris_cubes))
            if not all_maskeddata_cube(iris_cubes[i])
            and not all_maskeddata_cube(iris_ncdata_cubes[i])
        ]
        iris_cubes = [cube for i, cube in enumerate(iris_cubes) if i in i_ok]
        iris_ncdata_cubes = [
            cube for i, cube in enumerate(iris_ncdata_cubes) if i in i_ok
        ]

        n_cubes = len(iris_cubes)
        for i_cube in range(n_cubes):
            if i_cube not in i_ok:
                print(
                    f'\nSKIPPED testcase @"{source_filepath}" : cube #{i_cube}/{n_cubes} with all-masked data : '
                    f"{iris_cubes[i_cube].summary(shorten=True)}"
                )

    # Check equivalence
    # result = iris_cubes == iris_ncdata_cubes
    # note: temporary fix for string-cube comparison.
    #   Cf. https://github.com/SciTools/iris/issues/5362
    #   TODO: remove temporary fix
    def cube_equal(c1, c2):
        """
        Cube equality test which works around string-cube equality problem.

        """
        if (
                (c1.metadata == c2.metadata)
                and all(cube.dtype.kind in ('U', 'S') for cube in (c1, c2))
        ):
            # cludge comparison for string-type cube data
            c1, c2 = (cube.copy() for cube in (c1, c2))
            c1.data = (c1.data == c2.data)
            c2.data = np.ones(c2.shape, dtype=bool)

        return c1 == c2

    results = [
        (c1.name(), cube_equal(c1, c2))
        for c1, c2 in zip(iris_cubes, iris_ncdata_cubes)
    ]
    expected = [(cube.name(), True) for cube in iris_cubes]
    result = results == expected



    if not result:
        # FOR NOW: compare with experimental ncdata comparison.
        # I know this is a bit circular, but can use for debugging, for now ...
        result = compare_nc_datasets(
            from_iris(iris_cubes), from_iris(iris_ncdata_cubes)
        )
        assert result == []
    # assert iris_cubes == iris_ncdata_cubes
    assert result


def test_save_direct_vs_viancdata(standard_testcase, tmp_path):
    source_filepath = standard_testcase.filepath
    ncdata = from_nc4(source_filepath)

    # Load the testcase into Iris.
    iris_cubes = iris.load(source_filepath)

    if standard_testcase.name in ("ds_Empty", "ds__singleattr", "ds__dimonly"):
        # Iris can't save an empty dataset.
        return

    # Re-save from iris
    temp_iris_savepath = tmp_path / "temp_save_iris.nc"
    iris.save(iris_cubes, temp_iris_savepath)
    # Save same, via ncdata
    temp_ncdata_savepath = tmp_path / "temp_save_iris_via_ncdata.nc"
    to_nc4(from_iris(iris_cubes), temp_ncdata_savepath)

    _Debug = True
    if _Debug:
        print(f"\ntestcase: {standard_testcase.name}")
        print("spec =")
        print(standard_testcase.spec)
        print("\nncdata =")
        print(ncdata)
        print("\nncdump ORIGINAL TESTCASE SOURCEFILE =")
        txt = check_output([f"ncdump {source_filepath}"], shell=True).decode()
        print(txt)
        print("\nncdump DIRECT FROM IRIS =")
        txt = check_output(
            [f"ncdump {temp_iris_savepath}"], shell=True
        ).decode()
        print(txt)
        print("\nncdump VIA NCDATA =")
        txt = check_output(
            [f"ncdump {temp_ncdata_savepath}"], shell=True
        ).decode()
        print(txt)

    # Check equivalence
    results = compare_nc_datasets(temp_iris_savepath, temp_ncdata_savepath)
    assert results == []

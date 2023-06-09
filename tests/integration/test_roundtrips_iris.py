"""
Test ncdata.iris by checking roundtrips for standard testcases.

Testcases start as netcdf files.
(1) check equivalence of cubes : iris.load(file) VS iris.load(ncdata(file))
(2) check equivalence of files : iris -> file VS iris->ncdata->file
"""
import pytest
from subprocess import check_output

import iris

from ncdata.netcdf4 import from_nc4, to_nc4
from tests._compare_nc_datasets import compare_nc_datasets
from tests.data_testcase_schemas import standard_testcase, session_testdir

from ncdata.iris import from_iris, to_iris

# Avoid complaints that the fixture is unused
standard_testcase, session_testdir

_Debug = True
# _Debug = False


def test_load_direct_vs_viancdata(standard_testcase, tmp_path):
    source_filepath = standard_testcase.filepath
    ncdata = from_nc4(source_filepath)

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
    # Check equivalence
    assert iris_cubes == iris_ncdata_cubes


def test_save_direct_vs_viancdata(standard_testcase, tmp_path):
    source_filepath = standard_testcase.filepath
    ncdata = from_nc4(source_filepath)

    # Load the testcase into Iris.
    iris_cubes = iris.load(source_filepath)

    if standard_testcase.name == "ds_Empty":
        # Iris can't save an empty dataset.
        return

    # Re-save from iris
    temp_iris_savepath = tmp_path / "temp_save_iris.nc"
    iris.save(iris_cubes, temp_iris_savepath)
    # Save same, via ncdata
    temp_ncdata_savepath = tmp_path / "temp_save_iris_via_ncdata.nc"
    to_nc4(from_iris(iris_cubes), temp_ncdata_savepath)

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

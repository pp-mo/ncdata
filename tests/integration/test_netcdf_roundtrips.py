"""
Test ncdata.netcdf by checking load-save roundtrips for standard testcases.
"""
from subprocess import check_output

from ncdata.netcdf4 import from_nc4, to_nc4
from tests._compare_nc_datasets import compare_nc_datasets
from tests.data_testcase_schemas import session_testdir, standard_testcase

# Avoid complaints that the imported fixtures are "unused"
standard_testcase, session_testdir

# _Debug = True
_Debug = False


def test_basic(standard_testcase, tmp_path):
    source_filepath = standard_testcase.filepath
    intermediate_filepath = tmp_path / "temp_saved.nc"

    # Load the testfile.
    ncdata = from_nc4(source_filepath)
    # Re-save
    to_nc4(ncdata, intermediate_filepath)

    # _Debug = True
    _Debug = False
    if _Debug:
        print(f"\ntestcase: {standard_testcase.name}")
        print("spec =")
        print(standard_testcase.spec)
        print("\nncdata =")
        print(ncdata)
        print("\nncdump =")
        txt = check_output(
            [f"ncdump {intermediate_filepath}"], shell=True
        ).decode()
        print(txt)

    # Check that the re-saved file matches the original
    results = compare_nc_datasets(source_filepath, intermediate_filepath)
    assert results == []

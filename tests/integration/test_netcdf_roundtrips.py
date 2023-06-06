from pathlib import Path

from ncdata.netcdf4 import from_nc4, to_nc4
from tests._compare_nc_datasets import compare_nc_datasets
from tests.data_testcase_schemas import (
    _simple_test_spec,
    make_testcase_dataset,
)


def test_basic(tmp_path_factory):
    tmpdir_path = Path(tmp_path_factory.mktemp("nc_roundtrips"))
    testcase_filepath = tmpdir_path / "test_basic.nc"
    roundtrip_filepath = tmpdir_path / "test_basic_resaved.nc"
    make_testcase_dataset(testcase_filepath, _simple_test_spec)

    ncdata = from_nc4(testcase_filepath)
    to_nc4(ncdata, roundtrip_filepath)

    results = compare_nc_datasets(testcase_filepath, roundtrip_filepath)
    assert results == []

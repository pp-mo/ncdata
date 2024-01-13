from ncdata import NcData, NcVariable
from pathlib import Path

import netCDF4 as nc
import numpy as np
import pytest

_targettype_opts = ['str', 'path', 'file']

from tests.data_testcase_schemas import make_testcase_dataset
from tests._compare_nc_datasets import compare_nc_datasets

from ncdata.netcdf4 import from_nc4, to_nc4


@pytest.fixture()
def minimal_testfile_and_data(tmp_path):
    _minimal_test_spec = {
        "vars": [dict(name="x", dims=[], dtype=np.float32, data=[1.23])]
    }
    original_path = tmp_path / 'tmp_testcase.nc'
    make_testcase_dataset(original_path, _minimal_test_spec)
    ncdata = from_nc4(original_path)
    yield original_path, ncdata


@pytest.mark.parametrize('targettype', _targettype_opts)
def test_target_types(targettype, minimal_testfile_and_data, tmp_path):
    original_path, ncdata = minimal_testfile_and_data
    target_path = tmp_path / "tmp_output.nc"
    if targettype == "path":
        target = target_path
    elif targettype == 'str':
        target = str(target_path)
    elif targettype == 'file':
        target = nc.Dataset(target_path, 'w')
    else:
        raise ValueError(
            f"unexpected test param : {targettype} not in {_targettype_opts}"
        )

    to_nc4(ncdata, target)
    if targettype == 'file':
        target.close()

    assert target_path.exists()
    assert compare_nc_datasets(target_path, original_path) == []

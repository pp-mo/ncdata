import pytest

from tests.data_testcase_schemas import data_types

data_types  # avoid 'unused' warning


@pytest.fixture(params=[])
def context(request):
    return request.param

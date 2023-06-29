import numpy as np
import pytest


def cubes_equal__corrected(c1, c2):
    """
    A special cube equality test which works around a string-cube equality problem.

    Note: because string-cube comparison is currently "broken".
    Cf. https://github.com/SciTools/iris/issues/5362
    TODO: remove when fixed, replace usages with simple c1==c2

    If cubes contain string (char) data, replace them with booleans which duplicate
    the correct pointwise equivalence.
    I.E. c1.data == c2.data produces the result it "should have done".

    """
    if (
            (c1.metadata == c2.metadata)
            and (c1.shape == c2.shape)
            and all(cube.dtype.kind in ("U", "S") for cube in (c1, c2))
    ):
        # cludge comparison for string-type cube data
        c1, c2 = (cube.copy() for cube in (c1, c2))
        c1.data = c1.data == c2.data
        c2.data = np.ones(c2.shape, dtype=bool)

    return c1 == c2


_USE_TINY_CHUNKS = False
# Note: from experiment, the test most likely to fail due to thread-safety is
#   "test_load_direct_vs_viancdata[testdata____testing__small_theta_colpex]"
# Resulting errors vary widely, including netcdf/HDF errors, data mismatches and
# segfaults.
# The following _CHUNKSIZE_SPEC makes it fail ~70% of runs of
# "tests/integration/test_roundtrips_iris.py::test_load_direct_vs_viancdata"
# HOWEVER, the overall test runs get a LOT slower (e.g. 110sec --> )
_CHUNKSIZE_SPEC = "20Kib"


def set_tiny_chunks(on, size_spec="20Kib"):
    """Turn on and off the tiny-chunks effect of the 'adjust_chunks' fixture."""
    global _USE_TINY_CHUNKS, _CHUNKSIZE_SPEC
    _CHUNKSIZE_SPEC = size_spec
    _USE_TINY_CHUNKS = on


# this fixture can be referenced by anything, and will make all chunks small for that
# item, if enabled via the global setting.
@pytest.fixture
def adjust_chunks():
    import dask.config as dcfg
    global _USE_TINY_CHUNKS, _CHUNKSIZE_SPEC
    if _USE_TINY_CHUNKS:
        with dcfg.set({"array.chunk-size": _CHUNKSIZE_SPEC}):
            yield
    else:
        yield

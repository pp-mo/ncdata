"""Tests for :func:`ncdata.utils.rename_dimension`."""
import pytest

from ncdata import NcData, NcDimension, NcVariable
from ncdata.utils import rename_dimension


class TestRenameDimension:
    """Tests for :func:`ncdata.utils.rename_dimension`."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.ncdata = NcData(
            dimensions=[
                NcDimension("y", 2),
                NcDimension("x", 3),
            ],
            variables=[
                NcVariable("vx", ["x"]),
                NcVariable("vy", ["y"]),
                NcVariable("vyx", ["y", "x"]),
            ],
        )

    def test_basic(self):
        ncdata = self.ncdata
        xdim = ncdata.dimensions["x"]
        rename_dimension(ncdata, "x", "zz")
        assert ncdata.dimensions["zz"] is xdim
        assert ncdata.variables["vx"].dimensions == ("zz",)
        assert ncdata.variables["vy"].dimensions == ("y",)
        assert ncdata.variables["vyx"].dimensions == ("y", "zz")

    def test_name_collision_fail(self):
        ncdata = self.ncdata
        msg = "Cannot rename dimension 'x' to 'y' .* already exists."
        with pytest.raises(ValueError, match=msg):
            rename_dimension(ncdata, "x", "y")

    def test_groups(self):
        ncdata = self.ncdata
        ncdata.groups.addall(
            [
                NcData(
                    "a",
                    variables=[
                        NcVariable("ax", ["x"]),
                        NcVariable("aqxr", ["q", "x", "r"]),
                    ],
                ),
                NcData(
                    "b",
                    dimensions=[NcDimension("x", 20)],
                    variables=[NcVariable("bx", ["x"])],
                ),
            ]
        )
        rename_dimension(ncdata, "x", "zz")
        assert ncdata.groups["a"].variables["ax"].dimensions == ("zz",)
        assert ncdata.groups["a"].variables["aqxr"].dimensions == (
            "q",
            "zz",
            "r",
        )
        # This one doesn't get renamed: it is in a "scope hole" because the group
        #  defines its own "x" dimension, which takes precedence.
        assert ncdata.groups["b"].variables["bx"].dimensions == ("x",)

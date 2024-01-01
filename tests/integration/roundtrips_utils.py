import dask.array as da
import numpy as np
import pytest


def cubes_equal__corrected(c1, c2):
    """
    A special cube equality test which works around some equality problems.

    (1) If cubes contain string (char) data, replace them with booleans which duplicate
    the correct pointwise equivalence.
    I.E. c1.data == c2.data produces the result it "should have done".

    Note: because string-cube comparison is currently "broken".
    Cf. https://github.com/SciTools/iris/issues/5362
    TODO: remove when fixed, replace usages with simple c1==c2

    Note: this only applies to CUBE data, coords are ok.

    (2) If two cube have data arrays which are all-masked, comparison returns 'masked'
    instead of True (which would be more useful for our purpose.
    Note: this problem also applies to COORDINATES - both points and bounds arrays.

    (3) arrange that arrays with matching NaNs compare equal.

    """
    if c1.shape != c2.shape:
        # This shortcuts us out of a problem whereby cubes with string-type data don't
        # compare correctly EVEN to just fail when shapes differ.  Weird ?!?!
        return False

    if (c1.metadata == c2.metadata) and (c1.shape == c2.shape):
        # Only bother adjusting data/coords equality if cube comparison gets that far.
        # Copy original cubes so we can safely modify them in-place.
        c1, c2 = (cube.copy() for cube in (c1, c2))
        if all(cube.dtype.kind in ("U", "S") for cube in (c1, c2)):
            # Correct comparison of string-type cube data arrays.
            # NOTE: this problem does NOT apply to coordinates.
            c1.data = c1.data == c2.data
            c2.data = np.ones(c2.shape, dtype=bool)
        else:
            # Correct comparison of all-masked arrays, and arrays with NaNs.
            # NOTE: this problem DOES apply to coordinate data also.
            def fix_arrays(a1, a2):
                """
                Check if 2 arrays are both all-masked, and if so replace them.

                Return either the original arrays, or arrays of the same shape which
                reproduce the correct result : np.all(all-masked==all-masked) --> True.

                ALSO replace *matching* NaN points with safe values (zeros).
                """
                if a1 is not None and a2 is not None:
                    allmasked_1, allmasked_2 = (
                        da.all(da.ma.getmaskarray(arr).compute())
                        for arr in (a1, a2)
                    )
                    if allmasked_1 and allmasked_2:
                        # IN this case == will return 'masked', but for our purposes should be
                        # considered equal, i.e. 'True'
                        a1 = np.zeros(a1.shape, dtype=bool)
                        a2 = a1

                    # replace *matching* NaN points with zeros.
                    if a1.dtype.kind == "f" and a2.dtype.kind == "f":
                        bothnan = np.isnan(a1) & np.isnan(a2)
                        if np.any(bothnan):
                            # N.B. must make copies here, to ensure writeability
                            a1, a2 = a1[:], a2[:]
                            a1[bothnan] = 0
                            a2[bothnan] = 0

                return a1, a2

            # Fix matching of cube data arrays
            c1.data, c2.data = fix_arrays(
                *(cube.core_data() for cube in (c1, c2))
            )
            # Fix matching of all coords points + bounds
            for co1, co2 in zip(c1.coords(), c2.coords()):
                co1.points, co2.points = fix_arrays(
                    *(co.core_points() for co in (co1, co2))
                )
            for co1, co2 in zip(c1.coords(), c2.coords()):
                co1.bounds, co2.bounds = fix_arrays(
                    *(co.core_bounds() for co in (co1, co2))
                )

    return c1 == c2


_USE_TINY_CHUNKS = False
# Note: from experiment, the test most likely to fail due to thread-safety is
#   "test_load_direct_vs_viancdata[testdata____testing__small_theta_colpex]"
# Resulting errors vary widely, including netcdf/HDF errors, data mismatches and
# segfaults.
# The following _CHUNKSIZE_SPEC makes it fail ~70% of runs of
# "tests/integration/test_roundtrips_iris.py::test_load_direct_vs_viancdata"
# HOWEVER, the overall test runs get a LOT slower (e.g. 12sec --> 42sec )
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


#
# Specifically process all cube and coord data arrays to replace all NaN values
# with masked points.  This is highly inefficient, but it works as a first stab.
#
def nanmask_array(array):
    """
    Produce a replacement array with any NaNs masked.

    Convert array to masked, if not already, and mask any NaN values.
    Supports either Dask or Numpy arrays.
    """
    if array is not None and array.dtype.kind not in ("S", "U", "b"):
        # N.B. no NaNs in string data (!)
        # nans processing doesn't handle scalars properly, so ensure ndims>=1
        orig_shape = array.shape
        if array.ndim < 1:
            array = array.reshape((1,))
        nans = da.isnan(array)
        if da.any(nans.flatten()).compute():
            # Replace by a definitively masked version, with NaNs also masked
            mask = da.ma.getmaskarray(array) | nans
            array = da.asarray(array)
            array = da.ma.masked_array(array, mask=mask)
            array = array.reshape(orig_shape)
    return array


def nanmask_cube(cube):
    cube.data = nanmask_array(cube.core_data())
    for coord in cube.coords():
        coord.points = nanmask_array(coord.core_points())
        coord.bounds = nanmask_array(coord.core_bounds())
    return cube


#
# Horrible code to list the properties of a netCDF4.Variable object
#
import inspect
from pathlib import Path
import tempfile
import shutil
import netCDF4 as nc

dirpath = Path(tempfile.mkdtemp())
try:
    ds = nc.Dataset(dirpath / "tmp.nc", "w")
    v = ds.createVariable("x", int, ())
    _NCVAR_PROPERTY_NAMES = [
        nn[0] for nn in inspect.getmembers(v) if not nn[0].startswith("_")
    ]
    # print('\n'.join(_NCVAR_PROPERTY_NAMES))
    ds.close()
finally:
    shutil.rmtree(dirpath)


def prune_attrs_varproperties(attrs):
    names = set()
    for propname in _NCVAR_PROPERTY_NAMES:
        if propname in attrs:
            names.add(propname)
            attrs.pop(propname, None)
    return names


def prune_cube_varproperties(cube_or_cubes):
    if hasattr(cube_or_cubes, "add_aux_coord"):
        cube_or_cubes = [cube_or_cubes]

    names = set()
    for cube in cube_or_cubes:
        components = (
            [cube]
            + list(cube.coords())
            + list(cube.cell_measures())
            + list(cube.ancillary_variables())
        )
        for comp in components:
            names |= prune_attrs_varproperties(comp.attributes)

    return names


#
# Remove any "no-units" units, as these are not SAVED correctly.
# (see
#
import cf_units


def remove_element_nounits(obj):
    if obj.units == cf_units._NO_UNIT_STRING:
        obj.units = None


def remove_cube_nounits(cube_or_cubes):
    if hasattr(cube_or_cubes, "add_aux_coord"):
        cube_or_cubes = [cube_or_cubes]

    for cube in cube_or_cubes:
        components = (
            [cube]
            + list(cube.coords())
            + list(cube.cell_measures())
            + list(cube.ancillary_variables())
        )
        for comp in components:
            remove_element_nounits(comp)


#
# Make a safe repeatable ordering of cubes.
#
def _cube_metadata_key(cube):
    return (cube.name(), cube.long_name, cube.var_name)


def namesort_cubes(cubes):
    return sorted(cubes, key=_cube_metadata_key)

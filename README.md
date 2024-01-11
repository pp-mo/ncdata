# ncdata
Generic NetCDF data in Python.

Provides fast data exchange between analysis packages, and full control of storage
formatting.

Especially : Ncdata **exchanges data between Xarray and Iris** as efficently as possible  
> "lossless, copy-free and lazy-preserving".

This enables the user to freely mix+match operations from both projects, getting the
"best of both worlds".

## Contents
  * [Motivation](#motivation)
    * [Primary Use](#primary-use)
    * [Secondary Uses](#secondary-uses)
  * [Principles](#principles)
  * [Working Usage Examples](#code-examples) 
  * [API documentation](#api-documentation)
  * [Installation](#installation)
  * [Project Status](#project-status)
    * [Code stability](#code-stability)
    * [Iris and Xarray version compatibility](#iris-and-xarray-compatibility)
    * [Current Limitations](#known-limitations)
  * [References](#references)
  * [Developer Notes](#developer-notes)

# Motivation
## Primary Use
Fast and efficient translation of data between Xarray and Iris objects.

This allows the user to mix+match features from either package in code. 

For example:
``` python
from ncdata.iris_xarray import cubes_to_xarray, cubes_from_xarray

# Apply Iris regridder to xarray data
dataset = xarray.open_dataset('file1.nc', chunks='auto')
cube, = cubes_from_xarray(dataset)
cube2 = cube.regrid(grid_cube, iris.analysis.PointInCell)
dataset2 = cubes_to_xarray(cube2)

# Apply Xarray statistic to Iris data
cubes = iris.load('file1.nc')
dataset = cubes_to_xarray(cubes)
dataset2 = dataset.group_by('time.dayofyear').argmin()
cubes2 = cubes_from_xarray(dataset2)
``` 
  * data conversion is equivalent to writing to a file with one library, and reading it
    back with the other ..
    * .. except that no actual files are written
  * both real (numpy) and lazy (dask) variable data arrays are transferred directly, 
    without copying or computing


## Secondary Uses
### Exact control of file formatting
Ncdata can also be used as a transfer layer between Iris or Xarray file i/o and the
exact format of data stored in files.  
I.E. adjustments can be made to file data before loading it into Iris/Xarray; or
Iris/Xarray saved output can be adjusted before writing to a file.

This allows the user to workaround any package limitations in controlling storage
aspects such as : data chunking; reserved attributes; missing-value processing; or 
dimension control.

For example:
``` python
from ncdata.xarray import from_xarray
from ncdata.iris import to_iris
from ncdata.netcdf4 import to_nc4, from_nc4

# Rename a dimension in xarray output
dataset = xr.open_dataset('file1.nc')
xr_ncdata = from_xarray(dataset)
dim = xr_ncdata.dimensions.pop('dim0')
dim.name = 'newdim'
xr_ncdata.dimensions['newdim'] = dim
for var in xr_ncdata.variables.values():
    var.dimensions = [
        'newdim' if dim == 'dim0' else dim
        for dim in var.dimensions
    ]
to_nc4(ncdata, 'file_2a.nc')

# Fix chunking in Iris input
ncdata = from_nc4('file1.nc')
for var in ncdata.variables:
    # custom chunking() mimics the file chunks we want
    var.chunking = lambda: (
        100.e6 if dim == 'dim0' else -1
        for dim in var.dimensions
    )
cubes = to_iris(ncdata)
``` 

### Manipulation of data
ncdata can also be used for data extraction and modification, similar to the scope of
CDO and NCO command-line operators but without file operations.  
However, this type of usage is as yet still undeveloped :  There is no inbuilt support
for data consistency checking, or obviously useful operations such as indexing by
dimension. 
This could be added in future, but it is also true that many such operations (like
indexing) may be better done using Iris/Xarray.


# Principles
  * ncdata represents NetCDF data as Python objects
  * ncdata objects can be freely manipulated, independent of any data file
  * ncdata variables can contain either real (numpy) or lazy (Dask) arrays
  * ncdata can be losslessly converted to and from actual NetCDF files
  * Iris or Xarray objects can be converted to and from ncdata, in the same way that 
    they are read from and saved to NetCDF files
  * **_translation_** between Xarray and Iris is based on conversion to ncdata, which
    is in turn equivalent to file i/o
     * thus, Iris/Xarray translation is equivalent to _saving_ from one
       package into a file, then _loading_ the file in the other package
  * ncdata exchanges variable data directly with Iris/Xarray, with no copying of real
    data or computing of lazy data
  * ncdata exchanges lazy arrays with files using Dask 'streaming', thus allowing
    transfer of arrays larger than memory  


# Code Examples
  * mostly TBD
  * proof-of-concept script for
    [netCDF4 file i/o](https://github.com/pp-mo/ncdata/blob/main/tests/integration/example_scripts/ex_ncdata_netcdf_conversion.py)
  * proof-of-concept script for
    [iris-xarray conversions](https://github.com/pp-mo/ncdata/blob/main/tests/integration/example_scripts/ex_iris_xarray_conversion.py)    


# API documentation
  * see the [ReadTheDocs build](https://ncdata.readthedocs.io/en/latest/index.html)


# Installation
Install from conda-forge with conda
```
conda install ncdata
```

Or from PyPI with pip
```
pip install ncdata
```

# Project Status
## Code Stability
We intend to follow [PEP 440](https://peps.python.org/pep-0440/) or (older) [SemVer](https://semver.org/) versioning principles.

Release version is at **"v0.0.1"**.  
This is a first complete implementation, with functional operational of all public APIs.  
A **release "v0.1.0"** will follow when build and deployment mechanisms are sorted out.  
The code is however still experimental, and APIs are not stable (hence no major version yet).  

## Iris and Xarray Compatibility
* C.I. tests GitHub PRs and merges, against latest releases of Iris and Xarray
* compatible with iris >= v3.7.0
  * see : [support added in v3.7.0](https://scitools-iris.readthedocs.io/en/stable/whatsnew/3.7.html#internal)

## Known limitations
Unsupported features : _not planned_ 
 * user-defined datatypes are not supported
   * this includes compound and variable-length types

Unsupported features : _planned for future release_ 
 * groups (not yet fully supported ?)
 * file output chunking control

Untested features : _probably done, pending test_
 * unlimited dimensions (not yet fully supported)
 * file compression and encoding options
 * iris and xarray load/save keywords generally

# References
  * Iris issue : https://github.com/SciTools/iris/issues/4994
  * planning presentation : https://github.com/SciTools/iris/files/10499677/Xarray-Iris.bridge.proposal.--.NcData.pdf
  * in-Iris code workings : https://github.com/pp-mo/iris/pull/75


# Developer Notes
## Documentation build
  * For a full docs-build, a simple `make html` will do for now.  
    * The ``docs/Makefile`` wipes the API docs and invokes sphinx-apidoc for a full rebuild
    * Results are then available at ``docs/_build/html/index.html``
  * The above is just for _local testing_ if required :
    We have automatic builds for releases and PRs via [ReadTheDocs](https://readthedocs.org/projects/ncdata/) 

## Release actions
   1. Cut a release on GitHub : this triggers a new docs version on [ReadTheDocs](https://readthedocs.org/projects/ncdata/) 
   1. Build the distribution
      1. if needed, get [build](https://github.com/pypa/build)
      2. run `python -m build`
   2. Push to PyPI
      1. if needed, get [twine](https://github.com/pypa/twine)
      2. run `python -m twine --repository testpypi upload dist/*`
         * this uploads to TestPyPI
      3. if that checks OK, _remove_ `--repository testpypi` _and repeat_
         * --> uploads to "real" PyPI
      4. check that `pip install ncdata` can now find the new version
   3. Update conda to source the new version from PyPI
      1. create a PR on the [ncdata feedstock](https://github.com/conda-forge/ncdata-feedstock)
      1. update :
         * [version number](https://github.com/conda-forge/ncdata-feedstock/blob/3f6b35cbdffd2ee894821500f76f2b0b66f55939/recipe/meta.yaml#L2) 
         * [SHA](https://github.com/conda-forge/ncdata-feedstock/blob/3f6b35cbdffd2ee894821500f76f2b0b66f55939/recipe/meta.yaml#L10)
         * Note : the [PyPI reference](https://github.com/conda-forge/ncdata-feedstock/blob/3f6b35cbdffd2ee894821500f76f2b0b66f55939/recipe/meta.yaml#L9) will normally look after itself
         * Also : make any required changes to [dependencies](https://github.com/conda-forge/ncdata-feedstock/blob/3f6b35cbdffd2ee894821500f76f2b0b66f55939/recipe/meta.yaml#L17-L29) -- normally _no change required_
      1. get PR merged ; wait a few hours ; check the new version appears in `conda search ncdata`

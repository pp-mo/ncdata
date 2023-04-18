# ncdata
NetCDF data interoperability between Iris and Xarray.

Ncdata exchanges data between Xarray and Iris as efficently as possible  
> "lossless, copy-free and lazy-preserving".

This enables the user to freely mix+match operations from both projects, getting the
"best of both worlds".

## Contents
  * [Motivation](#motivation)
    * [Primary Use](#primary-use)
    * [Secondary Uses](#secondary-uses)
  * [Working Examples](#code-examples) 
  * [Project Status](#status)
    * [Code stability](#code-stability)
    * [Iris and Xarray version compatibility](#iris-and-xarray-compatibility)
    * [Current Limitations](#known-limitations)
  * [Principles](#principles)
  * [References](#references)
  * [Developer Notes](#developer-notes)

# Motivation
## Primary Use
Fast and efficient translation of data between Xarray and Iris objects.

This allows the user to mix+match features from either package in code. 

For example:
``` python
from ncdata.iris_xarray import dataset_to_cubes, cubes_to_dataset

# Apply Iris regridder to xarray data
dataset = xarray.open_dataset('file1.nc')
cube, = dataset_to_cubes(dataset)
cube2 = cube.regrid(grid_cube, iris.analysis.PointInCell)
dataset2 = cubes_to_dataset(cube2)

# Apply Xarray statistic to Iris data
cubes = iris.load('file1.nc')
dataset = cubes_to_dataset(cubes)
dataset2 = dataset.group_by('time.dayofyear').argmin()
cubes2 = dataset_to_cubes(dataset2)
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
from ncdata.iris import to_cubes
from ncdata.netcdf4 import to_nc4, from_nc4

# Rename a dimension in xarray output
dataset = xr.open_dataset('file1.nc')
xr_ncdata = from_xarray(dataset)
dim = xr_ncdata.dimensions.pop('dim0')
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
    var.chunking = lambda: (
        100.e6 if dim == 'dim0' else -1
        for dim in var.dimensions
    )
cubes = to_cubes(ncdata)
``` 

### Manipulation of data
ncdata can also be used for data extraction and modification, similar to the scope of
CDO and NCO command-line operators but without file operations.  
However, this type of usage is as yet still undeveloped :  There is no inbuilt support
for data consistency checking, or obviously useful operations such as dimension
indexing.  
This could be added in future, but it is also true that many such operations (like
indexing) may be better done using Iris/Xarray.


# Code Examples
  * mostly TBD
  * proof-of-concept script for
    [netCDF4 file i/o](https://github.com/pp-mo/ncdata/blob/main/lib/tests/integration/nc4_interface_exercise.py)
  * proof-of-concept script for
    [iris-xarray conversions](https://github.com/pp-mo/ncdata/blob/main/lib/tests/integration/ncdata_exercise.py)    

# Status
## Code Stability

Code here is all still experimental.   
Current APIs are unsupported and not stable.  
There is no release yet.

## Iris and Xarray Compatibility
### Iris
  * **currently** functions with a test branch of Iris
    * branch in pp-mo fork : https://github.com/pp-mo/iris/tree/bridge_support , *or*
    * this PR in main Iris repo : https://github.com/SciTools/iris/pull/5216
  * **in future** the necessary changes should be included and released with
    [Iris 3.6](https://github.com/orgs/SciTools/projects/11).
### Xarray
  * appears working against 'current' Xarray at time of writing
    * [v2023.03.0 (March 22, 2023)](https://docs.xarray.dev/en/latest/whats-new.html#v2023-03-0-march-22-2023)

## Known limitations
Unsupported features : not planned 
 * user-defined datatypes are not supported
   * this includes compound and variable-length types

Unsupported features : planned for future release 
 * groups (not yet fully supported)
 * unlimited dimensions (not yet fully supported)
 * file compression and encoding options
 * file output chunking control

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

# References
  * Iris issue : https://github.com/SciTools/iris/issues/4994
  * planning presentation : https://github.com/SciTools/iris/files/10499677/Xarray-Iris.bridge.proposal.--.NcData.pdf
  * in-Iris code workings : https://github.com/pp-mo/iris/pull/75


# Developer Notes
  * for a full docs-build, a simple `make html` will do for now.  
    * the ``docs/Makefile`` wipes the API docs and invokes sphinx-apidoc for a full rebuild
    * results are then available at ``docs/_build/html/index.html``

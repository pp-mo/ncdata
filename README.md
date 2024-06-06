# ncdata

<img src="docs/_static/ncdata_logo_full.png" alt="ncdata logo" width="400" class="center">

Generic NetCDF data in Python.

Provides fast data exchange between analysis packages, and full control of storage
formatting.

Especially : Ncdata **exchanges data between Xarray and Iris** as efficiently as possible  
> "lossless, copy-free and lazy-preserving".

This enables the user to freely mix+match operations from both projects, getting the
"best of both worlds".
  > import xarray  
  > import ncdata.iris_xarray as nci  
  > import iris.quickplot as qplt  
  >   
  > ds = xarray.open_dataset(filepath)  
  > ds_resample = ds.rolling(time=3).mean()  
  > cubes = nci.cubes_from_xarray(ds_resample)  
  > temp_cube = cubes.extract_cube("air_temperature")  
  > qplt.contourf(temp_cube[0])

# Motivation
see : 

## Primary Use
Fast and efficient translation of data between Xarray and Iris objects.

This allows the user to mix+match features from either package in code. 

For example:
``` python
from ncdata.iris_xarray import cubes_to_xarray, cubes_from_xarray

# Apply Iris regridder to xarray data
dataset = xarray.open_dataset("file1.nc", chunks="auto")
(cube,) = cubes_from_xarray(dataset)
cube2 = cube.regrid(grid_cube, iris.analysis.PointInCell)
dataset2 = cubes_to_xarray(cube2)

# Apply Xarray statistic to Iris data
cubes = iris.load("file1.nc")
dataset = cubes_to_xarray(cubes)
dataset2 = dataset.group_by("time.dayofyear").argmin()
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
dataset = xr.open_dataset("file1.nc")
xr_ncdata = from_xarray(dataset)
dim = xr_ncdata.dimensions.pop("dim0")
dim.name = "newdim"
xr_ncdata.dimensions["newdim"] = dim
for var in xr_ncdata.variables.values():
    var.dimensions = ["newdim" if dim == "dim0" else dim for dim in var.dimensions]
to_nc4(ncdata, "file_2a.nc")

# Fix chunking in Iris input
ncdata = from_nc4("file1.nc")
for var in ncdata.variables:
    # custom chunking() mimics the file chunks we want
    var.chunking = lambda: (100.0e6 if dim == "dim0" else -1 for dim in var.dimensions)
cubes = to_iris(ncdata)
``` 

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
conda install -c conda-forge ncdata
```

Or from PyPI with pip
```
pip install ncdata
```

# Project Status

## Iris and Xarray Compatibility
* C.I. tests GitHub PRs and merges, against latest releases of Iris and Xarray
* compatible with iris >= v3.7.0
  * see : [support added in v3.7.0](https://scitools-iris.readthedocs.io/en/stable/whatsnew/3.7.html#internal)

# References
  * Iris issue : https://github.com/SciTools/iris/issues/4994
  * planning presentation : https://github.com/SciTools/iris/files/10499677/Xarray-Iris.bridge.proposal.--.NcData.pdf
  * in-Iris code workings : https://github.com/pp-mo/iris/pull/75



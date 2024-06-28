# # PyBaked

## What is it?

This library allows you to "bake" your(or not) 
packages into a single file that can be imported 
as a normal package

> But IDEs will not support this, 
only, if someone create an extension

## Usage
There are two command-line tools: ``baked-make`` and ``baked-read``

### ``baked-read``
Created for reading "baked" python packages.
Reads metadata, creation date, packages and modules in it.

Usage:
```bash
baked-read backed_package_name
```
> ``backed_package_name`` it is a file with extension .py.baked
> 
> Note: you can pass name without extension(tool will add it)

Or, to read module source from it:
```bash
baked-read backed_package_name -m module_name
```
> ``module_name`` can be get from parentheses from first example run

___
### ``baked-make``
Created for "baking" packages into a single file.

Usage:
```bash
baked-make package_name -o baked_package_name
```
> ``package_name`` is the name of the source package
> 
> ``baked_package_name`` is the name of the output "baked" package
> (this is optional argument)

All optional parameters and description:  
-H / --hash - Hash modules in the package 
(if the hash not match in the package - loader will not load this package)  
-m / --metadata - JSON formated metadata that will be serialized and 
baked into a file  
-M / --metadata-file - path to a metadata JSON formatted file  
-o / --output - "baked" package name

___
### Importing
To import "baked" package you need to init loader first:
```python
import pybaked


pybaked.loader.init()
```

And then, you can import "baked" packages as normal python packages:
```python
import baked_package_name
```
___
### ``BakedMaker``
Class created for creating baked packages (used by ``baked-make`` tool)

Usage:
```python
import pybaked

# Make baked package from real existent package
pybaked.BakedMaker.from_package(
    "pybaked",
    hash_content=True,
    metadata={"a": "b"}
).file("baked_package_name.py.baked")
```
> This code will "bake" package pybaked into 
a single file named "baked_package_name.py.baked"

Example, without real existent package:
```python
import pybaked

pybaked.BakedMaker(
    hash_content=True,
    metadata={"a": "b"}
).include_module(b"module_name", b"print(\"Source code\")").file(
    "baked_package_name"
)

```
> **Note**: ``BakedMaker.include_module`` first parameter is a module name in 
an import format (example: ``subpackage.module_name``)
> 
> For example, if you pass ``some.py`` into ``BakedMaker.include_module`` it
will be added as ``py`` module in the ``some`` subpackage of the "baked" package
___
### ``BakedReader``
Class created for reading "baked" packages (used by ``baked-read`` tool)

Usage:
```python
import pybaked

reader = pybaked.BakedReader("baked_package_name.py.baked")

# Package creation date
print("Package created at:", reader.created)

# Package metadata
print("Package metadata:", reader.metadata)

# Package modules (module_name, source_offset)
print("Package modules:", reader.modules)

# Package modules as dict {module_name: source_offset}
print("Package modules as dict:", reader.modules_dict)

# Package subpackages
print("Package subpackages:", reader.packages)
```
> **Note**: reader combines ``package_name`` and ``module_name`` separating by dot  

For example, when ``module_name`` is a "``__init__``" and 
``package_name`` is a "``baked_package``". 
Then reader will return it as ``baked_package.__init__``.
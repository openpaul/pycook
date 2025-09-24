# PyCook

This package is a cooklang parser. 

I mostly develop this to be able to handle coklang files for my cookbook. 

It aims to be feature complete and compatible with the specs listed here:

[https://cooklang.org/docs/spec/](https://cooklang.org/docs/spec/)

It should not be very opinionated, for example it does not enforce special units. You can use SI units or any other unit you want.

You may use this as you please under the LICENSE given. 


## Usage
```sh
pip install git+https://github.com/openpaul/pycook
```

The core class is called `Recipe`.

### Read from file
```python
from pycook import read_cook

recipe = read_cook("recipe.cook")
```


### Parse from string
```python
from pycook import CooklangParser

parser = CooklangParser()
recipe = parser.parse("recipe text @in cooklang{}")
```

## Issues

If you figured out how to use this, feel free to open an issue and I'll take a look at it.


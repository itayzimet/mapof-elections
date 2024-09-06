[![codecov](https://codecov.io/github/science-for-democracy/mapof-elections/graph/badge.svg?token=EDMLWNYCTP)](https://codecov.io/github/science-for-democracy/mapof-elections)


# Mapof-elections
This pacakge is a plugin for [Mapof](https://pypi.org/project/mapof/) extending
it with capabilities of drawing maps of various elections intances.

For the most recent version of Mapof, visit its [git
repo](https://pypi.org/project/mapof/).

# Installation
For a simple installation, type:
`pip install mapof-elections`
in the console.

For more complicated variants of installation, refer to the readme of mapel
[here](https://github.com/szufix/mapel).

## Extra dependencies

For the full functionality of the package, it is recommended to also install
extra dependencies. Doing this is covered in [this
readme](https://pypi.org/project/mapel/). The extra dependencies contain:  
```
pulp~=2.5.1
abcvoting~=2.0.0b0
permanent
```  
which unlock approval based committee rules (which require solving I(L)P
programs) and sampling a matrix using a permanent-based approach.

One can do it by invoking  
`pip install mapel-elections[extras]`

> :exclamation: Note that this library contains C++ extensions. So installing
  this library from sources  might be a bit cumbersome. We will, one day, put
  here an instruction how to do it.


# Acknowledgments

This project is part of the [PRAGMA project](https://home.agh.edu.pl/~pragma/)
which has received funding from the [European Research Council
(ERC)](https://home.agh.edu.pl/~pragma/) under the European Union’s Horizon 2020
research and innovation programme ([grant agreement No
101002854](https://erc.easme-web.eu/?p=101002854)).




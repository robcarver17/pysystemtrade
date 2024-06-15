#!/bin/bash

# Cython 3.0.0 is not supported by pandas 1.0.5
python -m pip install "cython<3.0.0" wheel
python -m pip install pyyaml==5.4.1 --no-build-isolation

pip install -r requirements_apple_silicon.txt

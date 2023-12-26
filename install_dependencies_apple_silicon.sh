#!/bin/bash

# Cython 3.0.0 is not supported by pandas 1.0.5
python -m pip install "cython<3.0.0" wheel
python -m pip install pyyaml==5.4.1 --no-build-isolation
python -m pip install "numpy>=1.19.4,<1.24.0" --no-use-pep517
python -m pip install scipy --no-use-pep517
python -m pip install pandas==1.0.5 --no-use-pep517
python -m pip install statsmodels==0.12.2 --no-use-pep517

pip install -r requirements_apple_silicon.txt

# Installation

## Introduction

This guide shows the quickest and easiest way to install the project in a virtual environment


## pyenv

pyenv allows easy installation of multiple versions of Python on the same machine. It allows the version of python used to be defined at the user and project level. It is a great tool, easy to use, and does its one job very well. It is worth reading the introduction to have an overview of how it works at a high level. It's not necessary to understand the technical internals 

https://github.com/pyenv/pyenv#how-it-works

Installation instructions for pyenv are here:

https://github.com/pyenv/pyenv#installation

## Python 3.10

pysystemtrade currently requires Python 3.10, so once pyenv is installed, the first step is to get that. Get the latest 3.10.x version, at the time of writing it is 3.10.13

```
$ pyenv install 3.10
```

Once complete you should be able to see the new version in the output of `pyenv versions`

```
$ pyenv versions
  system
  3.7.14
  3.8.5
  3.8.6
  3.8.10
  3.8.13
  3.8.15
  3.8.16
  3.9.6
  3.9.13
  3.10.4
* 3.10.13
```

Your output will be different, it's just an example


## project files

Once we have the correct version of Python, it's time to get the project files. 

If you intend to contribute to the project, or run your own instance, you will likely want to clone your own fork

```
git clone https://github.com/<your_git_hub_id>/pysystemtrade.git
```

otherwise, you'll want the main repo

```
git clone https://github.com/robcarver17/pysystemtrade.git
```

Now we will want to let pyenv know that we want to use Python 3.10 for this project

```
cd pysystemtrade
pyenv local 3.10.13
```

this creates a file at the top level of the project `.python-version` that lets the Python execution environment know to use version 3.10.13. We can check this by running python

```
$ python
Python 3.10.13 (main, Nov 27 2023, 11:13:49) [Clang 14.0.0 (clang-1400.0.29.202)]
Type "help", "copyright", "credits" or "license" for more information.
>>> 
< ctrl-D to exit >
```

## venv

https://docs.python.org/3.10/library/venv.html

Now we want to create a virtual env (venv) for the project. Doing this will keep all the dependencies for pysystemtrade separate from your other python projects

```
$ python -m venv venv/3.10.13
```

This will create a brand new, isolated Python environment *inside the pysystemtrade project* at the directory
`<your_path>/pysystemtrade/venv/3.10.13`. You can give your environment any name (the *venv/3.10.13* bit).

Now activate the virtual environment

```
source venv/3.10.13/bin/activate
```

Once your virtual env is activated, the prompt will change. It will look something like 

```
(3.10.13) $
```
This reminds you that you're in a venv. (You can exit the venv at any time by running `deactivate`)


## dependencies

Now it's time to start setting up the venv. First check to see what is there 

```
(3.10.13) $ pip list
```

You will probably be prompted to update pip at this time. Do whatever command it suggests.

And now install the dependencies

```
(3.10.13) $ pip install -r requirements.txt
```

### MacOS (ARM)

If you're running MacOS on one of the new ARM chips, the process is more complex. You'll need Homebrew and the Apple XCode Commandline Development Tools, configured for ARM. Doing that is beyond the scope of this document, type `homebrew apple xcode command line tools` into your favourite search engine. Once installed and configured, run installation script:

```
chmod u+x install_dependencies_apple_silicon.sh
./install_dependencies_apple_silicon.sh

```
Note: this may (unfortunately) become out of date and require some tweaking.

### Check dependencies

Check what is installed, should look something like

```
(3.10.13) % pip list
Package         Version
--------------- ------------
blinker         1.7.0
click           8.1.7
contourpy       1.2.0
cycler          0.12.1
eventkit        1.0.3
exceptiongroup  1.2.0
Flask           3.0.1
fonttools       4.47.2
ib-insync       0.9.86
iniconfig       2.0.0
itsdangerous    2.1.2
Jinja2          3.1.3
joblib          1.3.2
kiwisolver      1.4.5
MarkupSafe      2.1.4
matplotlib      3.8.2
nest-asyncio    1.6.0
numpy           1.26.3
packaging       23.2
pandas          2.1.3
patsy           0.5.6
pillow          10.2.0
pip             23.3.2
pluggy          1.3.0
psutil          5.6.6
pyarrow         15.0.0
pymongo         3.11.3
pyparsing       3.1.1
PyPDF2          3.0.1
pytest          7.4.4
python-dateutil 2.8.2
pytz            2023.3.post1
PyYAML          5.3.1
scikit-learn    1.4.0
scipy           1.12.0
setuptools      65.5.0
six             1.16.0
statsmodels     0.14.0
threadpoolctl   3.2.0
tomli           2.0.1
tzdata          2023.4
Werkzeug        3.0.1
```

## pysystemtrade

And finally, install the project itself

```
(3.10.13) $ python setup.py develop
```

Check stuff works

```
(3.10.13) $ python
>>>
>>> from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
Configuring sim logging
>>> data=csvFuturesSimData()
>>> data
csvFuturesSimData object with 249 instruments
>>> 
```

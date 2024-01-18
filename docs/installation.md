# Installation

## Introduction

This project has some quirks relating to installation and dependencies. Mostly, they're to do with the reliance on Arctic. That project has very specific requirements with some versions of dependencies which are becoming seriously out of date. It makes most sense to have a specific Python installation for this project, with the dependencies isolated from those used by other projects. This guide shows the quickest and easiest way to manage that


## pyenv

pyenv allows easy installation of multiple versions of Python on the same machine. It allows the version of python used to be defined at the user and project level. It is a great tool, easy to use, and does its one job very well. It is worth reading the introduction to have an overview of how it works at a high level. It's not necessary to understand the technical internals 

https://github.com/pyenv/pyenv#how-it-works

Installation instructions for pyenv are here:

https://github.com/pyenv/pyenv#installation

## Python 3.8

pysystemtrade currently requires Python 3.8, so once pyenv is installed, the first step is to get that. Get the latest 3.8.x version, at the time of writing it is 3.8.16

```
$ pyenv install 3.8.16
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
* 3.8.15
  3.8.16
  3.9.6
  3.9.13
  3.10.4
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

Now we will want to let pyenv know that we want to use Python 3.8 for this project

```
cd pysystemtrade
pyenv local 3.8.16
```

this creates a file at the top level of the project `.python-version` that lets the Python execution environment know to use version 3.8.16. We can check this by running python

```
$ python
Python 3.8.16 (default, Mar 19 2023, 11:38:42) 
[Clang 14.0.0 (clang-1400.0.29.202)] 
Type "help", "copyright", "credits" or "license" for more information.
>>> 
< ctrl-D to exit >
```

## venv

https://docs.python.org/3.8/library/venv.html

Now we want to create a virtual env (venv) for the project. Doing this will keep all the dependencies for pysystemtrade (some of which are pretty old) separate from your other python projects

```
$ python -m venv venv/3.8.16
```

This will create a brand new, isolated Python environment *inside the pysystemtrade project* at the directory
`<your_path>/pysystemtrade/venv/3.8.6`. You can give your environment any name (the *venv/3.8.6* bit).

Now activate the virtual environment

```
source venv/3.8.16/bin/activate
```

Once your virtual env is activated, the prompt will change. It will look something like 

```
(3.8.16) $
```
This reminds you that you're in a venv. (You can exit the venv at any time by running `deactivate`)


## dependencies

Now it's time to start setting up the venv. First check to see what is there 

```
(3.8.16) $ pip list
```

You will probably be prompted to update pip at this time. Do whatever command it suggests.

Now install *wheel*

```
(3.8.16) $ pip install wheel
```

### Linux, Windows, MacOS (Intel)

Install *cython* 

```
(3.8.16) $ pip install cython
```

And now install the dependencies

```
(3.8.16) $ pip install -r requirements.txt
```

### MacOS (ARM)

If you're running MacOS on one of the new ARM chips, the process is more complex. You'll need Homebrew and the Apple XCode Commandline Development Tools, configured for ARM. Doing that is beyond the scope of this document, type `homebrew apple xcode command line tools` into your favourite search engine. Once installed and configured, run installation script:

```
chmod u+x install_dependencies_apple_silicon.sh
./install_dependencies_apple_silicon.sh
```
Note: this may (unfortunately) become out of date and require some tweaking.

### Check dependencies, all OSs

Check what is installed, should look something like

```
(3.8.16) $ pip list
Package               Version
--------------------- -----------
arctic                1.79.2
attrs                 22.2.0
backports.zoneinfo    0.2.1
click                 8.1.3
contourpy             1.0.7
cycler                0.11.0
Cython                0.29.33
decorator             5.1.1
enum-compat           0.0.3
eventkit              1.0.0
exceptiongroup        1.1.1
Flask                 2.2.3
fonttools             4.39.2
ib-insync             0.9.70
importlib-metadata    6.1.0
importlib-resources   5.12.0
iniconfig             2.0.0
itsdangerous          2.1.2
Jinja2                3.1.2
kiwisolver            1.4.4
lz4                   4.3.2
MarkupSafe            2.1.2
matplotlib            3.7.1
mockextras            1.0.2
nest-asyncio          1.5.6
numpy                 1.23.5
packaging             23.0
pandas                1.0.5
patsy                 0.5.3
Pillow                9.4.0
pip                   23.0.1
pluggy                1.0.0
psutil                5.6.6
pymongo               3.9.0
pyparsing             3.0.9
PyPDF2                3.0.1
pytest                7.2.2
python-dateutil       2.8.2
pytz                  2022.7.1
pytz-deprecation-shim 0.1.0.post0
PyYAML                5.4
scipy                 1.10.1
setuptools            56.0.0
six                   1.16.0
statsmodels           0.12.2
tomli                 2.0.1
typing_extensions     4.5.0
tzdata                2022.7
tzlocal               4.3
Werkzeug              2.2.3
wheel                 0.40.0
zipp                  3.15.0
```

## pysystemtrade

And finally, install the project itself

```
(3.8.16) $ python setup.py develop
```

Check stuff works

```
(3.8.16) $ python
>>>
>>> from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
>>> data=csvFuturesSimData()
2023-03-19 12:29:18 {'type': 'csvFuturesSimData'} [Warning] No datapaths provided for .csv, will use defaults  (may break in production, should be fine in sim)
>>> data
csvFuturesSimData object with 208 instruments
>>> 
```

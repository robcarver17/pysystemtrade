# Installation

## Introduction

This guide shows a couple of ways to install the project in a virtual environment.

## project files

Install the project files by cloning the GitHub repository. If you intend to contribute to the project, or run your own instance, you will likely want to clone your own fork

```
git clone https://github.com/<your_git_hub_id>/pysystemtrade.git
```

otherwise, you'll want the main repo

```
git clone https://github.com/robcarver17/pysystemtrade.git
```


## Option 1: pyenv + venv 

### pyenv

pyenv is a tool that makes it easy to manage multiple versions of Python on the same machine. It allows the version of Python used to be defined at the user and project level. It is a great tool, easy to use, and does its one job very well. It is worth reading the introduction to have an overview of how it works at a high level. It's not necessary to understand the technical internals 

https://github.com/pyenv/pyenv#how-it-works

Installation instructions for pyenv are here:

https://github.com/pyenv/pyenv#installation


First install Python itself. pysystemtrade currently requires Python 3.10 or newer

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
  3.8.16
  3.9.6
  3.9.13
  3.10.4
* 3.10.15
```

Your output will be different, it's just an example

### venv

https://docs.python.org/3.10/library/venv.html

Now we want to create a virtual environment (venv) for the project. Doing this will keep all the dependencies for pysystemtrade separate from your other Python projects

```
$ cd pysystemtrade
$ python -m venv .venv
```

This will create a brand new, isolated Python environment *inside the pysystemtrade project* at the directory
`<your_path>/pysystemtrade/.venv`. You can give your environment any name (the *.venv* bit).

Now activate the virtual environment

```
source .venv/bin/activate
```

Once your virtual env is activated, the prompt will change. It will look something like 

```
(.venv) $
```
This reminds you that your venv is active. You can exit the venv at any time by running `deactivate`

Now we will want to let pyenv know that we want to use Python 3.10 for this project

```
pyenv local 3.10.15
```

this creates a file at the top level of the project `.python-version` that lets the Python execution environment know to use version 3.10.15. We can check this by running `python`

```
$ python
Python 3.10.15 (main, Nov 27 2023, 11:13:49) [Clang 14.0.0 (clang-1400.0.29.202)]
Type "help", "copyright", "credits" or "license" for more information.
>>> 
< ctrl-D to exit >
```

### dependencies

Now it's time to start setting up the venv. First update the basic tools

```
(.venv) $ pip install --upgrade pip setuptools
```

And now install the project and its dependencies

```
(.venv) $ python -m pip install .
```

Or, if you intend to contribute to the project, you will need the optional development dependencies too, and will want to install in *editable* mode

```
(.venv) $ python -m pip install --editable '.[dev]'
```

Check what is installed, should look something like

```
(.venv) % pip list
Package           Version 
----------------- ----------- 
black             23.11.0
blinker           1.8.2
click             8.1.7
contourpy         1.3.0
cycler            0.12.1
decorator         5.1.1
enum-compat       0.0.3
eventkit          1.0.3
exceptiongroup    1.2.2
Flask             3.0.3
fonttools         4.54.1
ib-insync         0.9.86
iniconfig         2.0.0
itsdangerous      2.2.0
Jinja2            3.1.4
joblib            1.4.2
kiwisolver        1.4.7
lz4               4.3.3
MarkupSafe        2.1.5
matplotlib        3.9.2
mock              5.1.0
mockextras        1.0.2
mypy-extensions   1.0.0
nest-asyncio      1.6.0
numpy             1.26.4
packaging         24.1
pandas            2.1.3
pathspec          0.12.1
patsy             0.5.6
pillow            10.4.0
pip               24.3.1
platformdirs      4.3.6
pluggy            1.5.0
psutil            5.6.7
pyarrow           17.0.0
pymongo           3.11.3
pyparsing         3.1.4
PyPDF2            3.0.1
pysystemtrade     1.8.2
pytest            8.3.3
python-dateutil   2.9.0.post0
pytz              2023.3
PyYAML            6.0.1
scikit-learn      1.5.2
scipy             1.14.1
setuptools        65.5.0
six               1.16.0
statsmodels       0.14.0
threadpoolctl     3.5.0
tomli             2.0.1
typing_extensions 4.12.2
tzdata            2024.2
tzlocal           5.2
Werkzeug          3.0.4
```

## Option 2: uv

[uv](https://github.com/astral-sh/uv) is packaging tool that combines the functionality of pip, pyenv, venv and more; read about it [here](https://docs.astral.sh/uv/). It is written in Rust and **extremely** fast

Installation instructions for uv are here:

https://docs.astral.sh/uv/getting-started/installation/


First install Python itself. Pysystemtrade currently requires Python 3.10 or newer

```
$ uv python install 3.10
```

Once complete you should be able to see the new version in the output of `uv python list`

```
cpython-3.13.1+freethreaded-linux-x86_64-gnu    <download available>
cpython-3.13.1-linux-x86_64-gnu                 <download available>
cpython-3.13.0+freethreaded-linux-x86_64-gnu    /home/xxxxx/.local/share/uv/python/cpython-3.13.0+freethreaded-linux-x86_64-gnu/bin/python3.13t
cpython-3.13.0-linux-x86_64-gnu                 /home/xxxxx/.local/share/uv/python/cpython-3.13.0-linux-x86_64-gnu/bin/python3.13
cpython-3.12.8-linux-x86_64-gnu                 <download available>
cpython-3.12.7-linux-x86_64-gnu                 /usr/bin/python3.12
cpython-3.12.7-linux-x86_64-gnu                 /usr/bin/python3 -> python3.12
cpython-3.12.7-linux-x86_64-gnu                 /bin/python3.12
cpython-3.12.7-linux-x86_64-gnu                 /bin/python3 -> python3.12
cpython-3.12.5-linux-x86_64-gnu                 /home/xxxxx/.local/share/uv/python/cpython-3.12.5-linux-x86_64-gnu/bin/python3.12
cpython-3.11.11-linux-x86_64-gnu                <download available>
cpython-3.11.9-linux-x86_64-gnu                 /home/xxxxx/.local/share/uv/python/cpython-3.11.9-linux-x86_64-gnu/bin/python3.11
cpython-3.10.16-linux-x86_64-gnu                <download available>
cpython-3.10.15-linux-x86_64-gnu                /home/xxxxx/.local/share/uv/python/cpython-3.10.15-linux-x86_64-gnu/bin/python3.10
cpython-3.9.21-linux-x86_64-gnu                 <download available>
cpython-3.9.16-linux-x86_64-gnu                 /usr/bin/python3.9
cpython-3.9.16-linux-x86_64-gnu                 /usr/bin/python -> /etc/alternatives/python
cpython-3.9.16-linux-x86_64-gnu                 /bin/python3.9
cpython-3.9.16-linux-x86_64-gnu                 /bin/python -> /etc/alternatives/python
cpython-3.8.20-linux-x86_64-gnu                 <download available>
cpython-3.7.9-linux-x86_64-gnu                  <download available>
pypy-3.10.14-linux-x86_64-gnu                   <download available>
pypy-3.9.19-linux-x86_64-gnu                    <download available>
pypy-3.8.16-linux-x86_64-gnu                    <download available>
pypy-3.7.13-linux-x86_64-gnu                    <download available>
```

Now we want to create a virtual environment for the project with Python 3.10 we are using.

```
$ uv venv --python 3.10
```

This will create a brand new, isolated Python environment *inside the pysystemtrade project* at the directory
`<your_path>/pysystemtrade/.venv`.

You will see
```
Using CPython 3.10.15
Creating virtual environment at: .venv
Activate with: source .venv/bin/activate
```

Now activate the virtual envrionment as instructed.
```
source .venv/bin/activate
```

Once your virtual env is activated, the prompt will change. It will look something like

```
(pysystemtrade) $
```
This reminds you that your virtual environment is active. You can exit the virtual environment at any time by running `deactivate`

We can check this by running `python`

```
$ python
Python 3.10.15 (main, Nov 27 2023, 11:13:49) [Clang 14.0.0 (clang-1400.0.29.202)]
Type "help", "copyright", "credits" or "license" for more information.
>>>
< ctrl-D to exit >
```

### dependencies

And now install the project and its dependencies

```
(pysystemtrade) $ uv pip install .
```

Or, if you intend to contribute to the project, you will need the optional development dependencies too, and will want to install in *editable* mode

```
(pysystemtrade) $ uv pip install --editable '.[dev]'
```

Check what is installed, should look something like

```
(pysystemtrade) $ uv pip list
Package           Version     Editable project location
----------------- ----------- ---------------------------------
black             23.11.0
blinker           1.9.0
click             8.1.8
contourpy         1.3.1
cycler            0.12.1
eventkit          1.0.3
exceptiongroup    1.2.2
flask             3.1.0
fonttools         4.55.8
ib-insync         0.9.86
iniconfig         2.0.0
itsdangerous      2.2.0
jinja2            3.1.5
joblib            1.4.2
kiwisolver        1.4.8
markupsafe        3.0.2
matplotlib        3.10.0
mypy-extensions   1.0.0
nest-asyncio      1.6.0
numpy             1.26.4
packaging         24.2
pandas            2.1.3
pathspec          0.12.1
patsy             1.0.1
pillow            11.1.0
pip               25.0
platformdirs      4.3.6
pluggy            1.5.0
psutil            5.6.7
pyarrow           19.0.0
pymongo           3.11.3
pyparsing         3.2.1
pypdf2            3.0.1
pysystemtrade     1.8.2       /home/xxxxx/github/pysystemtrade
pytest            8.3.4
python-dateutil   2.9.0.post0
pytz              2023.3
pyyaml            6.0.1
scikit-learn      1.6.1
scipy             1.15.1
setuptools        75.8.0
six               1.17.0
statsmodels       0.14.0
threadpoolctl     3.5.0
tomli             2.2.1
typing-extensions 4.12.2
tzdata            2025.1
werkzeug          3.1.3
```




## test

Check stuff works

```
(.venv) $ python
>>>
>>> from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
Configuring sim logging
>>> data=csvFuturesSimData()
>>> data
csvFuturesSimData object with 249 instruments
>>>
```

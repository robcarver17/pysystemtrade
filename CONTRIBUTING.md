# Pysystemtrade contributing guide


## Unit tests
This project has a few unit tests. They get run automatically when any PR is 
submitted. You'll see the result of the run in the PR page. To run the tests
yourself locally, before submitting, you'll need `pytest` installed. Then run:
```
pytest
```

to run an individual unit test, pass the module file name and path
```
pytest sysdata/tests/test_config.py
```

To run all the tests except one module, use the `--ignore` flag
```
pytest --ignore=sysinit/futures/tests/test_sysinit_futures.py
```

Some tests are marked as `@pytest.mark.slow` because they take a long time. These
run automatically every evening. If you want to run them locally, pass
the `--runslow` flag
```
pytest --runslow
```


## Lint / Black

This project keeps its code pretty with 
[Black](https://black.readthedocs.io/en/stable/). Black gets automatically run 
over any PRs, and the PR won't be merged if it fails. To clean your code
submission manually you'll need Black installed, instructions 
[here](https://black.readthedocs.io/en/stable/getting_started.html). Then
run:
```
black path/to/module.py
```

Or, get your IDE or editor to automatically re-format files as you save. Configuration
instructions [here](https://black.readthedocs.io/en/stable/integrations/editors.html)

Note for pycharm users: The blackd plugin requires a blackd daemon to be running; add it to your crontab.

Or, configure your local git install to automatically check and fix your code
as you commit. Configuration instructions 
[here](https://black.readthedocs.io/en/stable/integrations/source_version_control.html)

### Black version

Black needs to be consistent between the version running in the CI build and your local environment. To check the currently used version, see the `[tool.black]` section of the project TOML file  (https://github.com/robcarver17/pysystemtrade/blob/master/pyproject.toml)

## General code guidelines (INCOMPLETE)

These guidelines are aspirations, and do not describe the system as it stands. The project has been written over a period of several years, and it is only quite recently I've decided to set out some guidelines. 

In general, we try and follow the original texts: [PEP 8](https://peps.python.org/pep-0008/) and [clean code](https://gist.github.com/wojteklu/73c6914cc446146b8b533c0988cf8d29).

### General

- Unless there is a single parameter, passed parameters should be explicit.
- It is almost always better to use `arg_not_supplied` (`from syscore.objects import arg_not_supplied`) as a default argument then resolve it to the appropriate value in the function. 
- Type hints should be used, with Unions if required `from typing import Union` and Lists / Dicts ...`from typing import List, Dict`
- Verbose doc strings specifying all the parameters are no longer required (superseded by type hints)

### Naming conventions

- For classes, I prefer mixedCase to CamelCase, but single word names should always be Camels.
- Common methods are `get`, `calculate`, `read`, `write`.
- There is a specific procedure for naming objects which form part of the data heirarchy, see [here](https://github.com/robcarver17/pysystemtrade/blob/master/docs/data.md#part-2-overview-of-futures-data-in-pysystemtrade). If this is not followed, then the [automated abstraction of data inside Data 'blob' instances](https://github.com/robcarver17/pysystemtrade/blob/master/docs/data.md#data-blobs) won't work.
- Although arguably redundant, I am a fan of describing eg objects that inherit from dicts with a dict_ prefix. This gives hints as to how they behave without having to look at their code.


### Error handling

- Production code should not throw an error unless things are completely unrecoverable; if it does throw an error it must also log.critical which will email the user


### Caching

FIXME This is a bit of a mess - Update when a unified cache system setup


### Testing

Doc tests should be removed from class methods, since they often require a lot of setup, and make the code harder to read. Unit tests are preferable.
Doc tests make more sense for seperate, standalone, functions. This is especially the case when they can be used to quickly demonstrate how a function works.

Test coverage is extremely sparse. 

# pysystemtrade contributing guide


## unit tests
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


## lint

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

> Note for pycharm users: The blackd plugin requires a blackd daemon to be running; add it to your crontab.

Or, configure your local git install to automatically check and fix your code
as you commit. Configuration instructions 
[here](https://black.readthedocs.io/en/stable/integrations/source_version_control.html)

### Black version

Black needs to be consistent between the version running in the CI build and your local environment. To check the currently used version, see the [GitHub action config](https://github.com/robcarver17/pysystemtrade/blob/master/.github/workflows/lint.yml)

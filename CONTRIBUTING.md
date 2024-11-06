# Pysystemtrade contributing guide

Welcome and thank you for your interest in contributing to the project. This document aims to describe the preferred workflow

## Contributing

For small bugs, typos, documentation improvements, and minor changes - follow the steps in the [Working on topic branches](#working-on-topic-branches) section below to create a Pull Request.

For large changes, or new feature requests - please start an **Ideas** discussion first. Explain your idea, include some reasoning, perhaps some implementation ideas.

## Setup

> Credit to the [QuantConnect Lean project](https://github.com/QuantConnect/Lean), where most of these instructions originated

* Set up a [GitHub](https://github.com/) account
* [Fork](https://help.github.com/articles/fork-a-repo/) the [repository](https://github.com/robcarver17/pysystemtrade) of the project
* Clone your fork locally

```bash
$ git clone https://github.com/<your_username>/pysystemtrade.git
```

* Navigate to the pysystemtrade directory and add a remote `upstream`

```bash
$ cd pysystemtrade
$ git remote add upstream https://github.com/robcarver17/pysystemtrade.git
```

The *upstream* remote links your fork of the project with the original

## Keeping your repo up to date

Now that you've defined the upstream branch, you can refresh your local copy with the following commands:

```bash
$ git checkout develop
$ git pull
```

This will checkout your local develop branch and then merge changes in from upstream

## Branching model

If you are not familiar with git branches, please read this [guide](https://www.atlassian.com/git/tutorials/using-branches/). Our branching model is based on the one outlined [here](https://nvie.com/posts/a-successful-git-branching-model/) 

The following names will be used to differentiate between the different repositories:

* **upstream** - The 'official' pysystemtrade [repository](https://github.com/robcarver17/pysystemtrade.git) (what is on Rob's GitHub account)
* **origin** - Your fork of the official repository on GitHub (what is on your GitHub account)
* **local** - This will be your local clone of **origin** (what is on your computer)

As a **contributor** you will push your completed **local** topic branch to **origin**. As a **contributor** you will pull your updates from **upstream**. Assuming the change is accepted, a **collaborator** will merge branches from a **contributor** into **upstream**.

## Primary branches

The upstream repository has two branches:

* **upstream/master** - Stable releases
* **upstream/develop** - where development work happens

From time to time, when **develop** is stable, everything on **develop** gets merged into **master**, and that becomes the new stable version.

## Topic branches

Topic branches are for contributors to develop bug fixes and new features so that they can be easily merged to **develop**. They must follow a few simple rules for consistency:

* Must branch off from **develop**
* Must be merged back into **develop**
* Ideally, should have the GitHub issue number in the branch name

Topic branches should exist in your **local** and **origin** repositories only. Submitting a pull request will request a merge from your topic branch to the **upstream/develop** branch.

## Working on topic branches

First create a new branch for the work you'd like to perform. When naming your branch, please use the following convention: `bug-<issue#>-<description>` or `feature-<issue#>-<description>`:

```bash
$ git checkout -b bug-123-short-issue-description
Switched to a new branch 'bug-123-short-issue-description'
```

Now perform some work and commit changes. Always review your changes before committing

```bash
$ git status
$ git diff
$ git add --all
$ git commit
```

You can push your changes to your fork's develop branch using:

```bash
$ git push origin develop
```

When committing, be sure to follow [best practices](https://github.com/erlang/otp/wiki/Writing-good-commit-messages) writing good commit descriptions.

After performing some work you'll want to merge in changes (if any) from the **upstream/develop**. You can use the following two commands in order to assist upstream merging:

```bash
$ git fetch upstream
$ git merge upstream/develop bug-123-short-issue-description
```

The `git fetch upstream` command will download the **upstream** repository to your computer but not merge it. The `merge upstream/develop bug-123-short-issue-description` command will [merge](https://www.atlassian.com/git/tutorials/using-branches/git-merge) your changes on top of **upstream/develop**. This will make the review process easier for **collaborators**.

If you need to merge changes in after pushing your branch to **origin**, use the following:

```bash
$ git pull upstream/develop
```

When topic branches are finished and ready for review, they should be pushed back to **origin**.

```bash
$ git push origin bug-123-short-issue-description
To git@github.com:username/pysystemtrade.git
    * [new branch]       bug-123-short-issue-description -> bug-123-short-issue-description
```

Now you're ready to send a [pull request](https://help.github.com/articles/using-pull-requests/) from this branch to **upstream/develop** and update the GitHub issue tracker to let a collaborator know that your branch is ready to be reviewed and merged.  If extra changes are required as part of the review process, make those changes on the topic branch and re-push. First re-checkout the topic branch you made your original changes on:

```bash
$ git checkout bug-123-short-issue-description
```

Now make responses to the review comments, commit, and re-push your changes:

```bash
$ git add --all
$ git commit
$ git push
```

## Unit tests
This project has a few unit tests. They get run automatically when any PR is submitted. You'll see the result of the run in the PR page. To run the tests yourself locally, before submitting, you'll need `pytest` installed. Then run:
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

Some tests are marked as `@pytest.mark.slow` because they take a long time. These run automatically every evening. If you want to run them locally, pass the `--runslow` flag
```
pytest --runslow
```


## Lint / Black

This project keeps its code pretty with [Black](https://black.readthedocs.io/en/stable/). Black gets automatically run over any PRs, and the PR won't be merged if it fails. To clean your code submission manually you'll need Black installed, instructions [here](https://black.readthedocs.io/en/stable/getting_started.html). Then run:
```
black .
```

If you have a virtual environment (venv), you will want to tell Black to ignore that. So if your venv is named `.venv`, the command would be:

```
black . --exclude '/.venv\/.+/'
```

Or, get your IDE or editor to automatically re-format files as you save. Configuration instructions [here](https://black.readthedocs.io/en/stable/integrations/editors.html)

Note for pycharm users: The blackd plugin requires a blackd daemon to be running; add it to your crontab.

Or, configure your local git install to automatically check and fix your code as you commit. Configuration instructions [here](https://black.readthedocs.io/en/stable/integrations/source_version_control.html)

### Black version

Black needs to be consistent between the version running in the CI build and your local environment. To check the currently used version, see the `[tool.black]` section of the project [TOML file](https://github.com/robcarver17/pysystemtrade/blob/develop/pyproject.toml)

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

- Production code should not throw an error unless things are completely unrecoverable; if it does throw an error it must also `log.critical()` which will email the user (with the default production log config)


### Caching

FIXME This is a bit of a mess - Update when a unified cache system setup


### Testing

Doc tests should be removed from class methods, since they often require a lot of setup, and make the code harder to read. Unit tests are preferable. Doc tests make more sense for separate, standalone, functions. This is especially the case when they can be used to quickly demonstrate how a function works.

Test coverage is extremely sparse. 

# pysystemtrade

Systematic Trading in python

Rob Carver

[https://qoppac.blogspot.com/p/pysystemtrade.html](https://qoppac.blogspot.com/p/pysystemtrade.html)


Version 0.51.0


20201028


## Release notes

See [DONE_TO_DO](DONE_TO_DO.md) for release notes, and future plans.


## Description

**pysystemtrade** is the open source version of my own backtesting engine that implements systems according to the framework outlined in my book ["Systematic Trading"](https://www.systematicmoney.org/systematic-trading), which is further developed on [my blog](https://qoppac.blogspot.com).

For a longer explanation of the motivation and point of this project see my [blog post.](https://qoppac.blogspot.com/2015/12/pysystemtrade.html)

Currently pysystemtrade can do the following:
- Backtesting environment that will work "out of the box" for chapter 15 of my book ["Systematic Trading"](https://www.systematicmoney.org/systematic-trading)
- Implement all the optimisation and system design principles in the book and on my website.
- a complete implementation of a fully automated system for futures trading (for interactive brokers) - in progress

pysystemtrade uses the [IB insync library](https://ib-insync.readthedocs.io/api.html) to connect to interactive brokers.

## Use and documentation

[Introduction (start here)](docs/introduction.md)

[Backtesting user guide](docs/userguide.md)

[Working with futures data](/docs/futures.md)

[Production system](/docs/) Documentation incomplete and in progress!

## Dependencies

Python 3.x, pandas, matplotlib, pyyaml, numpy, scipy, quandl, ib_insyc

See [requirements.txt](requirements.txt) for full details.

Make sure you get the python3 versions of the relevant packages, i.e. use:

```
sudo pip3 install ....
```

## Installation

This package isn't hosted on pip. So to get the code the easiest way is to use git:

```
git clone https://github.com/robcarver17/pysystemtrade.git
python3 setup.py develop
```
Notice that develop mode is required so that ipython sessions can see files inside subdirectories which would otherwise be inaccessible.

### A note on support

This is an open source project, designed for people who are already comfortable using and writing python code, are capable of installing the dependencies, and who want a head start on implementing a system of their own. I do not have the time to provide support. Primarily, this is my trading system which you are welcome to use or steal code from, I'm open sourcing it out of the goodness of my heart not so I can become an unpaid technical support helper to hundreds of strangers. Of course I am very happy if you get in touch with me on any of the following topics:

- Confusing error messages
- Missing or misleading documentation
- Suggestions for extra features
 
However I can't guarantee that I will reply immediately, or at all. If you need that level of support then you are better off with another project. The most efficient way of doing this is by [opening an issue on github](https://github.com/robcarver17/pysystemtrade/issues/new). If you discover a bug please include:

- The full script that produces the error, including all `import` statements, or if it's a standard example file a pointer to the file. Ideally this should be a "minimal example" - the shortest possible script that produces the problem.
- Versions of any neccessary libraries you have installed
- The full output trace including the error messages

If you don't include the information above I will close the issue and then ignore it.

I'll try and incorporate any feedback into the code, but this is a part time (and unpaid!) venture for me, and it will be competing with my other interests (writing books, blogging and research). But if you occasionally check github you will hopefully find it gradually improving. Offers to contribute will of course be gratefully accepted.

## Examples

A series of examples using pysystemtrade for my blog posts can be found [here](https://github.com/robcarver17/pysystemtrade_examples).

## Licensing and legal stuff

GNU v3
( See [LICENSE](LICENSE) )

Absolutely no warranty is implied with this product. Use at your own risk. I provide no guarantee that it will be profitable, or that it won't lose all your money very quickly, or delete every file on your computer (by the way: it's not *supposed* to do that. Just in case you thought it was.). All financial trading offers the possibility of loss. Leveraged trading, such as futures trading, may result in you losing all your money, and still owing more. Backtested results are no guarantee of future performance. I can take no responsibility for any losses caused by live trading using pysystemtrade. Use at your own risk. I am not registered or authorised by any financial regulator. 



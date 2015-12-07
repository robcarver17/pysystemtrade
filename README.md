# pysystemtrade
Systematic Trading in python
Version 0.1.1
201512..

Rob Carver
qoppac.blogspot.com/pysystemtrade.html

## Description

**pysystem** trade is the open source version of my own backtesting engine that implements systems according to the framework outlined in my book ["Systematic Trading"](www.systematictrading.org), which is further developed on [my blog](qoppac.blogspot.com).

For a longer explanation of the motivation and point of this projec see my blog post: 

*Eventually* pysystemtrade will include the following:

- Backtesting enviroment that will work out of the box for the three examples in "Systematic Trading" 
- Implement all the optimisation and system design principles in the book.
- Complete implementation of a fully automated system for futures trading (for interactive brokers only), including regularly updated data
- Code to run the present, and future, examples on my blog qoppac.blogspot.co.uk


## Dependencies

Python 3.x, pandas, matplotlib, pyyaml, numpy, scipy
See requirements.txt for full details.

Make sure you get the python3 versions of the relevant packages, i.e. use:

'''
sudo pip3 install ....
'''

## Installation

This package isn't hosted on pip. So to get the code the easiest way is to use git:

'''
git clone https://github.com/robcarver17/pysystemtrade.git
'''

A setup.py file is provided, however as the installation is trivial this shouldn't be neccessary. Just add the relevant ibsystemtrade directory to the path that python searches in, and off you go.

## Use and documentation

Introduction (start here):

User guide: 

Frequently asked questions:

### A note on support

This is an open source project, designed for people who are already comfortable using and writing python code, and who want to understand . I do not have the time to provide support. Of course I am very happy if you get in touch with me on any of the following topics:

- Confusing error messages
- Missing or misleading documentation
- Suggestions for extra features

However I can't guarantee that I will reply immediately, or at all. If you need that level of support then you are better off with another system.

I'll try and incorporate any feedback into the code, but this is a part time venture for me, and it will be competing with my other interests (writing books, blogging and research). But if you occasionally check github you will hopefully find it gradually improving. Offers to contribute will of course be gratefully accepted.

## Release notes

See DONE_TO_DO for release notes, and future plans.

## Licensing and legal stuff

GNU v3
(See LICENSE)

Absolutely no warranty is implied with this product. Use at your own risk. I provide no guarantee that it will be profitable, or that it won't lose all your money very quickly, or delete every file on your computer (by the way: it's not *supposed* to do that. Just in case you thought it was.).


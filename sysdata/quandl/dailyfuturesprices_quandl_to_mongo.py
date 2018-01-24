"""
Get raw futures prices from quandl, and write to mongo
    """

"""
A data system consists of a data input, and stages for calculation, then an output stage which is another data object with write access

The 'calculation' stage can be as simple as a pipe

config objects determine what kind of data processing is done, sources of data etc

data and output stages inherit in the same was as data stages do, eg asset class specific inherit, then source specific

we also need internal representations of things like instruments, futures contracts

open question: should we seperate input and output data for different types of data?
open question: do data configs work differently, in terms of defaults?
open question: do we need a lighter base data class (parent of system data class)?

things we need to store: futures instrument information, futures prices for individual contracts, individual contract information

notes: instrument_list: should we still have this?

"""
from systems.production import outputSystem

data_system = outputSystem(stage_list, data, output, config=config, stages = [futures_price_pipe])
data_system.run()

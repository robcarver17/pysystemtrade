'''
This is a futures system

A system consists of a system, plus a config

These classes suffice for both live and simulation

We need to override them for live by adding 'write optimal position' and 'monitor message bus for new price'

We need to override them for simulation by adding 'generate fake trade list' and 'calculate p&l' methods 
'''
from systems.basesystem import system
from systems.futures.rawdata import FuturesRawData

def full_futures_system( data, config):
    rawdata=FuturesRawData()
    return system(data,config, [rawdata])

    
    

  
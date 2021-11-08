This document describes how we should choose which instruments to trade, and how this is all configured.

INCOMPLETE SCRATCH JOTTINGS RIGHT NOW!


config
(feels like this could be more bulletproof eg override complete sections??)


You might want to calculate forecasts for certain instruments (so don't include them in `ignore_instruments`), but not actually trade them.



If you include the config element `allocate_zero_instrument_weights_to_these_instruments` then those instruments will have a zero instrument weight calculated, and the system will produce a zero desired position for them.


overrides

Overrides allow us to reduce positions for a given strategy, for a given instrument (across all strategies), or for a given instrument & strategy combination. They are either:

- a multiplier, between 0 and 1, by which we multiply the desired . A multiplier of 1 is equal to 'normal', and 0 means 'close everything'
- a flag, allowing us only to submit trades which reduce our positions
- a flag, allowing no trading to occur in the given instrument.



#### Position limits

We can set the maximum allowable position that can be held in a given instrument, or by a specific strategy for an instrument. An instrument trade that will result in a position which exceeds this limit will be rejected (this occurs when run_strategy_order_generator is run). We can:


- Auto update spread cost configuration based on sampling and trades
- Suggest 'bad' markets (illiquid or costly)
- Suggest which duplicate market to use


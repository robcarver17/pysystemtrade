This document describes how you'd make changes to strategies in production: adding new strategies, or replacing existing ones.

It is fairly 'bare bones', and you should have read and understand the [production documentation](/docs/production.md) first.

# Steps to follow

It's important that the following steps are followed, in order.

1. Set up any new instruments and get their prices sampling
2. Ensure you have a working backtest, and create a production configuration .yaml file
3. Create custom classes to run the strategy
4. Make a backup of your data
5. Stop any processes running
6. Update private_config.yaml and private_control_config.yaml
7. Update strategy capital
8. Check the production backtest will run
9. Transfer positions between strategies
10. Run any strategy backtests that will be closing or reducing in capital
11. Ensure position and trade limits are appropriate
12. Manually generate instrument orders
13. Run reports
14. Restart processes
15. Delete replaced strategies from configuration files
16. Clean up


Not all the steps are described in detail in this document, see [the production documents](/docs/production.md) for details.


## Set up any new instruments and get their prices sampling

If your new strategy has new instruments, [set these up first](/docs/data.md). You'll need to have their sampled data to do your backtests.


## Create custom classes to run the strategy

### Create a run_system to run the strategy backtest

If you are using a completely vanilla 'out of the box' strategy that can be run with the default provided stages then this isn't necessary. For clarity these are the default strategies:

- [Classic system](/sysproduction/strategy_code/run_system_classic.py)
- [Dynamic system](/sysproduction/strategy_code/run_dynamic_optimised_system.py) (as described [here](https://qoppac.blogspot.com/2021/10/mr-greedy-and-tale-of-minimum-tracking.html))

Otherwise you will need to create your own runSystem class. There is an example [here](/examples/production/example_of_custom_run_system.py). Notice that it overrides `system_method` to create a different system from the default; that in turn is built up from some custom stages.

You may also need to override the `run_backtest` method if you need your strategy to do something different in terms of saving optimised positions (again that is the principal difference between the classic and dynamic systems).


### Create an order creation class

If you are using a completely vanilla 'out of the box' strategy that can be run with the default order creation functions then this isn't necessary. For clarity these are the default strategies:

- [Classic system](/sysexecution/strategies/classic_buffered_positions.py)
- [Dynamic system](/sysexecution/strategies/dynamic_optimised_positions.py) (as described [here](https://qoppac.blogspot.com/2021/10/mr-greedy-and-tale-of-minimum-tracking.html))

Otherwise you'll need to write an order management function. You will need to overwrite the method `get_required_orders`.


### Create a reporting class

If you are using a completely vanilla 'out of the box' strategy that can be run with the default reporting functions then this isn't necessary. For clarity these are the default strategies:

- [Classic system](/sysproduction/strategy_code/report_system_classic.py)
- [Dynamic system](/sysproduction/strategy_code/report_system_dynamic_optimised.py) (as described [here](https://qoppac.blogspot.com/2021/10/mr-greedy-and-tale-of-minimum-tracking.html))

Otherwise you'll need to write a reporting function. If your strategy is similar enough to the 'classic' system, you can reuse the code as the dynamic system does.


## Update configuration files

Even if you're replacing a strategy I strongly advise that you initially *add* your new strategies to configuration files, keeping the old strategies in place for the time being. 

In your `private_control_config.yaml` file, for example:

```
process_configuration_methods:
  run_systems:
    ... existing systems ...
    dynamic_TF_carry:
      max_executions: 1
      object: private.systems.dynamic_carry_trend.run_system.runMySystemCarryTrendDynamic
      backtest_config_filename: private.systems.dynamic_carry_trend.production.yaml
  run_strategy_order_generator:
    ... existing systems ...
    dynamic_TF_carry:
      object: sysexecution.strategies.dynamic_optimised_positions.orderGeneratorForDynamicPositions
      max_executions: 1
```

Notice that we refer to the custom run_system and order_generator classes that we've created, or the provided classes. We also refer to the production.yaml backtest configuration file.

In your `private_config.yaml` file, for example:


```
strategy_list:
  ... existing systems ...
  dynamic_TF_carry:
    load_backtests:
      object: private.systems.dynamic_carry_trend.run_system.runMySystemCarryTrendDynamic
      function: system_method
    reporting_code:
      function: sysproduction.strategy_code.report_system_dynamic_optimised.report_system_dynamic
strategy_capital_allocation:
  function: sysproduction.strategy_code.strategy_allocation.weighted_strategy_allocation
  strategy_weights:
    dynamic_TF_carry: 99.99   
    medium_speed_TF_carry: 0.01
```

Again we refer to the custom run_system and reporting classes, or to default provided classes. Notice that the contents of strategy_weights will depend on exactly what you'd like to do. Here we're replacing `medium_speed_TF_carry` with `dynamic_TF_carry`. Of course we could also want to do this more gradually starting with just a small notional amount of capital to check everything is working, or only allocate part of our capital to the new strategy rather than all of it.


# Update strategy capital

Next we need to update the strategy capital (using the provided script `update_strategy_capital`). This is required to ensure the backtest will actually run. You should do this even if you're going to start with a nominal amount of capital just to make sure everything works.


# Check the production backtest will run

Using the `update_system_backtests` script make sure that the production system runs okay, and generates optimal positions. 


# Transfer positions between strategies

If you are replacing a strategy, wholly or partially, then it makes sense to transfer the positions across. Otherwise you'll do costly trading as one strategy closes it's positions, and the other opens up new ones. 

There is a script that does this by generating pseudo instrument orders at the current market price. For example (python):

```python
from sysinit.futures.strategy_transfer import *
transfer_positions_between_strategies('medium_speed_TF_carry', 'dynamic_TF_carry')
```

# Run any strategy backtests that will be closing or reducing in capital

This tidying up stage ensures that the optimal positions for existing strategies are correctly adjusted for the new capital, stops position breaks appearing, and ensures that we won't generate unnecessary orders for the old strategy.


# Ensure position and trade limits are appropriate

Using the interactive_controls script, you may want to create strategy specific limits or tweak existing limits.


# Manually generate instrument orders

I'd recommend running the `update_strategy_orders` script. You can run these for both the new and existing strategies. If you're replacing an existing strategy, all the optimal positions should be zero, and if you've transferred all the positions it shouldn't generate any trades.

It may be worth running `interactive_order_stack` and looking at both positions and the instrument order stack to check all is as expected.

# Run reports

I'd recommend running the full suite of reports to make sure everything works, and also to check that all is as it should be (the strategy report should be especially interesting in this respect).



# Restart processes

You can now restart your running processes.

Check that any new instruments can actually trade, i.e. you don't have any unforeseen regulatory issues.



# Clean up

FIXME: To do



# Implementing specific strategies

In this section of the document I describe how to implement specific provided strategies.

## Vanilla classic strategy

FIX ME

## Dynamic optimisation strategy

This is the strategy as described [here](https://qoppac.blogspot.com/2021/10/mr-greedy-and-tale-of-minimum-tracking.html).

### Ignore instruments

Under ignore_instruments in the .yaml configuration, I suggest you include only instruments which are duplicated for different multipliers (i.e. we should have only one of SP500 and SP500_micro). Do not include here untradeable instruments. This also means that for instrument weight calculations we'll include potentially untradeable instruments.



### Set shadow cost

The shadow cost is a key variable which is set in the private_config.yaml file (*not* the backtest configuration file, since it is used 'outside' the backtest in the strategy order generation). The default value is 50, but you may want to initially begin with a very large value (eg 500) and gradually reduce it over the first few days. This will produce a more gradual adjustment from old to new strategy positions, although bear in mind that any strategy position with the wrong sign will immediately be closed regardless of the shadow_cost value unless you set this instrument to don't trade.


### Strategy backtest output of optimal positions

The optimal positions are output from the strategy using a special '-raw' suffix which means they won't normally be displayed. However they are shown in strategy reports.


### Ensure position and trade limits are appropriate

It's particularly important to ensure position limits are in place, because these are used by the dynamic optimisation. I'd suggest using the auto-populate function from the interactive_controls script.

### Ensure any 'don't trade'  or 'reduce only' flags are in place

It's vital that you set don't trade or reduce only trade overrides for instruments that you don't wish to trade (these are set in interactive_controls). Reasons for this can include:

- Too expensive (see the costs report)
- Not enough contracts traded (see liquidity report)
- Not enough risk traded (see the liquidity report)
- Regulatory issues (eg Reg 871, or UK restrictions on crypto derivatives for non MFID professional clients)
- Tick data not available / too expensive (if you're using another source to get daily data)

Obviously if you have no existing position then it doesn't matter if you use don't trade or reduce only flags.

### Actual optimal positions

The actual optimal positions, used to generate instrument orders, are of simple integer values. In addition they also contain a lot of hidden diagnostic information about the optimisation, which is displayed by the strategy report and also by the interactive_diagnostics function to display optimal positions.








This document describes how you'd make changes to strategies in production: adding new strategies, or replacing existing ones.

# Steps to follow

It's important that the following steps are followed, in order.

1. Ensure you have a working backtest, with a production configuration .yaml file
2. Create custom classes to run the strategy
3. Make a backup of your data
4. Stop any processes running
5. Update private_config.yaml and private_control_config.yaml
6. Update strategy capital
7. Check the production backtest will run

Not all the steps are described in detail in this document, see [the production documents](/docs/production.md) for details.

# Create custom classes to run the strategy

## Create a run_system to run the strategy backtest

If you are using a completely vanilla 'out of the box' strategy that can be run with the default provided stages then this isn't neccessary. For clarity these are the default strategies:

- [Classic system](/sysproduction/strategy_code/run_system_classic.py)
- [Dynamic system](/sysproduction/strategy_code/run_dynamic_optimised_system.py) (as described [here](https://qoppac.blogspot.com/2021/10/mr-greedy-and-tale-of-minimum-tracking.html))

Otherwise you will need to create your own runSystem class. There is an example [here](/examples/production/example_of_custom_run_system.py). Notice that it overrides `system_method` to create a different system from the default; that in turn is built up from some custom stages.

You may also need to override the `run_backtest` method if you need your strategy to do something different in terms of saving optimised positions (again that is the principal difference between the classic and dynamic systems).

## Create an order management class

If you are using a completely vanilla 'out of the box' strategy that can be run with the default order management functions then this isn't neccessary. For clarity these are the default strategies:

- [Classic system](/sysexecution/strategies/classic_buffered_positions.py)
- [Dynamic system](/sysexecution/strategies/dynamic_optimised_positions.py) (as described [here](https://qoppac.blogspot.com/2021/10/mr-greedy-and-tale-of-minimum-tracking.html))

Otherwise you'll need to write an order management function. You will need to overwrite the method `get_required_orders`.


## Create a reporting class

If you are using a completely vanilla 'out of the box' strategy that can be run with the default reporting functions then this isn't neccessary. For clarity these are the default strategies:

- [Classic system](/sysproduction/strategy_code/report_system_classic.py)
- [Dynamic system](/sysproduction/strategy_code/report_system_dynamic_optimised.py) (as described [here](https://qoppac.blogspot.com/2021/10/mr-greedy-and-tale-of-minimum-tracking.html))

Otherwise you'll need to write a reporting function. If your strategy is similar enough to the 'classic' system, you can reuse the code as the dynamic system does.




# Update configuration files

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

Again we refer to the custom run_system and reporting classes, or to default provided classes. Notice that the contents of strategy_weights will depend on exactly what you'd like to do. Here we're replacing `medium_speed_TF_carry` with `dynamic_TF_carry`. Of course we could also want to do this more gradually, or only allocate part of our capital to the new strategy rather than all of it.

# Update strategy capital

Next we need to update the strategy capital (using the provided script `update_strategy_capital`). This is required to ensure the backtest will actually run. You should do this even if you're going to start with a nominal amount of capital just to make sure everything works.

# Check the production backtest will run

Using the `update_system_backtests` script make sure that the production system runs okay, and generates optimal positions. 

# Transfer positions between strategies

If you are replacing a strategy, wholly or partially, then it makes sense to transfer the positions across. Otherwise you'll do costly trading as one strategy closes it's positions, and the other opens up new ones.

For example (python):

```python
from sysinit.futures.strategy_transfer import *
ransfer_positions_between_strategies('medium_speed_TF_carry', 'dynamic_TF_carry')
```

# Run any strategy backtests that will be closing or reducing in capital

This tidying up stage ensures that the optimal positions for existing strategies are correctly adjusted for the new capital, stops position breaks appearing, and ensures that we won't generate uneccessary orders for the old strategy.

# Ensure position and trade limits are appropriate

Using the interactive_controls script, you may want to create strategy specific limits or tweak existing limits.


# Manually generate instrument orders


You may want to use 

# Run reports

I'd recommend running the full suite of reports to make sure everything works.





# Implementing specific strategies

In this section of the document I describe how to implement specific provided strategies.

## Vanilla classic strategy

blah

## Dynamic optimisation strategy

This is the strategy as described [here](https://qoppac.blogspot.com/2021/10/mr-greedy-and-tale-of-minimum-tracking.html).

# Strategy backtest output of optimal positions


# Ensure position and trade limits are appropriate

It's particularly important to ensure position limits are in place, because these are used by the dynamic optimisation.

# Ensure any 'don't trade'  or 'reduce only' flags are in place

This is 


This document describes how you'd make changes to strategies in production: adding new strategies, or replacing existing ones.

# Steps to follow

It's important that the following steps are followed, in order.

1. Ensure you have a working backtest, with a production configuration .yaml file
2. Create a run_system to run the strategy
3. Make a backup of your data
4. Stop any processes running
5. Update private_config.yaml and private_control_config.yaml
6. Check the production backtest will run

Not all the steps are described in detail in this document, see [the production documents](/docs/production.md) for details.

# Create a run_system to run the strategy

If you are using a completely vanilla 'out of the box' strategy that can be run with the default provided stages then this isn't neccessary. For clarity these are the default strategies:

- [Classic system](/sysproduction/strategy_code/run_system_classic.py)
- [Dynamic system](/sysproduction/strategy_code/run_dynamic_optimised_system.py) (as described [here](https://qoppac.blogspot.com/2021/10/mr-greedy-and-tale-of-minimum-tracking.html))

Otherwise you will need to create your own runSystem class. There is an example [here](/examples/production/example_of_custom_run_system.py). Notice that it overrides `system_method` to create a different system from the default; that in turn is built up from some custom stages.

You may also need to override the `run_backtest` method if you need your strategy to do something different in terms of saving optimised positions (again that is the principal difference between the classic and dynamic systems).

# Update configuration files

Even if you're replacing a strategy I strongly advise that you initially *add* your new strategies to configuration files before . 

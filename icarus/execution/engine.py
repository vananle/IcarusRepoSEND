# -*- coding: utf-8 -*-
"""This module implements the simulation engine.

The simulation engine, given the parameters according to which a single
experiments needs to be run, instantiates all the required classes and executes
the experiment by iterating through the event provided by an event generator
and providing them to a strategy instance.
"""
from icarus.execution.network import NetworkModel, NetworkView, NetworkController
from icarus.execution.collectors import CollectorProxy
from icarus.registry import DATA_COLLECTOR, STRATEGY

__all__ = ['exec_experiment']


def exec_experiment(topology, workload, netconf, strategy, cache_policy, repo_policy, collectors, warmup_strategy,
                    sched_policy={'name': 'EDF'}):
    """Execute the simulation of a specific scenario.

    Parameters
    ----------
    topology : Topology
        The FNSS Topology object modelling the network topology on which
        experiments are run.
    workload : iterable
        An iterable object whose elements are (time, event) tuples, where time
        is a float type indicating the timestamp of the event to be executed
        and event is a dictionary storing all the attributes of the event to
        execute
    netconf : dict
        Dictionary of attributes to inizialize the network model
    strategy : tree
        Strategy definition. It is tree describing the name of the strategy
        to use and a list of initialization attributes
    cache_policy : tree
        Cache policy definition. It is tree describing the name of the cache
        policy to use and a list of initialization attributes
    collectors: dict
        The collectors to be used. It is a dictionary in which keys are the
        names of collectors to use and values are dictionaries of attributes
        for the collector they refer to.

    Returns
    -------
    results : Tree
        A tree with the aggregated simulation results from all collectors
    """
    model = NetworkModel(topology, cache_policy, repo_policy, sched_policy['name'], workload.n_services, workload.rate,
                         **netconf)
    workload.model = model
    view = NetworkView(model)
    controller = NetworkController(model)

    collectors_inst = [DATA_COLLECTOR[name](view, **params) for name, params in list(collectors.items())]
    collector = CollectorProxy(view, collectors_inst)
    controller.attach_collector(collector)

    strategy_name = strategy['name']
    warmup_strategy_name = warmup_strategy['name']
    strategy_args = {k: v for k, v in list(strategy.items()) if k != 'name'}
    warmup_strategy_args = {k: v for k, v in warmup_strategy.items() if k != 'name'}
    strategy_inst = STRATEGY[strategy_name](view, controller, **strategy_args)
    warmup_strategy_inst = STRATEGY[warmup_strategy_name](view, controller, **warmup_strategy_args)

    n = 0
    for time, event in workload:
        # continue
        strategy_inst.process_event(time, **event)
        if n % 500 == 0 and n:
            collector.results()
        if event['status'] == 1:
            n += 1

    return collector.results()

    """
    counter = 0
    for time, event in workload:
        if counter < workload.n_warmup:
            counter += 1
            warmup_strategy_inst.process_event(time, **event)
        else:
            strategy_inst.process_event(time, **event)

    return collector.results()
    """

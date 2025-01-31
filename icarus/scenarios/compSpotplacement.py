# -*- coding: utf-8 -*-
"""Implements computational spot placement strategies
"""

import networkx as nx

from icarus.registry import register_computation_placement
from icarus.util import iround

__all__ = [
    'uniform_computation_placement',
    'central_computation_placement',
    'uniform_computation_cache_repo_placement'
]


@register_computation_placement('CENTRALITY')
def central_computation_placement(topology, computation_budget, service_budget, **kwargs):
    """Places computation budget proportionally to the betweenness centrality of the
    node.
    
    Parameters
    ----------
    topology : Topology
        The topology object
    computation_budget : int
        The cumulative computation budget in terms of the number of VMs
    """
    betw = nx.betweenness_centrality(topology)
    # root = [v for v in topology.graph['icr_candidates']
    #        if topology.node[v]['depth'] == 0][0]
    # total_betw = sum(betw.values()) - betw[root]
    total_betw = sum(betw.values())
    icr_candidates = topology.graph['icr_candidates']
    for v in icr_candidates:
        topology.node[v]['stack'][1]['computation_size'] = iround(computation_budget * betw[v] / total_betw)
        topology.node[v]['stack'][1]['service_size'] = iround(service_budget * betw[v] / total_betw)


@register_computation_placement('UNIFORM')
def uniform_computation_placement(topology, computation_budget, service_budget, **kwargs):
    """Places computation budget uniformly across cache nodes.
    
    Parameters
    ----------
    topology : Topology
        The topology object
    computation_budget : int
        The cumulative computation budget in terms of the number of VMs
    """

    icr_candidates = topology.graph['icr_candidates']
    print(("Computation budget: " + repr(computation_budget)))
    print(("Service budget: " + repr(service_budget)))
    cache_size = iround(computation_budget / (len(icr_candidates)))
    service_size = iround(service_budget / (len(icr_candidates)))
    # root = [v for v in icr_candidates if topology.node[v]['depth'] == 0][0]
    for v in icr_candidates:
        topology.node[v]['stack'][1]['service_size'] = service_size
        topology.node[v]['stack'][1]['computation_size'] = cache_size
        topology.node[v]['stack'][1]['cache_size'] = service_size


@register_computation_placement('UNIFORM_REPO')
def uniform_computation_cache_repo_placement(topology, computation_budget, service_budget, storage_budget, **kwargs):
    """Places computation budget uniformly across cache nodes.

    Parameters
    ----------
    topology : Topology
        The topology object
    computation_budget : int
        The cumulative computation budget in terms of the number of VMs
    """

    icr_candidates = topology.graph['icr_candidates']
    print(("Computation budget: " + repr(computation_budget)))
    print(("Service budget: " + repr(service_budget)))
    cache_size = iround(computation_budget / (len(icr_candidates)))
    service_size = iround(service_budget / (len(icr_candidates)))
    # root = [v for v in icr_candidates if topology.node[v]['depth'] == 0][0]
    for v in icr_candidates:
        topology.node[v]['stack'][1]['service_size'] = service_size
        topology.node[v]['stack'][1]['computation_size'] = cache_size
        topology.node[v]['stack'][1]['storageSize'] = storage_budget
        topology.node[v]['stack'][1]['cache_size'] = service_size

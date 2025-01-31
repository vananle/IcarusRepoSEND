# -*- coding: utf-8 -*-
"""Functions for creating or importing topologies for experiments.

To create a custom topology, create a function returning an instance of the
`IcnTopology` class. An IcnTopology is simply a subclass of a Topology class
provided by FNSS.

A valid ICN topology must have the following attributes:
 * Each node must have one stack among: source, receiver, router
 * The topology must have an attribute called `icr_candidates` which is a set
   of router nodes on which a cache may be possibly deployed. Caches are not
   deployed directly at topology creation, instead they are deployed by a
   cache placement algorithm.

   TODO: This file shows the topology nodes and their
        This might need to be changed, because the structure seems a bit different
        in our case. Are "receivers" strictly receivers, even if they send requests
        for services? If that is the case, then that's fine. Or, even so, I'd imagine
        some nodes could be both at different instances of time, anyway...?
"""

from os import path

import fnss
import networkx as nx

from icarus.registry import register_topology_factory

# TODO: Maybe modify ICNTopology, to implement repos
#  in all nodes, instead of cache_nodes AND sources?
#  Same goes for network.model...?

__all__ = [
    'IcnTopology',
    'topology_tree',
    'topology_repo_tree',
    'topology_path',
    'topology_ring',
    'topology_mesh',
    'topology_repo_mesh',
    'topology_geant',
    'topology_tiscali',
    'topology_wide',
    'topology_garr',
    'topology_rocketfuel_latency'
]

# Delays
# These values are suggested by this Computer Networks 2011 paper:
# http://www.cs.ucla.edu/classes/winter09/cs217/2011CN_NameRouting.pdf
# which is citing as source of this data, measurements from this IMC'06 paper:
# http://www.mpi-sws.org/~druschel/publications/ds2-imc.pdf
INTERNAL_LINK_DELAY = 2
EXTERNAL_LINK_DELAY = 34

# Path where all topologies are stored
TOPOLOGY_RESOURCES_DIR = path.abspath(path.join(path.dirname(__file__),
                                                path.pardir, path.pardir,
                                                'resources', 'topologies'))


class IcnTopology(fnss.Topology):
    """Class modelling an ICN topology

    An ICN topology is a simple FNSS Topology with addition methods that
    return sets of caching nodes, sources and receivers.
    """

    def cache_nodes(self):
        """Return a dictionary mapping nodes with a cache and respective cache
        size

        Returns
        -------
        cache_nodes : dict
            Dictionary mapping node identifiers and cache size
        """
        return {v: self.node[v]['stack'][1]['cache_size']
                for v in self
                if 'stack' in self.node[v]
                and 'cache_size' in self.node[v]['stack'][1]
                }

    def repo_nodes(self):
        """Return a dictionary mapping nodes with a cache and respective cache
        size

        Returns
        -------
        cache_nodes : dict
            Dictionary mapping node identifiers and cache size
        """
        return {v: self.node[v]['stack'][1]['storageSize']
                for v in self
                if 'stack' in self.node[v]
                and 'storageSize' in self.node[v]['stack'][1]
                }

    def sources(self):
        """Return a set of source nodes

        Returns
        -------
        sources : set
            Set of source nodes
        """
        return set(v for v in self
                   if 'stack' in self.node[v]
                   and self.node[v]['stack'][0] == 'source')

    def receivers(self):
        """Return a set of receiver nodes

        Returns
        -------
        receivers : set
            Set of receiver nodes
        """
        return set(v for v in self
                   if 'stack' in self.node[v]
                   and self.node[v]['stack'][0] == 'receiver')


@register_topology_factory('TREE')
def topology_tree(k, h, delay=0.020, **kwargs):
    """Returns a tree topology, with a source at the root, receivers at the
    leafs and caches at all intermediate nodes.

    Parameters
    ----------
    h : int
        The height of the tree
    k : int
        The branching factor of the tree
    delay : float
        The link delay in milliseconds

    Returns 
    -------
    topology : IcnTopology
        The topology object
    """

    receiver_access_delay = 0.001
    topology = fnss.k_ary_tree_topology(k, h)
    topology.graph['parent'] = [None for x in range(pow(k, h + 1) - 1)]
    for u, v in topology.edges():
        if topology.node[u]['depth'] > topology.node[v]['depth']:
            topology.graph['parent'][u] = v
        else:
            topology.graph['parent'][v] = u

        # TODO: Change(d) the edge allocation from .edges[u, v] to .edges[u, v]...don't really 
        #  understand where edges[u, v] came from originally, anyway, really...

        topology.edges[u, v]['type'] = 'internal'
        if u is 0 or v is 0:
            topology.edges[u, v]['delay'] = delay
            print(("Edge between " + repr(u) + " and " + repr(v) + " delay: " + repr(topology.edges[u, v]['delay'])))
        else:
            topology.edges[u, v]['delay'] = delay
            print(("Edge between " + repr(u) + " and " + repr(v) + " delay: " + repr(topology.edges[u, v]['delay'])))

    for v in topology.nodes():
        print(("Depth of " + repr(v) + " is " + repr(topology.node[v]['depth'])))

    # set weights and delays on all links
    fnss.set_weights_constant(topology, 1.0)
    # fnss.set_delays_constant(topology, delay, 'ms')

    routers = topology.nodes()
    topology.graph['icr_candidates'] = set(routers)
    topology.graph['type'] = 'TREE'
    topology.graph['height'] = h
    topology.graph['link_delay'] = delay
    topology.graph['receiver_access_delay'] = receiver_access_delay

    edge_routers = [v for v in topology.nodes()
                    if topology.node[v]['depth'] == h]
    root = [v for v in topology.nodes()
            if topology.node[v]['depth'] == 0]
    # routers = [v for v in topology.nodes()
    #          if topology.node[v]['depth'] > 0
    #          and topology.node[v]['depth'] < h]

    n_receivers = len(edge_routers)
    receivers = ['rec_%d' % i for i in range(n_receivers)]
    for i in range(n_receivers):
        topology.add_edge(receivers[i], edge_routers[i], delay=receiver_access_delay, type='internal')

    n_sources = len(root)
    sources = ['src_%d' % i for i in range(n_sources)]
    for i in range(n_sources):
        topology.add_edge(sources[i], root[0], delay=3 * delay, type='internal')

    print(("The number of sources: " + repr(n_sources)))
    print(("The number of receivers: " + repr(n_receivers)))
    topology.graph['receiver_access_delay'] = receiver_access_delay
    topology.graph['link_delay'] = delay
    topology.graph['depth'] = h
    for v in sources:
        fnss.add_stack(topology, v, 'source')
    for v in receivers:
        fnss.add_stack(topology, v, 'receiver')
    for v in routers:
        fnss.add_stack(topology, v, 'router')
    # label links as internal

    topology.graph['receivers'] = receivers
    topology.graph['sources'] = sources
    topology.graph['routers'] = routers
    topology.graph['edge_routers'] = edge_routers

    return IcnTopology(topology)


@register_topology_factory('REPO_TREE')
def topology_repo_tree(k, h, delay=0.020, **kwargs):
    """
    Returns a tree topology, with sources (and EDRs) at the root,
    receivers at the leaves and EDRs at all intermediate nodes.

    Parameters
    ----------
    h : int
        The height of the tree
    k : int
        The branching factor of the tree
    delay : float
        The link delay in milliseconds

    Returns
    -------
    topology : IcnTopology
        The topology object
    """

    receiver_access_delay = 0.001
    topology = fnss.k_ary_tree_topology(k, h)
    topology.graph['parent'] = [None for x in range(pow(k, h + 1) - 1)]
    for u, v in topology.edges():
        if topology.node[u]['depth'] > topology.node[v]['depth']:
            topology.graph['parent'][u] = v
        else:
            topology.graph['parent'][v] = u
        topology.edges[u, v]['type'] = 'internal'
        if u is 0 or v is 0:
            topology.edges[u, v]['delay'] = delay
            print(("Edge between " + repr(u) + " and " + repr(v) + " delay: " + repr(topology.edges[u, v]['delay'])))
        else:
            topology.edges[u, v]['delay'] = delay
            print(("Edge between " + repr(u) + " and " + repr(v) + " delay: " + repr(topology.edges[u, v]['delay'])))

    for v in topology.nodes():
        print(("Depth of " + repr(v) + " is " + repr(topology.node[v]['depth'])))

    # set weights and delays on all links
    fnss.set_weights_constant(topology, 1.0)
    # fnss.set_delays_constant(topology, delay, 'ms')

    routers = topology.nodes()
    # TODO: Add set of sources to ICR candidates and account for them as routers, as well as sources.
    topology.graph['icr_candidates'] = set(routers)
    topology.graph['type'] = 'TREE'
    topology.graph['height'] = h
    topology.graph['link_delay'] = delay
    topology.graph['receiver_access_delay'] = receiver_access_delay

    edge_routers = [v for v in topology.nodes()
                    if topology.node[v]['depth'] == h]
    root = [v for v in topology.nodes()
            if topology.node[v]['depth'] == 0]
    # routers = [v for v in topology.nodes()
    #          if topology.node[v]['depth'] > 0
    #          and topology.node[v]['depth'] < h]

    # TODO: THIS REALLY HAS TO BE CHANGED! NOT ALL RECEIVERS SHOULD BE AT THE EDGE!
    #  (I would argue that only a few should be, at most)

    n_receivers = len(edge_routers)
    receivers = ['rec_%d' % i for i in range(n_receivers)]
    for i in range(n_receivers):
        topology.add_edge(receivers[i], edge_routers[i], delay=receiver_access_delay, type='internal')

    n_sources = len(root)
    sources = ['src_%d' % i for i in range(n_sources)]
    for i in range(n_sources):
        topology.add_edge(sources[i], root[0], delay=3 * delay, type='internal')

    print(("The number of sources: " + repr(n_sources)))
    print(("The number of receivers: " + repr(n_receivers)))
    topology.graph['receiver_access_delay'] = receiver_access_delay
    topology.graph['link_delay'] = delay
    topology.graph['depth'] = h
    for v in routers:
        fnss.add_stack(topology, v, 'router')
        if 'source' not in topology.node[v]['stack']:
            try:
                if topology.node[v]['type'] == 'leaf':
                    try:
                        topology.node[v]['extra_types'].append('source')
                        topology.node[v]['extra_types'].append('router')
                    except Exception as e:
                        err_type = str(type(e)).split("'")[1].split(".")[1]
                        if err_type == "KeyError":
                            topology.node[v].update(extra_types=['source'])
                            topology.node[v]['extra_types'].append('router')

            except Exception as e:
                err_type = str(type(e)).split("'")[1].split(".")[1]
                if err_type == "KeyError":
                    continue
    for v in sources:
        fnss.add_stack(topology, v, 'source')
    for v in receivers:
        fnss.add_stack(topology, v, 'receiver')

    # label links as internal

    topology.graph['receivers'] = receivers
    topology.graph['sources'] = sources
    topology.graph['sources'].extend(routers)
    topology.graph['sources'].extend(edge_routers)
    topology.graph['routers'] = routers
    topology.graph['edge_routers'] = edge_routers

    return IcnTopology(topology)


@register_topology_factory('PATH')
def topology_path(n, delay=1, **kwargs):
    """Return a path topology with a receiver on node `0` and a source at node
    'n-1'

    Parameters
    ----------
    n : int (>=3)
        The number of nodes
    delay : float
        The link delay in milliseconds

    Returns
    -------
    topology : IcnTopology
        The topology object
    """
    topology = fnss.line_topology(n)
    receivers = [0]
    routers = list(range(1, n - 1))
    sources = [n - 1]
    topology.graph['icr_candidates'] = set(routers)
    for v in sources:
        fnss.add_stack(topology, v, 'source')
    for v in receivers:
        fnss.add_stack(topology, v, 'receiver')
    for v in routers:
        fnss.add_stack(topology, v, 'router')
    # set weights and delays on all links
    fnss.set_weights_constant(topology, 1.0)
    fnss.set_delays_constant(topology, delay, 'ms')
    # label links as internal or external
    for u, v in topology.edges():
        topology.edges[u, v]['type'] = 'internal'
    return IcnTopology(topology)


@register_topology_factory('RING')
def topology_ring(n, delay_int=1, delay_ext=5, **kwargs):
    """Returns a ring topology

    This topology is comprised of a ring of *n* nodes. Each of these nodes is
    attached to a receiver. In addition one router is attached to a source.
    Therefore, this topology has in fact 2n + 1 nodes.

    It models the case of a metro ring network, with many receivers and one
    only source towards the core network.

    Parameters
    ----------
    n : int
        The number of routers in the ring
    delay_int : float
        The internal link delay in milliseconds
    delay_ext : float
        The external link delay in milliseconds

    Returns
    -------
    topology : IcnTopology
        The topology object
    """
    topology = fnss.ring_topology(n)
    routers = list(range(n))
    receivers = list(range(n, 2 * n))
    source = 2 * n
    internal_links = list(zip(routers, receivers))
    external_links = [(routers[0], source)]
    for u, v in internal_links:
        topology.add_edge(u, v, type='internal')
    for u, v in external_links:
        topology.add_edge(u, v, type='external')
    topology.graph['icr_candidates'] = set(routers)
    fnss.add_stack(topology, source, 'source')
    for v in receivers:
        fnss.add_stack(topology, v, 'receiver')
    for v in routers:
        fnss.add_stack(topology, v, 'router')
    # set weights and delays on all links
    fnss.set_weights_constant(topology, 1.0)
    fnss.set_delays_constant(topology, delay_int, 'ms', internal_links)
    fnss.set_delays_constant(topology, delay_ext, 'ms', external_links)
    return IcnTopology(topology)


@register_topology_factory('MESH')
def topology_mesh(n, m, delay_int=1, delay_ext=5, **kwargs):
    """Returns a ring topology

    This topology is comprised of a mesh of *n* nodes. Each of these nodes is
    attached to a receiver. In addition *m* router are attached each to a source.
    Therefore, this topology has in fact 2n + m nodes.

    Parameters
    ----------
    n : int
        The number of routers in the ring
    m : int
        The number of sources
    delay_int : float
        The internal link delay in milliseconds
    delay_ext : float
        The external link delay in milliseconds

    Returns
    -------
    topology : IcnTopology
        The topology object
    """
    if m > n:
        raise ValueError("m cannot be greater than n")
    topology = fnss.full_mesh_topology(n)
    routers = list(range(n))
    receivers = list(range(n, 2 * n))
    sources = list(range(2 * n, 2 * n + m))
    internal_links = list(zip(routers, receivers))
    external_links = list(zip(routers[:m], sources))
    for u, v in internal_links:
        topology.add_edge(u, v, type='internal')
    for u, v in external_links:
        topology.add_edge(u, v, type='external')
    topology.graph['icr_candidates'] = set(routers)
    for v in sources:
        fnss.add_stack(topology, v, 'source')
    for v in receivers:
        fnss.add_stack(topology, v, 'receiver')
    for v in routers:
        fnss.add_stack(topology, v, 'router')
    # set weights and delays on all links
    fnss.set_weights_constant(topology, 1.0)
    fnss.set_delays_constant(topology, delay_int, 'ms', internal_links)
    fnss.set_delays_constant(topology, delay_ext, 'ms', external_links)
    return IcnTopology(topology)


@register_topology_factory('REPO_MESH')
def topology_repo_mesh(n, m, delay_int=0.02, delay_ext=1, **kwargs):
    """Returns a ring topology

    This topology is comprised of a mesh of *n* nodes. Each of these nodes is
    attached to a receiver. In addition *m* router are attached each to a source.
    Therefore, this topology has in fact 2n + m nodes.

    Parameters
    ----------
    n : int
        The number of routers in the ring
    m : int
        The number of sources
    delay_int : float
        The internal link delay in milliseconds
    delay_ext : float
        The external link delay in milliseconds

    Returns
    -------
    topology : IcnTopology
        The topology object
    """
    receiver_access_delay = 0.001
    if m > n:
        raise ValueError("m cannot be greater than n")
    topology = fnss.full_mesh_topology(n)
    topology.sources_no = m
    topology.routers_no = n
    routers = list(range(n))
    receivers = ['rec_%d' % i for i in range(n)]
    sources = ['src_%d' % i for i in range(m)]
    internal_links = list(zip(routers, receivers))
    for u in routers:
        for v in routers:
            if v != u:
                internal_links.append(tuple([u, v]))
    external_links = list(zip(routers[:m], sources))
    for u, v in internal_links:
        topology.add_edge(u, v, type='internal')
    for u, v in external_links:
        topology.add_edge(u, v, type='external')
    topology.graph['icr_candidates'] = set(routers)

    n_sources = m

    print(("The number of sources: " + repr(n_sources)))
    print(("The number of receivers: " + repr(n)))
    topology.graph['receiver_access_delay'] = receiver_access_delay
    topology.graph['link_delay'] = delay_int
    for v in routers:
        fnss.add_stack(topology, v, 'router')
        if 'source' not in topology.node[v]['stack']:
            try:
                try:
                    topology.node[v]['extra_types'].append('source')
                    topology.node[v]['extra_types'].append('router')
                except Exception as e:
                    err_type = str(type(e)).split("'")[1].split(".")[1]
                    if err_type == "KeyError":
                        topology.node[v].update(extra_types=['source'])
                        topology.node[v]['extra_types'].append('router')

            except Exception as e:
                err_type = str(type(e)).split("'")[1].split(".")[1]
                if err_type == "KeyError":
                    continue
    for v in sources:
        fnss.add_stack(topology, v, 'source')
    for v in receivers:
        fnss.add_stack(topology, v, 'receiver')

    # set weights and delays on all links
    fnss.set_weights_constant(topology, 1.0)
    fnss.set_delays_constant(topology, delay_int, 'ms', internal_links)
    fnss.set_delays_constant(topology, delay_ext, 'ms', external_links)

    # label links as internal

    topology.graph['receivers'] = receivers
    topology.graph['sources'] = sources
    topology.graph['sources'].extend(routers)
    topology.graph['routers'] = routers
    topology.graph['edge_routers'] = routers

    return IcnTopology(topology)


@register_topology_factory('GEANT')
def topology_geant(**kwargs):
    """Return a scenario based on GEANT topology

    Parameters
    ----------
    seed : int, optional
        The seed used for random number generation

    Returns
    -------
    topology : fnss.Topology
        The topology object
    """
    # 240 nodes in the main component
    topology = fnss.parse_topology_zoo(path.join(TOPOLOGY_RESOURCES_DIR,
                                                 'Geant2012.graphml')
                                       ).to_undirected()
    topology = list(nx.connected_component_subgraphs(topology))[0]
    deg = nx.degree(topology)
    receivers = [v for v in topology.nodes() if deg[v] == 1]  # 8 nodes
    icr_candidates = [v for v in topology.nodes() if deg[v] > 2]  # 19 nodes
    # attach sources to topology
    source_attachments = [v for v in topology.nodes() if deg[v] == 2]  # 13 nodes
    sources = []
    for v in source_attachments:
        u = v + 1000  # node ID of source
        topology.add_edge(v, u)
        sources.append(u)
    routers = [v for v in topology.nodes() if v not in sources + receivers]
    # add stacks to nodes
    topology.graph['icr_candidates'] = set(icr_candidates)
    for v in sources:
        fnss.add_stack(topology, v, 'source')
    for v in receivers:
        fnss.add_stack(topology, v, 'receiver')
    for v in routers:
        fnss.add_stack(topology, v, 'router')
    # set weights and delays on all links
    fnss.set_weights_constant(topology, 1.0)
    fnss.set_delays_constant(topology, INTERNAL_LINK_DELAY, 'ms')
    # label links as internal or external
    for u, v in topology.edges():
        if u in sources or v in sources:
            topology.edges[u, v]['type'] = 'external'
            # this prevents sources to be used to route traffic
            fnss.set_weights_constant(topology, 1000.0, [(u, v)])
            fnss.set_delays_constant(topology, EXTERNAL_LINK_DELAY, 'ms', [(u, v)])
        else:
            topology.edges[u, v]['type'] = 'internal'
    return IcnTopology(topology)


@register_topology_factory('TISCALI')
def topology_tiscali(**kwargs):
    """Return a scenario based on Tiscali topology, parsed from RocketFuel dataset

    Parameters
    ----------
    seed : int, optional
        The seed used for random number generation

    Returns
    -------
    topology : fnss.Topology
        The topology object
    """
    # 240 nodes in the main component
    topology = fnss.parse_rocketfuel_isp_map(path.join(TOPOLOGY_RESOURCES_DIR,
                                                       '3257.r0.cch')
                                             ).to_undirected()
    topology = list(nx.connected_component_subgraphs(topology))[0]
    # degree of nodes
    deg = nx.degree(topology)
    # nodes with degree = 1
    onedeg = [v for v in topology.nodes() if deg[v] == 1]  # they are 80
    # we select as caches nodes with highest degrees
    # we use as min degree 6 --> 36 nodes
    # If we changed min degrees, that would be the number of caches we would have:
    # Min degree    N caches
    #  2               160
    #  3               102
    #  4                75
    #  5                50
    #  6                36
    #  7                30
    #  8                26
    #  9                19
    # 10                16
    # 11                12
    # 12                11
    # 13                 7
    # 14                 3
    # 15                 3
    # 16                 2
    icr_candidates = [v for v in topology.nodes() if deg[v] >= 6]  # 36 nodes
    # sources are node with degree 1 whose neighbor has degree at least equal to 5
    # we assume that sources are nodes connected to a hub
    # they are 44
    sources = [v for v in onedeg if deg[list(topology.edge[v].keys())[0]] > 4.5]  # they are
    # receivers are node with degree 1 whose neighbor has degree at most equal to 4
    # we assume that receivers are nodes not well connected to the network
    # they are 36
    receivers = [v for v in onedeg if deg[list(topology.edge[v].keys())[0]] < 4.5]
    # we set router stacks because some strategies will fail if no stacks
    # are deployed
    routers = [v for v in topology.nodes() if v not in sources + receivers]

    # set weights and delays on all links
    fnss.set_weights_constant(topology, 1.0)
    fnss.set_delays_constant(topology, INTERNAL_LINK_DELAY, 'ms')

    # Deploy stacks
    topology.graph['icr_candidates'] = set(icr_candidates)
    for v in sources:
        fnss.add_stack(topology, v, 'source')
    for v in receivers:
        fnss.add_stack(topology, v, 'receiver')
    for v in routers:
        fnss.add_stack(topology, v, 'router')

    # label links as internal or external
    for u, v in topology.edges():
        if u in sources or v in sources:
            topology.edges[u, v]['type'] = 'external'
            # this prevents sources to be used to route traffic
            fnss.set_weights_constant(topology, 1000.0, [(u, v)])
            fnss.set_delays_constant(topology, EXTERNAL_LINK_DELAY, 'ms', [(u, v)])
        else:
            topology.edges[u, v]['type'] = 'internal'
    return IcnTopology(topology)


@register_topology_factory('WIDE')
def topology_wide(**kwargs):
    """Return a scenario based on GARR topology

    Parameters
    ----------
    seed : int, optional
        The seed used for random number generation

    Returns
    -------
    topology : fnss.Topology
        The topology object
    """
    topology = fnss.parse_topology_zoo(path.join(TOPOLOGY_RESOURCES_DIR, 'WideJpn.graphml')).to_undirected()
    # sources are nodes representing neighbouring AS's
    sources = [9, 8, 11, 13, 12, 15, 14, 17, 16, 19, 18]
    # receivers are internal nodes with degree = 1
    receivers = [27, 28, 3, 5, 4, 7]
    # caches are all remaining nodes --> 27 caches
    routers = [n for n in topology.nodes() if n not in receivers + sources]
    # All routers can be upgraded to ICN functionalitirs
    icr_candidates = routers
    # set weights and delays on all links
    fnss.set_weights_constant(topology, 1.0)
    fnss.set_delays_constant(topology, INTERNAL_LINK_DELAY, 'ms')
    # Deploy stacks
    topology.graph['icr_candidates'] = set(icr_candidates)
    for v in sources:
        fnss.add_stack(topology, v, 'source')
    for v in receivers:
        fnss.add_stack(topology, v, 'receiver')
    for v in routers:
        fnss.add_stack(topology, v, 'router')
    # label links as internal or external
    for u, v in topology.edges():
        if u in sources or v in sources:
            topology.edges[u, v]['type'] = 'external'
            # this prevents sources to be used to route traffic
            fnss.set_weights_constant(topology, 1000.0, [(u, v)])
            fnss.set_delays_constant(topology, EXTERNAL_LINK_DELAY, 'ms', [(u, v)])
        else:
            topology.edges[u, v]['type'] = 'internal'
    return IcnTopology(topology)


@register_topology_factory('GARR')
def topology_garr(**kwargs):
    """Return a scenario based on GARR topology

    Parameters
    ----------
    seed : int, optional
        The seed used for random number generation

    Returns
    -------
    topology : fnss.Topology
        The topology object
    """
    topology = fnss.parse_topology_zoo(path.join(TOPOLOGY_RESOURCES_DIR, 'Garr201201.graphml')).to_undirected()
    # sources are nodes representing neighbouring AS's
    sources = [0, 2, 3, 5, 13, 16, 23, 24, 25, 27, 51, 52, 54]
    # receivers are internal nodes with degree = 1
    receivers = [1, 7, 8, 9, 11, 12, 19, 26, 28, 30, 32, 33, 41, 42, 43, 47, 48, 50, 53, 57, 60]
    # caches are all remaining nodes --> 27 caches
    routers = [n for n in topology.nodes() if n not in receivers + sources]
    icr_candidates = routers
    # set weights and delays on all links
    fnss.set_weights_constant(topology, 1.0)
    fnss.set_delays_constant(topology, INTERNAL_LINK_DELAY, 'ms')

    # Deploy stacks
    topology.graph['icr_candidates'] = set(icr_candidates)
    for v in sources:
        fnss.add_stack(topology, v, 'source')
    for v in receivers:
        fnss.add_stack(topology, v, 'receiver')
    for v in routers:
        fnss.add_stack(topology, v, 'router')

    # label links as internal or external
    for u, v in topology.edges():
        if u in sources or v in sources:
            topology.edges[u, v]['type'] = 'external'
            # this prevents sources to be used to route traffic
            fnss.set_weights_constant(topology, 1000.0, [(u, v)])
            fnss.set_delays_constant(topology, EXTERNAL_LINK_DELAY, 'ms', [(u, v)])
        else:
            topology.edges[u, v]['type'] = 'internal'
    return IcnTopology(topology)


@register_topology_factory('GARR_2')
def topology_garr2(**kwargs):
    """Return a scenario based on GARR topology.

    Differently from plain GARR, this topology some receivers are appended to
    routers and only a subset of routers which are actually on the path of some
    traffic are selected to become ICN routers. These changes make this
    topology more realistic.

    Parameters
    ----------
    seed : int, optional
        The seed used for random number generation

    Returns
    -------
    topology : fnss.Topology
        The topology object
    """
    topology = fnss.parse_topology_zoo(path.join(TOPOLOGY_RESOURCES_DIR, 'Garr201201.graphml')).to_undirected()

    # sources are nodes representing neighbouring AS's
    sources = [0, 2, 3, 5, 13, 16, 23, 24, 25, 27, 51, 52, 54]
    # receivers are internal nodes with degree = 1
    receivers = [1, 7, 8, 9, 11, 12, 19, 26, 28, 30, 32, 33, 41, 42, 43, 47, 48, 50, 53, 57, 60]
    # routers are all remaining nodes --> 27 caches
    routers = [n for n in topology.nodes() if n not in receivers + sources]
    artificial_receivers = list(range(1000, 1000 + len(routers)))
    for i in range(len(routers)):
        topology.add_edge(routers[i], artificial_receivers[i])
    receivers += artificial_receivers
    # Caches to nodes with degree > 3 (after adding artificial receivers)
    degree = nx.degree(topology)
    icr_candidates = [n for n in topology.nodes() if degree[n] > 3.5]
    # set weights and delays on all links
    fnss.set_weights_constant(topology, 1.0)
    fnss.set_delays_constant(topology, INTERNAL_LINK_DELAY, 'ms')

    # Deploy stacks
    topology.graph['icr_candidates'] = set(icr_candidates)
    for v in sources:
        fnss.add_stack(topology, v, 'source')
    for v in receivers:
        fnss.add_stack(topology, v, 'receiver')
    for v in routers:
        fnss.add_stack(topology, v, 'router')
    # label links as internal or external
    for u, v in topology.edges():
        if u in sources or v in sources:
            topology.edges[u, v]['type'] = 'external'
            # this prevents sources to be used to route traffic
            fnss.set_weights_constant(topology, 1000.0, [(u, v)])
            fnss.set_delays_constant(topology, EXTERNAL_LINK_DELAY, 'ms', [(u, v)])
        else:
            topology.edges[u, v]['type'] = 'internal'
    return IcnTopology(topology)


@register_topology_factory('GEANT_2')
def topology_geant2(**kwargs):
    """Return a scenario based on GEANT topology.

    Differently from plain GEANT, this topology some receivers are appended to
    routers and only a subset of routers which are actually on the path of some
    traffic are selected to become ICN routers. These changes make this
    topology more realistic.

    Parameters
    ----------
    seed : int, optional
        The seed used for random number generation

    Returns
    -------
    topology : fnss.Topology
        The topology object
    """
    # 53 nodes
    topology = fnss.parse_topology_zoo(path.join(TOPOLOGY_RESOURCES_DIR,
                                                 'Geant2012.graphml')
                                       ).to_undirected()
    topology = list(nx.connected_component_subgraphs(topology))[0]
    deg = nx.degree(topology)
    receivers = [v for v in topology.nodes() if deg[v] == 1]  # 8 nodes
    # attach sources to topology
    source_attachments = [v for v in topology.nodes() if deg[v] == 2]  # 13 nodes
    sources = []
    for v in source_attachments:
        u = v + 1000  # node ID of source
        topology.add_edge(v, u)
        sources.append(u)
    routers = [v for v in topology.nodes() if v not in sources + receivers]
    # Put caches in nodes with top betweenness centralities
    betw = nx.betweenness_centrality(topology)
    routers = sorted(routers, key=lambda k: betw[k])
    # Select as ICR candidates the top 50% routers for betweenness centrality
    icr_candidates = routers[len(routers) // 2:]
    # add stacks to nodes
    topology.graph['icr_candidates'] = set(icr_candidates)
    for v in sources:
        fnss.add_stack(topology, v, 'source')
    for v in receivers:
        fnss.add_stack(topology, v, 'receiver')
    for v in routers:
        fnss.add_stack(topology, v, 'router')
    # set weights and delays on all links
    fnss.set_weights_constant(topology, 1.0)
    fnss.set_delays_constant(topology, INTERNAL_LINK_DELAY, 'ms')
    # label links as internal or external
    for u, v in topology.edges():
        if u in sources or v in sources:
            topology.edges[u, v]['type'] = 'external'
            # this prevents sources to be used to route traffic
            fnss.set_weights_constant(topology, 1000.0, [(u, v)])
            fnss.set_delays_constant(topology, EXTERNAL_LINK_DELAY, 'ms', [(u, v)])
        else:
            topology.edges[u, v]['type'] = 'internal'
    return IcnTopology(topology)


@register_topology_factory('TISCALI_2')
def topology_tiscali2(**kwargs):
    """Return a scenario based on Tiscali topology, parsed from RocketFuel dataset

    Differently from plain Tiscali, this topology some receivers are appended to
    routers and only a subset of routers which are actually on the path of some
    traffic are selected to become ICN routers. These changes make this
    topology more realistic.

    Parameters
    ----------
    seed : int, optional
        The seed used for random number generation

    Returns
    -------
    topology : fnss.Topology
        The topology object
    """
    # 240 nodes in the main component
    topology = fnss.parse_rocketfuel_isp_map(path.join(TOPOLOGY_RESOURCES_DIR,
                                                       '3257.r0.cch')
                                             ).to_undirected()
    topology = list(nx.connected_component_subgraphs(topology))[0]
    # degree of nodes
    deg = nx.degree(topology)
    # nodes with degree = 1
    onedeg = [v for v in topology.nodes() if deg[v] == 1]  # they are 80
    # we select as caches nodes with highest degrees
    # we use as min degree 6 --> 36 nodes
    # If we changed min degrees, that would be the number of caches we would have:
    # Min degree    N caches
    #  2               160
    #  3               102
    #  4                75
    #  5                50
    #  6                36
    #  7                30
    #  8                26
    #  9                19
    # 10                16
    # 11                12
    # 12                11
    # 13                 7
    # 14                 3
    # 15                 3
    # 16                 2
    icr_candidates = [v for v in topology.nodes() if deg[v] >= 6]  # 36 nodes
    # Add remove caches to adapt betweenness centrality of caches
    for i in [181, 208, 211, 220, 222, 250, 257]:
        icr_candidates.remove(i)
    icr_candidates.extend([232, 303, 326, 363, 378])
    # sources are node with degree 1 whose neighbor has degree at least equal to 5
    # we assume that sources are nodes connected to a hub
    # they are 44
    sources = [v for v in onedeg if deg[list(topology.edge[v].keys())[0]] > 4.5]  # they are
    # receivers are node with degree 1 whose neighbor has degree at most equal to 4
    # we assume that receivers are nodes not well connected to the network
    # they are 36
    receivers = [v for v in onedeg if deg[list(topology.edge[v].keys())[0]] < 4.5]
    # we set router stacks because some strategies will fail if no stacks
    # are deployed
    routers = [v for v in topology.nodes() if v not in sources + receivers]

    # set weights and delays on all links
    fnss.set_weights_constant(topology, 1.0)
    fnss.set_delays_constant(topology, INTERNAL_LINK_DELAY, 'ms')

    # deploy stacks
    topology.graph['icr_candidates'] = set(icr_candidates)
    for v in sources:
        fnss.add_stack(topology, v, 'source')
    for v in receivers:
        fnss.add_stack(topology, v, 'receiver')
    for v in routers:
        fnss.add_stack(topology, v, 'router')

    # label links as internal or external
    for u, v in topology.edges():
        if u in sources or v in sources:
            topology.edges[u, v]['type'] = 'external'
            # this prevents sources to be used to route traffic
            fnss.set_weights_constant(topology, 1000.0, [(u, v)])
            fnss.set_delays_constant(topology, EXTERNAL_LINK_DELAY, 'ms', [(u, v)])
        else:
            topology.edges[u, v]['type'] = 'internal'
    return IcnTopology(topology)


@register_topology_factory('ROCKET_FUEL')
def topology_rocketfuel_latency(asn, source_ratio=1.0, ext_delay=EXTERNAL_LINK_DELAY, **kwargs):
    """Parse a generic RocketFuel topology with annotated latencies

    To each node of the parsed topology it is attached an artificial receiver
    node. To the routers with highest degree it is also attached a source node.

    Parameters
    ----------
    asn : int
        AS number
    source_ratio : float
        Ratio between number of source nodes (artificially attached) and routers
    ext_delay : float
        Delay on external nodes
    """
    if source_ratio < 0 or source_ratio > 1:
        raise ValueError('source_ratio must be comprised between 0 and 1')
    f_topo = path.join(TOPOLOGY_RESOURCES_DIR, 'rocketfuel-latency', str(asn), 'latencies.intra')
    topology = fnss.parse_rocketfuel_isp_latency(f_topo).to_undirected()
    topology = list(nx.connected_component_subgraphs(topology))[0]
    # First mark all current links as inernal
    for u, v in topology.edges():
        topology.edges[u, v]['type'] = 'internal'
    # Note: I don't need to filter out nodes with degree 1 cause they all have
    # a greater degree value but we compute degree to decide where to attach sources
    routers = topology.nodes()
    # Source attachment
    n_sources = int(source_ratio * len(routers))
    sources = ['src_%d' % i for i in range(n_sources)]
    deg = nx.degree(topology)

    # Attach sources based on their degree purely, but they may end up quite clustered
    routers = sorted(routers, key=lambda k: deg[k], reverse=True)
    for i in range(len(sources)):
        topology.add_edge(sources[i], routers[i], delay=ext_delay, type='external')

    # Here let's try attach them via cluster
    #     clusters = compute_clusters(topology, n_sources, distance=None, n_iter=1000)
    #     source_attachments = [max(cluster, key=lambda k: deg[k]) for cluster in clusters]
    #     for i in range(len(sources)):
    #         topology.add_edge(sources[i], source_attachments[i], delay=ext_delay, type='external')

    # attach artificial receiver nodes to ICR candidates
    receivers = ['rec_%d' % i for i in range(len(routers))]
    for i in range(len(routers)):
        topology.add_edge(receivers[i], routers[i], delay=0, type='internal')
    # Set weights to latency values
    for u, v in topology.edges():
        topology.edges[u, v]['weight'] = topology.edges[u, v]['delay']
    # Deploy stacks on nodes
    topology.graph['icr_candidates'] = set(routers)
    for v in sources:
        fnss.add_stack(topology, v, 'source')
    for v in receivers:
        fnss.add_stack(topology, v, 'receiver')
    for v in routers:
        fnss.add_stack(topology, v, 'router')
    return IcnTopology(topology)

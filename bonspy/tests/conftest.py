# -*- coding: utf-8 -*-

from __future__ import (
    print_function, division, generators,
    absolute_import, unicode_literals
)

import networkx as nx

import pytest


@pytest.fixture
def graph():
    g = nx.DiGraph()

    g.add_node(0, split='segment', state={})
    g.add_node(1, split='age', state={'segment': 12345})
    g.add_node(2, split='age', state={'segment': 67890})
    g.add_node(3, split='geo', state={'segment': 12345, 'age': (0., 10.)})
    g.add_node(4, split='geo', state={'segment': 12345, 'age': (10., 20.)})
    g.add_node(5, split='geo', state={'segment': 67890, 'age': (0., 20.)})
    g.add_node(6, split='geo', state={'segment': 67890, 'age': (20., 40.)})
    g.add_node(7, is_leaf=True, output=0.10,
               state={'segment': 12345, 'age': (0, 10.),
                      'geo': ('UK', 'DE')})
    g.add_node(8, is_leaf=True, output=0.20,
               state={'segment': 12345, 'age': (0, 10.),
                      'geo': ('US', 'BR')})
    g.add_node(9, is_leaf=True, output=0.10,
               state={'segment': 12345, 'age': (10., 20.),
                      'geo': ('UK', 'DE')})
    g.add_node(10, is_leaf=True, output=0.20,
               state={'segment': 12345, 'age': (10., 20.),
                      'geo': ('US', 'BR')})
    g.add_node(11, is_leaf=True, output=0.10,
               state={'segment': 67890, 'age': (0., 20.),
                      'geo': ('UK', 'DE')})
    g.add_node(12, is_leaf=True, output=0.20,
               state={'segment': 67890, 'age': (0., 20.),
                      'geo': ('US', 'BR')})
    g.add_node(13, is_leaf=True, output=0.10,
               state={'segment': 67890, 'age': (20., 40.),
                      'geo': ('UK', 'DE')})
    g.add_node(14, is_leaf=True, output=0.20,
               state={'segment': 67890, 'age': (20., 40.),
                      'geo': ('US', 'BR')})
    g.add_node(15, is_default_leaf=True, output=0.05, state={})
    g.add_node(16, is_default_leaf=True, output=0.05, state={'segment': 12345})
    g.add_node(17, is_default_leaf=True, output=0.05, state={'segment': 67890})
    g.add_node(18, is_default_leaf=True, output=0.05,
               state={'segment': 12345, 'age': (0., 10.)})
    g.add_node(19, is_default_leaf=True, output=0.05,
               state={'segment': 12345, 'age': (10., 20.)})
    g.add_node(20, is_default_leaf=True, output=0.05,
               state={'segment': 67890, 'age': (0., 20.)})
    g.add_node(21, is_default_leaf=True, output=0.05,
               state={'segment': 67890, 'age': (20., 40.)})

    g.add_edge(0, 1, value=12345, type='assignment')
    g.add_edge(0, 2, value=67890, type='assignment')
    g.add_edge(1, 3, value=(0., 10.), type='range')
    g.add_edge(1, 4, value=(10., 20.), type='range')
    g.add_edge(2, 5, value=(0., 20.), type='range')
    g.add_edge(2, 6, value=(20., 40.), type='range')
    g.add_edge(3, 7, value=('UK', 'DE'), type='membership')
    g.add_edge(3, 8, value=('US', 'BR'), type='membership')
    g.add_edge(4, 9, value=('UK', 'DE'), type='membership')
    g.add_edge(4, 10, value=('US', 'BR'), type='membership')
    g.add_edge(5, 11, value=('UK', 'DE'), type='membership')
    g.add_edge(5, 12, value=('US', 'BR'), type='membership')
    g.add_edge(6, 13, value=('UK', 'DE'), type='membership')
    g.add_edge(6, 14, value=('US', 'BR'), type='membership')
    g.add_edge(0, 15)
    g.add_edge(1, 16)
    g.add_edge(2, 17)
    g.add_edge(3, 18)
    g.add_edge(4, 19)
    g.add_edge(5, 20)
    g.add_edge(6, 21)

    return g


@pytest.fixture
def graph_two_range_features():
    g = nx.DiGraph()

    g.add_node(0, split='segment', state={})
    g.add_node(1, split='age', state={'segment': 12345})
    g.add_node(2, split='age', state={'segment': 67890})
    g.add_node(3, split='user_hour', state={'segment': 12345, 'age': (0., 10.)})
    g.add_node(4, split='user_hour', state={'segment': 12345, 'age': (10., 20.)})
    g.add_node(5, split='user_hour', state={'segment': 67890, 'age': (0., 20.)})
    g.add_node(6, split='user_hour', state={'segment': 67890, 'age': (20., 40.)})
    g.add_node(7, is_leaf=True, output=0.10,
               state={'segment': 12345, 'age': (0, 10.),
                      'user_hour': (0., 12.)})
    g.add_node(8, is_leaf=True, output=0.20,
               state={'segment': 12345, 'age': (0, 10.),
                      'user_hour': (12., 100.)})
    g.add_node(9, is_leaf=True, output=0.10,
               state={'segment': 12345, 'age': (10., 20.),
                      'user_hour': (0., 12.)})
    g.add_node(10, is_leaf=True, output=0.20,
               state={'segment': 12345, 'age': (10., 20.),
                      'user_hour': (12., 100.)})
    g.add_node(11, is_leaf=True, output=0.10,
               state={'segment': 67890, 'age': (0., 20.),
                      'user_hour': (0., 12.)})
    g.add_node(12, is_leaf=True, output=0.20,
               state={'segment': 67890, 'age': (0., 20.),
                      'user_hour': (12., 100.)})
    g.add_node(13, is_leaf=True, output=0.10,
               state={'segment': 67890, 'age': (20., 40.),
                      'user_hour': (0., 12.)})
    g.add_node(14, is_leaf=True, output=0.20,
               state={'segment': 67890, 'age': (20., 40.),
                      'user_hour': (12., 100.)})
    g.add_node(15, is_default_leaf=True, output=0.05, state={})
    g.add_node(16, is_default_leaf=True, output=0.05, state={'segment': 12345})
    g.add_node(17, is_default_leaf=True, output=0.05, state={'segment': 67890})
    g.add_node(18, is_default_leaf=True, output=0.05,
               state={'segment': 12345, 'age': (0., 10.)})
    g.add_node(19, is_default_leaf=True, output=0.05,
               state={'segment': 12345, 'age': (10., 20.)})
    g.add_node(20, is_default_leaf=True, output=0.05,
               state={'segment': 67890, 'age': (0., 20.)})
    g.add_node(21, is_default_leaf=True, output=0.05,
               state={'segment': 67890, 'age': (20., 40.)})

    g.add_edge(0, 1, value=12345, type='assignment')
    g.add_edge(0, 2, value=67890, type='assignment')
    g.add_edge(1, 3, value=(0., 10.), type='range')
    g.add_edge(1, 4, value=(10., 20.), type='range')
    g.add_edge(2, 5, value=(0., 20.), type='range')
    g.add_edge(2, 6, value=(20., 40.), type='range')
    g.add_edge(3, 7, value=(0., 12.), type='range')
    g.add_edge(3, 8, value=(12., 100.), type='range')
    g.add_edge(4, 9, value=(0., 12.), type='range')
    g.add_edge(4, 10, value=(12., 100.), type='range')
    g.add_edge(5, 11, value=(0., 12.), type='range')
    g.add_edge(5, 12, value=(12., 100.), type='range')
    g.add_edge(6, 13, value=(0., 12.), type='range')
    g.add_edge(6, 14, value=(12., 100.), type='range')
    g.add_edge(0, 15)
    g.add_edge(1, 16)
    g.add_edge(2, 17)
    g.add_edge(3, 18)
    g.add_edge(4, 19)
    g.add_edge(5, 20)
    g.add_edge(6, 21)

    return g

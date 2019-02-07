# -*- coding: utf-8 -*-

from __future__ import (
    print_function, division, generators,
    absolute_import, unicode_literals
)

from collections import defaultdict
import math

import networkx as nx


class LogisticConverter:
    """
    Converter that translates a trained sklearn logistic regression classifier
    with one-hot-encoded, categorical features to a NetworkX graph that can
    be output to Bonsai with the `bonspy.BonsaiTree` converter.

    Attributes:
        features (list): List of feature names.
        vocabulary (dict): `vocabulary_` attribute of your trained `DictVectorizer`
            (http://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.DictVectorizer.html)
        weights (list): `coef_` attribute of your trained `SGDClassifier(loss='log', ...)`
            (http://scikit-learn.org/stable/modules/generated/sklearn.linear_model.SGDClassifier.html)
        intercept (float): `intercept_` attribute of your trained `SGDClassifier(loss='log', ...)`
        types (dict): Variable assignment type definitions: 'assignment', 'range', or membership.
        base_bid (float): Constant value that the output of the trained classifier
            is multiplied with to produce the output (bid).
        buckets (dict): Optional. Map for range features from bucket ID's to their bounds.
    """

    def __init__(self, features, vocabulary, weights, intercept, types, base_bid,
                 buckets=None):

        self.features = features
        self.vocabulary = vocabulary
        self.weights = weights
        self.intercept = intercept
        self.types = types
        self.base_bid = base_bid
        self.buckets = buckets or {}

        self.feature_map = self._get_feature_map()

        self.graph = self._create_graph()

    def _get_feature_map(self):
        buckets = self.buckets
        map_ = defaultdict(dict)
        for key, index in self.vocabulary.items():
            feature, value = key.split('=')
            range_ = buckets.get(feature, {}).get(value)

            if range_ is None:
                map_[feature][value] = index
            else:
                map_[feature][range_] = index

        return map_

    def _create_graph(self):
        g = self._create_graph_skeleton()
        g = self._populate_nodes(g)
        g = self._populate_edges(g)

        return g

    def _create_graph_skeleton(self):
        g = nx.DiGraph()

        features = [tuple()] + self.features
        queue = [tuple()]
        g.add_node(tuple(), weight=self.intercept)

        while len(queue) > 0:
            parent = queue.pop(0)
            index = len(parent)

            try:
                next_feature = features[index + 1]
            except IndexError:
                continue

            for value, weight_index in self.feature_map[next_feature].items():
                child = tuple(list(parent) + [value])
                g.add_edge(parent, child)
                g.node[child]['weight'] = self.weights[weight_index]
                queue.append(child)

            # add default leaf / else node:
            value = None
            child = tuple(list(parent) + [value])
            g.add_edge(parent, child)
            g.node[child]['weight'] = 0.

        return g

    def _populate_nodes(self, g):
        g = self._add_state(g)
        g = self._add_split(g)
        g = self._sum_weights(g)
        g = self._add_leaf_output(g)
        g = self._add_default_leaf_output(g)
        g = self._add_smart(g)

        return g

    def _add_smart(self, g):
        for node in g.nodes():
            #g.node[node]['is_smart'] = True
            g.node[node]['leaf_name']='blah'
            g.node[node]['value']=2

        return g

    def _populate_edges(self, g):
        g = self._add_value(g)
        g = self._add_type(g)

        return g

    def _add_state(self, g):
        for node in nx.dfs_preorder_nodes(g, tuple()):
            if node == tuple():
                state = {}
            elif node[-1] is None:
                parent = g.predecessors(node)[0]
                state = g.node[parent]['state']
            else:
                state = {feat: value for feat, value in zip(self.features, node)}

            g.node[node]['state'] = state

        return g

    def _add_split(self, g):
        for node in g.nodes():
            if node != tuple() and node[-1] is None:
                continue  # skip default leaf

            index = len(node)
            try:
                split = self.features[index]
                g.node[node]['split'] = split
            except IndexError:
                continue

        return g

    def _sum_weights(self, g):
        queue = [tuple()]
        g.node[tuple()]['sum'] = g.node[tuple()]['weight']

        while len(queue) > 0:
            parent = queue.pop(0)
            parent_sum = g.node[parent]['sum']

            children = g.successors(parent)
            queue += children

            for child in children:
                g.node[child]['sum'] = parent_sum + g.node[child]['weight']

        return g

    def _add_leaf_output(self, g):
        for node in g.nodes():
            if len(g.successors(node)) > 0 or node[-1] is None:
                continue

            g.node[node]['is_leaf'] = True
            g.node[node]['is_smart'] = True
            g.node[node]['output'] = self._sigmoid(g.node[node]['sum']) * self.base_bid

        return g

    def _add_default_leaf_output(self, g):
        for node in g.nodes():
            if len(g.successors(node)) > 0 or node[-1] is not None:
                continue

            g.node[node]['is_default_leaf'] = True
            g.node[node]['output'] = self._sigmoid(g.node[node]['sum']) * self.base_bid

        return g

    def _add_value(self, g):
        for parent, child in g.edges():
            value = child[-1]
            if value is None:
                continue

            g.edge[parent][child]['value'] = value

        return g

    def _add_type(self, g):
        for parent, child in g.edges():
            if child[-1] is None:
                continue

            feature = g.node[parent]['split']
            g.edge[parent][child]['type'] = self.types[feature]

        return g

    @staticmethod
    def _sigmoid(x):
        return 1. / (1. + math.exp(-x))

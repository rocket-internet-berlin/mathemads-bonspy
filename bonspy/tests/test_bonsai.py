# -*- coding: utf-8 -*-

from __future__ import (
    print_function, division, generators,
    absolute_import, unicode_literals
)

from bonspy import BonsaiTree


def test_switch_header(graph):
    tree = BonsaiTree(graph)
    text = tree.bonsai.replace('\t', '').split('\n')

    switch_header_nodes = [d for _, d in tree.nodes_iter(data=True) if d.get('split') == 'age']

    assert len(switch_header_nodes) == 2
    assert all([d.get('switch_header') is not None for d in switch_header_nodes])

    for row in text:
        if 'age' in row:
            assert row in ['switch segment[12345].age:', 'switch segment[67890].age:']


def test_switch_indent(graph):
    tree = BonsaiTree(graph)

    switch_header_nodes = [n for n, d in tree.nodes_iter(data=True) if d.get('split') == 'age']

    for node in switch_header_nodes:
        node_indent = tree.node[node]['indent'].count('\t')
        header_indent = tree.node[node]['switch_header'].count('\t')

        children_indent = [tree.node[c]['indent'].count('\t') for c in tree.successors_iter(node)]

        assert node_indent - 1 == header_indent
        assert all([header_indent + 2 == child_indent for child_indent in children_indent])


def test_compound_feature_presence(graph):
    tree = BonsaiTree(graph)

    text = tree.bonsai.replace('\t', '').split('\n')

    for row in text:
        if 'segment' in row and 'age' not in row:
            assert 'segment[12345]' in row or 'segment[67890]' in row


def test_two_range_features(graph_two_range_features):
    tree = BonsaiTree(graph_two_range_features)

    switch_nodes = [n for n, d in tree.nodes_iter(data=True) if d.get('switch_header')]

    for node in switch_nodes:
        parent = tree.predecessors(node)[0]

        header_indent = tree.node[node]['switch_header'].count('\t')
        parent_indent = tree.node[parent]['indent'].count('\t')

        assert header_indent - 1 == parent_indent

# -*- coding: utf-8 -*-

from __future__ import (
    print_function, division, generators,
    absolute_import, unicode_literals
)

from collections import deque

import networkx as nx


class BonsaiTree(nx.DiGraph):
    """
    A NetworkX DiGraph (directed graph) subclass that knows how to print
    itself out in the AppNexus Bonsai bidding tree language.

    See the readme for the expected graph structure:

    https://github.com/mathemads/bonspy

    The Bonsai text representation of this tree is stored in its `bonsai` attribute.
    """

    def __init__(self, graph=None):
        if graph is not None:
            super(BonsaiTree, self).__init__(graph)
            self._assign_indent()
            self._assign_condition()
            self._handle_switch_statements()
            self.bonsai = ''.join(self._tree_to_bonsai())
        else:
            super(BonsaiTree, self).__init__()

    def _get_root(self):
        for node in self.nodes():
            if len(self.predecessors(node)) == 0:
                return node

    def _assign_indent(self):
        root = self._get_root()
        queue = deque([root])

        self.node[root]['indent'] = ''

        while len(queue) > 0:
            node = queue.popleft()
            indent = self.node[node]['indent']

            next_nodes = self.successors(node)
            for node in next_nodes:
                self.node[node]['indent'] = indent + '\t'

            next_nodes = sorted(next_nodes, key=lambda x: self.node[x].get('is_default_leaf', False))

            queue.extend(next_nodes)

    def _assign_condition(self):
        root = self._get_root()
        queue = deque([root])

        while len(queue) > 0:
            node = queue.popleft()

            next_nodes = self.successors(node)
            next_nodes = sorted(next_nodes, key=lambda x: (self.node[x].get('is_default_leaf', False), x))

            for n_i, n in enumerate(next_nodes):
                if n_i == 0:
                    condition = 'if'
                elif n_i == len(next_nodes) - 1:
                    condition = 'else'
                else:
                    condition = 'elif'

                self.node[n]['condition'] = condition

            queue.extend(next_nodes)

    def _handle_switch_statements(self):
        self._assign_switch_headers()
        self._adapt_switch_indentation()

    def _assign_switch_headers(self):
        root = self._get_root()
        stack = deque(self._get_sorted_out_edges(root))

        while len(stack) > 0:
            parent, child = stack.popleft()

            next_edges = self._get_sorted_out_edges(child)
            stack.extendleft(next_edges[::-1])  # extendleft reverses order!

            type_ = self.edge[parent][child].get('type')

            if type_ == 'range':
                parent_indent = self.node[parent]['indent']
                feature = self.node[parent].get('split')

                if feature == 'age':
                    feature = 'segment[{}].age'.format(self.node[parent]['state']['segment'])

                header_indent = parent_indent
                header = header_indent + 'switch {}:'.format(feature)

                self.node[parent]['switch_header'] = header

    def _adapt_switch_indentation(self):
        switch_header_nodes = [n for n, d in self.nodes_iter(data=True) if d.get('switch_header')]
        stack = deque(switch_header_nodes)

        while len(stack) > 0:
            node = stack.popleft()
            next_nodes = self.successors(node)
            stack.extendleft(next_nodes[::-1])  # extendleft reverses order!

            self.node[node]['indent'] += '\t'

    def _get_sorted_out_edges(self, node):
        edges = self.out_edges_iter(node)
        keys = {'if': 0, 'elif': 1, 'else': 2}
        edges = sorted(edges, key=lambda x: keys[self.node[x[1]]['condition']])
        return edges

    def _get_output_text(self, node):
        out_text = ''
        if self.node[node].get('is_leaf') or self.node[node].get('is_default_leaf'):
            out_value = self.node[node]['output']
            out_indent = self.node[node]['indent']
            out_text = '{indent}{value:.4f}\n'.format(indent=out_indent, value=out_value)

        return out_text

    def _get_conditional_text(self, parent, child):
        indent = self.node[parent]['indent']
        feature = self.node[parent].get('split')
        value = self.edge[parent][child]['value']
        type_ = self.edge[parent][child]['type']
        conditional = self.node[child]['condition']

        pre_out = ''

        if feature == 'age':
            feature = 'segment[{}].age'.format(self.node[child]['state']['segment'])

        if type_ == 'range' and conditional == 'if':
            pre_out = self.node[parent]['switch_header'] + '\n'

        if type_ == 'range':
            left_bound, right_bound = value
            try:
                left_bound = int(left_bound)
            except TypeError:
                pass
            try:
                right_bound = int(right_bound)
            except TypeError:
                pass

            if (left_bound is not None) and (right_bound is not None):
                out = '{indent}case ({left_bound} .. {right_bound}):\n'.format(
                    indent=indent,
                    left_bound=left_bound,
                    right_bound=right_bound
                )
            elif (left_bound is not None) and (right_bound is None):
                out = '{indent}case ({left_bound}):\n'.format(
                    indent=indent,
                    left_bound=left_bound
                )
            elif (left_bound is None) and (right_bound is not None):
                out = '{indent}case ({right_bound}):\n'.format(
                    indent=indent,
                    right_bound=right_bound
                )
            else:
                raise ValueError('Value cannot be (None,None)')

        elif type_ == 'membership':
            value = tuple(value)
            if isinstance(value[0], str):
                value = '(\"{}\")'.format('\",\"'.join(value))
            out = '{indent}{conditional} {feature} in {value}:\n'.format(indent=indent,
                                                                         conditional=conditional,
                                                                         feature=feature,
                                                                         value=value)
        elif type_ == 'assignment':
            comparison = ' ' if feature in ['segment'] else '='
            value = '"{}"'.format(value) if not self._is_numerical(value) else value

            out = '{indent}{conditional} {feature}{comparison}{value}:\n'.format(indent=indent,
                                                                                 conditional=conditional,
                                                                                 feature=feature,
                                                                                 comparison=comparison,
                                                                                 value=value)

        return pre_out + out

    def _get_default_conditional_text(self, parent, child):
        type_ = self._get_sibling_type(parent, child)
        indent = self.node[parent]['indent']

        conditional = 'default' if type_ == 'range' else 'else'

        return '{indent}{conditional}:\n'.format(indent=indent, conditional=conditional)

    def _get_edge_siblings(self, parent, child):
        this_edge = (parent, child)
        sibling_edges = [edge for edge in self.out_edges(parent) if edge != this_edge]

        return sibling_edges

    def _get_sibling_type(self, parent, child):
        sibling_edges = self._get_edge_siblings(parent, child)
        sibling_types = [self.edge[parent][child]['type'] for parent, child in sibling_edges]

        return sibling_types[0]

    def _tree_to_bonsai(self):
        root = self._get_root()
        stack = deque(self._get_sorted_out_edges(root))

        while len(stack) > 0:
            parent, child = stack.popleft()

            next_edges = self._get_sorted_out_edges(child)
            stack.extendleft(next_edges[::-1])  # extendleft reverses order!

            if not self.node[child].get('is_default_leaf', False):
                conditional_text = self._get_conditional_text(parent, child)
            elif self.node[child].get('is_default_leaf', False):
                conditional_text = self._get_default_conditional_text(parent, child)

            out_text = self._get_output_text(child)

            yield conditional_text + out_text

    @staticmethod
    def _is_numerical(x):
        try:
            _ = int(x)
            _ = float(x)
            return True
        except ValueError:
            return False

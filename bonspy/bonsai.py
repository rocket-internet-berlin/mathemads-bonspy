# -*- coding: utf-8 -*-

from __future__ import (
    print_function, division, generators,
    absolute_import, unicode_literals
)

import networkx as nx


class BonsaiTree(nx.DiGraph):
    def __init__(self, graph=None):
        if graph is not None:
            super(BonsaiTree, self).__init__(graph)
            self._assign_indent()
            self._assign_condition()
            self.bonsai = ''.join(self._tree_to_bonsai())
        else:
            super(BonsaiTree, self).__init__()

    def _get_root(self):
        for node in self.nodes():
            if len(self.predecessors(node)) == 0:
                return node

    def _assign_indent(self):
        root = self._get_root()
        queue = [root]

        self.node[root]['indent'] = ''

        while len(queue) > 0:
            node = queue.pop(0)
            indent = self.node[node]['indent']

            next_nodes = self.successors(node)
            subgraph = self.subgraph(next_nodes)
            nx.set_node_attributes(subgraph, 'indent', indent+'\t')
            next_nodes = sorted(next_nodes, key=lambda x: self.node[x].get('is_default_leaf', False))

            queue += next_nodes

    def _assign_condition(self):
        root = self._get_root()
        queue = [root]

        while len(queue) > 0:
            node = queue.pop(0)

            next_nodes = self.successors(node)
            next_nodes = sorted(next_nodes, key=lambda x: self.node[x].get('is_default_leaf', False))

            for n_i, n in enumerate(next_nodes):
                if n_i == 0:
                    condition = 'if'
                elif n_i == len(next_nodes) - 1:
                    condition = 'else'
                else:
                    condition = 'elif'

                self.node[n]['condition'] = condition

            queue += next_nodes

    def _get_sorted_out_edges(self, node):
        edges = self.out_edges(node)
        edges = sorted(edges, key=lambda x: ['if', 'elif', 'else'].index(self.node[x[1]]['condition']))

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

        if feature == 'age':
            feature = 'segment {} age'.format(self.node[child]['state']['segment'])

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
                out = '{indent}{conditional} {feature} range {value}:\n'.format(indent=indent,
                                                                                conditional=conditional,
                                                                                feature=feature,
                                                                                value=value)
            elif (left_bound is None) and (right_bound is not None):
                out = '{indent}{conditional} {feature} <= {value}:\n'.format(indent=indent,
                                                                           conditional=conditional,
                                                                           feature=feature,
                                                                           value=right_bound)
            elif (left_bound is not None) and (right_bound is None):
                out = '{indent}{conditional} {feature} > {value}:\n'.format(indent=indent,
                                                                          conditional=conditional,
                                                                          feature=feature,
                                                                          value=left_bound)
            else:
                raise ValueError('Value cannot be (None,None)')

        elif type_ == 'membership':
            value = tuple(value)
            out = '{indent}{conditional} {feature} in {value}:\n'.format(indent=indent,
                                                                         conditional=conditional,
                                                                         feature=feature,
                                                                         value=value)
        elif type_ == 'assignment':
            comparison = ' ' if feature in ['segment'] else '='
            value = '"{}"'.format(value) if not self.is_numerical(value) else value

            out = '{indent}{conditional} {feature}{comparison}{value}:\n'.format(indent=indent,
                                                                                 conditional=conditional,
                                                                                 feature=feature,
                                                                                 comparison=comparison,
                                                                                 value=value)

        return out

    def _get_default_conditional_text(self, parent):
        indent = self.node[parent]['indent']
        return '{indent}else:\n'.format(indent=indent)

    def _tree_to_bonsai(self):
        root = self._get_root()
        stack = self._get_sorted_out_edges(root)

        while len(stack) > 0:
            parent, child = stack.pop(0)

            next_edges = self._get_sorted_out_edges(child)
            stack = next_edges + stack

            if not self.node[child].get('is_default_leaf'):
                conditional_text = self._get_conditional_text(parent, child)
            elif self.node[child].get('is_default_leaf'):
                conditional_text = self._get_default_conditional_text(parent)

            out_text = self._get_output_text(child)

            yield conditional_text + out_text

    @staticmethod
    def is_numerical(x):
        try:
            _ = int(x)
            _ = float(x)
            return True
        except ValueError:
            return False

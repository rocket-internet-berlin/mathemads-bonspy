# -*- coding: utf-8 -*-

from __future__ import (
    print_function, division, generators,
    absolute_import, unicode_literals
)

import base64

from collections import deque, OrderedDict
from functools import cmp_to_key

import networkx as nx

from bonspy.features import compound_features, get_validated, objects
from bonspy.utils import compare_vectors, is_absent_value

try:
    basestring
except NameError:
    basestring = str

RANGE_EPSILON = 1


class BonsaiTree(nx.DiGraph):
    """
    A NetworkX DiGraph (directed graph) subclass that knows how to print
    itself out in the AppNexus Bonsai bidding tree language.

    See the readme for the expected graph structure:

    https://github.com/markovianhq/bonspy

    The Bonsai text representation of this tree is stored in its `bonsai` attribute.

    :param graph: (optional) NetworkX graph to be exported to Bonsai.
    :param feature_order: (optional), iterable required when a parent node is split on more than one feature.
        Splitting the parent node on more than one feature is indicated through its `split` attribute
        set to an OrderedDict object [(child id, feature the parent node is split on]).
        The list `feature_order` then provides the order these different features appear in the
        Bonsai language output.
    :param feature_value_order: (optional), Similar to `feature_order` but a dictionary of lists
        of the form {feature: [feature value 1, feature value 2, ...]}.
    :param absence_values: (optional), Dictionary feature name -> iterable of values whose communal absence
        signals absence of the respective feature.
    :param slice_features: (optional) iterable, features to be used for slicing. The private _slice_graph method slices
        out the part of the graph where the "slice_features" have a value that is equal to the value of the
        "slice_feature_values" dict.
        Moreover, it splices out the levels where the "splice_features" are split.
        The "slice" method assumes that a node never splits on the "slice_features" together with another feature.
    :param slice_feature_values: (optional) dict, slice_feature -> feature values to not be sliced off the graph.
    """

    def __init__(self, graph=None, feature_order=(), feature_value_order={}, absence_values=None,
                 slice_features=None, slice_feature_values=(), **kwargs):
        if graph is not None:
            super(BonsaiTree, self).__init__(graph)
            self.feature_order = self._convert_to_dict(feature_order)
            self.feature_value_order = self._get_feature_value_order(feature_value_order)
            self.absence_values = absence_values or {}
            self.slice_features = slice_features or ()
            self.slice_feature_values = slice_feature_values or {}
            for key, value in kwargs.items():
                setattr(self, key, value)
            self._transform_splits()
            self._slice_graph()
            # self._replace_absent_values()
            # self._remove_missing_compound_features()
            self._validate_feature_values()
            self._assign_indent()
            self._assign_condition()
            self._handle_switch_statements()
            self.bonsai = ''.join(self._tree_to_bonsai())
        else:
            super(BonsaiTree, self).__init__(**kwargs)

    @staticmethod
    def _convert_to_dict(feature_order):
        for index, f in enumerate(feature_order):
            if isinstance(f, list):
                feature_order[index] = tuple(f)
        feature_order = {f: index for index, f in enumerate(feature_order)}
        return feature_order

    def _get_feature_value_order(self, feature_value_order):
        return {feature: self._convert_to_dict(list_) for feature, list_ in feature_value_order.items()}

    @property
    def bonsai_encoded(self):
        return base64.b64encode(self.bonsai.encode('ascii')).decode()

    def _transform_splits(self):
        root_id = self._get_root()

        for node_id in self.bfs_nodes(root_id):
            try:
                split = self.node[node_id]['split']
            except KeyError:
                continue

            if not isinstance(split, dict):
                self.node[node_id]['split'] = OrderedDict()

                for child_id in self.successors_iter(node_id):
                    if not self.node[child_id].get('is_default_leaf', self.node[child_id].get('is_default_node')):
                        self.node[node_id]['split'][child_id] = split

    def _slice_graph(self):
        for slice_feature in self.slice_features:
            self._slice_feature_out_of_graph(slice_feature)

    def _slice_feature_out_of_graph(self, slice_feature):
        root_id = self._get_root()

        queue = deque([root_id])
        while queue:
            node_id = queue.popleft()
            if self.node[node_id].get('is_default_leaf'):
                continue
            split_contains_slice_feature = self._split_contains_slice_feature(node_id, slice_feature)

            if not split_contains_slice_feature:
                next_nodes = self.successors(node_id)
                queue.extend(next_nodes)
            else:
                queue = self._update_sub_graph(node_id, slice_feature, queue)

    def _split_contains_slice_feature(self, node_id, slice_feature):
        try:
            split = self.node[node_id]['split']
            return slice_feature in split.values()
        except KeyError:  # default leaf or leaf
            return False

    def _update_sub_graph(self, node_id, slice_feature, queue):
        self._prune_unwanted_children(node_id, slice_feature)

        default_child = next((n for n in self.successors_iter(node_id) if self.node[n].get('is_default_leaf')))

        try:
            normal_child = self._get_normal_child(node_id, slice_feature)
            other_children = [n for n in self.successors_iter(node_id) if n not in {normal_child, default_child}]
            queue.extend(other_children)

            if self.node[normal_child].get('is_leaf'):
                self._remove_leaves_and_update_parent_default(
                    node_id, slice_feature, normal_child, default_child, other_children
                )
            else:
                self._splice_out_node(normal_child, slice_feature, slicing=True)

        except StopIteration:  # slice feature value not present in subtree
            other_children = [n for n in self.successors_iter(node_id) if n != default_child]
            if other_children:
                queue.extend(other_children)
            else:
                self._cut_single_default_child(node_id, default_child)

        return queue

    def _prune_unwanted_children(self, node_id, slice_feature):
        prunable_children = [
            n for n in self.successors_iter(node_id) if not self.node[n].get('is_default_leaf') and
                                                        slice_feature in self.node[n]['state'] and
                                                        self.node[n]['state'].get(slice_feature) !=
                                                        self.slice_feature_values[slice_feature]
        ]
        for prunable_child in prunable_children:
            if self.node[node_id].get('split'):
                del self.node[node_id]['split'][prunable_child]
            self._remove_sub_graph(prunable_child)

    def _remove_sub_graph(self, node):
        queue = deque([node])
        while queue:
            current_node = queue.popleft()
            next_nodes = self.successors(current_node)
            self.remove_node(current_node)
            queue.extend(next_nodes)

    def _get_normal_child(self, node_id, slice_feature):
        return next((
            n for n in self.successors_iter(node_id) if not self.node[n].get('is_default_leaf') and
                                                        slice_feature in self.node[n]['state']
        ))

    def _remove_leaves_and_update_parent_default(self, node_id, slice_feature, normal_child,
                                                 default_child, other_children):
        if not other_children:
            del self.node[node_id]['split']
            self._remove_feature_from_state(node_id, slice_feature)
            self.node[node_id] = self.node[normal_child].copy()

            self.remove_edge(node_id, default_child)
            self.remove_node(default_child)
        else:
            del self.node[node_id]['split'][normal_child]
            self._remove_feature_from_state(node_id, slice_feature)
            self.node[default_child] = self.node[normal_child].copy()
            del self.node[default_child]['is_leaf']
            self.node[default_child]['is_default_leaf'] = True

        self.remove_edge(node_id, normal_child)
        self.remove_node(normal_child)

    def _remove_feature_from_state(self, source, feature):
        for node_id in self.bfs_nodes(source):
            try:
                del self.node[node_id]['state'][feature]
            except KeyError:  # node_id is default leaf
                pass

    def _splice_out_node(self, source, feature, slicing=False):
        self._remove_feature_from_state(source, feature)
        self._skip_node(source, slicing)

    def _skip_node(self, node_id, slicing):
        parent_id = next(iter(self.predecessors_iter(node_id)))

        if slicing:
            self._skip_node_slicing(node_id, parent_id)
        else:
            self._skip_node_non_slicing(node_id, parent_id)

        self.remove_edge(parent_id, node_id)
        self.remove_node(node_id)

    def _cut_single_default_child(self, parent_id, default_child):
        if not self.node[parent_id].get('is_default_node'):
            self.node[parent_id] = self.node[default_child]
            del self.node[parent_id]['is_default_leaf']
            self.node[parent_id]['is_leaf'] = True
        else:
            self.node[parent_id] = self.node[default_child]
        self.remove_node(default_child)

    def _replace_absent_values(self):
        root_id = self._get_root()

        for parent_id, child_id in nx.bfs_edges(self, root_id):
            try:
                feature = next(reversed(self.node[child_id]['state']))
            except StopIteration:
                continue  # node_id is root_id

            value = self.node[child_id]['state'][feature]

            if self.absence_values.get(feature) and value is None:
                self._replace_absent_value_split(parent_id, child_id, feature)
                self._replace_absent_value_edge(parent_id, child_id, feature)
                self._replace_absent_value_state(child_id, feature)

    def _replace_absent_value_split(self, parent_id, child_id, feature):
        values = self.absence_values[feature]
        self.node[parent_id]['split'][child_id] = tuple(feature for value in values)

    def _replace_absent_value_edge(self, parent_id, child_id, feature):
        values = self.absence_values[feature]

        self.edge[parent_id][child_id]['value'] = values
        self.edge[parent_id][child_id]['type'] = ['assignment' for value in values]
        self.edge[parent_id][child_id]['is_negated'] = [True for value in values]

    def _replace_absent_value_state(self, source, feature):
        absent_values = self.absence_values[feature]

        for node_id in self.bfs_nodes(source):
            state = self.node[node_id]['state']
            absent_feature = tuple(feature for value in absent_values)

            state = OrderedDict(
                [(k, v) if k != feature else (absent_feature, absent_values) for k, v in state.items()]
            )

            self.node[node_id]['state'] = state

    def _remove_missing_compound_features(self):
        root_id = self._get_root()

        for node_id in self.bfs_nodes(root_id):
            try:
                feature = next(reversed(self.node[node_id]['state']))
            except StopIteration:
                continue  # node_id is root_id

            value = self.node[node_id]['state'][feature]

            is_compound_attribute = self._is_compound_attribute(feature)

            if is_compound_attribute and value is None:
                if self.node[node_id].get('is_leaf'):
                    self.remove_node(node_id)
                else:
                    self._splice_out_node(node_id, feature)

        self._remove_disconnected_nodes()
        self._prune_redundant_default_leaves()

    def bfs_nodes(self, source):
        queue = deque([source])

        while queue:
            node_id = queue.popleft()
            child_ids = self.successors_iter(node_id)
            queue.extend(child_ids)

            yield node_id

    def _is_compound_attribute(self, feature):
        if '.' in feature:
            return True
        else:
            return False

    def _skip_node_non_slicing(self, node_id, parent_id):
        for _, child_id, edge_data in self.edges(nbunch=(node_id,), data=True):
            if self.node[child_id].get('is_default_leaf'):
                continue
            else:
                self.add_edge(parent_id, child_id, attr_dict=edge_data)
                self.remove_edge(node_id, child_id)
        del self.node[parent_id]['split'][node_id]
        self._update_split(parent_id, node_id)

    def _skip_node_slicing(self, node_id, parent_id):
        for _, child_id, edge_data in self.out_edges(nbunch=(node_id,), data=True):
            if self.node[child_id].get('is_default_leaf'):
                self._update_parent_default_leaf(parent_id, child_id)
                del self.node[child_id]
            else:
                self.add_edge(parent_id, child_id, attr_dict=edge_data)
                self._update_split(parent_id, node_id, child_id=child_id)
                self.remove_edge(node_id, child_id)
        del self.node[parent_id]['split'][node_id]

    def _update_parent_default_leaf(self, parent_id, new_default):
        current_parent_default = next(iter(
            [n for n in self.successors(parent_id) if self.node[n].get('is_default_leaf')]
        ))
        self.node[current_parent_default] = self.node[new_default].copy()

    def _update_split(self, parent_id, node_id, child_id=None):
        node_split = self.node[node_id]['split']
        if child_id:
            self.node[parent_id]['split'][child_id] = node_split[child_id]
        else:
            self.node[parent_id]['split'].update(node_split)

    def _remove_disconnected_nodes(self):
        node_ids = self._get_disconnected_nodes()

        while node_ids:
            self.remove_nodes_from(node_ids)

            node_ids = self._get_disconnected_nodes()

    def _get_disconnected_nodes(self):
        root = self._get_root()
        node_ids = [n for n in self.nodes_iter() if not self.successors(n) and not self.predecessors(n) and n != root]
        return node_ids

    def _prune_redundant_default_leaves(self):
        only_child_default_leaves = self._get_only_child_default_leaves()
        queue = deque(only_child_default_leaves)

        while queue:
            node_id = queue.popleft()
            parent_id = next(iter(self.predecessors_iter(node_id)))

            if not self.node[parent_id].get('is_default_node'):
                self.node[parent_id] = self.node[node_id]
                del self.node[parent_id]['is_default_leaf']
                self.node[parent_id]['is_leaf'] = True
            else:
                self.node[parent_id] = self.node[node_id]
                queue.extend(parent_id)

            self.remove_node(node_id)

    def _get_only_child_default_leaves(self):
        default_edges = ((p, c) for (p, c) in self.edges_iter() if self.node[c].get('is_default_leaf'))
        only_child_default_leaves = (c for (p, c) in default_edges if self._has_only_one_child(p))
        return only_child_default_leaves

    def _has_only_one_child(self, parent_id):
        return len(self.successors(parent_id)) == 1

    def _validate_feature_values(self):
        self._validate_node_states()
        self._validate_edge_values()

    def _validate_node_states(self):
        for node, data in self.nodes_iter(data=True):
            for feature, value in data.get('state', {}).items():
                self.node[node]['state'][feature] = get_validated(feature, value)

    def _validate_edge_values(self):
        for parent, child, data in self.edges_iter(data=True):
            feature = self.node[parent]['split']
            if isinstance(feature, dict):
                feature = feature.get(child)
            try:
                value = data['value']
                self.edge[parent][child]['value'] = get_validated(feature, value)
            except KeyError:
                pass  # edge has no value attribute, nothing to validate

    def _get_root(self):
        for node in self.nodes():
            if len(self.predecessors(node)) == 0:
                return node

    def _assign_indent(self):
        root = self._get_root()
        queue = deque([root])

        self.node[root]['indent'] = ''

        while queue:
            node = queue.popleft()
            indent = self.node[node]['indent']

            next_nodes = self.successors(node)
            for node in next_nodes:
                self.node[node]['indent'] = indent + '\t'

            next_nodes = sorted(next_nodes, key=self._sort_key)

            queue.extend(next_nodes)

    @property
    def _sort_key(self):
        comparison_function = self._get_comparison_function()
        return cmp_to_key(comparison_function)

    def _get_comparison_function(self):
        _get_default_extended_vector = self._get_default_extended_vector

        def compare_nodes(x, y):
            x_ = _get_default_extended_vector(x)
            y_ = _get_default_extended_vector(y)

            return compare_vectors(x_, y_)

        return compare_nodes

    def _get_default_extended_vector(self, x):
        vec = [self.node[x].get('is_default_leaf', False), self.node[x].get('is_default_node', False)]
        vec += self._get_sorted_values(x)

        return vec

    def _get_sorted_values(self, x):
        values = []

        for feature, value in self.node[x]['state'].items():
            feature_key = self._get_feature_order_key(feature)
            value_key = self._get_value_order_key(feature, value)
            values.append(feature_key)
            values.append(value_key)

        return values

    def _get_feature_order_key(self, feature):
        feature_order = self.feature_order
        feature_order_key = self._get_order_key(dict_=feature_order, key=feature)
        return feature_order_key

    def _get_value_order_key(self, feature, value):
        value_order = self.feature_value_order.get(feature, {})
        value_order_key = self._get_order_key(dict_=value_order, key=value)
        return value_order_key

    @staticmethod
    def _get_order_key(dict_, key):
        order_key = 0
        if not dict_ == {}:
            try:
                order_key = dict_[key]
            except KeyError:
                order_key = max(dict_.values()) + 1

        return order_key

    def _assign_condition(self):
        root = self._get_root()
        queue = deque([root])

        while queue:
            node = queue.popleft()

            next_nodes = self.successors(node)
            next_nodes = sorted(next_nodes, key=self._sort_key)

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
        self._adapt_switch_header_indentation()

    def _assign_switch_headers(self):
        root = self._get_root()
        stack = deque(self._get_sorted_out_edges(root))

        while stack:
            parent, child = stack.popleft()

            next_edges = self._get_sorted_out_edges(child)
            stack.extendleft(next_edges[::-1])  # extendleft reverses order!

            type_ = self.edge[parent][child].get('type')

            if type_ == 'range' and len(set(self.node[parent]['split'].values())) == 1:
                feature = self._get_feature(parent, child, state_node=parent)

                header = 'switch {}:'.format(feature)  # appropriate indentation added later

                # self.node[parent]['switch_header'] = header
                self.node[parent]['switch_header'] = ''

    def _adapt_switch_indentation(self):
        switch_header_nodes = [n for n, d in self.nodes_iter(data=True) if d.get('switch_header')]
        stack = deque(switch_header_nodes)

        while stack:
            node = stack.popleft()
            next_nodes = self.successors(node)
            stack.extendleft(next_nodes[::-1])  # extendleft reverses order!

            self.node[node]['indent'] += '\t'

    def _adapt_switch_header_indentation(self):
        for node, data in self.nodes_iter(data=True):
            if data.get('switch_header'):
                try:
                    parent = self.predecessors(node)[0]
                except IndexError:  # node is root
                    continue
                parent_indent = self.node[parent]['indent']
                switch_header = self.node[node]['switch_header']
                self.node[node]['switch_header'] = parent_indent + '\t' + switch_header

    def _get_sorted_out_edges(self, node):
        edges = self.out_edges_iter(node)
        edges = sorted(edges, key=lambda x: self._sort_key(x[1]))
        return edges

    def _get_output_text(self, node):
        out_text = ''
        if self.node[node].get('is_leaf') or self.node[node].get('is_default_leaf'):
            if not self.node[node].get('is_smart'):
                out_text = self._get_leaf_output(node)
            else:
                name_line = self._get_name_line(node)
                value_line = self._get_value_line(node)
                out_text = name_line + value_line

        return out_text

    def _get_leaf_output(self, node):
        out_indent = self.node[node]['indent']
        out_value = self.node[node]['output']
        out_text = '{indent}{value:.4f}\n'.format(indent=out_indent, value=out_value)

        return out_text

    def _get_name_line(self, node):
        try:
            out_indent = self.node[node]['indent']
            out_name = self.node[node]['leaf_name']
            name_line = '{indent}leaf_name: "{name}"\n'.format(indent=out_indent, name=out_name)
        except KeyError:
            name_line = ''  # leaf_name is optional

        return name_line

    def _get_value_line(self, node):
        out_indent = self.node[node]['indent']
        out_value = self._get_smart_leaf_output_value(node)
        value_line = '{indent}{value}\n'.format(indent=out_indent, value=out_value)

        return value_line

    def _get_smart_leaf_output_value(self, node):
        if isinstance(self.node[node].get('value'), (int, float)):
            out_value = self._get_smart_leaf_output_bid_syntax(node)
        else:
            out_value = self._get_smart_leaf_output_compute_syntax(node)

        return out_value

    def _get_smart_leaf_output_bid_syntax(self, node):
        bid_value = self.node[node]['value']
        if round(bid_value, 4) <= 0:
            out_value = 'value: no_bid'
        else:
            out_value = 'value: {bid_value:.4f}'.format(bid_value=bid_value)
        return out_value

    def _get_smart_leaf_output_compute_syntax(self, node):
        input_field = self.node[node]['input_field']
        multiplier = self._get_compute_input(node, 'multiplier')
        offset = self._get_compute_input(node, 'offset')
        min_value = self._get_compute_input(node, 'min_value')
        max_value = self._get_compute_input(node, 'max_value')

        return 'value: compute({input_field}, {multiplier}, {offset}, {min_value}, {max_value})'.format(
            input_field=input_field,
            multiplier=multiplier,
            offset=offset,
            min_value=min_value,
            max_value=max_value
        )

    def _get_compute_input(self, node, parameter):
        node_dict = self.node[node]
        try:
            value = round(node_dict[parameter], 4)
        except KeyError:
            value = '_'
        return value

    def _get_conditional_text(self, parent, child):
        pre_out = self._get_pre_out_statement(parent, child)
        out = self._get_out_statement(parent, child)

        return pre_out + out

    def _get_pre_out_statement(self, parent, child):
        type_ = self.edge[parent][child].get('type')
        conditional = self.node[child]['condition']

        pre_out = ''

        if type_ == 'range' and conditional == 'if' and len(set(self.node[parent]['split'].values())) == 1:
            pre_out = self.node[parent]['switch_header'] + '\n'

        return pre_out

    def _get_out_statement(self, parent, child):
        indent = self.node[parent]['indent']
        value = self.edge[parent][child].get('value')
        type_ = self.edge[parent][child].get('type')
        conditional = self.node[child]['condition']
        feature = self._get_feature(parent, child, state_node=child)
        switch_header = self.node[parent].get('switch_header')
        join_statement = self.edge[parent][child].get('join_statement', False)
        is_negated = self._get_is_negated(parent, child, feature)

        if switch_header and type_ == 'range':
            out = self._get_switch_header_range_statement(indent, value)
        else:
            out = '{indent}{conditional}'
            if type_ is not None and all(isinstance(x, (list, tuple)) for x in (feature, type_)):
                out += ' ' + join_statement + ' ' + ', '.join(
                    self._get_if_conditional(v, t, f, i, join_statement=join_statement) for v, t, f, i
                    in zip(value, type_, feature, is_negated)
                )
            elif type_ is not None and not any(isinstance(x, (list, tuple)) for x in (feature, type_)):
                out += ' ' + self._get_if_conditional(value, type_, feature, is_negated, join_statement=join_statement)
            elif type_ is None:
                out += ''
            else:
                raise ValueError(
                    'Unable to deduce if-conditional '
                    'for feature "{}" and type "{}".'.format(
                        feature, type_
                    )
                )
            out += ':\n'

            out = out.format(indent=indent, conditional=conditional)

        return out

    def _get_feature(self, parent, child, state_node):
        feature = self.node[parent].get('split')
        if isinstance(feature, dict):
            try:
                feature = feature[child]
            except KeyError:
                assert self.node[child].get('is_default_leaf', self.node[child].get('is_default_node', False))
        if isinstance(feature, (list, tuple)):
            return self._get_formatted_multidimensional_compound_feature(feature, state_node)
        elif '.' in feature:
            return self._get_formatted_compound_feature(feature, state_node)
        else:
            return feature

    def _get_is_negated(self, parent, child, feature):
        try:
            return self.edge[parent][child]['is_negated']
        except KeyError:
            if isinstance(feature, (list, tuple)):
                return len(feature) * (False,)
            else:
                return False

    def _get_formatted_multidimensional_compound_feature(self, feature, state_node):
        attribute_indices = self._get_attribute_indices(feature)
        feature = list(feature)
        for i in attribute_indices:
            feature[i] = self._get_formatted_compound_feature(feature[i], state_node)

        return tuple(feature)

    @staticmethod
    def _get_attribute_indices(feature):
        return [feature.index(f) for f in feature if '.' in f and f.split('.')[0] in feature]

    def _get_formatted_compound_feature(self, feature, state_node):
        object_, attribute = feature.split('.')
        try:
            value = self.node[state_node]['state'][object_]
        except KeyError:
            value = self.__getattribute__(object_)
        feature = '{feature}[{value}].{attribute}'.format(
            feature=object_,
            value=value,
            attribute=attribute
        )

        return feature

    @staticmethod
    def _get_switch_header_range_statement(indent, value):
        if value is None:
            return ''

        left_bound, right_bound = value
        try:
            left_bound = round(left_bound, 4)
            _ = int(left_bound)  # NOQA
        except (TypeError, OverflowError):
            left_bound = ''
        try:
            right_bound = round(right_bound, 4)
            _ = int(right_bound)  # NOQA
        except (TypeError, OverflowError):
            right_bound = ''

        if left_bound == right_bound == '':
            raise ValueError(
                'Value "{}" not reasonable as value of a range feature.'.format(
                    value
                )
            )

        out = '{indent}case ({left_bound} .. {right_bound}):\n'.format(
            indent=indent,
            left_bound=left_bound,
            right_bound=right_bound
        )

        return out

    def _get_if_conditional(self, value, type_, feature, is_negated, join_statement=None):

        if type_ not in {'range', 'membership', 'assignment', 'association'}:
            raise ValueError(
                'Unable to deduce conditional statement for type "{}".'.format(type_)
            )

        if is_absent_value(value):
            out = self._get_if_conditional_missing_value(type_, feature)
        else:
            out = self._get_if_conditional_present_value(value, type_, feature, join_statement=join_statement)

        if is_negated:
            out = 'not {}'.format(out)

        return out

    def _get_if_conditional_missing_value(self, type_, feature):
        out = '{feature} absent'.format(feature=feature)

        return out

    def _get_if_conditional_present_value(self, value, type_, feature, join_statement=None):
        if type_ == 'range':
            out = self._get_range_statement(value, feature, join_statement=join_statement)
        elif type_ == 'membership':
            value = tuple(value)
            if isinstance(value[0], basestring):
                value = '(\"{}\")'.format('\",\"'.join(value))
            out = '{feature} in {value}'.format(
                feature=feature,
                value=value
            )
        elif type_ == 'assignment':
            comparison = '='
            value = '"{}"'.format(value) if not self._is_numerical(value) else value

            if feature.split('.')[0] not in compound_features:
                out = '{feature}{comparison}{value}'.format(
                    feature=feature,
                    comparison=comparison,
                    value=value
                )
            elif feature in compound_features:
                out = '{feature}[{value}]'.format(
                    feature=feature,
                    value=value
                )
            else:
                object_, attribute = feature.split('.')
                out = '{feature}[{value}].{attribute}'.format(
                    feature=object_,
                    value=value,
                    attribute=attribute
                )
        elif type_ == 'association':
            out = '{feature}: {value}'.format(
                feature=feature,
                value=value
            )
        return out

    def _get_range_statement(self, value, feature, join_statement=None):
        left_bound, right_bound = value

        if self._is_finite(left_bound) and self._is_finite(right_bound):
            left_bound = round(left_bound, 4)
            right_bound = round(right_bound, 4)
            out = self._get_range_output_for_finite_boundary_points(
                left_bound=left_bound, right_bound=right_bound, feature=feature, join_statement=join_statement
            )
        elif not self._is_finite(left_bound) and self._is_finite(right_bound):
            right_bound = round(right_bound, 4)
            out = '{feature} <= {right_bound}'.format(feature=feature, right_bound=right_bound)
        elif self._is_finite(left_bound) and not self._is_finite(right_bound):
            left_bound = round(left_bound, 4)
            join = self._get_join(join_statement)
            out = '{join}{feature} >= {left_bound}'.format(join=join, feature=feature, left_bound=left_bound)
        else:
            raise ValueError(
                'Value "{}" not reasonable as value of a range feature.'.format(
                    value
                )
            )

        return out

    def _get_range_output_for_finite_boundary_points(self, left_bound, right_bound, feature, join_statement=None):
        if left_bound < right_bound and all([obj not in feature for obj in objects]):
            out = '{feature} range ({left_bound}, {right_bound})'.format(
                feature=feature,
                left_bound=left_bound,
                right_bound=right_bound
            )
        elif left_bound < right_bound and any([obj in feature for obj in objects]):
            join = self._get_join(join_statement)
            out = '{join}{feature} >= {left_bound}, {feature} <= {right_bound}'.format(
                join=join,
                feature=feature,
                left_bound=left_bound,
                right_bound=right_bound
            )
        else:
            out = '{feature} = {left_bound}'.format(
                feature=feature,
                left_bound=left_bound
            )
        return out

    @staticmethod
    def _get_join(join_statement):
        if join_statement == 'any':
            raise ValueError(
                'Cannot combine object feature "range" with "any" join_statement.'
                'Object features are: {}.'.format(objects)
            )
        # join = '' if join_statement else 'every '
        join = 'every ' if join_statement else ''
        return join

    def _get_default_conditional_text(self, parent, child):
        type_ = self._get_sibling_type(parent, child)
        indent = self.node[parent]['indent']

        conditional = 'default' if type_ == 'range' and len(set(self.node[parent]['split'].values())) == 1 else 'else'
        conditional = 'else'

        return '{indent}{conditional}:\n'.format(indent=indent, conditional=conditional)

    def _get_edge_siblings(self, parent, child):
        this_edge = (parent, child)
        sibling_edges = [edge for edge in self.out_edges(parent) if edge != this_edge]

        return sibling_edges

    def _get_sibling_type(self, parent, child):
        sibling_edges = self._get_edge_siblings(parent, child)
        sibling_types = [self.edge[sibling_parent][sibling_child]['type']
                         for sibling_parent, sibling_child in sibling_edges]

        return sibling_types[0]

    def _tree_to_bonsai(self):
        root = self._get_root()
        stack = deque(self._get_sorted_out_edges(root))

        while stack:
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
            int(x)
            float(x)
            return True
        except ValueError:
            return False

    @staticmethod
    def _is_finite(x):
        try:
            is_finite = abs(x) < float('inf')
            return is_finite
        except TypeError:
            return False

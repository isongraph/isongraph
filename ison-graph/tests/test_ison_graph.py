#!/usr/bin/env python3
"""
Tests for ison-graph package
"""

import pytest
from ison_graph import (
    ISONGraph, Node, Edge, Path, Direction,
    NodeNotFoundError, EdgeNotFoundError,
    DuplicateNodeError, DuplicateEdgeError
)


# =============================================================================
# Node Tests
# =============================================================================

class TestNodes:
    """Test node operations"""

    def test_add_node(self):
        graph = ISONGraph()
        node = graph.add_node('person', 1, name='Alice', age=30)

        assert node.type == 'person'
        assert node.id == 1
        assert node.properties['name'] == 'Alice'
        assert node.properties['age'] == 30

    def test_get_node(self):
        graph = ISONGraph()
        graph.add_node('person', 1, name='Alice')

        node = graph.get_node('person', 1)
        assert node.properties['name'] == 'Alice'

    def test_get_node_not_found(self):
        graph = ISONGraph()

        with pytest.raises(NodeNotFoundError):
            graph.get_node('person', 999)

    def test_has_node(self):
        graph = ISONGraph()
        graph.add_node('person', 1)

        assert graph.has_node('person', 1)
        assert not graph.has_node('person', 2)
        assert not graph.has_node('company', 1)

    def test_duplicate_node_error(self):
        graph = ISONGraph()
        graph.add_node('person', 1)

        with pytest.raises(DuplicateNodeError):
            graph.add_node('person', 1)

    def test_remove_node(self):
        graph = ISONGraph()
        graph.add_node('person', 1)
        graph.add_node('person', 2)
        graph.add_edge('KNOWS', ('person', 1), ('person', 2))

        graph.remove_node('person', 1)

        assert not graph.has_node('person', 1)
        assert graph.edge_count() == 0  # Edges should be removed

    def test_update_node(self):
        graph = ISONGraph()
        graph.add_node('person', 1, name='Alice', age=30)

        graph.update_node('person', 1, age=31, email='alice@example.com')

        node = graph.get_node('person', 1)
        assert node.properties['age'] == 31
        assert node.properties['email'] == 'alice@example.com'
        assert node.properties['name'] == 'Alice'

    def test_node_count(self):
        graph = ISONGraph()
        graph.add_node('person', 1)
        graph.add_node('person', 2)
        graph.add_node('company', 1)

        assert graph.node_count() == 3
        assert graph.node_count('person') == 2
        assert graph.node_count('company') == 1

    def test_node_types(self):
        graph = ISONGraph()
        graph.add_node('person', 1)
        graph.add_node('company', 1)
        graph.add_node('post', 1)

        types = graph.node_types()
        assert set(types) == {'person', 'company', 'post'}


# =============================================================================
# Edge Tests
# =============================================================================

class TestEdges:
    """Test edge operations"""

    def test_add_edge(self):
        graph = ISONGraph()
        graph.add_node('person', 1)
        graph.add_node('person', 2)

        edge = graph.add_edge('KNOWS', ('person', 1), ('person', 2), since=2020)

        assert edge.rel_type == 'KNOWS'
        assert edge.source == ('person', 1)
        assert edge.target == ('person', 2)
        assert edge.properties['since'] == 2020

    def test_edge_requires_nodes(self):
        graph = ISONGraph()
        graph.add_node('person', 1)

        with pytest.raises(NodeNotFoundError):
            graph.add_edge('KNOWS', ('person', 1), ('person', 999))

    def test_duplicate_edge_error(self):
        graph = ISONGraph()
        graph.add_node('person', 1)
        graph.add_node('person', 2)
        graph.add_edge('KNOWS', ('person', 1), ('person', 2))

        with pytest.raises(DuplicateEdgeError):
            graph.add_edge('KNOWS', ('person', 1), ('person', 2))

    def test_has_edge(self):
        graph = ISONGraph()
        graph.add_node('person', 1)
        graph.add_node('person', 2)
        graph.add_edge('KNOWS', ('person', 1), ('person', 2))

        assert graph.has_edge('KNOWS', ('person', 1), ('person', 2))
        assert not graph.has_edge('KNOWS', ('person', 2), ('person', 1))

    def test_remove_edge(self):
        graph = ISONGraph()
        graph.add_node('person', 1)
        graph.add_node('person', 2)
        graph.add_edge('KNOWS', ('person', 1), ('person', 2))

        graph.remove_edge('KNOWS', ('person', 1), ('person', 2))

        assert not graph.has_edge('KNOWS', ('person', 1), ('person', 2))

    def test_remove_edge_undirected(self):
        """Removing an undirected edge removes the auto-created reverse too"""
        graph = ISONGraph(directed=False)
        graph.add_node('person', 1)
        graph.add_node('person', 2)
        graph.add_edge('KNOWS', ('person', 1), ('person', 2))

        graph.remove_edge('KNOWS', ('person', 1), ('person', 2))

        assert not graph.has_edge('KNOWS', ('person', 1), ('person', 2))
        assert not graph.has_edge('KNOWS', ('person', 2), ('person', 1))
        assert graph.edge_count() == 0

    def test_edge_count(self):
        graph = ISONGraph()
        graph.add_node('person', 1)
        graph.add_node('person', 2)
        graph.add_node('company', 1)
        graph.add_edge('KNOWS', ('person', 1), ('person', 2))
        graph.add_edge('WORKS_AT', ('person', 1), ('company', 1))

        assert graph.edge_count() == 2
        assert graph.edge_count('KNOWS') == 1
        assert graph.edge_count('WORKS_AT') == 1

    def test_edge_types(self):
        graph = ISONGraph()
        graph.add_node('person', 1)
        graph.add_node('person', 2)
        graph.add_node('company', 1)
        graph.add_edge('KNOWS', ('person', 1), ('person', 2))
        graph.add_edge('WORKS_AT', ('person', 1), ('company', 1))

        types = graph.edge_types()
        assert set(types) == {'KNOWS', 'WORKS_AT'}


# =============================================================================
# Traversal Tests
# =============================================================================

class TestTraversal:
    """Test graph traversal"""

    def setup_method(self):
        """Create a test graph: 1 -> 2 -> 3 -> 4 -> 5"""
        self.graph = ISONGraph()
        for i in range(1, 6):
            self.graph.add_node('person', i, name=f'Person{i}')

        self.graph.add_edge('KNOWS', ('person', 1), ('person', 2))
        self.graph.add_edge('KNOWS', ('person', 2), ('person', 3))
        self.graph.add_edge('KNOWS', ('person', 3), ('person', 4))
        self.graph.add_edge('KNOWS', ('person', 4), ('person', 5))

    def test_neighbors(self):
        neighbors = self.graph.neighbors(('person', 2), 'KNOWS')
        assert neighbors == [('person', 3)]

    def test_neighbors_incoming(self):
        neighbors = self.graph.neighbors(('person', 2), 'KNOWS', Direction.IN)
        assert neighbors == [('person', 1)]

    def test_neighbors_both(self):
        neighbors = self.graph.neighbors(('person', 2), 'KNOWS', Direction.BOTH)
        assert set(neighbors) == {('person', 1), ('person', 3)}

    def test_multi_hop_1(self):
        result = self.graph.multi_hop(('person', 1), 'KNOWS', hops=1)
        assert result == [('person', 2)]

    def test_multi_hop_2(self):
        result = self.graph.multi_hop(('person', 1), 'KNOWS', hops=2)
        assert result == [('person', 3)]

    def test_multi_hop_3(self):
        result = self.graph.multi_hop(('person', 1), 'KNOWS', hops=3)
        assert result == [('person', 4)]

    def test_multi_hop_range(self):
        result = self.graph.multi_hop_range(('person', 1), 'KNOWS', min_hops=1, max_hops=3)
        assert set(result) == {('person', 2), ('person', 3), ('person', 4)}

    def test_traverse_pattern(self):
        # Add company and works_at edge
        self.graph.add_node('company', 100, name='Acme')
        self.graph.add_edge('WORKS_AT', ('person', 2), ('company', 100))

        # person:1 -> KNOWS -> person:2 -> WORKS_AT -> company:100
        result = self.graph.traverse(
            ('person', 1),
            [('KNOWS', Direction.OUT), ('WORKS_AT', Direction.OUT)]
        )
        assert result == [('company', 100)]


# =============================================================================
# Path Finding Tests
# =============================================================================

class TestPathFinding:
    """Test path finding algorithms"""

    def setup_method(self):
        """Create test graph"""
        self.graph = ISONGraph()
        for i in range(1, 6):
            self.graph.add_node('person', i)

        # 1 -> 2 -> 3
        #      |    |
        #      v    v
        #      4 -> 5
        self.graph.add_edge('KNOWS', ('person', 1), ('person', 2))
        self.graph.add_edge('KNOWS', ('person', 2), ('person', 3))
        self.graph.add_edge('KNOWS', ('person', 2), ('person', 4))
        self.graph.add_edge('KNOWS', ('person', 3), ('person', 5))
        self.graph.add_edge('KNOWS', ('person', 4), ('person', 5))

    def test_shortest_path(self):
        path = self.graph.shortest_path(('person', 1), ('person', 5))

        assert path is not None
        assert path.length == 3
        assert path.start == ('person', 1)
        assert path.end == ('person', 5)

    def test_shortest_path_same_node(self):
        path = self.graph.shortest_path(('person', 1), ('person', 1))

        assert path is not None
        assert path.length == 0

    def test_no_path(self):
        self.graph.add_node('person', 99)  # Isolated node

        path = self.graph.shortest_path(('person', 1), ('person', 99))
        assert path is None

    def test_path_exists(self):
        assert self.graph.path_exists(('person', 1), ('person', 5))
        assert not self.graph.path_exists(('person', 5), ('person', 1))  # Directed

    def test_all_paths(self):
        paths = self.graph.all_paths(('person', 1), ('person', 5))

        assert len(paths) == 2  # Two paths: 1->2->3->5 and 1->2->4->5

    def test_shortest_path_max_hops_boundary(self):
        """max_hops must be a strict upper bound on path length"""
        # 1 -> 2 -> 3 needs 2 hops
        assert self.graph.shortest_path(('person', 1), ('person', 3), max_hops=1) is None

        path = self.graph.shortest_path(('person', 1), ('person', 3), max_hops=2)
        assert path is not None
        assert path.length == 2

        # Direct edge still found with max_hops=1
        path = self.graph.shortest_path(('person', 1), ('person', 2), max_hops=1)
        assert path is not None
        assert path.length == 1


# =============================================================================
# Graph Analysis Tests
# =============================================================================

class TestGraphAnalysis:
    """Test graph analysis functions"""

    def test_degree(self):
        graph = ISONGraph()
        graph.add_node('person', 1)
        graph.add_node('person', 2)
        graph.add_node('person', 3)
        graph.add_edge('KNOWS', ('person', 1), ('person', 2))
        graph.add_edge('KNOWS', ('person', 1), ('person', 3))

        assert graph.out_degree(('person', 1)) == 2
        assert graph.in_degree(('person', 1)) == 0
        assert graph.in_degree(('person', 2)) == 1

    def test_is_connected(self):
        graph = ISONGraph()
        graph.add_node('person', 1)
        graph.add_node('person', 2)
        graph.add_edge('KNOWS', ('person', 1), ('person', 2))

        assert graph.is_connected()

        graph.add_node('person', 99)  # Isolated
        assert not graph.is_connected()

    def test_has_cycle(self):
        graph = ISONGraph()
        graph.add_node('person', 1)
        graph.add_node('person', 2)
        graph.add_node('person', 3)
        graph.add_edge('KNOWS', ('person', 1), ('person', 2))
        graph.add_edge('KNOWS', ('person', 2), ('person', 3))

        assert not graph.has_cycle()

        graph.add_edge('KNOWS', ('person', 3), ('person', 1))
        assert graph.has_cycle()

    def test_has_cycle_undirected_single_edge(self):
        """A single undirected edge is not a cycle"""
        graph = ISONGraph(directed=False)
        graph.add_node('person', 1)
        graph.add_node('person', 2)
        graph.add_edge('KNOWS', ('person', 1), ('person', 2))

        assert not graph.has_cycle()

        # An acyclic undirected chain is not a cycle either
        graph.add_node('person', 3)
        graph.add_edge('KNOWS', ('person', 2), ('person', 3))
        assert not graph.has_cycle()

    def test_has_cycle_undirected_triangle(self):
        """A real undirected triangle is a cycle"""
        graph = ISONGraph(directed=False)
        graph.add_node('person', 1)
        graph.add_node('person', 2)
        graph.add_node('person', 3)
        graph.add_edge('KNOWS', ('person', 1), ('person', 2))
        graph.add_edge('KNOWS', ('person', 2), ('person', 3))
        graph.add_edge('KNOWS', ('person', 3), ('person', 1))

        assert graph.has_cycle()

    def test_connected_components(self):
        graph = ISONGraph()
        graph.add_node('person', 1)
        graph.add_node('person', 2)
        graph.add_node('person', 3)
        graph.add_node('person', 4)
        graph.add_edge('KNOWS', ('person', 1), ('person', 2))
        graph.add_edge('KNOWS', ('person', 3), ('person', 4))

        components = graph.connected_components()
        assert len(components) == 2


# =============================================================================
# Serialization Tests
# =============================================================================

class TestSerialization:
    """Test ISON serialization"""

    def test_to_ison(self):
        graph = ISONGraph()
        graph.add_node('person', 1, name='Alice')
        graph.add_node('person', 2, name='Bob')
        graph.add_edge('KNOWS', ('person', 1), ('person', 2), since=2020)

        ison = graph.to_ison()

        assert 'nodes.person' in ison
        assert 'edges.KNOWS' in ison
        assert ':person:1' in ison
        assert ':person:2' in ison

    def test_from_ison(self):
        ison = """
nodes.person
id name
1 Alice
2 Bob

edges.KNOWS
source target since
:person:1 :person:2 2020
"""
        graph = ISONGraph.from_ison(ison)

        assert graph.node_count() == 2
        assert graph.edge_count() == 1
        assert graph.get_node('person', 1).properties['name'] == 'Alice'

    def test_roundtrip(self):
        graph1 = ISONGraph()
        graph1.add_node('person', 1, name='Alice', age=30)
        graph1.add_node('person', 2, name='Bob', age=25)
        graph1.add_edge('KNOWS', ('person', 1), ('person', 2), since=2020)

        ison = graph1.to_ison()
        graph2 = ISONGraph.from_ison(ison)

        assert graph2.node_count() == graph1.node_count()
        assert graph2.edge_count() == graph1.edge_count()

    def test_to_isonl(self):
        graph = ISONGraph()
        graph.add_node('person', 1, name='Alice')
        graph.add_edge('KNOWS', ('person', 1), ('person', 1))  # Self loop for test

        isonl = graph.to_isonl()

        assert 'nodes.person|' in isonl
        assert 'edges.KNOWS|' in isonl

    SPECIAL_VALUES = {
        'title': 'Hello World',      # contains a space
        'tag': 'a|b',                # contains a pipe
        'body': 'line1\nline2',      # contains a newline
        'note': '',                  # empty string
        'quote': 'say "hi"',         # contains a double quote
    }

    def test_roundtrip_special_values_ison(self):
        """Values with spaces, pipes, newlines, quotes, and empty strings
        survive an ISON round-trip losslessly"""
        graph1 = ISONGraph()
        graph1.add_node('doc', 1, **self.SPECIAL_VALUES)

        graph2 = ISONGraph.from_ison(graph1.to_ison())

        props = graph2.get_node('doc', 1).properties
        for key, expected in self.SPECIAL_VALUES.items():
            assert props[key] == expected

    def test_roundtrip_special_values_isonl(self):
        """Values with spaces, pipes, newlines, quotes, and empty strings
        survive an ISONL round-trip losslessly"""
        graph1 = ISONGraph()
        graph1.add_node('doc', 1, **self.SPECIAL_VALUES)

        graph2 = ISONGraph.from_isonl(graph1.to_isonl())

        props = graph2.get_node('doc', 1).properties
        for key, expected in self.SPECIAL_VALUES.items():
            assert props[key] == expected


# =============================================================================
# Fluent API Tests
# =============================================================================

class TestFluentAPI:
    """Test fluent traversal API"""

    def setup_method(self):
        self.graph = ISONGraph()
        self.graph.add_node('person', 1, name='Alice', age=30)
        self.graph.add_node('person', 2, name='Bob', age=25)
        self.graph.add_node('person', 3, name='Charlie', age=35)
        self.graph.add_edge('KNOWS', ('person', 1), ('person', 2))
        self.graph.add_edge('KNOWS', ('person', 2), ('person', 3))

    def test_hop(self):
        result = self.graph.start(('person', 1)).hop('KNOWS').collect()
        assert result == [('person', 2)]

    def test_hops(self):
        result = self.graph.start(('person', 1)).hops(2, 'KNOWS').collect()
        assert result == [('person', 3)]

    def test_filter(self):
        result = self.graph.start(('person', 1)) \
            .hop('KNOWS') \
            .hop('KNOWS') \
            .filter(lambda n: n.properties.get('age', 0) > 30) \
            .collect()

        assert result == [('person', 3)]

    def test_collect_nodes(self):
        nodes = self.graph.start(('person', 1)).hop('KNOWS').collect_nodes()
        assert len(nodes) == 1
        assert nodes[0].properties['name'] == 'Bob'


# =============================================================================
# Query Pattern Tests
# =============================================================================

class TestQueryPatterns:
    """Test query pattern syntax"""

    def setup_method(self):
        self.graph = ISONGraph()
        for i in range(1, 5):
            self.graph.add_node('person', i)
        self.graph.add_edge('KNOWS', ('person', 1), ('person', 2))
        self.graph.add_edge('KNOWS', ('person', 2), ('person', 3))
        self.graph.add_edge('KNOWS', ('person', 3), ('person', 4))

    def test_simple_query(self):
        result = self.graph.query(":person:1 -[:KNOWS]-> *")
        assert result == [('person', 2)]

    def test_multi_hop_query(self):
        result = self.graph.query(":person:1 -[:KNOWS*2]-> *")
        assert result == [('person', 3)]

    def test_range_query(self):
        result = self.graph.query(":person:1 -[:KNOWS*1..2]-> *")
        assert set(result) == {('person', 2), ('person', 3)}


# =============================================================================
# Deep Graph Tests (iterative DFS must not overflow the call stack)
# =============================================================================

class TestDeepGraphs:
    """DFS-based operations must handle graphs deeper than the recursion limit"""

    DEPTH = 2000  # deeper than CPython's default recursion limit (~1000)

    def _build_chain(self):
        graph = ISONGraph()
        for i in range(1, self.DEPTH + 1):
            graph.add_node('node', i)
        for i in range(1, self.DEPTH):
            graph.add_edge('NEXT', ('node', i), ('node', i + 1))
        return graph

    def test_has_cycle_deep_chain(self):
        graph = self._build_chain()
        assert not graph.has_cycle()

        graph.add_edge('NEXT', ('node', self.DEPTH), ('node', 1))
        assert graph.has_cycle()

    def test_all_paths_deep_chain(self):
        graph = self._build_chain()
        paths = graph.all_paths(
            ('node', 1), ('node', self.DEPTH), max_hops=self.DEPTH
        )
        assert len(paths) == 1
        assert paths[0].length == self.DEPTH - 1


# =============================================================================
# Schema Default Tests
# =============================================================================

class TestSchemaDefaults:
    """Field defaults are applied to missing fields during validation"""

    def test_default_applied_to_missing_field(self):
        from ison_graph.schema import GraphSchema, NodeType, String

        graph = ISONGraph()
        graph.add_node('person', 1, name='Alice')

        Person = (NodeType('person')
                  .field('name', String().required())
                  .field('status', String().default('active')))
        result = GraphSchema('s').node_types(Person).validate(graph)

        assert result.valid
        assert graph.get_node('person', 1).properties['status'] == 'active'

    def test_default_satisfies_required(self):
        from ison_graph.schema import GraphSchema, NodeType, String

        graph = ISONGraph()
        graph.add_node('person', 1)

        Person = NodeType('person').field(
            'status', String().required().default('active')
        )
        result = GraphSchema('s').node_types(Person).validate(graph)

        assert result.valid
        assert graph.get_node('person', 1).properties['status'] == 'active'

    def test_missing_required_without_default_still_errors(self):
        from ison_graph.schema import GraphSchema, NodeType, String

        graph = ISONGraph()
        graph.add_node('person', 1)

        Person = NodeType('person').field('name', String().required())
        result = GraphSchema('s').node_types(Person).validate(graph)

        assert not result.valid

    def test_present_value_not_overwritten_by_default(self):
        from ison_graph.schema import GraphSchema, NodeType, String

        graph = ISONGraph()
        graph.add_node('person', 1, status='inactive')

        Person = NodeType('person').field('status', String().default('active'))
        result = GraphSchema('s').node_types(Person).validate(graph)

        assert result.valid
        assert graph.get_node('person', 1).properties['status'] == 'inactive'

    def test_edge_default_applied(self):
        from ison_graph.schema import GraphSchema, NodeType, EdgeType, Int

        graph = ISONGraph()
        graph.add_node('person', 1)
        graph.add_node('person', 2)
        graph.add_edge('KNOWS', ('person', 1), ('person', 2))

        Person = NodeType('person')
        Knows = EdgeType('KNOWS').field('weight', Int().default(1))
        result = (GraphSchema('s')
                  .node_types(Person)
                  .edge_types(Knows)
                  .validate(graph))

        assert result.valid
        edge = graph.get_edge('KNOWS', ('person', 1), ('person', 2))
        assert edge.properties['weight'] == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

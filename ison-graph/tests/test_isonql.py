#!/usr/bin/env python3
"""
Comprehensive Tests for ISONQL - Pure Property Graph Query Language

Tests all query types:
- NODES: Select and filter nodes
- EDGES: Select and filter edges
- TRAVERSE: Graph traversal with patterns
- PATH: Shortest path finding
- COUNT: Count nodes matching criteria
- SUM/AVG/MIN/MAX: Numeric aggregations

Also tests:
- ISONQLParser tokenization and parsing
- QueryEngine execution
- Fluent API (QueryBuilder, EdgeQueryBuilder)
- Operator evaluation
- Error handling
"""

import pytest
import re
from ison_graph import ISONGraph, Direction
from ison_graph.query import (
    QueryEngine,
    QueryBuilder,
    EdgeQueryBuilder,
    ISONQLParser,
    QueryResult,
    Condition,
    Operator,
    SortOrder,
    QueryType,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def empty_graph():
    """Empty graph for basic tests."""
    return ISONGraph()


@pytest.fixture
def simple_graph():
    """Simple graph with a few nodes and edges."""
    graph = ISONGraph()
    graph.add_node('person', 'alice', name='Alice', age=30, status='active')
    graph.add_node('person', 'bob', name='Bob', age=25, status='active')
    graph.add_node('person', 'charlie', name='Charlie', age=35, status='inactive')
    graph.add_edge('KNOWS', ('person', 'alice'), ('person', 'bob'), since=2020, strength=0.8)
    graph.add_edge('KNOWS', ('person', 'bob'), ('person', 'charlie'), since=2021, strength=0.5)
    return graph


@pytest.fixture
def social_graph():
    """Larger social network graph for complex queries."""
    graph = ISONGraph()

    # People
    graph.add_node('person', 1, name='Alice', age=30, city='NYC', salary=80000)
    graph.add_node('person', 2, name='Bob', age=25, city='LA', salary=60000)
    graph.add_node('person', 3, name='Charlie', age=35, city='NYC', salary=90000)
    graph.add_node('person', 4, name='Diana', age=28, city='Chicago', salary=75000)
    graph.add_node('person', 5, name='Eve', age=32, city='NYC', salary=85000)
    graph.add_node('person', 6, name='Frank', age=40, city='LA', salary=100000)

    # Companies
    graph.add_node('company', 100, name='TechCorp', employees=500, industry='tech')
    graph.add_node('company', 101, name='FinanceInc', employees=200, industry='finance')
    graph.add_node('company', 102, name='StartupXYZ', employees=50, industry='tech')

    # Projects
    graph.add_node('project', 'p1', name='Project Alpha', budget=100000)
    graph.add_node('project', 'p2', name='Project Beta', budget=50000)

    # KNOWS relationships
    graph.add_edge('KNOWS', ('person', 1), ('person', 2), since=2018, close=True)
    graph.add_edge('KNOWS', ('person', 1), ('person', 3), since=2019, close=False)
    graph.add_edge('KNOWS', ('person', 2), ('person', 4), since=2020, close=True)
    graph.add_edge('KNOWS', ('person', 3), ('person', 5), since=2017, close=True)
    graph.add_edge('KNOWS', ('person', 4), ('person', 5), since=2021, close=False)
    graph.add_edge('KNOWS', ('person', 5), ('person', 6), since=2016, close=True)

    # WORKS_AT relationships
    graph.add_edge('WORKS_AT', ('person', 1), ('company', 100), role='Engineer', years=5)
    graph.add_edge('WORKS_AT', ('person', 2), ('company', 100), role='Designer', years=2)
    graph.add_edge('WORKS_AT', ('person', 3), ('company', 101), role='Manager', years=8)
    graph.add_edge('WORKS_AT', ('person', 4), ('company', 102), role='Developer', years=3)
    graph.add_edge('WORKS_AT', ('person', 5), ('company', 100), role='Lead', years=6)
    graph.add_edge('WORKS_AT', ('person', 6), ('company', 101), role='Director', years=10)

    # WORKS_ON relationships
    graph.add_edge('WORKS_ON', ('person', 1), ('project', 'p1'), hours=20)
    graph.add_edge('WORKS_ON', ('person', 2), ('project', 'p1'), hours=15)
    graph.add_edge('WORKS_ON', ('person', 3), ('project', 'p2'), hours=10)

    return graph


@pytest.fixture
def engine(social_graph):
    """Query engine with social graph."""
    return QueryEngine(social_graph)


@pytest.fixture
def simple_engine(simple_graph):
    """Query engine with simple graph."""
    return QueryEngine(simple_graph)


@pytest.fixture
def parser():
    """ISONQL parser instance."""
    return ISONQLParser()


# =============================================================================
# Parser Tests
# =============================================================================

class TestISONQLParser:
    """Test ISONQL parser tokenization and parsing."""

    def test_tokenize_simple(self, parser):
        """Test basic tokenization."""
        tokens = parser._tokenize("NODES person")
        assert tokens == ['NODES', 'person']

    def test_tokenize_with_operators(self, parser):
        """Test tokenization with operators."""
        tokens = parser._tokenize("NODES person WHERE age > 25")
        assert tokens == ['NODES', 'person', 'WHERE', 'age', '>', '25']

    def test_tokenize_multi_char_operators(self, parser):
        """Test multi-character operators."""
        tokens = parser._tokenize("age >= 25 AND age <= 50")
        assert '>=' in tokens
        assert '<=' in tokens

    def test_tokenize_string_literals(self, parser):
        """Test string literal tokenization."""
        tokens = parser._tokenize('name = "Alice Smith"')
        assert 'Alice Smith' in tokens

    def test_tokenize_single_quoted_strings(self, parser):
        """Test single-quoted string literals."""
        tokens = parser._tokenize("name = 'Bob'")
        assert 'Bob' in tokens

    def test_tokenize_node_reference(self, parser):
        """Test node reference tokenization."""
        tokens = parser._tokenize("TRAVERSE :person:alice -> KNOWS")
        assert ':person:alice' in tokens

    def test_tokenize_arrows(self, parser):
        """Test arrow operator tokenization."""
        tokens = parser._tokenize("-> KNOWS -> <- FOLLOWS <-")
        assert '->' in tokens
        assert '<-' in tokens

    def test_parse_nodes_basic(self, parser):
        """Test parsing basic NODES query."""
        result = parser.parse("NODES person")
        assert result['type'] == 'NODES'
        assert result['node_type'] == 'person'
        assert result['conditions'] == []

    def test_parse_nodes_with_where(self, parser):
        """Test parsing NODES with WHERE clause."""
        result = parser.parse("NODES person WHERE age > 25")
        assert result['type'] == 'NODES'
        assert result['node_type'] == 'person'
        assert len(result['conditions']) == 1
        assert result['conditions'][0].field == 'age'
        assert result['conditions'][0].operator == Operator.GT
        assert result['conditions'][0].value == 25

    def test_parse_nodes_with_order_by(self, parser):
        """Test parsing NODES with ORDER BY."""
        result = parser.parse("NODES person ORDER BY name DESC")
        assert result['order_by'] == 'name'
        assert result['order_dir'] == 'DESC'

    def test_parse_nodes_with_limit_offset(self, parser):
        """Test parsing NODES with LIMIT and OFFSET."""
        result = parser.parse("NODES person LIMIT 10 OFFSET 5")
        assert result['limit'] == 10
        assert result['offset'] == 5

    def test_parse_nodes_shorthand(self, parser):
        """Test parsing shorthand NODES syntax."""
        result = parser.parse('NODES person(name="Alice", age=30)')
        assert result['node_type'] == 'person'
        assert len(result['conditions']) == 2

    def test_parse_edges_basic(self, parser):
        """Test parsing basic EDGES query."""
        result = parser.parse("EDGES KNOWS")
        assert result['type'] == 'EDGES'
        assert result['rel_type'] == 'KNOWS'

    def test_parse_edges_with_where(self, parser):
        """Test parsing EDGES with WHERE."""
        result = parser.parse("EDGES KNOWS WHERE since > 2020")
        assert result['conditions'][0].field == 'since'
        assert result['conditions'][0].value == 2020

    def test_parse_traverse(self, parser):
        """Test parsing TRAVERSE query."""
        result = parser.parse("TRAVERSE person:alice -> KNOWS -> person")
        assert result['type'] == 'TRAVERSE'
        assert result['start'] == ('person', 'alice')
        assert len(result['pattern']) == 1
        assert result['pattern'][0]['rel_type'] == 'KNOWS'

    def test_parse_traverse_with_max(self, parser):
        """Test parsing TRAVERSE with MAX depth."""
        result = parser.parse("TRAVERSE person:1 -> KNOWS -> person MAX 3")
        assert result['max_depth'] == 3

    def test_parse_path(self, parser):
        """Test parsing PATH query."""
        result = parser.parse("PATH person:alice TO person:bob")
        assert result['type'] == 'PATH'
        assert result['source'] == ('person', 'alice')
        assert result['target'] == ('person', 'bob')

    def test_parse_path_with_via(self, parser):
        """Test parsing PATH with VIA."""
        result = parser.parse("PATH person:1 TO person:5 VIA KNOWS MAX 5")
        assert result['via'] == 'KNOWS'
        assert result['max_hops'] == 5

    def test_parse_count(self, parser):
        """Test parsing COUNT query."""
        result = parser.parse("COUNT person WHERE age > 25")
        assert result['type'] == 'COUNT'
        assert result['node_type'] == 'person'
        assert len(result['conditions']) == 1

    def test_parse_aggregation_sum(self, parser):
        """Test parsing SUM query."""
        result = parser.parse("SUM person.salary WHERE city = NYC")
        assert result['type'] == 'SUM'
        assert result['node_type'] == 'person'
        assert result['property'] == 'salary'

    def test_parse_aggregation_avg(self, parser):
        """Test parsing AVG query."""
        result = parser.parse("AVG person.age")
        assert result['type'] == 'AVG'
        assert result['property'] == 'age'

    def test_parse_multiple_conditions(self, parser):
        """Test parsing multiple AND conditions."""
        result = parser.parse("NODES person WHERE age > 25 AND city = NYC AND status = active")
        assert len(result['conditions']) == 3

    def test_parse_in_operator(self, parser):
        """Test parsing IN operator."""
        result = parser.parse("NODES person WHERE city IN (NYC, LA, Chicago)")
        assert result['conditions'][0].operator == Operator.IN
        assert result['conditions'][0].value == ['NYC', 'LA', 'Chicago']

    def test_parse_contains_operator(self, parser):
        """Test parsing CONTAINS operator."""
        result = parser.parse("NODES person WHERE name CONTAINS Ali")
        assert result['conditions'][0].operator == Operator.CONTAINS

    def test_parse_exists_operator(self, parser):
        """Test parsing EXISTS operator."""
        result = parser.parse("NODES person WHERE EXISTS email")
        assert result['conditions'][0].operator == Operator.EXISTS

    def test_parse_boolean_values(self, parser):
        """Test parsing boolean values."""
        result = parser.parse("NODES person WHERE active = TRUE")
        assert result['conditions'][0].value is True

    def test_parse_null_values(self, parser):
        """Test parsing null values."""
        result = parser.parse("NODES person WHERE email = NULL")
        assert result['conditions'][0].value is None

    def test_parse_float_values(self, parser):
        """Test parsing float values."""
        result = parser.parse("NODES person WHERE score > 3.5")
        assert result['conditions'][0].value == 3.5

    def test_parse_invalid_query_type(self, parser):
        """Test parsing invalid query type raises error."""
        with pytest.raises(ValueError) as exc_info:
            parser.parse("INVALID person")
        assert "Unknown query type" in str(exc_info.value)

    def test_parse_empty_query(self, parser):
        """Test parsing empty query raises error."""
        with pytest.raises(ValueError):
            parser.parse("")

    def test_parse_invalid_node_ref(self, parser):
        """Test parsing invalid node reference."""
        with pytest.raises(ValueError) as exc_info:
            parser.parse("TRAVERSE invalid_ref -> KNOWS")
        assert "Invalid node reference" in str(exc_info.value)

    def test_tokenize_type_id_node_ref(self, parser):
        """A type:id node reference lexes as a single token."""
        tokens = parser._tokenize("TRAVERSE person:1 -> KNOWS -> person")
        assert 'person:1' in tokens
        tokens = parser._tokenize("PATH person:alice TO person:bob")
        assert 'person:alice' in tokens
        assert 'person:bob' in tokens

    def test_tokenize_bare_colon(self, parser):
        """A bare ':' not followed by an identifier stays its own token."""
        tokens = parser._tokenize("person :")
        assert tokens == ['person', ':']

    def test_tokenize_negative_numbers(self, parser):
        """Negative int and float literals lex as single tokens."""
        tokens = parser._tokenize("NODES person WHERE score > -5")
        assert '-5' in tokens
        tokens = parser._tokenize("NODES person WHERE score > -3.5")
        assert '-3.5' in tokens

    def test_parse_negative_values(self, parser):
        """Negative literals parse to negative numbers."""
        result = parser.parse("NODES person WHERE score > -5")
        assert result['conditions'][0].value == -5
        result = parser.parse("NODES person WHERE score > -3.5")
        assert result['conditions'][0].value == -3.5

    def test_unknown_character_raises(self, parser):
        """Unknown characters raise a parse error instead of being dropped."""
        with pytest.raises(ValueError) as exc_info:
            parser._tokenize("NODES person WHERE age > 25 ;")
        assert "Unexpected character" in str(exc_info.value)

    def test_parse_or_conditions(self, parser):
        """OR splits conditions into OR-groups."""
        result = parser.parse("NODES person WHERE city = LA OR city = Chicago")
        groups = result['conditions']
        assert len(groups) == 2
        assert isinstance(groups[0], list)
        assert groups[0][0].value == 'LA'
        assert groups[1][0].value == 'Chicago'

    def test_parse_and_or_precedence(self, parser):
        """AND binds tighter than OR: a AND b OR c == (a AND b) OR c."""
        result = parser.parse(
            "NODES person WHERE age > 30 AND city = NYC OR city = Chicago"
        )
        groups = result['conditions']
        assert len(groups) == 2
        assert len(groups[0]) == 2   # age > 30 AND city = NYC
        assert len(groups[1]) == 1   # city = Chicago


# =============================================================================
# Condition Tests
# =============================================================================

class TestCondition:
    """Test Condition evaluation."""

    def test_eq_operator(self):
        """Test equality operator."""
        cond = Condition('name', Operator.EQ, 'Alice')
        assert cond.evaluate({'name': 'Alice'}) is True
        assert cond.evaluate({'name': 'Bob'}) is False

    def test_ne_operator(self):
        """Test not-equal operator."""
        cond = Condition('name', Operator.NE, 'Alice')
        assert cond.evaluate({'name': 'Bob'}) is True
        assert cond.evaluate({'name': 'Alice'}) is False

    def test_gt_operator(self):
        """Test greater-than operator."""
        cond = Condition('age', Operator.GT, 25)
        assert cond.evaluate({'age': 30}) is True
        assert cond.evaluate({'age': 25}) is False
        assert cond.evaluate({'age': 20}) is False

    def test_ge_operator(self):
        """Test greater-or-equal operator."""
        cond = Condition('age', Operator.GE, 25)
        assert cond.evaluate({'age': 30}) is True
        assert cond.evaluate({'age': 25}) is True
        assert cond.evaluate({'age': 20}) is False

    def test_lt_operator(self):
        """Test less-than operator."""
        cond = Condition('age', Operator.LT, 25)
        assert cond.evaluate({'age': 20}) is True
        assert cond.evaluate({'age': 25}) is False
        assert cond.evaluate({'age': 30}) is False

    def test_le_operator(self):
        """Test less-or-equal operator."""
        cond = Condition('age', Operator.LE, 25)
        assert cond.evaluate({'age': 20}) is True
        assert cond.evaluate({'age': 25}) is True
        assert cond.evaluate({'age': 30}) is False

    def test_in_operator(self):
        """Test IN operator."""
        cond = Condition('city', Operator.IN, ['NYC', 'LA'])
        assert cond.evaluate({'city': 'NYC'}) is True
        assert cond.evaluate({'city': 'LA'}) is True
        assert cond.evaluate({'city': 'Chicago'}) is False

    def test_not_in_operator(self):
        """Test NOT IN operator."""
        cond = Condition('city', Operator.NOT_IN, ['NYC', 'LA'])
        assert cond.evaluate({'city': 'Chicago'}) is True
        assert cond.evaluate({'city': 'NYC'}) is False

    def test_contains_operator(self):
        """Test CONTAINS operator."""
        cond = Condition('name', Operator.CONTAINS, 'lic')
        assert cond.evaluate({'name': 'Alice'}) is True
        assert cond.evaluate({'name': 'Bob'}) is False

    def test_starts_with_operator(self):
        """Test STARTS_WITH operator."""
        cond = Condition('name', Operator.STARTS_WITH, 'Al')
        assert cond.evaluate({'name': 'Alice'}) is True
        assert cond.evaluate({'name': 'Bob'}) is False

    def test_ends_with_operator(self):
        """Test ENDS_WITH operator."""
        cond = Condition('email', Operator.ENDS_WITH, '.com')
        assert cond.evaluate({'email': 'alice@example.com'}) is True
        assert cond.evaluate({'email': 'alice@example.org'}) is False

    def test_matches_operator(self):
        """Test MATCHES (regex) operator."""
        cond = Condition('email', Operator.MATCHES, r'^[a-z]+@')
        assert cond.evaluate({'email': 'alice@example.com'}) is True
        assert cond.evaluate({'email': '123@example.com'}) is False

    def test_exists_operator(self):
        """Test EXISTS operator."""
        cond = Condition('email', Operator.EXISTS, None)
        assert cond.evaluate({'email': 'alice@example.com'}) is True
        assert cond.evaluate({'name': 'Alice'}) is False

    def test_not_exists_operator(self):
        """Test NOT_EXISTS operator."""
        cond = Condition('email', Operator.NOT_EXISTS, None)
        assert cond.evaluate({'name': 'Alice'}) is True
        assert cond.evaluate({'email': 'alice@example.com'}) is False

    def test_missing_field(self):
        """Test condition on missing field returns False."""
        cond = Condition('missing', Operator.EQ, 'value')
        assert cond.evaluate({'other': 'value'}) is False


# =============================================================================
# NODES Query Tests
# =============================================================================

class TestNodesQuery:
    """Test NODES query execution."""

    def test_nodes_all(self, engine):
        """Test selecting all nodes."""
        result = engine.execute("NODES")
        assert result.count > 0
        assert result.total_count == result.count

    def test_nodes_by_type(self, engine):
        """Test selecting nodes by type."""
        result = engine.execute("NODES person")
        assert result.count == 6
        for item in result.data:
            assert item['type'] == 'person'

    def test_nodes_where_gt(self, engine):
        """Test NODES with greater-than condition."""
        result = engine.execute("NODES person WHERE age > 30")
        assert result.count == 3  # Charlie (35), Eve (32), Frank (40)
        for item in result.data:
            assert item['properties']['age'] > 30

    def test_nodes_where_eq_string(self, engine):
        """Test NODES with string equality."""
        result = engine.execute("NODES person WHERE city = NYC")
        assert result.count == 3  # Alice, Charlie, Eve
        for item in result.data:
            assert item['properties']['city'] == 'NYC'

    def test_nodes_where_multiple_conditions(self, engine):
        """Test NODES with multiple AND conditions."""
        result = engine.execute("NODES person WHERE age > 25 AND city = NYC")
        assert result.count == 3  # Alice (30), Charlie (35), Eve (32)

    def test_nodes_order_by_asc(self, engine):
        """Test NODES with ORDER BY ascending."""
        result = engine.execute("NODES person ORDER BY age ASC")
        ages = [item['properties']['age'] for item in result.data]
        assert ages == sorted(ages)

    def test_nodes_order_by_desc(self, engine):
        """Test NODES with ORDER BY descending."""
        result = engine.execute("NODES person ORDER BY age DESC")
        ages = [item['properties']['age'] for item in result.data]
        assert ages == sorted(ages, reverse=True)

    def test_nodes_limit(self, engine):
        """Test NODES with LIMIT."""
        result = engine.execute("NODES person LIMIT 3")
        assert result.count == 3
        assert result.total_count == 6

    def test_nodes_offset(self, engine):
        """Test NODES with OFFSET."""
        result = engine.execute("NODES person ORDER BY age ASC LIMIT 2 OFFSET 2")
        assert result.count == 2
        # After skipping 2 youngest, should get middle ages
        ages = [item['properties']['age'] for item in result.data]
        assert ages[0] >= 28  # Should skip 25, 28

    def test_nodes_return_fields(self, engine):
        """Test NODES with RETURN fields projection."""
        result = engine.execute("NODES person RETURN name, age")
        assert result.count == 6
        for item in result.data:
            assert 'name' in item
            assert 'age' in item
            assert 'city' not in item
            assert 'properties' not in item

    def test_nodes_shorthand_syntax(self, engine):
        """Test NODES shorthand syntax."""
        result = engine.execute('NODES person(city="NYC")')
        assert result.count == 3

    def test_nodes_in_operator(self, engine):
        """Test NODES with IN operator."""
        result = engine.execute("NODES person WHERE city IN (NYC, LA)")
        assert result.count == 5  # Alice, Bob, Charlie, Eve, Frank

    def test_nodes_contains_operator(self, engine):
        """Test NODES with CONTAINS operator."""
        result = engine.execute("NODES person WHERE name CONTAINS a")
        # Alice, Diana, Frank (lowercase 'a')
        for item in result.data:
            assert 'a' in item['properties']['name'].lower()

    def test_nodes_starts_with(self, engine):
        """Test NODES with STARTS_WITH operator."""
        result = engine.execute("NODES person WHERE name STARTS_WITH A")
        assert result.count == 1  # Alice

    def test_nodes_empty_result(self, engine):
        """Test NODES query with no matches."""
        result = engine.execute("NODES person WHERE age > 100")
        assert result.count == 0
        assert result.data == []

    def test_nodes_where_or(self, engine):
        """Test NODES with OR condition."""
        result = engine.execute("NODES person WHERE city = LA OR city = Chicago")
        assert result.count == 3  # Bob (LA), Frank (LA), Diana (Chicago)
        for item in result.data:
            assert item['properties']['city'] in ('LA', 'Chicago')

    def test_nodes_where_and_or_precedence(self, engine):
        """AND binds tighter than OR when evaluating."""
        result = engine.execute(
            "NODES person WHERE age > 30 AND city = NYC OR city = Chicago"
        )
        # (age > 30 AND NYC) -> Charlie (35), Eve (32); OR Chicago -> Diana
        assert result.count == 3
        names = {item['properties']['name'] for item in result.data}
        assert names == {'Charlie', 'Eve', 'Diana'}

    def test_nodes_limit_zero(self, engine):
        """LIMIT 0 returns no rows, not all rows."""
        result = engine.execute("NODES person LIMIT 0")
        assert result.count == 0
        assert result.total_count == 6

    def test_nodes_where_negative_number(self, engine):
        """Negative literals work in WHERE comparisons."""
        result = engine.execute("NODES person WHERE age > -5")
        assert result.count == 6

    def test_nodes_order_by_missing_field(self, engine):
        """Nodes missing the ORDER BY field sort last and never crash."""
        engine.graph.add_node('person', 999, name='NoAge', city='NYC')

        result = engine.execute("NODES person ORDER BY age ASC")
        assert result.count == 7
        assert result.data[-1]['id'] == 999
        ages = [item['properties']['age'] for item in result.data[:-1]]
        assert ages == sorted(ages)

        result = engine.execute("NODES person ORDER BY age DESC")
        assert result.data[-1]['id'] == 999  # missing still last on DESC


# =============================================================================
# EDGES Query Tests
# =============================================================================

class TestEdgesQuery:
    """Test EDGES query execution."""

    def test_edges_all(self, engine):
        """Test selecting all edges."""
        result = engine.execute("EDGES")
        assert result.count > 0

    def test_edges_by_type(self, engine):
        """Test selecting edges by relationship type."""
        result = engine.execute("EDGES KNOWS")
        assert result.count == 6
        for item in result.data:
            assert item['rel_type'] == 'KNOWS'

    def test_edges_where_condition(self, engine):
        """Test EDGES with WHERE condition."""
        result = engine.execute("EDGES KNOWS WHERE since > 2019")
        for item in result.data:
            assert item['properties']['since'] > 2019

    def test_edges_where_boolean(self, engine):
        """Test EDGES with boolean condition."""
        result = engine.execute("EDGES KNOWS WHERE close = TRUE")
        for item in result.data:
            assert item['properties']['close'] is True

    def test_edges_limit(self, engine):
        """Test EDGES with LIMIT."""
        result = engine.execute("EDGES KNOWS LIMIT 3")
        assert result.count == 3

    def test_edges_works_at(self, engine):
        """Test selecting WORKS_AT edges."""
        result = engine.execute("EDGES WORKS_AT")
        assert result.count == 6
        for item in result.data:
            assert item['rel_type'] == 'WORKS_AT'

    def test_edges_with_property_filter(self, engine):
        """Test EDGES filtering by property."""
        result = engine.execute("EDGES WORKS_AT WHERE years > 5")
        for item in result.data:
            assert item['properties']['years'] > 5


# =============================================================================
# TRAVERSE Query Tests
# =============================================================================

class TestTraverseQuery:
    """Test TRAVERSE query execution."""

    def test_traverse_single_hop(self, engine):
        """Test single-hop traversal."""
        result = engine.execute("TRAVERSE person:1 -> KNOWS -> person")
        # Person 1 (Alice) knows person 2 (Bob) and person 3 (Charlie)
        assert result.count == 2

    def test_traverse_with_colon_prefix(self, engine):
        """Test traversal with colon-prefixed node ref."""
        result = engine.execute("TRAVERSE :person:1 -> KNOWS -> person")
        assert result.count == 2

    def test_traverse_max_depth(self, engine):
        """Test traversal with MAX depth."""
        result = engine.execute("TRAVERSE person:1 -> KNOWS -> person MAX 2")
        # Should find friends and friends-of-friends
        assert result.count >= 2

    def test_traverse_incoming(self, engine):
        """Test traversal following incoming edges."""
        result = engine.execute("TRAVERSE person:2 <- KNOWS <- person")
        # Who knows Bob? Alice (person 1)
        assert result.count >= 1

    def test_traverse_limit(self, engine):
        """Test traversal with LIMIT."""
        result = engine.execute("TRAVERSE person:1 -> KNOWS -> person MAX 3 LIMIT 2")
        assert result.count <= 2

    def test_traverse_wildcard_target(self, engine):
        """Test traversal with wildcard target type."""
        result = engine.execute("TRAVERSE person:1 -> WORKS_AT -> *")
        # Alice works at company 100
        assert result.count >= 1

    def test_traverse_from_string_id(self, simple_engine):
        """Test traversal from node with string ID."""
        result = simple_engine.execute("TRAVERSE person:alice -> KNOWS -> person")
        assert result.count >= 1


# =============================================================================
# PATH Query Tests
# =============================================================================

class TestPathQuery:
    """Test PATH query execution."""

    def test_path_direct(self, engine):
        """Test finding direct path."""
        result = engine.execute("PATH person:1 TO person:2")
        assert result.count == 1
        path = result.data[0]
        assert path['length'] == 1

    def test_path_multi_hop(self, engine):
        """Test finding multi-hop path."""
        result = engine.execute("PATH person:1 TO person:5 VIA KNOWS")
        assert result.count == 1
        path = result.data[0]
        assert path['length'] >= 1

    def test_path_via_relationship(self, engine):
        """Test path with VIA constraint."""
        result = engine.execute("PATH person:1 TO person:4 VIA KNOWS MAX 5")
        if result.count > 0:
            path = result.data[0]
            for edge in path['edges']:
                assert edge['rel_type'] == 'KNOWS'

    def test_path_max_hops(self, engine):
        """Test path with MAX hops limit."""
        result = engine.execute("PATH person:1 TO person:6 MAX 3")
        # May or may not find path within 3 hops
        assert result.count <= 1

    def test_path_not_found(self, engine):
        """Test path when no path exists."""
        # Create isolated node
        engine.graph.add_node('person', 999, name='Isolated')
        result = engine.execute("PATH person:1 TO person:999 MAX 5")
        assert result.count == 0

    def test_path_same_node(self, engine):
        """Test path from node to itself."""
        result = engine.execute("PATH person:1 TO person:1")
        # Implementation may return empty or single-node path
        assert result.count <= 1

    def test_path_with_string_ids(self, simple_engine):
        """Test path finding with string IDs."""
        result = simple_engine.execute("PATH person:alice TO person:charlie VIA KNOWS")
        assert result.count == 1


# =============================================================================
# COUNT Query Tests
# =============================================================================

class TestCountQuery:
    """Test COUNT query execution."""

    def test_count_all_of_type(self, engine):
        """Test counting all nodes of a type."""
        result = engine.execute("COUNT person")
        assert result.data[0] == 6

    def test_count_with_condition(self, engine):
        """Test COUNT with WHERE condition."""
        result = engine.execute("COUNT person WHERE age > 30")
        assert result.data[0] == 3  # Charlie (35), Eve (32), Frank (40)

    def test_count_with_multiple_conditions(self, engine):
        """Test COUNT with multiple conditions."""
        result = engine.execute("COUNT person WHERE age > 25 AND city = NYC")
        assert result.data[0] == 3  # Alice, Charlie, Eve

    def test_count_companies(self, engine):
        """Test counting companies."""
        result = engine.execute("COUNT company")
        assert result.data[0] == 3

    def test_count_zero(self, engine):
        """Test COUNT returning zero."""
        result = engine.execute("COUNT person WHERE age > 100")
        assert result.data[0] == 0

    def test_count_with_or(self, engine):
        """Test COUNT with OR condition."""
        result = engine.execute("COUNT person WHERE city = LA OR city = Chicago")
        assert result.data[0] == 3  # Bob (LA), Frank (LA), Diana (Chicago)


# =============================================================================
# Aggregation Query Tests
# =============================================================================

class TestAggregationQueries:
    """Test SUM, AVG, MIN, MAX query execution."""

    def test_sum_basic(self, engine):
        """Test SUM aggregation."""
        result = engine.execute("SUM person.salary")
        expected = 80000 + 60000 + 90000 + 75000 + 85000 + 100000
        assert result.data[0] == expected

    def test_sum_with_condition(self, engine):
        """Test SUM with WHERE condition."""
        result = engine.execute("SUM person.salary WHERE city = NYC")
        expected = 80000 + 90000 + 85000  # Alice, Charlie, Eve
        assert result.data[0] == expected

    def test_avg_basic(self, engine):
        """Test AVG aggregation."""
        result = engine.execute("AVG person.age")
        ages = [30, 25, 35, 28, 32, 40]
        expected = sum(ages) / len(ages)
        assert abs(result.data[0] - expected) < 0.01

    def test_avg_with_condition(self, engine):
        """Test AVG with WHERE condition."""
        result = engine.execute("AVG person.salary WHERE city = NYC")
        salaries = [80000, 90000, 85000]
        expected = sum(salaries) / len(salaries)
        assert abs(result.data[0] - expected) < 0.01

    def test_min_basic(self, engine):
        """Test MIN aggregation."""
        result = engine.execute("MIN person.age")
        assert result.data[0] == 25  # Bob

    def test_min_with_condition(self, engine):
        """Test MIN with WHERE condition."""
        result = engine.execute("MIN person.salary WHERE city = NYC")
        assert result.data[0] == 80000  # Alice

    def test_max_basic(self, engine):
        """Test MAX aggregation."""
        result = engine.execute("MAX person.age")
        assert result.data[0] == 40  # Frank

    def test_max_with_condition(self, engine):
        """Test MAX with WHERE condition."""
        result = engine.execute("MAX person.salary WHERE city = LA")
        assert result.data[0] == 100000  # Frank

    def test_aggregation_no_matches(self, engine):
        """Test aggregation with no matching nodes."""
        result = engine.execute("SUM person.salary WHERE age > 100")
        assert result.data[0] is None

    def test_aggregation_missing_property(self, engine):
        """Test aggregation on missing property."""
        result = engine.execute("SUM person.nonexistent")
        assert result.data[0] is None


# =============================================================================
# Fluent API Tests
# =============================================================================

class TestFluentAPI:
    """Test QueryBuilder fluent API."""

    def test_basic_match(self, engine):
        """Test basic match query."""
        result = engine.match("person").execute()
        assert result.count == 6

    def test_match_with_where(self, engine):
        """Test match with where condition."""
        result = (engine.match("person")
            .where("age", ">", 30)
            .execute())
        assert result.count == 3  # Charlie (35), Eve (32), Frank (40)

    def test_match_multiple_where(self, engine):
        """Test match with multiple where conditions."""
        result = (engine.match("person")
            .where("age", ">", 25)
            .where("city", "=", "NYC")
            .execute())
        assert result.count == 3

    def test_match_order_by(self, engine):
        """Test match with order by."""
        result = (engine.match("person")
            .order_by("age", "ASC")
            .execute())
        ages = [item['properties']['age'] for item in result.data]
        assert ages == sorted(ages)

    def test_match_limit(self, engine):
        """Test match with limit."""
        result = (engine.match("person")
            .limit(3)
            .execute())
        assert result.count == 3

    def test_match_offset(self, engine):
        """Test match with offset."""
        result = (engine.match("person")
            .order_by("age", "ASC")
            .offset(2)
            .limit(2)
            .execute())
        assert result.count == 2

    def test_match_return_fields(self, engine):
        """Test match with return fields projection."""
        result = (engine.match("person")
            .return_fields("name", "age")
            .execute())
        for item in result.data:
            assert 'name' in item
            assert 'age' in item
            assert 'city' not in item

    def test_match_where_exists(self, engine):
        """Test match with where_exists."""
        result = (engine.match("person")
            .where_exists("salary")
            .execute())
        assert result.count == 6

    def test_match_where_not_exists(self, engine):
        """Test match with where_not_exists."""
        # Add a node without email
        engine.graph.add_node('person', 999, name='NoEmail', age=50)
        result = (engine.match("person")
            .where_not_exists("email")
            .execute())
        assert result.count >= 1

    def test_match_count(self, engine):
        """Test match count method."""
        count = (engine.match("person")
            .where("age", ">", 30)
            .count())
        assert count == 3  # Charlie (35), Eve (32), Frank (40)

    def test_match_limit_zero(self, engine):
        """Fluent limit(0) returns no rows."""
        result = engine.match("person").limit(0).execute()
        assert result.count == 0
        assert result.total_count == 6

    def test_where_invalid_operator_raises(self, engine):
        """Unknown operators raise instead of silently becoming EQ."""
        with pytest.raises(ValueError) as exc_info:
            engine.match("person").where("age", "LIKE", "3%")
        assert "Unknown operator" in str(exc_info.value)

    def test_match_chaining(self, engine):
        """Test full method chaining."""
        result = (engine.match("person")
            .where("age", ">=", 25)
            .where("city", "IN", ["NYC", "LA"])
            .order_by("salary", "DESC")
            .limit(5)
            .return_fields("name", "salary")
            .execute())
        assert result.count <= 5


class TestEdgeQueryBuilder:
    """Test EdgeQueryBuilder fluent API."""

    def test_match_edges_basic(self, engine):
        """Test basic edge matching."""
        result = engine.match_edges("KNOWS").execute()
        assert result.count == 6

    def test_match_edges_with_where(self, engine):
        """Test edge matching with where condition."""
        result = (engine.match_edges("KNOWS")
            .where("since", ">", 2019)
            .execute())
        for item in result.data:
            assert item['properties']['since'] > 2019

    def test_match_edges_limit(self, engine):
        """Test edge matching with limit."""
        result = (engine.match_edges("KNOWS")
            .limit(3)
            .execute())
        assert result.count == 3

    def test_match_edges_all_types(self, engine):
        """Test matching all edge types."""
        result = engine.match_edges().execute()
        assert result.count > 6  # KNOWS + WORKS_AT + WORKS_ON

    def test_match_edges_invalid_operator_raises(self, engine):
        """Unknown operators raise instead of silently becoming EQ."""
        with pytest.raises(ValueError) as exc_info:
            engine.match_edges("KNOWS").where("since", "LIKE", 2020)
        assert "Unknown operator" in str(exc_info.value)


# =============================================================================
# QueryResult Tests
# =============================================================================

class TestQueryResult:
    """Test QueryResult class."""

    def test_result_iteration(self, engine):
        """Test iterating over results."""
        result = engine.execute("NODES person LIMIT 3")
        count = 0
        for item in result:
            count += 1
        assert count == 3

    def test_result_len(self, engine):
        """Test len() on result."""
        result = engine.execute("NODES person")
        assert len(result) == 6

    def test_result_first(self, engine):
        """Test first() method."""
        result = engine.execute("NODES person ORDER BY age ASC")
        first = result.first()
        assert first['properties']['age'] == 25  # Bob is youngest

    def test_result_first_empty(self, engine):
        """Test first() on empty result."""
        result = engine.execute("NODES person WHERE age > 100")
        assert result.first() is None

    def test_result_to_list(self, engine):
        """Test to_list() method."""
        result = engine.execute("NODES person LIMIT 3")
        lst = result.to_list()
        assert isinstance(lst, list)
        assert len(lst) == 3

    def test_result_repr(self, engine):
        """Test result string representation."""
        result = engine.execute("NODES person")
        repr_str = repr(result)
        assert 'count=6' in repr_str
        assert 'time=' in repr_str

    def test_result_execution_time(self, engine):
        """Test execution time is recorded."""
        result = engine.execute("NODES person")
        assert result.execution_time_ms >= 0

    def test_result_query_string(self, engine):
        """Test query string is preserved."""
        query = "NODES person WHERE age > 25"
        result = engine.execute(query)
        assert result.query == query

    def test_result_query_type(self, engine):
        """Test query type is recorded."""
        result = engine.execute("COUNT person")
        assert result.query_type == 'COUNT'


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Test error handling in query execution."""

    def test_invalid_query_syntax(self, engine):
        """Test invalid query syntax raises error."""
        with pytest.raises(ValueError) as exc_info:
            engine.execute("INVALID QUERY")
        assert "Unknown query type" in str(exc_info.value)

    def test_invalid_operator(self, parser):
        """Test invalid operator raises a clear parse error."""
        with pytest.raises(ValueError, match="unknown operator"):
            parser.parse("NODES person WHERE age INVALID 25")

    def test_missing_node_type_in_path(self, parser):
        """Test missing components in PATH query."""
        with pytest.raises(ValueError):
            parser.parse("PATH TO person:bob")

    def test_traverse_non_existent_node(self, engine):
        """Test traversal from non-existent node."""
        result = engine.execute("TRAVERSE person:99999 -> KNOWS -> person")
        assert result.count == 0

    def test_path_non_existent_nodes(self, engine):
        """Test path between non-existent nodes."""
        result = engine.execute("PATH person:99998 TO person:99999")
        assert result.count == 0


# =============================================================================
# Edge Cases and Complex Queries
# =============================================================================

class TestEdgeCases:
    """Test edge cases and complex queries."""

    def test_empty_graph_nodes(self, empty_graph):
        """Test NODES query on empty graph."""
        engine = QueryEngine(empty_graph)
        result = engine.execute("NODES person")
        assert result.count == 0

    def test_empty_graph_edges(self, empty_graph):
        """Test EDGES query on empty graph."""
        engine = QueryEngine(empty_graph)
        result = engine.execute("EDGES KNOWS")
        assert result.count == 0

    def test_empty_graph_count(self, empty_graph):
        """Test COUNT on empty graph."""
        engine = QueryEngine(empty_graph)
        result = engine.execute("COUNT person")
        assert result.data[0] == 0

    def test_special_characters_in_string(self, engine):
        """Test handling special characters in strings."""
        engine.graph.add_node('person', 'special', name="O'Brien", age=45)
        result = engine.execute("NODES person WHERE name CONTAINS Brien")
        assert result.count >= 1

    def test_numeric_string_id(self, engine):
        """Test node with numeric string ID."""
        engine.graph.add_node('item', '123', name='Item 123')
        result = engine.execute("NODES item")
        assert result.count == 1

    def test_unicode_in_properties(self, engine):
        """Test unicode characters in properties."""
        engine.graph.add_node('person', 'unicode', name='日本語', city='東京')
        result = engine.execute("NODES person WHERE name = 日本語")
        assert result.count == 1

    def test_very_long_traversal(self, engine):
        """Test traversal with high max depth."""
        result = engine.execute("TRAVERSE person:1 -> KNOWS -> person MAX 10")
        # Should complete without error
        assert result.count >= 0

    def test_case_sensitivity_keywords(self, parser):
        """Test that keywords are case-insensitive."""
        result1 = parser.parse("NODES person")
        result2 = parser.parse("nodes person")
        result3 = parser.parse("Nodes Person")
        assert result1['type'] == result2['type'] == result3['type']

    def test_whitespace_handling(self, parser):
        """Test handling of extra whitespace."""
        result = parser.parse("  NODES   person   WHERE   age  >  25  ")
        assert result['type'] == 'NODES'
        assert result['node_type'] == 'person'

    def test_query_with_return_all_fields(self, engine):
        """Test query without RETURN returns all data."""
        result = engine.execute("NODES person LIMIT 1")
        item = result.data[0]
        assert 'type' in item
        assert 'id' in item
        assert 'properties' in item

    def test_complex_multi_condition_query(self, engine):
        """Test complex query with many conditions."""
        result = engine.execute(
            "NODES person WHERE age >= 25 AND age <= 35 AND city = NYC ORDER BY age DESC LIMIT 2"
        )
        assert result.count <= 2
        for item in result.data:
            age = item['properties']['age']
            assert 25 <= age <= 35


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests combining multiple features."""

    def test_full_workflow(self):
        """Test complete query workflow."""
        # Create graph
        graph = ISONGraph()
        graph.add_node('user', 1, name='Alice', score=100)
        graph.add_node('user', 2, name='Bob', score=85)
        graph.add_node('user', 3, name='Charlie', score=92)
        graph.add_edge('FOLLOWS', ('user', 1), ('user', 2))
        graph.add_edge('FOLLOWS', ('user', 2), ('user', 3))

        engine = QueryEngine(graph)

        # Test various queries
        nodes_result = engine.execute("NODES user WHERE score > 90")
        assert nodes_result.count == 2

        count_result = engine.execute("COUNT user")
        assert count_result.data[0] == 3

        avg_result = engine.execute("AVG user.score")
        assert abs(avg_result.data[0] - 92.33) < 1

        traverse_result = engine.execute("TRAVERSE user:1 -> FOLLOWS -> user MAX 2")
        assert traverse_result.count >= 1

        path_result = engine.execute("PATH user:1 TO user:3 VIA FOLLOWS")
        assert path_result.count == 1

    def test_fluent_and_string_equivalence(self, engine):
        """Test that fluent API and string queries produce same results."""
        string_result = engine.execute("NODES person WHERE age > 30 ORDER BY age ASC LIMIT 2")

        fluent_result = (engine.match("person")
            .where("age", ">", 30)
            .order_by("age", "ASC")
            .limit(2)
            .execute())

        assert string_result.count == fluent_result.count
        assert len(string_result.data) == len(fluent_result.data)

    def test_query_after_graph_modification(self, engine):
        """Test queries after modifying graph."""
        initial_count = engine.execute("COUNT person").data[0]

        engine.graph.add_node('person', 100, name='NewPerson', age=50, city='Boston', salary=70000)

        new_count = engine.execute("COUNT person").data[0]
        assert new_count == initial_count + 1

        result = engine.execute("NODES person WHERE city = Boston")
        assert result.count == 1

    def test_multiple_engines_same_graph(self, social_graph):
        """Test multiple engines on same graph."""
        engine1 = QueryEngine(social_graph)
        engine2 = QueryEngine(social_graph)

        result1 = engine1.execute("COUNT person")
        result2 = engine2.execute("COUNT person")

        assert result1.data[0] == result2.data[0]


# =============================================================================
# Performance Sanity Tests
# =============================================================================

class TestPerformance:
    """Basic performance sanity tests."""

    def test_large_result_set(self):
        """Test handling larger result sets."""
        graph = ISONGraph()
        for i in range(100):
            graph.add_node('item', i, value=i, category=i % 10)

        engine = QueryEngine(graph)
        result = engine.execute("NODES item")
        assert result.count == 100

    def test_many_conditions(self):
        """Test query with many conditions."""
        graph = ISONGraph()
        graph.add_node('data', 1, a=1, b=2, c=3, d=4, e=5)

        engine = QueryEngine(graph)
        result = engine.execute("NODES data WHERE a = 1 AND b = 2 AND c = 3 AND d = 4 AND e = 5")
        assert result.count == 1

    def test_deep_traversal(self):
        """Test deep traversal performance."""
        graph = ISONGraph()
        # Create chain: 1 -> 2 -> 3 -> ... -> 20
        for i in range(1, 21):
            graph.add_node('node', i)
        for i in range(1, 20):
            graph.add_edge('NEXT', ('node', i), ('node', i + 1))

        engine = QueryEngine(graph)
        result = engine.execute("PATH node:1 TO node:20 VIA NEXT MAX 25")
        assert result.count == 1
        assert result.data[0]['length'] == 19


class TestParserRobustness:
    """Postfix EXISTS / NOT IN support and malformed-input errors."""

    def _engine(self):
        graph = ISONGraph("parser_robustness")
        graph.add_node("person", "1", name="Alice", email="a@x.com", city="NYC")
        graph.add_node("person", "2", name="Bob", city="LA")
        return QueryEngine(graph)

    def test_exists_postfix(self):
        engine = self._engine()
        result = engine.execute("NODES person WHERE email EXISTS")
        assert result.count == 1

    def test_not_exists_postfix(self):
        engine = self._engine()
        result = engine.execute("NODES person WHERE email NOT EXISTS")
        assert result.count == 1
        assert result.data[0]['properties']['name'] == 'Bob'

    def test_not_in_list(self):
        engine = self._engine()
        result = engine.execute("NODES person WHERE city NOT IN ('NYC')")
        assert result.count == 1
        assert result.data[0]['properties']['name'] == 'Bob'

    def test_unknown_operator_raises(self):
        engine = self._engine()
        with pytest.raises(ValueError):
            engine.execute("NODES person WHERE name LIKE 'A%'")

    def test_unclosed_list_raises(self):
        engine = self._engine()
        with pytest.raises(ValueError):
            engine.execute("NODES person WHERE city IN ('NYC', 'LA'")

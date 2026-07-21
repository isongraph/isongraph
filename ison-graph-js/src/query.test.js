/**
 * Tests for ISONQL - JavaScript Implementation
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { ISONGraph, Direction } from './index.js';
import {
  QueryEngine,
  QueryBuilder,
  EdgeQueryBuilder,
  ISONQLParser,
  QueryResult,
  Condition,
  Operator,
} from './query.js';

// =============================================================================
// Test Fixtures
// =============================================================================

function createSimpleGraph() {
  const graph = new ISONGraph();
  graph.addNode('person', 'alice', { name: 'Alice', age: 30, status: 'active' });
  graph.addNode('person', 'bob', { name: 'Bob', age: 25, status: 'active' });
  graph.addNode('person', 'charlie', { name: 'Charlie', age: 35, status: 'inactive' });
  graph.addEdge('KNOWS', ['person', 'alice'], ['person', 'bob'], { since: 2020, strength: 0.8 });
  graph.addEdge('KNOWS', ['person', 'bob'], ['person', 'charlie'], { since: 2021, strength: 0.5 });
  return graph;
}

function createSocialGraph() {
  const graph = new ISONGraph();

  // People
  graph.addNode('person', 1, { name: 'Alice', age: 30, city: 'NYC', salary: 80000 });
  graph.addNode('person', 2, { name: 'Bob', age: 25, city: 'LA', salary: 60000 });
  graph.addNode('person', 3, { name: 'Charlie', age: 35, city: 'NYC', salary: 90000 });
  graph.addNode('person', 4, { name: 'Diana', age: 28, city: 'Chicago', salary: 75000 });
  graph.addNode('person', 5, { name: 'Eve', age: 32, city: 'NYC', salary: 85000 });
  graph.addNode('person', 6, { name: 'Frank', age: 40, city: 'LA', salary: 100000 });

  // Companies
  graph.addNode('company', 100, { name: 'TechCorp', employees: 500, industry: 'tech' });
  graph.addNode('company', 101, { name: 'FinanceInc', employees: 200, industry: 'finance' });

  // KNOWS relationships
  graph.addEdge('KNOWS', ['person', 1], ['person', 2], { since: 2018, close: true });
  graph.addEdge('KNOWS', ['person', 1], ['person', 3], { since: 2019, close: false });
  graph.addEdge('KNOWS', ['person', 2], ['person', 4], { since: 2020, close: true });
  graph.addEdge('KNOWS', ['person', 3], ['person', 5], { since: 2017, close: true });
  graph.addEdge('KNOWS', ['person', 4], ['person', 5], { since: 2021, close: false });
  graph.addEdge('KNOWS', ['person', 5], ['person', 6], { since: 2016, close: true });

  // WORKS_AT relationships
  graph.addEdge('WORKS_AT', ['person', 1], ['company', 100], { role: 'Engineer', years: 5 });
  graph.addEdge('WORKS_AT', ['person', 2], ['company', 100], { role: 'Designer', years: 2 });
  graph.addEdge('WORKS_AT', ['person', 3], ['company', 101], { role: 'Manager', years: 8 });

  return graph;
}

// =============================================================================
// Parser Tests
// =============================================================================

describe('ISONQLParser', () => {
  let parser;

  beforeEach(() => {
    parser = new ISONQLParser();
  });

  describe('tokenization', () => {
    it('should tokenize simple query', () => {
      const result = parser.parse('NODES person');
      expect(result.type).toBe('NODES');
      expect(result.nodeType).toBe('person');
    });

    it('should tokenize query with string literals', () => {
      const result = parser.parse('NODES person WHERE name = "Alice"');
      expect(result.conditions[0].value).toBe('Alice');
    });

    it('should tokenize multi-char operators', () => {
      const result = parser.parse('NODES person WHERE age >= 25');
      expect(result.conditions[0].operator).toBe(Operator.GE);
    });
  });

  describe('NODES parsing', () => {
    it('should parse basic NODES query', () => {
      const result = parser.parse('NODES person');
      expect(result.type).toBe('NODES');
      expect(result.nodeType).toBe('person');
      expect(result.conditions).toHaveLength(0);
    });

    it('should parse NODES with WHERE', () => {
      const result = parser.parse('NODES person WHERE age > 25');
      expect(result.conditions).toHaveLength(1);
      expect(result.conditions[0].field).toBe('age');
      expect(result.conditions[0].operator).toBe(Operator.GT);
      expect(result.conditions[0].value).toBe(25);
    });

    it('should parse NODES with ORDER BY', () => {
      const result = parser.parse('NODES person ORDER BY name DESC');
      expect(result.orderBy).toBe('name');
      expect(result.orderDir).toBe('DESC');
    });

    it('should parse NODES with LIMIT and OFFSET', () => {
      const result = parser.parse('NODES person LIMIT 10 OFFSET 5');
      expect(result.limit).toBe(10);
      expect(result.offset).toBe(5);
    });

    it('should parse NODES shorthand syntax', () => {
      const result = parser.parse('NODES person(name="Alice", age=30)');
      expect(result.nodeType).toBe('person');
      expect(result.conditions).toHaveLength(2);
    });
  });

  describe('EDGES parsing', () => {
    it('should parse basic EDGES query', () => {
      const result = parser.parse('EDGES KNOWS');
      expect(result.type).toBe('EDGES');
      expect(result.relType).toBe('KNOWS');
    });

    it('should parse EDGES with WHERE', () => {
      const result = parser.parse('EDGES KNOWS WHERE since > 2020');
      expect(result.conditions[0].field).toBe('since');
    });
  });

  describe('TRAVERSE parsing', () => {
    it('should parse TRAVERSE query', () => {
      const result = parser.parse('TRAVERSE person:alice -> KNOWS -> person');
      expect(result.type).toBe('TRAVERSE');
      expect(result.start).toEqual(['person', 'alice']);
      expect(result.pattern).toHaveLength(1);
      expect(result.pattern[0].relType).toBe('KNOWS');
    });

    it('should parse TRAVERSE with MAX', () => {
      const result = parser.parse('TRAVERSE person:1 -> KNOWS -> person MAX 3');
      expect(result.maxDepth).toBe(3);
    });
  });

  describe('PATH parsing', () => {
    it('should parse PATH query', () => {
      const result = parser.parse('PATH person:alice TO person:bob');
      expect(result.type).toBe('PATH');
      expect(result.source).toEqual(['person', 'alice']);
      expect(result.target).toEqual(['person', 'bob']);
    });

    it('should parse PATH with VIA', () => {
      const result = parser.parse('PATH person:1 TO person:5 VIA KNOWS MAX 5');
      expect(result.via).toBe('KNOWS');
      expect(result.maxHops).toBe(5);
    });
  });

  describe('aggregation parsing', () => {
    it('should parse COUNT query', () => {
      const result = parser.parse('COUNT person WHERE age > 25');
      expect(result.type).toBe('COUNT');
      expect(result.nodeType).toBe('person');
    });

    it('should parse SUM query', () => {
      const result = parser.parse('SUM person.salary');
      expect(result.type).toBe('SUM');
      expect(result.property).toBe('salary');
    });

    it('should parse AVG query', () => {
      const result = parser.parse('AVG person.age');
      expect(result.type).toBe('AVG');
      expect(result.property).toBe('age');
    });
  });

  describe('error handling', () => {
    it('should throw on invalid query type', () => {
      expect(() => parser.parse('INVALID person')).toThrow('Unknown query type');
    });

    it('should throw on empty query', () => {
      expect(() => parser.parse('')).toThrow('Empty query');
    });
  });
});

// =============================================================================
// Condition Tests
// =============================================================================

describe('Condition', () => {
  it('should evaluate EQ operator', () => {
    const cond = new Condition('name', Operator.EQ, 'Alice');
    expect(cond.evaluate({ name: 'Alice' })).toBe(true);
    expect(cond.evaluate({ name: 'Bob' })).toBe(false);
  });

  it('should evaluate GT operator', () => {
    const cond = new Condition('age', Operator.GT, 25);
    expect(cond.evaluate({ age: 30 })).toBe(true);
    expect(cond.evaluate({ age: 25 })).toBe(false);
  });

  it('should evaluate IN operator', () => {
    const cond = new Condition('city', Operator.IN, ['NYC', 'LA']);
    expect(cond.evaluate({ city: 'NYC' })).toBe(true);
    expect(cond.evaluate({ city: 'Chicago' })).toBe(false);
  });

  it('should evaluate CONTAINS operator', () => {
    const cond = new Condition('name', Operator.CONTAINS, 'lic');
    expect(cond.evaluate({ name: 'Alice' })).toBe(true);
    expect(cond.evaluate({ name: 'Bob' })).toBe(false);
  });

  it('should evaluate EXISTS operator', () => {
    const cond = new Condition('email', Operator.EXISTS, null);
    expect(cond.evaluate({ email: 'test@test.com' })).toBe(true);
    expect(cond.evaluate({ name: 'Alice' })).toBe(false);
  });

  it('should return false for missing field', () => {
    const cond = new Condition('missing', Operator.EQ, 'value');
    expect(cond.evaluate({ other: 'value' })).toBe(false);
  });
});

// =============================================================================
// NODES Query Tests
// =============================================================================

describe('NODES Query', () => {
  let engine;

  beforeEach(() => {
    engine = new QueryEngine(createSocialGraph());
  });

  it('should select all nodes of type', () => {
    const result = engine.execute('NODES person');
    expect(result.count).toBe(6);
  });

  it('should filter with WHERE', () => {
    const result = engine.execute('NODES person WHERE age > 30');
    expect(result.count).toBe(3); // Charlie (35), Eve (32), Frank (40)
  });

  it('should filter with multiple conditions', () => {
    const result = engine.execute('NODES person WHERE age > 25 AND city = NYC');
    expect(result.count).toBe(3);
  });

  it('should order results', () => {
    const result = engine.execute('NODES person ORDER BY age ASC');
    const ages = result.data.map(n => n.properties.age);
    expect(ages).toEqual([...ages].sort((a, b) => a - b));
  });

  it('should limit results', () => {
    const result = engine.execute('NODES person LIMIT 3');
    expect(result.count).toBe(3);
    expect(result.totalCount).toBe(6);
  });

  it('should apply offset', () => {
    const result = engine.execute('NODES person ORDER BY age ASC LIMIT 2 OFFSET 2');
    expect(result.count).toBe(2);
  });

  it('should project fields with RETURN', () => {
    const result = engine.execute('NODES person RETURN name, age');
    expect(result.data[0]).toHaveProperty('name');
    expect(result.data[0]).toHaveProperty('age');
    expect(result.data[0]).not.toHaveProperty('city');
  });
});

// =============================================================================
// EDGES Query Tests
// =============================================================================

describe('EDGES Query', () => {
  let engine;

  beforeEach(() => {
    engine = new QueryEngine(createSocialGraph());
  });

  it('should select all edges of type', () => {
    const result = engine.execute('EDGES KNOWS');
    expect(result.count).toBe(6);
  });

  it('should filter with WHERE', () => {
    const result = engine.execute('EDGES KNOWS WHERE since > 2019');
    for (const edge of result.data) {
      expect(edge.properties.since).toBeGreaterThan(2019);
    }
  });

  it('should limit results', () => {
    const result = engine.execute('EDGES KNOWS LIMIT 3');
    expect(result.count).toBe(3);
  });
});

// =============================================================================
// TRAVERSE Query Tests
// =============================================================================

describe('TRAVERSE Query', () => {
  let engine;

  beforeEach(() => {
    engine = new QueryEngine(createSocialGraph());
  });

  it('should traverse single hop', () => {
    const result = engine.execute('TRAVERSE person:1 -> KNOWS -> person');
    expect(result.count).toBe(2); // Alice knows Bob and Charlie
  });

  it('should traverse with MAX depth', () => {
    const result = engine.execute('TRAVERSE person:1 -> KNOWS -> person MAX 2');
    expect(result.count).toBeGreaterThanOrEqual(2);
  });

  it('should handle string IDs', () => {
    const graph = createSimpleGraph();
    const eng = new QueryEngine(graph);
    const result = eng.execute('TRAVERSE person:alice -> KNOWS -> person');
    expect(result.count).toBeGreaterThanOrEqual(1);
  });
});

// =============================================================================
// PATH Query Tests
// =============================================================================

describe('PATH Query', () => {
  let engine;

  beforeEach(() => {
    engine = new QueryEngine(createSocialGraph());
  });

  it('should find direct path', () => {
    const result = engine.execute('PATH person:1 TO person:2');
    expect(result.count).toBe(1);
    expect(result.data[0].length).toBe(1);
  });

  it('should find multi-hop path', () => {
    const result = engine.execute('PATH person:1 TO person:5 VIA KNOWS');
    expect(result.count).toBe(1);
  });

  it('should return empty for no path', () => {
    engine.getGraph().addNode('person', 999, { name: 'Isolated' });
    const result = engine.execute('PATH person:1 TO person:999 MAX 5');
    expect(result.count).toBe(0);
  });
});

// =============================================================================
// COUNT Query Tests
// =============================================================================

describe('COUNT Query', () => {
  let engine;

  beforeEach(() => {
    engine = new QueryEngine(createSocialGraph());
  });

  it('should count all of type', () => {
    const result = engine.execute('COUNT person');
    expect(result.data[0]).toBe(6);
  });

  it('should count with condition', () => {
    const result = engine.execute('COUNT person WHERE age > 30');
    expect(result.data[0]).toBe(3); // Charlie (35), Eve (32), Frank (40)
  });
});

// =============================================================================
// Aggregation Query Tests
// =============================================================================

describe('Aggregation Queries', () => {
  let engine;

  beforeEach(() => {
    engine = new QueryEngine(createSocialGraph());
  });

  it('should calculate SUM', () => {
    const result = engine.execute('SUM person.salary');
    expect(result.data[0]).toBe(80000 + 60000 + 90000 + 75000 + 85000 + 100000);
  });

  it('should calculate AVG', () => {
    const result = engine.execute('AVG person.age');
    const ages = [30, 25, 35, 28, 32, 40];
    const expected = ages.reduce((a, b) => a + b, 0) / ages.length;
    expect(result.data[0]).toBeCloseTo(expected, 2);
  });

  it('should calculate MIN', () => {
    const result = engine.execute('MIN person.age');
    expect(result.data[0]).toBe(25);
  });

  it('should calculate MAX', () => {
    const result = engine.execute('MAX person.age');
    expect(result.data[0]).toBe(40);
  });

  it('should return null for no matches', () => {
    const result = engine.execute('SUM person.salary WHERE age > 100');
    expect(result.data[0]).toBeNull();
  });
});

// =============================================================================
// Fluent API Tests
// =============================================================================

describe('QueryBuilder Fluent API', () => {
  let engine;

  beforeEach(() => {
    engine = new QueryEngine(createSocialGraph());
  });

  it('should build basic query', () => {
    const result = engine.match('person').execute();
    expect(result.count).toBe(6);
  });

  it('should chain where conditions', () => {
    const result = engine
      .match('person')
      .where('age', '>', 30)
      .execute();
    expect(result.count).toBe(3); // Charlie (35), Eve (32), Frank (40)
  });

  it('should chain multiple where', () => {
    const result = engine
      .match('person')
      .where('age', '>', 25)
      .where('city', '=', 'NYC')
      .execute();
    expect(result.count).toBe(3);
  });

  it('should apply orderBy', () => {
    const result = engine
      .match('person')
      .orderBy('age', 'ASC')
      .execute();
    const ages = result.data.map(n => n.properties.age);
    expect(ages).toEqual([...ages].sort((a, b) => a - b));
  });

  it('should apply limit', () => {
    const result = engine
      .match('person')
      .limit(3)
      .execute();
    expect(result.count).toBe(3);
  });

  it('should apply offset', () => {
    const result = engine
      .match('person')
      .orderBy('age', 'ASC')
      .offset(2)
      .limit(2)
      .execute();
    expect(result.count).toBe(2);
  });

  it('should project fields', () => {
    const result = engine
      .match('person')
      .returnFields('name', 'age')
      .execute();
    expect(result.data[0]).toHaveProperty('name');
    expect(result.data[0]).not.toHaveProperty('city');
  });

  it('should count', () => {
    const count = engine
      .match('person')
      .where('age', '>', 30)
      .count();
    expect(count).toBe(3); // Charlie (35), Eve (32), Frank (40)
  });
});

describe('EdgeQueryBuilder Fluent API', () => {
  let engine;

  beforeEach(() => {
    engine = new QueryEngine(createSocialGraph());
  });

  it('should match edges', () => {
    const result = engine.matchEdges('KNOWS').execute();
    expect(result.count).toBe(6);
  });

  it('should filter edges', () => {
    const result = engine
      .matchEdges('KNOWS')
      .where('since', '>', 2019)
      .execute();
    for (const edge of result.data) {
      expect(edge.properties.since).toBeGreaterThan(2019);
    }
  });

  it('should limit edges', () => {
    const result = engine
      .matchEdges('KNOWS')
      .limit(3)
      .execute();
    expect(result.count).toBe(3);
  });
});

// =============================================================================
// QueryResult Tests
// =============================================================================

describe('QueryResult', () => {
  let engine;

  beforeEach(() => {
    engine = new QueryEngine(createSocialGraph());
  });

  it('should be iterable', () => {
    const result = engine.execute('NODES person LIMIT 3');
    let count = 0;
    for (const _ of result) {
      count++;
    }
    expect(count).toBe(3);
  });

  it('should return first item', () => {
    const result = engine.execute('NODES person ORDER BY age ASC');
    const first = result.first();
    expect(first?.properties.age).toBe(25);
  });

  it('should return undefined for empty first', () => {
    const result = engine.execute('NODES person WHERE age > 100');
    expect(result.first()).toBeUndefined();
  });

  it('should convert to list', () => {
    const result = engine.execute('NODES person LIMIT 3');
    const list = result.toList();
    expect(Array.isArray(list)).toBe(true);
    expect(list).toHaveLength(3);
  });

  it('should have length property', () => {
    const result = engine.execute('NODES person');
    expect(result.length).toBe(6);
  });

  it('should record execution time', () => {
    const result = engine.execute('NODES person');
    expect(result.executionTimeMs).toBeGreaterThanOrEqual(0);
  });

  it('should preserve query string', () => {
    const query = 'NODES person WHERE age > 25';
    const result = engine.execute(query);
    expect(result.query).toBe(query);
  });

  it('should record query type', () => {
    const result = engine.execute('COUNT person');
    expect(result.queryType).toBe('COUNT');
  });
});

// =============================================================================
// Error Handling Tests
// =============================================================================

describe('Error Handling', () => {
  let engine;

  beforeEach(() => {
    engine = new QueryEngine(createSocialGraph());
  });

  it('should throw on invalid query', () => {
    expect(() => engine.execute('INVALID QUERY')).toThrow();
  });

  it('should handle empty result gracefully', () => {
    const result = engine.execute('NODES person WHERE age > 100');
    expect(result.count).toBe(0);
    expect(result.data).toEqual([]);
  });
});

// =============================================================================
// Parser Robustness Tests
// =============================================================================

describe('Parser Robustness', () => {
  let engine;

  beforeEach(() => {
    const graph = new ISONGraph();
    graph.addNode('person', 1, { name: 'Alice', email: 'a@x.com', city: 'NYC' });
    graph.addNode('person', 2, { name: 'Bob', city: 'LA' });
    engine = new QueryEngine(graph);
  });

  it('should support postfix EXISTS', () => {
    expect(engine.execute('NODES person WHERE email EXISTS').count).toBe(1);
  });

  it('should support postfix NOT EXISTS', () => {
    expect(engine.execute('NODES person WHERE email NOT EXISTS').count).toBe(1);
  });

  it('should support NOT IN lists', () => {
    expect(engine.execute("NODES person WHERE city NOT IN ('NYC')").count).toBe(1);
  });

  it('should throw on unknown operators', () => {
    expect(() => engine.execute("NODES person WHERE name LIKE 'A%'")).toThrow(/unknown operator/);
  });
});

// =============================================================================
// Integration Tests
// =============================================================================

describe('Integration', () => {
  it('should work with full workflow', () => {
    const graph = new ISONGraph();
    graph.addNode('user', 1, { name: 'Alice', score: 100 });
    graph.addNode('user', 2, { name: 'Bob', score: 85 });
    graph.addNode('user', 3, { name: 'Charlie', score: 92 });
    graph.addEdge('FOLLOWS', ['user', 1], ['user', 2]);
    graph.addEdge('FOLLOWS', ['user', 2], ['user', 3]);

    const engine = new QueryEngine(graph);

    const nodes = engine.execute('NODES user WHERE score > 90');
    expect(nodes.count).toBe(2);

    const count = engine.execute('COUNT user');
    expect(count.data[0]).toBe(3);

    const avg = engine.execute('AVG user.score');
    expect(avg.data[0]).toBeCloseTo(92.33, 1);

    const traverse = engine.execute('TRAVERSE user:1 -> FOLLOWS -> user MAX 2');
    expect(traverse.count).toBeGreaterThanOrEqual(1);

    const path = engine.execute('PATH user:1 TO user:3 VIA FOLLOWS');
    expect(path.count).toBe(1);
  });

  it('should produce equivalent results from fluent and string API', () => {
    const engine = new QueryEngine(createSocialGraph());

    const stringResult = engine.execute('NODES person WHERE age > 30 ORDER BY age ASC LIMIT 2');
    const fluentResult = engine
      .match('person')
      .where('age', '>', 30)
      .orderBy('age', 'ASC')
      .limit(2)
      .execute();

    expect(stringResult.count).toBe(fluentResult.count);
    expect(stringResult.data.length).toBe(fluentResult.data.length);
  });
});

// =============================================================================
// Malformed Query Tests
// =============================================================================

describe('Malformed Queries', () => {
  let engine;

  beforeEach(() => {
    engine = new QueryEngine(createSocialGraph());
  });

  it('should throw on unclosed IN value list', () => {
    expect(() => engine.execute('NODES person WHERE x IN (1, 2')).toThrow('Parse error');
  });

  it('should throw on unclosed shorthand condition list', () => {
    expect(() => engine.execute('NODES person(name="Alice"')).toThrow('Parse error');
  });

  it('should not accept prototype members as operators', () => {
    // 'toString' lives on Object.prototype; it must not be treated as a
    // comparison operator from the operator map
    expect(() => engine.execute('NODES person WHERE name toString Alice'))
      .toThrow(/unknown operator/);
  });
});

// =============================================================================
// OR Condition Tests
// =============================================================================

describe('OR Conditions', () => {
  let engine;

  beforeEach(() => {
    engine = new QueryEngine(createSocialGraph());
  });

  it('should parse OR into condition groups', () => {
    const parser = new ISONQLParser();
    const result = parser.parse('NODES person WHERE age > 30 OR city = Chicago');
    expect(result.conditions).toHaveLength(2);
    expect(Array.isArray(result.conditions[0])).toBe(true);
  });

  it('should evaluate OR conditions', () => {
    const result = engine.execute('NODES person WHERE city = LA OR city = Chicago');
    expect(result.count).toBe(3); // Bob (LA), Frank (LA), Diana (Chicago)
  });

  it('should give AND higher precedence than OR', () => {
    // Parsed as (age > 30 AND city = NYC) OR city = Chicago
    const result = engine.execute('NODES person WHERE age > 30 AND city = NYC OR city = Chicago');
    expect(result.count).toBe(3); // Charlie, Eve, Diana
  });

  it('should evaluate OR in COUNT queries', () => {
    const result = engine.execute('COUNT person WHERE city = LA OR city = NYC');
    expect(result.data[0]).toBe(5);
  });
});

// =============================================================================
// Tokenizer type:id Tests
// =============================================================================

describe('Tokenizer type:id refs', () => {
  it('should tokenize type:id node refs as one token', () => {
    const parser = new ISONQLParser();
    const result = parser.parse('TRAVERSE person:1 -> KNOWS -> person');
    expect(result.start).toEqual(['person', 1]);
  });

  it('should execute TRAVERSE with numeric type:id refs', () => {
    const engine = new QueryEngine(createSocialGraph());
    const result = engine.execute('TRAVERSE person:1 -> KNOWS -> person');
    expect(result.count).toBe(2);
  });
});

// =============================================================================
// LIMIT / OFFSET Edge Cases
// =============================================================================

describe('LIMIT and OFFSET edge cases', () => {
  let engine;

  beforeEach(() => {
    engine = new QueryEngine(createSocialGraph());
  });

  it('should honor LIMIT 0', () => {
    const result = engine.execute('NODES person LIMIT 0');
    expect(result.count).toBe(0);
    expect(result.totalCount).toBe(6);
  });

  it('should honor OFFSET 0', () => {
    const result = engine.execute('NODES person LIMIT 10 OFFSET 0');
    expect(result.count).toBe(6);
  });

  it('should honor limit(0) in fluent API', () => {
    const result = engine.match('person').limit(0).execute();
    expect(result.count).toBe(0);
  });
});

// =============================================================================
// ORDER BY Missing Field Tests
// =============================================================================

describe('ORDER BY with missing fields', () => {
  function createPartialGraph() {
    const graph = new ISONGraph();
    graph.addNode('item', 1, { name: 'a', price: 30 });
    graph.addNode('item', 2, { name: 'b' });
    graph.addNode('item', 3, { name: 'c', price: 10 });
    return graph;
  }

  it('should sort nodes missing the field last (ASC)', () => {
    const engine = new QueryEngine(createPartialGraph());
    const result = engine.execute('NODES item ORDER BY price ASC');
    const names = result.data.map(n => n.properties.name);
    expect(names).toEqual(['c', 'a', 'b']);
  });

  it('should sort nodes missing the field last (DESC)', () => {
    const engine = new QueryEngine(createPartialGraph());
    const result = engine.execute('NODES item ORDER BY price DESC');
    const names = result.data.map(n => n.properties.name);
    expect(names).toEqual(['a', 'c', 'b']);
  });
});

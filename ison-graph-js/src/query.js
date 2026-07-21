/**
 * ISONQL - Pure Property Graph Query Language for ISONGraph (JavaScript)
 *
 * A declarative query language for property graph operations.
 *
 * Supported Query Types:
 * - NODES: Select and filter nodes
 * - EDGES: Select and filter edges
 * - TRAVERSE: Graph traversal with patterns
 * - PATH: Shortest path finding
 * - COUNT: Count nodes matching criteria
 * - SUM/AVG/MIN/MAX: Numeric aggregations
 *
 * @example
 * ```javascript
 * import { ISONGraph } from './index.js';
 * import { QueryEngine } from './query.js';
 *
 * const graph = new ISONGraph();
 * graph.addNode('person', 'alice', { name: 'Alice', age: 30 });
 * graph.addNode('person', 'bob', { name: 'Bob', age: 25 });
 * graph.addEdge('KNOWS', ['person', 'alice'], ['person', 'bob'], { since: 2020 });
 *
 * const engine = new QueryEngine(graph);
 * const result = engine.execute("NODES person WHERE age > 25");
 * ```
 *
 * @author Mahesh Vaikri
 * @version 1.0.0
 */

import { Direction } from './index.js';

export const QUERY_VERSION = "1.0.0";

// =============================================================================
// Enums
// =============================================================================

/** Query operators for conditions */
export const Operator = {
  EQ: "=",
  NE: "!=",
  GT: ">",
  GE: ">=",
  LT: "<",
  LE: "<=",
  IN: "IN",
  NOT_IN: "NOT IN",
  CONTAINS: "CONTAINS",
  STARTS_WITH: "STARTS_WITH",
  ENDS_WITH: "ENDS_WITH",
  MATCHES: "MATCHES",
  EXISTS: "EXISTS",
  NOT_EXISTS: "NOT_EXISTS"
};

/** Sort order for results */
export const SortOrder = {
  ASC: "ASC",
  DESC: "DESC"
};

// =============================================================================
// Condition Class
// =============================================================================

/** A query condition for filtering */
export class Condition {
  constructor(field, operator, value) {
    this.field = field;
    this.operator = operator;
    this.value = value;
  }

  /** Evaluate condition against a properties object */
  evaluate(properties) {
    // EXISTS / NOT_EXISTS checks
    if (this.operator === Operator.EXISTS) {
      return this.field in properties;
    }
    if (this.operator === Operator.NOT_EXISTS) {
      return !(this.field in properties);
    }

    // Field must exist for other comparisons
    if (!(this.field in properties)) {
      return false;
    }

    const propValue = properties[this.field];

    switch (this.operator) {
      case Operator.EQ:
        return propValue === this.value;
      case Operator.NE:
        return propValue !== this.value;
      case Operator.GT:
        return propValue > this.value;
      case Operator.GE:
        return propValue >= this.value;
      case Operator.LT:
        return propValue < this.value;
      case Operator.LE:
        return propValue <= this.value;
      case Operator.IN:
        return Array.isArray(this.value) && this.value.includes(propValue);
      case Operator.NOT_IN:
        return Array.isArray(this.value) && !this.value.includes(propValue);
      case Operator.CONTAINS:
        return String(propValue).includes(this.value);
      case Operator.STARTS_WITH:
        return String(propValue).startsWith(this.value);
      case Operator.ENDS_WITH:
        return String(propValue).endsWith(this.value);
      case Operator.MATCHES:
        return new RegExp(this.value).test(String(propValue));
      default:
        return false;
    }
  }

  toString() {
    return `${this.field} ${this.operator} ${this.value}`;
  }
}

// =============================================================================
// QueryResult Class
// =============================================================================

/** Result of a query execution */
export class QueryResult {
  constructor(data, count, totalCount, executionTimeMs, query, queryType = "") {
    this.data = data;
    this.count = count;
    this.totalCount = totalCount;
    this.executionTimeMs = executionTimeMs;
    this.query = query;
    this.queryType = queryType;
  }

  /** Iterate over result data */
  *[Symbol.iterator]() {
    yield* this.data;
  }

  /** Get first result or undefined */
  first() {
    return this.data[0];
  }

  /** Return data as array */
  toList() {
    return this.data;
  }

  /** Get length */
  get length() {
    return this.count;
  }

  toString() {
    return `QueryResult(count=${this.count}, total=${this.totalCount}, time=${this.executionTimeMs.toFixed(2)}ms)`;
  }
}

// =============================================================================
// ISONQL Parser
// =============================================================================

/** Operator mappings from string to enum */
const OPERATOR_MAP = {
  '=': Operator.EQ,
  '==': Operator.EQ,
  '!=': Operator.NE,
  '<>': Operator.NE,
  '>': Operator.GT,
  '>=': Operator.GE,
  '<': Operator.LT,
  '<=': Operator.LE,
};

/** Keywords recognized by the parser */
const KEYWORDS = new Set([
  'NODES', 'EDGES', 'TRAVERSE', 'PATH', 'COUNT', 'SUM', 'AVG', 'MIN', 'MAX',
  'WHERE', 'AND', 'OR', 'NOT', 'ORDER', 'BY', 'ASC', 'DESC', 'LIMIT', 'OFFSET',
  'TO', 'VIA', 'RETURN', 'AS', 'IN', 'CONTAINS', 'STARTS_WITH',
  'ENDS_WITH', 'MATCHES', 'EXISTS', 'TRUE', 'FALSE', 'NULL', 'NONE', 'NIL'
]);

/**
 * Parser for ISONQL (ISON Query Language)
 */
export class ISONQLParser {
  constructor() {
    this.tokens = [];
    this.pos = 0;
  }

  /** Parse an ISONQL query string into a structured object */
  parse(query) {
    this.tokens = this.tokenize(query);
    this.pos = 0;

    if (this.tokens.length === 0) {
      throw new Error("Empty query");
    }

    const keyword = this.tokens[0].toUpperCase();

    switch (keyword) {
      case 'NODES':
        return this.parseNodesQuery();
      case 'EDGES':
        return this.parseEdgesQuery();
      case 'TRAVERSE':
        return this.parseTraverseQuery();
      case 'PATH':
        return this.parsePathQuery();
      case 'COUNT':
        return this.parseCountQuery();
      case 'SUM':
      case 'AVG':
      case 'MIN':
      case 'MAX':
        return this.parseAggregationQuery(keyword);
      default:
        throw new Error(`Unknown query type: ${keyword}. Supported: NODES, EDGES, TRAVERSE, PATH, COUNT, SUM, AVG, MIN, MAX`);
    }
  }

  /** Tokenize query string */
  tokenize(query) {
    const tokens = [];
    let i = 0;
    query = query.trim();

    while (i < query.length) {
      // Skip whitespace
      if (/\s/.test(query[i])) {
        i++;
        continue;
      }

      // String literals
      if (query[i] === '"' || query[i] === "'") {
        const quote = query[i];
        i++;
        const start = i;
        while (i < query.length && query[i] !== quote) {
          if (query[i] === '\\' && i + 1 < query.length) {
            i += 2;
          } else {
            i++;
          }
        }
        tokens.push(query.substring(start, i));
        i++; // Skip closing quote
        continue;
      }

      // Multi-char operators
      if (i + 1 < query.length) {
        const twoChar = query.substring(i, i + 2);
        if (['==', '!=', '>=', '<=', '<>', '->', '<-', '--'].includes(twoChar)) {
          tokens.push(twoChar);
          i += 2;
          continue;
        }
      }

      // Single-char operators and punctuation
      if ('=<>!(),.'.includes(query[i])) {
        tokens.push(query[i]);
        i++;
        continue;
      }

      // Node reference :type:id
      if (query[i] === ':') {
        const start = i;
        i++;
        while (i < query.length && /[a-zA-Z0-9:_\-]/.test(query[i])) {
          i++;
        }
        tokens.push(query.substring(start, i));
        continue;
      }

      // Words (identifiers, keywords, numbers, type:id node refs)
      if (/[a-zA-Z0-9_]/.test(query[i])) {
        const start = i;
        while (i < query.length) {
          if (/[a-zA-Z0-9_.\-]/.test(query[i])) {
            i++;
          } else if (query[i] === ':' && i + 1 < query.length && /[a-zA-Z0-9_]/.test(query[i + 1])) {
            // ':' joins a word token when immediately followed by an
            // alphanumeric/underscore, so 'type:id' node refs stay one token
            i++;
          } else {
            break;
          }
        }
        tokens.push(query.substring(start, i));
        continue;
      }

      // Skip unknown characters
      i++;
    }

    return tokens;
  }

  current() {
    return this.tokens[this.pos];
  }

  advance() {
    const token = this.current();
    this.pos++;
    return token;
  }

  expect(expected) {
    const token = this.advance();
    if (!token || token.toUpperCase() !== expected.toUpperCase()) {
      throw new Error(`Expected '${expected}', got '${token}'`);
    }
    return token;
  }

  match(...expected) {
    const current = this.current();
    if (!current) return false;
    return expected.some(e => e.toUpperCase() === current.toUpperCase());
  }

  // -------------------------------------------------------------------------
  // Query Parsers
  // -------------------------------------------------------------------------

  parseNodesQuery() {
    this.advance(); // Skip 'NODES'

    const result = {
      type: 'NODES',
      nodeType: undefined,
      conditions: [],
      orderBy: undefined,
      orderDir: 'ASC',
      limit: undefined,
      offset: undefined,
      returnFields: undefined
    };

    // Node type (optional)
    let shorthand = [];
    if (this.current() && !this.match('WHERE', 'ORDER', 'LIMIT', 'RETURN')) {
      result.nodeType = this.advance();
      // Handle shorthand: person(name="Alice")
      if (this.match('(')) {
        this.advance(); // Skip '('
        shorthand = this.parseShorthandConditions();
      }
    }

    // WHERE clause
    if (this.match('WHERE')) {
      this.advance();
      let groups = this.parseConditions();
      if (shorthand.length > 0) {
        // Shorthand conditions AND-combine with every OR-group
        groups = groups.length > 0 ? groups.map(g => [...shorthand, ...g]) : [shorthand];
      }
      result.conditions = this.normalizeGroups(groups);
    } else if (shorthand.length > 0) {
      result.conditions = shorthand;
    }

    // ORDER BY clause
    if (this.match('ORDER')) {
      this.advance();
      this.expect('BY');
      result.orderBy = this.advance();
      if (this.match('ASC', 'DESC')) {
        result.orderDir = this.advance().toUpperCase();
      }
    }

    // LIMIT clause
    if (this.match('LIMIT')) {
      this.advance();
      result.limit = parseInt(this.advance(), 10);
    }

    // OFFSET clause
    if (this.match('OFFSET')) {
      this.advance();
      result.offset = parseInt(this.advance(), 10);
    }

    // RETURN clause
    if (this.match('RETURN')) {
      this.advance();
      result.returnFields = this.parseFieldList();
    }

    return result;
  }

  parseEdgesQuery() {
    this.advance(); // Skip 'EDGES'

    const result = {
      type: 'EDGES',
      relType: undefined,
      conditions: [],
      limit: undefined
    };

    // Edge type (optional)
    if (this.current() && !this.match('WHERE', 'LIMIT')) {
      result.relType = this.advance();
    }

    // WHERE clause
    if (this.match('WHERE')) {
      this.advance();
      result.conditions = this.normalizeGroups(this.parseConditions());
    }

    // LIMIT clause
    if (this.match('LIMIT')) {
      this.advance();
      result.limit = parseInt(this.advance(), 10);
    }

    return result;
  }

  parseTraverseQuery() {
    this.advance(); // Skip 'TRAVERSE'

    const result = {
      type: 'TRAVERSE',
      start: undefined,
      pattern: [],
      maxDepth: undefined,
      limit: undefined,
      conditions: []
    };

    // Start node: type:id or :type:id
    const startToken = this.advance();
    result.start = this.parseNodeRef(startToken);

    // Parse traversal pattern: -> REL -> target
    while (this.match('->', '<-', '--')) {
      const direction = this.advance();
      const relType = this.advance();

      let targetType = '*';
      let dir2 = direction;

      // Expect another direction arrow
      if (this.match('->', '<-', '--')) {
        dir2 = this.advance();
        if (this.current() && !this.match('MAX', 'LIMIT')) {
          targetType = this.advance();
        }
      }

      result.pattern.push({
        direction: this.directionFromArrows(direction, dir2),
        relType,
        targetType
      });
    }

    // MAX depth
    if (this.match('MAX')) {
      this.advance();
      result.maxDepth = parseInt(this.advance(), 10);
    }

    // LIMIT
    if (this.match('LIMIT')) {
      this.advance();
      result.limit = parseInt(this.advance(), 10);
    }

    return result;
  }

  parsePathQuery() {
    this.advance(); // Skip 'PATH'

    const result = {
      type: 'PATH',
      source: undefined,
      target: undefined,
      via: undefined,
      maxHops: 10,
      conditions: []
    };

    // Source node
    const sourceToken = this.advance();
    result.source = this.parseNodeRef(sourceToken);

    // TO keyword
    this.expect('TO');

    // Target node
    const targetToken = this.advance();
    result.target = this.parseNodeRef(targetToken);

    // VIA relationship type (optional)
    if (this.match('VIA')) {
      this.advance();
      result.via = this.advance();
    }

    // MAX hops
    if (this.match('MAX')) {
      this.advance();
      result.maxHops = parseInt(this.advance(), 10);
    }

    return result;
  }

  parseCountQuery() {
    this.advance(); // Skip 'COUNT'

    const result = {
      type: 'COUNT',
      nodeType: undefined,
      conditions: []
    };

    // Node type
    if (this.current() && !this.match('WHERE')) {
      result.nodeType = this.advance();
    }

    // WHERE clause
    if (this.match('WHERE')) {
      this.advance();
      result.conditions = this.normalizeGroups(this.parseConditions());
    }

    return result;
  }

  parseAggregationQuery(aggType) {
    this.advance(); // Skip aggregation keyword

    const result = {
      type: aggType,
      nodeType: undefined,
      property: undefined,
      conditions: []
    };

    // type.property
    const typeProp = this.advance();
    if (typeProp.includes('.')) {
      const parts = typeProp.split('.');
      result.nodeType = parts[0];
      result.property = parts[1];
    } else {
      result.property = typeProp;
    }

    // WHERE clause
    if (this.match('WHERE')) {
      this.advance();
      result.conditions = this.normalizeGroups(this.parseConditions());
    }

    return result;
  }

  // -------------------------------------------------------------------------
  // Condition Parsing
  // -------------------------------------------------------------------------

  /**
   * Parse a WHERE condition sequence into OR-groups of AND-ed conditions.
   * `a AND b OR c` parses to [[a, b], [c]]: groups are OR-ed together,
   * conditions within a group are AND-ed (AND binds tighter than OR).
   */
  parseConditions() {
    const groups = [];
    let group = [];

    while (true) {
      const condition = this.parseSingleCondition();
      if (condition) {
        group.push(condition);
      }

      if (this.match('AND')) {
        this.advance();
        continue;
      } else if (this.match('OR')) {
        this.advance();
        if (group.length > 0) {
          groups.push(group);
          group = [];
        }
        continue;
      } else {
        break;
      }
    }

    if (group.length > 0) {
      groups.push(group);
    }

    return groups;
  }

  /**
   * Normalize OR-groups: no groups -> [], a single group collapses to a
   * flat AND-ed condition list, multiple groups stay as Condition[][].
   */
  normalizeGroups(groups) {
    if (groups.length === 0) {
      return [];
    }
    if (groups.length === 1) {
      return groups[0];
    }
    return groups;
  }

  parseSingleCondition() {
    if (!this.current()) {
      return null;
    }

    // EXISTS / NOT EXISTS
    if (this.match('EXISTS')) {
      this.advance();
      const field = this.advance();
      return new Condition(field, Operator.EXISTS, null);
    }

    if (this.match('NOT')) {
      this.advance();
      if (this.match('EXISTS')) {
        this.advance();
        const field = this.advance();
        return new Condition(field, Operator.NOT_EXISTS, null);
      }
    }

    const field = this.advance();
    if (!field || KEYWORDS.has(field.toUpperCase())) {
      this.pos--;
      return null;
    }

    // Operator
    const opToken = this.current();
    if (!opToken) {
      return null;
    }

    const opUpper = opToken.toUpperCase();
    let operator;

    if (Object.prototype.hasOwnProperty.call(OPERATOR_MAP, opToken)) {
      this.advance();
      operator = OPERATOR_MAP[opToken];
    } else if (opUpper === 'IN') {
      this.advance();
      operator = Operator.IN;
    } else if (opUpper === 'CONTAINS') {
      this.advance();
      operator = Operator.CONTAINS;
    } else if (opUpper === 'STARTS_WITH') {
      this.advance();
      operator = Operator.STARTS_WITH;
    } else if (opUpper === 'ENDS_WITH') {
      this.advance();
      operator = Operator.ENDS_WITH;
    } else if (opUpper === 'MATCHES') {
      this.advance();
      operator = Operator.MATCHES;
    } else if (opUpper === 'EXISTS') {
      this.advance();
      return new Condition(field, Operator.EXISTS, null);
    } else if (opUpper === 'NOT') {
      const next = this.tokens[this.pos + 1];
      const nextUpper = next ? next.toUpperCase() : '';
      if (nextUpper === 'EXISTS') {
        this.advance();
        this.advance();
        return new Condition(field, Operator.NOT_EXISTS, null);
      }
      if (nextUpper === 'IN') {
        this.advance();
        this.advance();
        operator = Operator.NOT_IN;
      } else {
        throw new Error(`Parse error: expected EXISTS or IN after NOT, got '${next}'`);
      }
    } else {
      throw new Error(`Parse error: unknown operator '${opToken}' in condition`);
    }

    // Value
    const value = this.parseValue();

    return new Condition(field, operator, value);
  }

  parseValue() {
    const token = this.current();
    if (!token) {
      return null;
    }

    // List: (val1, val2, ...)
    if (token === '(') {
      this.advance();
      const values = [];
      while (!this.match(')')) {
        if (!this.current()) {
          throw new Error("Unexpected end of query: expected ')' to close value list");
        }
        const val = this.parseSingleValue();
        if (val !== null) {
          values.push(val);
        }
        if (this.match(',')) {
          this.advance();
        }
      }
      this.advance(); // Skip ')'
      return values;
    }

    return this.parseSingleValue();
  }

  parseSingleValue() {
    const token = this.advance();
    if (!token) {
      return null;
    }

    const upper = token.toUpperCase();

    // Booleans
    if (upper === 'TRUE') return true;
    if (upper === 'FALSE') return false;

    // Null
    if (['NULL', 'NONE', 'NIL'].includes(upper)) return null;

    // Numbers
    if (/^-?\d+\.?\d*$/.test(token)) {
      return token.includes('.') ? parseFloat(token) : parseInt(token, 10);
    }

    // String
    return token;
  }

  parseShorthandConditions() {
    const conditions = [];

    while (!this.match(')')) {
      if (!this.current()) {
        throw new Error("Unexpected end of query: expected ')' to close shorthand conditions");
      }
      const field = this.advance();
      if (this.match('=')) {
        this.advance();
        const value = this.parseSingleValue();
        conditions.push(new Condition(field, Operator.EQ, value));
      }
      if (this.match(',')) {
        this.advance();
      }
    }

    this.advance(); // Skip ')'
    return conditions;
  }

  parseFieldList() {
    const fields = [];
    while (this.current() && !this.match('LIMIT', 'OFFSET', 'ORDER')) {
      fields.push(this.advance());
      if (this.match(',')) {
        this.advance();
      } else {
        break;
      }
    }
    return fields;
  }

  // -------------------------------------------------------------------------
  // Helpers
  // -------------------------------------------------------------------------

  parseNodeRef(token) {
    if (token.startsWith(':')) {
      token = token.substring(1);
    }

    const parts = token.split(':');
    if (parts.length >= 2) {
      const nodeType = parts[0];
      let nodeId = parts[1];
      // Try to convert to number
      const numId = parseInt(nodeId, 10);
      if (!isNaN(numId) && String(numId) === nodeId) {
        nodeId = numId;
      }
      return [nodeType, nodeId];
    }

    throw new Error(`Invalid node reference: ${token}. Expected format: type:id`);
  }

  directionFromArrows(arrow1, arrow2) {
    if (arrow1 === '->' || arrow2 === '->') {
      return Direction.OUT;
    }
    if (arrow1 === '<-' || arrow2 === '<-') {
      return Direction.IN;
    }
    return Direction.BOTH;
  }
}

// =============================================================================
// Query Engine
// =============================================================================

/**
 * ISONQL Query Engine for ISONGraph
 *
 * Executes parsed ISONQL queries against an ISONGraph instance.
 */
export class QueryEngine {
  constructor(graph) {
    this.graph = graph;
    this.parser = new ISONQLParser();
  }

  /** Get the underlying graph */
  getGraph() {
    return this.graph;
  }

  /** Execute an ISONQL query string */
  execute(query) {
    const startTime = performance.now();

    let parsed;
    try {
      parsed = this.parser.parse(query);
    } catch (e) {
      throw new Error(`Parse error: ${e.message}`);
    }

    let data;
    let total;

    switch (parsed.type) {
      case 'NODES':
        [data, total] = this.executeNodes(parsed);
        break;
      case 'EDGES':
        [data, total] = this.executeEdges(parsed);
        break;
      case 'TRAVERSE':
        [data, total] = this.executeTraverse(parsed);
        break;
      case 'PATH':
        [data, total] = this.executePath(parsed);
        break;
      case 'COUNT':
        [data, total] = this.executeCount(parsed);
        break;
      case 'SUM':
      case 'AVG':
      case 'MIN':
      case 'MAX':
        [data, total] = this.executeAggregation(parsed);
        break;
      default:
        throw new Error(`Unknown query type: ${parsed.type}`);
    }

    const executionTime = performance.now() - startTime;

    return new QueryResult(
      data,
      Array.isArray(data) ? data.length : 1,
      total,
      executionTime,
      query,
      parsed.type
    );
  }

  // -------------------------------------------------------------------------
  // Query Executors
  // -------------------------------------------------------------------------

  executeNodes(parsed) {
    const nodeType = parsed.nodeType;
    const conditions = parsed.conditions || [];
    const orderBy = parsed.orderBy;
    const orderDir = parsed.orderDir || 'ASC';
    const limit = parsed.limit;
    const offset = parsed.offset ?? 0;
    const returnFields = parsed.returnFields;

    // Get nodes
    let nodes = Array.from(this.graph.nodes(nodeType));

    // Filter by conditions
    if (conditions.length > 0) {
      nodes = nodes.filter(n => this.matchesConditions(n.properties, conditions));
    }

    const total = nodes.length;

    // Sort
    if (orderBy) {
      const reverse = orderDir === 'DESC';
      nodes.sort((a, b) => {
        const aHas = orderBy in a.properties;
        const bHas = orderBy in b.properties;
        // Nodes missing the sort field always sort last
        if (!aHas && !bHas) return 0;
        if (!aHas) return 1;
        if (!bHas) return -1;
        const aVal = a.properties[orderBy];
        const bVal = b.properties[orderBy];
        if (aVal < bVal) return reverse ? 1 : -1;
        if (aVal > bVal) return reverse ? -1 : 1;
        return 0;
      });
    }

    // Pagination
    if (offset > 0) {
      nodes = nodes.slice(offset);
    }
    if (limit !== undefined) {
      nodes = nodes.slice(0, limit);
    }

    // Format output
    let data;
    if (returnFields) {
      data = nodes.map(n => {
        const obj = {};
        for (const f of returnFields) {
          obj[f] = n.properties[f];
        }
        return obj;
      });
    } else {
      data = nodes.map(n => ({
        type: n.type,
        id: n.id,
        properties: n.properties
      }));
    }

    return [data, total];
  }

  executeEdges(parsed) {
    const relType = parsed.relType;
    const conditions = parsed.conditions || [];
    const limit = parsed.limit;

    // Get edges
    let edges = Array.from(this.graph.edges(relType));

    // Filter by conditions
    if (conditions.length > 0) {
      edges = edges.filter(e => this.matchesConditions(e.properties, conditions));
    }

    const total = edges.length;

    // Limit
    if (limit !== undefined) {
      edges = edges.slice(0, limit);
    }

    const data = edges.map(e => ({
      relType: e.relType,
      source: e.source,
      target: e.target,
      properties: e.properties
    }));

    return [data, total];
  }

  executeTraverse(parsed) {
    const start = parsed.start;
    const pattern = parsed.pattern || [];
    const maxDepth = parsed.maxDepth;
    const limit = parsed.limit;

    // Start traversal
    let current = new Set([this.nodeRefToKey(start)]);
    const visited = new Set([this.nodeRefToKey(start)]);
    const currentRefs = new Map([[this.nodeRefToKey(start), start]]);

    for (const step of pattern) {
      const direction = step.direction;
      const relType = step.relType;
      const targetType = step.targetType;

      const nextLevel = new Set();
      const nextRefs = new Map();

      for (const key of current) {
        const nodeRef = currentRefs.get(key);
        const neighbors = this.graph.neighbors(nodeRef, relType, direction);
        for (const neighbor of neighbors) {
          const neighborKey = this.nodeRefToKey(neighbor);
          if (!visited.has(neighborKey)) {
            if (targetType === '*' || neighbor[0] === targetType) {
              nextLevel.add(neighborKey);
              nextRefs.set(neighborKey, neighbor);
            }
          }
        }
      }

      for (const [key, ref] of nextRefs) {
        visited.add(key);
        currentRefs.set(key, ref);
      }
      current = nextLevel;

      if (current.size === 0) {
        break;
      }
    }

    // Apply max_depth by doing additional hops
    if (maxDepth && maxDepth > pattern.length) {
      const remainingHops = maxDepth - pattern.length;
      const lastRel = pattern.length > 0 ? pattern[pattern.length - 1].relType : undefined;
      const lastDir = pattern.length > 0 ? pattern[pattern.length - 1].direction : Direction.OUT;

      for (let i = 0; i < remainingHops; i++) {
        const nextLevel = new Set();
        const nextRefs = new Map();

        for (const key of current) {
          const nodeRef = currentRefs.get(key);
          const neighbors = this.graph.neighbors(nodeRef, lastRel, lastDir);
          for (const neighbor of neighbors) {
            const neighborKey = this.nodeRefToKey(neighbor);
            if (!visited.has(neighborKey)) {
              nextLevel.add(neighborKey);
              nextRefs.set(neighborKey, neighbor);
            }
          }
        }

        for (const [key, ref] of nextRefs) {
          visited.add(key);
          current.add(key);
          currentRefs.set(key, ref);
        }

        if (nextLevel.size === 0) {
          break;
        }
      }
    }

    let result = Array.from(current).map(key => currentRefs.get(key));
    const total = result.length;

    if (limit !== undefined) {
      result = result.slice(0, limit);
    }

    return [result, total];
  }

  executePath(parsed) {
    const source = parsed.source;
    const target = parsed.target;
    const via = parsed.via;
    const maxHops = parsed.maxHops ?? 10;

    const path = this.graph.shortestPath(source, target, via, maxHops);

    if (path) {
      const data = [{
        nodes: path.nodes,
        edges: path.edges.map(e => ({
          relType: e.relType,
          source: e.source,
          target: e.target
        })),
        length: path.length
      }];
      return [data, 1];
    } else {
      return [[], 0];
    }
  }

  executeCount(parsed) {
    const nodeType = parsed.nodeType;
    const conditions = parsed.conditions || [];

    let nodes = Array.from(this.graph.nodes(nodeType));

    if (conditions.length > 0) {
      nodes = nodes.filter(n => this.matchesConditions(n.properties, conditions));
    }

    const count = nodes.length;
    return [[count], count];
  }

  executeAggregation(parsed) {
    const aggType = parsed.type;
    const nodeType = parsed.nodeType;
    const prop = parsed.property;
    const conditions = parsed.conditions || [];

    let nodes = Array.from(this.graph.nodes(nodeType));

    if (conditions.length > 0) {
      nodes = nodes.filter(n => this.matchesConditions(n.properties, conditions));
    }

    // Extract numeric values
    const values = [];
    for (const n of nodes) {
      if (prop in n.properties) {
        const val = n.properties[prop];
        if (typeof val === 'number') {
          values.push(val);
        }
      }
    }

    if (values.length === 0) {
      return [[null], 0];
    }

    let result;
    switch (aggType) {
      case 'SUM':
        result = values.reduce((a, b) => a + b, 0);
        break;
      case 'AVG':
        result = values.reduce((a, b) => a + b, 0) / values.length;
        break;
      case 'MIN':
        result = Math.min(...values);
        break;
      case 'MAX':
        result = Math.max(...values);
        break;
      default:
        return [[null], 0];
    }

    return [[result], values.length];
  }

  /**
   * Evaluate parsed conditions against a properties object.
   * Conditions are either a flat AND-ed list of Condition objects, or a
   * list of OR-groups (Condition[][]) where each group is AND-ed internally
   * and the groups are OR-ed together.
   */
  matchesConditions(properties, conditions) {
    if (!conditions || conditions.length === 0) {
      return true;
    }
    if (Array.isArray(conditions[0])) {
      return conditions.some(group => group.every(c => c.evaluate(properties)));
    }
    return conditions.every(c => c.evaluate(properties));
  }

  nodeRefToKey(ref) {
    return `${ref[0]}:${ref[1]}`;
  }

  // -------------------------------------------------------------------------
  // Fluent API
  // -------------------------------------------------------------------------

  /** Start a fluent query for nodes of a given type */
  match(nodeType) {
    return new QueryBuilder(this, nodeType);
  }

  /** Start a fluent query for edges */
  matchEdges(relType) {
    return new EdgeQueryBuilder(this, relType);
  }
}

// =============================================================================
// Fluent Query Builders
// =============================================================================

/**
 * Fluent API for building node queries
 */
export class QueryBuilder {
  constructor(engine, nodeType) {
    this.engine = engine;
    this.nodeType = nodeType;
    this.conditions = [];
    this._orderBy = undefined;
    this._orderDir = "ASC";
    this._limit = undefined;
    this._offset = 0;
    this._fields = undefined;
  }

  /** Add a WHERE condition */
  where(field, operator, value) {
    const opMap = {
      '=': Operator.EQ, '==': Operator.EQ,
      '!=': Operator.NE, '<>': Operator.NE,
      '>': Operator.GT, '>=': Operator.GE,
      '<': Operator.LT, '<=': Operator.LE,
      'IN': Operator.IN, 'NOT IN': Operator.NOT_IN,
      'CONTAINS': Operator.CONTAINS,
      'STARTS_WITH': Operator.STARTS_WITH,
      'ENDS_WITH': Operator.ENDS_WITH,
      'MATCHES': Operator.MATCHES,
    };
    const op = opMap[operator.toUpperCase()] || Operator.EQ;
    this.conditions.push(new Condition(field, op, value));
    return this;
  }

  /** Add EXISTS condition */
  whereExists(field) {
    this.conditions.push(new Condition(field, Operator.EXISTS, null));
    return this;
  }

  /** Add NOT EXISTS condition */
  whereNotExists(field) {
    this.conditions.push(new Condition(field, Operator.NOT_EXISTS, null));
    return this;
  }

  /** Set ORDER BY clause */
  orderBy(field, direction = "ASC") {
    this._orderBy = field;
    this._orderDir = direction.toUpperCase();
    return this;
  }

  /** Set LIMIT */
  limit(n) {
    this._limit = n;
    return this;
  }

  /** Set OFFSET for pagination */
  offset(n) {
    this._offset = n;
    return this;
  }

  /** Set fields to return (projection) */
  returnFields(...fields) {
    this._fields = fields;
    return this;
  }

  /** Execute the built query */
  execute() {
    const parsed = {
      type: 'NODES',
      nodeType: this.nodeType,
      conditions: this.conditions,
      orderBy: this._orderBy,
      orderDir: this._orderDir,
      limit: this._limit,
      offset: this._offset,
      returnFields: this._fields
    };

    const startTime = performance.now();
    const [data, total] = this.engine.executeNodes(parsed);
    const executionTime = performance.now() - startTime;

    // Build query string for logging
    let queryStr = `NODES ${this.nodeType}`;
    if (this.conditions.length > 0) {
      const conds = this.conditions.map(c => c.toString()).join(' AND ');
      queryStr += ` WHERE ${conds}`;
    }
    if (this._orderBy) {
      queryStr += ` ORDER BY ${this._orderBy} ${this._orderDir}`;
    }
    if (this._limit !== undefined) {
      queryStr += ` LIMIT ${this._limit}`;
    }

    return new QueryResult(
      data,
      data.length,
      total,
      executionTime,
      queryStr,
      'NODES'
    );
  }

  /** Execute count query and return count */
  count() {
    const parsed = {
      type: 'COUNT',
      nodeType: this.nodeType,
      conditions: this.conditions
    };
    const [data] = this.engine.executeCount(parsed);
    return data[0] || 0;
  }
}

/**
 * Fluent API for building edge queries
 */
export class EdgeQueryBuilder {
  constructor(engine, relType) {
    this.engine = engine;
    this.relType = relType;
    this.conditions = [];
    this._limit = undefined;
  }

  /** Add a WHERE condition */
  where(field, operator, value) {
    const opMap = {
      '=': Operator.EQ, '==': Operator.EQ,
      '!=': Operator.NE, '<>': Operator.NE,
      '>': Operator.GT, '>=': Operator.GE,
      '<': Operator.LT, '<=': Operator.LE,
    };
    const op = opMap[operator.toUpperCase()] || Operator.EQ;
    this.conditions.push(new Condition(field, op, value));
    return this;
  }

  /** Set LIMIT */
  limit(n) {
    this._limit = n;
    return this;
  }

  /** Execute the built query */
  execute() {
    const parsed = {
      type: 'EDGES',
      relType: this.relType,
      conditions: this.conditions,
      limit: this._limit
    };

    const startTime = performance.now();
    const [data, total] = this.engine.executeEdges(parsed);
    const executionTime = performance.now() - startTime;

    let queryStr = `EDGES ${this.relType || ''}`;
    if (this.conditions.length > 0) {
      const conds = this.conditions.map(c => c.toString()).join(' AND ');
      queryStr += ` WHERE ${conds}`;
    }

    return new QueryResult(
      data,
      data.length,
      total,
      executionTime,
      queryStr.trim(),
      'EDGES'
    );
  }
}

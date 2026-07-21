/**
 * ISONGraph Schema Validation Module
 *
 * Provides graph schema validation with:
 * - Node type schemas with property validation
 * - Edge type schemas with reference integrity
 * - Graph-level constraints (cycles, connectivity, cardinality)
 * - Fluent API for schema definition
 *
 * @example
 * ```typescript
 * import {
 *   GraphSchema, NodeType, EdgeType,
 *   StringField, IntField, FloatField, BoolField, RefField,
 *   Cardinality
 * } from 'ison-graph-ts';
 *
 * // Define node types
 * const Person = new NodeType('person')
 *   .id(new IntField())
 *   .field('name', new StringField().required().max(100))
 *   .field('age', new IntField().min(0).max(150));
 *
 * const Company = new NodeType('company')
 *   .id(new IntField())
 *   .field('name', new StringField().required());
 *
 * // Define edge types
 * const Knows = new EdgeType('KNOWS')
 *   .fromNode(Person)
 *   .toNode(Person)
 *   .noSelfLoop()
 *   .unique();
 *
 * const WorksAt = new EdgeType('WORKS_AT')
 *   .fromNode(Person)
 *   .toNode(Company)
 *   .cardinality(Cardinality.MANY_TO_ONE);
 *
 * // Define graph schema
 * const Schema = new GraphSchema('social')
 *   .nodeTypes(Person, Company)
 *   .edgeTypes(Knows, WorksAt)
 *   .noOrphans();
 *
 * // Validate
 * const result = Schema.validate(graph);
 * if (!result.valid) {
 *   for (const error of result.errors) {
 *     console.log(error.toString());
 *   }
 * }
 * ```
 *
 * @author Mahesh Vaikri
 */

import { ISONGraph, Node, Edge, NodeRef } from './index';

// =============================================================================
// Enums
// =============================================================================

/** Edge cardinality constraints */
export enum Cardinality {
  ONE_TO_ONE = "1:1",
  ONE_TO_MANY = "1:N",
  MANY_TO_ONE = "N:1",
  MANY_TO_MANY = "N:N"
}

/** Validation error codes */
export enum ErrorCode {
  // Field errors
  REQUIRED_FIELD = "REQUIRED_FIELD",
  INVALID_TYPE = "INVALID_TYPE",
  MIN_VALUE = "MIN_VALUE",
  MAX_VALUE = "MAX_VALUE",
  MIN_LENGTH = "MIN_LENGTH",
  MAX_LENGTH = "MAX_LENGTH",
  PATTERN_MISMATCH = "PATTERN_MISMATCH",
  INVALID_EMAIL = "INVALID_EMAIL",
  INVALID_ENUM = "INVALID_ENUM",

  // Reference errors
  REF_NOT_FOUND = "REF_NOT_FOUND",
  REF_WRONG_TYPE = "REF_WRONG_TYPE",

  // Edge errors
  SELF_LOOP = "SELF_LOOP",
  DUPLICATE_EDGE = "DUPLICATE_EDGE",
  CARDINALITY_VIOLATION = "CARDINALITY_VIOLATION",
  INVALID_SOURCE_TYPE = "INVALID_SOURCE_TYPE",
  INVALID_TARGET_TYPE = "INVALID_TARGET_TYPE",

  // Graph errors
  CYCLE_DETECTED = "CYCLE_DETECTED",
  NOT_CONNECTED = "NOT_CONNECTED",
  ORPHAN_NODE = "ORPHAN_NODE",
  MAX_DEPTH_EXCEEDED = "MAX_DEPTH_EXCEEDED"
}

// =============================================================================
// Validation Result
// =============================================================================

/** Represents a single validation error */
export class ValidationError {
  constructor(
    public readonly code: ErrorCode,
    public readonly message: string,
    public location: string = "",
    public readonly context: Record<string, any> = {}
  ) {}

  toString(): string {
    const loc = this.location ? `[${this.location}] ` : "";
    return `${loc}${this.code}: ${this.message}`;
  }
}

/** Result of schema validation */
export class ValidationResult {
  public valid: boolean;
  public readonly errors: ValidationError[] = [];
  public readonly warnings: ValidationError[] = [];

  constructor(valid: boolean = true) {
    this.valid = valid;
  }

  /** Add a validation error */
  addError(
    code: ErrorCode,
    message: string,
    location: string = "",
    context: Record<string, any> = {}
  ): void {
    this.errors.push(new ValidationError(code, message, location, context));
    this.valid = false;
  }

  /** Add a validation warning */
  addWarning(
    code: ErrorCode,
    message: string,
    location: string = "",
    context: Record<string, any> = {}
  ): void {
    this.warnings.push(new ValidationError(code, message, location, context));
  }

  /** Merge another result into this one */
  merge(other: ValidationResult): void {
    this.errors.push(...other.errors);
    this.warnings.push(...other.warnings);
    if (!other.valid) {
      this.valid = false;
    }
  }

  toString(): string {
    const status = this.valid ? "VALID" : `INVALID (${this.errors.length} errors)`;
    return `ValidationResult(${status})`;
  }
}

// =============================================================================
// Field Types
// =============================================================================

/** Base class for field type validators */
export abstract class FieldType {
  protected _required: boolean = false;
  protected _default: any = null;
  protected _hasDefault: boolean = false;

  /** Mark field as required */
  required(): this {
    this._required = true;
    return this;
  }

  /** Set default value */
  default(value: any): this {
    this._default = value;
    this._hasDefault = true;
    return this;
  }

  /** Validate a value */
  abstract validate(value: any, fieldName: string): ValidationResult;

  /** Check required constraint */
  protected _checkRequired(value: any, fieldName: string): ValidationResult | null {
    if (value === null || value === undefined) {
      if (this._required) {
        const result = new ValidationResult(false);
        result.addError(
          ErrorCode.REQUIRED_FIELD,
          `Field '${fieldName}' is required`,
          fieldName
        );
        return result;
      }
      return new ValidationResult(true);
    }
    return null;
  }
}

/** String field validator */
export class StringField extends FieldType {
  private static EMAIL_PATTERN = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

  private _minLength?: number;
  private _maxLength?: number;
  private _pattern?: RegExp;
  private _email: boolean = false;
  private _enum?: string[];

  /** Set minimum length */
  min(length: number): this {
    this._minLength = length;
    return this;
  }

  /** Set maximum length */
  max(length: number): this {
    this._maxLength = length;
    return this;
  }

  /** Set regex pattern */
  pattern(regex: string | RegExp): this {
    this._pattern = typeof regex === "string" ? new RegExp(regex) : regex;
    return this;
  }

  /** Validate as email */
  email(): this {
    this._email = true;
    return this;
  }

  /** Restrict to enum values */
  enum(...values: string[]): this {
    this._enum = values;
    return this;
  }

  validate(value: any, fieldName: string): ValidationResult {
    const reqResult = this._checkRequired(value, fieldName);
    if (reqResult !== null) return reqResult;

    const result = new ValidationResult(true);

    if (typeof value !== "string") {
      result.addError(
        ErrorCode.INVALID_TYPE,
        `Field '${fieldName}' must be a string, got ${typeof value}`,
        fieldName
      );
      return result;
    }

    if (this._minLength !== undefined && value.length < this._minLength) {
      result.addError(
        ErrorCode.MIN_LENGTH,
        `Field '${fieldName}' must be at least ${this._minLength} characters`,
        fieldName,
        { minLength: this._minLength, actual: value.length }
      );
    }

    if (this._maxLength !== undefined && value.length > this._maxLength) {
      result.addError(
        ErrorCode.MAX_LENGTH,
        `Field '${fieldName}' must be at most ${this._maxLength} characters`,
        fieldName,
        { maxLength: this._maxLength, actual: value.length }
      );
    }

    if (this._pattern !== undefined && !this._pattern.test(value)) {
      result.addError(
        ErrorCode.PATTERN_MISMATCH,
        `Field '${fieldName}' does not match pattern`,
        fieldName,
        { pattern: this._pattern.source }
      );
    }

    if (this._email && !StringField.EMAIL_PATTERN.test(value)) {
      result.addError(
        ErrorCode.INVALID_EMAIL,
        `Field '${fieldName}' is not a valid email address`,
        fieldName
      );
    }

    if (this._enum !== undefined && !this._enum.includes(value)) {
      result.addError(
        ErrorCode.INVALID_ENUM,
        `Field '${fieldName}' must be one of: ${this._enum.join(", ")}`,
        fieldName,
        { allowed: this._enum, actual: value }
      );
    }

    return result;
  }
}

/** Integer field validator */
export class IntField extends FieldType {
  private _min?: number;
  private _max?: number;

  /** Set minimum value */
  min(value: number): this {
    this._min = value;
    return this;
  }

  /** Set maximum value */
  max(value: number): this {
    this._max = value;
    return this;
  }

  /** Set value range */
  range(minVal: number, maxVal: number): this {
    this._min = minVal;
    this._max = maxVal;
    return this;
  }

  validate(value: any, fieldName: string): ValidationResult {
    const reqResult = this._checkRequired(value, fieldName);
    if (reqResult !== null) return reqResult;

    const result = new ValidationResult(true);

    if (typeof value !== "number" || !Number.isInteger(value)) {
      result.addError(
        ErrorCode.INVALID_TYPE,
        `Field '${fieldName}' must be an integer, got ${typeof value}`,
        fieldName
      );
      return result;
    }

    if (this._min !== undefined && value < this._min) {
      result.addError(
        ErrorCode.MIN_VALUE,
        `Field '${fieldName}' must be at least ${this._min}`,
        fieldName,
        { min: this._min, actual: value }
      );
    }

    if (this._max !== undefined && value > this._max) {
      result.addError(
        ErrorCode.MAX_VALUE,
        `Field '${fieldName}' must be at most ${this._max}`,
        fieldName,
        { max: this._max, actual: value }
      );
    }

    return result;
  }
}

/** Float field validator */
export class FloatField extends FieldType {
  private _min?: number;
  private _max?: number;

  /** Set minimum value */
  min(value: number): this {
    this._min = value;
    return this;
  }

  /** Set maximum value */
  max(value: number): this {
    this._max = value;
    return this;
  }

  /** Set value range */
  range(minVal: number, maxVal: number): this {
    this._min = minVal;
    this._max = maxVal;
    return this;
  }

  validate(value: any, fieldName: string): ValidationResult {
    const reqResult = this._checkRequired(value, fieldName);
    if (reqResult !== null) return reqResult;

    const result = new ValidationResult(true);

    if (typeof value !== "number") {
      result.addError(
        ErrorCode.INVALID_TYPE,
        `Field '${fieldName}' must be a number, got ${typeof value}`,
        fieldName
      );
      return result;
    }

    if (this._min !== undefined && value < this._min) {
      result.addError(
        ErrorCode.MIN_VALUE,
        `Field '${fieldName}' must be at least ${this._min}`,
        fieldName,
        { min: this._min, actual: value }
      );
    }

    if (this._max !== undefined && value > this._max) {
      result.addError(
        ErrorCode.MAX_VALUE,
        `Field '${fieldName}' must be at most ${this._max}`,
        fieldName,
        { max: this._max, actual: value }
      );
    }

    return result;
  }
}

/** Boolean field validator */
export class BoolField extends FieldType {
  validate(value: any, fieldName: string): ValidationResult {
    const reqResult = this._checkRequired(value, fieldName);
    if (reqResult !== null) return reqResult;

    const result = new ValidationResult(true);

    if (typeof value !== "boolean") {
      result.addError(
        ErrorCode.INVALID_TYPE,
        `Field '${fieldName}' must be a boolean, got ${typeof value}`,
        fieldName
      );
    }

    return result;
  }
}

/** Reference field validator */
export class RefField extends FieldType {
  private _nodeType?: string;

  constructor(nodeType?: string) {
    super();
    this._nodeType = nodeType;
  }

  /** Specify target node type */
  to(nodeType: string): this {
    this._nodeType = nodeType;
    return this;
  }

  validate(value: any, fieldName: string): ValidationResult {
    const reqResult = this._checkRequired(value, fieldName);
    if (reqResult !== null) return reqResult;

    const result = new ValidationResult(true);

    // Value should be a NodeRef tuple [type, id]
    if (!Array.isArray(value) || value.length !== 2) {
      result.addError(
        ErrorCode.INVALID_TYPE,
        `Field '${fieldName}' must be a node reference [type, id]`,
        fieldName
      );
      return result;
    }

    if (this._nodeType && value[0] !== this._nodeType) {
      result.addError(
        ErrorCode.REF_WRONG_TYPE,
        `Field '${fieldName}' must reference '${this._nodeType}', got '${value[0]}'`,
        fieldName,
        { expected: this._nodeType, actual: value[0] }
      );
    }

    return result;
  }
}

// =============================================================================
// Node Type Schema
// =============================================================================

/**
 * Schema definition for a node type.
 *
 * @example
 * const Person = new NodeType('person')
 *   .id(new IntField())
 *   .field('name', new StringField().required())
 *   .field('age', new IntField().min(0));
 */
export class NodeType {
  public readonly name: string;
  private _idType?: FieldType;
  private _fields: Map<string, FieldType> = new Map();
  private _constraints: Array<(node: Node) => ValidationError | null> = [];

  constructor(name: string) {
    this.name = name;
  }

  /** Define ID field type */
  id(fieldType: FieldType): this {
    this._idType = fieldType;
    return this;
  }

  /** Add a field definition */
  field(name: string, fieldType: FieldType): this {
    this._fields.set(name, fieldType);
    return this;
  }

  /** Add custom constraint */
  constraint(fn: (node: Node) => ValidationError | null): this {
    this._constraints.push(fn);
    return this;
  }

  /** Validate a single node */
  validateNode(node: Node): ValidationResult {
    const result = new ValidationResult(true);
    const location = `nodes.${this.name}[${node.id}]`;

    // Validate ID
    if (this._idType) {
      const idResult = this._idType.validate(node.id, "id");
      if (!idResult.valid) {
        for (const err of idResult.errors) {
          err.location = location;
        }
        result.merge(idResult);
      }
    }

    // Validate fields
    for (const [fieldName, fieldType] of this._fields) {
      const value = node.properties[fieldName];
      const fieldResult = fieldType.validate(value, fieldName);
      if (!fieldResult.valid) {
        for (const err of fieldResult.errors) {
          err.location = `${location}.${fieldName}`;
        }
        result.merge(fieldResult);
      }
    }

    // Custom constraints
    for (const constraint of this._constraints) {
      const error = constraint(node);
      if (error) {
        error.location = location;
        result.errors.push(error);
        result.valid = false;
      }
    }

    return result;
  }

  toString(): string {
    return `NodeType(${this.name})`;
  }
}

// =============================================================================
// Edge Type Schema
// =============================================================================

/**
 * Schema definition for an edge/relationship type.
 *
 * @example
 * const Knows = new EdgeType('KNOWS')
 *   .fromNode(Person)
 *   .toNode(Person)
 *   .field('since', new IntField())
 *   .noSelfLoop()
 *   .unique();
 */
export class EdgeType {
  public readonly name: string;
  private _sourceType?: NodeType;
  private _targetType?: NodeType;
  private _fields: Map<string, FieldType> = new Map();
  private _noSelfLoop: boolean = false;
  private _unique: boolean = false;
  private _acyclic: boolean = false;
  private _bidirectional: boolean = false;
  private _cardinality?: Cardinality;
  private _constraints: Array<(edge: Edge) => ValidationError | null> = [];

  constructor(name: string) {
    this.name = name;
  }

  /** Set source node type */
  fromNode(nodeType: NodeType): this {
    this._sourceType = nodeType;
    return this;
  }

  /** Set target node type */
  toNode(nodeType: NodeType): this {
    this._targetType = nodeType;
    return this;
  }

  /** Add edge property field */
  field(name: string, fieldType: FieldType): this {
    this._fields.set(name, fieldType);
    return this;
  }

  /** Disallow self-referential edges */
  noSelfLoop(): this {
    this._noSelfLoop = true;
    return this;
  }

  /** Ensure unique source-target pairs */
  unique(): this {
    this._unique = true;
    return this;
  }

  /** Enforce DAG (no cycles via this edge type) */
  acyclic(): this {
    this._acyclic = true;
    return this;
  }

  /** Require symmetric edges (if A->B, then B->A) */
  bidirectional(): this {
    this._bidirectional = true;
    return this;
  }

  /** Set cardinality constraint */
  cardinality(card: Cardinality): this {
    this._cardinality = card;
    return this;
  }

  /** Add custom constraint */
  constraint(fn: (edge: Edge) => ValidationError | null): this {
    this._constraints.push(fn);
    return this;
  }

  /** Get unique flag (for internal use) */
  get isUnique(): boolean {
    return this._unique;
  }

  /** Get acyclic flag (for internal use) */
  get isAcyclic(): boolean {
    return this._acyclic;
  }

  /** Get bidirectional flag (for internal use) */
  get isBidirectional(): boolean {
    return this._bidirectional;
  }

  /** Get cardinality (for internal use) */
  get cardinalityConstraint(): Cardinality | undefined {
    return this._cardinality;
  }

  /** Validate a single edge */
  validateEdge(edge: Edge, graph: ISONGraph): ValidationResult {
    const result = new ValidationResult(true);
    const location = `edges.${this.name}[${edge.source}->${edge.target}]`;

    // Validate source type
    if (this._sourceType && edge.source[0] !== this._sourceType.name) {
      result.addError(
        ErrorCode.INVALID_SOURCE_TYPE,
        `Edge source must be '${this._sourceType.name}', got '${edge.source[0]}'`,
        location,
        { expected: this._sourceType.name, actual: edge.source[0] }
      );
    }

    // Validate target type
    if (this._targetType && edge.target[0] !== this._targetType.name) {
      result.addError(
        ErrorCode.INVALID_TARGET_TYPE,
        `Edge target must be '${this._targetType.name}', got '${edge.target[0]}'`,
        location,
        { expected: this._targetType.name, actual: edge.target[0] }
      );
    }

    // Validate source exists
    if (!graph.hasNode(edge.source[0], edge.source[1])) {
      result.addError(
        ErrorCode.REF_NOT_FOUND,
        `Source node :${edge.source[0]}:${edge.source[1]} does not exist`,
        location
      );
    }

    // Validate target exists
    if (!graph.hasNode(edge.target[0], edge.target[1])) {
      result.addError(
        ErrorCode.REF_NOT_FOUND,
        `Target node :${edge.target[0]}:${edge.target[1]} does not exist`,
        location
      );
    }

    // Validate self-loop constraint
    if (this._noSelfLoop && edge.source[0] === edge.target[0] && edge.source[1] === edge.target[1]) {
      result.addError(
        ErrorCode.SELF_LOOP,
        `Self-loop not allowed: :${edge.source[0]}:${edge.source[1]}`,
        location
      );
    }

    // Validate fields
    for (const [fieldName, fieldType] of this._fields) {
      const value = edge.properties[fieldName];
      const fieldResult = fieldType.validate(value, fieldName);
      if (!fieldResult.valid) {
        for (const err of fieldResult.errors) {
          err.location = `${location}.${fieldName}`;
        }
        result.merge(fieldResult);
      }
    }

    // Custom constraints
    for (const constraint of this._constraints) {
      const error = constraint(edge);
      if (error) {
        error.location = location;
        result.errors.push(error);
        result.valid = false;
      }
    }

    return result;
  }

  toString(): string {
    return `EdgeType(${this.name})`;
  }
}

// =============================================================================
// Graph Schema
// =============================================================================

/**
 * Complete graph schema definition.
 *
 * @example
 * const Schema = new GraphSchema('social')
 *   .nodeTypes(Person, Company)
 *   .edgeTypes(Knows, WorksAt)
 *   .connected()
 *   .noOrphans();
 */
export class GraphSchema {
  public readonly name: string;
  private _nodeTypes: Map<string, NodeType> = new Map();
  private _edgeTypes: Map<string, EdgeType> = new Map();
  private _requireConnected: boolean = false;
  private _requireNoOrphans: boolean = false;
  private _maxDepth?: number;
  private _constraints: Array<(graph: ISONGraph) => ValidationError[]> = [];

  constructor(name: string) {
    this.name = name;
  }

  /** Add node type schemas */
  nodeTypes(...types: NodeType[]): this {
    for (const nt of types) {
      this._nodeTypes.set(nt.name, nt);
    }
    return this;
  }

  /** Add edge type schemas */
  edgeTypes(...types: EdgeType[]): this {
    for (const et of types) {
      this._edgeTypes.set(et.name, et);
    }
    return this;
  }

  /** Require graph to be connected */
  connected(): this {
    this._requireConnected = true;
    return this;
  }

  /** Require all nodes to have at least one edge */
  noOrphans(): this {
    this._requireNoOrphans = true;
    return this;
  }

  /** Set maximum graph depth */
  maxDepth(depth: number): this {
    this._maxDepth = depth;
    return this;
  }

  /** Add custom graph-level constraint */
  constraint(fn: (graph: ISONGraph) => ValidationError[]): this {
    this._constraints.push(fn);
    return this;
  }

  /**
   * Validate a graph against this schema.
   * @param graph ISONGraph instance to validate
   * @returns ValidationResult with errors and warnings
   */
  validate(graph: ISONGraph): ValidationResult {
    const result = new ValidationResult(true);

    // Validate nodes
    for (const node of graph.nodes()) {
      const nodeType = this._nodeTypes.get(node.type);
      if (nodeType) {
        const nodeResult = nodeType.validateNode(node);
        result.merge(nodeResult);
      }
    }

    // Validate edges
    for (const [relType, edgeType] of this._edgeTypes) {
      const edgesOfType = Array.from(graph.edges(relType));

      // Check uniqueness
      if (edgeType.isUnique) {
        const seen = new Set<string>();
        for (const edge of edgesOfType) {
          const key = `${edge.source[0]}:${edge.source[1]}->${edge.target[0]}:${edge.target[1]}`;
          if (seen.has(key)) {
            result.addError(
              ErrorCode.DUPLICATE_EDGE,
              `Duplicate edge: ${edge.source} -> ${edge.target}`,
              `edges.${relType}`
            );
          }
          seen.add(key);
        }
      }

      // Check cardinality
      if (edgeType.cardinalityConstraint) {
        this._checkCardinality(graph, edgeType, edgesOfType, result);
      }

      // Check acyclic
      if (edgeType.isAcyclic) {
        if (graph.hasCycle(relType)) {
          result.addError(
            ErrorCode.CYCLE_DETECTED,
            `Cycle detected in '${relType}' edges (must be DAG)`,
            `edges.${relType}`
          );
        }
      }

      // Check bidirectional
      if (edgeType.isBidirectional) {
        for (const edge of edgesOfType) {
          if (!graph.hasEdge(relType, edge.target, edge.source)) {
            result.addError(
              ErrorCode.DUPLICATE_EDGE,
              `Missing reverse edge for bidirectional: ${edge.target} -> ${edge.source}`,
              `edges.${relType}`
            );
          }
        }
      }

      // Validate individual edges
      for (const edge of edgesOfType) {
        const edgeResult = edgeType.validateEdge(edge, graph);
        result.merge(edgeResult);
      }
    }

    // Graph-level constraints
    if (this._requireConnected && !graph.isConnected()) {
      result.addError(
        ErrorCode.NOT_CONNECTED,
        "Graph is not connected (some nodes are unreachable)",
        "graph"
      );
    }

    if (this._requireNoOrphans) {
      for (const node of graph.nodes()) {
        if (graph.degree(node.ref) === 0) {
          result.addError(
            ErrorCode.ORPHAN_NODE,
            `Orphan node (no edges): :${node.type}:${node.id}`,
            `nodes.${node.type}[${node.id}]`
          );
        }
      }
    }

    // Custom constraints
    for (const constraint of this._constraints) {
      const errors = constraint(graph);
      for (const error of errors) {
        result.errors.push(error);
        result.valid = false;
      }
    }

    return result;
  }

  /** Check cardinality constraints */
  private _checkCardinality(
    graph: ISONGraph,
    edgeType: EdgeType,
    edges: Edge[],
    result: ValidationResult
  ): void {
    const cardinality = edgeType.cardinalityConstraint;
    const location = `edges.${edgeType.name}`;

    // Count outgoing edges per source
    const sourceCounts = new Map<string, number>();
    // Count incoming edges per target
    const targetCounts = new Map<string, number>();

    for (const edge of edges) {
      const sourceKey = `${edge.source[0]}:${edge.source[1]}`;
      const targetKey = `${edge.target[0]}:${edge.target[1]}`;
      sourceCounts.set(sourceKey, (sourceCounts.get(sourceKey) || 0) + 1);
      targetCounts.set(targetKey, (targetCounts.get(targetKey) || 0) + 1);
    }

    if (cardinality === Cardinality.ONE_TO_ONE) {
      for (const [source, count] of sourceCounts) {
        if (count > 1) {
          result.addError(
            ErrorCode.CARDINALITY_VIOLATION,
            `ONE_TO_ONE violation: :${source} has ${count} outgoing edges`,
            location
          );
        }
      }
      for (const [target, count] of targetCounts) {
        if (count > 1) {
          result.addError(
            ErrorCode.CARDINALITY_VIOLATION,
            `ONE_TO_ONE violation: :${target} has ${count} incoming edges`,
            location
          );
        }
      }
    } else if (cardinality === Cardinality.ONE_TO_MANY) {
      for (const [target, count] of targetCounts) {
        if (count > 1) {
          result.addError(
            ErrorCode.CARDINALITY_VIOLATION,
            `ONE_TO_MANY violation: :${target} has ${count} incoming edges`,
            location
          );
        }
      }
    } else if (cardinality === Cardinality.MANY_TO_ONE) {
      for (const [source, count] of sourceCounts) {
        if (count > 1) {
          result.addError(
            ErrorCode.CARDINALITY_VIOLATION,
            `MANY_TO_ONE violation: :${source} has ${count} outgoing edges`,
            location
          );
        }
      }
    }
    // MANY_TO_MANY has no restrictions
  }

  toString(): string {
    return `GraphSchema(${this.name})`;
  }
}

// =============================================================================
// Constraint Helpers
// =============================================================================

/** Create no self-loop constraint */
export function noSelfLoopConstraint(): (edge: Edge) => ValidationError | null {
  return (edge: Edge) => {
    if (edge.source[0] === edge.target[0] && edge.source[1] === edge.target[1]) {
      return new ValidationError(
        ErrorCode.SELF_LOOP,
        `Self-loop not allowed: :${edge.source[0]}:${edge.source[1]}`
      );
    }
    return null;
  };
}

/** Create custom edge constraint */
export function customEdgeConstraint(
  fn: (edge: Edge) => boolean,
  message: string = "Custom constraint failed"
): (edge: Edge) => ValidationError | null {
  return (edge: Edge) => {
    if (!fn(edge)) {
      return new ValidationError(ErrorCode.INVALID_TYPE, message);
    }
    return null;
  };
}

/** Create custom graph constraint */
export function graphConstraint(
  fn: (graph: ISONGraph) => boolean,
  message: string = "Graph constraint failed",
  code: ErrorCode = ErrorCode.NOT_CONNECTED
): (graph: ISONGraph) => ValidationError[] {
  return (graph: ISONGraph) => {
    if (!fn(graph)) {
      return [new ValidationError(code, message, "graph")];
    }
    return [];
  };
}

#!/usr/bin/env python3
"""
ISONGraph Schema Validation Module

Provides graph schema validation with:
- Node type schemas with property validation
- Edge type schemas with reference integrity
- Graph-level constraints (cycles, connectivity, cardinality)
- Fluent API for schema definition

Usage:
    from ison_graph.schema import (
        GraphSchema, NodeType, EdgeType,
        String, Int, Float, Bool, Ref,
        Cardinality
    )

    # Define node types
    Person = NodeType('person') \\
        .id(Int()) \\
        .field('name', String().required().max(100)) \\
        .field('age', Int().min(0).max(150))

    Company = NodeType('company') \\
        .id(Int()) \\
        .field('name', String().required())

    # Define edge types
    Knows = EdgeType('KNOWS') \\
        .from_node(Person) \\
        .to_node(Person) \\
        .no_self_loop() \\
        .unique()

    WorksAt = EdgeType('WORKS_AT') \\
        .from_node(Person) \\
        .to_node(Company) \\
        .cardinality(Cardinality.MANY_TO_ONE)

    # Define graph schema
    Schema = GraphSchema('social') \\
        .node_types(Person, Company) \\
        .edge_types(Knows, WorksAt) \\
        .no_orphans()

    # Validate
    result = Schema.validate(graph)
    if not result.valid:
        for error in result.errors:
            print(error)

Author: Mahesh Vaikri
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    Any, Dict, List, Optional, Set, Tuple,
    Union, Callable, Pattern, TYPE_CHECKING
)
from enum import Enum

# Import from parent module (relative imports)
if TYPE_CHECKING:
    from . import ISONGraph, Node, Edge, NodeRef


# =============================================================================
# Enums
# =============================================================================

class Cardinality(Enum):
    """Edge cardinality constraints"""
    ONE_TO_ONE = "1:1"
    ONE_TO_MANY = "1:N"
    MANY_TO_ONE = "N:1"
    MANY_TO_MANY = "N:N"


class ErrorCode(Enum):
    """Validation error codes"""
    # Field errors
    REQUIRED_FIELD = "REQUIRED_FIELD"
    INVALID_TYPE = "INVALID_TYPE"
    MIN_VALUE = "MIN_VALUE"
    MAX_VALUE = "MAX_VALUE"
    MIN_LENGTH = "MIN_LENGTH"
    MAX_LENGTH = "MAX_LENGTH"
    PATTERN_MISMATCH = "PATTERN_MISMATCH"
    INVALID_EMAIL = "INVALID_EMAIL"
    INVALID_ENUM = "INVALID_ENUM"

    # Reference errors
    REF_NOT_FOUND = "REF_NOT_FOUND"
    REF_WRONG_TYPE = "REF_WRONG_TYPE"

    # Edge errors
    SELF_LOOP = "SELF_LOOP"
    DUPLICATE_EDGE = "DUPLICATE_EDGE"
    CARDINALITY_VIOLATION = "CARDINALITY_VIOLATION"
    INVALID_SOURCE_TYPE = "INVALID_SOURCE_TYPE"
    INVALID_TARGET_TYPE = "INVALID_TARGET_TYPE"

    # Graph errors
    CYCLE_DETECTED = "CYCLE_DETECTED"
    NOT_CONNECTED = "NOT_CONNECTED"
    ORPHAN_NODE = "ORPHAN_NODE"
    MAX_DEPTH_EXCEEDED = "MAX_DEPTH_EXCEEDED"


# =============================================================================
# Validation Result
# =============================================================================

@dataclass
class ValidationError:
    """Represents a single validation error"""
    code: ErrorCode
    message: str
    location: str = ""
    context: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        loc = f"[{self.location}] " if self.location else ""
        return f"{loc}{self.code.value}: {self.message}"


@dataclass
class ValidationResult:
    """Result of schema validation"""
    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)

    def add_error(
        self,
        code: ErrorCode,
        message: str,
        location: str = "",
        **context: Any
    ) -> None:
        """Add a validation error"""
        self.errors.append(ValidationError(code, message, location, context))
        self.valid = False

    def add_warning(
        self,
        code: ErrorCode,
        message: str,
        location: str = "",
        **context: Any
    ) -> None:
        """Add a validation warning"""
        self.warnings.append(ValidationError(code, message, location, context))

    def merge(self, other: 'ValidationResult') -> None:
        """Merge another result into this one"""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if not other.valid:
            self.valid = False

    def __repr__(self) -> str:
        status = "VALID" if self.valid else f"INVALID ({len(self.errors)} errors)"
        return f"ValidationResult({status})"


# =============================================================================
# Field Types
# =============================================================================

class FieldType(ABC):
    """Base class for field type validators"""

    def __init__(self) -> None:
        self._required: bool = False
        self._default: Any = None
        self._has_default: bool = False

    def required(self) -> 'FieldType':
        """Mark field as required"""
        self._required = True
        return self

    def default(self, value: Any) -> 'FieldType':
        """Set default value, applied to missing fields during validation.

        A missing field with a default never raises REQUIRED_FIELD; the
        default is written into the node/edge properties and then validated.
        """
        self._default = value
        self._has_default = True
        return self

    @abstractmethod
    def validate(self, value: Any, field_name: str) -> ValidationResult:
        """Validate a value"""
        pass

    def _check_required(self, value: Any, field_name: str) -> Optional[ValidationResult]:
        """Check required constraint"""
        if value is None:
            if self._required:
                result = ValidationResult(valid=False)
                result.add_error(
                    ErrorCode.REQUIRED_FIELD,
                    f"Field '{field_name}' is required",
                    field_name
                )
                return result
            return ValidationResult(valid=True)
        return None


class String(FieldType):
    """String field validator"""

    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

    def __init__(self) -> None:
        super().__init__()
        self._min_length: Optional[int] = None
        self._max_length: Optional[int] = None
        self._pattern: Optional[Pattern] = None
        self._email: bool = False
        self._enum: Optional[List[str]] = None

    def min(self, length: int) -> 'String':
        """Set minimum length"""
        self._min_length = length
        return self

    def max(self, length: int) -> 'String':
        """Set maximum length"""
        self._max_length = length
        return self

    def pattern(self, regex: str) -> 'String':
        """Set regex pattern"""
        self._pattern = re.compile(regex)
        return self

    def email(self) -> 'String':
        """Validate as email"""
        self._email = True
        return self

    def enum(self, *values: str) -> 'String':
        """Restrict to enum values"""
        self._enum = list(values)
        return self

    def validate(self, value: Any, field_name: str) -> ValidationResult:
        result = self._check_required(value, field_name)
        if result is not None:
            return result

        result = ValidationResult(valid=True)

        if not isinstance(value, str):
            result.add_error(
                ErrorCode.INVALID_TYPE,
                f"Field '{field_name}' must be a string, got {type(value).__name__}",
                field_name
            )
            return result

        if self._min_length is not None and len(value) < self._min_length:
            result.add_error(
                ErrorCode.MIN_LENGTH,
                f"Field '{field_name}' must be at least {self._min_length} characters",
                field_name,
                min_length=self._min_length,
                actual=len(value)
            )

        if self._max_length is not None and len(value) > self._max_length:
            result.add_error(
                ErrorCode.MAX_LENGTH,
                f"Field '{field_name}' must be at most {self._max_length} characters",
                field_name,
                max_length=self._max_length,
                actual=len(value)
            )

        if self._pattern is not None and not self._pattern.match(value):
            result.add_error(
                ErrorCode.PATTERN_MISMATCH,
                f"Field '{field_name}' does not match pattern",
                field_name,
                pattern=self._pattern.pattern
            )

        if self._email and not self.EMAIL_PATTERN.match(value):
            result.add_error(
                ErrorCode.INVALID_EMAIL,
                f"Field '{field_name}' is not a valid email address",
                field_name
            )

        if self._enum is not None and value not in self._enum:
            result.add_error(
                ErrorCode.INVALID_ENUM,
                f"Field '{field_name}' must be one of: {', '.join(self._enum)}",
                field_name,
                allowed=self._enum,
                actual=value
            )

        return result


class Int(FieldType):
    """Integer field validator"""

    def __init__(self) -> None:
        super().__init__()
        self._min: Optional[int] = None
        self._max: Optional[int] = None

    def min(self, value: int) -> 'Int':
        """Set minimum value"""
        self._min = value
        return self

    def max(self, value: int) -> 'Int':
        """Set maximum value"""
        self._max = value
        return self

    def range(self, min_val: int, max_val: int) -> 'Int':
        """Set value range"""
        self._min = min_val
        self._max = max_val
        return self

    def validate(self, value: Any, field_name: str) -> ValidationResult:
        result = self._check_required(value, field_name)
        if result is not None:
            return result

        result = ValidationResult(valid=True)

        if not isinstance(value, int) or isinstance(value, bool):
            result.add_error(
                ErrorCode.INVALID_TYPE,
                f"Field '{field_name}' must be an integer, got {type(value).__name__}",
                field_name
            )
            return result

        if self._min is not None and value < self._min:
            result.add_error(
                ErrorCode.MIN_VALUE,
                f"Field '{field_name}' must be at least {self._min}",
                field_name,
                min=self._min,
                actual=value
            )

        if self._max is not None and value > self._max:
            result.add_error(
                ErrorCode.MAX_VALUE,
                f"Field '{field_name}' must be at most {self._max}",
                field_name,
                max=self._max,
                actual=value
            )

        return result


class Float(FieldType):
    """Float field validator"""

    def __init__(self) -> None:
        super().__init__()
        self._min: Optional[float] = None
        self._max: Optional[float] = None

    def min(self, value: float) -> 'Float':
        """Set minimum value"""
        self._min = value
        return self

    def max(self, value: float) -> 'Float':
        """Set maximum value"""
        self._max = value
        return self

    def range(self, min_val: float, max_val: float) -> 'Float':
        """Set value range"""
        self._min = min_val
        self._max = max_val
        return self

    def validate(self, value: Any, field_name: str) -> ValidationResult:
        result = self._check_required(value, field_name)
        if result is not None:
            return result

        result = ValidationResult(valid=True)

        if not isinstance(value, (int, float)) or isinstance(value, bool):
            result.add_error(
                ErrorCode.INVALID_TYPE,
                f"Field '{field_name}' must be a number, got {type(value).__name__}",
                field_name
            )
            return result

        if self._min is not None and value < self._min:
            result.add_error(
                ErrorCode.MIN_VALUE,
                f"Field '{field_name}' must be at least {self._min}",
                field_name,
                min=self._min,
                actual=value
            )

        if self._max is not None and value > self._max:
            result.add_error(
                ErrorCode.MAX_VALUE,
                f"Field '{field_name}' must be at most {self._max}",
                field_name,
                max=self._max,
                actual=value
            )

        return result


class Bool(FieldType):
    """Boolean field validator"""

    def validate(self, value: Any, field_name: str) -> ValidationResult:
        result = self._check_required(value, field_name)
        if result is not None:
            return result

        result = ValidationResult(valid=True)

        if not isinstance(value, bool):
            result.add_error(
                ErrorCode.INVALID_TYPE,
                f"Field '{field_name}' must be a boolean, got {type(value).__name__}",
                field_name
            )

        return result


class Ref(FieldType):
    """Reference field validator"""

    def __init__(self, node_type: Optional[str] = None) -> None:
        super().__init__()
        self._node_type = node_type

    def to(self, node_type: str) -> 'Ref':
        """Specify target node type"""
        self._node_type = node_type
        return self

    def validate(self, value: Any, field_name: str) -> ValidationResult:
        result = self._check_required(value, field_name)
        if result is not None:
            return result

        result = ValidationResult(valid=True)

        # Value should be a NodeRef tuple or similar
        if not isinstance(value, tuple) or len(value) != 2:
            result.add_error(
                ErrorCode.INVALID_TYPE,
                f"Field '{field_name}' must be a node reference (type, id)",
                field_name
            )
            return result

        if self._node_type and value[0] != self._node_type:
            result.add_error(
                ErrorCode.REF_WRONG_TYPE,
                f"Field '{field_name}' must reference '{self._node_type}', got '{value[0]}'",
                field_name,
                expected=self._node_type,
                actual=value[0]
            )

        return result


# =============================================================================
# Node Type Schema
# =============================================================================

class NodeType:
    """
    Schema definition for a node type.

    Example:
        Person = NodeType('person') \\
            .id(Int()) \\
            .field('name', String().required()) \\
            .field('age', Int().min(0))
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self._id_type: Optional[FieldType] = None
        self._fields: Dict[str, FieldType] = {}
        self._constraints: List[Callable[['Node'], Optional[ValidationError]]] = []

    def id(self, field_type: FieldType) -> 'NodeType':
        """Define ID field type"""
        self._id_type = field_type
        return self

    def field(self, name: str, field_type: FieldType) -> 'NodeType':
        """Add a field definition"""
        self._fields[name] = field_type
        return self

    def constraint(self, fn: Callable[['Node'], Optional[ValidationError]]) -> 'NodeType':
        """Add custom constraint"""
        self._constraints.append(fn)
        return self

    def validate_node(self, node: 'Node') -> ValidationResult:
        """Validate a single node"""
        result = ValidationResult(valid=True)
        location = f"nodes.{self.name}[{node.id}]"

        # Validate ID
        if self._id_type:
            id_result = self._id_type.validate(node.id, "id")
            if not id_result.valid:
                for err in id_result.errors:
                    err.location = location
                result.merge(id_result)

        # Validate fields
        for field_name, field_type in self._fields.items():
            value = node.properties.get(field_name)
            # Apply declared default for missing fields before validating
            if value is None and field_type._has_default:
                value = field_type._default
                node.properties[field_name] = value
            field_result = field_type.validate(value, field_name)
            if not field_result.valid:
                for err in field_result.errors:
                    err.location = f"{location}.{field_name}"
                result.merge(field_result)

        # Custom constraints
        for constraint in self._constraints:
            error = constraint(node)
            if error:
                error.location = location
                result.errors.append(error)
                result.valid = False

        return result

    def __repr__(self) -> str:
        return f"NodeType({self.name})"


# =============================================================================
# Edge Type Schema
# =============================================================================

class EdgeType:
    """
    Schema definition for an edge/relationship type.

    Example:
        Knows = EdgeType('KNOWS') \\
            .from_node(Person) \\
            .to_node(Person) \\
            .field('since', Int()) \\
            .no_self_loop() \\
            .unique()
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self._source_type: Optional[NodeType] = None
        self._target_type: Optional[NodeType] = None
        self._fields: Dict[str, FieldType] = {}
        self._no_self_loop: bool = False
        self._unique: bool = False
        self._acyclic: bool = False
        self._bidirectional: bool = False
        self._cardinality: Optional[Cardinality] = None
        self._constraints: List[Callable[['Edge'], Optional[ValidationError]]] = []

    def from_node(self, node_type: NodeType) -> 'EdgeType':
        """Set source node type"""
        self._source_type = node_type
        return self

    def to_node(self, node_type: NodeType) -> 'EdgeType':
        """Set target node type"""
        self._target_type = node_type
        return self

    def field(self, name: str, field_type: FieldType) -> 'EdgeType':
        """Add edge property field"""
        self._fields[name] = field_type
        return self

    def no_self_loop(self) -> 'EdgeType':
        """Disallow self-referential edges"""
        self._no_self_loop = True
        return self

    def unique(self) -> 'EdgeType':
        """Ensure unique source-target pairs"""
        self._unique = True
        return self

    def acyclic(self) -> 'EdgeType':
        """Enforce DAG (no cycles via this edge type)"""
        self._acyclic = True
        return self

    def bidirectional(self) -> 'EdgeType':
        """Require symmetric edges (if A->B, then B->A)"""
        self._bidirectional = True
        return self

    def cardinality(self, card: Cardinality) -> 'EdgeType':
        """Set cardinality constraint"""
        self._cardinality = card
        return self

    def constraint(self, fn: Callable[['Edge'], Optional[ValidationError]]) -> 'EdgeType':
        """Add custom constraint"""
        self._constraints.append(fn)
        return self

    def validate_edge(self, edge: 'Edge', graph: 'ISONGraph') -> ValidationResult:
        """Validate a single edge"""
        result = ValidationResult(valid=True)
        location = f"edges.{self.name}[{edge.source}->{edge.target}]"

        # Validate source type
        if self._source_type and edge.source[0] != self._source_type.name:
            result.add_error(
                ErrorCode.INVALID_SOURCE_TYPE,
                f"Edge source must be '{self._source_type.name}', got '{edge.source[0]}'",
                location,
                expected=self._source_type.name,
                actual=edge.source[0]
            )

        # Validate target type
        if self._target_type and edge.target[0] != self._target_type.name:
            result.add_error(
                ErrorCode.INVALID_TARGET_TYPE,
                f"Edge target must be '{self._target_type.name}', got '{edge.target[0]}'",
                location,
                expected=self._target_type.name,
                actual=edge.target[0]
            )

        # Validate source exists
        if not graph.has_node(edge.source[0], edge.source[1]):
            result.add_error(
                ErrorCode.REF_NOT_FOUND,
                f"Source node :{edge.source[0]}:{edge.source[1]} does not exist",
                location
            )

        # Validate target exists
        if not graph.has_node(edge.target[0], edge.target[1]):
            result.add_error(
                ErrorCode.REF_NOT_FOUND,
                f"Target node :{edge.target[0]}:{edge.target[1]} does not exist",
                location
            )

        # Validate self-loop constraint
        if self._no_self_loop and edge.source == edge.target:
            result.add_error(
                ErrorCode.SELF_LOOP,
                f"Self-loop not allowed: :{edge.source[0]}:{edge.source[1]}",
                location
            )

        # Validate fields
        for field_name, field_type in self._fields.items():
            value = edge.properties.get(field_name)
            # Apply declared default for missing fields before validating
            if value is None and field_type._has_default:
                value = field_type._default
                edge.properties[field_name] = value
            field_result = field_type.validate(value, field_name)
            if not field_result.valid:
                for err in field_result.errors:
                    err.location = f"{location}.{field_name}"
                result.merge(field_result)

        # Custom constraints
        for constraint in self._constraints:
            error = constraint(edge)
            if error:
                error.location = location
                result.errors.append(error)
                result.valid = False

        return result

    def __repr__(self) -> str:
        return f"EdgeType({self.name})"


# =============================================================================
# Graph Schema
# =============================================================================

class GraphSchema:
    """
    Complete graph schema definition.

    Example:
        Schema = GraphSchema('social') \\
            .node_types(Person, Company) \\
            .edge_types(Knows, WorksAt) \\
            .connected() \\
            .no_orphans()
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self._node_types: Dict[str, NodeType] = {}
        self._edge_types: Dict[str, EdgeType] = {}
        self._require_connected: bool = False
        self._require_no_orphans: bool = False
        self._max_depth: Optional[int] = None
        self._constraints: List[Callable[['ISONGraph'], List[ValidationError]]] = []

    def node_types(self, *types: NodeType) -> 'GraphSchema':
        """Add node type schemas"""
        for nt in types:
            self._node_types[nt.name] = nt
        return self

    def edge_types(self, *types: EdgeType) -> 'GraphSchema':
        """Add edge type schemas"""
        for et in types:
            self._edge_types[et.name] = et
        return self

    def connected(self) -> 'GraphSchema':
        """Require graph to be connected"""
        self._require_connected = True
        return self

    def no_orphans(self) -> 'GraphSchema':
        """Require all nodes to have at least one edge"""
        self._require_no_orphans = True
        return self

    def max_depth(self, depth: int) -> 'GraphSchema':
        """Set maximum graph depth"""
        self._max_depth = depth
        return self

    def constraint(
        self,
        fn: Callable[['ISONGraph'], List[ValidationError]]
    ) -> 'GraphSchema':
        """Add custom graph-level constraint"""
        self._constraints.append(fn)
        return self

    def validate(self, graph: 'ISONGraph') -> ValidationResult:
        """
        Validate a graph against this schema.

        Args:
            graph: ISONGraph instance to validate

        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult(valid=True)

        # Validate nodes
        for node in graph.nodes():
            if node.type in self._node_types:
                node_result = self._node_types[node.type].validate_node(node)
                result.merge(node_result)

        # Validate edges
        for rel_type, edge_type in self._edge_types.items():
            edges_of_type = list(graph.edges(rel_type))

            # Check uniqueness
            if edge_type._unique:
                seen = set()
                for edge in edges_of_type:
                    key = (edge.source, edge.target)
                    if key in seen:
                        result.add_error(
                            ErrorCode.DUPLICATE_EDGE,
                            f"Duplicate edge: {edge.source} -> {edge.target}",
                            f"edges.{rel_type}"
                        )
                    seen.add(key)

            # Check cardinality
            if edge_type._cardinality:
                self._check_cardinality(graph, edge_type, edges_of_type, result)

            # Check acyclic
            if edge_type._acyclic:
                if graph.has_cycle(rel_type):
                    result.add_error(
                        ErrorCode.CYCLE_DETECTED,
                        f"Cycle detected in '{rel_type}' edges (must be DAG)",
                        f"edges.{rel_type}"
                    )

            # Check bidirectional
            if edge_type._bidirectional:
                for edge in edges_of_type:
                    if not graph.has_edge(rel_type, edge.target, edge.source):
                        result.add_error(
                            ErrorCode.DUPLICATE_EDGE,  # Reusing code
                            f"Missing reverse edge for bidirectional: {edge.target} -> {edge.source}",
                            f"edges.{rel_type}"
                        )

            # Validate individual edges
            for edge in edges_of_type:
                edge_result = edge_type.validate_edge(edge, graph)
                result.merge(edge_result)

        # Graph-level constraints
        if self._require_connected and not graph.is_connected():
            result.add_error(
                ErrorCode.NOT_CONNECTED,
                "Graph is not connected (some nodes are unreachable)",
                "graph"
            )

        if self._require_no_orphans:
            for node in graph.nodes():
                if graph.degree(node.ref) == 0:
                    result.add_error(
                        ErrorCode.ORPHAN_NODE,
                        f"Orphan node (no edges): :{node.type}:{node.id}",
                        f"nodes.{node.type}[{node.id}]"
                    )

        # Custom constraints
        for constraint in self._constraints:
            errors = constraint(graph)
            for error in errors:
                result.errors.append(error)
                result.valid = False

        return result

    def _check_cardinality(
        self,
        graph: 'ISONGraph',
        edge_type: EdgeType,
        edges: List['Edge'],
        result: ValidationResult
    ) -> None:
        """Check cardinality constraints"""
        cardinality = edge_type._cardinality
        location = f"edges.{edge_type.name}"

        # Count outgoing edges per source
        source_counts: Dict['NodeRef', int] = {}
        # Count incoming edges per target
        target_counts: Dict['NodeRef', int] = {}

        for edge in edges:
            source_counts[edge.source] = source_counts.get(edge.source, 0) + 1
            target_counts[edge.target] = target_counts.get(edge.target, 0) + 1

        if cardinality == Cardinality.ONE_TO_ONE:
            for source, count in source_counts.items():
                if count > 1:
                    result.add_error(
                        ErrorCode.CARDINALITY_VIOLATION,
                        f"ONE_TO_ONE violation: :{source[0]}:{source[1]} has {count} outgoing edges",
                        location
                    )
            for target, count in target_counts.items():
                if count > 1:
                    result.add_error(
                        ErrorCode.CARDINALITY_VIOLATION,
                        f"ONE_TO_ONE violation: :{target[0]}:{target[1]} has {count} incoming edges",
                        location
                    )

        elif cardinality == Cardinality.ONE_TO_MANY:
            for target, count in target_counts.items():
                if count > 1:
                    result.add_error(
                        ErrorCode.CARDINALITY_VIOLATION,
                        f"ONE_TO_MANY violation: :{target[0]}:{target[1]} has {count} incoming edges",
                        location
                    )

        elif cardinality == Cardinality.MANY_TO_ONE:
            for source, count in source_counts.items():
                if count > 1:
                    result.add_error(
                        ErrorCode.CARDINALITY_VIOLATION,
                        f"MANY_TO_ONE violation: :{source[0]}:{source[1]} has {count} outgoing edges",
                        location
                    )

        # MANY_TO_MANY has no restrictions

    def __repr__(self) -> str:
        return f"GraphSchema({self.name})"


# =============================================================================
# Constraint Helpers
# =============================================================================

def no_self_loop_constraint() -> Callable[['Edge'], Optional[ValidationError]]:
    """Create no self-loop constraint"""
    def check(edge: 'Edge') -> Optional[ValidationError]:
        if edge.source == edge.target:
            return ValidationError(
                ErrorCode.SELF_LOOP,
                f"Self-loop not allowed: :{edge.source[0]}:{edge.source[1]}"
            )
        return None
    return check


def unique_edge_constraint() -> Callable[['Edge'], Optional[ValidationError]]:
    """Note: uniqueness is checked at EdgeType level"""
    def check(edge: 'Edge') -> Optional[ValidationError]:
        return None  # Handled by EdgeType._unique
    return check


def custom_edge_constraint(
    fn: Callable[['Edge'], bool],
    message: str = "Custom constraint failed"
) -> Callable[['Edge'], Optional[ValidationError]]:
    """Create custom edge constraint"""
    def check(edge: 'Edge') -> Optional[ValidationError]:
        if not fn(edge):
            return ValidationError(ErrorCode.INVALID_TYPE, message)
        return None
    return check


def graph_constraint(
    fn: Callable[['ISONGraph'], bool],
    message: str = "Graph constraint failed",
    code: ErrorCode = ErrorCode.NOT_CONNECTED
) -> Callable[['ISONGraph'], List[ValidationError]]:
    """Create custom graph constraint"""
    def check(graph: 'ISONGraph') -> List[ValidationError]:
        if not fn(graph):
            return [ValidationError(code, message, "graph")]
        return []
    return check


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Enums
    'Cardinality',
    'ErrorCode',

    # Results
    'ValidationResult',
    'ValidationError',

    # Field Types
    'FieldType',
    'String',
    'Int',
    'Float',
    'Bool',
    'Ref',

    # Schema Types
    'NodeType',
    'EdgeType',
    'GraphSchema',

    # Constraint Helpers
    'no_self_loop_constraint',
    'unique_edge_constraint',
    'custom_edge_constraint',
    'graph_constraint',
]

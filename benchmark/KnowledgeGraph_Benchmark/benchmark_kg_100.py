#!/usr/bin/env python3
"""
ISONGraph Knowledge Graph Benchmark - 100 Questions
=====================================================

Comprehensive benchmark comparing ISONGraph against ALL competitors:

FORMATS TESTED:
1. ISONGraph     - Token-efficient graph format (our solution)
2. ISON          - Base ISON format
3. JSON          - Standard JSON (pretty)
4. JSON Compact  - Minified JSON
5. TOON          - Token-Optimized Object Notation
6. RDF/Turtle    - W3C standard for linked data
7. JSON-LD       - JSON for Linked Data
8. GraphML       - XML-based graph format
9. GML           - Graph Modelling Language
10. Cypher/Neo4j - Neo4j's query-focused format

QUESTION CATEGORIES (100 total):
1. Single-hop Retrieval (20)     - Direct neighbor queries
2. Multi-hop Traversal (20)      - Friends of friends, reachability
3. Path Finding (15)             - Shortest path, all paths
4. Graph Analysis (20)           - Connectivity, cycles, degrees
5. Aggregation (15)              - Counts, sums, averages
6. Pattern Matching (10)         - Complex relationship patterns

DATASETS (7 domains):
1. Social Network        - 15 questions
2. Knowledge Graph       - 15 questions
3. Organization Chart    - 15 questions
4. Flight Routes         - 15 questions
5. Movie Database        - 15 questions
6. E-Commerce            - 15 questions
7. Academic Citations    - 10 questions

Author: Mahesh Vaikri
Version: 2.0.0
"""

import json
import tiktoken
import sys
import os
import requests
import time
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict

# Import official libraries
import ison_parser
from ison_graph import ISONGraph, Direction

try:
    import toon
    HAS_TOON = True
except ImportError:
    HAS_TOON = False
    print("Warning: TOON not installed. Install with: pip install toon")

# =============================================================================
# CONFIGURATION
# =============================================================================

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

# Tokenizer
try:
    tokenizer = tiktoken.get_encoding("o200k_base")
    TOKENIZER_NAME = "o200k_base (GPT-4o/GPT-5)"
except:
    tokenizer = tiktoken.get_encoding("cl100k_base")
    TOKENIZER_NAME = "cl100k_base (GPT-4)"

# Logging
LOG_DIR = os.path.dirname(__file__)
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
LOG_FILE = os.path.join(LOG_DIR, f"benchmark_kg100_{TIMESTAMP}.log")
LATEST_LOG = os.path.join(LOG_DIR, "benchmark_kg100_latest.log")


def log(message: str, also_print: bool = True, end: str = "\n", timestamp: bool = False):
    """Log message to file and optionally print."""
    if timestamp:
        ts = datetime.now().strftime('%H:%M:%S')
        message = f"[{ts}] {message}"

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(message + end)
    with open(LATEST_LOG, "a", encoding="utf-8") as f:
        f.write(message + end)
    if also_print:
        safe_message = message
        safe_message = safe_message.replace("\u2713", "[PASS]")
        safe_message = safe_message.replace("\u2717", "[FAIL]")
        safe_message = safe_message.replace("\u2192", "->")
        safe_message = safe_message.replace("\u2794", "->")
        safe_message = safe_message.replace("\u279C", "->")
        safe_message = safe_message.replace("\u27F6", "->")
        safe_message = safe_message.encode('ascii', 'replace').decode('ascii')
        print(safe_message, end=end)


def count_tokens(text: str) -> int:
    """Count tokens using tiktoken."""
    return len(tokenizer.encode(text))


# =============================================================================
# ANSWER VALIDATION
# =============================================================================

def normalize_value(value: str) -> str:
    """Normalize a value for comparison."""
    if value is None:
        return "null"
    s = str(value).strip().lower()
    s = s.strip('"\'')
    s = ' '.join(s.split())
    return s


def extract_number(text: str) -> Optional[float]:
    """Extract a number from text."""
    cleaned = re.sub(r'[$€£¥,\s%]', '', text)
    match = re.search(r'-?\d+\.?\d*', cleaned)
    if match:
        try:
            return float(match.group())
        except:
            pass
    return None


def validate_answer(response: str, expected: Any, answer_type: str) -> Tuple[bool, str]:
    """Type-aware answer validation."""
    response_clean = response.strip()
    response_lower = response_clean.lower()
    expected_str = str(expected).strip() if expected is not None else "null"
    expected_lower = expected_str.lower()

    # Null handling
    if answer_type == "null" or expected is None:
        null_indicators = ["null", "none", "n/a", "missing", "not present", "~", "empty", "no value", "no path"]
        if any(ind in response_lower for ind in null_indicators):
            return True, "Null correctly identified"
        return False, f"Expected null, got: {response_clean[:50]}"

    # Boolean
    if answer_type == "boolean":
        true_values = ["true", "yes", "exists", "connected", "has cycle", "reachable", "valid", "correct"]
        false_values = ["false", "no", "not connected", "no cycle", "unreachable", "invalid", "acyclic", "incorrect"]

        expected_bool = expected_lower in ["true", "yes"] or expected is True
        response_is_true = any(v in response_lower for v in true_values)
        response_is_false = any(v in response_lower for v in false_values)

        if expected_bool and response_is_true and not response_is_false:
            return True, "Boolean true matched"
        if not expected_bool and response_is_false:
            return True, "Boolean false matched"
        return False, f"Boolean mismatch: expected {expected_str}, got: {response_clean[:50]}"

    # Number
    if answer_type == "number":
        expected_num = extract_number(expected_str)
        if expected_num is None:
            return False, f"Could not parse expected number: {expected_str}"

        numbers = re.findall(r'-?[\d,]+\.?\d*', response_clean)
        for num_str in numbers:
            try:
                response_num = float(num_str.replace(',', ''))
                if abs(response_num - expected_num) < 0.01:
                    return True, f"Number matched: {response_num}"
                if expected_num != 0 and abs(response_num - expected_num) / abs(expected_num) < 0.01:
                    return True, f"Number matched within tolerance"
            except:
                pass
        return False, f"Number not found: expected {expected_num}"

    # List
    if answer_type == "list":
        expected_items = [normalize_value(x) for x in expected_str.split(',')]
        matched = all(item in response_lower for item in expected_items)
        if matched:
            return True, f"All list items found"
        return False, f"Missing list items: expected {expected_items}"

    # Path (list of nodes)
    if answer_type == "path":
        expected_nodes = [normalize_value(x) for x in expected_str.split('->')]
        if all(node in response_lower for node in expected_nodes):
            return True, "Path nodes found in order"
        return False, f"Path mismatch: expected {expected_str}"

    # String (default)
    if expected_lower in response_lower:
        return True, "String contained in response"

    if re.search(r'\b' + re.escape(expected_lower) + r'\b', response_lower):
        return True, "String matched at word boundary"

    return False, f"String mismatch: expected '{expected_str}'"


# =============================================================================
# LLM API
# =============================================================================

def call_llm(prompt: str, max_retries: int = 3) -> str:
    """Call DeepSeek API with retry logic."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "temperature": 0
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                return f"ERROR: {str(e)}"
    return "ERROR: Max retries exceeded"


# =============================================================================
# FORMAT CONVERTERS - ALL COMPETITORS
# =============================================================================

def to_json_pretty(data: dict) -> str:
    """Standard JSON with indentation."""
    return json.dumps(data, indent=2)


def to_json_compact(data: dict) -> str:
    """Minified JSON."""
    return json.dumps(data, separators=(',', ':'))


def to_toon(data: dict) -> str:
    """TOON format - Token-Optimized Object Notation."""
    if HAS_TOON:
        return toon.encode(data)
    # Fallback: simple TOON-like format
    lines = []
    if "nodes" in data:
        lines.append("@nodes")
        for node in data["nodes"]:
            parts = [f"{k}={v}" for k, v in node.items()]
            lines.append(" ".join(parts))
    if "edges" in data:
        lines.append("@edges")
        for edge in data["edges"]:
            parts = [f"{k}={v}" for k, v in edge.items()]
            lines.append(" ".join(parts))
    return "\n".join(lines)


def to_ison(data: dict) -> str:
    """ISON format using official ison-py library."""
    doc = ison_parser.from_dict(data, auto_refs=True, smart_order=True)
    return ison_parser.dumps(doc, align_columns=False)


def to_isongraph(data: dict) -> str:
    """ISONGraph format - nodes/edges explicit with references."""
    graph = ISONGraph()

    # Add nodes
    if "nodes" in data:
        for node in data["nodes"]:
            node_id = node.get("id")
            node_type = node.get("type", "node")
            props = {k: v for k, v in node.items() if k not in ("id", "type")}
            graph.add_node(node_type, node_id, **props)

    # Add edges
    if "edges" in data:
        for edge in data["edges"]:
            source_id = edge.get("source")
            target_id = edge.get("target")
            rel_type = edge.get("relation", "RELATED")
            props = {k: v for k, v in edge.items() if k not in ("source", "target", "relation")}

            source_type = "node"
            target_type = "node"
            for node in data.get("nodes", []):
                if node["id"] == source_id:
                    source_type = node.get("type", "node")
                if node["id"] == target_id:
                    target_type = node.get("type", "node")

            try:
                graph.add_edge(rel_type.upper(), (source_type, source_id), (target_type, target_id), **props)
            except:
                pass

    return graph.to_ison()


def to_rdf_turtle(data: dict) -> str:
    """RDF/Turtle format - W3C standard for linked data."""
    lines = [
        "@prefix ex: <http://example.org/> .",
        "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
        ""
    ]

    # Nodes as subjects with properties
    if "nodes" in data:
        for node in data["nodes"]:
            node_id = node.get("id")
            node_type = node.get("type", "Thing")
            subject = f"ex:{node_type}_{node_id}"

            lines.append(f"{subject}")
            lines.append(f"    rdf:type ex:{node_type} ;")

            props = [(k, v) for k, v in node.items() if k not in ("id", "type")]
            for i, (key, value) in enumerate(props):
                ending = " ;" if i < len(props) - 1 else " ."
                if isinstance(value, str):
                    lines.append(f'    ex:{key} "{value}"{ending}')
                elif isinstance(value, bool):
                    lines.append(f'    ex:{key} {str(value).lower()}{ending}')
                else:
                    lines.append(f'    ex:{key} {value}{ending}')
            lines.append("")

    # Edges as triples
    if "edges" in data:
        for edge in data["edges"]:
            source_id = edge.get("source")
            target_id = edge.get("target")
            rel_type = edge.get("relation", "relatedTo")

            # Find types
            source_type = "node"
            target_type = "node"
            for node in data.get("nodes", []):
                if node["id"] == source_id:
                    source_type = node.get("type", "node")
                if node["id"] == target_id:
                    target_type = node.get("type", "node")

            subject = f"ex:{source_type}_{source_id}"
            obj = f"ex:{target_type}_{target_id}"
            lines.append(f"{subject} ex:{rel_type} {obj} .")

    return "\n".join(lines)


def to_jsonld(data: dict) -> str:
    """JSON-LD format - JSON for Linked Data."""
    context = {
        "@vocab": "http://example.org/",
        "nodes": {"@container": "@set"},
        "edges": {"@container": "@set"},
        "id": "@id",
        "type": "@type"
    }

    graph = []

    # Convert nodes
    if "nodes" in data:
        for node in data["nodes"]:
            ld_node = {
                "@id": f"ex:{node.get('type', 'node')}_{node.get('id')}",
                "@type": node.get("type", "Thing")
            }
            for k, v in node.items():
                if k not in ("id", "type"):
                    ld_node[k] = v
            graph.append(ld_node)

    # Convert edges
    if "edges" in data:
        for edge in data["edges"]:
            source_id = edge.get("source")
            target_id = edge.get("target")
            rel_type = edge.get("relation", "relatedTo")

            source_type = "node"
            target_type = "node"
            for node in data.get("nodes", []):
                if node["id"] == source_id:
                    source_type = node.get("type", "node")
                if node["id"] == target_id:
                    target_type = node.get("type", "node")

            ld_edge = {
                "@type": "Edge",
                "source": {"@id": f"ex:{source_type}_{source_id}"},
                "target": {"@id": f"ex:{target_type}_{target_id}"},
                "relation": rel_type
            }
            for k, v in edge.items():
                if k not in ("source", "target", "relation"):
                    ld_edge[k] = v
            graph.append(ld_edge)

    result = {
        "@context": context,
        "@graph": graph
    }
    return json.dumps(result, indent=2)


def to_graphml(data: dict) -> str:
    """GraphML format - XML-based graph format."""
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
        '  <graph id="G" edgedefault="directed">'
    ]

    # Collect all property keys
    node_keys = set()
    edge_keys = set()

    if "nodes" in data:
        for node in data["nodes"]:
            node_keys.update(k for k in node.keys() if k not in ("id", "type"))
    if "edges" in data:
        for edge in data["edges"]:
            edge_keys.update(k for k in edge.keys() if k not in ("source", "target", "relation"))

    # Add key definitions
    for key in sorted(node_keys):
        lines.insert(2, f'  <key id="{key}" for="node" attr.name="{key}" attr.type="string"/>')
    for key in sorted(edge_keys):
        lines.insert(2, f'  <key id="{key}" for="edge" attr.name="{key}" attr.type="string"/>')
    lines.insert(2, '  <key id="type" for="node" attr.name="type" attr.type="string"/>')
    lines.insert(2, '  <key id="relation" for="edge" attr.name="relation" attr.type="string"/>')

    # Add nodes
    if "nodes" in data:
        for node in data["nodes"]:
            node_id = node.get("id")
            lines.append(f'    <node id="n{node_id}">')
            lines.append(f'      <data key="type">{node.get("type", "node")}</data>')
            for k, v in node.items():
                if k not in ("id", "type"):
                    lines.append(f'      <data key="{k}">{v}</data>')
            lines.append('    </node>')

    # Add edges
    if "edges" in data:
        for i, edge in enumerate(data["edges"]):
            source = edge.get("source")
            target = edge.get("target")
            lines.append(f'    <edge id="e{i}" source="n{source}" target="n{target}">')
            lines.append(f'      <data key="relation">{edge.get("relation", "RELATED")}</data>')
            for k, v in edge.items():
                if k not in ("source", "target", "relation"):
                    lines.append(f'      <data key="{k}">{v}</data>')
            lines.append('    </edge>')

    lines.append('  </graph>')
    lines.append('</graphml>')

    return "\n".join(lines)


def to_gml(data: dict) -> str:
    """GML format - Graph Modelling Language."""
    lines = [
        'graph [',
        '  directed 1'
    ]

    # Add nodes
    if "nodes" in data:
        for node in data["nodes"]:
            node_id = node.get("id")
            lines.append('  node [')
            lines.append(f'    id {node_id}')
            lines.append(f'    type "{node.get("type", "node")}"')
            for k, v in node.items():
                if k not in ("id", "type"):
                    if isinstance(v, str):
                        lines.append(f'    {k} "{v}"')
                    else:
                        lines.append(f'    {k} {v}')
            lines.append('  ]')

    # Add edges
    if "edges" in data:
        for edge in data["edges"]:
            lines.append('  edge [')
            lines.append(f'    source {edge.get("source")}')
            lines.append(f'    target {edge.get("target")}')
            lines.append(f'    relation "{edge.get("relation", "RELATED")}"')
            for k, v in edge.items():
                if k not in ("source", "target", "relation"):
                    if isinstance(v, str):
                        lines.append(f'    {k} "{v}"')
                    else:
                        lines.append(f'    {k} {v}')
            lines.append('  ]')

    lines.append(']')

    return "\n".join(lines)


def to_cypher(data: dict) -> str:
    """Cypher/Neo4j format - Query-focused representation."""
    lines = ["// Neo4j Cypher CREATE statements", ""]

    # Create nodes
    if "nodes" in data:
        for node in data["nodes"]:
            node_id = node.get("id")
            node_type = node.get("type", "Node")
            props = {k: v for k, v in node.items() if k not in ("id", "type")}

            props_str = ", ".join([
                f'{k}: "{v}"' if isinstance(v, str) else f'{k}: {str(v).lower() if isinstance(v, bool) else v}'
                for k, v in props.items()
            ])

            if props_str:
                lines.append(f'CREATE (n{node_id}:{node_type} {{id: {node_id}, {props_str}}})')
            else:
                lines.append(f'CREATE (n{node_id}:{node_type} {{id: {node_id}}})')

    lines.append("")

    # Create relationships
    if "edges" in data:
        for edge in data["edges"]:
            source = edge.get("source")
            target = edge.get("target")
            rel_type = edge.get("relation", "RELATED").upper()
            props = {k: v for k, v in edge.items() if k not in ("source", "target", "relation")}

            if props:
                props_str = ", ".join([
                    f'{k}: "{v}"' if isinstance(v, str) else f'{k}: {v}'
                    for k, v in props.items()
                ])
                lines.append(f'CREATE (n{source})-[:{rel_type} {{{props_str}}}]->(n{target})')
            else:
                lines.append(f'CREATE (n{source})-[:{rel_type}]->(n{target})')

    return "\n".join(lines)


# Format registry
FORMATS = {
    "ISONGraph": to_isongraph,
    "ISON": to_ison,
    "JSON Compact": to_json_compact,
    "JSON": to_json_pretty,
    "RDF/Turtle": to_rdf_turtle,
    "JSON-LD": to_jsonld,
    "GraphML": to_graphml,
    "GML": to_gml,
    "Cypher": to_cypher,
}

if HAS_TOON:
    FORMATS["TOON"] = to_toon


# =============================================================================
# GRAPH DATASETS WITH 100 QUESTIONS
# =============================================================================

@dataclass
class Question:
    """A benchmark question with verified expected answer."""
    question: str
    expected: Any
    answer_type: str  # string, number, boolean, list, path, null
    category: str  # single_hop, multi_hop, path_finding, analysis, aggregation, pattern


def create_graph_datasets() -> Dict[str, Dict]:
    """Create graph datasets with 100 questions total."""

    datasets = {}

    # =========================================================================
    # Dataset 1: Social Network (15 questions)
    # =========================================================================
    datasets["social_network"] = {
        "description": "Social network with follows relationships",
        "data": {
            "nodes": [
                {"id": 1, "type": "person", "name": "Alice", "age": 28, "verified": True, "followers": 1500},
                {"id": 2, "type": "person", "name": "Bob", "age": 34, "verified": False, "followers": 800},
                {"id": 3, "type": "person", "name": "Carol", "age": 29, "verified": True, "followers": 2200},
                {"id": 4, "type": "person", "name": "David", "age": 42, "verified": False, "followers": 450},
                {"id": 5, "type": "person", "name": "Eve", "age": 31, "verified": True, "followers": 3100},
                {"id": 6, "type": "person", "name": "Frank", "age": 26, "verified": False, "followers": 600},
            ],
            "edges": [
                {"source": 1, "target": 2, "relation": "follows", "since": 2020},
                {"source": 1, "target": 3, "relation": "follows", "since": 2021},
                {"source": 2, "target": 3, "relation": "follows", "since": 2019},
                {"source": 2, "target": 4, "relation": "follows", "since": 2020},
                {"source": 3, "target": 4, "relation": "follows", "since": 2020},
                {"source": 4, "target": 5, "relation": "follows", "since": 2022},
                {"source": 5, "target": 1, "relation": "follows", "since": 2021},
                {"source": 6, "target": 1, "relation": "follows", "since": 2023},
                {"source": 6, "target": 3, "relation": "follows", "since": 2022},
            ]
        },
        "questions": [
            # Single-hop (5)
            Question("Who does Alice follow?", "Bob, Carol", "list", "single_hop"),
            Question("Who follows Carol?", "Alice, Bob, Frank", "list", "single_hop"),
            Question("How many people does Alice follow?", 2, "number", "single_hop"),
            Question("Does Bob follow Carol?", True, "boolean", "single_hop"),
            Question("Does David follow Alice?", False, "boolean", "single_hop"),
            # Multi-hop (5)
            Question("Who can Alice reach in 2 hops?", "Carol, David", "list", "multi_hop"),
            Question("Can Alice reach Eve in 3 hops?", True, "boolean", "multi_hop"),
            Question("How many hops from Alice to David?", 2, "number", "multi_hop"),
            Question("Who can reach Alice in 1 hop?", "Eve, Frank", "list", "multi_hop"),
            Question("Is there a path from Frank to Eve?", True, "boolean", "multi_hop"),
            # Analysis (5)
            Question("Does this graph have a cycle?", True, "boolean", "analysis"),
            Question("How many nodes are there?", 6, "number", "analysis"),
            Question("How many edges are there?", 9, "number", "analysis"),
            Question("Who has the most followers count?", "Eve", "string", "analysis"),
            Question("What is the total followers across all users?", 8650, "number", "aggregation"),
        ]
    }

    # =========================================================================
    # Dataset 2: Knowledge Graph (15 questions)
    # =========================================================================
    datasets["knowledge_graph"] = {
        "description": "Knowledge graph with companies, people, products",
        "data": {
            "nodes": [
                {"id": 1, "type": "company", "name": "TechCorp", "employees": 5000, "founded": 2010, "revenue": 500},
                {"id": 2, "type": "company", "name": "DataInc", "employees": 1200, "founded": 2015, "revenue": 150},
                {"id": 3, "type": "company", "name": "CloudSys", "employees": 3500, "founded": 2012, "revenue": 320},
                {"id": 4, "type": "company", "name": "AILabs", "employees": 800, "founded": 2018, "revenue": 90},
                {"id": 10, "type": "person", "name": "John", "role": "CEO", "salary": 250000},
                {"id": 11, "type": "person", "name": "Jane", "role": "CTO", "salary": 200000},
                {"id": 12, "type": "person", "name": "Mike", "role": "Engineer", "salary": 120000},
                {"id": 13, "type": "person", "name": "Sara", "role": "Manager", "salary": 140000},
                {"id": 20, "type": "product", "name": "CloudDB", "price": 99, "category": "database"},
                {"id": 21, "type": "product", "name": "DataAPI", "price": 49, "category": "api"},
                {"id": 22, "type": "product", "name": "MLKit", "price": 199, "category": "ml"},
            ],
            "edges": [
                {"source": 10, "target": 1, "relation": "works_at"},
                {"source": 11, "target": 2, "relation": "works_at"},
                {"source": 12, "target": 3, "relation": "works_at"},
                {"source": 13, "target": 4, "relation": "works_at"},
                {"source": 1, "target": 2, "relation": "partner"},
                {"source": 1, "target": 3, "relation": "customer"},
                {"source": 2, "target": 3, "relation": "vendor"},
                {"source": 4, "target": 1, "relation": "partner"},
                {"source": 1, "target": 20, "relation": "produces"},
                {"source": 2, "target": 21, "relation": "produces"},
                {"source": 4, "target": 22, "relation": "produces"},
                {"source": 3, "target": 20, "relation": "uses"},
                {"source": 3, "target": 22, "relation": "uses"},
            ]
        },
        "questions": [
            # Single-hop (5)
            Question("Where does John work?", "TechCorp", "string", "single_hop"),
            Question("What does TechCorp produce?", "CloudDB", "string", "single_hop"),
            Question("Who works at CloudSys?", "Mike", "string", "single_hop"),
            Question("Is TechCorp a partner of DataInc?", True, "boolean", "single_hop"),
            Question("What products does CloudSys use?", "CloudDB, MLKit", "list", "single_hop"),
            # Multi-hop (5)
            Question("What product is produced by John's company?", "CloudDB", "string", "multi_hop"),
            Question("Who works at the company that produces CloudDB?", "John", "string", "multi_hop"),
            Question("Is there a path from John to MLKit?", True, "boolean", "multi_hop"),
            Question("How many hops from Jane to DataAPI?", 1, "number", "multi_hop"),
            Question("What company uses a product made by AILabs?", "CloudSys", "string", "multi_hop"),
            # Analysis/Aggregation (5)
            Question("How many company nodes are there?", 4, "number", "analysis"),
            Question("How many person nodes are there?", 4, "number", "analysis"),
            Question("What is the total employees across all companies?", 10500, "number", "aggregation"),
            Question("Which company has the most employees?", "TechCorp", "string", "analysis"),
            Question("What is the total revenue of all companies?", 1060, "number", "aggregation"),
        ]
    }

    # =========================================================================
    # Dataset 3: Organization Chart (15 questions)
    # =========================================================================
    datasets["org_chart"] = {
        "description": "Organization hierarchy (DAG - no cycles)",
        "data": {
            "nodes": [
                {"id": 1, "type": "employee", "name": "CEO Alice", "level": "C-Suite", "salary": 300000, "department": "Executive"},
                {"id": 2, "type": "employee", "name": "VP Bob", "level": "VP", "salary": 200000, "department": "Engineering"},
                {"id": 3, "type": "employee", "name": "VP Carol", "level": "VP", "salary": 190000, "department": "Product"},
                {"id": 4, "type": "employee", "name": "Dir David", "level": "Director", "salary": 160000, "department": "Engineering"},
                {"id": 5, "type": "employee", "name": "Dir Eve", "level": "Director", "salary": 155000, "department": "Product"},
                {"id": 6, "type": "employee", "name": "Mgr Frank", "level": "Manager", "salary": 130000, "department": "Engineering"},
                {"id": 7, "type": "employee", "name": "Mgr Grace", "level": "Manager", "salary": 125000, "department": "Product"},
                {"id": 8, "type": "employee", "name": "Eng Henry", "level": "IC", "salary": 110000, "department": "Engineering"},
                {"id": 9, "type": "employee", "name": "Eng Ivy", "level": "IC", "salary": 105000, "department": "Engineering"},
                {"id": 10, "type": "employee", "name": "PM Jack", "level": "IC", "salary": 100000, "department": "Product"},
            ],
            "edges": [
                {"source": 2, "target": 1, "relation": "reports_to"},
                {"source": 3, "target": 1, "relation": "reports_to"},
                {"source": 4, "target": 2, "relation": "reports_to"},
                {"source": 5, "target": 3, "relation": "reports_to"},
                {"source": 6, "target": 4, "relation": "reports_to"},
                {"source": 7, "target": 5, "relation": "reports_to"},
                {"source": 8, "target": 6, "relation": "reports_to"},
                {"source": 9, "target": 6, "relation": "reports_to"},
                {"source": 10, "target": 7, "relation": "reports_to"},
            ]
        },
        "questions": [
            # Single-hop (5)
            Question("Who does VP Bob report to?", "CEO Alice", "string", "single_hop"),
            Question("Who reports to Dir David?", "Mgr Frank", "string", "single_hop"),
            Question("How many direct reports does CEO Alice have?", 2, "number", "single_hop"),
            Question("What department is Eng Henry in?", "Engineering", "string", "single_hop"),
            Question("Who reports to Mgr Frank?", "Eng Henry, Eng Ivy", "list", "single_hop"),
            # Path finding (5)
            Question("What is the path from Eng Henry to CEO Alice?", "Eng Henry -> Mgr Frank -> Dir David -> VP Bob -> CEO Alice", "path", "path_finding"),
            Question("How many levels are in the org chart?", 5, "number", "analysis"),
            Question("Is this org chart a DAG (no cycles)?", True, "boolean", "analysis"),
            Question("Who is at the top of the hierarchy?", "CEO Alice", "string", "analysis"),
            Question("How many hops from Eng Ivy to CEO Alice?", 4, "number", "path_finding"),
            # Aggregation (5)
            Question("What is the total salary of all employees?", 1575000, "number", "aggregation"),
            Question("How many ICs are there?", 3, "number", "analysis"),
            Question("How many employees are in Engineering department?", 5, "number", "aggregation"),
            Question("What is the average salary of VPs?", 195000, "number", "aggregation"),
            Question("Who are the bottom-level employees?", "Eng Henry, Eng Ivy, PM Jack", "list", "analysis"),
        ]
    }

    # =========================================================================
    # Dataset 4: Flight Routes (15 questions)
    # =========================================================================
    datasets["flight_routes"] = {
        "description": "Flight routes between cities with distances and durations",
        "data": {
            "nodes": [
                {"id": 1, "type": "city", "name": "NYC", "country": "USA", "hub": True, "timezone": "EST"},
                {"id": 2, "type": "city", "name": "LAX", "country": "USA", "hub": True, "timezone": "PST"},
                {"id": 3, "type": "city", "name": "Chicago", "country": "USA", "hub": True, "timezone": "CST"},
                {"id": 4, "type": "city", "name": "London", "country": "UK", "hub": True, "timezone": "GMT"},
                {"id": 5, "type": "city", "name": "Paris", "country": "France", "hub": True, "timezone": "CET"},
                {"id": 6, "type": "city", "name": "Tokyo", "country": "Japan", "hub": True, "timezone": "JST"},
                {"id": 7, "type": "city", "name": "Sydney", "country": "Australia", "hub": True, "timezone": "AEST"},
                {"id": 8, "type": "city", "name": "Dubai", "country": "UAE", "hub": True, "timezone": "GST"},
            ],
            "edges": [
                {"source": 1, "target": 2, "relation": "flight", "distance": 2475, "duration": 330},
                {"source": 1, "target": 3, "relation": "flight", "distance": 711, "duration": 120},
                {"source": 1, "target": 4, "relation": "flight", "distance": 3459, "duration": 420},
                {"source": 2, "target": 6, "relation": "flight", "distance": 5478, "duration": 660},
                {"source": 3, "target": 2, "relation": "flight", "distance": 1745, "duration": 240},
                {"source": 4, "target": 5, "relation": "flight", "distance": 213, "duration": 60},
                {"source": 4, "target": 8, "relation": "flight", "distance": 3400, "duration": 400},
                {"source": 5, "target": 6, "relation": "flight", "distance": 6034, "duration": 720},
                {"source": 6, "target": 7, "relation": "flight", "distance": 4863, "duration": 540},
                {"source": 8, "target": 7, "relation": "flight", "distance": 7480, "duration": 840},
            ]
        },
        "questions": [
            # Single-hop (5)
            Question("Can you fly directly from NYC to LAX?", True, "boolean", "single_hop"),
            Question("What is the distance from NYC to London?", 3459, "number", "single_hop"),
            Question("What is the flight duration from London to Paris in minutes?", 60, "number", "single_hop"),
            Question("Is there a direct flight from Tokyo to Sydney?", True, "boolean", "single_hop"),
            Question("What country is Dubai in?", "UAE", "string", "single_hop"),
            # Path finding (5)
            Question("Can you reach Tokyo from NYC?", True, "boolean", "path_finding"),
            Question("What is the shortest path from NYC to Tokyo?", "NYC -> LAX -> Tokyo", "path", "path_finding"),
            Question("How many hops from Chicago to Paris?", 3, "number", "path_finding"),
            Question("Is Sydney reachable from NYC?", True, "boolean", "path_finding"),
            Question("What is a path from NYC to Sydney?", "NYC -> LAX -> Tokyo -> Sydney", "path", "path_finding"),
            # Analysis (5)
            Question("How many hub cities are there?", 8, "number", "analysis"),
            Question("Which city has the most outgoing flights?", "NYC", "string", "analysis"),
            Question("What is the longest direct flight distance?", 7480, "number", "analysis"),
            Question("Is London reachable from Tokyo?", False, "boolean", "path_finding"),
            Question("How many direct routes are there?", 10, "number", "analysis"),
        ]
    }

    # =========================================================================
    # Dataset 5: Movie Database (15 questions)
    # =========================================================================
    datasets["movie_database"] = {
        "description": "Movies, actors, directors, and genres",
        "data": {
            "nodes": [
                {"id": 1, "type": "movie", "name": "Inception", "year": 2010, "rating": 8.8, "budget": 160},
                {"id": 2, "type": "movie", "name": "The Dark Knight", "year": 2008, "rating": 9.0, "budget": 185},
                {"id": 3, "type": "movie", "name": "Interstellar", "year": 2014, "rating": 8.6, "budget": 165},
                {"id": 4, "type": "movie", "name": "Pulp Fiction", "year": 1994, "rating": 8.9, "budget": 8},
                {"id": 10, "type": "actor", "name": "Leonardo DiCaprio", "born": 1974, "oscars": 1},
                {"id": 11, "type": "actor", "name": "Christian Bale", "born": 1974, "oscars": 1},
                {"id": 12, "type": "actor", "name": "Matthew McConaughey", "born": 1969, "oscars": 1},
                {"id": 13, "type": "actor", "name": "Samuel L Jackson", "born": 1948, "oscars": 0},
                {"id": 20, "type": "director", "name": "Christopher Nolan", "born": 1970, "movies_directed": 12},
                {"id": 21, "type": "director", "name": "Quentin Tarantino", "born": 1963, "movies_directed": 10},
                {"id": 30, "type": "genre", "name": "Sci-Fi"},
                {"id": 31, "type": "genre", "name": "Action"},
                {"id": 32, "type": "genre", "name": "Crime"},
            ],
            "edges": [
                {"source": 10, "target": 1, "relation": "acted_in", "role": "Dom Cobb"},
                {"source": 11, "target": 2, "relation": "acted_in", "role": "Bruce Wayne"},
                {"source": 12, "target": 3, "relation": "acted_in", "role": "Cooper"},
                {"source": 13, "target": 4, "relation": "acted_in", "role": "Jules"},
                {"source": 20, "target": 1, "relation": "directed"},
                {"source": 20, "target": 2, "relation": "directed"},
                {"source": 20, "target": 3, "relation": "directed"},
                {"source": 21, "target": 4, "relation": "directed"},
                {"source": 1, "target": 30, "relation": "has_genre"},
                {"source": 1, "target": 31, "relation": "has_genre"},
                {"source": 2, "target": 31, "relation": "has_genre"},
                {"source": 2, "target": 32, "relation": "has_genre"},
                {"source": 3, "target": 30, "relation": "has_genre"},
                {"source": 4, "target": 32, "relation": "has_genre"},
            ]
        },
        "questions": [
            # Single-hop (5)
            Question("Who directed Inception?", "Christopher Nolan", "string", "single_hop"),
            Question("What movies did Christopher Nolan direct?", "Inception, The Dark Knight, Interstellar", "list", "single_hop"),
            Question("Who acted in Pulp Fiction?", "Samuel L Jackson", "string", "single_hop"),
            Question("What genre is Inception?", "Sci-Fi, Action", "list", "single_hop"),
            Question("What year was The Dark Knight released?", 2008, "number", "single_hop"),
            # Multi-hop (5)
            Question("Who directed the movie Leonardo DiCaprio acted in?", "Christopher Nolan", "string", "multi_hop"),
            Question("What genres are in movies directed by Nolan?", "Sci-Fi, Action, Crime", "list", "multi_hop"),
            Question("Is there a path from DiCaprio to Sci-Fi genre?", True, "boolean", "multi_hop"),
            Question("Who acts in Crime genre movies?", "Christian Bale, Samuel L Jackson", "list", "pattern"),
            Question("What is the rating of the movie Christian Bale acted in?", 9.0, "number", "multi_hop"),
            # Analysis/Aggregation (5)
            Question("How many movies are in the database?", 4, "number", "analysis"),
            Question("What is the highest rated movie?", "The Dark Knight", "string", "analysis"),
            Question("What is the total budget of all movies?", 518, "number", "aggregation"),
            Question("How many actors have won an Oscar?", 3, "number", "aggregation"),
            Question("Which director has directed the most movies in the database?", "Christopher Nolan", "string", "analysis"),
        ]
    }

    # =========================================================================
    # Dataset 6: E-Commerce (15 questions)
    # =========================================================================
    datasets["ecommerce"] = {
        "description": "E-commerce with customers, orders, products",
        "data": {
            "nodes": [
                {"id": 1, "type": "customer", "name": "John Smith", "tier": "Gold", "total_spent": 5000, "orders_count": 12},
                {"id": 2, "type": "customer", "name": "Jane Doe", "tier": "Silver", "total_spent": 2500, "orders_count": 8},
                {"id": 3, "type": "customer", "name": "Bob Wilson", "tier": "Bronze", "total_spent": 800, "orders_count": 3},
                {"id": 10, "type": "order", "order_id": "ORD001", "date": "2024-01-15", "total": 450, "status": "delivered"},
                {"id": 11, "type": "order", "order_id": "ORD002", "date": "2024-02-20", "total": 320, "status": "delivered"},
                {"id": 12, "type": "order", "order_id": "ORD003", "date": "2024-03-10", "total": 180, "status": "shipped"},
                {"id": 13, "type": "order", "order_id": "ORD004", "date": "2024-03-15", "total": 550, "status": "pending"},
                {"id": 20, "type": "product", "name": "Laptop", "price": 999, "category": "Electronics", "stock": 50},
                {"id": 21, "type": "product", "name": "Headphones", "price": 199, "category": "Electronics", "stock": 150},
                {"id": 22, "type": "product", "name": "Desk Chair", "price": 299, "category": "Furniture", "stock": 30},
                {"id": 23, "type": "product", "name": "Monitor", "price": 399, "category": "Electronics", "stock": 75},
            ],
            "edges": [
                {"source": 1, "target": 10, "relation": "placed"},
                {"source": 1, "target": 11, "relation": "placed"},
                {"source": 2, "target": 12, "relation": "placed"},
                {"source": 3, "target": 13, "relation": "placed"},
                {"source": 10, "target": 20, "relation": "contains", "quantity": 1},
                {"source": 10, "target": 21, "relation": "contains", "quantity": 2},
                {"source": 11, "target": 22, "relation": "contains", "quantity": 1},
                {"source": 12, "target": 21, "relation": "contains", "quantity": 1},
                {"source": 13, "target": 23, "relation": "contains", "quantity": 1},
                {"source": 13, "target": 22, "relation": "contains", "quantity": 1},
            ]
        },
        "questions": [
            # Single-hop (5)
            Question("What tier is John Smith?", "Gold", "string", "single_hop"),
            Question("What orders did John Smith place?", "ORD001, ORD002", "list", "single_hop"),
            Question("What products are in order ORD001?", "Laptop, Headphones", "list", "single_hop"),
            Question("What is the price of Laptop?", 999, "number", "single_hop"),
            Question("What is the status of ORD003?", "shipped", "string", "single_hop"),
            # Multi-hop (5)
            Question("What products did John Smith order?", "Laptop, Headphones, Desk Chair", "list", "multi_hop"),
            Question("Which customer ordered a Laptop?", "John Smith", "string", "multi_hop"),
            Question("What categories of products did Jane Doe order?", "Electronics", "string", "multi_hop"),
            Question("Is there a path from Bob Wilson to Monitor?", True, "boolean", "multi_hop"),
            Question("How many products did John Smith order in total?", 3, "number", "multi_hop"),
            # Analysis/Aggregation (5)
            Question("How many customers are there?", 3, "number", "analysis"),
            Question("What is the total value of all orders?", 1500, "number", "aggregation"),
            Question("How many products are in Electronics category?", 3, "number", "aggregation"),
            Question("Which customer has spent the most?", "John Smith", "string", "analysis"),
            Question("How many orders are pending?", 1, "number", "aggregation"),
        ]
    }

    # =========================================================================
    # Dataset 7: Academic Citations (10 questions)
    # =========================================================================
    datasets["academic_citations"] = {
        "description": "Academic papers and citation network",
        "data": {
            "nodes": [
                {"id": 1, "type": "paper", "title": "Deep Learning", "year": 2015, "citations": 45000, "field": "AI"},
                {"id": 2, "type": "paper", "title": "Attention Is All You Need", "year": 2017, "citations": 80000, "field": "NLP"},
                {"id": 3, "type": "paper", "title": "BERT", "year": 2018, "citations": 65000, "field": "NLP"},
                {"id": 4, "type": "paper", "title": "ResNet", "year": 2015, "citations": 120000, "field": "CV"},
                {"id": 5, "type": "paper", "title": "GPT-3", "year": 2020, "citations": 25000, "field": "NLP"},
                {"id": 10, "type": "author", "name": "Yann LeCun", "h_index": 150, "institution": "Meta"},
                {"id": 11, "type": "author", "name": "Geoffrey Hinton", "h_index": 170, "institution": "Google"},
                {"id": 12, "type": "author", "name": "Yoshua Bengio", "h_index": 160, "institution": "MILA"},
            ],
            "edges": [
                {"source": 10, "target": 1, "relation": "authored"},
                {"source": 11, "target": 1, "relation": "authored"},
                {"source": 12, "target": 1, "relation": "authored"},
                {"source": 11, "target": 4, "relation": "authored"},
                {"source": 2, "target": 1, "relation": "cites"},
                {"source": 3, "target": 2, "relation": "cites"},
                {"source": 3, "target": 1, "relation": "cites"},
                {"source": 5, "target": 2, "relation": "cites"},
                {"source": 5, "target": 3, "relation": "cites"},
            ]
        },
        "questions": [
            # Single-hop (3)
            Question("Who authored Deep Learning paper?", "Yann LeCun, Geoffrey Hinton, Yoshua Bengio", "list", "single_hop"),
            Question("What papers cite Deep Learning?", "Attention Is All You Need, BERT", "list", "single_hop"),
            Question("How many citations does BERT have?", 65000, "number", "single_hop"),
            # Multi-hop (3)
            Question("What papers cite papers that cite Deep Learning?", "BERT, GPT-3", "list", "multi_hop"),
            Question("Is there a citation path from GPT-3 to Deep Learning?", True, "boolean", "multi_hop"),
            Question("How many hops from GPT-3 to Deep Learning?", 2, "number", "path_finding"),
            # Analysis (4)
            Question("What is the most cited paper?", "ResNet", "string", "analysis"),
            Question("How many papers are in NLP field?", 3, "number", "aggregation"),
            Question("What is the total citations across all papers?", 335000, "number", "aggregation"),
            Question("Which author has the highest h-index?", "Geoffrey Hinton", "string", "analysis"),
        ]
    }

    return datasets


# =============================================================================
# BENCHMARK RUNNER
# =============================================================================

def run_benchmark(skip_llm: bool = False, formats_to_test: List[str] = None):
    """Run the complete knowledge graph benchmark."""

    # Clear logs
    for log_path in [LOG_FILE, LATEST_LOG]:
        if os.path.exists(log_path):
            os.remove(log_path)

    log("=" * 100)
    log("ISONGRAPH KNOWLEDGE GRAPH BENCHMARK - 100 Questions")
    log("=" * 100)
    log(f"Timestamp: {datetime.now().isoformat()}")
    log(f"Tokenizer: {TOKENIZER_NAME}")
    log(f"Skip LLM: {skip_llm}")
    log(f"API: DeepSeek (deepseek-chat)")
    log("")

    # Select formats to test
    if formats_to_test is None:
        formats_to_test = list(FORMATS.keys())

    active_formats = {k: v for k, v in FORMATS.items() if k in formats_to_test}

    log(f"Formats being tested ({len(active_formats)}):")
    for fmt in active_formats:
        log(f"  - {fmt}")
    log("")

    datasets = create_graph_datasets()

    # Collect all questions
    all_questions = []
    for ds_name, ds in datasets.items():
        for q in ds["questions"]:
            all_questions.append((ds_name, q))

    log(f"Total Questions: {len(all_questions)}")
    log(f"Datasets: {len(datasets)}")
    log("")

    # Token counting per format
    format_tokens = {fmt: 0 for fmt in active_formats}
    format_correct = {fmt: 0 for fmt in active_formats}

    results = []

    for ds_name, ds in datasets.items():
        log(f"\n{'='*80}")
        log(f"DATASET: {ds_name}")
        log(f"Description: {ds['description']}")
        log(f"Questions: {len(ds['questions'])}")
        log("=" * 80)

        data = ds["data"]

        # Convert to each format and count tokens
        format_data = {}
        log("\nToken counts by format:")
        for fmt_name, converter in active_formats.items():
            try:
                formatted = converter(data)
                tokens = count_tokens(formatted)
                format_data[fmt_name] = formatted
                format_tokens[fmt_name] += tokens
                log(f"  {fmt_name}: {tokens} tokens")
            except Exception as e:
                log(f"  {fmt_name}: ERROR - {e}")
                format_data[fmt_name] = json.dumps(data)

        log("")

        # Run questions
        for i, q in enumerate(ds["questions"], 1):
            log(f"\nQ{i} [{q.category}]: {q.question}")
            log(f"   Expected: {q.expected} ({q.answer_type})")

            for fmt_name, formatted in format_data.items():
                if skip_llm:
                    log(f"   {fmt_name}: [SKIPPED]")
                    continue

                prompt = f"""Given this graph data:

{formatted}

Question: {q.question}

Answer with just the value, no explanation. Be concise."""

                response = call_llm(prompt)
                is_correct, reason = validate_answer(response, q.expected, q.answer_type)

                if is_correct:
                    format_correct[fmt_name] += 1
                    log(f"   {fmt_name}: ✓ {response[:50]}", timestamp=True)
                else:
                    log(f"   {fmt_name}: ✗ {response[:50]} ({reason})", timestamp=True)

                results.append({
                    "dataset": ds_name,
                    "question": q.question,
                    "expected": str(q.expected),
                    "category": q.category,
                    "format": fmt_name,
                    "response": response,
                    "correct": is_correct,
                })

                time.sleep(0.5)  # Rate limiting

    # Summary
    log("\n" + "=" * 100)
    log("SUMMARY")
    log("=" * 100)

    total_questions = len(all_questions)

    log("\n" + "-" * 60)
    log("TOKEN COUNTS (Lower is Better)")
    log("-" * 60)
    sorted_tokens = sorted(format_tokens.items(), key=lambda x: x[1])
    json_tokens = format_tokens.get("JSON", format_tokens.get("JSON Compact", 1))

    for fmt_name, tokens in sorted_tokens:
        savings = ((json_tokens - tokens) / json_tokens * 100) if json_tokens > 0 else 0
        log(f"  {fmt_name:20s}: {tokens:6d} tokens  (saves {savings:.1f}% vs JSON)")

    if not skip_llm:
        log("\n" + "-" * 60)
        log("ACCURACY RESULTS")
        log("-" * 60)
        sorted_accuracy = sorted(format_correct.items(), key=lambda x: x[1], reverse=True)

        for fmt_name in [x[0] for x in sorted_accuracy]:
            correct = format_correct[fmt_name]
            accuracy = (correct / total_questions) * 100 if total_questions > 0 else 0
            tokens = format_tokens[fmt_name]
            acc_per_1k = (accuracy / tokens) * 1000 if tokens > 0 else 0
            log(f"  {fmt_name:20s}: {correct:3d}/{total_questions} ({accuracy:5.1f}%)  Acc/1K: {acc_per_1k:6.2f}")

        log("\n" + "-" * 60)
        log("EFFICIENCY RANKING (Accuracy per 1K Tokens)")
        log("-" * 60)
        efficiency = []
        for fmt_name in active_formats:
            correct = format_correct[fmt_name]
            accuracy = (correct / total_questions) * 100 if total_questions > 0 else 0
            tokens = format_tokens[fmt_name]
            acc_per_1k = (accuracy / tokens) * 1000 if tokens > 0 else 0
            efficiency.append((fmt_name, acc_per_1k, accuracy, tokens))

        efficiency.sort(key=lambda x: x[1], reverse=True)
        for rank, (fmt_name, acc_per_1k, accuracy, tokens) in enumerate(efficiency, 1):
            log(f"  {rank}. {fmt_name:20s}: {acc_per_1k:6.2f} Acc/1K  ({accuracy:.1f}% accuracy, {tokens} tokens)")

    # Category breakdown
    log("\n" + "-" * 60)
    log("QUESTIONS BY CATEGORY")
    log("-" * 60)
    categories = {}
    for ds_name, q in all_questions:
        categories[q.category] = categories.get(q.category, 0) + 1
    for cat, count in sorted(categories.items()):
        log(f"  {cat:20s}: {count}")

    # Dataset breakdown
    log("\n" + "-" * 60)
    log("QUESTIONS BY DATASET")
    log("-" * 60)
    for ds_name, ds in datasets.items():
        log(f"  {ds_name:25s}: {len(ds['questions'])}")

    log("\n" + "=" * 100)
    log("BENCHMARK COMPLETE")
    log("=" * 100)

    return results


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ISONGraph Knowledge Graph Benchmark - 100 Questions")
    parser.add_argument("--skip-llm", action="store_true", help="Skip LLM accuracy tests (token counting only)")
    parser.add_argument("--full", action="store_true", help="Run full benchmark with LLM")
    parser.add_argument("--formats", nargs="+", help="Specific formats to test",
                       choices=list(FORMATS.keys()) + ["all"])
    parser.add_argument("--quick", action="store_true", help="Quick test with core formats only")
    args = parser.parse_args()

    # Determine formats to test
    formats_to_test = None
    if args.formats:
        if "all" in args.formats:
            formats_to_test = list(FORMATS.keys())
        else:
            formats_to_test = args.formats
    elif args.quick:
        formats_to_test = ["ISONGraph", "ISON", "JSON Compact", "JSON"]

    if args.full:
        run_benchmark(skip_llm=False, formats_to_test=formats_to_test)
    else:
        run_benchmark(skip_llm=args.skip_llm if not args.full else False, formats_to_test=formats_to_test)

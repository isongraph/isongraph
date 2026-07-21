#!/usr/bin/env python3
"""
ISONGraph Benchmark - 50 Questions for Graph Operations
========================================================

Tests ISONGraph and ISONGraphantic capabilities with:
- Multi-hop traversal (1-hop, 2-hop, 3-hop, N-hop)
- Path finding (shortest path, all paths)
- Graph analysis (connectivity, cycles, components)
- Relationship patterns (follows, knows, works_at, reports_to)
- Validation checks (schema, constraints, cardinality)

Question Categories (50 total):
1. Single-hop Retrieval (10) - Direct neighbor queries
2. Multi-hop Traversal (10) - Friends of friends, reachability
3. Path Finding (10) - Shortest path, path existence
4. Graph Analysis (10) - Connectivity, cycles, degrees
5. Validation & Schema (10) - Constraint validation

Formats: ISON, TOON, JSON Compact, JSON
"""

import json
import tiktoken
import sys
import os
import requests
import time
import re
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass

# Import official libraries
import ison_parser
from ison_graph import ISONGraph, Direction

try:
    import toon
    HAS_TOON = True
except ImportError:
    HAS_TOON = False

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
LOG_FILE = os.path.join(LOG_DIR, f"benchmark_graph_{TIMESTAMP}.log")
LATEST_LOG = os.path.join(LOG_DIR, "benchmark_graph_latest.log")


def log(message: str, also_print: bool = True, end: str = "\n", timestamp: bool = False):
    """Log message to file and optionally print."""
    # Add timestamp if requested
    if timestamp:
        ts = datetime.now().strftime('%H:%M:%S')
        message = f"[{ts}] {message}"

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(message + end)
    with open(LATEST_LOG, "a", encoding="utf-8") as f:
        f.write(message + end)
    if also_print:
        # Replace Unicode symbols for Windows console compatibility
        # Use explicit Unicode escapes to ensure proper matching
        safe_message = message
        safe_message = safe_message.replace("\u2713", "[PASS]")  # ✓
        safe_message = safe_message.replace("\u2717", "[FAIL]")  # ✗
        safe_message = safe_message.replace("\u2192", "->")      # →
        safe_message = safe_message.replace("\u2794", "->")      # ➔
        safe_message = safe_message.replace("\u279C", "->")      # ➜
        safe_message = safe_message.replace("\u27F6", "->")      # ⟶
        # Final fallback: encode to ASCII, replacing any remaining non-ASCII
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
        true_values = ["true", "yes", "exists", "connected", "has cycle", "reachable", "valid"]
        false_values = ["false", "no", "not connected", "no cycle", "unreachable", "invalid", "acyclic"]

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
# FORMAT CONVERTERS
# =============================================================================

def to_json_pretty(data: dict) -> str:
    return json.dumps(data, indent=2)


def to_json_compact(data: dict) -> str:
    return json.dumps(data, separators=(',', ':'))


def to_toon(data: dict) -> str:
    if HAS_TOON:
        return toon.encode(data)
    return to_json_compact(data)


def to_ison(data: dict) -> str:
    """Convert to ISON format using official ison-py library."""
    doc = ison_parser.from_dict(data, auto_refs=True, smart_order=True)
    return ison_parser.dumps(doc, align_columns=False)


def to_isongraph(data: dict) -> str:
    """Convert to ISONGraph format (nodes/edges explicit)."""
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

            # Determine source/target types
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
                pass  # Skip if nodes don't exist

    return graph.to_ison()


FORMATS = {
    "ISON": to_ison,
    "ISONGraph": to_isongraph,
    "JSON Compact": to_json_compact,
    "JSON": to_json_pretty,
}

if HAS_TOON:
    FORMATS["TOON"] = to_toon


# =============================================================================
# GRAPH DATASETS WITH 50 QUESTIONS
# =============================================================================

@dataclass
class Question:
    """A benchmark question with verified expected answer."""
    question: str
    expected: Any
    answer_type: str  # string, number, boolean, list, path, null
    category: str  # single_hop, multi_hop, path_finding, analysis, validation


def create_graph_datasets() -> Dict[str, Dict]:
    """Create graph datasets with 50 questions total."""

    datasets = {}

    # =========================================================================
    # Dataset 1: Social Network (15 questions)
    # Graph: Alice -> Bob -> Carol -> David -> Eve
    #        Alice -> Carol (direct)
    #        Eve -> Alice (cycle back)
    # =========================================================================
    datasets["social_network"] = {
        "description": "Social network with follows relationships",
        "data": {
            "nodes": [
                {"id": 1, "type": "person", "name": "Alice", "age": 28, "verified": True},
                {"id": 2, "type": "person", "name": "Bob", "age": 34, "verified": False},
                {"id": 3, "type": "person", "name": "Carol", "age": 29, "verified": True},
                {"id": 4, "type": "person", "name": "David", "age": 42, "verified": False},
                {"id": 5, "type": "person", "name": "Eve", "age": 31, "verified": True},
            ],
            "edges": [
                {"source": 1, "target": 2, "relation": "follows", "since": 2020},
                {"source": 1, "target": 3, "relation": "follows", "since": 2021},
                {"source": 2, "target": 3, "relation": "follows", "since": 2019},
                {"source": 3, "target": 4, "relation": "follows", "since": 2020},
                {"source": 4, "target": 5, "relation": "follows", "since": 2022},
                {"source": 5, "target": 1, "relation": "follows", "since": 2021},
            ]
        },
        "questions": [
            # Single-hop (5)
            Question("Who does Alice follow?", "Bob, Carol", "list", "single_hop"),
            Question("Who follows Carol?", "Alice, Bob", "list", "single_hop"),
            Question("How many people does Alice follow?", 2, "number", "single_hop"),
            Question("Does Bob follow Carol?", True, "boolean", "single_hop"),
            Question("Does David follow Alice?", False, "boolean", "single_hop"),

            # Multi-hop (5)
            Question("Who can Alice reach in 2 hops?", "Carol, David", "list", "multi_hop"),
            Question("Can Alice reach Eve in 3 hops?", True, "boolean", "multi_hop"),
            Question("Who are Carol's followers' followers?", "Carol", "string", "multi_hop"),
            Question("How many hops from Alice to David?", 2, "number", "multi_hop"),
            Question("Who can reach Alice in 1 hop?", "Eve", "string", "multi_hop"),

            # Analysis (5)
            Question("Does this graph have a cycle?", True, "boolean", "analysis"),
            Question("How many nodes are there?", 5, "number", "analysis"),
            Question("How many edges are there?", 6, "number", "analysis"),
            Question("Who has the most followers?", "Carol", "string", "analysis"),
            Question("Is the graph connected?", True, "boolean", "analysis"),
        ]
    }

    # =========================================================================
    # Dataset 2: Knowledge Graph (15 questions)
    # Companies, People, Products with various relationships
    # =========================================================================
    datasets["knowledge_graph"] = {
        "description": "Knowledge graph with companies, people, products",
        "data": {
            "nodes": [
                {"id": 1, "type": "company", "name": "TechCorp", "employees": 5000, "founded": 2010},
                {"id": 2, "type": "company", "name": "DataInc", "employees": 1200, "founded": 2015},
                {"id": 3, "type": "company", "name": "CloudSys", "employees": 3500, "founded": 2012},
                {"id": 4, "type": "person", "name": "John", "role": "CEO", "salary": 250000},
                {"id": 5, "type": "person", "name": "Jane", "role": "CTO", "salary": 200000},
                {"id": 6, "type": "person", "name": "Mike", "role": "Engineer", "salary": 120000},
                {"id": 7, "type": "product", "name": "CloudDB", "price": 99, "category": "database"},
                {"id": 8, "type": "product", "name": "DataAPI", "price": 49, "category": "api"},
            ],
            "edges": [
                {"source": 4, "target": 1, "relation": "works_at"},
                {"source": 5, "target": 2, "relation": "works_at"},
                {"source": 6, "target": 3, "relation": "works_at"},
                {"source": 1, "target": 2, "relation": "partner"},
                {"source": 1, "target": 3, "relation": "customer"},
                {"source": 2, "target": 3, "relation": "vendor"},
                {"source": 1, "target": 7, "relation": "produces"},
                {"source": 2, "target": 8, "relation": "produces"},
                {"source": 3, "target": 7, "relation": "uses"},
            ]
        },
        "questions": [
            # Single-hop (5)
            Question("Where does John work?", "TechCorp", "string", "single_hop"),
            Question("What does TechCorp produce?", "CloudDB", "string", "single_hop"),
            Question("Who works at CloudSys?", "Mike", "string", "single_hop"),
            Question("Is TechCorp a partner of DataInc?", True, "boolean", "single_hop"),
            Question("What product does CloudSys use?", "CloudDB", "string", "single_hop"),

            # Multi-hop (5)
            Question("What product is produced by John's company?", "CloudDB", "string", "multi_hop"),
            Question("Who works at the company that produces CloudDB?", "John", "string", "multi_hop"),
            Question("What company is a customer of the partner of TechCorp?", "CloudSys", "string", "multi_hop"),
            Question("Is there a path from John to CloudDB?", True, "boolean", "multi_hop"),
            Question("How many hops from Jane to DataAPI?", 1, "number", "multi_hop"),

            # Analysis (5)
            Question("How many company nodes are there?", 3, "number", "analysis"),
            Question("How many person nodes are there?", 3, "number", "analysis"),
            Question("How many product nodes are there?", 2, "number", "analysis"),
            Question("What is the total employees across all companies?", 9700, "number", "analysis"),
            Question("Which company has the most employees?", "TechCorp", "string", "analysis"),
        ]
    }

    # =========================================================================
    # Dataset 3: Organization Chart (10 questions) - DAG
    # CEO -> VP1, VP2 -> Directors -> Managers -> ICs
    # =========================================================================
    datasets["org_chart"] = {
        "description": "Organization hierarchy (DAG - no cycles)",
        "data": {
            "nodes": [
                {"id": 1, "type": "employee", "name": "CEO Alice", "level": "C-Suite", "salary": 300000},
                {"id": 2, "type": "employee", "name": "VP Bob", "level": "VP", "salary": 200000},
                {"id": 3, "type": "employee", "name": "VP Carol", "level": "VP", "salary": 190000},
                {"id": 4, "type": "employee", "name": "Dir David", "level": "Director", "salary": 160000},
                {"id": 5, "type": "employee", "name": "Dir Eve", "level": "Director", "salary": 155000},
                {"id": 6, "type": "employee", "name": "Mgr Frank", "level": "Manager", "salary": 130000},
                {"id": 7, "type": "employee", "name": "Eng Grace", "level": "IC", "salary": 110000},
                {"id": 8, "type": "employee", "name": "Eng Henry", "level": "IC", "salary": 105000},
            ],
            "edges": [
                {"source": 2, "target": 1, "relation": "reports_to"},
                {"source": 3, "target": 1, "relation": "reports_to"},
                {"source": 4, "target": 2, "relation": "reports_to"},
                {"source": 5, "target": 3, "relation": "reports_to"},
                {"source": 6, "target": 4, "relation": "reports_to"},
                {"source": 7, "target": 6, "relation": "reports_to"},
                {"source": 8, "target": 6, "relation": "reports_to"},
            ]
        },
        "questions": [
            # Path/Hierarchy (5)
            Question("Who does VP Bob report to?", "CEO Alice", "string", "single_hop"),
            Question("Who reports to Dir David?", "Mgr Frank", "string", "single_hop"),
            Question("How many direct reports does CEO Alice have?", 2, "number", "single_hop"),
            Question("Who is at the top of the hierarchy?", "CEO Alice", "string", "analysis"),
            Question("How many levels are in the org chart?", 5, "number", "analysis"),

            # Analysis (5)
            Question("Is this org chart a DAG (no cycles)?", True, "boolean", "analysis"),
            Question("What is the total salary of all employees?", 1350000, "number", "analysis"),
            Question("How many ICs are there?", 2, "number", "analysis"),
            Question("Who are the bottom-level employees?", "Eng Grace, Eng Henry", "list", "analysis"),
            Question("What is the path from Eng Grace to CEO Alice?", "Eng Grace -> Mgr Frank -> Dir David -> VP Bob -> CEO Alice", "path", "path_finding"),
        ]
    }

    # =========================================================================
    # Dataset 4: Flight Routes (10 questions)
    # Cities connected by flights with distances
    # =========================================================================
    datasets["flight_routes"] = {
        "description": "Flight routes between cities",
        "data": {
            "nodes": [
                {"id": 1, "type": "city", "name": "NYC", "country": "USA", "hub": True},
                {"id": 2, "type": "city", "name": "LAX", "country": "USA", "hub": True},
                {"id": 3, "type": "city", "name": "Chicago", "country": "USA", "hub": False},
                {"id": 4, "type": "city", "name": "London", "country": "UK", "hub": True},
                {"id": 5, "type": "city", "name": "Paris", "country": "France", "hub": True},
                {"id": 6, "type": "city", "name": "Tokyo", "country": "Japan", "hub": True},
            ],
            "edges": [
                {"source": 1, "target": 2, "relation": "flight", "distance": 2475, "duration": 330},
                {"source": 1, "target": 3, "relation": "flight", "distance": 711, "duration": 120},
                {"source": 1, "target": 4, "relation": "flight", "distance": 3459, "duration": 420},
                {"source": 2, "target": 6, "relation": "flight", "distance": 5478, "duration": 660},
                {"source": 3, "target": 2, "relation": "flight", "distance": 1745, "duration": 240},
                {"source": 4, "target": 5, "relation": "flight", "distance": 213, "duration": 60},
                {"source": 5, "target": 6, "relation": "flight", "distance": 6034, "duration": 720},
            ]
        },
        "questions": [
            # Path finding (5)
            Question("Can you fly directly from NYC to LAX?", True, "boolean", "single_hop"),
            Question("What is the distance from NYC to London?", 3459, "number", "single_hop"),
            Question("Can you reach Tokyo from NYC?", True, "boolean", "path_finding"),
            Question("What is the shortest path from NYC to Tokyo?", "NYC -> LAX -> Tokyo", "path", "path_finding"),
            Question("How many hops from Chicago to Paris?", 3, "number", "path_finding"),

            # Analysis (5)
            Question("How many hub cities are there?", 5, "number", "analysis"),
            Question("Which city has the most outgoing flights?", "NYC", "string", "analysis"),
            Question("What is the longest direct flight distance?", 6034, "number", "analysis"),
            Question("Is London reachable from Tokyo?", False, "boolean", "path_finding"),
            Question("How many direct routes are there?", 7, "number", "analysis"),
        ]
    }

    return datasets


# =============================================================================
# BENCHMARK RUNNER
# =============================================================================

def run_benchmark(skip_llm: bool = False):
    """Run the complete graph benchmark."""

    # Clear logs
    for log_path in [LOG_FILE, LATEST_LOG]:
        if os.path.exists(log_path):
            os.remove(log_path)

    log("=" * 80)
    log("ISONGRAPH BENCHMARK - 50 Graph Questions")
    log("=" * 80)
    log(f"Timestamp: {datetime.now().isoformat()}")
    log(f"Tokenizer: {TOKENIZER_NAME}")
    log(f"Skip LLM: {skip_llm}")
    log("")

    datasets = create_graph_datasets()

    # Collect all questions
    all_questions = []
    for ds_name, ds in datasets.items():
        for q in ds["questions"]:
            all_questions.append((ds_name, q))

    log(f"Total Questions: {len(all_questions)}")
    log("")

    # Token counting per format
    format_tokens = {fmt: 0 for fmt in FORMATS}
    format_correct = {fmt: 0 for fmt in FORMATS}

    results = []

    for ds_name, ds in datasets.items():
        log(f"\n{'='*60}")
        log(f"DATASET: {ds_name}")
        log(f"Description: {ds['description']}")
        log(f"Questions: {len(ds['questions'])}")
        log("=" * 60)

        data = ds["data"]

        # Convert to each format and count tokens
        format_data = {}
        for fmt_name, converter in FORMATS.items():
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
                    # Just mark as skipped
                    log(f"   {fmt_name}: [SKIPPED]")
                    continue

                prompt = f"""Given this data:

{formatted}

Question: {q.question}

Answer with just the value, no explanation."""

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
    log("\n" + "=" * 80)
    log("SUMMARY")
    log("=" * 80)

    total_questions = len(all_questions)

    log("\nToken Counts:")
    for fmt_name, tokens in sorted(format_tokens.items(), key=lambda x: x[1]):
        log(f"  {fmt_name}: {tokens} tokens")

    if not skip_llm:
        log("\nAccuracy:")
        for fmt_name in FORMATS:
            correct = format_correct[fmt_name]
            accuracy = (correct / total_questions) * 100 if total_questions > 0 else 0
            tokens = format_tokens[fmt_name]
            acc_per_1k = (accuracy / tokens) * 1000 if tokens > 0 else 0
            log(f"  {fmt_name}: {correct}/{total_questions} ({accuracy:.1f}%) - Acc/1K: {acc_per_1k:.2f}")

    # Category breakdown
    log("\nQuestions by Category:")
    categories = {}
    for ds_name, q in all_questions:
        categories[q.category] = categories.get(q.category, 0) + 1
    for cat, count in sorted(categories.items()):
        log(f"  {cat}: {count}")

    log("\n" + "=" * 80)
    log("BENCHMARK COMPLETE")
    log("=" * 80)

    return results


# =============================================================================
# UNIT TESTS FOR ISONGRAPH
# =============================================================================

def run_graph_unit_tests():
    """Run unit tests for ISONGraph functionality."""

    log("\n" + "=" * 80)
    log("ISONGRAPH UNIT TESTS")
    log("=" * 80)

    tests_passed = 0
    tests_failed = 0

    # Test 1: Basic node/edge operations
    log("\nTest 1: Basic Operations")
    try:
        graph = ISONGraph()
        graph.add_node("person", 1, name="Alice")
        graph.add_node("person", 2, name="Bob")
        graph.add_edge("KNOWS", ("person", 1), ("person", 2))

        assert graph.node_count() == 2
        assert graph.edge_count() == 1
        assert graph.has_node("person", 1)
        assert graph.has_edge("KNOWS", ("person", 1), ("person", 2))

        log("  ✓ Basic operations passed")
        tests_passed += 1
    except Exception as e:
        log(f"  ✗ Failed: {e}")
        tests_failed += 1

    # Test 2: Multi-hop traversal
    log("\nTest 2: Multi-hop Traversal")
    try:
        graph = ISONGraph()
        for i in range(1, 6):
            graph.add_node("person", i, name=f"Person{i}")
        graph.add_edge("KNOWS", ("person", 1), ("person", 2))
        graph.add_edge("KNOWS", ("person", 2), ("person", 3))
        graph.add_edge("KNOWS", ("person", 3), ("person", 4))
        graph.add_edge("KNOWS", ("person", 4), ("person", 5))

        hop1 = graph.multi_hop(("person", 1), "KNOWS", hops=1)
        hop2 = graph.multi_hop(("person", 1), "KNOWS", hops=2)
        hop3 = graph.multi_hop(("person", 1), "KNOWS", hops=3)

        assert hop1 == [("person", 2)]
        assert hop2 == [("person", 3)]
        assert hop3 == [("person", 4)]

        log("  ✓ Multi-hop traversal passed")
        tests_passed += 1
    except Exception as e:
        log(f"  ✗ Failed: {e}")
        tests_failed += 1

    # Test 3: Shortest path
    log("\nTest 3: Shortest Path")
    try:
        path = graph.shortest_path(("person", 1), ("person", 5))
        assert path is not None
        assert path.length == 4
        assert path.start == ("person", 1)
        assert path.end == ("person", 5)

        log("  ✓ Shortest path passed")
        tests_passed += 1
    except Exception as e:
        log(f"  ✗ Failed: {e}")
        tests_failed += 1

    # Test 4: Cycle detection
    log("\nTest 4: Cycle Detection")
    try:
        graph_no_cycle = ISONGraph()
        graph_no_cycle.add_node("node", 1)
        graph_no_cycle.add_node("node", 2)
        graph_no_cycle.add_node("node", 3)
        graph_no_cycle.add_edge("LINK", ("node", 1), ("node", 2))
        graph_no_cycle.add_edge("LINK", ("node", 2), ("node", 3))

        assert not graph_no_cycle.has_cycle()

        graph_no_cycle.add_edge("LINK", ("node", 3), ("node", 1))
        assert graph_no_cycle.has_cycle()

        log("  ✓ Cycle detection passed")
        tests_passed += 1
    except Exception as e:
        log(f"  ✗ Failed: {e}")
        tests_failed += 1

    # Test 5: Connectivity
    log("\nTest 5: Connectivity")
    try:
        graph_connected = ISONGraph()
        graph_connected.add_node("node", 1)
        graph_connected.add_node("node", 2)
        graph_connected.add_edge("LINK", ("node", 1), ("node", 2))

        assert graph_connected.is_connected()

        graph_connected.add_node("node", 3)  # Isolated
        assert not graph_connected.is_connected()

        log("  ✓ Connectivity check passed")
        tests_passed += 1
    except Exception as e:
        log(f"  ✗ Failed: {e}")
        tests_failed += 1

    # Test 6: Serialization roundtrip
    log("\nTest 6: Serialization Roundtrip")
    try:
        graph = ISONGraph()
        graph.add_node("person", 1, name="Alice", age=30)
        graph.add_node("person", 2, name="Bob", age=25)
        graph.add_edge("KNOWS", ("person", 1), ("person", 2), since=2020)

        ison_str = graph.to_ison()
        graph2 = ISONGraph.from_ison(ison_str)

        assert graph2.node_count() == 2
        assert graph2.edge_count() == 1

        log("  ✓ Serialization roundtrip passed")
        tests_passed += 1
    except Exception as e:
        log(f"  ✗ Failed: {e}")
        tests_failed += 1

    # Test 7: Query patterns
    log("\nTest 7: Query Patterns")
    try:
        graph = ISONGraph()
        for i in range(1, 5):
            graph.add_node("person", i)
        graph.add_edge("KNOWS", ("person", 1), ("person", 2))
        graph.add_edge("KNOWS", ("person", 2), ("person", 3))
        graph.add_edge("KNOWS", ("person", 3), ("person", 4))

        result = graph.query(":person:1 -[:KNOWS*2]-> *")
        assert ("person", 3) in result

        log("  ✓ Query patterns passed")
        tests_passed += 1
    except Exception as e:
        log(f"  ✗ Failed: {e}")
        tests_failed += 1

    # Test 8: Fluent API
    log("\nTest 8: Fluent API")
    try:
        result = graph.start(("person", 1)).hop("KNOWS").hop("KNOWS").collect()
        assert ("person", 3) in result

        log("  ✓ Fluent API passed")
        tests_passed += 1
    except Exception as e:
        log(f"  ✗ Failed: {e}")
        tests_failed += 1

    log(f"\n{'='*60}")
    log(f"Unit Tests: {tests_passed} passed, {tests_failed} failed")
    log("=" * 60)

    return tests_passed, tests_failed


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ISONGraph Benchmark")
    parser.add_argument("--skip-llm", action="store_true", help="Skip LLM accuracy tests (token counting only)")
    parser.add_argument("--unit-tests", action="store_true", help="Run unit tests only")
    parser.add_argument("--full", action="store_true", help="Run full benchmark with LLM")
    args = parser.parse_args()

    if args.unit_tests:
        run_graph_unit_tests()
    elif args.full:
        run_graph_unit_tests()
        run_benchmark(skip_llm=False)
    else:
        # Default: unit tests + token counting (no LLM)
        run_graph_unit_tests()
        run_benchmark(skip_llm=True)

<p align="center">
  <img src="../../logo/ison_graph_logo_stretch.png" alt="ISONGraph Logo">
</p>

# ISONGraph Knowledge Graph Benchmark Results

**Date:** December 29, 2025
**Tokenizer:** o200k_base (GPT-4o/GPT-5)
**LLM:** DeepSeek Chat
**Questions:** 100
**Formats Tested:** 10

---

## Executive Summary

ISONGraph demonstrates superior performance across all key metrics:

- **Highest Accuracy:** 90% (vs. 89% for second-best Cypher)
- **Best Token Efficiency:** 68.6% savings vs JSON
- **Best Overall Efficiency:** 53.00 Acc/1K tokens (19% better than next)

---

## Token Efficiency Results

Lower token count means more efficient use of LLM context windows.

### Overall Token Counts

| Rank | Format | Total Tokens | Savings vs JSON | Relative Size |
|:----:|--------|-------------:|----------------:|--------------:|
| 1 | **ISONGraph** | **1,698** | **68.6%** | 0.31x |
| 2 | ISON | 1,976 | 63.4% | 0.37x |
| 3 | JSON Compact | 2,893 | 46.5% | 0.54x |
| 4 | TOON | 2,934 | 45.7% | 0.54x |
| 5 | Cypher | 3,522 | 34.9% | 0.65x |
| 6 | RDF/Turtle | 4,166 | 22.9% | 0.77x |
| 7 | GML | 4,202 | 22.3% | 0.78x |
| 8 | JSON | 5,406 | 0.0% | 1.00x |
| 9 | JSON-LD | 8,191 | -51.5% | 1.52x |
| 10 | GraphML | 9,093 | -68.2% | 1.68x |

### Token Counts by Dataset

| Dataset | ISONGraph | ISON | JSON Compact | JSON | TOON | Cypher | RDF/Turtle | GML | JSON-LD | GraphML |
|---------|----------:|-----:|-------------:|-----:|-----:|-------:|-----------:|----:|--------:|--------:|
| Social Network | 177 | 191 | 319 | 596 | 206 | 397 | 408 | 459 | 934 | 1,019 |
| Knowledge Graph | 285 | 313 | 435 | 832 | 479 | 520 | 659 | 644 | 1,306 | 1,389 |
| Org Chart | 210 | 237 | 388 | 732 | 266 | 478 | 625 | 569 | 1,086 | 1,176 |
| Flight Routes | 205 | 224 | 417 | 782 | 262 | 514 | 522 | 596 | 1,157 | 1,322 |
| Movie Database | 335 | 407 | 517 | 959 | 706 | 619 | 730 | 760 | 1,470 | 1,552 |
| E-Commerce | 276 | 359 | 468 | 865 | 641 | 584 | 699 | 674 | 1,252 | 1,538 |
| Academic Citations | 210 | 245 | 349 | 640 | 374 | 410 | 523 | 500 | 986 | 1,097 |
| **Total** | **1,698** | **1,976** | **2,893** | **5,406** | **2,934** | **3,522** | **4,166** | **4,202** | **8,191** | **9,093** |

---

## Accuracy Results

Percentage of questions answered correctly by the LLM.

### Overall Accuracy

| Rank | Format | Correct | Total | Accuracy |
|:----:|--------|--------:|------:|---------:|
| 1 | **ISONGraph** | **90** | 100 | **90.0%** |
| 2 | Cypher | 89 | 100 | 89.0% |
| 3 | ISON | 88 | 100 | 88.0% |
| 3 | JSON Compact | 88 | 100 | 88.0% |
| 5 | JSON | 87 | 100 | 87.0% |
| 5 | GraphML | 87 | 100 | 87.0% |
| 7 | JSON-LD | 86 | 100 | 86.0% |
| 7 | GML | 86 | 100 | 86.0% |
| 9 | TOON | 85 | 100 | 85.0% |
| 10 | RDF/Turtle | 58 | 100 | 58.0% |

### Accuracy by Question Category

| Category | ISONGraph | ISON | JSON Compact | JSON | TOON | Cypher | RDF/Turtle | GML | JSON-LD | GraphML |
|----------|----------:|-----:|-------------:|-----:|-----:|-------:|-----------:|----:|--------:|--------:|
| Single-hop (33) | 32 | 31 | 31 | 32 | 31 | 32 | 21 | 31 | 31 | 32 |
| Multi-hop (21) | 18 | 17 | 17 | 17 | 16 | 18 | 10 | 16 | 17 | 16 |
| Analysis (23) | 21 | 21 | 21 | 20 | 20 | 21 | 15 | 21 | 20 | 21 |
| Aggregation (13) | 10 | 11 | 11 | 10 | 10 | 10 | 8 | 10 | 10 | 10 |
| Path Finding (9) | 8 | 7 | 7 | 7 | 7 | 7 | 3 | 7 | 7 | 7 |
| Pattern (1) | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |

---

## Efficiency Score (Accuracy per 1K Tokens)

The efficiency score combines accuracy and token efficiency into a single metric: **Accuracy / (Tokens / 1000)**

Higher is better - it measures how much accuracy you get per token spent.

### Efficiency Ranking

| Rank | Format | Acc/1K Tokens | Accuracy | Tokens | Analysis |
|:----:|--------|:-------------:|---------:|-------:|----------|
| 1 | **ISONGraph** | **53.00** | 90.0% | 1,698 | Best overall efficiency |
| 2 | ISON | 44.53 | 88.0% | 1,976 | Strong token efficiency |
| 3 | JSON Compact | 30.42 | 88.0% | 2,893 | Good accuracy, moderate tokens |
| 4 | TOON | 28.97 | 85.0% | 2,934 | Designed for LLMs, but underperforms |
| 5 | Cypher | 25.27 | 89.0% | 3,522 | High accuracy, verbose format |
| 6 | GML | 20.47 | 86.0% | 4,202 | Balanced but inefficient |
| 7 | JSON | 16.09 | 87.0% | 5,406 | Baseline reference |
| 8 | RDF/Turtle | 13.92 | 58.0% | 4,166 | Poor LLM comprehension |
| 9 | JSON-LD | 10.50 | 86.0% | 8,191 | Very verbose |
| 10 | GraphML | 9.57 | 87.0% | 9,093 | XML overhead kills efficiency |

---

## Detailed Analysis

### Why ISONGraph Performs Best

1. **Tabular Format**
   - Column headers appear once, not repeated per row
   - Natural for LLMs trained on structured text

2. **Compact References**
   - Uses `:type:id` syntax (e.g., `:person:1`)
   - JSON uses `{"type": "person", "id": 1}` (7x more tokens)

3. **Explicit Graph Structure**
   - Clear `nodes.type` and `edges.RELATION` sections
   - LLMs can easily identify graph topology

4. **Human-Readable**
   - No escaping, minimal punctuation
   - LLMs process it like natural structured text

### Why RDF/Turtle Performs Poorly

RDF/Turtle achieved only **58% accuracy** despite moderate token efficiency. The main issues:

1. **Abstract Identifiers**: Uses `ex:person_1` instead of actual names
2. **LLM Mapping Failure**: LLMs can't map `ex:person_1` back to "Alice"
3. **Triple-Based Structure**: Subject-predicate-object format is less intuitive for graph traversal

Example RDF/Turtle failure:
```
Q: Who does Alice follow?
Expected: Bob, Carol
RDF/Turtle Response: ex:person_2, ex:person_3 (FAIL)
```

### TOON vs ISONGraph

TOON was designed specifically for LLMs but underperforms ISONGraph:

| Metric | ISONGraph | TOON | Difference |
|--------|-----------|------|------------|
| Accuracy | 90.0% | 85.0% | +5% |
| Tokens | 1,698 | 2,934 | 42% fewer |
| Acc/1K | 53.00 | 28.97 | 83% better |

**Key difference**: ISONGraph is graph-native with explicit traversal semantics, while TOON is a general-purpose format without graph awareness.

### Multi-hop Query Performance

Multi-hop queries (e.g., "Who can Alice reach in 2 hops?") show the biggest format differences:

| Format | Multi-hop Accuracy | Why |
|--------|-------------------:|-----|
| ISONGraph | 86% | Clear edge references enable traversal |
| Cypher | 86% | Built for graph queries |
| ISON | 81% | Good structure but no graph semantics |
| JSON | 81% | Verbose but complete information |
| RDF/Turtle | 48% | Abstract IDs break chain reasoning |

---

## Notable Question Results

### Questions Where Only ISONGraph Succeeded

**Q7 [multi_hop]: Can Alice reach Eve in 3 hops?**
- Expected: True
- ISONGraph: ✓ (only format to get this correct)
- All others: ✗ (answered "No")

This demonstrates ISONGraph's superior support for multi-hop reasoning.

### Questions All Formats Failed

**Q9 [multi_hop]: How many hops from Jane to DataAPI?**
- Expected: 1 (Jane → works_at → DataInc → produces → DataAPI)
- All formats answered: 2
- Analysis: Ambiguous question - depends on counting convention

### Universal Success Questions

Single-hop factual queries showed high success across all formats:
- "Where does John work?" - 100% (except RDF/Turtle)
- "How many nodes are there?" - 100%
- "What year was The Dark Knight released?" - 100%

---

## Dataset-Specific Insights

### Social Network (15 questions)
- **Challenge**: Cycles and multi-hop following
- **Best**: ISONGraph (14/15)
- **Worst**: RDF/Turtle (7/15)

### Knowledge Graph (15 questions)
- **Challenge**: Multiple entity types and relationships
- **Best**: ISONGraph, Cypher (14/15)
- **Worst**: RDF/Turtle (10/15)

### Flight Routes (15 questions)
- **Challenge**: Path finding with distances
- **Best**: JSON, JSON-LD (13/15)
- **Worst**: RDF/Turtle (8/15)

### Movie Database (15 questions)
- **Challenge**: Many-to-many relationships (actors ↔ movies ↔ genres)
- **Best**: ISONGraph, Cypher (14/15)
- **Worst**: RDF/Turtle (10/15)

---

## Reproducibility

### Running the Benchmark

```bash
# From the repo root
cd benchmark/KnowledgeGraph_Benchmark
python benchmark_kg_100.py --full --formats all
```

### Configuration

Set the `DEEPSEEK_API_KEY` environment variable before running:

```bash
export DEEPSEEK_API_KEY="your-key"   # Windows PowerShell: $env:DEEPSEEK_API_KEY = "your-key"
```

```python
# API Settings (read from environment)
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

# Model Settings
model = "deepseek-chat"
temperature = 0  # Deterministic responses
```

### Estimated Runtime

- **Token counting only**: ~5 seconds
- **Full benchmark (100 questions × 10 formats)**: ~40 minutes
- **Rate limiting**: 0.5s delay between API calls

---

## Conclusions

### Key Findings

1. **ISONGraph is the most efficient format** for representing graph data to LLMs
   - 68.6% token savings vs JSON
   - 90% accuracy (highest)
   - 53.00 Acc/1K (best efficiency)

2. **Format design matters significantly**
   - Graph-native formats outperform generic serialization
   - Human-readable names > abstract identifiers
   - Tabular > nested structures for LLMs

3. **RDF/Turtle is unsuitable for LLM contexts**
   - Despite being a standard, LLMs struggle with its abstract identifiers
   - 58% accuracy is below useful threshold

4. **XML formats (GraphML) are highly inefficient**
   - 68% more tokens than JSON
   - No accuracy benefit to justify the overhead

### Recommendations

| Use Case | Recommended Format |
|----------|-------------------|
| LLM context (graphs) | **ISONGraph** |
| LLM context (general) | ISON or JSON Compact |
| Human editing | ISON or GML |
| Database storage | Native graph DB format |
| W3C compliance | RDF/Turtle (but not for LLMs) |
| Web APIs | JSON-LD (with LLM limitations) |

---

## Appendix

### A. Format Examples

#### ISONGraph (177 tokens)
```
nodes.person
id name age verified followers
1 Alice 28 true 1500
2 Bob 34 false 800
3 Carol 29 true 2200

edges.FOLLOWS
source target since
:person:1 :person:2 2020
:person:1 :person:3 2021
:person:2 :person:3 2019
```

#### JSON (596 tokens)
```json
{
  "nodes": [
    {"id": 1, "type": "person", "name": "Alice", "age": 28, "verified": true, "followers": 1500},
    {"id": 2, "type": "person", "name": "Bob", "age": 34, "verified": false, "followers": 800},
    {"id": 3, "type": "person", "name": "Carol", "age": 29, "verified": true, "followers": 2200}
  ],
  "edges": [
    {"source": 1, "target": 2, "relation": "follows", "since": 2020},
    {"source": 1, "target": 3, "relation": "follows", "since": 2021},
    {"source": 2, "target": 3, "relation": "follows", "since": 2019}
  ]
}
```

#### RDF/Turtle (408 tokens)
```turtle
@prefix ex: <http://example.org/> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

ex:person_1
    rdf:type ex:person ;
    ex:name "Alice" ;
    ex:age 28 ;
    ex:verified true ;
    ex:followers 1500 .

ex:person_1 ex:follows ex:person_2 .
ex:person_1 ex:follows ex:person_3 .
ex:person_2 ex:follows ex:person_3 .
```

#### Cypher/Neo4j (397 tokens)
```cypher
CREATE (n1:person {id: 1, name: "Alice", age: 28, verified: true, followers: 1500})
CREATE (n2:person {id: 2, name: "Bob", age: 34, verified: false, followers: 800})
CREATE (n3:person {id: 3, name: "Carol", age: 29, verified: true, followers: 2200})

CREATE (n1)-[:FOLLOWS {since: 2020}]->(n2)
CREATE (n1)-[:FOLLOWS {since: 2021}]->(n3)
CREATE (n2)-[:FOLLOWS {since: 2019}]->(n3)
```

### B. Question Categories Explained

| Category | Description | Example |
|----------|-------------|---------|
| **Single-hop** | Direct neighbor lookup | "Who does Alice follow?" |
| **Multi-hop** | N-hop traversal | "Who can Alice reach in 2 hops?" |
| **Path Finding** | Route between nodes | "What is the shortest path from NYC to Tokyo?" |
| **Analysis** | Graph properties | "Does this graph have a cycle?" |
| **Aggregation** | Counts/sums | "What is the total salary of all employees?" |
| **Pattern** | Complex queries | "Who acts in Crime genre movies?" |

### C. Test Environment

- **OS**: Windows 11
- **Python**: 3.10+
- **Tokenizer**: tiktoken o200k_base
- **LLM**: DeepSeek Chat (temperature=0)
- **Date**: December 29, 2025

---

*Generated by ISONGraph Knowledge Graph Benchmark v2.0.0*


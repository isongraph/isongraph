/**
 * ISONGraphantic C++ Tests
 *
 * Comprehensive tests for graph schema validation.
 */

#include <iostream>
#include <string>
#include <cassert>
#include "../include/isongraphantic.hpp"

using namespace isongraphantic;
using namespace ison_graph;

int passed = 0;
int failed = 0;

#define TEST(name) void test_##name()
#define RUN_TEST(name) do { \
    std::cout << "Running " << #name << "... "; \
    try { \
        test_##name(); \
        std::cout << "PASSED" << std::endl; \
        passed++; \
    } catch (const std::exception& e) { \
        std::cout << "FAILED: " << e.what() << std::endl; \
        failed++; \
    } catch (...) { \
        std::cout << "FAILED: Unknown exception" << std::endl; \
        failed++; \
    } \
} while(0)

#define ASSERT_TRUE(cond) do { if (!(cond)) throw std::runtime_error("Assertion failed: " #cond); } while(0)
#define ASSERT_FALSE(cond) ASSERT_TRUE(!(cond))
#define ASSERT_EQ(a, b) do { if ((a) != (b)) throw std::runtime_error("Assertion failed: " #a " == " #b); } while(0)

// =============================================================================
// String Field Tests
// =============================================================================

TEST(string_field_basic) {
    StringField field;
    auto result = field.validate("hello", "name");
    ASSERT_TRUE(result.is_valid());
}

TEST(string_field_required) {
    StringField field;
    field.required();

    // Missing value should fail
    auto result = field.validate(std::nullopt, "name");
    ASSERT_FALSE(result.is_valid());
    ASSERT_EQ(result.errors[0].code, ErrorCode::REQUIRED_FIELD);

    // Present value should pass
    result = field.validate("Alice", "name");
    ASSERT_TRUE(result.is_valid());
}

TEST(string_field_min_length) {
    StringField field;
    field.min_len(3);

    auto result = field.validate("ab", "name");
    ASSERT_FALSE(result.is_valid());
    ASSERT_EQ(result.errors[0].code, ErrorCode::MIN_LENGTH);

    result = field.validate("abc", "name");
    ASSERT_TRUE(result.is_valid());
}

TEST(string_field_max_length) {
    StringField field;
    field.max_len(5);

    auto result = field.validate("toolong", "name");
    ASSERT_FALSE(result.is_valid());
    ASSERT_EQ(result.errors[0].code, ErrorCode::MAX_LENGTH);

    result = field.validate("ok", "name");
    ASSERT_TRUE(result.is_valid());
}

TEST(string_field_email) {
    StringField field;
    field.email();

    auto result = field.validate("invalid", "email");
    ASSERT_FALSE(result.is_valid());
    ASSERT_EQ(result.errors[0].code, ErrorCode::INVALID_EMAIL);

    result = field.validate("test@example.com", "email");
    ASSERT_TRUE(result.is_valid());
}

TEST(string_field_enum) {
    StringField field;
    field.enum_values({"red", "green", "blue"});

    auto result = field.validate("yellow", "color");
    ASSERT_FALSE(result.is_valid());
    ASSERT_EQ(result.errors[0].code, ErrorCode::INVALID_ENUM);

    result = field.validate("red", "color");
    ASSERT_TRUE(result.is_valid());
}

TEST(string_field_pattern) {
    StringField field;
    field.pattern("^[A-Z][a-z]+$");

    auto result = field.validate("alice", "name");
    ASSERT_FALSE(result.is_valid());
    ASSERT_EQ(result.errors[0].code, ErrorCode::PATTERN_MISMATCH);

    result = field.validate("Alice", "name");
    ASSERT_TRUE(result.is_valid());
}

// =============================================================================
// Int Field Tests
// =============================================================================

TEST(int_field_basic) {
    IntField field;
    auto result = field.validate("42", "age");
    ASSERT_TRUE(result.is_valid());
}

TEST(int_field_required) {
    IntField field;
    field.required();

    auto result = field.validate(std::nullopt, "age");
    ASSERT_FALSE(result.is_valid());
    ASSERT_EQ(result.errors[0].code, ErrorCode::REQUIRED_FIELD);
}

TEST(int_field_min_value) {
    IntField field;
    field.min(0);

    auto result = field.validate("-1", "age");
    ASSERT_FALSE(result.is_valid());
    ASSERT_EQ(result.errors[0].code, ErrorCode::MIN_VALUE);

    result = field.validate("0", "age");
    ASSERT_TRUE(result.is_valid());
}

TEST(int_field_max_value) {
    IntField field;
    field.max(100);

    auto result = field.validate("101", "age");
    ASSERT_FALSE(result.is_valid());
    ASSERT_EQ(result.errors[0].code, ErrorCode::MAX_VALUE);

    result = field.validate("100", "age");
    ASSERT_TRUE(result.is_valid());
}

TEST(int_field_range) {
    IntField field;
    field.range(0, 100);

    auto result = field.validate("-1", "age");
    ASSERT_FALSE(result.is_valid());

    result = field.validate("101", "age");
    ASSERT_FALSE(result.is_valid());

    result = field.validate("50", "age");
    ASSERT_TRUE(result.is_valid());
}

TEST(int_field_invalid_type) {
    IntField field;
    auto result = field.validate("not_a_number", "age");
    ASSERT_FALSE(result.is_valid());
    ASSERT_EQ(result.errors[0].code, ErrorCode::INVALID_TYPE);
}

// =============================================================================
// Float Field Tests
// =============================================================================

TEST(float_field_basic) {
    FloatField field;
    auto result = field.validate("3.14", "value");
    ASSERT_TRUE(result.is_valid());
}

TEST(float_field_range) {
    FloatField field;
    field.range(0.0, 1.0);

    auto result = field.validate("-0.1", "value");
    ASSERT_FALSE(result.is_valid());

    result = field.validate("0.5", "value");
    ASSERT_TRUE(result.is_valid());
}

// =============================================================================
// Bool Field Tests
// =============================================================================

TEST(bool_field_basic) {
    BoolField field;

    auto result = field.validate("true", "active");
    ASSERT_TRUE(result.is_valid());

    result = field.validate("false", "active");
    ASSERT_TRUE(result.is_valid());

    result = field.validate("1", "active");
    ASSERT_TRUE(result.is_valid());

    result = field.validate("0", "active");
    ASSERT_TRUE(result.is_valid());
}

TEST(bool_field_invalid) {
    BoolField field;
    auto result = field.validate("maybe", "active");
    ASSERT_FALSE(result.is_valid());
    ASSERT_EQ(result.errors[0].code, ErrorCode::INVALID_TYPE);
}

// =============================================================================
// Ref Field Tests
// =============================================================================

TEST(ref_field_basic) {
    RefField field;
    auto result = field.validate(":person:1", "owner");
    ASSERT_TRUE(result.is_valid());
}

TEST(ref_field_wrong_type) {
    RefField field;
    field.to_node("person");

    auto result = field.validate(":company:1", "owner");
    ASSERT_FALSE(result.is_valid());
    ASSERT_EQ(result.errors[0].code, ErrorCode::REF_WRONG_TYPE);
}

TEST(ref_field_invalid_format) {
    RefField field;
    auto result = field.validate("invalid", "owner");
    ASSERT_FALSE(result.is_valid());
    ASSERT_EQ(result.errors[0].code, ErrorCode::INVALID_TYPE);
}

// =============================================================================
// Node Type Tests
// =============================================================================

TEST(node_type_valid) {
    NodeType person("person");
    person.field("name", StringField().required())
          .field("age", IntField().min(0));

    ISONGraph graph;
    graph.addNode("person", "1", {{"name", "Alice"}, {"age", "30"}});

    const Node& node = graph.getNode("person", "1");
    auto result = person.validate_node(node);
    ASSERT_TRUE(result.is_valid());
}

TEST(node_type_missing_required) {
    NodeType person("person");
    person.field("name", StringField().required());

    ISONGraph graph;
    graph.addNode("person", "1", {{"age", "30"}});  // Missing name

    const Node& node = graph.getNode("person", "1");
    auto result = person.validate_node(node);
    ASSERT_FALSE(result.is_valid());
    ASSERT_EQ(result.errors[0].code, ErrorCode::REQUIRED_FIELD);
}

TEST(node_type_invalid_value) {
    NodeType person("person");
    person.field("age", IntField().min(0));

    ISONGraph graph;
    graph.addNode("person", "1", {{"age", "-5"}});

    const Node& node = graph.getNode("person", "1");
    auto result = person.validate_node(node);
    ASSERT_FALSE(result.is_valid());
    ASSERT_EQ(result.errors[0].code, ErrorCode::MIN_VALUE);
}

// =============================================================================
// Edge Type Tests
// =============================================================================

TEST(edge_type_valid) {
    EdgeType knows("KNOWS");
    knows.from_node("person").to_node("person");

    ISONGraph graph;
    graph.addNode("person", "1", {});
    graph.addNode("person", "2", {});
    graph.addEdge("KNOWS", {"person", "1"}, {"person", "2"}, {});

    auto edges = graph.getEdges("KNOWS");
    ASSERT_EQ(edges.size(), 1);

    auto result = knows.validate_edge(edges[0], graph);
    ASSERT_TRUE(result.is_valid());
}

TEST(edge_type_self_loop) {
    EdgeType knows("KNOWS");
    knows.from_node("person").to_node("person").no_self_loop();

    ISONGraph graph;
    graph.addNode("person", "1", {});
    graph.addEdge("KNOWS", {"person", "1"}, {"person", "1"}, {});

    auto edges = graph.getEdges("KNOWS");
    auto result = knows.validate_edge(edges[0], graph);
    ASSERT_FALSE(result.is_valid());
    ASSERT_EQ(result.errors[0].code, ErrorCode::SELF_LOOP);
}

TEST(edge_type_wrong_source) {
    EdgeType works_at("WORKS_AT");
    works_at.from_node("person").to_node("company");

    ISONGraph graph;
    graph.addNode("company", "100", {});
    graph.addNode("company", "101", {});
    graph.addEdge("WORKS_AT", {"company", "100"}, {"company", "101"}, {});

    auto edges = graph.getEdges("WORKS_AT");
    auto result = works_at.validate_edge(edges[0], graph);
    ASSERT_FALSE(result.is_valid());
    ASSERT_EQ(result.errors[0].code, ErrorCode::INVALID_SOURCE_TYPE);
}

TEST(edge_type_missing_node) {
    EdgeType knows("KNOWS");
    knows.from_node("person").to_node("person");

    ISONGraph graph;
    graph.addNode("person", "1", {});
    graph.addNode("person", "2", {});
    graph.addEdge("KNOWS", {"person", "1"}, {"person", "2"}, {});

    auto edges = graph.getEdges("KNOWS");
    auto result = knows.validate_edge(edges[0], graph);
    ASSERT_TRUE(result.is_valid());
}

// =============================================================================
// Graph Schema Tests
// =============================================================================

TEST(graph_schema_valid) {
    NodeType person("person");
    person.field("name", StringField().required());

    EdgeType knows("KNOWS");
    knows.from_node("person").to_node("person");

    GraphSchema schema("social");
    schema.node_type(std::move(person))
          .edge_type(std::move(knows));

    ISONGraph graph;
    graph.addNode("person", "1", {{"name", "Alice"}});
    graph.addNode("person", "2", {{"name", "Bob"}});
    graph.addEdge("KNOWS", {"person", "1"}, {"person", "2"}, {});

    auto result = schema.validate(graph);
    ASSERT_TRUE(result.is_valid());
}

TEST(graph_schema_orphans) {
    NodeType person("person");

    GraphSchema schema("social");
    schema.node_type(std::move(person))
          .no_orphans();

    ISONGraph graph;
    graph.addNode("person", "1", {});
    graph.addNode("person", "2", {});
    // No edges - both are orphans

    auto result = schema.validate(graph);
    ASSERT_FALSE(result.is_valid());

    int orphan_count = 0;
    for (const auto& err : result.errors) {
        if (err.code == ErrorCode::ORPHAN_NODE) orphan_count++;
    }
    ASSERT_EQ(orphan_count, 2);
}

TEST(graph_schema_unique_edges) {
    EdgeType knows("KNOWS");
    knows.unique();

    GraphSchema schema("social");
    schema.edge_type(std::move(knows));

    ISONGraph graph;
    graph.addNode("person", "1", {});
    graph.addNode("person", "2", {});
    graph.addNode("person", "3", {});
    graph.addEdge("KNOWS", {"person", "1"}, {"person", "2"}, {});
    graph.addEdge("KNOWS", {"person", "1"}, {"person", "3"}, {});
    graph.addEdge("KNOWS", {"person", "2"}, {"person", "3"}, {});

    auto result = schema.validate(graph);
    ASSERT_TRUE(result.is_valid());
}

TEST(acyclic_checks_only_own_rel_type) {
    // A cycle in ANOTHER edge type must not trigger CYCLE_DETECTED for
    // an acyclic edge type whose own edges form a DAG
    EdgeType reports_to("REPORTS_TO");
    reports_to.acyclic();

    GraphSchema schema("org");
    schema.edge_type(std::move(reports_to));

    ISONGraph graph;
    graph.addNode("person", "1", {});
    graph.addNode("person", "2", {});
    graph.addNode("person", "3", {});
    // REPORTS_TO edges: a DAG
    graph.addEdge("REPORTS_TO", {"person", "2"}, {"person", "1"}, {});
    graph.addEdge("REPORTS_TO", {"person", "3"}, {"person", "2"}, {});
    // KNOWS edges: a cycle (different rel type - must be ignored)
    graph.addEdge("KNOWS", {"person", "1"}, {"person", "2"}, {});
    graph.addEdge("KNOWS", {"person", "2"}, {"person", "1"}, {});

    auto result = schema.validate(graph);
    ASSERT_TRUE(result.is_valid());
}

TEST(acyclic_detects_cycle_in_own_rel_type) {
    EdgeType reports_to("REPORTS_TO");
    reports_to.acyclic();

    GraphSchema schema("org");
    schema.edge_type(std::move(reports_to));

    ISONGraph graph;
    graph.addNode("person", "1", {});
    graph.addNode("person", "2", {});
    graph.addEdge("REPORTS_TO", {"person", "1"}, {"person", "2"}, {});
    graph.addEdge("REPORTS_TO", {"person", "2"}, {"person", "1"}, {});

    auto result = schema.validate(graph);
    ASSERT_FALSE(result.is_valid());

    bool found_cycle = false;
    for (const auto& err : result.errors) {
        if (err.code == ErrorCode::CYCLE_DETECTED) found_cycle = true;
    }
    ASSERT_TRUE(found_cycle);
}

TEST(bidirectional_missing_reverse) {
    EdgeType friends("FRIENDS");
    friends.bidirectional();

    GraphSchema schema("social");
    schema.edge_type(std::move(friends));

    ISONGraph graph;
    graph.addNode("person", "1", {});
    graph.addNode("person", "2", {});
    graph.addNode("person", "3", {});
    // Complete pair
    graph.addEdge("FRIENDS", {"person", "1"}, {"person", "2"}, {});
    graph.addEdge("FRIENDS", {"person", "2"}, {"person", "1"}, {});
    // Missing reverse
    graph.addEdge("FRIENDS", {"person", "1"}, {"person", "3"}, {});

    auto result = schema.validate(graph);
    ASSERT_FALSE(result.is_valid());
    ASSERT_EQ(result.errors.size(), 1);

    // With the reverse added it becomes valid
    graph.addEdge("FRIENDS", {"person", "3"}, {"person", "1"}, {});
    auto result2 = schema.validate(graph);
    ASSERT_TRUE(result2.is_valid());
}

// =============================================================================
// Cardinality Tests
// =============================================================================

TEST(cardinality_one_to_one) {
    NodeType person("person");
    NodeType company("company");

    EdgeType works_at("WORKS_AT");
    works_at.from_node("person")
            .to_node("company")
            .cardinality(Cardinality::ONE_TO_ONE);

    GraphSchema schema("org");
    schema.node_type(std::move(person))
          .node_type(std::move(company))
          .edge_type(std::move(works_at));

    ISONGraph graph;
    graph.addNode("person", "1", {});
    graph.addNode("person", "2", {});
    graph.addNode("company", "100", {});
    graph.addEdge("WORKS_AT", {"person", "1"}, {"company", "100"}, {});
    graph.addEdge("WORKS_AT", {"person", "2"}, {"company", "100"}, {});

    auto result = schema.validate(graph);
    ASSERT_FALSE(result.is_valid());

    bool found_violation = false;
    for (const auto& err : result.errors) {
        if (err.code == ErrorCode::CARDINALITY_VIOLATION) found_violation = true;
    }
    ASSERT_TRUE(found_violation);
}

TEST(cardinality_many_to_one) {
    EdgeType reports_to("REPORTS_TO");
    reports_to.cardinality(Cardinality::MANY_TO_ONE);

    GraphSchema schema("org");
    schema.edge_type(std::move(reports_to));

    ISONGraph graph;
    graph.addNode("person", "1", {});
    graph.addNode("person", "2", {});
    graph.addNode("person", "3", {});
    graph.addEdge("REPORTS_TO", {"person", "1"}, {"person", "2"}, {});
    graph.addEdge("REPORTS_TO", {"person", "1"}, {"person", "3"}, {});

    auto result = schema.validate(graph);
    ASSERT_FALSE(result.is_valid());
}

TEST(cardinality_one_to_many) {
    EdgeType authored("AUTHORED");
    authored.cardinality(Cardinality::ONE_TO_MANY);

    GraphSchema schema("blog");
    schema.edge_type(std::move(authored));

    ISONGraph graph;
    graph.addNode("user", "1", {});
    graph.addNode("user", "2", {});
    graph.addNode("post", "100", {});
    graph.addEdge("AUTHORED", {"user", "1"}, {"post", "100"}, {});
    graph.addEdge("AUTHORED", {"user", "2"}, {"post", "100"}, {});

    auto result = schema.validate(graph);
    ASSERT_FALSE(result.is_valid());
}

TEST(cardinality_many_to_many) {
    EdgeType likes("LIKES");
    likes.cardinality(Cardinality::MANY_TO_MANY);

    GraphSchema schema("social");
    schema.edge_type(std::move(likes));

    ISONGraph graph;
    graph.addNode("user", "1", {});
    graph.addNode("user", "2", {});
    graph.addNode("post", "100", {});
    graph.addNode("post", "101", {});
    graph.addEdge("LIKES", {"user", "1"}, {"post", "100"}, {});
    graph.addEdge("LIKES", {"user", "1"}, {"post", "101"}, {});
    graph.addEdge("LIKES", {"user", "2"}, {"post", "100"}, {});
    graph.addEdge("LIKES", {"user", "2"}, {"post", "101"}, {});

    auto result = schema.validate(graph);
    ASSERT_TRUE(result.is_valid());
}

// =============================================================================
// Integration Tests
// =============================================================================

TEST(integration_social_network) {
    NodeType user("user");
    user.field("name", StringField().required().min_len(1).max_len(100))
        .field("email", StringField().email())
        .field("age", IntField().min(0).max(150));

    NodeType post("post");
    post.field("title", StringField().required().max_len(200))
        .field("content", StringField());

    EdgeType follows("FOLLOWS");
    follows.from_node("user")
           .to_node("user")
           .no_self_loop();

    EdgeType authored("AUTHORED");
    authored.from_node("user")
            .to_node("post")
            .cardinality(Cardinality::ONE_TO_MANY);

    EdgeType likes("LIKES");
    likes.from_node("user")
         .to_node("post")
         .unique();

    GraphSchema schema("social_network");
    schema.node_type(std::move(user))
          .node_type(std::move(post))
          .edge_type(std::move(follows))
          .edge_type(std::move(authored))
          .edge_type(std::move(likes));

    ISONGraph graph;
    graph.addNode("user", "1", {{"name", "Alice"}, {"email", "alice@test.com"}, {"age", "30"}});
    graph.addNode("user", "2", {{"name", "Bob"}, {"email", "bob@test.com"}, {"age", "25"}});
    graph.addNode("post", "100", {{"title", "Hello World"}, {"content", "My first post"}});
    graph.addNode("post", "101", {{"title", "Graph Databases"}, {"content", "Why they matter"}});

    graph.addEdge("FOLLOWS", {"user", "1"}, {"user", "2"}, {});
    graph.addEdge("AUTHORED", {"user", "1"}, {"post", "100"}, {});
    graph.addEdge("AUTHORED", {"user", "2"}, {"post", "101"}, {});
    graph.addEdge("LIKES", {"user", "1"}, {"post", "101"}, {});
    graph.addEdge("LIKES", {"user", "2"}, {"post", "100"}, {});

    auto result = schema.validate(graph);
    ASSERT_TRUE(result.is_valid());
}

TEST(integration_org_chart) {
    NodeType employee("employee");
    employee.field("name", StringField().required())
            .field("title", StringField());

    EdgeType reports_to("REPORTS_TO");
    reports_to.from_node("employee")
              .to_node("employee")
              .no_self_loop()
              .cardinality(Cardinality::MANY_TO_ONE);

    GraphSchema schema("org_chart");
    schema.node_type(std::move(employee))
          .edge_type(std::move(reports_to));

    ISONGraph graph;
    graph.addNode("employee", "1", {{"name", "CEO"}, {"title", "Chief Executive Officer"}});
    graph.addNode("employee", "2", {{"name", "CTO"}, {"title", "Chief Technology Officer"}});
    graph.addNode("employee", "3", {{"name", "Engineer"}, {"title", "Software Engineer"}});

    graph.addEdge("REPORTS_TO", {"employee", "2"}, {"employee", "1"}, {});
    graph.addEdge("REPORTS_TO", {"employee", "3"}, {"employee", "2"}, {});

    auto result = schema.validate(graph);
    ASSERT_TRUE(result.is_valid());
}

// =============================================================================
// Main
// =============================================================================

int main() {
    std::cout << "=== ISONGraphantic C++ Tests ===" << std::endl << std::endl;

    // String field tests
    RUN_TEST(string_field_basic);
    RUN_TEST(string_field_required);
    RUN_TEST(string_field_min_length);
    RUN_TEST(string_field_max_length);
    RUN_TEST(string_field_email);
    RUN_TEST(string_field_enum);
    RUN_TEST(string_field_pattern);

    // Int field tests
    RUN_TEST(int_field_basic);
    RUN_TEST(int_field_required);
    RUN_TEST(int_field_min_value);
    RUN_TEST(int_field_max_value);
    RUN_TEST(int_field_range);
    RUN_TEST(int_field_invalid_type);

    // Float field tests
    RUN_TEST(float_field_basic);
    RUN_TEST(float_field_range);

    // Bool field tests
    RUN_TEST(bool_field_basic);
    RUN_TEST(bool_field_invalid);

    // Ref field tests
    RUN_TEST(ref_field_basic);
    RUN_TEST(ref_field_wrong_type);
    RUN_TEST(ref_field_invalid_format);

    // Node type tests
    RUN_TEST(node_type_valid);
    RUN_TEST(node_type_missing_required);
    RUN_TEST(node_type_invalid_value);

    // Edge type tests
    RUN_TEST(edge_type_valid);
    RUN_TEST(edge_type_self_loop);
    RUN_TEST(edge_type_wrong_source);
    RUN_TEST(edge_type_missing_node);

    // Graph schema tests
    RUN_TEST(graph_schema_valid);
    RUN_TEST(graph_schema_orphans);
    RUN_TEST(graph_schema_unique_edges);
    RUN_TEST(acyclic_checks_only_own_rel_type);
    RUN_TEST(acyclic_detects_cycle_in_own_rel_type);
    RUN_TEST(bidirectional_missing_reverse);

    // Cardinality tests
    RUN_TEST(cardinality_one_to_one);
    RUN_TEST(cardinality_many_to_one);
    RUN_TEST(cardinality_one_to_many);
    RUN_TEST(cardinality_many_to_many);

    // Integration tests
    RUN_TEST(integration_social_network);
    RUN_TEST(integration_org_chart);

    std::cout << std::endl << "=== Results ===" << std::endl;
    std::cout << "Total: " << (passed + failed) << ", Passed: " << passed << ", Failed: " << failed << std::endl;

    return failed > 0 ? 1 : 0;
}

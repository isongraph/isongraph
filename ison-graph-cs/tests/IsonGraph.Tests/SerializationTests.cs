// Tests for ISON/ISONL serialization: round-trips (including values with
// spaces, pipes, newlines, quotes, and empty strings) and malformed-input
// errors (never a silent skip).

using Xunit;

namespace IsonGraph.Tests;

public class ToIsonTests
{
    [Fact]
    public void ToIsonContainsBlocksAndRefs()
    {
        var graph = new ISONGraph();
        graph.AddNode("person", "1", Props.Of(("name", "Alice")));
        graph.AddNode("person", "2", Props.Of(("name", "Bob")));
        graph.AddEdge("KNOWS", new("person", "1"), new("person", "2"),
                      Props.Of(("since", "2020")));

        var ison = graph.ToIson();

        Assert.Contains("nodes.person", ison);
        Assert.Contains("edges.KNOWS", ison);
        Assert.Contains(":person:1", ison);
        Assert.Contains(":person:2", ison);
    }

    [Fact]
    public void ToIsonSortsTypesAndPropKeys()
    {
        var graph = new ISONGraph();
        graph.AddNode("zebra", "1", Props.Of(("b", "2"), ("a", "1")));
        graph.AddNode("apple", "1");

        var ison = graph.ToIson();
        var appleIdx = ison.IndexOf("nodes.apple", StringComparison.Ordinal);
        var zebraIdx = ison.IndexOf("nodes.zebra", StringComparison.Ordinal);
        Assert.True(appleIdx >= 0 && zebraIdx > appleIdx);
        Assert.Contains("id a b", ison);
    }

    [Fact]
    public void ToIsonFillsMissingPropsWithNull()
    {
        var graph = new ISONGraph();
        graph.AddNode("person", "1", Props.Of(("name", "Alice"), ("age", "30")));
        graph.AddNode("person", "2", Props.Of(("name", "Bob")));

        var ison = graph.ToIson();
        Assert.Contains("2 null Bob", ison); // sorted keys: age name
    }

    [Fact]
    public void ToIsonl()
    {
        var graph = new ISONGraph();
        graph.AddNode("person", "1", Props.Of(("name", "Alice")));
        graph.AddEdge("KNOWS", new("person", "1"), new("person", "1"));

        var isonl = graph.ToIsonl();

        Assert.Contains("nodes.person|", isonl);
        Assert.Contains("edges.KNOWS|", isonl);
        Assert.Contains("nodes.person|id name|1 Alice", isonl);
    }

    [Fact]
    public void QuotingRules()
    {
        Assert.Equal("plain", ISONGraph.QuoteValue("plain"));
        Assert.Equal("\"\"", ISONGraph.QuoteValue(""));
        Assert.Equal("\"a b\"", ISONGraph.QuoteValue("a b"));
        Assert.Equal("\"a|b\"", ISONGraph.QuoteValue("a|b"));
        Assert.Equal("\"a\\\"b\"", ISONGraph.QuoteValue("a\"b"));
        Assert.Equal("\"a\\nb\"", ISONGraph.QuoteValue("a\nb"));
        Assert.Equal("\"a\\\\ b\"", ISONGraph.QuoteValue("a\\ b"));
    }
}

public class FromIsonTests
{
    private const string SampleIson = """
nodes.person
id name
1 Alice
2 Bob

edges.KNOWS
source target since
:person:1 :person:2 2020
""";

    [Fact]
    public void ParsesNodesAndEdges()
    {
        var graph = ISONGraph.FromIson(SampleIson);

        Assert.Equal(2, graph.NodeCount());
        Assert.Equal(1, graph.EdgeCount());
        Assert.Equal("Alice", graph.GetNode("person", "1").Properties["name"]);
        Assert.True(graph.HasEdge("KNOWS", new("person", "1"), new("person", "2")));
        Assert.Equal("2020",
                     graph.GetEdge("KNOWS", new("person", "1"), new("person", "2"))
                          .Properties["since"]);
    }

    [Fact]
    public void ParseAliasWorks()
    {
        Assert.Equal(2, ISONGraph.Parse(SampleIson).NodeCount());
    }

    [Fact]
    public void RoundTrip()
    {
        var graph1 = new ISONGraph();
        graph1.AddNode("person", "1", Props.Of(("name", "Alice"), ("age", "30")));
        graph1.AddNode("person", "2", Props.Of(("name", "Bob"), ("age", "25")));
        graph1.AddEdge("KNOWS", new("person", "1"), new("person", "2"),
                       Props.Of(("since", "2020")));

        var graph2 = ISONGraph.FromIson(graph1.ToIson());

        Assert.Equal(graph1.NodeCount(), graph2.NodeCount());
        Assert.Equal(graph1.EdgeCount(), graph2.EdgeCount());
        Assert.Equal("30", graph2.GetNode("person", "1").Properties["age"]);
    }

    public static readonly (string Key, string Value)[] SpecialValues =
    {
        ("title", "Hello World"),   // contains a space
        ("tag", "a|b"),             // contains a pipe
        ("body", "line1\nline2"),   // contains a newline
        ("note", ""),               // empty string
        ("quote", "say \"hi\""),    // contains a double quote
        ("path", "C:\\temp\\x y"),  // backslashes + space
    };

    [Fact]
    public void RoundTripSpecialValuesIson()
    {
        var graph1 = new ISONGraph();
        graph1.AddNode("doc", "1", SpecialValues.ToDictionary(p => p.Key, p => p.Value));

        var graph2 = ISONGraph.FromIson(graph1.ToIson());

        var props = graph2.GetNode("doc", "1").Properties;
        foreach (var (key, expected) in SpecialValues)
            Assert.Equal(expected, props[key]);
    }

    [Fact]
    public void RoundTripSpecialValuesIsonl()
    {
        var graph1 = new ISONGraph();
        graph1.AddNode("doc", "1", SpecialValues.ToDictionary(p => p.Key, p => p.Value));

        var graph2 = ISONGraph.FromIsonl(graph1.ToIsonl());

        var props = graph2.GetNode("doc", "1").Properties;
        foreach (var (key, expected) in SpecialValues)
            Assert.Equal(expected, props[key]);
    }

    [Fact]
    public void RoundTripSpecialEdgePropertiesIsonl()
    {
        var graph1 = new ISONGraph();
        graph1.AddNode("a", "1");
        graph1.AddNode("a", "2");
        graph1.AddEdge("REL", new("a", "1"), new("a", "2"),
                       Props.Of(("note", "has | pipe and space"), ("empty", "")));

        var graph2 = ISONGraph.FromIsonl(graph1.ToIsonl());
        var edge = graph2.GetEdge("REL", new("a", "1"), new("a", "2"));
        Assert.Equal("has | pipe and space", edge.Properties["note"]);
        Assert.Equal("", edge.Properties["empty"]);
    }

    [Fact]
    public void RoundTripQuotedIdWithSpace()
    {
        var graph1 = new ISONGraph();
        graph1.AddNode("doc", "my id", Props.Of(("name", "X")));
        var graph2 = ISONGraph.FromIson(graph1.ToIson());
        Assert.True(graph2.HasNode("doc", "my id"));
    }

    [Fact]
    public void ValueCountMismatchThrows()
    {
        const string bad = """
nodes.person
id name age
1 Alice
""";
        var ex = Assert.Throws<GraphError>(() => ISONGraph.FromIson(bad));
        Assert.Contains("2 values", ex.Message);
        Assert.Contains("3 fields", ex.Message);
    }

    [Fact]
    public void MissingIdColumnThrows()
    {
        const string bad = """
nodes.person
name age
Alice 30
""";
        var ex = Assert.Throws<GraphError>(() => ISONGraph.FromIson(bad));
        Assert.Contains("id", ex.Message);
    }

    [Fact]
    public void MissingSourceTargetThrows()
    {
        const string bad = """
nodes.person
id
1
2

edges.KNOWS
source since
:person:1 2020
""";
        var ex = Assert.Throws<GraphError>(() => ISONGraph.FromIson(bad));
        Assert.Contains("target", ex.Message);
    }

    [Fact]
    public void UnknownBlockKindThrows()
    {
        const string bad = """
widgets.person
id name
1 Alice
""";
        var ex = Assert.Throws<GraphError>(() => ISONGraph.FromIson(bad));
        Assert.Contains("unknown block kind", ex.Message);
    }

    [Fact]
    public void HeaderWithoutDotThrows()
    {
        const string bad = """
person
id name
1 Alice
""";
        var ex = Assert.Throws<GraphError>(() => ISONGraph.FromIson(bad));
        Assert.Contains("malformed block header", ex.Message);
    }

    [Fact]
    public void DuplicateNodeRowThrows()
    {
        const string bad = """
nodes.person
id name
1 Alice
1 Alice2
""";
        var ex = Assert.Throws<GraphError>(() => ISONGraph.FromIson(bad));
        Assert.Contains("duplicate node", ex.Message);
    }

    [Fact]
    public void EdgeReferencingUndefinedNodeThrows()
    {
        const string bad = """
edges.KNOWS
source target
:person:1 :person:2
""";
        var ex = Assert.Throws<GraphError>(() => ISONGraph.FromIson(bad));
        Assert.Contains("has not been defined", ex.Message);
    }

    [Fact]
    public void MalformedNodeRefThrows()
    {
        const string bad = """
nodes.person
id
1
2

edges.KNOWS
source target
person1 :person:2
""";
        var ex = Assert.Throws<GraphError>(() => ISONGraph.FromIson(bad));
        Assert.Contains("Invalid node reference", ex.Message);
    }

    [Fact]
    public void DuplicateEdgeRowThrows()
    {
        const string bad = """
nodes.person
id
1
2

edges.KNOWS
source target
:person:1 :person:2
:person:1 :person:2
""";
        var ex = Assert.Throws<GraphError>(() => ISONGraph.FromIson(bad));
        Assert.Contains("duplicate edge", ex.Message);
    }
}

public class FromIsonlTests
{
    [Fact]
    public void ParsesLines()
    {
        const string isonl = """
nodes.person|id name age|1 Alice 30
nodes.person|id name age|2 Bob 25
edges.KNOWS|source target since|:person:1 :person:2 2020
""";
        var graph = ISONGraph.FromIsonl(isonl);
        Assert.Equal(2, graph.NodeCount());
        Assert.Equal(1, graph.EdgeCount());
        Assert.Equal("25", graph.GetNode("person", "2").Properties["age"]);
    }

    [Fact]
    public void RoundTripIsonl()
    {
        var graph1 = new ISONGraph();
        graph1.AddNode("person", "1", Props.Of(("name", "Alice")));
        graph1.AddNode("company", "acme", Props.Of(("name", "Acme Corp")));
        graph1.AddEdge("WORKS_AT", new("person", "1"), new("company", "acme"),
                       Props.Of(("role", "Engineer II")));

        var graph2 = ISONGraph.FromIsonl(graph1.ToIsonl());
        Assert.Equal(2, graph2.NodeCount());
        Assert.Equal(1, graph2.EdgeCount());
        Assert.Equal("Acme Corp", graph2.GetNode("company", "acme").Properties["name"]);
        Assert.Equal("Engineer II",
                     graph2.GetEdge("WORKS_AT", new("person", "1"), new("company", "acme"))
                           .Properties["role"]);
    }

    [Fact]
    public void MalformedLineThrows()
    {
        var ex = Assert.Throws<GraphError>(() => ISONGraph.FromIsonl("nodes.person|id name"));
        Assert.Contains("malformed line", ex.Message);
    }

    [Fact]
    public void FieldValueCountMismatchThrows()
    {
        var ex = Assert.Throws<GraphError>(
            () => ISONGraph.FromIsonl("nodes.person|id name age|1 Alice"));
        Assert.Contains("2 values", ex.Message);
    }

    [Fact]
    public void MissingIdThrows()
    {
        var ex = Assert.Throws<GraphError>(
            () => ISONGraph.FromIsonl("nodes.person|name|Alice"));
        Assert.Contains("id", ex.Message);
    }

    [Fact]
    public void UnknownKindThrows()
    {
        var ex = Assert.Throws<GraphError>(
            () => ISONGraph.FromIsonl("things.person|id|1"));
        Assert.Contains("unknown block kind", ex.Message);
    }

    [Fact]
    public void HeaderWithoutDotThrows()
    {
        Assert.Throws<GraphError>(() => ISONGraph.FromIsonl("person|id|1"));
    }

    [Fact]
    public void BlankLinesSkipped()
    {
        const string isonl = "\nnodes.person|id|1\n\n\nnodes.person|id|2\n";
        Assert.Equal(2, ISONGraph.FromIsonl(isonl).NodeCount());
    }

    [Fact]
    public void QuotedPipeInsideValueSurvives()
    {
        var graph1 = new ISONGraph();
        graph1.AddNode("doc", "1", Props.Of(("tag", "a|b|c")));
        var graph2 = ISONGraph.FromIsonl(graph1.ToIsonl());
        Assert.Equal("a|b|c", graph2.GetNode("doc", "1").Properties["tag"]);
    }
}

public class SplitterTests
{
    [Fact]
    public void SplitFieldsBasic()
    {
        Assert.Equal(new List<string> { "a", "b", "c" }, ISONGraph.SplitFields("a b c"));
    }

    [Fact]
    public void SplitFieldsQuoted()
    {
        Assert.Equal(new List<string> { "a b", "c" }, ISONGraph.SplitFields("\"a b\" c"));
    }

    [Fact]
    public void SplitFieldsEmptyQuoted()
    {
        Assert.Equal(new List<string> { "", "x" }, ISONGraph.SplitFields("\"\" x"));
    }

    [Fact]
    public void SplitFieldsUnescapes()
    {
        Assert.Equal(new List<string> { "say \"hi\"", "l1\nl2", "a\\b" },
                     ISONGraph.SplitFields("\"say \\\"hi\\\"\" \"l1\\nl2\" \"a\\\\b\""));
    }

    [Fact]
    public void SplitFieldsMultipleSpaces()
    {
        Assert.Equal(new List<string> { "a", "b" }, ISONGraph.SplitFields("a   b"));
    }

    [Fact]
    public void SplitPipeAwareRespectsQuotes()
    {
        Assert.Equal(new List<string> { "a", "\"b|c\"", "d" },
                     ISONGraph.SplitPipeAware("a|\"b|c\"|d"));
    }
}

public class FileIoTests
{
    [Fact]
    public void SaveAndLoadIson()
    {
        var dir = Directory.CreateTempSubdirectory("isongraph-io").FullName;
        try
        {
            var graph = new ISONGraph("social");
            graph.AddNode("person", "1", Props.Of(("name", "Alice")));
            graph.AddNode("person", "2", Props.Of(("name", "Bob")));
            graph.AddEdge("KNOWS", new("person", "1"), new("person", "2"));

            var path = System.IO.Path.Combine(dir, "social.ison");
            graph.Save(path);

            var loaded = ISONGraph.Load(path);
            Assert.Equal("social", loaded.Name); // name from file stem
            Assert.Equal(2, loaded.NodeCount());
            Assert.Equal(1, loaded.EdgeCount());
        }
        finally
        {
            Directory.Delete(dir, recursive: true);
        }
    }

    [Fact]
    public void SaveAndLoadIsonlByExtension()
    {
        var dir = Directory.CreateTempSubdirectory("isongraph-io").FullName;
        try
        {
            var graph = new ISONGraph();
            graph.AddNode("person", "1", Props.Of(("name", "Alice")));

            var path = System.IO.Path.Combine(dir, "g.isonl");
            graph.Save(path);

            Assert.Contains("nodes.person|", File.ReadAllText(path));
            var loaded = ISONGraph.Load(path);
            Assert.Equal(1, loaded.NodeCount());
        }
        finally
        {
            Directory.Delete(dir, recursive: true);
        }
    }
}

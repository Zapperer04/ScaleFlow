import difflib
import json

def pretty_json_diff(json_a, json_b):
    str_a = json.dumps(json_a, indent=2, sort_keys=True)
    str_b = json.dumps(json_b, indent=2, sort_keys=True)
    diff = difflib.unified_diff(
        str_a.splitlines(keepends=True),
        str_b.splitlines(keepends=True),
        fromfile="golden",
        tofile="current"
    )
    return "".join(diff)

def graph_diff(graph_a, graph_b):
    # Diffs graph nodes and edges
    diff_report = []
    nodes_a = graph_a.get("nodes", []) or graph_a.get("pages", [])
    nodes_b = graph_b.get("nodes", []) or graph_b.get("pages", [])
    if len(nodes_a) != len(nodes_b):
        diff_report.append(f"Node count mismatch: golden={len(nodes_a)}, current={len(nodes_b)}")
    
    edges_a = graph_a.get("edges", [])
    edges_b = graph_b.get("edges", [])
    if len(edges_a) != len(edges_b):
        diff_report.append(f"Edge count mismatch: golden={len(edges_a)}, current={len(edges_b)}")
        
    if not diff_report:
        # Detailed diff
        js_diff = pretty_json_diff(graph_a, graph_b)
        if js_diff:
            diff_report.append(js_diff)
            
    return "\n".join(diff_report)

def chunk_diff(chunks_a, chunks_b):
    diff_report = []
    if len(chunks_a) != len(chunks_b):
        diff_report.append(f"Chunk count mismatch: golden={len(chunks_a)}, current={len(chunks_b)}")
        
    js_diff = pretty_json_diff(chunks_a, chunks_b)
    if js_diff:
        diff_report.append(js_diff)
        
    return "\n".join(diff_report)

def metadata_diff(meta_a, meta_b):
    return pretty_json_diff(meta_a, meta_b)

def artifact_diff(art_a, art_b):
    return pretty_json_diff(art_a, art_b)

def pipeline_diff(pipe_a, pipe_b):
    return pretty_json_diff(pipe_a, pipe_b)

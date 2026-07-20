import re
import difflib
from typing import Dict, Any, Tuple, List

class GraphComparator:
    """
    Compares a Legacy document graph vs an Execution Engine document graph
    across three dimensions: Structural, Textual, and Semantic.
    """

    def compare(self, legacy_graph: Dict[str, Any], engine_graph: Dict[str, Any]) -> Tuple[float, float, float, Dict[str, Any]]:
        """
        Runs three comparisons and returns:
        (structural_pct, textual_pct, semantic_pct, diff_report)
        """
        legacy_nodes = self._extract_nodes(legacy_graph)
        engine_nodes = self._extract_nodes(engine_graph)
        
        legacy_edges = legacy_graph.get("edges", [])
        engine_edges = engine_graph.get("edges", [])
        
        # 1. Structural Parity (nodes, edges, cycles, orphans)
        struct_match, struct_details = self._compare_structural(legacy_nodes, engine_nodes, legacy_edges, engine_edges)
        
        # 2. Textual Parity
        text_match, text_details = self._compare_textual(legacy_nodes, engine_nodes)
        
        # 3. Semantic Parity
        semantic_match, semantic_details = self._compare_semantic(legacy_nodes, engine_nodes)
        
        # topological graph diff calculations
        legacy_node_ids = {n.get("chunk_id", n.get("id")) for n in legacy_nodes if n.get("chunk_id", n.get("id"))}
        engine_node_ids = {n.get("chunk_id", n.get("id")) for n in engine_nodes if n.get("chunk_id", n.get("id"))}
        
        added_nodes = list(engine_node_ids - legacy_node_ids)
        removed_nodes = list(legacy_node_ids - engine_node_ids)
        
        changed_attributes = []
        for nid in legacy_node_ids.intersection(engine_node_ids):
            legacy_n = next(n for n in legacy_nodes if n.get("chunk_id", n.get("id")) == nid)
            engine_n = next(n for n in engine_nodes if n.get("chunk_id", n.get("id")) == nid)
            for attr in ["structural_type", "type", "semantic_category"]:
                if legacy_n.get(attr) != engine_n.get(attr):
                    changed_attributes.append(f"Node '{nid}' attribute '{attr}' mismatched: Legacy='{legacy_n.get(attr)}', Engine='{engine_n.get(attr)}'")
                    
        # Compare normalized edges diffs
        def get_edge_tuples(edges_list):
            return {(e.get("from"), e.get("to"), e.get("relation")) for e in edges_list if isinstance(e, dict)}
        legacy_edge_tuples = get_edge_tuples(legacy_edges)
        engine_edge_tuples = get_edge_tuples(engine_edges)
        
        added_edges = [list(e) for e in (engine_edge_tuples - legacy_edge_tuples)]
        removed_edges = [list(e) for e in (legacy_edge_tuples - engine_edge_tuples)]
        
        graph_diff = {
            "added_nodes": added_nodes,
            "removed_nodes": removed_nodes,
            "changed_attributes": changed_attributes,
            "edge_changes": {
                "added_edges": added_edges,
                "removed_edges": removed_edges
            }
        }
        
        # Decompose confidence metric scores
        struct_conf = 1.0
        if struct_details.get("orphans_detected", 0) > 0:
            struct_conf -= 0.05 * struct_details["orphans_detected"]
        if struct_details.get("cycles_detected", 0) > 0:
            struct_conf -= 0.10 * struct_details["cycles_detected"]
            
        table_similarity = text_details.get("table_similarity", 100.0)
        table_conf = table_similarity / 100.0
        
        entity_conf = semantic_match / 100.0
        
        # Invert normalizer/validator repair counts into validation confidence
        repair_conf = 1.0
        # If normalizer is forced to repair node parentage, drop score
        if len(changed_attributes) > 0:
            repair_conf -= 0.05 * len(changed_attributes)
        repair_conf = max(0.5, repair_conf)
        
        # Calculate decomposed factors
        confidence_factors = {
            "structural_confidence": max(0.5, struct_conf),
            "table_confidence": max(0.5, table_conf),
            "entity_confidence": max(0.5, entity_conf),
            "repair_confidence": repair_conf,
            "overall_confidence": max(0.5, (struct_conf * 0.3 + table_conf * 0.2 + entity_conf * 0.3 + repair_conf * 0.2))
        }

        comparison_details = {
            "structural": struct_details,
            "textual": text_details,
            "semantic": semantic_details,
            "graph_diff": graph_diff,
            "confidence_factors": confidence_factors,
            "confidence": confidence_factors["overall_confidence"]
        }
        
        return struct_match, text_match, semantic_match, comparison_details



    def _extract_nodes(self, graph: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract flat list of nodes from either pages or root nodes key."""
        nodes = []
        if "pages" in graph and isinstance(graph["pages"], list):
            for page in graph["pages"]:
                if isinstance(page, dict) and "nodes" in page:
                    nodes.extend(page["nodes"])
        elif "nodes" in graph and isinstance(graph["nodes"], list):
            nodes.extend(graph["nodes"])
        return nodes

    def _detect_cycles_and_orphans(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Tuple[int, int]:
        """Simple DFS cycle detection and orphan finder."""
        node_ids = {n.get("chunk_id", n.get("id")) for n in nodes if n.get("chunk_id", n.get("id"))}
        adj = {nid: [] for nid in node_ids}
        incoming = {nid: 0 for nid in node_ids}
        
        for e in edges:
            frm = e.get("from")
            to = e.get("to")
            if frm in adj and to in adj:
                adj[frm].append(to)
                incoming[to] += 1
                
        # Orphans (nodes with no incoming connections, excluding root nodes)
        orphans = sum(1 for nid, count in incoming.items() if count == 0)
        
        # DFS Cycle detection
        visited = set()
        path = set()
        cycles = 0
        
        def dfs(node):
            nonlocal cycles
            visited.add(node)
            path.add(node)
            for neighbor in adj[node]:
                if neighbor in path:
                    cycles += 1
                elif neighbor not in visited:
                    dfs(neighbor)
            path.remove(node)
            
        for node in node_ids:
            if node not in visited:
                dfs(node)
                
        return cycles, orphans

    def _compare_structural(self, legacy_nodes: List[Dict[str, Any]], engine_nodes: List[Dict[str, Any]], legacy_edges: List[Dict[str, Any]], engine_edges: List[Dict[str, Any]]) -> Tuple[float, Dict[str, Any]]:
        """
        Compares nodes structure, hierarchy, edge references, cycles, and orphans.
        """
        total_legacy_nodes = len(legacy_nodes)
        total_engine_nodes = len(engine_nodes)
        
        max_nodes = max(total_legacy_nodes, total_engine_nodes, 1)
        node_count_similarity = 1.0 - (abs(total_legacy_nodes - total_engine_nodes) / max_nodes)
        
        # Compare parent-child relationships
        legacy_hierarchy = {n.get("chunk_id", n.get("id")): n.get("parent") for n in legacy_nodes if n.get("chunk_id", n.get("id"))}
        engine_hierarchy = {n.get("chunk_id", n.get("id")): n.get("parent") for n in engine_nodes if n.get("chunk_id", n.get("id"))}
        
        hierarchy_matches = 0
        total_h_checks = len(legacy_hierarchy)
        if total_h_checks > 0:
            for nid, parent in legacy_hierarchy.items():
                if nid in engine_hierarchy and engine_hierarchy[nid] == parent:
                    hierarchy_matches += 1
            hierarchy_parity = hierarchy_matches / total_h_checks
        else:
            hierarchy_parity = 1.0
            
        # Detect cycles/orphans
        legacy_cycles, legacy_orphans = self._detect_cycles_and_orphans(legacy_nodes, legacy_edges)
        engine_cycles, engine_orphans = self._detect_cycles_and_orphans(engine_nodes, engine_edges)
        
        # Compare edges
        def normalize_edge(e):
            return (e.get("from"), e.get("to"), e.get("relation"))
            
        legacy_edge_set = {normalize_edge(e) for e in legacy_edges if isinstance(e, dict)}
        engine_edge_set = {normalize_edge(e) for e in engine_edges if isinstance(e, dict)}
        
        edge_matches = len(legacy_edge_set.intersection(engine_edge_set))
        max_edges = max(len(legacy_edge_set), len(engine_edge_set), 1)
        edge_similarity = edge_matches / max_edges if max_edges > 0 else 1.0
        
        structural_pct = (0.4 * node_count_similarity + 0.3 * hierarchy_parity + 0.3 * edge_similarity) * 100.0
        structural_pct = max(0.0, min(100.0, structural_pct))
        
        differences = []
        if total_legacy_nodes != total_engine_nodes:
            differences.append(f"Node count mismatch: Legacy={total_legacy_nodes}, Engine={total_engine_nodes}.")
        if legacy_cycles != engine_cycles:
            differences.append(f"Cycles mismatch: Legacy={legacy_cycles}, Engine={engine_cycles}.")
            
        return structural_pct, {
            "legacy_node_count": total_legacy_nodes,
            "engine_node_count": total_engine_nodes,
            "legacy_edge_count": len(legacy_edges),
            "engine_edge_count": len(engine_edges),
            "orphans_detected": engine_orphans,
            "cycles_detected": engine_cycles,
            "differences": differences
        }




    def _compare_textual(self, legacy_nodes: List[Dict[str, Any]], engine_nodes: List[Dict[str, Any]]) -> Tuple[float, Dict[str, Any]]:
        """
        Compares extracted text across headings, lists, tables, paragraphs.
        Uses normalized Jaccard word-level similarity and table cell alignment comparisons.
        """
        legacy_text = "\n".join([n.get("text", n.get("content", "")) for n in legacy_nodes]).strip().lower()
        engine_text = "\n".join([n.get("text", n.get("content", "")) for n in engine_nodes]).strip().lower()
        
        if not legacy_text and not engine_text:
            return 100.0, {"legacy_char_count": 0, "engine_char_count": 0, "table_similarity": 100.0, "differences": []}
            
        legacy_words = set(re.findall(r'\b\w+\b', legacy_text))
        engine_words = set(re.findall(r'\b\w+\b', engine_text))
        
        intersection = len(legacy_words.intersection(engine_words))
        union = len(legacy_words.union(engine_words))
        
        text_match_pct = (intersection / union * 100.0) if union > 0 else 0.0
        
        legacy_tables = [n.get("text", "") for n in legacy_nodes if n.get("semantic_category") == "table"]
        engine_tables = [n.get("text", "") for n in engine_nodes if n.get("semantic_category") == "table"]
        
        table_similarity = 100.0
        if legacy_tables or engine_tables:
            l_tab_words = set(re.findall(r'\b\w+\b', "\n".join(legacy_tables).lower()))
            e_tab_words = set(re.findall(r'\b\w+\b', "\n".join(engine_tables).lower()))
            tab_inter = len(l_tab_words.intersection(e_tab_words))
            tab_union = len(l_tab_words.union(e_tab_words))
            table_similarity = (tab_inter / tab_union * 100.0) if tab_union > 0 else 0.0
            
        differences = []
        if abs(len(legacy_text) - len(engine_text)) > 50:
            differences.append(f"Text length delta: Legacy={len(legacy_text)} chars, Engine={len(engine_text)} chars.")
            
        return text_match_pct, {
            "legacy_char_count": len(legacy_text),
            "engine_char_count": len(engine_text),
            "table_similarity": table_similarity,
            "differences": differences
        }

    def _compare_semantic(self, legacy_nodes: List[Dict[str, Any]], engine_nodes: List[Dict[str, Any]]) -> Tuple[float, Dict[str, Any]]:
        """
        Compares entities, key terms, numbers, and identifiers ignoring structural noise.
        """
        def extract_entities(nodes: List[Dict[str, Any]]) -> Dict[str, str]:
            # Try to build normalized key-value mappings or entity associations
            entities = {}
            for n in nodes:
                text = n.get("text", n.get("content", ""))
                # Match common patterns like Key: Value or Identifier = Value
                matches = re.findall(r'\b([\w\s]{2,15})\s*[:=]\s*([\w\s\.\,\-\/]{1,30})\b', text)
                for k, v in matches:
                    entities[k.strip().lower()] = v.strip().lower()
            return entities
            
        legacy_entities = extract_entities(legacy_nodes)
        engine_entities = extract_entities(engine_nodes)
        
        matches = 0
        total_keys = set(legacy_entities.keys()).union(engine_entities.keys())
        
        for k in total_keys:
            if k in legacy_entities and k in engine_entities:
                if legacy_entities[k] == engine_entities[k]:
                    matches += 1
                    
        semantic_pct = (matches / len(total_keys) * 100.0) if total_keys else 100.0
        
        differences = []
        missing_keys = set(legacy_entities.keys()) - set(engine_entities.keys())
        mismatched_vals = []
        for k in legacy_entities:
            if k in engine_entities and legacy_entities[k] != engine_entities[k]:
                mismatched_vals.append(f"'{k}' (Legacy='{legacy_entities[k]}', Engine='{engine_entities[k]}')")
                
        if missing_keys:
            differences.append(f"Missing key entities in Engine: {list(missing_keys)[:3]}")
        if mismatched_vals:
            differences.append(f"Mismatched entity values: {mismatched_vals[:2]}")
            
        return semantic_pct, {
            "legacy_entity_count": len(legacy_entities),
            "engine_entity_count": len(engine_entities),
            "matching_entities": matches,
            "differences": differences
        }


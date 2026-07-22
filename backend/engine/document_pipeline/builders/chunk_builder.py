import re
from typing import Dict, Any, List
from engine.document_pipeline.builders.base_builder import BaseBuilder
from engine.document_pipeline.schemas import CanonicalDocument, SemanticChunk

class ChunkBuilder(BaseBuilder):
    @property
    def name(self) -> str:
        return "chunks"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def dependencies(self) -> List[str]:
        return ["graph", "entities", "layout"]

    def build(self, doc: CanonicalDocument, context: Dict[str, Any]) -> List[SemanticChunk]:
        chunks: List[SemanticChunk] = []
        
        # Load stable ID mapping from context
        graph_id_map = context.get("graph_id_map", {})

        # Boundaries come from parsed sections hierarchy
        sections = doc.sections or []
        heading_ids = [s.get("heading_id") for s in sections if s.get("heading_id")]

        groups = []
        current_heading_block = None
        current_blocks = []
        active_section_path = []

        for block in doc.blocks:
            if block.id in heading_ids or block.type == "heading":
                if current_blocks:
                    groups.append((current_heading_block, current_blocks, list(active_section_path)))
                current_heading_block = block
                current_blocks = [block]
                
                sec_path = [block.text]
                for s in sections:
                    if s.get("heading_id") == block.id:
                        sec_path = [s.get("title", block.text)]
                        break
                active_section_path = sec_path
            else:
                current_blocks.append(block)

        if current_blocks:
            groups.append((current_heading_block, current_blocks, list(active_section_path)))

        if not groups and doc.blocks:
            groups.append((None, doc.blocks, ["Root"]))

        # Load entity records
        entity_graph = context.get("entities")
        all_entity_names = []
        entity_records_list = []
        if entity_graph:
            if isinstance(entity_graph, dict):
                entity_records_list = entity_graph.get("entities", [])
            else:
                entity_records_list = entity_graph.entities

            for e in entity_records_list:
                e_name = e.get("name") if isinstance(e, dict) else e.name
                all_entity_names.append(e_name)

        previous_chunk_id = None

        for idx, (heading_block, blocks, path) in enumerate(groups):
            chunk_id = f"chunk-{idx}"
            body_text = "\n".join([b.text for b in blocks])
            heading_text = heading_block.text if heading_block else ""

            # Keywords extraction
            stopwords = {"about", "above", "after", "again", "against", "along", "could", "would", "should", "their", "there", "these", "those", "under", "which", "while"}
            words = re.findall(r'\b[a-zA-Z]{5,}\b', body_text.lower())
            keywords = sorted(list(set([w for w in words if w not in stopwords])))[:8]

            # Table & Figure references
            table_refs = []
            for match in re.finditer(r'\bTable\s+\d+\b', body_text, re.IGNORECASE):
                ref_str = match.group(0)
                if ref_str not in table_refs:
                    table_refs.append(ref_str)

            figure_refs = []
            for match in re.finditer(r'\bFigure\s+\d+\b', body_text, re.IGNORECASE):
                ref_str = match.group(0)
                if ref_str not in figure_refs:
                    figure_refs.append(ref_str)

            # Generate VLM/Extractive Summary
            sentences = re.split(r'(?<=[.!?])\s+', body_text.strip())
            summary = " ".join(sentences[:2])
            if len(summary) > 200:
                summary = summary[:197] + "..."

            # Page Range & Bounding Box
            pages = sorted(list(set([b.page for b in blocks])))
            ymin, xmin, ymax, xmax = 1.0, 1.0, 0.0, 0.0
            
            lineage = []
            stable_node_ids = []

            for b in blocks:
                stable_id = graph_id_map.get(b.id, b.id)
                stable_node_ids.append(stable_id)

                bbox_dict = b.bbox.to_dict() if b.bbox else {"ymin": 0.0, "xmin": 0.0, "ymax": 1.0, "xmax": 1.0}
                lineage.append({
                    "block_id": b.id,
                    "stable_node_id": stable_id,
                    "page": b.page,
                    "bbox": bbox_dict
                })

                if b.bbox:
                    ymin = min(ymin, b.bbox.ymin)
                    xmin = min(xmin, b.bbox.xmin)
                    ymax = max(ymax, b.bbox.ymax)
                    xmax = max(xmax, b.bbox.xmax)

            if ymax < ymin:
                ymin, xmin, ymax, xmax = 0.0, 0.0, 1.0, 1.0

            # Entity tagging
            chunk_entities = []
            for ent in entity_records_list:
                e_name = ent.get("name") if isinstance(ent, dict) else ent.name
                if e_name.lower() in body_text.lower():
                    chunk_entities.append(e_name)
                    # Backlink Chunk ID to Entity Record
                    if isinstance(ent, dict):
                        ent.setdefault("chunk_ids", []).append(chunk_id)
                        ent.setdefault("graph_node_ids", []).extend(stable_node_ids)
                    else:
                        if hasattr(ent, "chunk_ids"):
                            ent.chunk_ids.append(chunk_id)
                        if hasattr(ent, "graph_node_ids"):
                            ent.graph_node_ids.extend(stable_node_ids)

            # Importance score
            importance_score = 1.0
            if heading_block:
                importance_score += 0.3
            if len(body_text) > 1000:
                importance_score += 0.2
            if len(chunk_entities) > 5:
                importance_score += 0.2
            importance_score = round(importance_score, 2)

            # Retrieval hints & Best_for tags
            chunk_type = "narrative"
            retrieval_tags = ["body"]
            query_intent = ["informational"]
            best_for = ["semantic"]

            if heading_block:
                chunk_type = "factual"
                retrieval_tags.append("section_start")
                best_for.append("comparison")
            if any(term in body_text.lower() for term in ["define", "definition", "refers to", "means"]):
                chunk_type = "definition"
                retrieval_tags.append("terminology")
                query_intent.append("conceptual")
                best_for.append("definition")
            if len(chunk_entities) > 2:
                best_for.append("entity")
            if table_refs:
                best_for.append("table_lookup")

            chunk = SemanticChunk(
                chunk_id=chunk_id,
                text=body_text,
                summary=summary,
                parent_node=graph_id_map.get(heading_block.id, heading_block.id) if heading_block else "doc-root",
                section_path=path,
                page_range=pages,
                bbox={"ymin": ymin, "xmin": xmin, "ymax": ymax, "xmax": xmax},
                graph_node_ids=stable_node_ids,
                entities=chunk_entities,
                keywords=keywords,
                table_refs=table_refs,
                figure_refs=figure_refs,
                previous_chunk=previous_chunk_id,
                next_chunk=None,
                reading_order=idx,
                importance_score=importance_score,
                lineage=lineage,
                retrieval_tags=retrieval_tags,
                query_intent=query_intent,
                chunk_type=chunk_type,
                priority=importance_score,
                best_for=best_for
            )

            if chunks:
                chunks[-1].next_chunk = chunk_id

            chunks.append(chunk)
            previous_chunk_id = chunk_id

        # Update backlinks to tables in doc
        for table in doc.tables:
            table_id_stable = graph_id_map.get(table.id, table.id)
            table.graph_node_id = table_id_stable
            for chunk in chunks:
                if table.caption and table.caption.lower() in chunk.text.lower():
                    table.chunk_ids.append(chunk.chunk_id)

        # Update backlinks into graph node dictionaries
        graph = context.get("graph")
        if graph and "nodes" in graph:
            node_map = {n["id"]: n for n in graph["nodes"]}
            for chunk in chunks:
                for n_id in chunk.graph_node_ids:
                    if n_id in node_map:
                        node_map[n_id].setdefault("chunk_ids", []).append(chunk.chunk_id)

        return chunks

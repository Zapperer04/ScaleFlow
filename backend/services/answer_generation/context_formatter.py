from typing import List
from services.document_retrieval.candidate import Candidate

class ContextFormatter:
    def format_candidates(self, candidates: List[Candidate]) -> str:
        if not candidates:
            return "No evidence retrieved."

        formatted_blocks = []
        for idx, cand in enumerate(candidates):
            evidence_index = idx + 1
            section = " > ".join(cand.section_path) if cand.section_path else "General Section"
            pages = ", ".join(map(str, cand.page_numbers)) if cand.page_numbers else "Unknown Page"
            
            block_header = f"--- EVIDENCE [{evidence_index}] (Section: {section} | Page: {pages}) ---"
            
            # Format entities list if available
            entities_str = ""
            if cand.entities:
                entities_str = f"Entities Mentioned: {', '.join(cand.entities)}\n"

            # Check if block has unflattened table structures inside metadata and preserve them
            table_str = ""
            table_data = cand.metadata.get("table")
            if table_data:
                headers = table_data.get("headers", [])
                cells = table_data.get("cells", [])
                table_str = f"\n[Table Schema]\nHeaders: {' | '.join(headers)}\n"
                for cell in cells:
                    table_str += f"Row {cell.get('row')}, Col {cell.get('col')}: {cell.get('text')}\n"

            formatted_block = (
                f"{block_header}\n"
                f"{entities_str}"
                f"{cand.text}\n"
                f"{table_str}"
            )
            formatted_blocks.append(formatted_block)

        return "\n\n".join(formatted_blocks)

import os
import sys
import json

# Adjust path to find backend modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import config
from services.embedding_service import embed_text
from services.vector_store import search_similar, get_client
import qdrant_client.models as qmodels
from services.bm25_service import retrieve_bm25
from services.retrieval_service import detect_query_intent, retrieve_dense, merge_candidates, apply_importance_boost
from services.graph_expansion_service import expand_graph_context
from services.reranker_service import rerank

query = "who are the inventors"
pipeline_id = 549
file_id = 178

print("=== 1. Dense retrieval output ===")
q_vec = embed_text(query)
collections = detect_query_intent(query)
dense_candidates = []
for coll in collections:
    filters = {"pipeline_id": pipeline_id}
    res = search_similar(coll, q_vec, top_k=20, filters=filters)
    dense_candidates.extend(res)
print(json.dumps(dense_candidates[:3], indent=2))

print("\n=== 2. BM25 output ===")
bm25_candidates = retrieve_bm25(pipeline_id, query, top_k=20)
print(json.dumps(bm25_candidates[:3], indent=2))

print("\n=== 3. Reciprocal rank fusion output ===")
# RRF in merge_candidates
merged = merge_candidates(dense_candidates, bm25_candidates)
print(json.dumps(merged[:3], indent=2))

print("\n=== 4. Graph expansion output ===")
# Graph expansion on merged candidates
expanded = expand_graph_context(merged, pipeline_id=pipeline_id, expansion_depth=1, limit=50)
print(json.dumps(expanded[:3], indent=2))

print("\n=== 5. Reranker input ===")
boosted = apply_importance_boost(expanded)
boosted.sort(key=lambda x: x.get("final_score", 0.0), reverse=True)
candidates_for_rerank = boosted[:20]
print(json.dumps(candidates_for_rerank[:2], indent=2))

print("\n=== 6. Reranker output ===")
reranked = rerank(query, candidates_for_rerank, top_k=5)
print(json.dumps(reranked, indent=2))

print("\n=== 7. Final context assembly object ===")
top_chunks = reranked[:3]
context_window = ""
for idx, c in enumerate(top_chunks):
    context_window += f"[Source {idx+1}]: {c.get('chunk_text', '')}\n"
print("Context Window Structure Object:")
print(repr(context_window))

print("\n=== 8. Exact prompt sent to LLM ===")
system_prompt = (
    "You are a precise document Q&A assistant. Answer the user's question in 1-3 clear, natural sentences "
    "using ONLY the information from the provided sources.\n"
    "Strict Grounding Rules:\n"
    "1. Do NOT use external knowledge, infer, or extrapolate beyond the provided sources.\n"
    "2. Do NOT conflate or combine unrelated facts from different sources.\n"
    "3. Answer directly.\n"
    "4. Do NOT copy-paste raw source text verbatim.\n"
    "5. If the sources do not contain direct, explicit information, you MUST respond exactly: "
    "'The document does not contain sufficient information to answer this question.'"
)
user_prompt = f"Sources:\n{context_window}\nQuestion: {query}\nProvide a direct, concise answer in 1-3 sentences:"
print("System Prompt:\n", system_prompt)
print("User Prompt:\n", user_prompt)

print("\n=== 9. Raw LLM response ===")
from services.llm_service import generate_answer
ans, provider, status = generate_answer(query, top_chunks)
print(f"Provider: {provider}, Status: {status}")
print("Response:\n", ans)

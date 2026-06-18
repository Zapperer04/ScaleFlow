import sys
sys.stdout.reconfigure(encoding='utf-8')
from services.vector_store import get_client, search_similar
from services.embedding_service import get_embedding_model

model = get_embedding_model()
query = 'what projects has this candidate built'
vec = model.encode(query).tolist()
results = search_similar('scaleflow_chunks', vec, top_k=5)
print('Results count:', len(results))
for r in results:
    print('Score:', r['score'], 'Section:', r.get('section','?'), 'Text:', (r.get('chunk_text') or '')[:100])

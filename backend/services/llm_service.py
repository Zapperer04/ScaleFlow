import os
import requests
import json
import re

def generate_answer(query: str, chunks: list[dict]) -> tuple[str, str, str]:
    """
    Generates a synthesized answer for the given query and chunks.
    Returns: (answer_text, provider_used, response_status)
    """
    # Build prompt/context window
    context_text = ""
    for idx, c in enumerate(chunks):
        text = c.get("chunk_text") or c.get("text") or ""
        context_text += f"[Source {idx+1}]: {text}\n\n"
        
    system_prompt = (
        "You are a precise document Q&A assistant. Answer the user's question in 1-3 clear, natural sentences "
        "using ONLY the information from the provided sources. "
        "Rules: (1) Answer directly and concisely — do NOT use bullet points or numbered lists. "
        "(2) Do NOT copy-paste raw source text verbatim. Write a proper synthesized sentence. "
        "(3) If the exact answer is in the sources, state it clearly (e.g. 'The deadline is 07/04/2026.'). "
        "(4) If the answer is not in the sources, respond: 'The document does not contain sufficient information to answer this question.'"
    )
    user_prompt = f"Sources:\n{context_text}\nQuestion: {query}\nProvide a direct, concise answer in 1-3 sentences:"
    
    # Try Groq if API key exists
    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.2
            }
            res = requests.post(url, json=data, headers=headers, timeout=10)
            if res.status_code == 200:
                answer = res.json()["choices"][0]["message"]["content"].strip()
                return answer, "Groq (llama-3.1-8b-instant)", "200 OK"
            else:
                print(f"Groq API failed: {res.status_code} - {res.text}", flush=True)
        except Exception as e:
            print(f"Groq API error: {e}", flush=True)

    # Try OpenAI if API key exists
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {openai_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.2
            }
            res = requests.post(url, json=data, headers=headers, timeout=10)
            if res.status_code == 200:
                answer = res.json()["choices"][0]["message"]["content"].strip()
                return answer, "OpenAI (gpt-4o-mini)", "200 OK"
            else:
                print(f"OpenAI API failed: {res.status_code} - {res.text}", flush=True)
        except Exception as e:
            print(f"OpenAI API error: {e}", flush=True)

    # Try Ollama (default local host)
    ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    try:
        url = f"{ollama_host}/api/generate"
        data = {
            "model": "llama3",
            "prompt": f"{system_prompt}\n\n{user_prompt}",
            "stream": False,
            "options": {"temperature": 0.2}
        }
        res = requests.post(url, json=data, timeout=8)
        if res.status_code == 200:
            answer = res.json().get("response", "").strip()
            return answer, "Ollama (llama3)", "200 OK"
    except Exception:
        pass

    # ──────────────────────────────────────────────────────────────────────────
    # Document-Agnostic Extractive RAG Fallback
    # ──────────────────────────────────────────────────────────────────────────
    query_lower = query.lower()

    # Tokenize query to extract keywords (excluding standard stopwords)
    stopwords = {
        "what", "is", "the", "does", "has", "completed", "candidate", "have", "listed", "about",
        "role", "at", "in", "of", "and", "a", "an", "to", "for", "on", "with", "by", "from", "are",
        "who", "which", "where", "how", "did", "do", "done", "this", "that", "these", "those"
    }
    query_tokens = re.findall(r"\b\w{3,}\b", query_lower)
    keywords = [kw for kw in query_tokens if kw not in stopwords]

    # If no keywords are found, use all query tokens
    if not keywords:
        keywords = [t for t in query_tokens if t]

    sentences_pool = []
    seen_sentences = set()

    for chunk_idx, chunk in enumerate(chunks):
        text = chunk.get("chunk_text") or chunk.get("text") or ""
        # Clean standard unicode dashes and normalize whitespaces
        text = text.replace("\u2013", " — ").replace("\u2014", " — ").replace("\u2022", " ").replace("\x95", " ")
        text = re.sub(r"\s+", " ", text).strip()
        
        # Split into sentences using punctuation boundaries
        sentences = re.split(r"(?<=[.!?])\s+", text)
        for s in sentences:
            s_clean = s.strip()
            if len(s_clean) > 15:
                # Deduplicate sentences case-insensitively
                s_lower = s_clean.lower()
                if s_lower not in seen_sentences:
                    seen_sentences.add(s_lower)
                    
                    # Calculate keyword match score
                    unique_matches = sum(1 for kw in keywords if kw in s_lower)
                    total_occurrences = sum(s_lower.count(kw) for kw in keywords)
                    
                    # Chunk position weight (semantic relevance from vector database/reranker)
                    # The top chunk is the most semantically relevant
                    chunk_weight = 10.0 / (chunk_idx + 1)
                    
                    # Combine keyword matches and semantic position weight
                    score = (unique_matches * 5.0 + total_occurrences * 0.5 + 1.0) * chunk_weight
                    sentences_pool.append((score, s_clean))

    # Sort sentences by score descending
    sentences_pool.sort(key=lambda x: x[0], reverse=True)

    # Select top 4 sentences
    selected_sentences = [s for _, s in sentences_pool[:4]]
    if not selected_sentences:
        return "No sufficiently relevant context was found for this query.", "Local Heuristic Synthesizer", "404 Empty"

    ans = "Based on the retrieved document context:\n" + "\n".join([f"- {s}" for s in selected_sentences])
    return ans, "Local Heuristic Synthesizer", "200 OK (Heuristic)"

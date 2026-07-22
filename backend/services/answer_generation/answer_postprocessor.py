import re

class AnswerPostprocessor:
    def postprocess(self, text: str) -> str:
        if not text:
            return ""

        # 1. Remove duplicate adjacent sentences
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        seen = []
        for s in sentences:
            s_clean = s.strip()
            # Basic fuzzy duplicate check
            if not seen or all(self._sentence_similarity(s_clean, prev) < 0.85 for prev in seen[-3:]):
                seen.append(s_clean)
        
        text = " ".join(seen)

        # 2. Polishing citations formatting (e.g. [1][2] -> [1, 2] or separating spaced brackets)
        text = re.sub(r'\[(\d+)\]\s*\[(\d+)\]', r'[\1, \2]', text)

        # 3. Clean trailing whitespace / format punctuation around brackets
        text = re.sub(r'\s+([.,;!?])', r'\1', text)

        return text.strip()

    def _sentence_similarity(self, s1: str, s2: str) -> float:
        w1 = set(s1.lower().split())
        w2 = set(s2.lower().split())
        if not w1 or not w2:
            return 0.0
        return len(w1.intersection(w2)) / len(w1.union(w2))

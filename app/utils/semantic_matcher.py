# app/utils/semantic_matcher.py

from sentence_transformers import SentenceTransformer, util
from typing import List, Optional, Dict, Tuple
import torch
import os
from dotenv import load_dotenv
# from app.services.transcript_parser import standardize_objective_text

load_dotenv()

ST_MODEL = os.getenv("ST_MODEL")

model = SentenceTransformer(ST_MODEL)

# Top K Semantic Matches
def top_k_semantic_matches(
    query: str,
    candidates: List[Dict],
    key: str,
    id_key: str = "id",
    top_k: int = 3,
    threshold: float = 0
) -> List[Dict]:
    if not candidates:
        return []
    
    print("top_k_semantic_matches called");
    print("candidates: ", candidates)
    print("key: ", key)

    texts = [c[key] for c in candidates]
    print("Encoding texts: ", texts)
    print("Encoding query: ", query)
    candidate_embeddings = model.encode(texts, convert_to_tensor=True)
    query_embedding = model.encode(query, convert_to_tensor=True)

    scores = util.cos_sim(query_embedding, candidate_embeddings)[0]

    results = []
    for i, score in enumerate(scores):
        print("semantic matcher score: ", score, "for query: ", query, "and candidate: ", candidates[i][key])
        if score >= threshold:
            match = {
                "id": str(candidates[i][id_key]),
                "similarity": float(score)
            }
            # include either 'name' or 'description' in match
            if key == "name":
                match["name"] = candidates[i]["name"]
            elif key == "description":
                match["description"] = candidates[i]["description"]

            results.append(match)

    # sort by similarity descending
    results.sort(key=lambda x: x["similarity"], reverse=True)

    print("semantic matcher results: ", results[:top_k], "for query: ", query)

    return results[:top_k]
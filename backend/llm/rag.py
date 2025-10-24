import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
from backend.llm.llm_wrapper import LLMWrapper

# initialize embedding model (local)
EMBED_MODEL = "backend/models/embedder/all-MiniLM-L6-v2"  # ensure downloaded locally or will attempt to fetch
EMB_DIM = 384  # embedding dim for the MiniLM model

class RAG:
    def __init__(self, model_dir_for_llm: str, device: Optional[str] = None, embed_model_dir: str = None):
        # LLM
        self.llm = LLMWrapper(model_dir_for_llm, device=device)
        # Embeddings
        embed_dir = embed_model_dir or EMBED_MODEL
        self.embedder = SentenceTransformer(embed_dir, device="cpu")
        self.index = None
        self.docs = []  # store passages aligned with index

    def build_index_for_video(self, video_dir: str):
        """
        Load transcript segments and vision captions, build FAISS index.
        Each entry is a short passage string.
        """
        video_dir = Path(video_dir)
        # load transcript (pick latest transcript_*.json)
        transcripts = sorted(video_dir.glob("transcript_*.json"), key=os.path.getmtime, reverse=True)
        passages = []
        # transcripts segments
        if transcripts:
            t = json.loads(transcripts[0].read_text(encoding="utf-8"))
            for seg in t.get("segments", []):
                text = seg.get("text", "")
                start, end, conf = seg.get("start", 0.0), seg.get("end", 0.0), seg.get("confidence", 1.0)
                passages.append({"source":"transcript", "start":start, "end":end, "confidence":conf, "text": text})
        # vision captions (ocr + object labels)
        ocr_path = video_dir / "ocr.json"
        if ocr_path.exists():
            ocr_list = json.loads(ocr_path.read_text(encoding="utf-8"))
            for o in ocr_list:
                passages.append({"source":"ocr", "timestamp": o.get("timestamp"), "text": o.get("text",""), "confidence": o.get("confidence",1.0)})
        # object summary: top objects per video
        objects_path = video_dir / "objects.json"
        if objects_path.exists():
            objs = json.loads(objects_path.read_text(encoding="utf-8"))
            # compose small descriptions per timestamp
            for o in objs:
                cname = o.get("class_name") or str(o.get("class_id"))
                passages.append({"source":"vision_obj", "timestamp":o.get("timestamp"), "text": f"Detected {cname} (conf {o.get('confidence',0):.2f})", "confidence": o.get("confidence",1.0)})

        # store passages
        self.docs = passages
        texts = [p["text"] for p in passages]
        if len(texts) == 0:
            # create a minimal index
            self.index = None
            return

        embeddings = self.embedder.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dim)  # inner product for cosine when vectors normalized
        # normalize embeddings
        faiss.normalize_L2(embeddings)
        self.index.add(embeddings)

    def retrieve(self, query: str, top_k: int = 5):
        if self.index is None or len(self.docs) == 0:
            return []
        q_emb = self.embedder.encode([query], convert_to_numpy=True)
        faiss.normalize_L2(q_emb)
        D, I = self.index.search(q_emb, top_k)
        results = []
        for score, idx in zip(D[0], I[0]):
            if idx < 0 or idx >= len(self.docs):
                continue
            doc = self.docs[idx].copy()
            doc["score"] = float(score)
            results.append(doc)
        return results

    def compose_prompt(self, task: str, retrieved: List[Dict], max_ctx_chars: int = 4000) -> str:
        """
        Compose a prompt containing:
         - short instruction
         - retrieved context blocks with source/timestamp
         - user task/query
        """
        instruction = "You are an assistant that summarizes and answers questions about a short meeting video. Use the context to answer precisely."
        task_lower = task.lower()
        if "summarize" in task_lower or "summary" in task_lower:
            instruction = (
                "You are a factual assistant. Summarize the following context. "
                "Include timestamps where available. If unsure, say 'uncertain' rather than invent facts."
            )
        else:
            instruction = (
                "You are a concise assistant. Use only the context below to answer. "
                "If the answer is not present, say 'I don't know'. Provide any timestamped evidence."
            )
        ctx = []
        total = 0
        for r in retrieved:
            block = f"[{r.get('source')} {r.get('start', r.get('timestamp', ''))}] {r.get('text')}"
            if total + len(block) > max_ctx_chars:
                break
            ctx.append(block)
            total += len(block)

        # Final combined prompt
        prompt = (
            f"{instruction}\n\n"
            "Context:\n" + "\n---\n".join(ctx) + "\n\n"
            f"User: {task}\nAssistant:"
        )
        return prompt

    def summarize(self, video_dir: str) -> str:
        # build index if not done
        self.build_index_for_video(video_dir)
        # simple query
        query = "Summarize the context briefly."
        retrieved = self.retrieve(query, top_k=8)
        prompt = self.compose_prompt(query, retrieved)
        out = self.llm.generate(prompt, max_new_tokens=256)
        return out["text"]

    def answer(self, video_dir: str, question: str, top_k: int = 6) -> Dict[str,Any]:
        # quick rule: if question about graphs, check graphs.json first
        video_dir = Path(video_dir)
        if "graph" in question.lower() or "chart" in question.lower():
            graphs_path = video_dir / "graphs" / "graphs.json"
            if graphs_path.exists():
                graphs = json.loads(graphs_path.read_text(encoding="utf-8"))
                if graphs:
                    # produce short description from graphs
                    descs = [f"At {g.get('timestamp')}s found bbox {g.get('bbox')}" for g in graphs[:5]]
                    text = "Yes, the video includes graphs/charts. Examples: " + "; ".join(descs)
                    return {"answer": text, "confidence": 0.9, "source": "vision_graphs"}
            # else continue to RAG path if no graphs found
        # RAG path
        self.build_index_for_video(video_dir)
        retrieved = self.retrieve(question, top_k=top_k)
        prompt = self.compose_prompt(question, retrieved)
        out = self.llm.generate(prompt, max_new_tokens=200)
        # simple confidence heuristic: average retrieval score * average passage confidence (if present)
        if len(retrieved) > 0:
            avg_score = float(sum(r.get("score",0.0) for r in retrieved)/len(retrieved))
            avg_conf = float(sum(r.get("confidence",1.0) for r in retrieved)/len(retrieved))
            confidence = (avg_score + avg_conf) / 2.0
            confidence = max(0.0, min(1.0, confidence))
        else:
            confidence = 0.2
        return {"answer": out["text"].strip(), "confidence": confidence, "retrieved": retrieved}

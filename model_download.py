# backend/scripts/download_models.py
from transformers import AutoTokenizer, AutoModelForCausalLM
from sentence_transformers import SentenceTransformer
from pathlib import Path

import os
from pathlib import Path
from ultralytics import YOLO

# LLM (example)
llm_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
out_llm = Path("backend/models/llm/hf_llm")
out_llm.mkdir(parents=True, exist_ok=True)

# download LLM tokenizer + weights into HF cache and copy to local folder
tokenizer = AutoTokenizer.from_pretrained(llm_name)
model = AutoModelForCausalLM.from_pretrained(llm_name)
tokenizer.save_pretrained(str(out_llm))
model.save_pretrained(str(out_llm))

# Embedding model
embed_name = "sentence-transformers/all-MiniLM-L6-v2"
out_emb = Path("backend/models/embedder/all-MiniLM-L6-v2")
out_emb.mkdir(parents=True, exist_ok=True)
embed = SentenceTransformer(embed_name)
embed.save(str(out_emb))
print("Downloaded models to backend/models/")


# Export ONNX model
model = YOLO('yolov8n.pt')
onnx_path = model.export(format='onnx', imgsz=640, simplify=True)
dest_dir = Path('backend/models')
dest_dir.mkdir(parents=True, exist_ok=True)
dest_path = dest_dir / 'yolov8n.onnx'

# Move the exported ONNX file
Path(onnx_path).rename(dest_path)
print(f"Moved ONNX model to: {dest_path}")

# Clean up PT file if it exists and isn't needed elsewhere
pt_path = Path('yolov8n.pt')
if pt_path.exists():
    pt_path.unlink()
    print(f"Removed temporary PT file: {pt_path}")
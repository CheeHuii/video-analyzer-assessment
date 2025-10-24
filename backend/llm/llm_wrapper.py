# backend/llm/llm_wrapper.py
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig
from pathlib import Path

class LLMWrapper:
    def __init__(self, model_dir: str, device: str = None):
        self.model_dir = model_dir
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        print(f"[LLM] device set to {self.device}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
        self.model = AutoModelForCausalLM.from_pretrained(model_dir, local_files_only=True)
        self.model.to(self.device)
        self.model.eval()

    def generate(self, prompt: str, max_new_tokens: int = 256, temperature: float = 0.0):
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048).to(self.device)
        gen_config = GenerationConfig(max_new_tokens=max_new_tokens, temperature=temperature, do_sample=False)
        with torch.no_grad():
            out = self.model.generate(**inputs, generation_config=gen_config)
        text = self.tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        return {"text": text}

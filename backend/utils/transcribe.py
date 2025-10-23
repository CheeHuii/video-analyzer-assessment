"""
Local audio transcription using Faster-Whisper (fully offline).
Outputs segment-level text with confidence and timestamps.
"""

from faster_whisper import WhisperModel
from typing import List, Dict
import math

def map_confidence(avg_logprob: float) -> float:
    """Map avg_logprob (usually between -1.0 and -10.0) to [0,1] confidence."""
    if avg_logprob is None:
        return 1.0
    low, high = -10.0, 0.0
    val = (avg_logprob - low) / (high - low)
    return max(0.0, min(1.0, val))

def transcribe_audio(audio_path: str, model_size: str = "small", device: str = "cpu") -> List[Dict]:
    """
    Transcribe a local WAV file and return segments as list of dicts:
    [
      {"start": float, "end": float, "text": str, "confidence": float}
    ]
    """
    model = WhisperModel(model_size, device=device, compute_type="int8" if device == "cpu" else "float16")

    segments, _ = model.transcribe(audio_path, beam_size=5)

    results = []
    for seg in segments:
        results.append({
            "start": float(seg.start),
            "end": float(seg.end),
            "text": seg.text.strip(),
            "confidence": map_confidence(seg.avg_logprob)
        })
    return results

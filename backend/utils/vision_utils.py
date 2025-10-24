"""
Local visual analysis utilities:
- Object detection (OpenVINO + YOLOv8 ONNX)
- OCR (EasyOCR)
- Simple graph/plot detection
"""

import cv2
import numpy as np
import easyocr
from openvino.runtime import Core
from pathlib import Path
from typing import List, Dict
import json

# ---------- Object Detection ----------
def load_openvino_yolo(model_path: str):
    ie = Core()
    available_devices = ie.available_devices

    # Use GPU if available, otherwise CPU
    target_device = "AUTO" if "GPU" in available_devices else "CPU"
    compiled_model = ie.compile_model(model_path, target_device)

    input_layer = compiled_model.input(0)
    output_layer = compiled_model.output(0)
    return compiled_model, input_layer, output_layer

def detect_objects_yolo(compiled_model, input_layer, output_layer, frame: np.ndarray, conf_thresh=0.4):
    # Resize + normalize
    img = cv2.resize(frame, (640, 640))
    img = img.transpose(2, 0, 1)[None] / 255.0
    pred = compiled_model([img])[output_layer]
    pred = np.squeeze(pred)

    detections = []
    for det in pred:
        conf = det[4]
        if conf < conf_thresh:
            continue
        cls = int(det[5])
        x, y, w, h = det[:4]
        detections.append({
            "class_id": cls,
            "confidence": float(conf),
            "bbox": [float(x), float(y), float(w), float(h)]
        })
    return detections

# ---------- OCR ----------
_reader = None
def ocr_text(frame: np.ndarray):
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(['en'], gpu=False)
    result = _reader.readtext(frame)
    texts = []
    for (bbox, text, conf) in result:
        texts.append({"text": text, "confidence": float(conf), "bbox": bbox})
    return texts

# ---------- Graph / Chart Detection ----------
def detect_graphs(frame: np.ndarray):
    """
    Heuristic: detect chart-like regions (many lines, axes).
    Returns list of cropped graph images.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 100, 200)
    contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    graphs = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w > 150 and h > 150 and w/h < 3 and h/w < 3:
            roi = frame[y:y+h, x:x+w]
            graphs.append({"bbox": [x, y, w, h], "image": roi})
    return graphs

def intersection_over_union(b1, b2):
    x1, y1, w1, h1 = b1
    x2, y2, w2, h2 = b2
    xa = max(x1, x2)
    ya = max(y1, y2)
    xb = min(x1 + w1, x2 + w2)
    yb = min(y1 + h1, y2 + h2)
    inter = max(0, xb - xa) * max(0, yb - ya)
    union = w1 * h1 + w2 * h2 - inter
    return inter / union if union > 0 else 0


# ---------- Main entry ----------
def analyze_frame(frame_path, timestamp, model_info, output_dir, prev_graphs=None):
    compiled_model, input_layer, output_layer = model_info

    frame = cv2.imread(frame_path)
    objects = detect_objects_yolo(compiled_model, input_layer, output_layer, frame)
    # texts = ocr_text(frame)
    texts = []
    # graphs = detect_graphs(frame)
    graphs = []

    graphs_out = []
    for i, g in enumerate(graphs):
        bbox = g["bbox"]
        # skip if highly overlapping with a previous graph
        if prev_graphs:
            for pg in prev_graphs:
                iou = intersection_over_union(bbox, pg["bbox"])
                if iou > 0.8:
                    break
            else:
                # only add if not break
                crop_path = output_dir / f"graph_{int(timestamp)}_{i}.jpg"
                cv2.imwrite(str(crop_path), g["image"])
                graphs_out.append({"timestamp": timestamp, "bbox": bbox, "file": str(crop_path)})
        else:
            crop_path = output_dir / f"graph_{int(timestamp)}_{i}.jpg"
            cv2.imwrite(str(crop_path), g["image"])
            graphs_out.append({"timestamp": timestamp, "bbox": bbox, "file": str(crop_path)})
    return {"timestamp": timestamp, "graphs": graphs_out, "objects": objects, "texts": texts}

def _to_serializable(obj):
    # numpy scalars
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.bool_ ,)):
        return bool(obj)
    # numpy arrays
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    # bytes -> string
    if isinstance(obj, (bytes, bytearray)):
        try:
            return obj.decode("utf-8")
        except Exception:
            return list(obj)
    # fallback: let json raise for unsupported types
    raise TypeError(f"Type {type(obj)} not serializable")

def process_video_frames(frames_dir: str, model_path: str, out_dir: str):
    frames = sorted(list(Path(frames_dir).glob("*.jpg")) + list(Path(frames_dir).glob("*.png")))
    model_info = load_openvino_yolo(model_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_objects, all_ocr, all_graphs = [], [], []
    prev_graphs = []
    for i, f in enumerate(frames):
        timestamp = i  # approximate, 1 frame = 1 sec if sampled that way
        result = analyze_frame(str(f), timestamp, model_info, out_dir, prev_graphs)
        prev_graphs.extend(result["graphs"])
        for o in result["objects"]:
            o["timestamp"] = timestamp
        for t in result["texts"]:
            t["timestamp"] = timestamp
        all_objects.extend(result["objects"])
        all_ocr.extend(result["texts"])
        all_graphs.extend(result["graphs"])

    # Save results
    (out_dir / "objects.json").write_text(json.dumps(all_objects, indent=2))
    ocr_path = out_dir / "ocr.json"
    ocr_json = json.dumps(all_ocr, indent=2, default=_to_serializable, ensure_ascii=False)
    ocr_path.write_text(ocr_json, encoding="utf-8")
    (out_dir / "graphs.json").write_text(json.dumps(all_graphs, indent=2))

    return len(frames)

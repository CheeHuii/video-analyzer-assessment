# backend/ingest.py
import os
import shutil
import subprocess
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

# Optional: if you want Python bindings to ffmpeg (not required here)
# import ffmpeg

# Optional scene detection library (more robust than ffmpeg scene filter)
# try:
#     from scenedetect import VideoManager, SceneManager
#     from scenedetect.detectors import ContentDetector
#     PYSCT_AVAILABLE = True
# except Exception:
#     PYSCT_AVAILABLE = False


def run_cmd(cmd: List[str], cwd: Optional[str] = None) -> str:
    """Run a command and return stdout. Raise subprocess.CalledProcessError on error."""
    # Use text=True for Python3.6+ to get str output
    print("RUN:", " ".join(cmd))
    out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, cwd=cwd, text=True)
    return out


def ffprobe_metadata(video_path: str) -> Dict[str, Any]:
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        video_path,
    ]
    out = run_cmd(cmd)
    return json.loads(out)


def extract_audio(video_path: str, out_wav: str, sample_rate: int = 16000):
    """
    Extract audio as WAV, mono, given sample rate.
    """
    cmd = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-vn",  # no video
        "-acodec", "pcm_s16le",
        "-ar", str(sample_rate),
        "-ac", "1",
        out_wav,
    ]
    run_cmd(cmd)


def extract_frames(video_path: str, frames_dir: str, sample_ms: int = 500, scale: Optional[str] = None):
    """
    Extract frames every sample_ms milliseconds.
    Saves PNGs as frames/frame_000001.png ...
    scale: optional ffmpeg scale string, e.g. "640:-1" to preserve aspect ratio
    """
    Path(frames_dir).mkdir(parents=True, exist_ok=True)
    # fps = frames per second = 1000 / sample_ms
    if sample_ms <= 0:
        raise ValueError("sample_ms must be > 0")
    fps_val = 1000.0 / sample_ms
    vf = f"fps={fps_val}"
    if scale:
        vf += f",scale={scale}"
    cmd = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-vf", vf,
        "-q:v", "2",
        os.path.join(frames_dir, "frame_%06d.png"),
    ]
    run_cmd(cmd)


# def detect_scenes_pyscenedetect(video_path: str, threshold: float = 30.0) -> List[Dict[str, Any]]:
#     """
#     Use PySceneDetect ContentDetector to detect boundaries.
#     Returns list of scenes as dicts: {start_time_s, end_time_s}
#     threshold: sensitivity parameter (higher => fewer cuts)
#     """
#     if not PYSCT_AVAILABLE:
#         raise RuntimeError("PySceneDetect is not installed. pip install scenedetect")

#     video_manager = VideoManager([video_path])
#     scene_manager = SceneManager()
#     scene_manager.add_detector(ContentDetector(threshold=threshold))
#     base_timecode = video_manager.get_base_timecode()

#     try:
#         video_manager.start()
#         scene_manager.detect_scenes(frame_source=video_manager)
#         scene_list = scene_manager.get_scene_list(base_timecode)
#         scenes = []
#         for (start, end) in scene_list:
#             scenes.append({
#                 "start_time_s": start.get_seconds(),
#                 "end_time_s": end.get_seconds()
#             })
#         return scenes
#     finally:
#         video_manager.release()


def ingest_video(src_path: str, video_id: Optional[str] = None, sample_ms: int = 500, do_scene_detect: bool = False) -> Dict[str, Any]:
    """
    Ingest video:
      - copy mp4 into data/videos/{video_id}/raw.mp4
      - extract audio -> audio.wav
      - extract frames into frames/
      - write meta.json with ffprobe metadata + derived fields
    Returns metadata dict.
    """
    if not video_id:
        video_id = str(uuid.uuid4())[:8]
    base_dir = Path("data") / "videos" / video_id
    base_dir.mkdir(parents=True, exist_ok=True)

    # copy raw file
    raw_dest = base_dir / "raw.mp4"
    shutil.copy2(src_path, raw_dest)
    print(f"Copied raw video to {raw_dest}")

    # get ffprobe metadata
    meta = ffprobe_metadata(str(raw_dest))
    # compute some derived values safely
    format_info = meta.get("format", {})
    streams = meta.get("streams", [])
    video_stream = None
    audio_stream = None
    for s in streams:
        if s.get("codec_type") == "video":
            video_stream = s
        elif s.get("codec_type") == "audio":
            audio_stream = s

    duration = float(format_info.get("duration", 0.0))
    width = int(video_stream.get("width")) if video_stream and video_stream.get("width") else None
    height = int(video_stream.get("height")) if video_stream and video_stream.get("height") else None
    fps = None
    if video_stream:
        # try parse r_frame_rate like "30000/1001"
        rfr = video_stream.get("r_frame_rate") or video_stream.get("avg_frame_rate")
        if rfr and rfr != "0/0":
            try:
                num, den = rfr.split("/")
                fps = float(num) / float(den)
            except Exception:
                fps = None

    # extract audio
    audio_out = base_dir / "audio.wav"
    extract_audio(str(raw_dest), str(audio_out), sample_rate=16000)

    # extract frames
    frames_dir = base_dir / "frames"
    extract_frames(str(raw_dest), str(frames_dir), sample_ms=sample_ms, scale=None)

    # optional scene detection
    # scenes = []
    # if do_scene_detect:
    #     if PYSCT_AVAILABLE:
    #         try:
    #             scenes = detect_scenes_pyscenedetect(str(raw_dest))
    #         except Exception as e:
    #             print("Scene detection (PySceneDetect) failed:", e)
    #             scenes = []
    #     else:
    #         print("PySceneDetect not installed; skipping scene detection. Install with: pip install scenedetect")

    # build meta
    meta_out = {
        "video_id": video_id,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "src_filename": os.path.basename(src_path),
        "raw_path": str(raw_dest),
        "audio_path": str(audio_out),
        "frames_dir": str(frames_dir),
        "duration_s": duration,
        "width": width,
        "height": height,
        "fps": fps,
        "format": format_info.get("format_name"),
        "size_bytes": int(format_info.get("size", 0)) if format_info.get("size") else None,
        "video_stream": video_stream,
        "audio_stream": audio_stream,
        # "scenes": scenes,
    }

    # write meta.json
    meta_json_path = base_dir / "meta.json"
    with open(meta_json_path, "w", encoding="utf-8") as f:
        json.dump(meta_out, f, indent=2)

    print(f"Metadata written to {meta_json_path}")
    return meta_out


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ingest local MP4 into data/videos/{video_id}/")
    parser.add_argument("src", help="source MP4 path")
    parser.add_argument("--id", help="optional video id (folder name)")
    parser.add_argument("--sample-ms", type=int, default=500, help="sample frame every N milliseconds")
    parser.add_argument("--scenes", action="store_true", help="run scene detection (requires scenedetect)")
    args = parser.parse_args()

    meta = ingest_video(args.src, video_id=args.id, sample_ms=args.sample_ms, do_scene_detect=args.scenes)
    print("Ingest done:", meta["video_id"])

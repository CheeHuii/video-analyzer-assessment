# backend/agents/transcription_agent.py
import asyncio
import json
import logging
import os
from pathlib import Path
from datetime import datetime

from ..utils.transcribe import transcribe_audio
from backend.agents.agent_base import AgentBase  # from your Step 3
from backend.protos import common_pb2 as common_pb

logger = logging.getLogger("TranscriptionAgent")
logging.basicConfig(level=logging.INFO)


class TranscriptionAgent(AgentBase):
    def __init__(self, name="transcription-agent", server_addr="localhost:50051",
                 model_size="small", device="cpu", confidence_threshold=0.6):
        super().__init__(name=name, a_type=common_pb.AgentType.AGENT_TRANSCRIPTION, server_addr=server_addr)
        self.model_size = model_size
        self.device = device
        self.conf_threshold = confidence_threshold
        self._cap_token = ""

    async def handle_command(self, cmd: str):
        logger.info(f"[TranscriptionAgent] Received: {cmd}")
        if not cmd.startswith("run-task:"):
            return

        _, task_id, input_path = cmd.split(":", 2)
        await self._process_task(task_id, input_path)

    async def _process_task(self, task_id: str, input_path: str):
        audio_path = input_path
        if input_path.endswith("meta.json") and os.path.exists(input_path):
            with open(input_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            audio_path = meta.get("audio_path")

        if not audio_path or not os.path.exists(audio_path):
            self._cap_token = f"result:{task_id}:ERROR_NO_AUDIO"
            return

        base_dir = Path(audio_path).parent
        self._cap_token = f"progress:{task_id}:10"

        loop = asyncio.get_running_loop()
        segments = await loop.run_in_executor(None, lambda: transcribe_audio(audio_path, self.model_size, self.device))

        self._cap_token = f"progress:{task_id}:80"

        # identify low confidence segments
        low_conf = [s for s in segments if s["confidence"] < self.conf_threshold]

        # write transcript file
        out_path = base_dir / f"transcript_{task_id}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({
                "task_id": task_id,
                "audio_path": str(audio_path),
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "segments": segments,
                "low_confidence_segments": low_conf
            }, f, indent=2, ensure_ascii=False)

        if low_conf:
            clar_path = base_dir / f"clarify_requests_{task_id}.json"
            with open(clar_path, "w", encoding="utf-8") as f:
                json.dump(low_conf, f, indent=2, ensure_ascii=False)

        self._cap_token = f"result:{task_id}:{str(out_path)}"
        await asyncio.sleep(1.0)
        self._cap_token = ""

# backend/agents/vision_agent.py
import asyncio
import logging
from pathlib import Path

from backend.agents.agent_base import AgentBase
from backend.protos import common_pb2 as common_pb
from ..utils.vision_utils import process_video_frames

logger = logging.getLogger("VisionAgent")
logging.basicConfig(level=logging.INFO)


class VisionAgent(AgentBase):
    def __init__(self, name="vision-agent", server_addr="localhost:50051",
                 model_path="backend/models/yolov8n.onnx"):
        super().__init__(name=name, a_type=common_pb.AgentType.AGENT_VISION, server_addr=server_addr)
        self.model_path = model_path
        self._cap_token = ""

    async def handle_command(self, cmd: str):
        logger.info(f"[VisionAgent] Received: {cmd}")
        if not cmd.startswith("run-task:"):
            return

        _, task_id, input_dir = cmd.split(":", 2)
        await self._process_task(task_id, input_dir)

    async def _process_task(self, task_id: str, input_dir: str):
        frames_dir = Path(input_dir) / "frames"
        out_dir = Path(input_dir)
        if not frames_dir.exists():
            logger.error(f"No frames directory found at {frames_dir}")
            self._cap_token = f"result:{task_id}:ERROR_NO_FRAMES"
            return

        self._cap_token = f"progress:{task_id}:10"
        await asyncio.sleep(0.5)

        loop = asyncio.get_running_loop()
        frame_count = await loop.run_in_executor(None,
            lambda: process_video_frames(str(frames_dir), self.model_path, str(out_dir / "graphs")))

        self._cap_token = f"result:{task_id}:{str(out_dir)}"
        logger.info(f"Vision analysis done for {frame_count} frames at {out_dir}")
        await asyncio.sleep(1)
        self._cap_token = ""

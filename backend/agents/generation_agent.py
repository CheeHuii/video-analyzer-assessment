# backend/agents/generation_agent.py
import asyncio
import logging
from pathlib import Path
from backend.agents.agent_base import AgentBase
from backend.protos import common_pb2 as common_pb
from ..utils.generation_utils import generate_pdf, generate_pptx

logger = logging.getLogger("GenerationAgent")
logging.basicConfig(level=logging.INFO)

class GenerationAgent(AgentBase):
    def __init__(self, name="generation-agent", server_addr="localhost:50051"):
        super().__init__(name=name, a_type=common_pb.AgentType.AGENT_GENERATION, server_addr=server_addr)
        self._cap_token = ""

    async def handle_command(self, cmd: str):
        logger.info(f"[GenerationAgent] Received: {cmd}")
        if not cmd.startswith("run-task:"):
            return
        _, task_id, input_uri = cmd.split(":", 2)
        await self._process_task(task_id, input_uri)

    async def _process_task(self, task_id: str, input_uri: str):
        """
        input_uri can be either:
         - path to meta.json (preferred) -> derive video_dir
         - path to the video_dir itself
        """
        if input_uri.endswith("meta.json"):
            video_dir = Path(input_uri).parent
        else:
            video_dir = Path(input_uri)

        transcript_candidates = list(video_dir.glob("transcript_*.json"))
        if not transcript_candidates:
            self._cap_token = f"result:{task_id}:ERROR_NO_TRANSCRIPT"
            return

        # choose the transcript that matches this task_id if present
        transcript_path = None
        for t in transcript_candidates:
            if task_id in t.name:
                transcript_path = t
                break
        if not transcript_path:
            transcript_path = transcript_candidates[0]

        # PDF
        self._cap_token = f"progress:{task_id}:10"
        pdf_out = video_dir / f"{task_id}_summary.pdf"
        generate_pdf(str(video_dir), str(transcript_path), str(pdf_out))
        self._cap_token = f"progress:{task_id}:60"

        # PPTX
        ppt_out = video_dir / f"{task_id}_slides.pptx"
        generate_pptx(str(video_dir), str(transcript_path), str(ppt_out))
        self._cap_token = f"progress:{task_id}:95"

        # done
        self._cap_token = f"result:{task_id}:{str(pdf_out)}|{str(ppt_out)}"
        await asyncio.sleep(1.0)
        self._cap_token = ""

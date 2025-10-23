# backend/agents/dummy_agent.py
import asyncio
import logging
import os
from datetime import datetime, timezone

from backend.protos import common_pb2 as common_pb

from backend.agents.agent_base import AgentBase

logger = logging.getLogger("DummyAgent")
logging.basicConfig(level=logging.INFO)


class DummyAgent(AgentBase):
    def __init__(self, name="dummy-transcriber", server_addr="localhost:50051"):
        super().__init__(name=name, a_type=common_pb.AgentType.AGENT_TRANSCRIPTION, server_addr=server_addr)
        # internal state for which task we're executing
        self._current_task = None
        self._cap_token = ""  # used to send progress tokens in heartbeat

    async def handle_command(self, cmd: str):
        logger.info(f"Handling command: {cmd}")
        if cmd.startswith("run-task:"):
            parts = cmd.split(":", 2)
            if len(parts) >= 3:
                task_id = parts[1]
                input_uri = parts[2]
            else:
                logger.warning("Malformed run-task command")
                return
            await self._simulate_task(task_id, input_uri)

    async def _simulate_task(self, task_id, input_uri):
        logger.info(f"Simulating task {task_id} on input {input_uri}")
        self._current_task = task_id
        # simulate progress updates at 20% intervals
        for p in range(0, 101, 20):
            # set capability token to tell server our progress
            self._cap_token = f"progress:{task_id}:{p}"
            await asyncio.sleep(1.0)  # wait 1 sec between updates
        # write a fake output file
        out_path = os.path.abspath(f"./fake_output_{task_id}.txt")
        with open(out_path, "w") as f:
            f.write(f"Fake output for {task_id}\ninput: {input_uri}\n")
        # report result token
        self._cap_token = f"result:{task_id}:{out_path}"
        # done (keep reporting final status for a brief moment)
        await asyncio.sleep(1.0)
        self._cap_token = ""

async def main():
    agent = DummyAgent()
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())

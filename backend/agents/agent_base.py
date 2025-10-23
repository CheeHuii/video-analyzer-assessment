# backend/agents/agent_base.py
import asyncio
import logging
import uuid
from datetime import datetime, timezone

import grpc
from google.protobuf.timestamp_pb2 import Timestamp
from backend.protos import agent_manager_pb2 as mgr_pb2
from backend.protos import agent_manager_pb2_grpc as mgr_grpc
from backend.protos import common_pb2 as common_pb

logger = logging.getLogger("AgentBase")


class AgentBase:
    def __init__(self, name: str, a_type: common_pb.AgentType, server_addr="localhost:50051"):
        self.name = name
        self.type = a_type
        self.server_addr = server_addr
        self.id = str(uuid.uuid4())
        self._channel = grpc.aio.insecure_channel(self.server_addr)
        self._stub = mgr_grpc.AgentManagerStub(self._channel)
        self._task = None
        self._stop = False

    async def register(self):
        info = common_pb.AgentInfo(
            id=self.id,
            name=self.name,
            type=self.type,
            version="0.1",
            capabilities="",
        )
        resp = await self._stub.RegisterAgent(info)
        logger.info(f"Registered with server: {resp.assigned_id} ok={resp.ok}")

    async def heartbeat_loop(self):
        """
        Open heartbeat bidi stream: send periodic AgentInfo and read HeartbeatResponse commands from server.
        """
        async def outgoing():
            while not self._stop:
                info = common_pb.AgentInfo(
                    id=self.id,
                    name=self.name,
                    type=self.type,
                    version="0.1",
                    capabilities=self._capabilities_for_heartbeat(),
                )
                hb = mgr_pb2.HeartbeatRequest(agent=info)
                yield hb
                await asyncio.sleep(1.0)  # tick interval

        # Start bidi stream
        try:
            async for resp in self._stub.Heartbeat(outgoing()):
                # inspect commands
                if resp.commands:
                    for cmd in resp.commands:
                        # process commands (we expect "run-task:taskid:input_uri")
                        await self.handle_command(cmd)
        except grpc.RpcError as e:
            logger.info(f"Heartbeat RPC ended: {e}")

    def _capabilities_for_heartbeat(self):
        # override to include progress tokens if needed
        return getattr(self, "_cap_token", "")

    async def handle_command(self, cmd: str):
        # override in subclass
        logger.info(f"Received command: {cmd}")

    async def run(self):
        await self.register()
        await self.heartbeat_loop()

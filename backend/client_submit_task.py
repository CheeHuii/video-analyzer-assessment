# backend/client_submit_task.py
import asyncio
import uuid
import logging

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

from backend.protos import agent_manager_pb2 as mgr_pb2
from backend.protos import agent_manager_pb2_grpc as mgr_grpc
from backend.protos import common_pb2 as common_pb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("client")


async def submit_and_watch():
    channel = grpc.aio.insecure_channel("localhost:50051")
    stub = mgr_grpc.AgentManagerStub(channel)

    # create task request
    task_id = str(uuid.uuid4())
    file_ref = common_pb.FileRef(uri="C:/tmp/example.mp4", mime="video/mp4", size_bytes=12345)
    req = common_pb.TaskRequest(task_id=task_id, agent_type_hint="AGENT_TRANSCRIPTION", input=file_ref)
    resp = await stub.AssignTask(req)
    logger.info(f"AssignTask resp: accepted={resp.accepted} agent={resp.assigned_agent_id} message={resp.message}")

    if not resp.accepted:
        print("No agent available")
        return

    # subscribe to progress
    sreq = mgr_pb2.TaskProgressRequest(task_id=task_id, agent_id=resp.assigned_agent_id)
    async for update in stub.StreamProgress(sreq):
        logger.info(f"Progress update: task={update.task_id} status={update.status} percent={update.percent} msg={update.message}")
        if update.status in (common_pb.TaskStatus.TASK_SUCCEEDED, common_pb.TaskStatus.TASK_FAILED):
            break

    await channel.close()

if __name__ == "__main__":
    asyncio.run(submit_and_watch())

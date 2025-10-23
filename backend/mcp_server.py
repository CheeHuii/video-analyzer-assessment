# backend/mcp_server.py
import asyncio
from concurrent import futures
import uuid
import logging
import re
from datetime import datetime, timezone

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

# Import generated stubs (adjust if your stubs live elsewhere)
from backend.protos import agent_manager_pb2 as mgr_pb2
from backend.protos import agent_manager_pb2_grpc as mgr_grpc
from backend.protos import common_pb2 as common_pb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MCPServer")


class MCPServer(mgr_grpc.AgentManagerServicer):
    def __init__(self):
        # agent_id -> AgentInfo
        self.agents = {}
        # agent_id -> asyncio.Queue[str]  (commands to send to agent)
        self.agent_queues = {}
        # task_id -> dict(status, percent, message, assigned_agent)
        self.tasks = {}
        # For notifying StreamProgress watchers: task_id -> list of asyncio.Queue
        self.progress_listeners = {}

        # simple lock
        self._lock = asyncio.Lock()

    # RegisterAgent(genai.common.AgentInfo) => RegisterResponse
    async def RegisterAgent(self, request, context):
        agent_id = request.id or str(uuid.uuid4())
        async with self._lock:
            self.agents[agent_id] = request
            # ensure queue exists
            if agent_id not in self.agent_queues:
                self.agent_queues[agent_id] = asyncio.Queue()
        logger.info(f"Agent registered: {agent_id} name={request.name} type={request.type}")
        return mgr_pb2.RegisterResponse(ok=True, assigned_id=agent_id, message="Registered")

    # Heartbeat bidi stream: agent sends HeartbeatRequest; server replies with HeartbeatResponse(s)
    async def Heartbeat(self, request_iterator, context):
        # The agent should send an initial heartbeat message with AgentInfo (id included).
        agent_id = None
        queue = None
        try:
            async for hb_req in request_iterator:
                agent = hb_req.agent
                agent_id = agent.id
                now = Timestamp()
                now.FromDatetime(datetime.now(timezone.utc))
                # store / update agent info
                async with self._lock:
                    self.agents[agent_id] = agent
                # parse capability-borne progress messages (we use simple patterns)
                # expected patterns inside agent.capabilities:
                # "progress:<task_id>:<percent>"
                # "result:<task_id>:<output_uri>"
                if agent.capabilities:
                    # scan tokens
                    tokens = agent.capabilities.split(";")
                    for t in tokens:
                        t = t.strip()
                        if t.startswith("progress:"):
                            # progress:task123:45
                            m = re.match(r"progress:([^:]+):(\d+)", t)
                            if m:
                                task_id = m.group(1)
                                percent = int(m.group(2))
                                await self._update_task_progress(task_id, percent, f"Agent {agent_id} at {percent}%")
                        elif t.startswith("result:"):
                            m = re.match(r"result:([^:]+):(.+)", t)
                            if m:
                                task_id = m.group(1)
                                output = m.group(2)
                                await self._complete_task(task_id, True, output, "")
                # Now produce any queued commands for this agent (non-blocking)
                async with self._lock:
                    queue = self.agent_queues.get(agent_id)
                if queue is None:
                    # create queue for future commands
                    async with self._lock:
                        self.agent_queues[agent_id] = asyncio.Queue()
                        queue = self.agent_queues[agent_id]

                # if there is a command, send it out as a HeartbeatResponse
                try:
                    cmd = queue.get_nowait()
                except asyncio.QueueEmpty:
                    # send an empty response to keep the stream alive
                    yield mgr_pb2.HeartbeatResponse(commands=[])
                else:
                    yield mgr_pb2.HeartbeatResponse(commands=[cmd])
        except grpc.RpcError as e:
            logger.info(f"Heartbeat stream closed for agent {agent_id}: {e}")
        finally:
            logger.info(f"Heartbeat handler exiting for agent {agent_id}")

    # AssignTask(TaskRequest) -> AssignResponse
    async def AssignTask(self, request, context):
        # pick an agent according to agent_type_hint
        task_id = request.task_id or str(uuid.uuid4())
        async with self._lock:
            # find agent with matching type and that has a queue
            selected_agent = None
            for aid, info in self.agents.items():
                if request.agent_type_hint:
                    if info.type == common_pb.AgentType.Value(request.agent_type_hint) if isinstance(request.agent_type_hint, str) else info.type == request.agent_type_hint:
                        selected_agent = aid
                        break
                else:
                    selected_agent = aid
                    break
            if not selected_agent:
                # fail gracefully
                self.tasks[task_id] = {"status": common_pb.TaskStatus.TASK_FAILED, "percent": 0, "message": "No agent available", "agent": None}
                return mgr_pb2.AssignResponse(accepted=False, assigned_agent_id="", message="No agent available")

            # push task into tasks map and into agent's queue
            self.tasks[task_id] = {"status": common_pb.TaskStatus.TASK_QUEUED, "percent": 0, "message": "Queued", "agent": selected_agent}
            cmd = f"run-task:{task_id}:{request.input.uri}"
            await self.agent_queues[selected_agent].put(cmd)
            logger.info(f"Assigned task {task_id} to agent {selected_agent}")
            return mgr_pb2.AssignResponse(accepted=True, assigned_agent_id=selected_agent, message="Assigned")

    # ListAgents(Empty) -> AgentList
    async def ListAgents(self, request, context):
        al = mgr_pb2.AgentList()
        async with self._lock:
            for aid, info in self.agents.items():
                al.agents.append(info)
        return al

    # StreamProgress(TaskProgressRequest) returns stream<ProgressUpdate>
    async def StreamProgress(self, request, context):
        task_id = request.task_id
        # create a dedicated queue for this listener
        q = asyncio.Queue()
        self.progress_listeners.setdefault(task_id, []).append(q)
        logger.info(f"Client subscribed to progress for task {task_id}")
        try:
            # stream until task completed
            while True:
                try:
                    update = await q.get()
                except asyncio.CancelledError:
                    break
                # yield the update
                yield update
                # stop on terminal states
                if update.status in (common_pb.TaskStatus.TASK_SUCCEEDED, common_pb.TaskStatus.TASK_FAILED, common_pb.TaskStatus.TASK_CANCELLED):
                    break
        finally:
            # cleanup listener
            listeners = self.progress_listeners.get(task_id, [])
            if q in listeners:
                listeners.remove(q)
            logger.info(f"Client unsubscribed from progress for task {task_id}")

    # Helpers to update tasks and notify listeners
    async def _update_task_progress(self, task_id, percent, message):
        async with self._lock:
            t = self.tasks.get(task_id)
            if not t:
                # ignore unknown tasks
                return
            t["status"] = common_pb.TaskStatus.TASK_RUNNING
            t["percent"] = percent
            t["message"] = message
        # notify listeners
        update = common_pb.ProgressUpdate(
            task_id=task_id,
            status=common_pb.TaskStatus.TASK_RUNNING,
            percent=percent,
            message=message,
            updated_at=Timestamp()
        )
        update.updated_at.GetCurrentTime()
        listeners = self.progress_listeners.get(task_id, [])
        for q in listeners:
            await q.put(update)

    async def _complete_task(self, task_id, success: bool, output_uri: str, error_message: str):
        async with self._lock:
            t = self.tasks.get(task_id)
            if not t:
                return
            t["status"] = common_pb.TaskStatus.TASK_SUCCEEDED if success else common_pb.TaskStatus.TASK_FAILED
            t["percent"] = 100
            t["message"] = "Completed" if success else "Failed"
        # notify listeners
        update = common_pb.ProgressUpdate(
            task_id=task_id,
            status=t["status"],
            percent=100,
            message=t["message"],
            updated_at=Timestamp()
        )
        update.updated_at.GetCurrentTime()
        listeners = self.progress_listeners.get(task_id, [])
        for q in listeners:
            await q.put(update)


async def serve_async(host="[::]", port=50051):
    server = grpc.aio.server()
    mcp = MCPServer()
    mgr_grpc.add_AgentManagerServicer_to_server(mcp, server)
    server.add_insecure_port(f"{host}:{port}")
    await server.start()
    logger.info(f"MCP server started on {host}:{port}")
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve_async())

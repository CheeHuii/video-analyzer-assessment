import importlib
import sys

_pkg = __name__  # "backend.protos"

# load in a safe order: import common modules first so other generated files that do
# "import common_pb2" (absolute) will find them after we register the short names.
_MODULES = [
    "common_pb2",
    "common_pb2_grpc",
    "agent_manager_pb2",
    "agent_manager_pb2_grpc",
    "chat_pb2",
    "chat_pb2_grpc",
    "generation_pb2",
    "generation_pb2_grpc",
    "transcription_pb2",
    "transcription_pb2_grpc",
    "vision_pb2",
    "vision_pb2_grpc",
]

for short in _MODULES:
    full_name = f"{_pkg}.{short}"
    # import the module under its full package name
    mod = importlib.import_module(full_name)
    # expose it as package attribute
    globals()[short] = mod
    # register the module under its short top-level name so absolute imports in generated code succeed
    sys.modules[short] = mod

# optional convenience exports (adjust if you want fewer symbols)
from .agent_manager_pb2 import *
from .agent_manager_pb2_grpc import *
from .chat_pb2 import *
from .chat_pb2_grpc import *
from .common_pb2 import *
from .common_pb2_grpc import *
from .generation_pb2 import *
from .generation_pb2_grpc import *
from .transcription_pb2 import *
from .transcription_pb2_grpc import *
from .vision_pb2 import *
from .vision_pb2_grpc import *
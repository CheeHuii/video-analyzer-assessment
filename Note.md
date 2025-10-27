# Functional requirement:

## Working according to requirements:
Allow user to select and upload local .mp4 files

Natural language interaction to process and query video content.
-   Transcribe the video
-   Create powerpoint/pdf with the key points of video
-   Object are shown in the video (partially)
-   Are there any graph in the video? If yes, describe them. (partially)

Maintain persistent chat history, accessible for reading even after app restart (artifacts)

## What could be achieved with more time:
-   Summarizing discussion so far and generate a PDF.
-   There is no valid agent with this purpose right now, however, SQLite db, and history of artifact metadata is available, able to complete with more time.
Human-in-the-loop claritication:
-   Does not have this feature for now, but also, confidence level is there, completing it should be possible too.
Persistent chat history:
-   Chat history is stored in DB, can be retrieved anytime by querying chat_history.db, but not engineered to display in chat panel yet.
-   All previous generated file from video however, may be retrieved easily with artifact panel.

## Challenges:
-   OpenVINO only detect Intel GPUs, can cause very slow inferencing, to infer Nvidia GPU might need extra steps to enable CUDA 
-   Due to local constraint, no good enough model can be used, however, improved from facebook/opt-350m to TinyLlama/TinyLlama-1.1B-Chat-v1.0, generally llama3.2 is a good choice, but for now lets leave it as it is
-   MCP, gRPC, tauri are all new to me, for more complex task like building the tauri apps require the help of AI tools.

## Future Enhancement:
-   Transcribed output should be in a more convenient format, like a word file, instead of a json
-   Yolov8n used for vision agent, dont do good in graph detection, have better specified model to do it.
-   Generated pdf/pptx just the text of the transcribed json, this feature can be improved with proper model.
-   Add licenses for library/models used
-   Common resource pool for db instance control
-   Limit file format that is available to upload.
-   Error notification on UI, prompt 
-   Get a more reliable cloud-based datastore
-   Improves UI, shows list of graphs generated too.
-   Introduce sessions, prevent lost in the middle problem.

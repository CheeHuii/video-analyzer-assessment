Challenges:
OpenVINO only detect Intel GPUs, having only Nvidia GPU can cause very slow inferencing
Due to local constraint, no good enough model can be used, however, improved from facebook/opt-350m to TinyLlama/TinyLlama-1.1B-Chat-v1.0, generally llama3.2 is a good choice, but for now lets leave it as it is

Enhancement:
yolov8n used for vision agent, dont do good in graph detection, have better specified model to do it.
to add license, which is not done for now
I could create a common resource pool for db instance control

Get a more reliable datastore
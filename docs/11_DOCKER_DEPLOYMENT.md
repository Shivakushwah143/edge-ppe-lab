# 11 — Docker Deployment

## Learning order

Do **not** begin with Docker. First run the inference API directly on Ubuntu and understand process, environment, port, logs, and model path. Then containerize the already-understood runtime.

## Image vs container

A Docker image is an immutable filesystem/config template. A container is a running (or stopped) process instance created from an image. Deleting a container does not delete the image; rebuilding an image does not magically replace an already-running container.

## Required exercises

- `docker build` — create the application image.
- `docker run` — start one container with explicit port and required environment/config.
- `docker ps` — see running containers.
- `docker ps -a` — see exited containers too.
- `docker logs` — inspect application stdout/stderr.
- `docker inspect` — inspect runtime config, mounts, env metadata, network settings, exit code.
- `docker stats` — inspect container CPU/RAM usage.
- `docker exec` — enter a running container for controlled diagnostics.
- `docker stop` — graceful stop.

## Image tagging

Use immutable, traceable tags for release candidates, such as a Git SHA or explicit release version. Do not depend on `latest` as proof of what is deployed.

A useful deployment identity connects:

`Git SHA + registered model version + ONNX SHA-256 + Docker image tag`

## Model artifact strategy

For the lab, choose one clearly documented strategy:

1. Bake a validated ONNX model into an image built for a specific model version, **or**
2. Mount/fetch an immutable validated model artifact by concrete identity at startup.

The simplest implementation should win. Whichever is chosen, `/model-info` must expose the concrete model identity.

## Docker failure lab

When a container exits:

1. `docker ps -a`
2. note exit status
3. `docker logs <container>`
4. `docker inspect <container>`
5. verify env/model path/mount/port configuration
6. fix the root cause
7. recreate container
8. `curl` health/readiness/model-info

## Why Docker does not replace Linux

Containers still rely on the Linux kernel's process scheduling, memory, networking, filesystem, permissions/capabilities, and device model. You still need Linux skills to debug real container workloads.

## Future NVIDIA relationship

`Linux → NVIDIA driver → NVIDIA Container Runtime/toolkit → CUDA/TensorRT-capable container → optimized model`

A container cannot provide a physical GPU or host driver by itself. The host must expose compatible NVIDIA capabilities to the container.

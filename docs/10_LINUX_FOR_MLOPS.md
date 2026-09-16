# 10 — Linux for MLOps

This is not a generic Linux tutorial. Every command below is tied to operating EdgePPE Lab.

## Filesystem mental model

- `~/projects/edge-ppe-lab`: source, virtual environment, local working files during development.
- `/opt/edge-ppe`: a realistic location for deployed application/model assets in a traditional host deployment.
- `/etc/edge-ppe`: a realistic location for host-level service configuration/environment files.
- `/var/log`: common host log location, although systemd services should normally be inspected through the journal.
- `/tmp`: temporary files only; never the durable model registry or trusted deployment location.

## Navigation and inspection

| Command | EdgePPE use |
|---|---|
| `pwd` | confirm which deployment directory you are in before destructive commands |
| `ls -lah` | inspect checkpoint/model/config presence and hidden files |
| `cd` | move between repo, artifacts, and deployment directories |
| `mkdir -p` | create controlled project/deployment directories |
| `cp` | copy a validated artifact into a release directory |
| `mv` | rename/move artifacts carefully |
| `rm` | remove disposable files; dangerous for model assets |
| `find` | locate `model.onnx` when configured path is wrong |
| `grep` | search logs/config for model version, error, port, env key |
| `cat` | inspect small config/status files |
| `less` | inspect long logs/reports safely |
| `head` / `tail` | sample beginning/end of logs; `tail -f` follows live logs |

## Permissions and identity

Use `whoami`, `id`, `groups`, `ls -l`, `chmod`, `chown`, and `sudo` to answer: **which user is the service running as, and can that user read the model?**

Production habit: do not “fix” permission errors with `chmod 777`. Identify the intended service user/group and grant only needed read/execute permissions.

## Processes

- `ps aux | grep uvicorn` — locate a manual service process.
- `top` / `htop` — observe CPU and memory pressure.
- `kill <pid>` — request termination.
- `pkill` — broad process-name termination; use cautiously because it can kill unrelated processes.

A process is the running instance of your program. A source file and a Docker image are not processes.

## CPU and memory

- `free -h` — host memory availability.
- `lscpu` — CPU architecture/core details relevant to inference capacity.
- `top` — process-level CPU/memory behavior.

When latency rises, correlate application latency metrics with resource observations before blaming the model.

## Storage

- `df -h` — filesystem free capacity.
- `du -sh <path>` — which directory consumes storage.
- `lsblk` — block device layout.

ML artifacts and Docker layers can consume disk silently over time. “No space left on device” can look like an application failure.

## Networking

- `ip addr` — interface/IP information.
- `ping` — basic network reachability when ICMP is available; not an HTTP health check.
- `curl http://127.0.0.1:8000/health` — application-level proof.
- `ss -lntp` — which TCP ports are listening and, with sufficient permission, which process owns them.

### `localhost` vs `0.0.0.0`

`127.0.0.1`/localhost is loopback: accessible from the same network namespace. `0.0.0.0` is a bind address meaning “listen on all available interfaces”; it is not a destination clients normally browse to. In containers or remote hosts, binding only to localhost can make a healthy process unreachable externally.

## Environment

- `env` — inspect current environment.
- `echo "$MODEL_URI"` — inspect a specific variable.
- `export MODEL_URI=...` — set a variable in the current shell/session.
- `echo "$PATH"` — understand executable lookup.

Configuration must be explicit. A missing model URI or MLflow URI should create a clear startup failure rather than guessing.

## Logging

Manual process: stdout/stderr in terminal.  
Long-running/manual redirection: use explicit redirection if needed, but keep the setup simple.  
Systemd: `journalctl -u edge-ppe`.  
Docker: `docker logs <container>`.

Logs should include startup configuration summary without secrets, concrete model version, model hash, runtime provider, errors, and request correlation information if implemented.

## Remote operations concepts

SSH gives a shell on a remote Linux machine. SCP transfers files over SSH. In a future deployment, these concepts matter for inspecting a Linux inference node, but production release automation should avoid ad-hoc copying of unverified models.

## Destructive-command discipline

Before `rm`, `chmod`, `chown`, or killing processes, first prove the target using `pwd`, `ls -l`, `ps`, or `ss`. This habit is part of production engineering, not just Linux syntax.

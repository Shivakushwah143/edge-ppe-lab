# 12 — systemd and Process Management

## Why learn both manual and supervised operation

A foreground `uvicorn` command teaches the raw process. systemd teaches how Linux supervises that process: startup, restart, boot integration, identity, environment, and centralized logs.

## Phase 1 — manual process

The build journey must start the API manually with Uvicorn from the project virtual environment. Then prove:

- PID exists (`ps`)
- expected port listens (`ss -lntp`)
- health endpoint responds (`curl`)
- logs appear in terminal
- Ctrl+C terminates the process

## Phase 2 — verify systemd availability under WSL

Check WSL version on Windows and check whether PID 1/service management is systemd in Ubuntu. On current WSL/Ubuntu installations systemd may already be enabled. If not, the learner may need `/etc/wsl.conf` with:

```ini
[boot]
systemd=true
```

Then WSL must be fully shut down from Windows and restarted before verification. Do not assume systemd is available merely because `systemctl` exists.

## Service unit design

The build phase should create one `edge-ppe.service` unit that defines:
- dedicated working directory
- explicit service user where practical
- executable path from the project/deployment virtual environment
- environment file location
- restart policy appropriate for a crash
- startup after basic network availability if needed

The unit must not embed secrets in the documentation/repository.

## Required commands

- `systemctl start edge-ppe`
- `systemctl status edge-ppe`
- `systemctl restart edge-ppe`
- `systemctl stop edge-ppe`
- `journalctl -u edge-ppe`
- `journalctl -u edge-ppe -f`

## Crash exercise

Break the model path or another required startup condition, restart the unit, then observe:

1. service state becomes failed/restarting according to policy
2. `systemctl status` shows recent failure context
3. journal shows actionable application exception
4. root cause is fixed
5. service restarted
6. `/ready` returns healthy

## Restart behavior

A restart policy can recover from transient process crashes, but it cannot repair a permanently invalid model path. Repeated restart loops are a signal to inspect logs, not proof that supervision is “working fine.”

## Boot startup

Enabling a service at boot is useful on a real Linux host. Under WSL, behavior depends on WSL/systemd lifecycle; the learning objective is service supervision, not pretending WSL is identical to a production VM.

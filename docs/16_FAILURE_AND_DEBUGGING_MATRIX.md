# 16 — Failure and Debugging Matrix

The diagnostic loop is always: **symptom → hypothesis → command → evidence → root cause → fix → verification**.

| # | Scenario | Symptom | Commands / evidence | Typical root cause | Fix | Verification |
|---|---|---|---|---|---|---|
| 1 | Wrong model path | startup/readiness failure; file-not-found log | `pwd`, `ls -lah`, `find ... -name '*.onnx'` | configured path does not match deployment layout | correct path/config | restart; `/ready`; `/model-info` |
| 2 | Missing env variable | startup configuration error | `env`, `echo "$MODEL_URI"`, service/container logs | variable not exported/passed to runtime | define in correct shell/env file/container args | restart; startup logs show resolved non-secret config |
| 3 | Permission denied | model exists but cannot be opened | `ls -l`, `id`, `groups` | service user lacks file/dir read/execute permission | correct owner/group/mode; avoid `777` | run/read as service user; readiness passes |
| 4 | Port already occupied | bind error / address in use | `ss -lntp`, `ps aux` | old process or another service owns port | stop correct process or choose intended port | `ss`; curl health |
| 5 | Inference service crashes | process disappears/restarts | `ps`, `systemctl status`, `journalctl -u edge-ppe` | unhandled startup/runtime error | fix root exception | stable service + ready + prediction |
| 6 | Docker container exits | absent from `docker ps` | `docker ps -a`, `docker logs`, `docker inspect` | bad env/path/command/artifact | correct config/image | container running + curl endpoints |
| 7 | High CPU/RAM | latency spikes, host sluggish | `top`, `free -h`, `docker stats` | large model/input/concurrency or leak | reduce load/model/input; investigate leak | latency/resource baseline restored |
| 8 | Disk space issue | writes/builds/logging fail | `df -h`, `du -sh`, Docker disk inspection | artifacts/images/logs filled disk | remove only verified disposable data; retention | free space + successful operation |
| 9 | MLflow unavailable | model resolution/tracking fails | `curl` MLflow endpoint, process/container logs, `ss` | MLflow server down/wrong URI | restore server or use explicitly verified pinned local artifact path if design allows | registry query works; startup identity correct |
| 10 | Bad model v2 | release health/parity/smoke fails | `/ready`, `/model-info`, logs, parity report, metrics | invalid conversion/config/artifact/behavior | rollback alias + redeploy v1; investigate v2 | `/model-info` v1 + ready + prediction |

## Lab report format for each failure

Create a short incident note with these headings:

### Symptom
What did the user/system observe?

### Hypothesis
What could explain the symptom? List more than one when appropriate.

### Commands
Which Linux/Docker/systemd commands were used and why?

### Evidence
Paste the minimal decisive output: error line, PID, port owner, permission bits, disk %, model version, etc.

### Root cause
State the technical cause, not merely the symptom.

### Fix
What exact configuration/artifact/process action corrected it?

### Verification
Which command/endpoint proves the system recovered?

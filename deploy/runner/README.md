# Self-hosted deployment runner

The `deploy` job in `.github/workflows/cd.yml` runs on a GitHub Actions
**self-hosted runner** installed on this WSL2 machine, because the deployment
target (`~/projects/edge-ppe-lab`) and its Docker daemon are local to this host.

GitHub-hosted runners build and publish the image. The self-hosted runner only
deploys it.

## Why self-hosted

The deployment target is a real machine with a real Docker daemon and the
qualified ONNX artifact on disk. A GitHub-hosted runner cannot reach it, and
copying a 3.4 MB model plus a Docker image into a hosted runner would prove
nothing about the actual deployment.

## Layout

| Path | Purpose |
|---|---|
| `~/actions-runner-edgeppe/` | runner installation (outside the repo, never committed) |
| `~/actions-runner-edgeppe/runner.pid` | pidfile written by `start.sh` |
| `~/actions-runner-edgeppe/runner.log` | runner listener log |
| `~/projects/edge-ppe-lab/var/deployment/` | deployment state + `cd_deploy.log` |

## Install

Registration needs a short-lived **runner registration token**. Either let the
script fetch one, or copy it from
`Settings → Actions → Runners → New self-hosted runner`.

```bash
# option A: let the script request the token (needs a repo-scoped PAT)
GH_TOKEN=<classic PAT with 'repo' scope> ./deploy/runner/install.sh

# option B: paste the token from the GitHub UI
RUNNER_TOKEN=<registration token> ./deploy/runner/install.sh
```

The script downloads the runner, registers it with the label
`edgeppe-deploy`, and prints the runner name and directory. Tokens are used
in-memory only; nothing is written into the repository.

## Run

```bash
./deploy/runner/start.sh     # start in the background
./deploy/runner/stop.sh      # stop (registration kept)
```

`start.sh` runs `./run.sh` under `nohup` as the normal desktop user. It is
deliberately **not** a root systemd service: the deployment job writes into
`~/projects/edge-ppe-lab`, and a root-owned service would create root-owned files
in the user's tree.

Confirm the runner is online:

```bash
# locally
tail -5 ~/actions-runner-edgeppe/runner.log
# on GitHub
# Settings -> Actions -> Runners   (status should be "Idle")
```

## Disable (temporarily)

Stop the process so it cannot pick up jobs. The registration is preserved, so
`start.sh` brings it back with no re-registration:

```bash
./deploy/runner/stop.sh
```

While the runner is offline, a `cd` deployment job stays **queued** rather than
failing. Cancel queued runs from the Actions UI if the runner will be down for a
while.

## Remove

```bash
GH_TOKEN=<PAT> ./deploy/runner/remove.sh
```

This stops the runner, unregisters it from the repository and deletes
`~/actions-runner-edgeppe`. Without a token it deletes the local files and
leaves an offline runner entry that you remove in
`Settings → Actions → Runners`.

## Security notes

- The runner is **not** reachable from pull requests: `.github/workflows/cd.yml`
  has no `pull_request` trigger and the deploy job also asserts the event name.
  This is the property that keeps untrusted PR code off this machine.
- No registry password is stored anywhere. GHCR access uses the ephemeral
  `github.token`, scoped per job (`packages:write` to publish, `packages:read`
  to pull) and piped to `docker login` over stdin rather than the command line.
- The runner inherits the user's Docker access because it must recreate the
  `edgeppe-api` container. Treat anything able to push to `main` in this
  repository as able to run code on this host — that is inherent to self-hosted
  runners and is the reason the deployment jobs are push/tag-only.
- `var/deployment/cd_state.json` records the deployed image, its digest, the
  previous image, the fault-injection value and the GitHub run id for every
  deployment.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Job queued forever | runner offline — `./deploy/runner/start.sh` |
| `Runner.Listener --version` fails | missing libicu — `sudo ./bin/installdependencies.sh` |
| Deploy job cannot pull the image | GHCR package permissions; re-run, or make the package public |
| `cd_deploy.sh` exits 1 with "ROLLBACK SUCCEEDED" | expected: the candidate failed and the previous image was restored; check the job summary |

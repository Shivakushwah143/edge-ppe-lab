# Official References Used for Documentation Decisions

This package is primarily a project specification. The following official references were checked for current operational conventions that can change over time.

## MLflow

- MLflow Model Registry: https://mlflow.org/docs/latest/ml/model-registry/
- MLflow Model Registry workflows: https://mlflow.org/docs/latest/ml/model-registry/workflow/

Documentation decision: prefer immutable model versions plus aliases/tags (for example `@champion`) for the release pointer. Do not make legacy stage-based promotion the center of EdgePPE Lab.

## WSL / systemd

- Microsoft WSL advanced settings (`wsl.conf`, systemd): https://learn.microsoft.com/windows/wsl/wsl-config
- Microsoft systemd on WSL: https://learn.microsoft.com/windows/wsl/systemd

Documentation decision: verify current WSL/systemd state before the systemd lab. Recent Ubuntu/WSL setups may already have systemd; older setups may require enabling it and restarting WSL.

## Source-of-truth rule

The build phase should use current official documentation for exact CLI/API flags if a dependency release has changed since this package was generated, while preserving EdgePPE Lab's locked behavior and acceptance criteria.

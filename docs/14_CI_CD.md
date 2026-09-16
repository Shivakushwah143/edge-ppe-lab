# 14 — CI/CD

## Goal

Build a small pipeline that proves a commit is a valid deployment candidate. It is not an enterprise release platform.

## Pipeline

```text
Git push
  → GitHub Actions
  → install locked Python dependencies
  → lint/static checks/tests implemented by build phase
  → validate model/ONNX contract when artifact is available to CI
  → build Docker image
  → tag image with immutable identity (e.g. Git SHA)
  → output deployment-candidate metadata
```

## Important separation

CI validating application code does not automatically validate a new model. A model candidate needs its own lineage, evaluation, parity, and smoke evidence. The build phase may combine these in one workflow, but the concepts remain separate.

## Model artifacts in CI

Do not commit large training artifacts to Git merely to make CI easy. For the local lab, the implementation can use a small fixture/smoke ONNX artifact or conditionally run model checks when the artifact is present. The workflow must clearly state what was and was not validated.

## Docker image tagging

Use an immutable tag such as commit SHA. A later production extension could push to GitHub Container Registry, Amazon ECR, Azure Container Registry, or another OCI registry. Pushing to a registry is conceptually separate from deploying/running the image.

## What CD means in this lab

The project may stop at a **deployment candidate** rather than automatically modifying a real server. The learner should still manually execute the release verification and rollback flow on Ubuntu. This preserves the hands-on Linux objective.

## Failure behavior

A failing parity/model-contract check or failing test must stop image candidacy. Never mark a build deployable while hiding a failed validation step.

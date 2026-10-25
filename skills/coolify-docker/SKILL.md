---
name: coolify-docker
description: Write, review, and deploy Dockerfiles and Docker Compose for Coolify Applications and Services. Use when containerising an app for Coolify, adding a database or worker, preparing a community-shareable stack, configuring magic variables, domains, health checks or storage, or debugging a Coolify build/deployment—even if the user only asks to make a repository Coolify-ready. Covers Git-backed and Docker Image Applications and custom Services; does not require contributing to Coolify's catalogue.
---

# Docker and Coolify

Produce maintainable container definitions and a working Coolify configuration. Keep the repository, Coolify's saved configuration, and the deployed containers consistent; success requires evidence from the running workload.

## Establish the deployment contract

Inspect the repository and available Coolify connection before asking for information already present. Determine:

- Language/runtime, lockfile, build output, production command, listening interface/port, and real readiness endpoint.
- Web processes, workers, scheduled jobs, migrations, databases, writable paths, and external dependencies.
- Coolify instance/version, project/environment, server/destination, architecture, proxy, and existing resource UUID when available.
- Required configuration, secret sources, build/runtime scope, public domains, and persistent data.

Infer routine choices from the application. Ask only for missing consequential choices, such as which production resource to replace. Continue preparing files while resolving deployment access. A request to write a skill or prepare files does not itself request a live deployment.

## Choose the actual Coolify resource

| Need | Resource and source of truth |
| --- | --- |
| Build one application from repository files | Git-backed **Application**, Dockerfile strategy |
| Deploy repository-managed web/worker/database topology | Git-backed **Application**, Compose strategy |
| Run an image already published by CI or upstream | **Application**, Docker Image |
| Share or operate a self-contained stack through Coolify's component layout | **Service**, Docker Compose Empty or an existing one-click template |

A lowercase Compose `service` is a container definition. A Coolify **Service** is a distinct resource with stack/component controls. Multi-container YAML alone does not decide the resource type. Preserve the user's intended layout and update mechanism.

Read [references/coolify.md](references/coolify.md) for variables, GUI ownership, routing and health. For a Service or community sharing, also read [references/services.md](references/services.md). For file authoring, read [references/docker.md](references/docker.md). Before deployment, read [references/deployment.md](references/deployment.md).

The references link to official documentation checked on 2026-10-25. Recheck version-sensitive behaviour against the target instance and current official docs: especially generated variables, secret transport, raw Compose, API schemas and GUI controls. Do not present a newly documented feature as available on an older installation.

## Write the smallest suitable container configuration

Use the project's package manager, lockfile and production entry point. Choose supported runtime/image versions and an explicit update policy. Keep build tools out of the final image when practical, run application code without root when compatible, and minimise the build context. Make signals, writable directories and health checks work in the final image.

For Compose, keep dependencies private, declare persistence at verified data paths, and distinguish startup order from readiness. Use Coolify-generated values where appropriate, preserving shared identifiers so components receive matching credentials. Do not introduce a host port, custom proxy labels or privileged access just to make an ordinary HTTP application reachable.

Use bundled examples only when their documented contract fits:

- [assets/Dockerfile.node](assets/Dockerfile.node): npm build emitting `dist/server.js`; adapt rather than imposing this layout.
- [assets/compose.yaml](assets/compose.yaml): image-based Node web application plus PostgreSQL, suitable for a custom Service or a Git Compose Application.
- [assets/dockerignore](assets/dockerignore): starting exclusions; retain any files the actual build needs.
- [assets/deployment-notes.md](assets/deployment-notes.md): concise handover shape for the resulting project.

Do not add a Compose file to a single-container Application merely to use the example. Do not make a Service depend on an unprovided local build context.

## Validate, deploy and report evidence

1. Review the final diff, secrets, image references, port targets, volume destinations and required settings.
2. Validate Compose with disposable non-secret values. Local Docker does not generate Coolify magic variables. Avoid printing an interpolated configuration containing real credentials.
3. Build and smoke-test the application when the environment supports it. Test its real health command, runtime user, dependency connection, shutdown and persistence as relevant. Check the target architecture; a local build alone does not prove server compatibility.
4. Configure the chosen Coolify resource and inspect its effective configuration. Saving a form is not the same as updating running containers.
5. When deployment is requested and the target is established, deploy within that authorisation. Follow logs to completion, verify required containers/jobs, and exercise the public route or worker behaviour. Do not substitute an SSH `docker compose up` for a Coolify-managed deployment.
6. Report files, exact GUI settings still needed, checks actually run, deployed revision/image and resource/deployment identifiers when available. State any unverified stage explicitly. Use the handover template proportionately; do not expose secret values.

Keep changes scoped to the requested resource. Stop repeated deployment attempts when the same failure recurs; collect the first useful error and correct its cause before retrying. Never delete a volume or reset a database to make a deployment pass without explicit authorisation for that data loss.

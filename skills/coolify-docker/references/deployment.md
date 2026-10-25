# Deploy through Coolify and verify the result

## Make the intended change concrete

Prepare the files and a short settings map using [../assets/deployment-notes.md](../assets/deployment-notes.md). Identify the exact instance, resource type, project/environment, server/destination and resource UUID. Use available connected tools, authenticated CLI/API or the GUI; inspect capabilities instead of inventing a Coolify integration. A Dockerfile/Compose authoring request alone does not authorise changing a live resource. If deployment is already requested and the target is clear, proceed without another blanket permission step.

For a new resource, create the selected Application or Service and configure it before triggering deployment. Check source access or registry credentials, branch/image revision, build paths, required variables, domain/internal port, storage and health. Follow the corresponding GUI route in [coolify.md](coolify.md) or [services.md](services.md). Keep the GUI usable: editable settings should appear as variables, public components should have the right domain, and stateful components should expose the intended storage.

Prefer narrowly scoped environment-variable edits over bulk Developer-view replacement. Review source and effective configuration for divergence, including overrides and image health checks. Do not overwrite unrelated operator settings while applying a template.

## Migrations and rollback

Work out first-deployment behaviour, migration concurrency and compatibility with the previous app before deployment. A pre-deployment command on a Dockerfile Application runs in the existing container and is skipped when none exists. Post-deployment failure can occur after Coolify has marked deployment successful, so inspect the command result separately. Use a verified one-shot migration mechanism when startup depends on schema readiness. [Dockerfile deployment commands](https://coolify.io/docs/applications/builds/dockerfile)

Record the previous revision/image and relevant configuration. Prefer backward-compatible migrations and take a recoverable backup before a risky schema/data change. Restoring an older image does not undo a database migration or restore volumes. Do not promise zero downtime for a stateful Compose stack; check the resource's supported replacement behaviour. [Rollbacks](https://coolify.io/docs/applications/deployments/rollbacks)

## GUI execution

Select Deploy and follow Deployment Logs. For a Service, inspect every required component and finite job; for an Application, inspect the deployment and runtime views. Verify the resulting revision/image matches the requested change. A saved setting, queued operation, green build or running process alone is insufficient.

Test the actual user-facing HTTPS route, expected response and certificate, plus an application-level dependency operation. For a worker or non-HTTP workload, verify the job/queue/output instead of inventing a public domain. Exercise an authorised, non-destructive write/read flow when persistence is part of the change. Avoid logging credentials or returning whole configuration dumps.

## API or CLI execution

Read the installed CLI's help or the instance-compatible API schema before creating/updating a resource; payloads differ for Applications and Services. Use the user's established token source without printing it. Confirm API access and the minimum permissions needed for the operation. Use the trusted instance's `/api/v1` base, not a hard-coded cloud endpoint for a self-hosted user. [API overview](https://coolify.io/docs/api/overview)

For supported versions, the deploy API accepts `POST /deploy` with a resource `uuid` (query or JSON). Prefer one exact UUID over a tag that could deploy unrelated resources. Preserve the returned deployment identifier where provided. [Deploy endpoint](https://coolify.io/docs/api/endpoints/deployments/deploy-by-tag-or-uuid)

Follow an Application's deployment with `GET /deployments/{deployment_uuid}` and inspect its status/logs. The deployment UUID differs from the resource UUID. Do not assume Service operations return the same Application deployment record; follow their operation output and component status using the resource-specific API or GUI. [Deployment endpoint](https://coolify.io/docs/api/endpoints/deployments/get-deployment-by-uuid)

Poll with a bounded deadline and reasonable backoff; report still-running or unknown outcomes honestly. Reconcile state after a network timeout before retrying a create/deploy request, since the first request may have succeeded. Do not deploy repeatedly to compensate for a broken health check or missing secret. After operation completion, perform the same runtime checks as the GUI workflow.

## Diagnose at the failing layer

| Symptom | First evidence to inspect |
| --- | --- |
| Build fails | Selected context/Dockerfile, lockfile, native architecture, first build error, secret mount availability |
| Process exits | Production command, runtime-only inputs, file permissions and migration outcome |
| Running but unhealthy | Run the exact probe inside the final container; check executable, path, port and startup time |
| Proxy error / no available server | Runtime health, bind address, receiving component, internal port, effective networks/labels |
| Works internally, wrong public URL | Domain scheme/path, DNS/TLS, generated URL versus app callback/base URL |
| Database authentication fails | Same generated identifier in both components; existing account versus changed initialisation variable |
| Data disappears | Effective mount target/name, resource/component renaming and image data-path changes |

Correct the smallest evidenced cause and retry once it has changed. If access, DNS, credentials or an external dependency prevents verification, deliver the prepared artefacts and precise remaining action; do not label the application deployed.

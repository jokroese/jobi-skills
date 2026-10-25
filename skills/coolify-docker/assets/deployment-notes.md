# Coolify deployment

## Resource and source

- Resource type and reason: <Application/Dockerfile, Application/Compose, Application/Docker Image, or Service>
- Instance, project/environment, server/destination: <target>
- Source of truth and update route: <Git commit and paths, image digest, or versioned Service YAML>
- Build/runtime contract: <commands, architecture, internal port and readiness>

## Configure in Coolify

| Setting | Value or action | Owner |
| --- | --- | --- |
| Build strategy and source paths | <actual values, or not applicable> | <repository/GUI> |
| Domain and receiving component | <public URL and internal target port> | <GUI/generated> |
| Health check | <real command/path and location> | <image/Compose/GUI> |
| Persistent storage | <mount target, ownership and backup route> | <Compose/GUI> |

## Variables

List names and sources, never resolved secrets.

| Name | Purpose/source | Required/default/generated | Build/runtime |
| --- | --- | --- | --- |
| <name> | <secret source or non-secret value> | <requirement> | <scope> |

## Deployment and recovery

- First deployment/migrations: <mechanism and success evidence>
- Update procedure: <source change and Coolify action>
- Recovery: <previous image/revision, configuration and data considerations>
- Shared Services: <template release, manual paste/update instructions; omit for Applications>

## Verification

- Local validation: <commands run and results>
- Coolify deployment: <resource UUID, deployment ID if supplied, revision/image and result>
- Runtime: <health, dependency/worker behaviour, public route and persistence checks>
- Remaining work: <specific unverified step, or none>

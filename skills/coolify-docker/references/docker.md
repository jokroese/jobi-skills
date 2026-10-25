# Docker authoring and local validation

## Build the application that exists

Read the manifest, lockfile, framework output and start command before choosing a Dockerfile. Separate dependency installation from frequently changing source to preserve cache reuse. Use locked installs and multi-stage builds where they remove compilers/dev dependencies from runtime. Copy required assets and migrations as well as binaries; avoid copying the entire builder filesystem. Match native dependencies' libc and architecture across stages; Alpine is not automatically the best runtime. Use an absolute working directory and a compatible non-root account with deliberate directory ownership. Prefer exec-form commands so termination reaches the process. Choose supported version tags; use verified digests when immutable builds are needed and arrange updates rather than freezing vulnerable images indefinitely. [Docker build guidance](https://docs.docker.com/build/building/best-practices/)

Keep credentials, local dependencies, Git metadata and unrelated outputs outside the context using `.dockerignore`. Do not exclude required workspace manifests or compiled assets when those are the intended input. Inspect the actual context directory: Dockerfile location and context are separate concepts. [Build contexts](https://docs.docker.com/build/concepts/context/)

`assets/Dockerfile.node` assumes npm, `package-lock.json`, a build script, a Node-supported runtime image with the `node` user, output at `dist/server.js`, and HTTP readiness at `/healthz`. Select a compatible supported `NODE_IMAGE`; no default is supplied to avoid silently choosing an ageing runtime. Pass it with `--build-arg NODE_IMAGE=<verified-image>` locally and configure the same non-secret build argument in Coolify; for a project-specific deliverable, replacing the parameter with the selected image is also appropriate. Add runtime assets and writable directories required by the real application. Use a different recipe for Next.js standalone output, Python, Go, static files or another package manager.

## Separate secrets and configuration stages

Use `ARG` only for non-secret build inputs. Use BuildKit secret/SSH mounts for private dependencies; deleting a copied secret later does not remove it from earlier layers. Verify that the command does not persist credentials in generated files or logs. Build secrets are separate from Compose runtime `secrets:` and application environment values. [Build secrets](https://docs.docker.com/build/building/secrets/)

For example, with a secret supplied as a complete npm configuration file:

```dockerfile
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc,required=true \
    npm ci
```

The caller must supply that exact ID. Verify Coolify's supported secret mapping before adopting the example; do not assume its variable names automatically create `npmrc`. If secure remote build-secret transport is unavailable, build in an authorised CI environment and deploy the image rather than falling back to secret build arguments.

Treat client-side configuration as public, even when injected during build. A frontend bundle cannot keep a token secret. Keep database passwords runtime-only and isolate production from preview credentials.

## Compose semantics that affect correctness

Use the Compose Specification without obsolete top-level `version`. Prefer `docker compose`; check the server's supported keys before adding recently introduced features. Avoid fixed `container_name`, global network/volume names and Swarm assumptions: these interfere with resource isolation and previews. [Compose reference](https://docs.docker.com/reference/compose-file/), [obsolete version field](https://docs.docker.com/reference/compose-file/version-and-name/)

`.env` and `--env-file` supply interpolation; they do not automatically inject every entry into a container. Declare container inputs under `environment` or an intentionally supplied `env_file`. `${KEY:?}` rejects empty/unset values; `${KEY:-value}` provides a default. `${KEY:?value}` is an error message, not a default. Escape container-side shell references as `$$`, for example `$${POSTGRES_USER}` in a `CMD-SHELL` health check. Keep Compose interpolation, shell expansion and Coolify's own interpolation distinct. [Interpolation](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/)

Use `depends_on.condition: service_healthy` for dependencies with a meaningful readiness check, and `service_completed_successfully` for a migration job that must finish before startup. Plain `depends_on` only orders startup. Retain application retries for later outages. Use `restart: "no"` for finite jobs; health failure alone is not a Docker restart policy. [Startup order](https://docs.docker.com/compose/how-tos/startup-order/)

Persist data at the image's documented path, with writable ownership. Verify path changes on major upgrades: the bundled Compose example deliberately uses PostgreSQL 17's `/var/lib/postgresql/data`; do not change its major version without checking storage and migration requirements. A volume is not a backup, and adding a mount does not migrate existing container data. Avoid host source bind mounts in production; file mounts need an actual file on the deployment host. [Volumes](https://docs.docker.com/engine/storage/volumes/), [official PostgreSQL image](https://hub.docker.com/_/postgres)

Choose resource limits, log rotation, `read_only`, capability drops and `no-new-privileges` where workload-compatible; verify writes, temporary directories and image startup before applying them. Do not force a different UID on a database image whose entrypoint manages permissions. Keep CPU/memory limits realistic for build and runtime separately.

## Validate without contaminating production

Use a disposable project name and dummy variables to render the actual chosen Compose file:

```sh
docker compose --env-file /path/to/disposable-validation.env -f compose.yaml config --quiet
docker build --check -f Dockerfile .
```

Pass required non-secret build arguments to both checks and builds. If the installed builder lacks `--check`, report that and use available build/lint checks. A schema check cannot prove Coolify parsing or application behaviour. Unset conflicting shell variables during fixture validation because they can override the env file. Do not run `config --environment` or print resolved YAML with production credentials.

Build, run and inspect health using the actual image. For local HTTP testing, bind a temporary port to `127.0.0.1`; local convenience mappings need not enter production Compose. A failing probe should fail validation. Check graceful stop and persistence for stateful changes. Clean up only test-owned containers/networks; do not delete volumes containing existing data.

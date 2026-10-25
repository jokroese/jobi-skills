# Coolify configuration contract

## Keep the right source of truth

For a Git Dockerfile Application, choose the Git source/branch and Dockerfile build strategy, then set Base Directory (context) and Dockerfile Location relative to it. Set Ports Exposes to the internal listening port. A Dockerfile entered directly into Coolify without Git cannot `COPY` repository files. [Dockerfile Applications](https://coolify.io/docs/applications/builds/dockerfile)

For a Git Compose Application, set Compose strategy, Base Directory and Docker Compose Location. Edit the repository file and reload/redeploy the intended revision. Configure each public component in Domains. For an existing image, use a Docker Image Application and specify the verified image/tag or digest and registry access. [Deployment methods](https://coolify.io/docs/applications/choose-deployment-method)

For a Service, follow [services.md](services.md). Do not tell users that the standard Application forms override settings owned by Compose. Do not edit generated server-side files: the next deployment can replace them.

## Variables: ordinary, generated and scoped

Expose user-editable settings with `${KEY}`, required values with `${KEY:?}`, and safe initial defaults with `${KEY:-value}`. Fixed environment literals remain source-owned. Existing GUI values can survive changes to source defaults; verify the stored value instead of expecting a changed default to overwrite it. [Compose Applications](https://coolify.io/docs/applications/builds/docker-compose)

For Compose-generated values, use these forms and inspect the parsed result:

| Reference | Meaning |
| --- | --- |
| `SERVICE_URL_WEB_3000` | Public URL with scheme for `web`, targeting internal port 3000 |
| `SERVICE_FQDN_WEB_3000` | Corresponding hostname without scheme |
| `SERVICE_USER_DB` | Generated username |
| `SERVICE_PASSWORD_64_DB` | Generated 64-character password; reuse the full name in both clients and database |
| `SERVICE_REALBASE64_64_SESSION` | Base64-encoded random bytes; verify the application's required encoding/length |

Declare the domain variable on its corresponding Compose component, for example `SERVICE_URL_WEB_3000: /`, and reference it as `${SERVICE_URL_WEB_3000}` for the app's public-URL setting. Normalise hyphens/dots in service names to underscores. For credential/random identifiers, use one token such as `DBPASSWORD`; `SERVICE_PASSWORD_DB_PASSWORD` can be parsed incorrectly. Do not assume `SERVICE_BASE64_*` is encoded Base64. Generated values persist; renaming them can create different credentials. These are Coolify features, not local Docker generators. [Generated values](https://coolify.io/docs/services/configuration/docker-compose)

For non-Compose Applications, inspect predefined `COOLIFY_*` variables instead of assuming the Compose generator is available. Mark runtime secrets unavailable during build. Verify Build secrets uses Docker BuildKit secrets and the builder supports it: documented fallback uses build arguments. Preserve `$` using the appropriate literal-value control. Developer view replaces its managed variable set; inspect existing entries before bulk edits. Use Normal view for locked/multiline fields. Separate preview values and use shared references such as `{{environment.DATABASE_URL}}` only in supported Coolify value fields. Rebuild after build-time changes; recreate containers after runtime changes. [Application variables](https://coolify.io/docs/applications/configuration/environment-variables)

Do not mistake generated credentials for rotation. Changing a database initialisation password variable does not normally change an existing database account; coordinate database-side rotation and dependent clients. Prefer separate connection fields when supported, or correctly URL-encode credentials in a connection URI.

## Public routes and private connections

Bind public application processes to `0.0.0.0`. In a Coolify Domains field, `https://app.example.com:3000` selects internal port 3000; the client URL remains `https://app.example.com`. The same distinction applies to a magic variable's port suffix. A generated URL does not guarantee HTTPS: verify its scheme and the target server's wildcard/custom domain, DNS, proxy and certificate provisioning before promising a working secure endpoint. `EXPOSE`/`expose` describe container ports; `ports` publishes host ports. Use proxy-managed domains/TLS for ordinary HTTP traffic and omit host publication unless direct TCP/UDP access is intended. [Compose routing](https://coolify.io/docs/applications/builds/docker-compose)

Within a stack, connect by Compose DNS name and internal port, such as `database:5432`. `localhost` points back to the caller. Separate resources need a shared network; a project/environment name does not provide connectivity. For a Service that needs its selected destination network, inspect Connect To Predefined Network. Such networks are server-local, not cross-server tunnels. Do not manually hard-code `coolify` as an external network for every stack. [Service networking](https://coolify.io/docs/services/configuration/networking)

Let Coolify generate proxy labels and resource names in managed mode. Raw Compose transfers responsibility for routing/network configuration to the author; use it only for a deliberate requirement and verify the installed version's behaviour. Check DNS and the selected proxy before inventing Traefik labels on a Caddy installation. [Compose modes](https://coolify.io/docs/applications/builds/docker-compose)

## Health, storage and the GUI

Put Compose health checks and mounts in Compose. For non-Compose Dockerfile Applications, an image `HEALTHCHECK` takes precedence over the GUI check. Dashboard HTTP probes need `curl` or `wget` in the final container; runtime-native command probes can avoid that dependency. Use the application's actual path, port, startup grace and success condition. Traefik can remove unhealthy targets, so a bad probe can break routing even when the process runs. [Health checks](https://coolify.io/docs/applications/configuration/health-checks)

Inspect persistent storage after parsing and confirm the effective mount source, target and ownership. For a non-Compose Application, configure required storage through its storage controls; for Compose, edit the source definition. Preserve existing names when updating stateful components. Check backup/restore support for the actual resource type rather than assuming every database inside an Application receives standalone Database features. [Application storage](https://coolify.io/docs/applications/configuration/persistent-storage)

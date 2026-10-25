# Custom Services and community sharing

## Use the actual Service resource

A Coolify Service has stack-level configuration and detected application/database component cards. Create it through **Docker Compose Empty**, paste the YAML, save, then review variables, component domains and persistent storage. For generated HTTPS, check the resolved URL scheme, wildcard/custom-domain DNS and working TLS proxy; the magic variable alone does not provision all prerequisites. This creates a Service even when its YAML came from a public repository; connecting that repository through the Git Compose workflow creates an Application instead. [Services](https://coolify.io/docs/services/)

Under Configuration > General > Edit Compose File, edit **Source Compose**. Inspect **Deployable Compose** to see Coolify's generated configuration. Verify parsed component names and storage before deploying; renaming a component can affect its identity and data attachment. [Service Compose](https://coolify.io/docs/services/configuration/docker-compose)

Prefer released images for a self-contained shared stack. Do not assume pasted YAML brings a repository checkout, relative `build: .` context, `env_file`, or adjacent configuration files. Package required files in the image or use explicitly supported file-mount provisioning. Keep environment references and persistent mounts in the shared definition; confirm every mount source exists on the server. See [storage mounts](https://coolify.io/docs/services/configuration/persistent-storage).

Let normal Service parsing supply resource naming, networking and its default restart policy. Explicitly set `restart: "no"` for one-time jobs. Keeping top-level named-volume declarations makes the file easier to validate with ordinary Compose, even where Coolify can infer them. Put health checks in Compose/image and assess how finite jobs affect aggregate status on the installed release. [Service template conventions](https://coolify.io/docs/contribute/service)

## Share independently of the official catalogue

Share a versioned, secret-free Compose file in a repository or release, with image provenance, supported architectures, app-specific prerequisites, configuration fields, expected ports, storage paths and upgrade/migration notes. Recipients copy its YAML into **Docker Compose Empty** and configure their own instance. This distribution method follows the documented paste workflow; it is not an automatic catalogue installation or a subscription to the source repository. [Custom Service deployment](https://coolify.io/docs/services/)

An upstream template contribution is optional and separate. Official contributions were paused when checked on 2026-10-25; consult the current policy only if the user asks to submit upstream. Do not require catalogue metadata, logo paths or popularity criteria for an ordinary community-shared stack. [Contribution status](https://coolify.io/docs/contribute/service)

Do not claim a raw URL import, custom catalogue registration, or one-click community installation unless the actual instance supports it. A link can distribute YAML without being an import endpoint. Offer a Git Compose Application when users specifically want repository-driven updates, making clear that it changes the Coolify resource type and layout.

## Update installed copies deliberately

An existing Service owns its saved definition. Neither a repository update nor a newer official template automatically merges into it. Compare the new source with the installed copy, preserve instance values and storage identities, back up state where needed, then apply compatible image/schema changes. Pull Latest Images & Restart pulls the references already saved; it does not fetch a new Compose definition. [Service lifecycle](https://coolify.io/docs/services/how-services-work)

Record the shared template release and tested image versions so operators can reproduce an upgrade. Do not publish generated instance passwords, resolved environment files or deployable YAML containing secrets. A shareable artefact should instantiate fresh configuration on the recipient's instance.

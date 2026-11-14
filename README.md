# ContextForge on UBI 9

Builds unmodified [IBM ContextForge](https://github.com/IBM/mcp-context-forge) stable releases with Red Hat UBI 9 bases for older x86 NAS CPUs, including the Intel Celeron J3355. Official recent images use UBI 10 and require x86-64-v3. This build targets `linux/amd64`; it is not an ARM image.

**Status:** CI must complete successfully before there is a usable image. A passing build is not an end-to-end Synology SSO or tenant-isolation certification. Test the first image on the NAS before using real data.

## How updates work

The [build workflow](.github/workflows/build.yaml) runs on changes to build files, daily at 04:23 UTC, and manually from Actions. Each run selects the latest published stable `vMAJOR.MINOR.PATCH` release from IBM (not `main`), resolves its commit, and builds its Containerfile with UBI 9 overrides. Rebuilding daily also picks up refreshed base images and upstream dependency resolutions. Dependencies are resolved according to upstream's Containerfile; these are not bit-for-bit reproducible builds.

All builder stages and the final runtime use UBI 9. The upstream bundled Admin UI build stays enabled. No FIPS mode is enabled: the base override is for CPU compatibility.

Before publication, CI checks:

- Python, SQLite, SSL, gRPC, cryptography and Pydantic native imports under QEMU's Nehalem CPU model (no AVX).
- Native container startup with one worker and SQLite, a built-in HTML login page, and rejection of an unauthenticated MCP request.
- Schema initialization and SQLite persistence over a container restart.

These checks do not execute every dependency path or simulate all J3355/kernel behavior. SSO requires your real identity provider and is tested after deployment. Separate users still need correctly scoped resources and upstream credentials.

Successful default builds publish to `ghcr.io/jkrenzer/contextforge-ubi9`:

| Tag | Meaning |
| --- | --- |
| `v1.1.1-ubi9-RUN_ID-ATTEMPT` | Unique build tag; use its digest for immutable deployment |
| `v1.1.1-ubi9` | Most recent successful rebuild of that release; mutable |
| `stable-ubi9` | Most recent successful automatically selected stable release; mutable |

The Actions summary records the upstream commit and registry digest. A manual build with an explicit release publishes the version/build tags but does not move `stable-ubi9` backwards. No workflow deploys to the NAS, mounts your NAS data, or requires your SSO secret.

GitHub schedules can be delayed; scheduled workflows in inactive public repositories can be disabled by GitHub. Check Actions notifications for failures. A failed build does not replace published tags. Future upstream changes may require adapting build arguments or dependencies.

## First build

Pushes to `main` containing the workflow start a build. Otherwise open **Actions > Build UBI 9 image > Run workflow** and leave the release blank for latest stable. The default `GITHUB_TOKEN` is used for GHCR; no personal access token is needed for publishing. Organization/repository policies can restrict Actions or package writes.

The first GHCR package may be private even when this source repository is public. Either authenticate the NAS to GHCR with a read-only package credential or change the package visibility to public yourself. Public images must not contain deployment secrets. This repository contains examples only.

## Synology deployment

See [deploy/README.md](deploy/README.md). After the first successful build, copy the Compose example and `.env.example` into a Container Manager project folder. Enter your own secrets and a dedicated data-directory path. Deploy a tested digest, not an assumed upstream tag.

The built-in Admin UI is at `/admin`. It is separate from ContextForge's redesigned standalone Web UI. Upstream v1.1.1 announces built-in Admin UI support ending on 27 January 2027; the notice does not itself shut it down. A future standalone UI deployment needs its own container/session configuration.

## Local build

Requires Git, Docker Engine, Buildx and Bash. A stronger Linux AMD64 build host is preferable to compiling on the NAS; there is no need for the build host to have the same CPU. Do not add `-march=native` compiler flags.

```bash
git clone --branch v1.1.1 --depth 1 https://github.com/IBM/mcp-context-forge.git upstream
RELEASE=v1.1.1 bash scripts/build.sh upstream contextforge-ubi9:local
python3 scripts/smoke_test.py contextforge-ubi9:local
```

For offline transfer, `docker save -o contextforge-ubi9.tar contextforge-ubi9:local`, transfer the archive, then import it in Container Manager or use `docker load`. Set `CONTEXTFORGE_IMAGE=contextforge-ubi9:local`.

The build uses upstream's own Containerfile, not a vendored fork. UBI 9 remains a maintained base, but CPU compatibility still needs acceptance on actual hardware. Upstream application and bundled dependency licenses remain applicable; upstream is Apache-2.0. Do not assume that changing a container base proves security compliance.

## Maintenance

GitHub Actions dependencies are commit-pinned and Dependabot proposes updates. On failures inspect the Actions logs and retain the last working NAS deployment. Before upgrades, stop ContextForge and back up the entire SQLite directory and its JWT/encryption secrets. Database migrations may prevent simply switching back to an older application image; restore the matching backup when necessary.

Upstream references: [Containerfile](https://github.com/IBM/mcp-context-forge/blob/main/Containerfile), [releases](https://github.com/IBM/mcp-context-forge/releases), [deployment docs](https://ibm.github.io/mcp-context-forge/latest/deployment/container/).

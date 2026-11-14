# Synology Container Manager

1. Wait for a successful build in GitHub Actions. Set `CONTEXTFORGE_IMAGE` to the published image digest. This avoids accidental changes to a mutable tag.
2. Copy `compose.yaml` and `.env.example` to your NAS project folder; rename the latter to `.env` and fill every secret placeholder. Never commit `.env`.
3. Create a **dedicated empty directory** at `CONTEXTFORGE_DATA_DIR`. Both services bind it to `/app/data`; the initializer sets its owner to UID/GID 10001 and mode 0700. Do not point it at a general shared folder: these permissions intentionally restrict access. Existing Synology ACLs may also need adjustment.
4. Import the Compose file as a Container Manager project. Keep the same project name when updating.
5. Configure DSM's HTTPS reverse proxy to forward the external hostname to `http://127.0.0.1:4444`. Preserve Host, Authorization, X-Forwarded-Proto and MCP headers; allow streaming and suitable timeouts. The service is HTTP internally; cookies remain Secure because the browser uses HTTPS. Web Station may require a published port: this configuration binds one to loopback only.
6. Open `https://YOUR_HOST/admin`. Create users/approve registrations, verify private/team resource visibility, and configure each user's own upstream credentials.

## Synology SSO Server

Create an OIDC application with the exact callback `https://YOUR_HOST/auth/sso/callback/synology`. Enable the appropriate NAS account sources. Users need unique email attributes. Populate SSO values from your server's discovery document, typically `https://NAS_HOST/webman/sso/.well-known/openid-configuration`.

Apply `compose.sso.yaml` as an overlay or merge its environment mapping into the main Compose file in the Container Manager editor. Only request scopes advertised by your provider; the example requests openid/email/groups. Local admin login is retained, new SSO users require approval, and no NAS group automatically grants administrator access. Group-role/team mappings should be added only after inspecting actual claims.

If the SSO hostname resolves to a private address, include that specific NAS address as a /32 in `SSRF_ALLOWED_NETWORKS`, along with any internal MCP service CIDRs needed. Keep certificate verification enabled. The container needs working DNS and access to the provider's HTTPS token, userinfo and JWKS endpoints.

Web SSO does not automatically implement interactive OAuth authorization for every MCP client. Start with separately issued per-user ContextForge tokens in clients supporting Bearer headers. Test the chosen client's OAuth flow separately.

## Existing SQLite data

Stop the old deployment before copying the **entire** SQLite directory (including any WAL/SHM files) from the old volume into the bind-mounted directory. Preserve the original JWT/encryption secrets. The initializer changes the mount-root ownership only, not existing files recursively; copied database files must also be writable by UID/GID 10001. Do not delete the old volume until migration is verified.

## Upgrades and troubleshooting

Publishing a new image does not update the NAS. Stop the service, back up the data directory plus `.env`, update the image digest, pull/recreate the service, and test UI/SSO plus cross-user denial. Restore both the matching database backup and older image if a schema migration prevents rollback.

`Fatal glibc error: CPU does not support x86-64-v3` means the old UBI 10 image is still selected. Check the image reference. An exit-127 dependency error is only a summary; inspect that container's logs and Docker `.State.Error`.

The QEMU CPU check in CI is useful screening, not a guarantee that every optional backend or native plugin works on the NAS. First acceptance should use a disposable SQLite directory. Do not mount the Docker socket into ContextForge; manage backend containers separately and connect by their MCP HTTP endpoints.

"""Exercise a disposable container. Never mounts deployment data or secrets."""
import json
import secrets
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


def docker(*args, capture=False):
    return subprocess.run(["docker", *args], check=True, text=True,
                          stdout=subprocess.PIPE if capture else None).stdout


def main():
    image = sys.argv[1]
    suffix = secrets.token_hex(5)
    name, volume = "cf-smoke-" + suffix, "cf-smoke-data-" + suffix
    password = secrets.token_urlsafe(40) + "Aa1!"
    values = {
        "HOST": "0.0.0.0", "PORT": "4444", "SSL": "false",
        "ENVIRONMENT": "development", "APP_DOMAIN": "http://localhost:4444",
        "SECURE_COOKIES": "false", "GUNICORN_WORKERS": "1", "CACHE_TYPE": "memory",
        "DATABASE_URL": "sqlite:////app/data/mcp.db", "MCPGATEWAY_SKIP_MIGRATIONS": "false",
        "JWT_SECRET_KEY": secrets.token_hex(32), "AUTH_ENCRYPTION_SECRET": secrets.token_hex(32),
        "PLATFORM_ADMIN_EMAIL": "smoke@example.com", "PLATFORM_ADMIN_PASSWORD": password,
        "DEFAULT_USER_PASSWORD": secrets.token_urlsafe(40) + "Aa1!",
        "BASIC_AUTH_PASSWORD": secrets.token_urlsafe(40) + "Aa1!",
        "EMAIL_AUTH_ENABLED": "true", "MCPGATEWAY_UI_ENABLED": "true",
        "MCPGATEWAY_ADMIN_API_ENABLED": "true", "PUBLIC_REGISTRATION_ENABLED": "false",
        "AUTH_REQUIRED": "true", "MCP_REQUIRE_AUTH": "true", "MCP_CLIENT_AUTH_ENABLED": "true",
        "API_ALLOW_BASIC_AUTH": "false", "DOCS_ALLOW_BASIC_AUTH": "false",
    }
    try:
        docker("volume", "create", volume)
        docker("run", "--rm", "--network", "none", "--user", "0:0",
               "-v", volume + ":/app/data", "--entrypoint", "/app/.venv/bin/python", image,
               "-c", "import os; os.chown('/app/data',10001,10001); os.chmod('/app/data',0o700)")
        with tempfile.TemporaryDirectory() as directory:
            envfile = Path(directory) / "smoke.env"
            envfile.write_text("".join(f"{k}={v}\n" for k, v in values.items()), encoding="utf-8")
            envfile.chmod(0o600)
            docker("run", "-d", "--name", name, "--env-file", str(envfile),
                   "-v", volume + ":/app/data", "-p", "127.0.0.1::4444", image)
        def request(path, data=None):
            port = docker("port", name, "4444/tcp", capture=True).strip().rsplit(":", 1)[1]
            req = urllib.request.Request("http://127.0.0.1:" + port + path,
                                         data=json.dumps(data).encode() if data is not None else None,
                                         headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=10) as response:
                    return response.status, response.read()
            except urllib.error.HTTPError as error:
                return error.code, error.read()
        def wait():
            deadline = time.monotonic() + 300
            while time.monotonic() < deadline:
                try:
                    if request("/health")[0] == 200:
                        return
                except (OSError, ValueError):
                    pass
                state = json.loads(docker("inspect", name, capture=True))[0]["State"]
                if not state["Running"]:
                    raise RuntimeError("Gateway exited during startup")
                time.sleep(3)
            raise TimeoutError("Gateway health did not become ready")
        wait()
        docker("exec", name, "/bin/sh", "-ec", '. /etc/os-release; test "$VERSION_ID" = "9" || test "${VERSION_ID%%.*}" = "9"')
        status, body = request("/admin/login")
        assert status == 200 and b"<html" in body.lower(), "Bundled login UI missing"
        status, _ = request("/mcp", {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        assert status == 401, f"Unauthenticated MCP request returned {status}, expected 401"
        status, body = request("/auth/email/login", {
            "email": values["PLATFORM_ADMIN_EMAIL"], "password": password,
        })
        assert status == 200 and json.loads(body).get("access_token"), "Admin login failed"
        status, _ = request("/auth/email/login", {
            "email": values["PLATFORM_ADMIN_EMAIL"], "password": "incorrect-password",
        })
        assert status == 401, "Invalid password was not rejected"
        # Confirm application migrations produced tables, then retain a sentinel
        # across a real restart of the same SQLite-backed deployment.
        docker("exec", name, "/app/.venv/bin/python", "-c",
               "import sqlite3; c=sqlite3.connect('/app/data/mcp.db'); "
               "assert c.execute(\"select count(*) from sqlite_master where type='table'\").fetchone()[0]>1; "
               "c.execute('create table smoke_persistence (value text)'); "
               "c.execute(\"insert into smoke_persistence values ('retained')\"); c.commit()")
        docker("restart", name)
        wait()
        docker("exec", name, "/app/.venv/bin/python", "-c",
               "import sqlite3; assert sqlite3.connect('/app/data/mcp.db').execute("
               "'select value from smoke_persistence').fetchone()[0]=='retained'")
        print("PASS: UBI 9, startup, UI, MCP auth, admin login, migrations and SQLite persistence")
    except Exception:
        subprocess.run(["docker", "logs", "--tail", "120", name], check=False)
        raise
    finally:
        subprocess.run(["docker", "rm", "-f", name], check=False, stdout=subprocess.DEVNULL)
        subprocess.run(["docker", "volume", "rm", volume], check=False, stdout=subprocess.DEVNULL)


if __name__ == "__main__":
    main()

"""Apply the narrowly scoped SSO null-name workaround before image builds."""
import ast
from pathlib import Path
import sys

OLD = 'user_info.get("full_name", email)'
NEW = '(user_info.get("full_name") or email)'


def patch_source(source):
    """Handle missing, null and empty names without changing approval policy."""
    if OLD not in source:
        if NEW in source:
            return source
        raise RuntimeError("SSO name fallback changed upstream; review this workaround before building")
    patched = source.replace(OLD, NEW)
    ast.parse(patched)
    return patched


def main():
    path = Path(sys.argv[1]) / "mcpgateway/services/sso_service.py"
    source = path.read_text(encoding="utf-8")
    patched = patch_source(source)
    count = source.count(OLD)
    path.write_text(patched, encoding="utf-8")
    print(f"SSO null-name workaround: {count} fallback(s) updated")


if __name__ == "__main__":
    main()

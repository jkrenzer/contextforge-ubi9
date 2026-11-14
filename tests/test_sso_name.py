import ast
import importlib.util
from pathlib import Path
import sqlite3
import unittest

spec = importlib.util.spec_from_file_location("sso_patch", Path(__file__).parents[1] / "scripts/patch_sso_name.py")
patch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)


class SSONameFallback(unittest.TestCase):
    def test_sqlite_approval_accepts_missing_null_empty_and_named_users(self):
        original = 'full_name = user_info.get("full_name", email)\n'
        compiled = compile(patch.patch_source(original), "<patched>", "exec")
        with sqlite3.connect(":memory:") as db:
            db.execute("CREATE TABLE pending_user_approvals (full_name TEXT NOT NULL)")
            for info, expected in [
                ({}, "user@example.com"),
                ({"full_name": None}, "user@example.com"),
                ({"full_name": ""}, "user@example.com"),
                ({"full_name": "Jörn"}, "Jörn"),
            ]:
                with self.subTest(info=info):
                    namespace = {"user_info": info, "email": "user@example.com"}
                    exec(compiled, namespace)
                    self.assertEqual(namespace["full_name"], expected)
                    db.execute("INSERT INTO pending_user_approvals VALUES (?)", (namespace["full_name"],))
            self.assertEqual(db.execute("SELECT COUNT(*) FROM pending_user_approvals").fetchone()[0], 4)

    def test_all_fallback_sites_and_approval_policy_preserved(self):
        source = ('if require_admin_approval:\n'
                  '    pending = PendingUserApproval(full_name=user_info.get("full_name", email))\n'
                  'resolved = user_info.get("full_name", email)\n'
                  'user = create_user(full_name=user_info.get("full_name", email))\n')
        result = patch.patch_source(source)
        self.assertEqual(result.count(patch.NEW), 3)
        self.assertIn("if require_admin_approval:", result)
        self.assertIn("PendingUserApproval(", result)
        ast.parse(result)

    def test_idempotent(self):
        source = "full_name = " + patch.OLD
        patched = patch.patch_source(source)
        self.assertEqual(patch.patch_source(patched), patched)

    def test_unrecognized_upstream_fails_closed(self):
        with self.assertRaises(RuntimeError):
            patch.patch_source("full_name = custom_resolution(user_info)")


if __name__ == "__main__":
    unittest.main()

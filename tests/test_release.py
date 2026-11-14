import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("resolver", Path(__file__).parents[1] / "scripts/resolve_release.py")
resolver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resolver)


class ReleaseSelection(unittest.TestCase):
    def test_stable_release(self):
        self.assertEqual(resolver.validate_release({"tag_name": "v1.1.1"}), "v1.1.1")

    def test_reject_unpublished_or_unstable(self):
        for data in ({"tag_name": "v1.1.1", "draft": True},
                     {"tag_name": "v1.1.1", "prerelease": True},
                     {"tag_name": "v2.0.0-rc1"}, {"tag_name": "main"},
                     {"tag_name": "v1.1.1\ninjected=true"}, {"tag_name": "--upload-pack=x"}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                resolver.validate_release(data)


if __name__ == "__main__":
    unittest.main()

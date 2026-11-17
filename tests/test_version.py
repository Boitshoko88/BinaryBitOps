import unittest

from binarybitops.version import BuildInfo, load_build_info


class BuildInfoTests(unittest.TestCase):
    def test_defaults_are_safe(self):
        build = load_build_info({})
        self.assertEqual(build.version, "0.1.0")
        self.assertEqual(build.git_sha, "unknown")
        self.assertEqual(build.build_date, "unknown")
        self.assertEqual(build.image_ref, "local")

    def test_valid_values_are_accepted(self):
        build = load_build_info({
            "APP_VERSION": "0.1.0-rc.1",
            "GIT_SHA": "1ab7ca0",
            "BUILD_DATE": "2026-11-17T09:30:00Z",
            "IMAGE_REF": "registry.example/binarybitops-demo@sha256:" + "a" * 64,
        })
        self.assertEqual(build.git_sha, "1ab7ca0")
        self.assertEqual(build.version, "0.1.0-rc.1")

    def test_invalid_sha_is_rejected(self):
        for value in ("not-a-sha", "../etc/passwd", "12345", "TRUNCATED"):
            with self.subTest(value=value):
                self.assertEqual(load_build_info({"GIT_SHA": value}).git_sha, "unknown")

    def test_labels_cannot_inject_markup(self):
        build = load_build_info({
            "APP_VERSION": "<script>",
            "BUILD_DATE": '"><img src=x>',
            "IMAGE_REF": "registry/app:1\n",
        })
        self.assertEqual(build.version, "0.1.0")
        self.assertEqual(build.build_date, "unknown")
        # A trailing newline is stripped, not accepted as a label break-out.
        self.assertEqual(build.image_ref, "registry/app:1")
        self.assertNotIn("\n", load_build_info({"IMAGE_REF": "registry/app:1\n"}).image_ref)

    def test_serialisation_shape(self):
        payload = BuildInfo().as_dict()
        self.assertEqual(payload["service"], "binarybitops-demo")
        self.assertEqual(set(payload), {"service", "version", "git_sha", "build_date", "image_ref"})


if __name__ == "__main__":
    unittest.main()

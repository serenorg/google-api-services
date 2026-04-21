# Critical regression test for serenorg/google-api-services#15.
#
# Every cloudbuild-*.yaml at the repo root MUST contain both a docker
# build step and a Cloud Run deploy step. Build-only pipelines silently
# skip production rollout and caused the false-positive serenorg/seren-core#143
# (stale Gmail revision reported as a gateway bug).

from __future__ import annotations

import pathlib
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# The auth deploy wiring is separate from the others; keep this list
# anchored on the filename and do not exclude new configs so a future
# cloudbuild-*.yaml that someone adds is covered automatically.
CLOUDBUILD_GLOB = "cloudbuild-*.yaml"


class CloudBuildDeployCoverageTests(unittest.TestCase):
    def test_every_cloudbuild_config_builds_and_deploys(self):
        configs = sorted(REPO_ROOT.glob(CLOUDBUILD_GLOB))
        self.assertGreater(
            len(configs),
            0,
            "No cloudbuild-*.yaml files found — test is looking in the wrong directory.",
        )

        missing_deploy: list[str] = []
        missing_build: list[str] = []

        for config in configs:
            text = config.read_text()
            # Build step: any Cloud Build step invoking `docker` with `build`.
            has_build = "cloud-builders/docker" in text and "'build'" in text
            # Deploy step: a `gcloud run deploy` invocation. Accept either the
            # gcloud builder image or an inline entrypoint.
            has_deploy = "'run'" in text and "'deploy'" in text

            if not has_build:
                missing_build.append(config.name)
            if not has_deploy:
                missing_deploy.append(config.name)

        self.assertEqual(
            missing_build,
            [],
            f"cloudbuild files missing a docker build step: {missing_build}",
        )
        self.assertEqual(
            missing_deploy,
            [],
            "cloudbuild files missing a `gcloud run deploy` step "
            f"(they only build+push, production will not roll out): {missing_deploy}",
        )

    def test_deploy_pins_image_to_commit_sha(self):
        """Deploys must reference $COMMIT_SHA, not :latest.

        Pinning to :latest deploys whatever was last pushed — including
        concurrent builds — and makes rollback-by-SHA impossible. Every
        deploy step must use $COMMIT_SHA in its --image flag.
        """
        offenders: list[str] = []
        for config in sorted(REPO_ROOT.glob(CLOUDBUILD_GLOB)):
            text = config.read_text()
            if "'deploy'" not in text:
                continue  # covered by the previous test
            # Find the --image= line in the deploy step and assert SHA pinning.
            image_lines = [
                line.strip()
                for line in text.splitlines()
                if "--image=" in line
            ]
            if not any("$COMMIT_SHA" in line for line in image_lines):
                offenders.append(config.name)

        self.assertEqual(
            offenders,
            [],
            "cloudbuild deploy steps must pin --image to $COMMIT_SHA, "
            f"not :latest (non-deterministic rollout): {offenders}",
        )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.config import load_manifest, parse_repos
from src.git import ensure_workspace_gitignore
from src.rtk import rtk_asset_name_for_platform


ROOT = Path(__file__).resolve().parents[1]


class WorkspaceManifestTests(unittest.TestCase):
    def test_rtk_asset_can_be_resolved_for_current_platform(self) -> None:
        asset = rtk_asset_name_for_platform()

        self.assertTrue(asset.startswith("rtk-"))
        self.assertTrue(asset.endswith((".zip", ".tar.gz")))

    def test_default_repositories_and_branches(self) -> None:
        repos = parse_repos(load_manifest(ROOT / "repos.manifest.json"), ["all"])

        self.assertEqual(
            [(repo.key, repo.dir, repo.branch) for repo in repos],
            [
                ("nebula", "nebula", "development"),
                ("nebula-studio", "nebula-studio", "development"),
            ],
        )

    def test_ignore_rules_are_complete_and_idempotent(self) -> None:
        repos = parse_repos(load_manifest(ROOT / "repos.manifest.json"), ["all"])
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            ensure_workspace_gitignore(workspace, repos)
            first = (workspace / ".gitignore").read_text(encoding="utf-8")
            ensure_workspace_gitignore(workspace, repos)
            second = (workspace / ".gitignore").read_text(encoding="utf-8")

        self.assertIn("/nebula/", first)
        self.assertIn("/nebula-studio/", first)
        self.assertIn(".venv/", first)
        self.assertEqual(first, second)

    def test_only_missing_ignore_rules_are_appended(self) -> None:
        repos = parse_repos(load_manifest(ROOT / "repos.manifest.json"), ["all"])
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            gitignore = workspace / ".gitignore"
            gitignore.write_text(
                "# Nested repositories (managed through repos.manifest.json)\n"
                "/nebula/\n"
                "/nebula-studio/\n",
                encoding="utf-8",
            )

            ensure_workspace_gitignore(workspace, repos)
            text = gitignore.read_text(encoding="utf-8")

        self.assertEqual(text.count("/nebula/"), 1)
        self.assertEqual(text.count("/nebula-studio/"), 1)
        self.assertEqual(
            text.count("# Nested repositories (managed through repos.manifest.json)"),
            1,
        )
        self.assertIn(".venv/", text)


if __name__ == "__main__":
    unittest.main()

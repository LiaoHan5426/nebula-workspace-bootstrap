from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.config import load_manifest, parse_repos
from src.crg import (
    configure_hermes_crg,
    graph_repositories,
    hermes_mcp_add_command,
    sanitized_python_environment,
    stale_registered_paths,
    unregister_repo_alias,
)
from src.knowledge import knowledge_repo, project_repos, run_knowledge_refresh


ROOT = Path(__file__).resolve().parents[1]


class KnowledgeNavigationBootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repos = parse_repos(load_manifest(ROOT / "repos.manifest.json"), ["all"])

    def test_manifest_declares_portable_knowledge_repository(self) -> None:
        knowledge = knowledge_repo(self.repos)

        self.assertEqual(knowledge.key, "agent-memory")
        self.assertEqual(knowledge.dir, ".knowledge/agent-memory")
        self.assertEqual(knowledge.branch, "main")
        self.assertEqual(knowledge.role, "knowledge")
        self.assertFalse(knowledge.build_graph)

    def test_only_source_repositories_are_graphed_and_refreshed(self) -> None:
        self.assertEqual(
            [repo.key for repo in graph_repositories(self.repos)],
            ["nebula", "nebula-studio"],
        )
        self.assertEqual(
            [repo.project_id for repo in project_repos(self.repos)],
            ["LiaoHan5426--nebula", "LiaoHan5426--nebula-studio"],
        )

    def test_hermes_mcp_add_uses_workspace_venv_executable(self) -> None:
        command = hermes_mcp_add_command(Path("C:/work/nebula-workspace/.venv"))

        self.assertEqual(command[:4], ["hermes", "mcp", "add", "code-review-graph"])
        self.assertIn("code-review-graph.exe", command[command.index("--command") + 1])
        self.assertEqual(command[-4:], ["--env", "PYTHONPATH=", "--args", "serve"])

    def test_workspace_python_does_not_inherit_hermes_pythonpath(self) -> None:
        environment = sanitized_python_environment(
            {"PATH": "C:/Windows", "PYTHONPATH": "E:/ai/Hermes/venv/site-packages"}
        )

        self.assertEqual(environment["PATH"], "C:/Windows")
        self.assertNotIn("PYTHONPATH", environment)

    def test_hermes_mcp_registration_answers_both_idempotent_prompts(self) -> None:
        with patch("src.crg.shutil.which", return_value="hermes"), patch(
            "src.crg.subprocess.run"
        ) as run_process, patch("src.crg.subprocess.check_call") as check_call:
            configure_hermes_crg(Path("C:/work/nebula-workspace/.venv"))

        self.assertEqual(run_process.call_args.kwargs["input"], "y\ny\n")
        self.assertTrue(run_process.call_args.kwargs["check"])
        self.assertEqual(
            check_call.call_args.args[0],
            [
                "hermes",
                "config",
                "set",
                "mcp_servers.code-review-graph.enabled",
                "true",
                "--force",
            ],
        )

    def test_knowledge_refresh_uses_workspace_relative_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            vault = workspace / ".knowledge" / "agent-memory"
            script = vault / "scripts" / "project_navigation.py"
            script.parent.mkdir(parents=True)
            script.write_text("print('stub')\n", encoding="utf-8")
            calls: list[tuple[list[str], Path | None]] = []

            run_knowledge_refresh(
                workspace,
                self.repos,
                python_executable="python",
                runner=lambda command, cwd=None: calls.append((command, cwd)),
            )

        self.assertEqual(len(calls), 1)
        command, cwd = calls[0]
        self.assertEqual(command[0], "python")
        self.assertEqual(Path(command[1]), script)
        self.assertEqual(command[2:4], ["refresh", "--workspace-root"])
        self.assertEqual(Path(command[4]), workspace)
        self.assertEqual(cwd, vault)

    def test_missing_crg_alias_is_ignored_during_portable_reregistration(self) -> None:
        with patch("src.crg.subprocess.run") as run_process:
            run_process.return_value.returncode = 1

            unregister_repo_alias("code-review-graph", "nebula", Path("C:/work"))

        call = run_process.call_args
        self.assertEqual(call.args[0], ["code-review-graph", "unregister", "nebula"])
        self.assertEqual(call.kwargs["cwd"], "C:\\work")
        self.assertNotIn("PYTHONPATH", call.kwargs["env"])
        self.assertEqual(call.kwargs["creationflags"], 0x08000000)
        self.assertFalse(call.kwargs["check"])

    def test_only_missing_registry_paths_are_pruned(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            existing = root / "existing"
            existing.mkdir()
            missing = root / "moved-workspace"
            registry = root / "registry.json"
            registry.write_text(
                json.dumps(
                    {
                        "repos": [
                            {"path": str(existing), "alias": "current"},
                            {"path": str(missing), "alias": "old"},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            stale = stale_registered_paths(registry)

        self.assertEqual(stale, [str(missing)])


if __name__ == "__main__":
    unittest.main()

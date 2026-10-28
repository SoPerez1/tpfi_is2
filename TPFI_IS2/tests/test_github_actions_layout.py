"""Assert the published repository's discoverable Actions and project paths."""

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
PROJECT = REPO / "TPFI_IS2"
WORKFLOWS = ("ci.yml", "docs.yml")
BRANCHES = ["main", "tpfi/docs-automation", "tpfi/aws-evidence", "ci/tpfi-actions-root"]


def load_workflow(name):
    """Load the public repository-root workflow, not a nested template."""
    return yaml.load((REPO / ".github/workflows" / name).read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def test_repository_root_discovers_both_workflows_and_keeps_templates():
    for name in WORKFLOWS:
        assert (REPO / ".github/workflows" / name).is_file()
        assert (PROJECT / ".github/workflows" / name).is_file()


def test_root_workflows_validate_only_authorized_push_refs_and_pr_events():
    for name in WORKFLOWS:
        workflow = load_workflow(name)
        assert workflow["on"]["push"]["branches"] == BRANCHES
        assert workflow["on"]["pull_request"]["types"] == ["opened", "synchronize", "reopened", "ready_for_review"]
        assert "workflow_dispatch" in workflow["on"]
        assert workflow["permissions"] == {}


def test_every_shell_step_runs_in_project_with_bash_pipefail():
    for name in WORKFLOWS:
        workflow = load_workflow(name)
        for job in workflow["jobs"].values():
            if any("run" in step for step in job["steps"]):
                assert job["defaults"]["run"] == {"working-directory": "TPFI_IS2", "shell": "bash"}
    ci = load_workflow("ci.yml")
    report = next(step["run"] for step in ci["jobs"]["coverage"]["steps"] if step.get("name") == "Coverage report")
    assert "coverage report | tee -a $GITHUB_STEP_SUMMARY" in report
    assert ci["jobs"]["coverage"]["defaults"]["run"]["shell"] == "bash"


def test_artifact_actions_resolve_paths_from_repository_root():
    ci = load_workflow("ci.yml")
    upload = next(step for step in ci["jobs"]["test"]["steps"] if "actions/upload-artifact@" in step.get("uses", ""))
    coverage_steps = ci["jobs"]["coverage"]["steps"]
    download = next(step for step in coverage_steps if "actions/download-artifact@" in step.get("uses", ""))
    assert upload["with"]["path"] == "TPFI_IS2/.coverage.*"
    assert upload["with"]["include-hidden-files"] == "true"
    assert download["with"]["path"] == "TPFI_IS2"
    assert download["with"]["merge-multiple"] == "true"
    assert "coverage combine" in next(step["run"] for step in coverage_steps if step.get("name") == "Combine coverage")
    docs = load_workflow("docs.yml")
    pages = next(
        step for step in docs["jobs"]["build"]["steps"] if "actions/upload-pages-artifact@" in step.get("uses", "")
    )
    assert pages["with"]["path"] == "TPFI_IS2/site"


def test_ci_keeps_assignment_checks_matrix_and_aggregate_result():
    ci = load_workflow("ci.yml")
    assert set(ci["jobs"]) == {"lint", "type-check", "security", "test", "coverage", "all-checks-pass"}
    assert ci["jobs"]["test"]["strategy"]["matrix"]["python-version"] == ["3.12", "3.13", "3.14"]
    commands = "\n".join(step.get("run", "") for job in ci["jobs"].values() for step in job["steps"])
    for check in (
        "ruff format --check",
        "black --check",
        "ruff check --select D",
        "ruff check .",
        "mypy",
        "pyright",
        "bandit -r",
        "coverage run -m pytest",
        "coverage combine",
        "coverage report",
    ):
        assert check in commands
    assert "ty check" not in commands
    assert ci["jobs"]["all-checks-pass"]["needs"] == ["lint", "type-check", "security", "test", "coverage"]
    assert "re-actors/alls-green@" in ci["jobs"]["all-checks-pass"]["steps"][0]["uses"]
    assert "fail_under = 85" in (PROJECT / "pyproject.toml").read_text(encoding="utf-8")

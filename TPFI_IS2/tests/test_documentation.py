"""Check the generated application API and the read-only PR documentation gate."""

from html.parser import HTMLParser
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MODULES = {
    "storage": ("MemoryCorporateDataGateway", "merge_record", "AwsCorporateDataSingleton"),
    "proxy": ("CorporateDataProxy", "set_fields"),
    "observer": ("CorporateDataObserver", "subscribe"),
    "proxy_server": ("ProxyApplicationServer", "handle_request"),
    "singleton_client": ("SingletonClient", "build_request"),
    "observer_client": ("ObserverClient", "listen"),
    "http_transport": ("HTTPRequestError", "read_request"),
}


class Anchors(HTMLParser):
    """Collect published HTML IDs without relying on pdoc's styling."""

    def __init__(self):
        super().__init__()
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        self.ids.update(value for name, value in attrs if name == "id")


def test_generated_api_contains_application_modules_and_members():
    for module, members in MODULES.items():
        page = ROOT / "docs/html/tpfi_is2" / f"{module}.html"
        assert page.is_file(), f"Missing generated API page: {module}"
        parser = Anchors()
        parser.feed(page.read_text(encoding="utf-8"))
        for member in members:
            assert any(anchor == member or anchor.endswith(f".{member}") for anchor in parser.ids), (module, member)


def test_yaml_parser_is_declared_in_the_test_dependency_group():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    test_dependencies = pyproject.split("test = [", 1)[1].split("]", 1)[0]
    assert '"PyYAML>=6.0"' in test_dependencies


def test_docs_workflow_builds_on_pr_and_deploys_only_after_gated_main_events():
    workflow = yaml.load((ROOT / ".github/workflows/docs.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert "pull_request" in workflow["on"]
    assert "workflow_dispatch" in workflow["on"]  # Preserve manual validation.
    assert "main" in workflow["on"]["push"]["branches"]
    assert workflow["permissions"] == {}
    assert workflow["concurrency"]["group"] == "docs-deploy"
    assert workflow["concurrency"]["cancel-in-progress"] == "false"
    build = workflow["jobs"]["build"]
    assert build["permissions"] == {"contents": "read"}
    assert "if" not in build
    commands = [step.get("run", "") for step in build["steps"]]
    assert any("pdoc tpfi_is2 tpfi_is2.storage" in command and "-o docs/html" in command for command in commands)
    assert any("zensical build --clean" in command for command in commands)
    allowed_deployment = (
        "${{ (github.event_name == 'push' || github.event_name == 'workflow_dispatch') "
        "&& github.ref == 'refs/heads/main' && vars.DOCS_DEPLOYMENT_ENABLED == 'true' }}"
    )
    page_steps = [
        step
        for step in build["steps"]
        if "actions/configure-pages@" in step.get("uses", "")
        or "actions/upload-pages-artifact@" in step.get("uses", "")
    ]
    assert len(page_steps) == 2
    for step in page_steps:
        assert step["if"] == allowed_deployment
        if "actions/upload-pages-artifact@" in step["uses"]:
            assert step["with"]["path"] == "site"
    deploy = workflow["jobs"]["deploy"]
    assert deploy["needs"] == "build"
    assert deploy["if"] == allowed_deployment
    assert deploy["permissions"] == {"pages": "write", "id-token": "write"}

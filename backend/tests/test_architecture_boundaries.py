import ast
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = BACKEND_ROOT / "app"


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


class ArchitectureBoundaryTests(unittest.TestCase):
    def test_application_services_do_not_depend_on_concrete_adapters(self):
        compatibility_facades = {"ai_providers.py", "object_storage.py"}
        violations: list[str] = []
        for path in (APP_ROOT / "services").glob("*.py"):
            if path.name in compatibility_facades:
                continue
            concrete_imports = sorted(
                module
                for module in imported_modules(path)
                if module == "app.infrastructure" or module.startswith("app.infrastructure.")
            )
            if concrete_imports:
                violations.append(f"{path.name}: {', '.join(concrete_imports)}")
        self.assertEqual(violations, [])

    def test_http_endpoints_do_not_import_celery_tasks_or_adapters(self):
        violations: list[str] = []
        for path in (APP_ROOT / "api" / "v1" / "endpoints").glob("*.py"):
            forbidden = sorted(
                module
                for module in imported_modules(path)
                if module == "app.tasks"
                or module.startswith("app.infrastructure")
            )
            if forbidden:
                violations.append(f"{path.name}: {', '.join(forbidden)}")
        self.assertEqual(violations, [])

    def test_vendor_adapters_are_selected_only_at_composition_boundaries(self):
        allowed = {
            APP_ROOT / "bootstrap.py",
            APP_ROOT / "services" / "ai_providers.py",
            APP_ROOT / "services" / "object_storage.py",
        }
        violations: list[str] = []
        for path in APP_ROOT.rglob("*.py"):
            if path in allowed or "infrastructure" in path.parts:
                continue
            if any(module.startswith("app.infrastructure") for module in imported_modules(path)):
                violations.append(str(path.relative_to(BACKEND_ROOT)))
        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Repository structural invariant checks for recurring mistake classes.

Each check corresponds to a mistake class that recurred in git history and
emits an actionable message naming the file, type, or function to use instead.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app"
TEMPLATES_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"
JS_DIR = STATIC_DIR / "js"

LLM_PROVIDER_OWNERS = {
    Path("app/services/llm/factory.py"),
    Path("app/services/llm/providers.py"),
}
GENAI_CLIENT_OWNERS = {
    Path("app/services/llm/providers.py"),
    Path("app/services/image_generation_service.py"),
}
EAGER_CLIENT_CALLEES = {
    "AsyncOpenAI",
    "Client",
    "FeedbackService",
    "GeminiService",
    "ImageGenerationService",
    "OpenAI",
    "OpenAIService",
    "StateStorageService",
    "TelemetryService",
    "create_client",
    "create_flash_lite",
    "create_for_use_case",
}

JS_IMPORT_WITH_VERSION_RE = re.compile(
    r"""(?:import\s+[^;]*?\s+from\s+|import\s*\(\s*)['"]([^'"]+\.js\?v=[^'"]+)['"]"""
)
TEMPLATE_MANUAL_VERSION_RE = re.compile(
    r"""(?:/static/[^"'\s>]+\?v=|url_for\(\s*['"]static['"][^)]*\)\s*\}\}\?v=)"""
)
STATIC_URL_CALL_RE = re.compile(r"""static_url\(\s*['"]([^'"]+)['"]\s*\)""")
SUMMARY_LIST_ATTRS = {"chapter_summaries", "summary_chapter_titles"}


def _rel(path: Path) -> Path:
    return path.relative_to(ROOT)


def check_js_imports(root: Path = ROOT) -> list[str]:
    violations: list[str] = []
    js_dir = root / "app/static/js"
    if not js_dir.exists():
        return violations
    for js_file in sorted(js_dir.glob("*.js")):
        rel = js_file.relative_to(root)
        text = js_file.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), 1):
            if JS_IMPORT_WITH_VERSION_RE.search(line):
                violations.append(
                    f"{rel}:{lineno}: [js-manual-version-query] Do not hardcode `?v=` on JS module imports. "
                    "Use a bare relative path (`./module.js`); `app/templates/base.html` emits a content-hashed "
                    "`<script type=\"importmap\">` from `app/utils/static_assets.py` so every import shares one instance."
                )
    return violations


def check_templates(root: Path = ROOT) -> list[str]:
    violations: list[str] = []
    templates_dir = root / "app/templates"
    static_dir = root / "app/static"
    if not templates_dir.exists():
        return violations
    for tpl in sorted(templates_dir.rglob("*.html")):
        rel = tpl.relative_to(root)
        text = tpl.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), 1):
            if TEMPLATE_MANUAL_VERSION_RE.search(line):
                violations.append(
                    f"{rel}:{lineno}: [template-manual-version-query] Do not hardcode `?v=` on static URLs in Jinja templates. "
                    "Use `{{ static_url('...') }}` from `app/utils/static_assets.py`."
                )
            for match in STATIC_URL_CALL_RE.finditer(line):
                asset = match.group(1).lstrip("/").removeprefix("static/")
                target = (static_dir / asset).resolve()
                if not target.is_relative_to(static_dir.resolve()) or not target.is_file():
                    violations.append(
                        f"{rel}:{lineno}: [static-asset-exists] `static_url('{match.group(1)}')` points to missing file "
                        f"`app/static/{asset}`."
                    )
    return violations


def _attr_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _is_maybe_single_execute_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "execute"
        and isinstance(node.func.value, ast.Call)
        and isinstance(node.func.value.func, ast.Attribute)
        and node.func.value.func.attr == "maybe_single"
    )


def _node_uses_summary_lock(node: ast.AST) -> bool:
    if not isinstance(node, ast.AsyncWith):
        return False
    for item in node.items:
        ctx = item.context_expr
        if isinstance(ctx, ast.Attribute) and ctx.attr == "summary_lock":
            return True
    return False


def _is_summary_list_mutation(node: ast.AST) -> bool:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if (
                isinstance(target, ast.Subscript)
                and isinstance(target.value, ast.Attribute)
                and target.value.attr in SUMMARY_LIST_ATTRS
            ):
                return True
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in {"append", "extend", "insert", "clear", "pop"}
        and isinstance(node.func.value, ast.Attribute)
        and node.func.value.attr in SUMMARY_LIST_ATTRS
    )


def _walk_summary_mutations(
    node: ast.AST,
    *,
    under_lock: bool,
    rel: Path,
    violations: list[str],
) -> None:
    now_locked = under_lock or _node_uses_summary_lock(node)
    if not now_locked and _is_summary_list_mutation(node):
        violations.append(
            f"{rel}:{getattr(node, 'lineno', 1)}: [summary-list-lock-discipline] Mutating "
            "`state.chapter_summaries` or `state.summary_chapter_titles` outside `async with state.summary_lock:`. "
            "Wrap the write in `async with state.summary_lock:` or route through `_store_summary_safe` in "
            "`app/services/websocket/choice_processor.py`."
        )
    for child in ast.iter_child_nodes(node):
        _walk_summary_mutations(
            child, under_lock=now_locked, rel=rel, violations=violations
        )


def _is_main_guard(stmt: ast.stmt) -> bool:
    return (
        isinstance(stmt, ast.If)
        and isinstance(stmt.test, ast.Compare)
        and isinstance(stmt.test.left, ast.Name)
        and stmt.test.left.id == "__name__"
        and len(stmt.test.ops) == 1
        and isinstance(stmt.test.ops[0], ast.Eq)
        and len(stmt.test.comparators) == 1
        and isinstance(stmt.test.comparators[0], ast.Constant)
        and stmt.test.comparators[0].value == "__main__"
    )


def check_python_invariants(root: Path = ROOT) -> list[str]:
    violations: list[str] = []
    app_dir = root / "app"
    if not app_dir.exists():
        return violations

    for py_file in sorted(app_dir.rglob("*.py")):
        rel = py_file.relative_to(root)
        source = py_file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(rel))

        # 1. LLM provider bypass checks
        if rel not in LLM_PROVIDER_OWNERS:
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module in {
                    "app.services.llm",
                    "app.services.llm.providers",
                    "openai",
                }:
                    for alias in node.names:
                        if alias.name in {"OpenAIService", "GeminiService", "AsyncOpenAI", "OpenAI"}:
                            violations.append(
                                f"{rel}:{node.lineno}: [llm-provider-bypass] Do not import `{alias.name}` directly. "
                                "Use `LLMServiceFactory.create_for_use_case(...)` from `app/services/llm/factory.py`."
                            )
                if isinstance(node, ast.Call):
                    callee = _attr_name(node.func)
                    if callee in {"OpenAIService", "GeminiService", "AsyncOpenAI", "OpenAI"}:
                        violations.append(
                            f"{rel}:{node.lineno}: [llm-provider-bypass] Do not instantiate `{callee}` directly. "
                            "Use `LLMServiceFactory.create_for_use_case(...)` from `app/services/llm/factory.py`."
                        )

        if rel not in GENAI_CLIENT_OWNERS:
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "Client"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "genai"
                ):
                    violations.append(
                        f"{rel}:{node.lineno}: [llm-provider-bypass] Do not instantiate `genai.Client` directly. "
                        "Use `LLMServiceFactory.create_for_use_case(...)` or `ImageGenerationService`."
                    )

        # 2. Module-level eager client instantiation in app/services/ and app/routers/
        if rel.parts[:2] in {("app", "services"), ("app", "routers")}:
            for stmt in tree.body:
                if isinstance(
                    stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                ) or _is_main_guard(stmt):
                    continue
                for node in ast.walk(stmt):
                    if isinstance(node, ast.Call):
                        callee = _attr_name(node.func)
                        if callee in EAGER_CLIENT_CALLEES:
                            violations.append(
                                f"{rel}:{node.lineno}: [eager-external-client-import] Do not call `{callee}()` at module import time. "
                                "Instantiate external clients lazily inside a getter or request handler (see "
                                "`app/services/websocket/content_generator.py:get_llm_service`)."
                            )

        # 3. Direct `.data` dereference on `.maybe_single().execute()`
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Attribute)
                and node.attr == "data"
                and _is_maybe_single_execute_call(node.value)
            ):
                violations.append(
                    f"{rel}:{node.lineno}: [supabase-maybe-single-null-guard] Do not dereference `.data` directly on "
                    "`.maybe_single().execute()`. Supabase 2.33 may return `None`; check `if response and response.data:` "
                    "(see `app/services/state_storage_service.py`)."
                )

        # 4. Unlocked writes to summary lists in websocket handlers
        if rel.parts[:3] == ("app", "services", "websocket"):
            _walk_summary_mutations(tree, under_lock=False, rel=rel, violations=violations)

    return violations


def run_all_checks(root: Path = ROOT) -> list[str]:
    return [
        *check_js_imports(root),
        *check_templates(root),
        *check_python_invariants(root),
    ]


def main() -> int:
    violations = run_all_checks(ROOT)
    if violations:
        print(f"Found {len(violations)} repository invariant violation(s):", file=sys.stderr)
        for violation in violations:
            print(f"  - {violation}", file=sys.stderr)
        return 1
    print("Repository invariant checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

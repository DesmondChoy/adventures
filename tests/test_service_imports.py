import os
import subprocess
import sys
from pathlib import Path


def test_application_modules_do_not_create_clients_during_import() -> None:
    """Importing any app service or router must not instantiate external clients."""
    project_root = Path(__file__).resolve().parents[1]
    import_script = """
import importlib
import pkgutil
import dotenv
import openai
import supabase
from google import genai


def fail_if_client_is_created(name):
    def _fail(*args, **kwargs):
        raise AssertionError(f"{name} created during module import")
    return _fail


dotenv.load_dotenv = lambda *args, **kwargs: False
genai.Client = fail_if_client_is_created("genai.Client")
openai.AsyncOpenAI = fail_if_client_is_created("openai.AsyncOpenAI")
openai.OpenAI = fail_if_client_is_created("openai.OpenAI")
supabase.create_client = fail_if_client_is_created("supabase.create_client")

for pkg_name in ("app.models", "app.auth", "app.services", "app.routers"):
    pkg = importlib.import_module(pkg_name)
    for mod in pkgutil.walk_packages(pkg.__path__, prefix=f"{pkg_name}."):
        importlib.import_module(mod.name)

import tests.simulations.generate_chapter_summaries
"""

    clean_environment = os.environ.copy()
    for variable_name in (
        "GOOGLE_API_KEY",
        "OPENAI_API_KEY",
        "SUPABASE_ANON_KEY",
        "SUPABASE_KEY",
        "SUPABASE_SERVICE_KEY",
        "SUPABASE_URL",
    ):
        clean_environment.pop(variable_name, None)

    result = subprocess.run(
        [sys.executable, "-c", import_script],
        cwd=project_root,
        env=clean_environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr

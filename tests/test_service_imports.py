import os
import subprocess
import sys
from pathlib import Path


def test_application_modules_do_not_create_clients_during_import() -> None:
    """Application imports must not require external-service credentials."""
    project_root = Path(__file__).resolve().parents[1]
    import_script = """
import dotenv
from google import genai


def fail_if_client_is_created(*args, **kwargs):
    raise AssertionError("Gemini client created during module import")


dotenv.load_dotenv = lambda *args, **kwargs: False
genai.Client = fail_if_client_is_created

import app.services.websocket.content_generator
import app.services.websocket.summary_generator
import tests.simulations.generate_chapter_summaries
"""

    clean_environment = os.environ.copy()
    for variable_name in (
        "GOOGLE_API_KEY",
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

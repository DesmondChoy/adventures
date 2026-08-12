import json
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATE_MANAGER_PATH = PROJECT_ROOT / "app/static/js/adventureStateManager.js"


def test_fallback_uuid_uses_secure_random_bytes() -> None:
    module_source = STATE_MANAGER_PATH.read_text()
    script = f"""
        const source = {json.dumps(module_source)};
        const moduleUrl = 'data:text/javascript;base64,' + Buffer.from(source).toString('base64');
        const {{ AdventureStateManager }} = await import(moduleUrl);
        let calls = 0;
        const cryptoApi = {{
            getRandomValues(bytes) {{
                calls += 1;
                for (let index = 0; index < bytes.length; index += 1) {{
                    bytes[index] = index;
                }}
                return bytes;
            }}
        }};
        const manager = Object.create(AdventureStateManager.prototype);
        const uuid = manager.generateFallbackUuid(cryptoApi);
        console.log(JSON.stringify({{ uuid, calls }}));
    """

    result = subprocess.run(
        ["node", "--input-type=module", "--eval", script],
        check=True,
        capture_output=True,
        text=True,
    )
    output = json.loads(result.stdout)

    assert output == {
        "uuid": "00010203-0405-4607-8809-0a0b0c0d0e0f",
        "calls": 1,
    }
    assert "Math.random" not in module_source

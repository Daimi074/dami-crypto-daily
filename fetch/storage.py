import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate(name, data):
    from jsonschema import Draft202012Validator, FormatChecker

    schema = json.loads((ROOT / "schema" / (name + ".schema.json")).read_text("utf-8"))
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(data)


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=path.parent, delete=False, mode="w", encoding="utf-8"
    ) as f:
        try:
            json.dump(
                data, f, ensure_ascii=False, allow_nan=False, separators=(",", ":")
            )
            f.write("\n")
        except Exception:
            f.close()
            os.unlink(f.name)
            raise
    os.replace(f.name, path)

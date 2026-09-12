"""Write the API contract to openapi.yaml at the repository root.

Spec section 8: the hand-written contract is replaced by an export of
FastAPI's generated schema once the backend is real. Run `make openapi`, or
`uv run python scripts/export_openapi.py`, after changing any route.
"""
import os
import pathlib
import sys

import yaml

os.environ.setdefault("STAFF_PASSWORD", "export-only")
os.environ.setdefault("SESSION_SECRET", "export-only")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.main import create_app  # noqa: E402

TARGET = pathlib.Path(__file__).resolve().parents[2] / "openapi.yaml"


def main() -> None:
    schema = create_app().openapi()
    TARGET.write_text(
        "# Generated from the FastAPI app. Do not edit by hand:\n"
        "# run `uv run python scripts/export_openapi.py` from backend/.\n"
        + yaml.safe_dump(schema, sort_keys=False, width=100),
        encoding="utf-8",
    )
    print(f"wrote {TARGET}")


if __name__ == "__main__":
    main()

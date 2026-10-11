"""Write the OpenAPI schema the web app's TypeScript client is generated from.

    docker compose --profile serve run --rm --no-deps api python -m hclust_api.openapi
"""

import json
import sys
from pathlib import Path

from hclust_api.main import create_app

SCHEMA_PATH = Path(__file__).parents[2] / "openapi.json"


def schema() -> str:
    return json.dumps(create_app().openapi(), indent=2, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    SCHEMA_PATH.write_text(schema())
    print(f"wrote {SCHEMA_PATH}", file=sys.stderr)

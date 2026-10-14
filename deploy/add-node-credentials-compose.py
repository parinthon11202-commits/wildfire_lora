"""Add the private node credential file to the existing ForestGuard Compose service.

Run only on a copied release. The JSON remains outside the image/build context.
"""

from pathlib import Path
import sys


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: add-node-credentials-compose.py COMPOSE_FILE SECRET_FILE")
    compose_file = Path(sys.argv[1])
    secret_file = Path(sys.argv[2])
    if not secret_file.is_absolute() or not secret_file.is_file():
        raise SystemExit("secret file must exist at an absolute path")
    text = compose_file.read_text(encoding="utf-8")
    if "NODE_CREDENTIALS_FILE" in text or "node_credentials:" in text:
        raise SystemExit("node credentials already configured")

    start = text.index("  backend:\n")
    end = text.index("  cloudflared:\n", start)
    backend = text[start:end]
    environment = "    environment:\n      TZ: Asia/Bangkok\n"
    if backend.count(environment) != 1:
        raise SystemExit("unexpected backend environment structure")
    backend = backend.replace(
        environment,
        environment + "      NODE_CREDENTIALS_FILE: /run/secrets/node_credentials\n",
    )
    if backend.count("    depends_on:\n") != 1:
        raise SystemExit("unexpected backend dependencies structure")
    backend = backend.replace(
        "    depends_on:\n",
        "    secrets:\n      - node_credentials\n    depends_on:\n",
    )
    text = text[:start] + backend + text[end:]
    if text.count("\nsecrets:\n") != 1:
        raise SystemExit("unexpected top-level secrets structure")
    text = text.rstrip() + f"\n  node_credentials:\n    file: {secret_file}\n"
    compose_file.write_text(text, encoding="utf-8")
    print("Configured private node credentials for the Backend service")


if __name__ == "__main__":
    main()

"""Restore the matching Strata server.py backup and stop persistent prompt logging."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

from INSTALL import default_root, replace_atomically


def snapshot(path):
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()[:12]
    backup = path.with_name(path.name + f".prompt-log-before-restore.{digest}.bak")
    if not backup.exists():
        shutil.copy2(path, backup)
    elif backup.read_bytes() != data:
        raise RuntimeError(f"backup name collision: {backup}")
    return backup


def patched_from(original, variants):
    source = original.decode("utf-8")
    newline = "\r\n" if b"\r\n" in original else "\n"
    results = []
    for variant in variants:
        changed = source
        for item in variant["patches"]:
            before = item["old"].replace("\n", newline)
            after = item["new"].replace("\n", newline)
            if changed.count(before) != 1:
                break
            changed = changed.replace(before, after, 1)
        else:
            results.append(changed.encode("utf-8"))
    return results


def main():
    parser = argparse.ArgumentParser(description="Restore Strata before the prompt-log patch")
    parser.add_argument("--root", type=Path, default=default_root())
    parser.add_argument("--config", default="strata-nvfp4-nvfp4.json")
    args = parser.parse_args()
    server = args.root / "serve" / "server.py"
    config_path = args.root / args.config
    if not server.is_file() or not config_path.is_file():
        parser.error("Strata server.py or model config is missing; no file was changed")

    current_server = server.read_bytes()
    current_config_bytes = config_path.read_bytes()
    current_config = json.loads(current_config_bytes.decode("utf-8-sig"))
    if not isinstance(current_config, dict):
        parser.error("the model config is not a JSON object; no file was changed")

    variants = json.loads((Path(__file__).parent / "patch.json").read_text(encoding="utf-8"))["variants"]
    matches = []
    for backup in server.parent.glob(server.name + ".prompt-log-original*.bak"):
        original = backup.read_bytes()
        if current_server in patched_from(original, variants):
            matches.append((backup, original))
    if matches:
        if len({data for _, data in matches}) != 1:
            parser.error("multiple different backups match; no file was changed")
        chosen = matches[0]
    elif b"self.api_request_log: Path | None" in current_server:
        parser.error("the patched server.py has changed since installation; no file was changed")
    else:
        chosen = None

    original_config = None
    for backup in config_path.parent.glob(config_path.name + ".prompt-log-original*.bak"):
        data = backup.read_bytes()
        try:
            candidate = json.loads(data.decode("utf-8-sig"))
        except (UnicodeError, ValueError):
            continue
        if not isinstance(candidate, dict) or "api_request_log" in candidate:
            continue
        without_log = {key: value for key, value in current_config.items() if key != "api_request_log"}
        if candidate == without_log:
            original_config = data
            break

    if chosen:
        saved = snapshot(server)
        replace_atomically(server, chosen[1])
        print(f"Restored server.py from {chosen[0]}; patched copy saved to {saved}")
    else:
        print("server.py is not patched by this installer; left unchanged.")

    if original_config is not None and original_config != current_config_bytes:
        saved = snapshot(config_path)
        replace_atomically(config_path, original_config)
        print(f"Restored original model config; previous copy saved to {saved}")
    elif "api_request_log" in current_config:
        del current_config["api_request_log"]
        saved = snapshot(config_path)
        updated = (json.dumps(current_config, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        replace_atomically(config_path, updated)
        print(f"Removed api_request_log while preserving other settings; previous copy saved to {saved}")
    else:
        print("Prompt logging is already disabled in the model config.")
    print("Restart Strata. Existing prompt log files were kept for your review.")


if __name__ == "__main__":
    main()

"""Safely enable Strata's opt-in API request log on an existing Windows install."""
import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path


def replace_atomically(path, data):
    temporary = path.with_name(path.name + ".prompt-log.tmp")
    try:
        shutil.copy2(path, temporary)
        temporary.write_bytes(data)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def backup_once(path):
    original = path.read_bytes()
    backup = path.with_name(path.name + ".prompt-log-original.bak")
    if backup.exists() and backup.read_bytes() != original:
        digest = hashlib.sha256(original).hexdigest()[:12]
        backup = path.with_name(path.name + f".prompt-log-original.{digest}.bak")
    if backup.exists():
        if backup.read_bytes() != original:
            raise RuntimeError(f"backup name collision; {path} was not changed: {backup}")
    else:
        shutil.copy2(path, backup)
    return backup


def main():
    parser = argparse.ArgumentParser(description="Enable persistent Strata API prompt logging")
    parser.add_argument("--root", type=Path, default=Path(r"C:\Strata-main"))
    parser.add_argument("--config", default="strata-nvfp4-nvfp4.json")
    parser.add_argument("--log", default="strata-api-requests.jsonl")
    parser.add_argument("--disable", action="store_true", help="stop logging after the next Strata restart")
    args = parser.parse_args()

    server_path = args.root / "serve" / "server.py"
    config_path = args.root / args.config
    if not config_path.is_file():
        parser.error(f"missing config: {config_path}")
    original_config = config_path.read_bytes()
    config = json.loads(original_config.decode("utf-8-sig"))
    if not isinstance(config, dict):
        parser.error("the config must contain a JSON object")

    if args.disable:
        if "api_request_log" not in config:
            print("Prompt logging is already disabled.")
            return
        del config["api_request_log"]
    else:
        if not args.log.strip():
            parser.error("--log must be a non-empty file path")
        if not server_path.is_file():
            parser.error(f"missing server: {server_path}")
        original_server = server_path.read_bytes()
        source = original_server.decode("utf-8")
        newline = "\r\n" if b"\r\n" in original_server else "\n"
        patch_data = json.loads((Path(__file__).parent / "patch.json").read_text(encoding="utf-8"))
        variants = []
        for variant in patch_data["variants"]:
            pairs = [(item["old"].replace("\n", newline), item["new"].replace("\n", newline))
                     for item in variant["patches"]]
            variants.append((variant["name"], pairs))
        installed = [(name, pairs) for name, pairs in variants if all(source.count(new) == 1 for _, new in pairs)]
        available = [(name, pairs) for name, pairs in variants if all(source.count(before) == 1 for before, _ in pairs)]

        if len(installed) == 1:
            print("Strata server.py already has the prompt logging patch.")
        else:
            if len(installed) > 1 or len(available) != 1:
                parser.error("this Strata version differs from the tested versions; server.py was not changed")
            name, pairs = available[0]
            for before, after in pairs:
                source = source.replace(before, after, 1)
            compile(source, str(server_path), "exec")
            backup = backup_once(server_path)
            replace_atomically(server_path, source.encode("utf-8"))
            print(f"Patched {server_path} for {name}; original saved to {backup}")

        config["api_request_log"] = args.log

    updated = (json.dumps(config, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if updated != original_config:
        backup = backup_once(config_path)
        replace_atomically(config_path, updated)
        print(f"Updated {config_path}; original backup: {backup}")
    print("Restart Strata for this setting to take effect.")


if __name__ == "__main__":
    main()

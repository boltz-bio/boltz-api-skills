#!/usr/bin/env python3
"""Validate Boltz Codex plugin packaging and repository hygiene."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def add_issue(issues: list[str], message: str) -> None:
    issues.append(message)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def resolve_relative(base: Path, value: str) -> Path:
    if value.startswith("./"):
        value = value[2:]
    return (base / value).resolve()


def main() -> int:
    script_path = Path(__file__).resolve()
    plugin_root = script_path.parent.parent
    repo_root = plugin_root.parent
    manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
    marketplace_path = repo_root / ".agents" / "plugins" / "marketplace.json"

    issues: list[str] = []
    warnings: list[str] = []

    if not manifest_path.is_file():
        add_issue(issues, f"missing manifest: {manifest_path}")
        manifest = {}
    else:
        try:
            manifest = load_json(manifest_path)
        except json.JSONDecodeError as exc:
            add_issue(issues, f"manifest is not valid JSON: {exc}")
            manifest = {}

    required_manifest_fields = [
        "name",
        "version",
        "description",
        "author",
        "homepage",
        "repository",
        "license",
        "keywords",
        "skills",
        "interface",
    ]
    for field in required_manifest_fields:
        if field not in manifest:
            add_issue(issues, f"manifest missing required field: {field}")

    author = manifest.get("author", {})
    if not isinstance(author, dict) or not author.get("name"):
        add_issue(issues, "manifest author.name is required")

    interface = manifest.get("interface", {})
    required_interface_fields = [
        "displayName",
        "shortDescription",
        "longDescription",
        "developerName",
        "category",
        "capabilities",
        "websiteURL",
        "defaultPrompt",
    ]
    for field in required_interface_fields:
        if field not in interface:
            add_issue(issues, f"manifest interface missing field: {field}")

    if isinstance(manifest.get("skills"), str):
        skills_path = resolve_relative(plugin_root, manifest["skills"])
        if not skills_path.is_dir():
            add_issue(issues, f"skills path does not exist: {skills_path}")
    else:
        skills_path = plugin_root / "skills"

    text_files_to_scan = [manifest_path, repo_root / "README.md", plugin_root / "README.md"]
    for path in text_files_to_scan:
        if path.is_file():
            text = path.read_text()
            if "[TODO:" in text or "[TODO" in text:
                add_issue(issues, f"unresolved TODO placeholder found in {path}")

    optional_asset_fields = ["composerIcon", "logo"]
    for field in optional_asset_fields:
        value = interface.get(field)
        if value:
            asset_path = resolve_relative(plugin_root, value)
            if not asset_path.is_file():
                add_issue(issues, f"manifest interface.{field} path does not exist: {asset_path}")
    for value in interface.get("screenshots", []):
        asset_path = resolve_relative(plugin_root, value)
        if not asset_path.is_file():
            add_issue(issues, f"manifest screenshot path does not exist: {asset_path}")

    skill_dirs = sorted(path for path in skills_path.iterdir() if path.is_dir()) if skills_path.is_dir() else []
    if not skill_dirs:
        add_issue(issues, "no skill directories found under the declared skills path")
    for skill_dir in skill_dirs:
        skill_md = skill_dir / "SKILL.md"
        agent_yaml = skill_dir / "agents" / "openai.yaml"
        scripts_dir = skill_dir / "scripts"
        if not skill_md.is_file():
            add_issue(issues, f"missing SKILL.md: {skill_md}")
        if not agent_yaml.is_file():
            add_issue(issues, f"missing agents/openai.yaml: {agent_yaml}")
        if not scripts_dir.is_dir():
            warnings.append(f"skill has no scripts directory: {skill_dir}")

    pycache_hits = sorted(repo_root.rglob("__pycache__")) + sorted(repo_root.rglob("*.pyc"))
    if pycache_hits:
        for path in pycache_hits:
            add_issue(issues, f"bytecode artifact should not be tracked: {path}")

    if not marketplace_path.is_file():
        add_issue(issues, f"missing marketplace file: {marketplace_path}")
    else:
        try:
            marketplace = load_json(marketplace_path)
        except json.JSONDecodeError as exc:
            add_issue(issues, f"marketplace is not valid JSON: {exc}")
            marketplace = {}
        plugins = marketplace.get("plugins", [])
        if not isinstance(plugins, list):
            add_issue(issues, "marketplace plugins field must be a list")
            plugins = []
        entry = next((item for item in plugins if item.get("name") == manifest.get("name")), None)
        if entry is None:
            add_issue(issues, f"marketplace does not include plugin entry for {manifest.get('name')!r}")
        else:
            source = entry.get("source", {})
            if source.get("source") != "local":
                add_issue(issues, "marketplace entry source.source must be 'local'")
            source_path = source.get("path")
            if not isinstance(source_path, str):
                add_issue(issues, "marketplace entry source.path must be a string")
            else:
                resolved = resolve_relative(repo_root, source_path)
                if resolved != plugin_root.resolve():
                    add_issue(issues, f"marketplace source path does not resolve to plugin root: {resolved}")
            policy = entry.get("policy", {})
            if policy.get("installation") not in {"AVAILABLE", "NOT_AVAILABLE", "INSTALLED_BY_DEFAULT"}:
                add_issue(issues, "marketplace entry policy.installation is missing or invalid")
            if policy.get("authentication") not in {"ON_INSTALL", "ON_USE"}:
                add_issue(issues, "marketplace entry policy.authentication is missing or invalid")
            if not entry.get("category"):
                add_issue(issues, "marketplace entry category is required")

    if issues:
        print("FAIL")
        for issue in issues:
            print(f"- {issue}")
        if warnings:
            print("WARN")
            for warning in warnings:
                print(f"- {warning}")
        return 1

    print("PASS")
    print(f"- manifest: {manifest_path}")
    print(f"- marketplace: {marketplace_path}")
    print(f"- skills: {len(skill_dirs)}")
    if warnings:
        print("WARN")
        for warning in warnings:
            print(f"- {warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Install this repository's skills using only Python's standard library."""

import argparse
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile


def default_skills_dir():
    """Use CODEX_HOME when set, otherwise the standard per-user Codex home."""
    home = os.environ.get("CODEX_HOME")
    return (Path(home).expanduser() if home else Path.home() / ".codex") / "skills"


def default_agents_dir():
    home = os.environ.get("CODEX_HOME")
    return (Path(home).expanduser() if home else Path.home() / ".codex") / "agents"


def _is_link(path):
    # Windows junctions can also redirect a copy or replacement outside its tree.
    if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
        return True
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except FileNotFoundError:
        return False
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def _validate_source(source):
    if _is_link(source) or not source.is_dir():
        raise ValueError("skills source must be a real directory")
    skills = sorted(source.iterdir(), key=lambda p: p.name)
    skills = [p for p in skills if p.is_dir() or p.is_symlink()]
    if not skills:
        raise ValueError("no skills found in source directory")
    for skill in skills:
        if _is_link(skill) or not (skill / "SKILL.md").is_file():
            raise ValueError("invalid skill directory: " + skill.name)
        for root, dirs, files in os.walk(skill, followlinks=False):
            for name in dirs + files:
                if _is_link(Path(root) / name):
                    raise ValueError("symbolic links are not supported in skills: " + skill.name)
    return skills


def install_skills(source, target, *, replace=False, dry_run=False):
    """Return a report; replacements retain a uniquely named on-disk backup."""
    source = Path(source).expanduser()
    skills = _validate_source(source)
    return _install_entries(source, target, skills, "skill", replace=replace, dry_run=dry_run)


def install_roles(source, target, skills_dir, *, replace=False, dry_run=False):
    """Install role TOMLs with a portable absolute skill-directory substitution."""
    source = Path(source).expanduser()
    if _is_link(source) or not source.is_dir():
        raise ValueError("roles source must be a real directory")
    roles = sorted(source.glob("*.toml"), key=lambda p: p.name)
    if not roles:
        raise ValueError("no role TOMLs found in source directory")
    content = {}
    # Placeholder is embedded in TOML basic strings: escape quotes/control chars.
    skill_path = json.dumps(Path(skills_dir).expanduser().resolve().as_posix(), ensure_ascii=False)[1:-1]
    for role in roles:
        if _is_link(role) or not role.is_file():
            raise ValueError("role must be a real file: " + role.name)
        content[role.name] = role.read_text(encoding="utf-8").replace("{{SKILLS_DIR}}", skill_path)
    return _install_entries(source, target, roles, "role", replace=replace, dry_run=dry_run, content=content)


def _install_entries(source, target, entries, kind, *, replace, dry_run, content=None):
    target = Path(target).expanduser()
    if _is_link(target):
        raise ValueError("target directory must not be a symbolic link")
    source = source.resolve()
    target = target.resolve()
    if source == target or source in target.parents or target in source.parents:
        raise ValueError("source and target directories must not overlap")
    if target.exists() and not target.is_dir():
        raise ValueError("target must be a directory")
    backup_root = target / ".codex-expert-teams-backups"
    # Validate all requested replacements before modifying any skill.
    for skill in entries:
        destination = target / skill.name
        if replace and (destination.exists() or destination.is_symlink()):
            expected_type = destination.is_dir() if kind == "skill" else destination.is_file()
            if _is_link(destination) or not expected_type:
                raise ValueError("cannot replace wrong entry type or symbolic link: " + skill.name)
    if replace and (_is_link(backup_root) or (backup_root.exists() and not backup_root.is_dir())):
        raise ValueError("backup location must be a real directory")
    report = []
    for skill in entries:
        destination = target / skill.name
        exists = destination.exists() or destination.is_symlink()
        action = "skip" if exists and not replace else "replace" if exists else "install"
        item = {kind: skill.name, "action": action, "destination": str(destination)}
        report.append(item)
        if dry_run or action == "skip":
            continue
        target.mkdir(parents=True, exist_ok=True)
        # Copy first, then move the old directory aside. A failed copy leaves it intact.
        stage = Path(tempfile.mkdtemp(prefix=".codex-expert-stage-", dir=target))
        backup = None
        try:
            staged_skill = stage / skill.name
            if kind == "skill":
                shutil.copytree(skill, staged_skill)
            else:
                staged_skill.write_text(content[skill.name], encoding="utf-8")
            if exists:
                backup_root.mkdir(exist_ok=True)
                backup_session = Path(tempfile.mkdtemp(prefix="replacement-", dir=backup_root))
                backup = backup_session / skill.name
                destination.rename(backup)
                item["backup"] = str(backup)
            try:
                staged_skill.rename(destination)
            except Exception:
                if backup is not None:
                    backup.rename(destination)
                raise
        finally:
            shutil.rmtree(stage)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills-dir", type=Path, default=None, help="destination; defaults to CODEX_HOME/skills or ~/.codex/skills")
    parser.add_argument("--include-roles", action="store_true", help="also install role TOMLs; does not edit config.toml")
    parser.add_argument("--agents-dir", type=Path, default=None, help="role destination; defaults to CODEX_HOME/agents or ~/.codex/agents")
    parser.add_argument("--replace", action="store_true", help="replace existing skills while retaining a backup")
    parser.add_argument("--dry-run", action="store_true", help="report planned actions without writing files")
    args = parser.parse_args(argv)
    repository = Path(__file__).resolve().parents[1]
    skills_dir = args.skills_dir if args.skills_dir is not None else default_skills_dir()
    agents_dir = args.agents_dir if args.agents_dir is not None else default_agents_dir()
    try:
        if args.include_roles:
            # Check both sets before writing either; role errors should not cause a partial install.
            install_skills(repository / "skills", skills_dir, replace=args.replace, dry_run=True)
            install_roles(repository / "roles", agents_dir, skills_dir, replace=args.replace, dry_run=True)
        report = install_skills(repository / "skills", skills_dir, replace=args.replace, dry_run=args.dry_run)
        roles_report = install_roles(repository / "roles", agents_dir, skills_dir, replace=args.replace, dry_run=args.dry_run) if args.include_roles else []
    except (OSError, ValueError) as error:
        parser.exit(1, "Installation failed: " + str(error) + "\n")
    print(json.dumps({"dry_run": args.dry_run, "skills": report, "roles": roles_report}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

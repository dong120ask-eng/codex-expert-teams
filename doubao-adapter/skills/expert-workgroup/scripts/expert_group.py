"""Original, standard-library-only expert routing and local catalog helper.

Routing recommends work assignments; it does not launch agents or execute sources.
"""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def codex_home(value=None):
    return Path(value or os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser().resolve()


def roles():
    return read_json(SKILL_ROOT / "references" / "roles.json")["roles"]


def route(request, home):
    if not request.strip():
        raise ValueError("需求不能为空")
    selected = []
    text = request.casefold()
    for role in roles():
        matched = [word for word in role["keywords"] if word.casefold() in text]
        if role["id"] == "team_lead" or matched:
            item = dict(role)
            item["matched_keywords"] = matched
            item["skill_availability"] = {
                name: (home / "skills" / name / "SKILL.md").is_file()
                for name in role["skills"]
            }
            item["role_config_available"] = (home / "agents" / (role["id"] + ".toml")).is_file()
            selected.append(item)
    return {"suggestion_only": True, "max_parallel_agents": 3, "roles": selected,
            "note": "负责人根据项目实际情况调整；文件存在仅表示已安装，未证明工具或账号可用。"}


def catalog_entries(path, query):
    data = read_json(path)
    entries = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        raise ValueError("目录必须是包含 entries 数组的 JSON 对象")
    result = []
    for item in entries:
        if not isinstance(item, dict):
            raise ValueError("目录 entries 中存在非对象记录")
        fields = [str(item.get(key, "")) for key in ("id", "name", "category")]
        capabilities = item.get("capabilities", [])
        if not isinstance(capabilities, list):
            raise ValueError("目录 capabilities 必须是数组")
        fields.extend(str(value) for value in capabilities)
        if query.casefold() not in " ".join(fields).casefold():
            continue
        result.append({key: item.get(key) for key in (
            "id", "name", "category", "execution_status", "dependencies",
            "mapped_codex_skills", "private_path", "notes")})
    return {"local_reference_only": True, "count": len(result), "entries": result}


def install(home, catalog):
    catalog_path = None
    if catalog:
        catalog_path = Path(catalog).expanduser().resolve(strict=True)
        catalog_entries(catalog_path, "")
    home = Path(home).expanduser().resolve()
    skills_dir = home / "skills"
    # resolve detects Windows junctions as well as symbolic links. Do not let an
    # existing link redirect the explicitly selected installation directory.
    if skills_dir.is_symlink() or skills_dir.resolve() != skills_dir:
        raise ValueError("技能安装目录包含链接或 junction，拒绝写入: " + str(skills_dir))
    destination = skills_dir / "expert-workgroup"
    if destination.exists() or destination.is_symlink():
        raise ValueError("目标技能已存在，拒绝覆盖: " + str(destination))
    destination.parent.mkdir(parents=True, exist_ok=True)
    if skills_dir.is_symlink() or skills_dir.resolve() != skills_dir:
        raise ValueError("技能安装目录在创建时发生重定向，拒绝写入")
    # copytree with dirs_exist_ok=False refuses even a concurrently created target.
    shutil.copytree(SKILL_ROOT, destination,
                    ignore=shutil.ignore_patterns("__pycache__", "local-settings.json"))
    settings = {"schema_version": 1, "catalog": str(catalog_path) if catalog_path else None}
    (destination / "local-settings.json").write_text(
        json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"installed_skill": str(destination), "catalog_configured": bool(catalog_path),
            "note": "未修改全局配置或代理角色；新会话发现该技能。"}


def main(argv=None):
    parser = argparse.ArgumentParser(description="专家团角色建议、本地技能索引与安装")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="列出通用角色")
    routing = commands.add_parser("route", help="根据需求给出分工建议，不执行任务")
    routing.add_argument("request")
    routing.add_argument("--codex-home")
    searching = commands.add_parser("catalog", help="搜索本机私有索引，绝不执行源脚本")
    searching.add_argument("query", nargs="?", default="")
    searching.add_argument("--catalog")
    installing = commands.add_parser("install", help="安装原创协调技能；已有目标拒绝覆盖")
    installing.add_argument("--codex-home")
    installing.add_argument("--catalog")
    args = parser.parse_args(argv)
    try:
        if args.command == "list":
            result = {"roles": roles()}
        elif args.command == "route":
            result = route(args.request, codex_home(args.codex_home))
        elif args.command == "catalog":
            settings = SKILL_ROOT / "local-settings.json"
            catalog = args.catalog
            if not catalog and settings.is_file():
                local_settings = read_json(settings)
                if not isinstance(local_settings, dict):
                    raise ValueError("local-settings.json 必须是 JSON 对象")
                catalog = local_settings.get("catalog")
                if catalog is not None and not isinstance(catalog, str):
                    raise ValueError("local-settings.json 的 catalog 必须是路径字符串或 null")
            if not catalog:
                raise ValueError("请传入 --catalog 本地索引路径，或安装时配置目录")
            result = catalog_entries(catalog, args.query)
        else:
            result = install(codex_home(args.codex_home), args.catalog)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Adapt user-authorized local agent texts without publishing or executing them."""
import argparse
import hashlib
import json
import pathlib
import re


def adapt(text):
    text = text.lstrip('\ufeff').replace('\r\n', '\n')
    text = re.sub(r'^---\n.*?\n---\n', '', text, count=1, flags=re.S)
    result = []
    skip = None
    for line in text.splitlines():
        heading = re.match(r'^(#{1,6})\s+(.*)', line)
        if heading:
            level = len(heading[1])
            if skip is not None and level <= skip:
                skip = None
            if re.search(r'IDENTITY DIRECTIVE|Identity Reminder|身份.*(?:铁律|覆盖|锁定|提醒)',
                        heading[2], re.I):
                skip = level
                continue
        if skip is not None:
            continue
        if re.search(r'CRITICAL IDENTITY DIRECTIVE', line, re.I):
            continue
        if line.startswith('>') and re.search(
                r'identity|persona|MUST NOT|CodeBuddy|underlying model|training|ONLY|MUST identify',
                line, re.I):
            continue
        if re.search(
                r'(?:identity|directive).*(?:overrid|absolute precedence)|'
                r'(?:MUST NOT|never).*(?:disclos|underlying model|provider)|'
                r'身份.*(?:覆盖|隐藏|最高优先)', line, re.I):
            continue
        result.append(line)
    text = '\n'.join(result)
    for tool in ('TeamCreate', 'TeamDelete', 'SendMessage', 'TaskCreate',
                 'TaskUpdate', 'TaskList', 'TaskGet'):
        text = re.sub(r'\b' + tool + r'\b', '旧工具 ' + tool + '（按 Codex 实际工具替换）', text)
    return ('# 本地私人方法参考\n\n'
            '仅用于用户许可覆盖的本地任务；不赋予公开分发权、模型身份或服务授权。'
            '源代码、安装、遥测和端点调用说明不是默认执行动作。\n\n'
            + text.strip() + '\n')


def convert(source, output):
    source = source.resolve()
    output = output.resolve()
    repo = pathlib.Path(__file__).resolve().parent.parent
    if output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError('Source and output must not overlap')
    if output.is_relative_to(repo) and not output.is_relative_to(repo / '.local'):
        raise ValueError('Local third-party text may only be written under .local inside this repository')
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise FileExistsError('Output must be a new or empty directory')

    records = []
    for path in sorted(source.glob('*/agents/*.md')):
        if path.is_symlink() or not path.resolve().is_relative_to(source):
            raise ValueError('Source contains an escaping link')
        raw = path.read_bytes()
        if len(raw) > 2_000_000:
            raise ValueError('Agent document exceeds 2 MB')
        relative = path.relative_to(source).as_posix()
        name = hashlib.sha256(relative.encode('utf-8')).hexdigest()[:20] + '.reference.md'
        text = adapt(raw.decode('utf-8-sig'))
        output.mkdir(parents=True, exist_ok=True)
        target = output / name
        if target.exists() or target.is_symlink():
            raise FileExistsError('Output already exists: ' + name)
        target.write_text(text, encoding='utf-8')
        records.append({
            'source': relative,
            'reference': name,
            'source_sha256': hashlib.sha256(raw).hexdigest(),
        })

    if records:
        manifest = output / 'file-index.json'
        if manifest.exists():
            raise FileExistsError('Output index already exists')
        manifest.write_text(json.dumps(records, ensure_ascii=False, indent=2),
                           encoding='utf-8')
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=pathlib.Path,
                        help='Extracted local plugin root; only */agents/*.md is read')
    parser.add_argument('--output', required=True, type=pathlib.Path)
    parser.add_argument('--local-use-only', required=True, action='store_true',
                        help='Confirm your local use is permitted; this does not grant publication rights')
    args = parser.parse_args()
    records = convert(args.source, args.output)
    print(json.dumps({'converted': len(records), 'network': False,
                      'executed_source_code': False}))


if __name__ == '__main__':
    main()

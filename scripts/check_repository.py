"""检查Git暂存区；仅输出问题文件名，不回显疑似凭据内容。"""

from pathlib import Path
from zipfile import ZipFile
import io
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = [
    re.compile(rb'gh[pousr]_[A-Za-z0-9]{25,}'),
    re.compile(rb'github_pat_[A-Za-z0-9_]{30,}'),
    re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    re.compile(rb'[?&](?:X-Amz-Signature|X-Goog-Signature|sig)=[A-Za-z0-9%+/=]{16,}', re.I),
]
BLOCKED_PARTS = {'private', '.private-social', 'runtime', 'output', '__pycache__', '.venv'}
BLOCKED_NAMES = re.compile(r'(?:^\.env(?:\.|$)|receipt|identity|materialize_result|upload_request|auth\.json)', re.I)


def main():
    raw = subprocess.check_output(['git', 'ls-files', '--cached', '-z'], cwd=ROOT)
    names = [x.decode('utf-8') for x in raw.split(b'\0') if x]
    problems = []
    for name in names:
        path = Path(name)
        if BLOCKED_PARTS.intersection(path.parts) or BLOCKED_NAMES.search(path.name):
            problems.append((name, '不应提交的运行文件或账号配置'))
            continue
        data = subprocess.check_output(['git', 'show', ':' + name], cwd=ROOT)
        contents = [data]
        if path.suffix.lower() == '.xlsx':
            with ZipFile(io.BytesIO(data)) as archive:
                contents = [archive.read(n) for n in archive.namelist() if n.endswith(('.xml', '.rels'))]
        if any(pattern.search(body) for body in contents for pattern in PATTERNS):
            problems.append((name, '疑似凭据或临时签名地址；需人工检查'))
    for name, reason in problems:
        print(f'{name}: {reason}')
    print(f'checked_files={len(names)} findings={len(problems)}')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())

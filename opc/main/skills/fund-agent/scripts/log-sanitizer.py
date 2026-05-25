#!/usr/bin/env python3
"""
Log Sanitizer — 提交前自动脱敏敏感信息

用法：
  python3 log-sanitizer.py                    # 扫描并修复暂存区
  python3 log-sanitizer.py --scan-only         # 只扫描不修复
  python3 log-sanitizer.py --check-all         # 扫描整个项目
  python3 log-sanitizer.py --git-hooks         # 安装 git pre-commit hook

检测模式：
  - 邮箱密码（SMTP/IMAP）
  - GitHub/Token 密钥
  - 数据库连接字符串
  - API Key（OpenAI/Claude/Brave 等）
  - 手机号
  - IP 地址（内网/外网）
  - 数据库密码

脱敏规则：保留前 4 位 + **** + 后 2 位，或直接替换为 <REDACTED>
"""

import os
import re
import sys
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple

# ─── 敏感信息正则模式 ──────────────────────────────────────────
SENSITIVE_PATTERNS: List[Tuple[str, re.Pattern, str]] = [
    # 邮箱密码 / SMTP 密码（支持中英文关键词）
    (
        "SMTP/邮箱密码",
        re.compile(
            r'(?:password|passwd|pwd|app_password|smtp_password|imap_password|密码|授权密码)\s*[=:]\s*["\']?([A-Za-z0-9]{8,})["\']?',
            re.IGNORECASE
        ),
        "PASSWORD_REPLACED"
    ),
    # GitHub Token (ghp_, gho_, github_pat_)
    (
        "GitHub Token",
        re.compile(r'(ghp_[A-Za-z0-9_]{20,}|gho_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})'),
        "GITHUB_TOKEN_REPLACED"
    ),
    # 通用 Token / API Key
    (
        "API Key / Token",
        re.compile(
        r'(?:api_key|apikey|secret_key|secret|access_key)\s*[=:]\s*["\']?([A-Za-z0-9_\-]{16,})["\']?',
            re.IGNORECASE
        ),
        "API_KEY_REPLACED"
    ),
    # 数据库连接字符串（含密码）
    (
        "数据库连接串",
        re.compile(
            r'(mysql|postgres|mongodb|redis)://[^\s"\']+:[^\s"\']+@[^\s"\']+',
            re.IGNORECASE
        ),
        "DB_URL_REPLACED"
    ),
    # 数据库密码
    (
        "数据库密码",
        re.compile(
            r'(?:db_password|database_password|mysql_password|mongo_password)\s*[=:]\s*["\']?([^\s"\']{4,})["\']?',
            re.IGNORECASE
        ),
        "DB_PASSWORD_REPLACED"
    ),
    # OpenAI / Claude / 其他 API Key
    (
        "AI 服务商 API Key",
        re.compile(
            r'(?:OPENAI_API_KEY|ANTHROPIC_API_KEY|GOOGLE_API_KEY|BRAVE_API_KEY|DEEPSEEK_API_KEY)\s*[=:]\s*["\']?([^\s"\']{8,})["\']?'
        ),
        "AI_API_KEY_REPLACED"
    ),
    # 加密密钥
    (
        "加密密钥",
        re.compile(
            r'(?:ENC_KEY|ENCRYPTION_KEY|SECRET_KEY)\s*[=:]\s*["\']?([A-Za-z0-9_\-]{16,})["\']?',
            re.IGNORECASE
        ),
        "ENC_KEY_REPLACED"
    ),
    # 手机号
    (
        "手机号",
        re.compile(r'1[3-9]\d{9}'),
        "PHONE_REPLACED"
    ),
    # IP 地址
    (
        "IP 地址",
        re.compile(r'(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)'),
        "IP_REPLACED"
    ),
    # 邮箱地址
    (
        "邮箱地址",
        re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
        "EMAIL_REPLACED"
    ),
]

# ─── 白名单（不脱敏的词） ───────────────────────────────────
WHITELIST_WORDS = {
    "password_field", "password_input", "password_change", "password_reset",
    "password_policy", "password_required", "no_password", "empty_password",
    "PASSWORD_REPLACED", "API_KEY_REPLACED", "TOKEN_REPLACED",
    "DB_URL_REPLACED", "DB_PASSWORD_REPLACED", "AI_API_KEY_REPLACED",
    "ENC_KEY_REPLACED", "PHONE_REPLACED", "IP_REPLACED", "EMAIL_REPLACED",
    "GITHUB_TOKEN_REPLACED",
    "<REDACTED>", "your_password", "your_api_key", "your_token",
    "example@email.com", "placeholder", "xxx", "*****",
}

# ─── 需要跳过的文件 ────────────────────────────────────────
SKIP_EXTENSIONS = {
    '.enc', '.gpg', '.pem', '.key', '.crt', '.p12',
    '.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico',
    '.pyc', '.pyo', '.so', '.dll', '.exe', '.bin',
    '.lock', '.gitignore',
}
SKIP_DIRS = {
    'node_modules', '.git', '__pycache__', '.venv', 'venv',
    '.DS_Store', '.archive',
}


def should_skip(path: str) -> bool:
    """判断文件是否跳过"""
    ext = Path(path).suffix.lower()
    if ext in SKIP_EXTENSIONS:
        return True
    for part in Path(path).parts:
        if part in SKIP_DIRS:
            return True
    return False


def scan_file(filepath: str) -> List[Dict]:
    """扫描单个文件，返回发现的问题列表"""
    if should_skip(filepath):
        return []

    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except (IOError, OSError):
        return []

    findings = []
    for line_num, line in enumerate(lines, 1):
        for pattern_name, pattern, replacement in SENSITIVE_PATTERNS:
            for match in pattern.finditer(line):
                value = match.group(0)
                # 检查是否是白名单词
                if any(w in value for w in WHITELIST_WORDS):
                    continue
                findings.append({
                    'file': filepath,
                    'line': line_num,
                    'pattern': pattern_name,
                    'match': value[:60] + ('...' if len(value) > 60 else ''),
                    'full_match': value,
                })
    return findings


def sanitize_content(content: str) -> Tuple[str, List[Dict]]:
    """脱敏内容，返回新内容和替换记录"""
    replacements = []
    for pattern_name, pattern, replacement in SENSITIVE_PATTERNS:
        def replacer(m):
            original = m.group(0)
            if any(w in original for w in WHITELIST_WORDS):
                return original
            replacements.append({
                'pattern': pattern_name,
                'original': original[:30] + '...' if len(original) > 30 else original
            })
            return replacement

        content = pattern.sub(replacer, content)
    return content, replacements


def sanitize_file(filepath: str) -> bool:
    """脱敏单个文件，返回是否修改"""
    if should_skip(filepath):
        return False

    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except (IOError, OSError):
        return False

    new_content, replacements = sanitize_content(content)
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False


def get_staged_files() -> List[str]:
    """获取 git 暂存区文件"""
    try:
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACMR'],
            capture_output=True, text=True, timeout=10
        )
        return [f for f in result.stdout.strip().split('\n') if f]
    except Exception:
        return []


def get_all_project_files() -> List[str]:
    """获取项目所有文件"""
    files = []
    for root, dirs, filenames in os.walk('.'):
        # 跳过 .git 目录
        if '.git' in root:
            continue
        for fn in filenames:
            path = os.path.join(root, fn)
            if not should_skip(path):
                files.append(path)
    return files


def scan_files(file_list: List[str]) -> List[Dict]:
    """扫描文件列表"""
    all_findings = []
    for f in file_list:
        findings = scan_file(f)
        all_findings.extend(findings)
    return all_findings


def sanitize_files(file_list: List[str]) -> int:
    """脱敏文件列表，返回修改的文件数"""
    count = 0
    for f in file_list:
        if sanitize_file(f):
            count += 1
    return count


def install_git_hook():
    """安装 git pre-commit hook"""
    hook_path = Path('.git/hooks/pre-commit')
    hook_path.parent.mkdir(exist_ok=True)

    script_path = os.path.abspath(__file__)
    hook_content = f'''#!/bin/sh
# Auto-generated by log-sanitizer
# 提交前自动脱敏敏感信息
echo "🔒 运行 Log Sanitizer..."
python3 {script_path} --scan-only
if [ $? -ne 0 ]; then
    echo "❌ 发现敏感信息，提交已拒绝！"
    echo "请运行: python3 {script_path} 进行脱敏"
    exit 1
fi
python3 {script_path} 2>/dev/null
exit 0
'''
    hook_path.write_text(hook_content)
    os.chmod(hook_path, 0o755)
    print(f"✅ Git pre-commit hook 已安装: {hook_path}")


def main():
    mode = 'fix'
    if '--scan-only' in sys.argv:
        mode = 'scan'
    elif '--check-all' in sys.argv:
        mode = 'scan_all'
    elif '--git-hooks' in sys.argv:
        install_git_hook()
        return

    if mode == 'scan':
        # 扫描暂存区
        files = get_staged_files()
        if not files:
            print("✅ 暂存区为空")
            sys.exit(0)

        findings = scan_files(files)
        if findings:
            print(f"❌ 发现 {len(findings)} 个敏感信息：")
            for f in findings:
                print(f"  🚨 {f['file']}:{f['line']} [{f['pattern']}] {f['match']}")
            sys.exit(1)
        else:
            print("✅ 暂存区文件安全")
            sys.exit(0)

    elif mode == 'scan_all':
        # 扫描整个项目
        files = get_all_project_files()
        findings = scan_files(files)
        if findings:
            print(f"❌ 发现 {len(findings)} 个敏感信息：")
            for f in findings:
                print(f"  🚨 {f['file']}:{f['line']} [{f['pattern']}] {f['match']}")
            sys.exit(1)
        else:
            print("✅ 项目文件安全")
            sys.exit(0)

    else:
        # 修复模式：自动脱敏暂存区文件
        files = get_staged_files()
        if not files:
            print("✅ 暂存区为空，无需脱敏")
            sys.exit(0)

        count = sanitize_files(files)
        if count > 0:
            print(f"✅ 已脱敏 {count} 个文件")
            # 重新添加到暂存区
            for f in files:
                subprocess.run(['git', 'add', f], capture_output=True)
        else:
            print("✅ 文件安全，无需脱敏")


if __name__ == '__main__':
    main()

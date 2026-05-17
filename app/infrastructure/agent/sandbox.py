from __future__ import annotations

import re
from pathlib import Path

SECRET_PATTERNS = (
    re.compile(r"(bot[_-]?token|api[_-]?hash|api[_-]?key|secret|password|proxy)\s*[=:]\s*\S+", re.I),
    re.compile(r"\d{8,10}:[A-Za-z0-9_-]{30,}"),
    re.compile(r"socks5://[^\s]+", re.I),
    re.compile(r"mtproto://[^\s]+", re.I),
)

ALLOWED_READ_SUFFIXES = {".py", ".md", ".mdc", ".toml", ".yaml", ".yml", ".ini", ".txt"}
ALLOWED_READ_NAMES = {"Dockerfile", "render.yaml", "railway.toml", "alembic.ini"}
ALLOWED_DIR_PREFIXES = (
    "app",
    "CursoRules",
    "alembic",
    "scripts",
    "tests",
    "docs",
)


class AgentSandboxError(PermissionError):
    pass


class AgentSandbox:
    """Read-only доступ только к файлам внутри корня проекта."""

    def __init__(self, project_root: str) -> None:
        self.root = Path(project_root).resolve()
        self.reports_dir = self.root / "reports" / "agent"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def resolve_read_path(self, relative: str) -> Path:
        candidate = (self.root / relative).resolve()
        if not str(candidate).startswith(str(self.root)):
            raise AgentSandboxError("Путь вне проекта запрещён.")
        if candidate.is_dir():
            raise AgentSandboxError("Чтение директорий запрещено.")
        if candidate.name in {".env", "render.env.local"} or candidate.suffix == ".session":
            raise AgentSandboxError("Секретные файлы недоступны агенту.")
        if candidate.suffix not in ALLOWED_READ_SUFFIXES and candidate.name not in ALLOWED_READ_NAMES:
            raise AgentSandboxError(f"Тип файла не разрешён: {candidate.name}")
        if not candidate.exists():
            raise AgentSandboxError(f"Файл не найден: {relative}")
        return candidate

    def is_listable(self, path: Path) -> bool:
        try:
            rel = path.resolve().relative_to(self.root)
        except ValueError:
            return False
        parts = rel.parts
        if not parts:
            return True
        return parts[0] in ALLOWED_DIR_PREFIXES or rel.name in ALLOWED_READ_NAMES

    def list_project_files(self, limit: int = 80) -> list[str]:
        files: list[str] = []
        for path in sorted(self.root.rglob("*")):
            if len(files) >= limit:
                break
            if not path.is_file():
                continue
            if not self.is_listable(path):
                continue
            if path.suffix == ".pyc" or "__pycache__" in path.parts:
                continue
            files.append(str(path.relative_to(self.root)).replace("\\", "/"))
        return files

    def read_text(self, relative: str, *, max_chars: int = 12_000) -> str:
        path = self.resolve_read_path(relative)
        text = path.read_text(encoding="utf-8", errors="replace")
        if len(text) > max_chars:
            text = text[:max_chars] + "\n… [обрезано]"
        return redact_secrets(text)

    def write_report(self, filename: str, content: str) -> Path:
        safe_name = re.sub(r"[^\w.\-]", "_", filename)[:120]
        target = (self.reports_dir / safe_name).resolve()
        if not str(target).startswith(str(self.reports_dir.resolve())):
            raise AgentSandboxError("Недопустимое имя отчёта.")
        target.write_text(content, encoding="utf-8")
        return target


def redact_secrets(text: str) -> str:
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted

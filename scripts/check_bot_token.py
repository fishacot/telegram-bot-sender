"""Quick BOT_TOKEN / ADMIN_IDS check (no secrets printed)."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)


async def main() -> None:
    root = Path(__file__).resolve().parents[1]
    for name in ("render.env.local", ".env"):
        load_env_file(root / name)

    token = os.environ.get("BOT_TOKEN", "")
    admins = os.environ.get("ADMIN_IDS", "")
    proxy = os.environ.get("TELEGRAM_PROXY", "")

    print("BOT_TOKEN:", "ok" if token and ":" in token else "MISSING or invalid")
    print("ADMIN_IDS:", admins or "MISSING")
    print("TELEGRAM_PROXY:", "set" if proxy else "not set")

    import httpx

    async def get_me(use_proxy: str | None = None) -> None:
        label = "via proxy" if use_proxy else "direct"
        try:
            async with httpx.AsyncClient(timeout=30.0, proxy=use_proxy) as client:
                response = await client.get(f"https://api.telegram.org/bot{token}/getMe")
                payload = response.json()
        except Exception as error:
            print(f"getMe {label}: ERROR {error}")
            return
        if payload.get("ok"):
            user = payload["result"]
            print(f"getMe {label}: OK @{user.get('username')} id={user.get('id')}")
        else:
            print(f"getMe {label}: FAIL {payload.get('description', payload)}")

    if not token:
        return
    await get_me(None)
    if proxy:
        await get_me(proxy)


if __name__ == "__main__":
    asyncio.run(main())

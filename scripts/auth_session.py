import argparse
import asyncio

from app.config import get_settings
from app.infrastructure.telethon_clients.factory import TelethonClientFactory


async def auth_session(name: str) -> None:
    settings = get_settings()
    if not settings.telegram_api_id or not settings.telegram_api_hash:
        raise RuntimeError("TELEGRAM_API_ID and TELEGRAM_API_HASH are required in .env")
    factory = TelethonClientFactory(
        sessions_dir=settings.sessions_dir,
        api_id=settings.telegram_api_id,
        api_hash=settings.telegram_api_hash,
        proxy_url=settings.telegram_proxy,
    )
    client = factory.create(name)
    await client.start()
    me = await client.get_me()
    print(f"Session '{name}' authenticated as {me.username or me.id}")
    await client.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True, help="Session file name")
    args = parser.parse_args()
    asyncio.run(auth_session(args.name))


if __name__ == "__main__":
    main()

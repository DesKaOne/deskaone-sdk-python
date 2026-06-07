from __future__ import annotations

import asyncio
import os

from deskaone_sdk import HttpClient, ProxyConfig


async def main() -> None:
    proxy_url = os.environ.get("PROXY_URL")
    proxy = ProxyConfig.from_url_string(proxy_url) if proxy_url else None
    response = await HttpClient(proxy_config=proxy).get("https://api.ipify.org/")
    print("Status:", response.status_code)
    print("Headers:", response.headers)
    print("Body:", response.text())


if __name__ == "__main__":
    asyncio.run(main())

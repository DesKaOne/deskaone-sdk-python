from __future__ import annotations

import asyncio
import os

from deskaone_sdk import ProxyConfig, WebSocketClient, WebSocketOpcode


async def main() -> None:
    proxy_url = os.environ.get("PROXY_URL")
    proxy = ProxyConfig.from_url_string(proxy_url) if proxy_url else None
    ws = await WebSocketClient.connect("wss://ws.postman-echo.com/raw", proxy_config=proxy)
    await ws.send_text("halo dari DesKaOne SDK Python")
    message = await ws.recv()
    if message.opcode == WebSocketOpcode.TEXT:
        print("text:", message.text)
    elif message.opcode == WebSocketOpcode.BINARY:
        print("binary:", message.data)
    elif message.opcode == WebSocketOpcode.PING:
        print("ping:", message.data)
    elif message.opcode == WebSocketOpcode.PONG:
        print("pong:", message.data)
    await ws.close(1000, "done")


if __name__ == "__main__":
    asyncio.run(main())

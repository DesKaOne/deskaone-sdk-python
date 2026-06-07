from __future__ import annotations

import asyncio
import os

from deskaone_sdk import ProxyConfig, ReconnectWebSocketClient, WebSocketClient, WebSocketMessage


async def on_connect(ws: WebSocketClient) -> None:
    print("connected")
    await ws.send_text("halo dari reconnect client")


async def on_message(message: WebSocketMessage) -> None:
    print("message:", message.data)


async def main() -> None:
    proxy_url = os.environ.get("PROXY_URL")
    proxy = ProxyConfig.from_url_string(proxy_url) if proxy_url else None
    client = ReconnectWebSocketClient(
        "wss://ws.postman-echo.com/raw",
        proxy_config=proxy,
        reconnect_delay=2.0,
        max_reconnects=3,
        on_connect=on_connect,
        on_message=on_message,
    )
    # In a real app you might run this forever. This example stops after 10 seconds.
    task = asyncio.create_task(client.run())
    await asyncio.sleep(10)
    await client.stop()
    await task


if __name__ == "__main__":
    asyncio.run(main())

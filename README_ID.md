# DesKaOne SDK Python

[English version](README.md)

Fondasi Python async untuk jaringan DesKaOne SDK. Phase 1 mencakup TCP/TLS langsung, HTTP CONNECT, SOCKS4/SOCKS4a, SOCKS5, client HTTP/1.1 manual, client WebSocket manual, helper reconnect, dan utilitas ringan. Fitur storage dan database belum diimplementasikan pada fase ini.

## Fitur

- Python 3.11+ dan `asyncio`.
- Tanpa dependency runtime.
- Implementasi TCP, HTTP/1.1, dan WebSocket manual di atas asyncio streams.
- Dukungan proxy HTTP, SOCKS4/SOCKS4a, dan SOCKS5.
- Client HTTP/HTTPS langsung dan WebSocket `ws`/`wss`.
- Wrapper WebSocket dengan reconnect otomatis.
- Utilitas bytes, debouncer, event emitter, warna terminal, dan logger.

## Instalasi

```bash
python -m pip install deskaone-sdk-python
```

Untuk pengembangan lokal:

```bash
python -m pip install -e ".[dev]"
```

## Import

```python
from deskaone_sdk import HttpClient, ProxyConfig, WebSocketClient
```

## Contoh HTTP langsung

```python
import asyncio
from deskaone_sdk import HttpClient

async def main():
    response = await HttpClient().get("https://api.ipify.org/")
    print(response.status_code, response.text())

asyncio.run(main())
```

## Contoh HTTP melalui proxy

```python
from deskaone_sdk import HttpClient, ProxyConfig

proxy = ProxyConfig.from_url_string("http://proxy.example:8080")
client = HttpClient(proxy_config=proxy)
```

## Contoh HTTPS melalui proxy

```python
from deskaone_sdk import HttpClient, ProxyConfig

proxy = ProxyConfig.from_url_string("socks5://proxy.example:1080")
response = await HttpClient(proxy_config=proxy).get("https://example.com/")
```

## Contoh WebSocket wss

```python
ws = await WebSocketClient.connect("wss://ws.postman-echo.com/raw")
await ws.send_text("halo dari DesKaOne SDK Python")
message = await ws.recv()
await ws.close()
```

## Contoh WebSocket wss melalui proxy

```python
proxy = ProxyConfig.from_url_string("socks5://proxy.example:1080")
ws = await WebSocketClient.connect("wss://ws.postman-echo.com/raw", proxy_config=proxy)
```

## Contoh Reconnect WebSocket

```python
from deskaone_sdk import ReconnectWebSocketClient

client = ReconnectWebSocketClient("wss://ws.postman-echo.com/raw", reconnect_delay=2.0)
await client.run()
```

## Contoh environment PROXY_URL

```bash
export PROXY_URL='socks5://proxy.example:1080'
python examples/http_client_example.py
```

Peringatan keamanan: jangan pernah menulis kredensial proxy, API key, token, atau password langsung di kode. Gunakan environment variable atau secret manager.

## SDK Referensi

- Go SDK: <https://github.com/DesKaOne/deskaone-sdk>
- Dart SDK: <https://github.com/DesKaOne/deskaone-sdk-dart>
- TypeScript SDK: <https://github.com/DesKaOne/deskaone-sdk-ts>

import asyncio

from deskaone_sdk.utils import EventEmitter


def test_event_emitter_sync_async_once():
    async def scenario():
        emitter = EventEmitter()
        calls = []
        emitter.on("a", lambda value: calls.append(value))
        emitter.once("a", lambda value: calls.append(value + 1))
        emitter.emit("a", 1)
        emitter.emit("a", 2)
        assert calls == [1, 2, 2]
        assert emitter.listener_count("a") == 1

        async def handler(value):
            calls.append(value)

        emitter.on("b", handler)
        await emitter.emit_async("b", 5)
        assert calls[-1] == 5

    asyncio.run(scenario())

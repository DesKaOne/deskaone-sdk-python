import asyncio

from deskaone_sdk.utils import Debouncer


def test_debouncer_runs_last_call():
    async def scenario():
        calls = []
        debouncer = Debouncer(0.01, lambda: calls.append("x"))
        debouncer.call()
        debouncer.call()
        await asyncio.sleep(0.03)
        assert calls == ["x"]
        debouncer.dispose()

    asyncio.run(scenario())

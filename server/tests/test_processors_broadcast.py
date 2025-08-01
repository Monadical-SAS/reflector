import pytest


@pytest.mark.asyncio
async def test_processor_broadcast():
    from reflector.processors.base import BroadcastProcessor, Pipeline, Processor

    class TestProcessor(Processor):
        INPUT_TYPE = str
        OUTPUT_TYPE = str

        def __init__(self, name, **kwargs):
            super().__init__(**kwargs)
            self.name = name

        async def _push(self, data):
            data = data + f":{self.name}"
            await self.emit(data)

    processors = [
        TestProcessor("A"),
        BroadcastProcessor(
            processors=[
                TestProcessor("B"),
                TestProcessor("C"),
            ],
        ),
    ]

    events = []

    async def on_event(event):
        events.append(event)

    pipeline = Pipeline(*processors)
    pipeline.on(on_event)
    await pipeline.push("test")
    await pipeline.flush()

    assert len(events) == 3
    assert events[0].processor == "A"
    assert events[0].data == "test:A"
    assert events[1].processor == "B"
    assert events[1].data == "test:A:B"
    assert events[2].processor == "C"
    assert events[2].data == "test:A:C"

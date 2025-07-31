import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Union
from uuid import uuid4

from prometheus_client import Counter, Gauge, Histogram
from pydantic import BaseModel

from reflector.logger import logger


class PipelineEvent(BaseModel):
    processor: str
    uid: str
    data: Any


class Emitter:
    def __init__(self, **kwargs):
        self._callbacks = {}

        # register callbacks from kwargs (on_*)
        for key, value in kwargs.items():
            if key.startswith("on_"):
                self.on(value, name=key[3:])

    def on(self, callback, name="default"):
        """
        Register a callback to be called when data is emitted
        """
        # ensure callback is asynchronous
        if not asyncio.iscoroutinefunction(callback):
            raise ValueError("Callback must be a coroutine function")
        if name not in self._callbacks:
            self._callbacks[name] = []
        self._callbacks[name].append(callback)

    def off(self, callback, name="default"):
        """
        Unregister a callback to be called when data is emitted
        """
        if name not in self._callbacks:
            return
        self._callbacks[name].remove(callback)

    async def emit(self, data, name="default"):
        if name not in self._callbacks:
            return
        for callback in self._callbacks[name]:
            await callback(data)


class Processor(Emitter):
    INPUT_TYPE: type = None
    OUTPUT_TYPE: type = None

    m_processor = Histogram(
        "processor",
        "Time spent in Processor.process",
        ["processor"],
    )
    m_processor_call = Counter(
        "processor_call",
        "Number of calls to Processor.process",
        ["processor"],
    )
    m_processor_success = Counter(
        "processor_success",
        "Number of successful calls to Processor.process",
        ["processor"],
    )
    m_processor_failure = Counter(
        "processor_failure",
        "Number of failed calls to Processor.process",
        ["processor"],
    )
    m_processor_flush = Histogram(
        "processor_flush",
        "Time spent in Processor.flush",
        ["processor"],
    )
    m_processor_flush_call = Counter(
        "processor_flush_call",
        "Number of calls to Processor.flush",
        ["processor"],
    )
    m_processor_flush_success = Counter(
        "processor_flush_success",
        "Number of successful calls to Processor.flush",
        ["processor"],
    )
    m_processor_flush_failure = Counter(
        "processor_flush_failure",
        "Number of failed calls to Processor.flush",
        ["processor"],
    )

    def __init__(self, callback=None, custom_logger=None, **kwargs):
        super().__init__(**kwargs)
        self.name = name = self.__class__.__name__
        self.m_processor = self.m_processor.labels(name)
        self.m_processor_call = self.m_processor_call.labels(name)
        self.m_processor_success = self.m_processor_success.labels(name)
        self.m_processor_failure = self.m_processor_failure.labels(name)
        self.m_processor_flush = self.m_processor_flush.labels(name)
        self.m_processor_flush_call = self.m_processor_flush_call.labels(name)
        self.m_processor_flush_success = self.m_processor_flush_success.labels(name)
        self.m_processor_flush_failure = self.m_processor_flush_failure.labels(name)
        self._processors = []

        # register callbacks
        if callback:
            self.on(callback)

        self.uid = uuid4().hex
        self.flushed = False
        self.logger = (custom_logger or logger).bind(processor=self.__class__.__name__)
        self.pipeline = None

    def set_pipeline(self, pipeline: "Pipeline"):
        # if pipeline is used, pipeline logger will be used instead
        self.pipeline = pipeline
        self.logger = pipeline.logger.bind(processor=self.__class__.__name__)

    def connect(self, processor: "Processor"):
        """
        Connect this processor output to another processor
        """
        if processor.INPUT_TYPE != self.OUTPUT_TYPE:
            raise ValueError(
                f"Processor {processor} input type {processor.INPUT_TYPE} "
                f"does not match {self.OUTPUT_TYPE}"
            )
        self._processors.append(processor)

    def disconnect(self, processor: "Processor"):
        """
        Disconnect this processor data from another processor
        """
        self._processors.remove(processor)

    def get_pref(self, key: str, default: Any = None):
        """
        Get a preference from the pipeline prefs
        """
        if self.pipeline:
            return self.pipeline.get_pref(key, default)
        return default

    async def emit(self, data, name="default"):
        if name == "default":
            if self.pipeline:
                await self.pipeline.emit(
                    PipelineEvent(processor=self.name, uid=self.uid, data=data)
                )
        await super().emit(data, name=name)
        if name == "default":
            for processor in self._processors:
                await processor.push(data)

    async def push(self, data):
        """
        Push data to this processor. `data` must be of type `INPUT_TYPE`
        The function returns the output of type `OUTPUT_TYPE`
        """
        self.m_processor_call.inc()
        try:
            self.flushed = False
            with self.m_processor.time():
                ret = await self._push(data)
                self.m_processor_success.inc()
                return ret
        except Exception:
            self.m_processor_failure.inc()
            self.logger.exception("Error in push")

    async def flush(self):
        """
        Flush data to this processor
        Works only one time, until another push is called
        """
        if self.flushed:
            return
        self.m_processor_flush_call.inc()
        self.flushed = True
        try:
            with self.m_processor_flush.time():
                ret = await self._flush()
                self.m_processor_flush_success.inc()
                return ret
        except Exception:
            self.m_processor_flush_failure.inc()
            raise

    def describe(self, level=0):
        logger.info("  " * level + self.__class__.__name__)

    async def _push(self, data):
        raise NotImplementedError

    async def _flush(self):
        pass

    @classmethod
    def as_threaded(cls, *args, **kwargs):
        """
        Return a single threaded processor where output is guaranteed
        to be in order
        """
        return ThreadedProcessor(cls(*args, **kwargs), max_workers=1)


class ThreadedProcessor(Processor):
    """
    A processor that runs in a separate thread
    """

    m_processor_queue = Gauge(
        "processor_queue",
        "Number of items in the processor queue",
        ["processor", "processor_uid"],
    )
    m_processor_queue_in_progress = Gauge(
        "processor_queue_in_progress",
        "Number of items in the processor queue in progress (global)",
        ["processor"],
    )

    def __init__(self, processor: Processor, max_workers=1):
        super().__init__()
        # FIXME: This is a hack to make sure that the processor is single threaded
        # but if it is more than 1, then we need to make sure that the processor
        # is emiting data in order
        assert max_workers == 1
        self.m_processor_queue = self.m_processor_queue.labels(processor.name, self.uid)
        self.m_processor_queue_in_progress = self.m_processor_queue_in_progress.labels(
            processor.name
        )
        self.processor = processor
        self.INPUT_TYPE = processor.INPUT_TYPE
        self.OUTPUT_TYPE = processor.OUTPUT_TYPE
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.queue = asyncio.Queue()
        self.task = asyncio.get_running_loop().create_task(self.loop())

    def set_pipeline(self, pipeline: "Pipeline"):
        super().set_pipeline(pipeline)
        self.processor.set_pipeline(pipeline)

    async def loop(self):
        while True:
            data = await self.queue.get()
            self.m_processor_queue.set(self.queue.qsize())
            with self.m_processor_queue_in_progress.track_inprogress():
                try:
                    if data is None:
                        await self.processor.flush()
                        break
                    try:
                        await self.processor.push(data)
                    except Exception:
                        self.logger.error(
                            f"Error in push {self.processor.__class__.__name__}"
                            ", continue"
                        )
                finally:
                    self.queue.task_done()

    async def _push(self, data):
        await self.queue.put(data)

    async def _flush(self):
        await self.queue.put(None)
        await self.queue.join()

    def connect(self, processor: Processor):
        self.processor.connect(processor)

    def disconnect(self, processor: Processor):
        self.processor.disconnect(processor)

    def on(self, callback, name="default"):
        self.processor.on(callback, name=name)

    def off(self, callback, name="default"):
        self.processor.off(callback, name=name)

    def describe(self, level=0):
        super().describe(level)
        self.processor.describe(level + 1)


class BroadcastProcessor(Processor):
    """
    A processor that broadcasts data to multiple processors, in the order
    they were passed to the constructor

    This processor does not guarantee that the output is in order.

    This processor connect all the output of the processors to the input of
    the next processor; so the next processor must be able to accept different
    types of input.
    """

    def __init__(self, processors: list[Processor]):
        super().__init__()
        self.processors = processors
        self.INPUT_TYPE = processors[0].INPUT_TYPE
        output_types = set([processor.OUTPUT_TYPE for processor in processors])
        self.OUTPUT_TYPE = Union[tuple(output_types)]

    def set_pipeline(self, pipeline: "Pipeline"):
        super().set_pipeline(pipeline)
        for processor in self.processors:
            processor.set_pipeline(pipeline)

    async def _push(self, data):
        coros = [processor.push(data) for processor in self.processors]
        await asyncio.gather(*coros)

    async def _flush(self):
        coros = [processor.flush() for processor in self.processors]
        await asyncio.gather(*coros)

    def connect(self, processor: Processor):
        for processor in self.processors:
            processor.connect(processor)

    def disconnect(self, processor: Processor):
        for processor in self.processors:
            processor.disconnect(processor)

    def on(self, callback, name="default"):
        for processor in self.processors:
            processor.on(callback, name=name)

    def off(self, callback, name="default"):
        for processor in self.processors:
            processor.off(callback, name=name)

    def describe(self, level=0):
        super().describe(level)
        for processor in self.processors:
            processor.describe(level + 1)


class Pipeline(Processor):
    """
    A pipeline of processors
    """

    INPUT_TYPE = None
    OUTPUT_TYPE = None

    def __init__(self, *processors: Processor):
        super().__init__()
        self.logger = logger.bind(pipeline=self.uid)
        self.logger.info("Pipeline created")

        self.processors = processors
        self.options = None
        self.prefs = {}

        for processor in processors:
            processor.set_pipeline(self)

        for i in range(len(processors) - 1):
            processors[i].connect(processors[i + 1])

        self.INPUT_TYPE = processors[0].INPUT_TYPE
        self.OUTPUT_TYPE = processors[-1].OUTPUT_TYPE

    async def _push(self, data):
        await self.processors[0].push(data)

    async def _flush(self):
        self.logger.debug("Pipeline flushing")
        for processor in self.processors:
            await processor.flush()
        self.logger.info("Pipeline flushed")

    def describe(self, level=0):
        logger.info("  " * level + "Pipeline:")
        for processor in self.processors:
            processor.describe(level + 1)
        logger.info("")

    def set_pref(self, key: str, value: Any):
        """
        Set a preference for this pipeline
        """
        self.prefs[key] = value

    def get_pref(self, key: str, default=None):
        """
        Get a preference for this pipeline
        """
        if key not in self.prefs:
            self.logger.warning(f"Pref {key} not found, using default")
        return self.prefs.get(key, default)

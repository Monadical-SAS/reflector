from reflector.logger import logger
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import asyncio


class Processor:
    INPUT_TYPE: type = None
    OUTPUT_TYPE: type = None

    def __init__(self, callback=None, custom_logger=None):
        self._processors = []
        self._callbacks = []
        if callback:
            self.on(callback)
        self.uid = uuid4().hex
        self.flushed = False
        self.logger = (custom_logger or logger).bind(processor=self.__class__.__name__)

    def set_pipeline(self, pipeline: "Pipeline"):
        # if pipeline is used, pipeline logger will be used instead
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

    def on(self, callback):
        """
        Register a callback to be called when data is emitted
        """
        # ensure callback is asynchronous
        if not asyncio.iscoroutinefunction(callback):
            raise ValueError("Callback must be a coroutine function")
        self._callbacks.append(callback)

    def off(self, callback):
        """
        Unregister a callback to be called when data is emitted
        """
        self._callbacks.remove(callback)

    async def emit(self, data):
        for callback in self._callbacks:
            await callback(data)
        for processor in self._processors:
            await processor.push(data)

    async def push(self, data):
        """
        Push data to this processor. `data` must be of type `INPUT_TYPE`
        The function returns the output of type `OUTPUT_TYPE`
        """
        # logger.debug(f"{self.__class__.__name__} push")
        try:
            self.flushed = False
            return await self._push(data)
        except Exception:
            self.logger.exception("Error in push")

    async def flush(self):
        """
        Flush data to this processor
        Works only one time, until another push is called
        """
        if self.flushed:
            return
        # logger.debug(f"{self.__class__.__name__} flush")
        self.flushed = True
        return await self._flush()

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

    def __init__(self, processor: Processor, max_workers=1):
        super().__init__()
        # FIXME: This is a hack to make sure that the processor is single threaded
        # but if it is more than 1, then we need to make sure that the processor
        # is emiting data in order
        assert max_workers == 1
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
            try:
                if data is None:
                    await self.processor.flush()
                    break
                await self.processor.push(data)
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

    def on(self, callback):
        self.processor.on(callback)

    def describe(self, level=0):
        super().describe(level)
        self.processor.describe(level + 1)


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

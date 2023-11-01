"""
Pipeline Runner
===============

Pipeline runner designed to be executed in a asyncio task.

It is meant to be subclassed, and implement a create() method
that expose/return a Pipeline instance.

During its lifecycle, it will emit the following status:
- started: the pipeline has been started
- push: the pipeline received at least one data
- flush: the pipeline is flushing
- ended: the pipeline has ended
- error: the pipeline has ended with an error
"""

import asyncio

from pydantic import BaseModel, ConfigDict
from reflector.logger import logger
from reflector.processors import Pipeline


class PipelineRunner(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    status: str = "idle"
    pipeline: Pipeline | None = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._q_cmd = asyncio.Queue()
        self._ev_done = asyncio.Event()
        self._is_first_push = True
        self._logger = logger.bind(
            runner=id(self),
            runner_cls=self.__class__.__name__,
        )

    def create(self) -> Pipeline:
        """
        Create the pipeline if not specified earlier.
        Should be implemented in a subclass
        """
        raise NotImplementedError()

    def start(self):
        """
        Start the pipeline as a coroutine task
        """
        asyncio.get_event_loop().create_task(self.run())

    def start_sync(self):
        """
        Start the pipeline synchronously (for non-asyncio apps)
        """
        coro = self.run()
        asyncio.run(coro)

    def push(self, data):
        """
        Push data to the pipeline
        """
        self._add_cmd("PUSH", data)

    def flush(self):
        """
        Flush the pipeline
        """
        self._add_cmd("FLUSH", None)

    async def on_status(self, status):
        """
        Called when the status of the pipeline changes
        """
        pass

    async def on_ended(self):
        """
        Called when the pipeline ends
        """
        pass

    def _add_cmd(self, cmd: str, data):
        """
        Enqueue a command to be executed in the runner.
        Currently supported commands: PUSH, FLUSH
        """
        self._q_cmd.put_nowait([cmd, data])

    async def _set_status(self, status):
        self._logger.debug("Runner status updated", status=status)
        self.status = status
        if self.on_status:
            try:
                await self.on_status(status)
            except Exception:
                self._logger.exception("Runer error while setting status")

    async def run(self):
        try:
            # create the pipeline if not yet done
            await self._set_status("init")
            self._is_first_push = True
            if not self.pipeline:
                self.pipeline = await self.create()

            # start the loop
            await self._set_status("started")
            while not self._ev_done.is_set():
                cmd, data = await self._q_cmd.get()
                func = getattr(self, f"cmd_{cmd.lower()}")
                if func:
                    await func(data)
                else:
                    raise Exception(f"Unknown command {cmd}")
        except Exception:
            self._logger.exception("Runner error")
            await self._set_status("error")
            self._ev_done.set()
            if self.on_ended:
                await self.on_ended()

    async def cmd_push(self, data):
        if self._is_first_push:
            await self._set_status("push")
            self._is_first_push = False
        await self.pipeline.push(data)

    async def cmd_flush(self, data):
        await self._set_status("flush")
        await self.pipeline.flush()
        await self._set_status("ended")
        self._ev_done.set()
        if self.on_ended:
            await self.on_ended()

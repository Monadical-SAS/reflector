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
from typing import Generic, TypeVar

from reflector.logger import logger
from reflector.processors import Pipeline

PipelineMessage = TypeVar("PipelineMessage")


class PipelineRunner(Generic[PipelineMessage]):
    def __init__(self):
        self._task = None
        self._q_cmd = asyncio.Queue(maxsize=4096)
        self._ev_done = asyncio.Event()
        self._is_first_push = True
        self._logger = logger.bind(
            runner=id(self),
            runner_cls=self.__class__.__name__,
        )
        self.status = "idle"
        self.pipeline: Pipeline | None = None

    async def create(self) -> Pipeline:
        """
        Create the pipeline if not specified earlier.
        Should be implemented in a subclass
        """
        raise NotImplementedError()

    def start(self):
        """
        Start the pipeline as a coroutine task
        """
        self._task = asyncio.get_event_loop().create_task(self.run())

    async def join(self):
        """
        Wait for the pipeline to finish
        """
        if self._task:
            await self._task

    def start_sync(self):
        """
        Start the pipeline synchronously (for non-asyncio apps)
        """
        coro = self.run()
        asyncio.run(coro)

    async def push(self, data: PipelineMessage):
        """
        Push data to the pipeline
        """
        await self._add_cmd("PUSH", data)

    async def flush(self):
        """
        Flush the pipeline
        """
        await self._add_cmd("FLUSH", None)

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

    async def _add_cmd(
        self,
        cmd: str,
        data: PipelineMessage,
        max_retries: int = 3,
        retry_time_limit: int = 3,
    ):
        """
        Enqueue a command to be executed in the runner.
        Currently supported commands: PUSH, FLUSH
        """
        for _ in range(max_retries):
            try:
                self._q_cmd.put_nowait([cmd, data])
                break  # Break if put succeeds
            except asyncio.queues.QueueFull:
                # Handle only the QueueFull exception, retry after a small delay
                self._logger.debug(
                    f"Encountered a full queue, while trying to add [{cmd, data}]. "
                    f"Retrying in {retry_time_limit} seconds"
                )
                await asyncio.sleep(retry_time_limit)
        else:
            print(f"Failed to add [{cmd, data}] after {max_retries} attempts.")

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

            if not self.pipeline:
                # no pipeline created in create, just finish it then.
                await self._set_status("ended")
                self._ev_done.set()
                if self.on_ended:
                    await self.on_ended()
                return

            # start the loop
            await self._set_status("started")
            while not self._ev_done.is_set():
                cmd, data = await self._q_cmd.get()
                func = getattr(self, f"cmd_{cmd.lower()}")
                if func:
                    if cmd.upper() == "FLUSH":
                        await func()
                    else:
                        await func(data)
                else:
                    raise Exception(f"Unknown command {cmd}")
        except Exception:
            self._logger.exception("Runner error")
            await self._set_status("error")
            self._ev_done.set()
            raise

    async def cmd_push(self, data: PipelineMessage):
        if self._is_first_push:
            await self._set_status("push")
            self._is_first_push = False
        await self.pipeline.push(data)

    async def cmd_flush(self):
        await self._set_status("flush")
        await self.pipeline.flush()
        await self._set_status("ended")
        self._ev_done.set()
        if self.on_ended:
            await self.on_ended()

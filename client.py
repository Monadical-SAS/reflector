import argparse
import asyncio
import signal

from aiortc.contrib.signaling import (add_signaling_arguments,
                                      create_signaling)

from utils.log_utils import LOGGER
from stream_client import StreamClient
from typing import NoReturn

async def main() -> NoReturn:
    """
    Reflector's entry point to the python client for WebRTC streaming if not
    using the browser based UI-application
    :return:
    """
    parser = argparse.ArgumentParser(description="Data channels ping/pong")

    parser.add_argument(
            "--url", type=str, nargs="?", default="http://0.0.0.0:1250/offer"
    )

    parser.add_argument(
            "--ping-pong",
            help="Benchmark data channel with ping pong",
            type=eval,
            choices=[True, False],
            default="False",
    )

    parser.add_argument(
            "--play-from",
            type=str,
            default="",
    )
    add_signaling_arguments(parser)

    args = parser.parse_args()

    signaling = create_signaling(args)

    async def shutdown(signal, loop):
        """Cleanup tasks tied to the service's shutdown."""
        LOGGER.info(f"Received exit signal {signal.name}...")
        LOGGER.info("Closing database connections")
        LOGGER.info("Nacking outstanding messages")
        tasks = [t for t in asyncio.all_tasks() if t is not
                 asyncio.current_task()]

        [task.cancel() for task in tasks]

        LOGGER.info(f"Cancelling {len(tasks)} outstanding tasks")
        await asyncio.gather(*tasks, return_exceptions=True)
        LOGGER.info(f'{"Flushing metrics"}')
        loop.stop()

    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    loop = asyncio.get_event_loop()
    for s in signals:
        loop.add_signal_handler(
                s, lambda s=s: asyncio.create_task(shutdown(s, loop)))

    # Init client
    sc = StreamClient(
            signaling=signaling,
            url=args.url,
            play_from=args.play_from,
            ping_pong=args.ping_pong
    )
    await sc.start()
    async for msg in sc.get_reader():
        print(msg)


if __name__ == "__main__":
    asyncio.run(main())

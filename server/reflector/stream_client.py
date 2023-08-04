import asyncio
import time
import uuid

import httpx
import stamina
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaPlayer, MediaRelay

from reflector.logger import logger
from reflector.settings import settings


class StreamClient:
    def __init__(
        self,
        signaling,
        url="http://0.0.0.0:1250/offer",
        play_from=None,
        ping_pong=False,
    ):
        self.signaling = signaling
        self.server_url = url
        self.play_from = play_from
        self.ping_pong = ping_pong

        self.pc = RTCPeerConnection()

        self.relay = None
        self.pcs = set()
        self.time_start = None
        self.queue = asyncio.Queue()
        self.logger = logger.bind(stream_client=id(self))

    async def stop(self):
        await self.signaling.close()
        await self.pc.close()

    def create_local_tracks(self, play_from):
        if play_from:
            player = MediaPlayer(play_from)
            return player.audio, player.video
        else:
            if self.relay is None:
                self.relay = MediaRelay()
            self.player = MediaPlayer(
                f":{settings.AUDIO_AV_FOUNDATION_DEVICE_ID}",
                format="avfoundation",
                options={"channels": "2"},
            )
            return self.relay.subscribe(self.player.audio), None

    def channel_send(self, channel, message):
        # self.channel_log(channel, ">", message)
        channel.send(message)

    def current_stamp(self):
        if self.time_start is None:
            self.time_start = time.time()
            return 0
        else:
            return int((time.time() - self.time_start) * 1000000)

    async def run_offer(self, pc, signaling):
        # microphone
        audio, video = self.create_local_tracks(self.play_from)
        pc_id = uuid.uuid4().hex
        self.pcs.add(pc)
        self.logger = self.logger.bind(pc_id=pc_id)

        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            self.logger.info(f"Connection state is {pc.connectionState}")
            if pc.connectionState == "failed":
                await pc.close()
                self.pcs.discard(pc)

        @pc.on("track")
        def on_track(track):
            self.logger.info(f"Sending {track.kind}")
            self.pc.addTrack(track)

            @track.on("ended")
            async def on_ended():
                self.logger.info(f"Track {track.kind} ended")

        self.pc.addTrack(audio)
        self.track_audio = audio

        channel = pc.createDataChannel("data-channel")
        self.logger = self.logger.bind(channel=channel.label)
        self.logger.info("Created by local party")

        async def send_pings():
            while True:
                self.channel_send(channel, "ping %d" % self.current_stamp())
                await asyncio.sleep(1)

        @channel.on("open")
        def on_open():
            if self.ping_pong:
                asyncio.ensure_future(send_pings())

        @channel.on("message")
        def on_message(message):
            self.queue.put_nowait(message)
            if self.ping_pong:
                self.logger.info(f"Message: {message}")

                if isinstance(message, str) and message.startswith("pong"):
                    elapsed_ms = (self.current_stamp() - int(message[5:])) / 1000
                    self.logger.debug("RTT %.2f ms" % elapsed_ms)

        await pc.setLocalDescription(await pc.createOffer())

        sdp = {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}

        @stamina.retry(on=httpx.HTTPError, attempts=5)
        async def connect_to_server():
            async with httpx.AsyncClient() as client:
                response = await client.post(self.server_url, json=sdp, timeout=10)
                response.raise_for_status()
                return response.json()

        params = await connect_to_server()
        answer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
        await pc.setRemoteDescription(answer)

        self.reader = self.worker(f'{"worker"}', self.queue)

    def get_reader(self):
        return self.reader

    async def worker(self, name, queue):
        while True:
            msg = await self.queue.get()
            yield msg
            self.queue.task_done()

    async def start(self):
        coro = self.run_offer(self.pc, self.signaling)
        task = asyncio.create_task(coro)
        await task

    def is_ended(self):
        return self.track_audio is None or self.track_audio.readyState == "ended"

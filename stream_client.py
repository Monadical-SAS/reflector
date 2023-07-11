import ast
import asyncio
import time
import uuid

import httpx
import pyaudio
import requests
import stamina
from aiortc import (RTCPeerConnection, RTCSessionDescription)
from aiortc.contrib.media import (MediaPlayer, MediaRelay)

from utils.log_utils import logger
from utils.run_utils import config, Mutex

file_lock = Mutex(open("test_sm_6.txt", "a"))


class StreamClient:
    def __init__(
            self,
            signaling,
            url="http://127.0.0.1:1250",
            play_from=None,
            ping_pong=False
    ):
        self.signaling = signaling
        self.server_url = url
        self.play_from = play_from
        self.ping_pong = ping_pong
        self.paudio = pyaudio.PyAudio()

        self.pc = RTCPeerConnection()

        self.loop = asyncio.get_event_loop()
        self.relay = None
        self.pcs = set()
        self.time_start = None
        self.queue = asyncio.Queue()
        self.player = MediaPlayer(':' + str(config['DEFAULT']["AV_FOUNDATION_DEVICE_ID"]),
                                  format='avfoundation', options={'channels': '2'})

    def stop(self):
        self.loop.run_until_complete(self.signaling.close())
        self.loop.run_until_complete(self.pc.close())
        # self.loop.close()

    def create_local_tracks(self, play_from):
        if play_from:
            player = MediaPlayer(play_from)
            return player.audio, player.video
        else:
            if self.relay is None:
                self.relay = MediaRelay()
            return self.relay.subscribe(self.player.audio), None

    def channel_log(self, channel, t, message):
        print("channel(%s) %s %s" % (channel.label, t, message))

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
        pc_id = "PeerConnection(%s)" % uuid.uuid4()
        self.pcs.add(pc)

        def log_info(msg, *args):
            logger.info(pc_id + " " + msg, *args)

        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            print("Connection state is %s" % pc.connectionState)
            if pc.connectionState == "failed":
                await pc.close()
                self.pcs.discard(pc)

        @pc.on("track")
        def on_track(track):
            print("Sending %s" % track.kind)
            self.pc.addTrack(track)

            @track.on("ended")
            async def on_ended():
                log_info("Track %s ended", track.kind)

        self.pc.addTrack(audio)

        channel = pc.createDataChannel("data-channel")
        self.channel_log(channel, "-", "created by local party")

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
                self.channel_log(channel, "<", message)

                if isinstance(message, str) and message.startswith("pong"):
                    elapsed_ms = (self.current_stamp() - int(message[5:])) / 1000
                    print(" RTT %.2f ms" % elapsed_ms)

        await pc.setLocalDescription(await pc.createOffer())

        sdp = {
                "sdp": pc.localDescription.sdp,
                "type": pc.localDescription.type
        }

        @stamina.retry(on=httpx.HTTPError, attempts=5)
        def connect_to_server():
            response = requests.post(self.server_url, json=sdp, timeout=10)
            response.raise_for_status()
            return response

        params = connect_to_server().json()
        answer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
        await pc.setRemoteDescription(answer)

        self.reader = self.worker(f"worker", self.queue)

    def get_reader(self):
        return self.reader

    async def worker(self, name, queue):
        while True:
            msg = await self.queue.get()
            msg = ast.literal_eval(msg)
            with file_lock.lock() as file:
                file.write(msg["text"])
            yield msg["text"]
            self.queue.task_done()

    async def start(self):
        coro = self.run_offer(self.pc, self.signaling)
        task = asyncio.create_task(coro)
        await task

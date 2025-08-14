"""
Websocket manager
=================

This module contains the WebsocketManager class, which is responsible for
managing websockets and handling websocket connections.

It uses the RedisPubSubManager class to subscribe to Redis channels and
broadcast messages to all connected websockets.
"""

import asyncio
import json
import threading

import redis.asyncio as redis
from fastapi import WebSocket

from reflector.settings import settings


class RedisPubSubManager:
    def __init__(self, host="localhost", port=6379):
        self.redis_host = host
        self.redis_port = port
        self.redis_connection = None
        self.pubsub = None

    async def get_redis_connection(self) -> redis.Redis:
        return redis.Redis(
            host=self.redis_host,
            port=self.redis_port,
            auto_close_connection_pool=False,
        )

    async def connect(self) -> None:
        if self.redis_connection is not None:
            return
        self.redis_connection = await self.get_redis_connection()
        self.pubsub = self.redis_connection.pubsub()

    async def disconnect(self) -> None:
        if self.redis_connection is None:
            return
        await self.redis_connection.close()
        self.redis_connection = None

    async def send_json(self, room_id: str, message: str) -> None:
        if not self.redis_connection:
            await self.connect()
        message = json.dumps(message)
        await self.redis_connection.publish(room_id, message)

    async def subscribe(self, room_id: str) -> redis.Redis:
        await self.pubsub.subscribe(room_id)
        return self.pubsub

    async def unsubscribe(self, room_id: str) -> None:
        await self.pubsub.unsubscribe(room_id)


class WebsocketManager:
    def __init__(self, pubsub_client: RedisPubSubManager = None):
        self.rooms: dict = {}
        self.tasks: dict = {}
        self.pubsub_client = pubsub_client

    async def add_user_to_room(self, room_id: str, websocket: WebSocket) -> None:
        await websocket.accept()

        if room_id in self.rooms:
            self.rooms[room_id].append(websocket)
        else:
            self.rooms[room_id] = [websocket]

            await self.pubsub_client.connect()
            pubsub_subscriber = await self.pubsub_client.subscribe(room_id)
            task = asyncio.create_task(self._pubsub_data_reader(pubsub_subscriber))
            self.tasks[id(websocket)] = task

    async def send_json(self, room_id: str, message: dict) -> None:
        await self.pubsub_client.send_json(room_id, message)

    async def remove_user_from_room(self, room_id: str, websocket: WebSocket) -> None:
        self.rooms[room_id].remove(websocket)
        task = self.tasks.pop(id(websocket), None)
        if task:
            task.cancel()

        if len(self.rooms[room_id]) == 0:
            del self.rooms[room_id]
            await self.pubsub_client.unsubscribe(room_id)

    async def _pubsub_data_reader(self, pubsub_subscriber):
        while True:
            message = await pubsub_subscriber.get_message(
                ignore_subscribe_messages=True
            )
            if message is not None:
                room_id = message["channel"].decode("utf-8")
                all_sockets = self.rooms[room_id]
                for socket in all_sockets:
                    data = json.loads(message["data"].decode("utf-8"))
                    await socket.send_json(data)


def get_ws_manager() -> WebsocketManager:
    """
    Returns the WebsocketManager instance for managing websockets.

    This function initializes and returns the WebsocketManager instance,
    which is responsible for managing websockets and handling websocket
    connections.

    Returns:
        WebsocketManager: The initialized WebsocketManager instance.

    Raises:
        ImportError: If the 'reflector.settings' module cannot be imported.
        RedisConnectionError: If there is an error connecting to the Redis server.
    """
    local = threading.local()
    if hasattr(local, "ws_manager"):
        return local.ws_manager

    pubsub_client = RedisPubSubManager(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
    )
    ws_manager = WebsocketManager(pubsub_client=pubsub_client)
    local.ws_manager = ws_manager
    return ws_manager

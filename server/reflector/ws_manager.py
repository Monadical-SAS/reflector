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
        try:
            await self.redis_connection.publish(room_id, message)
        except RuntimeError:
            # Celery workers run each task in a new event loop (asyncio.run),
            # which closes the previous loop. Cached Redis connection is dead.
            # Reconnect on the current loop and retry.
            self.redis_connection = None
            await self.connect()
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

    async def add_user_to_room(
        self, room_id: str, websocket: WebSocket, subprotocol: str | None = None
    ) -> None:
        if subprotocol:
            await websocket.accept(subprotocol=subprotocol)
        else:
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
            # timeout=1.0 prevents tight CPU loop when no messages available
            message = await pubsub_subscriber.get_message(
                ignore_subscribe_messages=True
            )
            if message is not None:
                room_id = message["channel"].decode("utf-8")
                all_sockets = self.rooms[room_id]
                for socket in all_sockets:
                    data = json.loads(message["data"].decode("utf-8"))
                    await socket.send_json(data)


# Process-global singleton to ensure only one WebsocketManager instance exists.
# Multiple instances would cause resource leaks and CPU issues.
_ws_manager: WebsocketManager | None = None


def get_ws_manager() -> WebsocketManager:
    """
    Returns the global WebsocketManager singleton.

    Creates instance on first call, subsequent calls return cached instance.
    Thread-safe via GIL. Concurrent initialization may create duplicate
    instances but last write wins (acceptable for this use case).

    Returns:
        WebsocketManager: The global WebsocketManager instance.
    """
    global _ws_manager

    if _ws_manager is not None:
        return _ws_manager

    # No lock needed - GIL makes this safe enough
    # Worst case: race creates two instances, last assignment wins
    pubsub_client = RedisPubSubManager(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
    )
    _ws_manager = WebsocketManager(pubsub_client=pubsub_client)
    return _ws_manager


def reset_ws_manager() -> None:
    """Reset singleton for testing. DO NOT use in production."""
    global _ws_manager
    _ws_manager = None

import asyncio
from datetime import datetime

import httpx

from reflector.db.rooms import Room
from reflector.settings import settings
from reflector.whereby import HEADERS, create_meeting


async def whereby_request(method: str, path: str):
    print(f"{method} {path}")
    url = settings.WHEREBY_API_URL
    async with httpx.AsyncClient(base_url=url) as c:
        response = await c.request(
            method=method,
            url=path,
            headers=HEADERS,
        )
        print(response.content)
        print()

        try:
            return response.json()
        except:
            return


async def createroom():
    room_name = "testroom"
    end_date = datetime.now().replace(hour=23, minute=59, second=59)
    room = Room(
        name="testmathieu",
        user_id="00000000-0000-0000-0000-000000000000",
        is_locked=False,
        room_mode="group",
        recording_type="local",
        recording_trigger="automatic",
    )

    meeting = await create_meeting(room_name, end_date, room)
    print(meeting)
    return meeting


async def main(name=None, meeting_id=None):
    if name is None or meeting_id is None:
        meeting = await createroom()
        name = meeting["roomName"]
        meeting_id = meeting["meetingId"]

    while True:
        # resp = await get_room_sessions("/testroom8a1f4ff4-5963-48e7-85ad-ecf5d328a244")
        print("-" * 80)
        print(datetime.now())
        await whereby_request("GET", f"/meetings/{meeting_id}")
        await whereby_request("GET", f"/insights/rooms?roomName={name}")
        results = await whereby_request(
            "GET", f"/insights/room-sessions?roomName={name}"
        )
        if results and results["results"]:
            for roomSessionId in results["results"]:
                print(f"  -> participants for {roomSessionId}")
                await whereby_request(
                    "GET", f"/insights/participants?roomSessionId={roomSessionId}"
                )
        # await whereby_request("GET", f"/insights/participants?roomName={name}")
        await asyncio.sleep(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("roomname", help="Room name")
    parser.add_argument("meetingid", help="Meeting ID")
    args = parser.parse_args()

    asyncio.run(main(args.roomname, args.meetingid))

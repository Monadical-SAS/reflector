from reflector.db import database
from reflector.db.meetings import meetings
from reflector.db.rooms import rooms
from reflector.db.transcripts import transcripts

users_to_migrate = [
    ["123@lifex.pink", "63b727f5-485d-449f-b528-563d779b11ef", None],
    ["ana@monadical.com", "1bae2e4d-5c04-49c2-932f-a86266a6ca13", None],
    ["cspencer@sprocket.org", "614ed0be-392e-488c-bd19-6a9730fd0e9e", None],
    ["daniel.f.lopez.j@gmail.com", "ca9561bd-c989-4a1e-8877-7081cf62ae7f", None],
    ["jenalee@monadical.com", "c7c1e79e-b068-4b28-a9f4-29d98b1697ed", None],
    ["jennifer@rootandseed.com", "f5321727-7546-4b2b-b69d-095a931ef0c4", None],
    ["jose@monadical.com", "221f079c-7ce0-4677-90b7-0359b6315e27", None],
    ["labenclayton@gmail.com", "40078cd0-543c-40e4-9c2e-5ce57a686428", None],
    ["mathieu@monadical.com", "c7a36151-851e-4afa-9fab-aaca834bfd30", None],
    ["michal.flak.96@gmail.com", "3096eb5e-b590-41fc-a0d1-d152c1895402", None],
    ["sara@monadical.com", "31ab0cfe-5d2c-4c7a-84de-a29494714c99", None],
    ["sara@monadical.com", "b871e5f0-754e-447f-9c3d-19f629f0082b", None],
    ["sebastian@monadical.com", "f024f9d0-15d0-480f-8529-43959fc8b639", None],
    ["sergey@monadical.com", "5c4798eb-b9ab-4721-a540-bd96fc434156", None],
    ["sergey@monadical.com", "9dd8a6b4-247e-48fe-b1fb-4c84dd3c01bc", None],
    ["transient.tran@gmail.com", "617ba2d3-09b6-4b1f-a435-a7f41c3ce060", None],
]


async def migrate_user(email, user_id):
    # if the email match the email in the users_to_migrate list
    # reassign all transcripts/rooms/meetings to the new user_id

    user_ids = [user[1] for user in users_to_migrate if user[0] == email]
    if not user_ids:
        return

    # do not migrate back
    if user_id in user_ids:
        return

    for old_user_id in user_ids:
        query = (
            transcripts.update()
            .where(transcripts.c.user_id == old_user_id)
            .values(user_id=user_id)
        )
        await database.execute(query)

        query = (
            rooms.update().where(rooms.c.user_id == old_user_id).values(user_id=user_id)
        )
        await database.execute(query)

        query = (
            meetings.update()
            .where(meetings.c.user_id == old_user_id)
            .values(user_id=user_id)
        )
        await database.execute(query)

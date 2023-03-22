from nio import AsyncClient


async def send_room_message(client: AsyncClient,
                            room_id: str,
                            send_text: str,
                            reply_to_event_id: str = '') -> None:
    if reply_to_event_id == '':
        content = {"msgtype": "m.text", "body": f"{send_text}", }
    else:
        content={"msgtype": "m.text", "body": f"{send_text}",
                 "m.relates_to": {"m.in_reply_to": {"event_id": reply_to_event_id}}, }
    await client.room_send(
        room_id,
        message_type="m.room.message",
        content=content,
        ignore_unverified_devices=True,
    )
    await client.room_typing(room_id, typing_state=False)

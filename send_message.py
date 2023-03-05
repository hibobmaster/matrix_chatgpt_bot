from nio import AsyncClient


async def send_room_message(client: AsyncClient,
                            room_id: str,
                            send_text: str) -> None:
    await client.room_send(
        room_id,
        message_type="m.room.message",
        content={"msgtype": "m.text", "body": f"{send_text}"},
    )
    await client.room_typing(room_id, typing_state=False)

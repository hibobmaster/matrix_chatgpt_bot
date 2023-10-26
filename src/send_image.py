"""
code derived from:
https://matrix-nio.readthedocs.io/en/latest/examples.html#sending-an-image
"""
import os

import aiofiles.os
import magic
from log import getlogger
from nio import AsyncClient
from nio import UploadResponse
from PIL import Image

logger = getlogger()


async def send_room_image(client: AsyncClient, room_id: str, image: str):
    """
    image: image path
    """
    mime_type = magic.detect_from_filename(image).mime_type
    im = Image.open(image)
    (width, height) = im.size  # im.size returns (width,height) tuple

    # first do an upload of image, then send URI of upload to room
    file_stat = await aiofiles.os.stat(image)
    async with aiofiles.open(image, "r+b") as f:
        resp, maybe_keys = await client.upload(
            f,
            content_type=mime_type,  # image/jpeg
            filename=os.path.basename(image),
            filesize=file_stat.st_size,
        )
    if not isinstance(resp, UploadResponse):
        logger.warning(f"Failed to upload image. Failure response: {resp}")
        await client.room_send(
            room_id,
            message_type="m.room.message",
            content={
                "msgtype": "m.text",
                "body": f"Failed to upload image. Failure response: {resp}",
            },
            ignore_unverified_devices=True,
        )
        return

    content = {
        "body": os.path.basename(image),  # descriptive title
        "info": {
            "size": file_stat.st_size,
            "mimetype": mime_type,
            "w": width,  # width in pixel
            "h": height,  # height in pixel
        },
        "msgtype": "m.image",
        "url": resp.content_uri,
    }

    try:
        await client.room_send(room_id, message_type="m.room.message", content=content)
    except Exception as e:
        logger.error(f"Image send of file {image} failed.\n Error: {e}", exc_info=True)
        raise Exception(e)

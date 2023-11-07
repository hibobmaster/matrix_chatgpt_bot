import httpx
from pathlib import Path
import uuid
import base64
import io
from PIL import Image


async def get_images(
    aclient: httpx.AsyncClient, url: str, prompt: str, backend_type: str, **kwargs
) -> list[str]:
    timeout = kwargs.get("timeout", 120.0)
    if backend_type == "openai":
        resp = await aclient.post(
            url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {kwargs.get('api_key')}",
            },
            json={
                "prompt": prompt,
                "model": "dall-e-3",
                "n": kwargs.get("n", 1),
                "size": "1792x1024",
                "quality": "hd",
                "response_format": "b64_json",
            },
            timeout=timeout,
        )
        if resp.status_code == 200:
            b64_datas = []
            for data in resp.json()["data"]:
                b64_datas.append(data["b64_json"])
            return b64_datas
        else:
            raise Exception(
                f"{resp.status_code} {resp.reason_phrase} {resp.text}",
            )
    elif backend_type == "sdwui":
        resp = await aclient.post(
            url,
            headers={
                "Content-Type": "application/json",
            },
            json={
                "prompt": prompt,
                "sampler_name": kwargs.get("sampler_name", "Euler a"),
                "batch_size": kwargs.get("n", 1),
                "steps": kwargs.get("steps", 20),
                "width": 256 if "256" in kwargs.get("size") else 512,
                "height": 256 if "256" in kwargs.get("size") else 512,
            },
            timeout=timeout,
        )
        if resp.status_code == 200:
            b64_datas = resp.json()["images"]
            return b64_datas
        else:
            raise Exception(
                f"{resp.status_code} {resp.reason_phrase} {resp.text}",
            )


def save_images(b64_datas: list[str], path: Path, **kwargs) -> list[str]:
    images = []
    for b64_data in b64_datas:
        image_path = path / (str(uuid.uuid4()) + ".jpeg")
        img = Image.open(io.BytesIO(base64.decodebytes(bytes(b64_data, "utf-8"))))
        img.save(image_path)
        images.append(image_path)
    return images

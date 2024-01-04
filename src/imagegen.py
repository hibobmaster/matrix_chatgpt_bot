import httpx
from pathlib import Path
import uuid
import base64
import io
from PIL import Image


async def get_images(
    aclient: httpx.AsyncClient,
    url: str,
    prompt: str,
    backend_type: str,
    output_path: str,
    **kwargs,
) -> list[str]:
    timeout = kwargs.get("timeout", 180.0)
    if backend_type == "openai":
        resp = await aclient.post(
            url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {kwargs.get('api_key')}",
            },
            json={
                "prompt": prompt,
                "n": kwargs.get("n", 1),
                "size": kwargs.get("size", "512x512"),
                "response_format": "b64_json",
            },
            timeout=timeout,
        )
        if resp.status_code == 200:
            b64_datas = []
            for data in resp.json()["data"]:
                b64_datas.append(data["b64_json"])
            return save_images_b64(b64_datas, output_path, **kwargs)
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
                "cfg_scale": kwargs.get("cfg_scale", 7),
                "batch_size": kwargs.get("n", 1),
                "steps": kwargs.get("steps", 20),
                "width": kwargs.get("width", 512),
                "height": kwargs.get("height", 512),
            },
            timeout=timeout,
        )
        if resp.status_code == 200:
            b64_datas = resp.json()["images"]
            return save_images_b64(b64_datas, output_path, **kwargs)
        else:
            raise Exception(
                f"{resp.status_code} {resp.reason_phrase} {resp.text}",
            )
    elif backend_type == "localai":
        resp = await aclient.post(
            url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {kwargs.get('api_key')}",
            },
            json={
                "prompt": prompt,
                "size": kwargs.get("size", "512x512"),
            },
            timeout=timeout,
        )
        if resp.status_code == 200:
            image_url = resp.json()["data"][0]["url"]
            return await save_image_url(image_url, aclient, output_path, **kwargs)


def save_images_b64(b64_datas: list[str], path: Path, **kwargs) -> list[str]:
    images_path_list = []
    for b64_data in b64_datas:
        image_path = path / (
            str(uuid.uuid4()) + "." + kwargs.get("image_format", "jpeg")
        )
        img = Image.open(io.BytesIO(base64.decodebytes(bytes(b64_data, "utf-8"))))
        img.save(image_path)
        images_path_list.append(image_path)
    return images_path_list


async def save_image_url(
    url: str, aclient: httpx.AsyncClient, path: Path, **kwargs
) -> list[str]:
    images_path_list = []
    r = await aclient.get(url)
    image_path = path / (str(uuid.uuid4()) + "." + kwargs.get("image_format", "jpeg"))
    if r.status_code == 200:
        img = Image.open(io.BytesIO(r.content))
        img.save(image_path)
        images_path_list.append(image_path)
    return images_path_list

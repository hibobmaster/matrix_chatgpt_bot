"""
Code derived from:
https://github.com/acheong08/EdgeGPT/blob/f940cecd24a4818015a8b42a2443dd97c3c2a8f4/src/ImageGen.py
"""

from log import getlogger
from uuid import uuid4
import os
import contextlib
import aiohttp
import asyncio
import random
import requests
import regex

logger = getlogger()

BING_URL = "https://www.bing.com"
# Generate random IP between range 13.104.0.0/14
FORWARDED_IP = (
    f"13.{random.randint(104, 107)}.{random.randint(0, 255)}.{random.randint(0, 255)}"
)
HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",  # noqa: E501
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "max-age=0",
    "content-type": "application/x-www-form-urlencoded",
    "referrer": "https://www.bing.com/images/create/",
    "origin": "https://www.bing.com",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36 Edg/110.0.1587.63",  # noqa: E501
    "x-forwarded-for": FORWARDED_IP,
}


class ImageGenAsync:
    """
    Image generation by Microsoft Bing
    Parameters:
        auth_cookie: str
    """

    def __init__(self, auth_cookie: str, quiet: bool = True) -> None:
        self.session = aiohttp.ClientSession(
            headers=HEADERS,
            cookies={"_U": auth_cookie},
        )
        self.quiet = quiet

    async def __aenter__(self):
        return self

    async def __aexit__(self, *excinfo) -> None:
        await self.session.close()

    def __del__(self):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(self._close())

    async def _close(self):
        await self.session.close()

    async def get_images(self, prompt: str) -> list:
        """
        Fetches image links from Bing
        Parameters:
            prompt: str
        """
        if not self.quiet:
            print("Sending request...")
        url_encoded_prompt = requests.utils.quote(prompt)
        # https://www.bing.com/images/create?q=<PROMPT>&rt=3&FORM=GENCRE
        url = f"{BING_URL}/images/create?q={url_encoded_prompt}&rt=4&FORM=GENCRE"
        async with self.session.post(url, allow_redirects=False) as response:
            content = await response.text()
            if "this prompt has been blocked" in content.lower():
                raise Exception(
                    "Your prompt has been blocked by Bing. Try to change any bad words and try again.",  # noqa: E501
                )
            if response.status != 302:
                # if rt4 fails, try rt3
                url = (
                    f"{BING_URL}/images/create?q={url_encoded_prompt}&rt=3&FORM=GENCRE"
                )
                async with self.session.post(
                    url,
                    allow_redirects=False,
                    timeout=200,
                ) as response3:
                    if response3.status != 302:
                        print(f"ERROR: {response3.text}")
                        raise Exception("Redirect failed")
                    response = response3
        # Get redirect URL
        redirect_url = response.headers["Location"].replace("&nfy=1", "")
        request_id = redirect_url.split("id=")[-1]
        await self.session.get(f"{BING_URL}{redirect_url}")
        # https://www.bing.com/images/create/async/results/{ID}?q={PROMPT}
        polling_url = f"{BING_URL}/images/create/async/results/{request_id}?q={url_encoded_prompt}"  # noqa: E501
        # Poll for results
        if not self.quiet:
            print("Waiting for results...")
        while True:
            if not self.quiet:
                print(".", end="", flush=True)
            # By default, timeout is 300s, change as needed
            response = await self.session.get(polling_url)
            if response.status != 200:
                raise Exception("Could not get results")
            content = await response.text()
            if content and content.find("errorMessage") == -1:
                break

            await asyncio.sleep(1)
            continue
        # Use regex to search for src=""
        image_links = regex.findall(r'src="([^"]+)"', content)
        # Remove size limit
        normal_image_links = [link.split("?w=")[0] for link in image_links]
        # Remove duplicates
        normal_image_links = list(set(normal_image_links))

        # Bad images
        bad_images = [
            "https://r.bing.com/rp/in-2zU3AJUdkgFe7ZKv19yPBHVs.png",
            "https://r.bing.com/rp/TX9QuO3WzcCJz1uaaSwQAz39Kb0.jpg",
        ]
        for im in normal_image_links:
            if im in bad_images:
                raise Exception("Bad images")
        # No images
        if not normal_image_links:
            raise Exception("No images")
        return normal_image_links

    async def save_images(
        self, links: list, output_dir: str, output_four_images: bool
    ) -> list:
        """
        Saves images to output directory
        """
        with contextlib.suppress(FileExistsError):
            os.mkdir(output_dir)

        image_path_list = []

        if output_four_images:
            for link in links:
                image_name = str(uuid4())
                image_path = os.path.join(output_dir, f"{image_name}.jpeg")
                try:
                    async with self.session.get(
                        link, raise_for_status=True
                    ) as response:
                        with open(image_path, "wb") as output_file:
                            async for chunk in response.content.iter_chunked(8192):
                                output_file.write(chunk)
                    image_path_list.append(image_path)
                except aiohttp.client_exceptions.InvalidURL as url_exception:
                    raise Exception(
                        "Inappropriate contents found in the generated images. Please try again or try another prompt."
                    ) from url_exception  # noqa: E501
        else:
            image_name = str(uuid4())
            if links:
                link = links.pop()
                try:
                    async with self.session.get(
                        link, raise_for_status=True
                    ) as response:
                        image_path = os.path.join(output_dir, f"{image_name}.jpeg")
                        with open(image_path, "wb") as output_file:
                            async for chunk in response.content.iter_chunked(8192):
                                output_file.write(chunk)
                        image_path_list.append(image_path)
                except aiohttp.client_exceptions.InvalidURL as url_exception:
                    raise Exception(
                        "Inappropriate contents found in the generated images. Please try again or try another prompt."
                    ) from url_exception  # noqa: E501

        return image_path_list

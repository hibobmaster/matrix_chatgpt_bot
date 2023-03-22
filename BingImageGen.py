"""
Code derived from:
https://github.com/acheong08/EdgeGPT/blob/f940cecd24a4818015a8b42a2443dd97c3c2a8f4/src/ImageGen.py
"""
from log import getlogger
from uuid import uuid4
import os
import urllib
import time
import requests
import regex

BING_URL = "https://www.bing.com"
logger = getlogger()


class ImageGen:
    """
    Image generation by Microsoft Bing
    Parameters:
        auth_cookie: str
    """

    def __init__(self, auth_cookie: str) -> None:
        self.session: requests.Session = requests.Session()
        self.session.headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "max-age=0",
            "content-type": "application/x-www-form-urlencoded",
            "referrer": "https://www.bing.com/images/create/",
            "origin": "https://www.bing.com",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36 Edg/110.0.1587.63",
        }
        self.session.cookies.set("_U", auth_cookie)

    def get_images(self, prompt: str) -> list:
        """
        Fetches image links from Bing
        Parameters:
            prompt: str
        """
        print("Sending request...")
        url_encoded_prompt = urllib.parse.quote(prompt)
        # https://www.bing.com/images/create?q=<PROMPT>&rt=4&FORM=GENCRE
        url = f"{BING_URL}/images/create?q={url_encoded_prompt}&rt=4&FORM=GENCRE"
        response = self.session.post(url, allow_redirects=False)
        if response.status_code != 302:
            logger.error(f"ERROR: {response.text}")
            return []
        # Get redirect URL
        redirect_url = response.headers["Location"]
        request_id = redirect_url.split("id=")[-1]
        self.session.get(f"{BING_URL}{redirect_url}")
        # https://www.bing.com/images/create/async/results/{ID}?q={PROMPT}
        polling_url = f"{BING_URL}/images/create/async/results/{request_id}?q={url_encoded_prompt}"
        # Poll for results
        print("Waiting for results...")
        while True:
            print(".", end="", flush=True)
            response = self.session.get(polling_url)
            if response.status_code != 200:
                logger.error("Could not get results", exc_info=True)
                return []
            if response.text == "":
                time.sleep(1)
                continue
            else:
                break

        # Use regex to search for src=""
        image_links = regex.findall(r'src="([^"]+)"', response.text)
        # Remove duplicates
        return list(set(image_links))

    def save_images(self, links: list, output_dir: str) -> str:
        """
        Saves images to output directory
        """
        print("\nDownloading images...")
        try:
            os.mkdir(output_dir)
        except FileExistsError:
            pass
        # image name
        image_name = str(uuid4())
        # since matrix only support one media attachment per message, we just need one link
        if links:
            link = links.pop()
        else:
            logger.error("Get Image URL failed")
            # return "" if there is no link
            return ""

        with self.session.get(link, stream=True) as response:
            # save response to file
            response.raise_for_status()
            with open(f"{output_dir}/{image_name}.jpeg", "wb") as output_file:
                for chunk in response.iter_content(chunk_size=8192):
                    output_file.write(chunk)
        # image_num = 0
        # for link in links:
        #     with self.session.get(link, stream=True) as response:
        #         # save response to file
        #         response.raise_for_status()
        #         with open(f"{output_dir}/{image_num}.jpeg", "wb") as output_file:
        #             for chunk in response.iter_content(chunk_size=8192):
        #                 output_file.write(chunk)
        #
        #     image_num += 1

        # return image path
        return f"{output_dir}/{image_name}.jpeg"

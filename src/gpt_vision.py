import httpx


async def gpt_vision_query(
    api_url: str,
    prompt: str,
    image_url: str,
    model: str,
    session: httpx.AsyncClient,
    **kwargs,
) -> str:
    """
    model: gpt-4-vision-preview or llava
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {kwargs.get('api_key', '')}",
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ],
    }

    response = await session.post(
        api_url, headers=headers, json=payload, timeout=kwargs.get("timeout", "120")
    )
    if response.status_code == 200:
        resp = response.json()["choices"][0]
        return resp["message"]["content"]
    else:
        response.raise_for_status()


async def test():
    async with httpx.AsyncClient() as session:
        api_url = "http://127.0.0.1:12345/v1/chat/completions"
        prompt = "What is in the image?"
        image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
        model = "llava"
        api_key = "xxxx"
        response = await gpt_vision_query(
            api_url, prompt, image_url, model, session, api_key=api_key, timeout=300
        )
        print(response)


if __name__ == "__main__":
    import asyncio

    asyncio.run(test())

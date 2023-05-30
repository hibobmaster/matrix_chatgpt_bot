import requests


def flowise_query(api_url: str, prompt: str, headers: dict = None) -> str:
    """
    Sends a query to the Flowise API and returns the response.

    Args:
        api_url (str): The URL of the Flowise API.
        prompt (str): The question to ask the API.

    Returns:
        str: The response from the API.
    """
    if headers:
        response = requests.post(
            api_url, json={"question": prompt}, headers=headers, timeout=120
        )
    else:
        response = requests.post(api_url, json={"question": prompt}, timeout=120)
    return response.text

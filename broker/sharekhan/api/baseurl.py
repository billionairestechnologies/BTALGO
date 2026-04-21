BASE_URL = "https://api.sharekhan.com"


def get_url(endpoint):
    if not endpoint.startswith("/"):
        endpoint = "/" + endpoint
    return BASE_URL + endpoint

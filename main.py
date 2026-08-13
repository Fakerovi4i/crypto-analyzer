import functools
from time import sleep
import requests
import pprint

API_URL = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=50&page=1"


def retry(max_attempts=3, delay=2):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for _ in range(max_attempts):
                try:
                    result = func(*args, **kwargs)
                except requests.exceptions.RequestException:
                    print("Повторная попытка подключения...")
                    sleep(delay)
                else:
                    if not result:
                        return {"detail": "not found"}
                    return result
            raise requests.exceptions.RequestException("Не удалось подключиться, возможно неверный URL")
        return wrapper
    return decorator

@retry(3, 1)
def top_50_coin():
    response = requests.get(API_URL)
    return response




if __name__ == "__main__":
    top_coins = top_50_coin()
    pprint.pprint(top_coins.json())
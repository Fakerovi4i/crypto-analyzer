import functools
from time import sleep
import requests
import pprint

API_URL = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=50&page=1"


def retry(max_attempts, delay):
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

@retry(3, 2)
def top_50_coin() -> list[dict]:
    response = requests.get(API_URL)
    response.raise_for_status()
    return response.json()


def top_3_growth_coin_change(coins: list[dict]) -> list[dict]:
    sorted_coins = sorted(coins, key=lambda coin: coin["price_change_percentage_24h"], reverse=True)
    return sorted_coins[:3]

def top_3_fall_coin_change(coins: list[dict]) -> list[dict]:
    sorted_coins = sorted(coins, key=lambda coin: coin["price_change_percentage_24h"], reverse=False)
    return sorted_coins[:3]

def top_1_total_volume(coins: list[dict]) -> dict:
    return max(coins, key=lambda coin: coin["total_volume"])

def capitalize_50_coin(coins: list[dict]) -> float:
    return sum((coin["market_cap"] for coin in coins))


if __name__ == "__main__":
    top_coins = top_50_coin()
    top_3_grow = top_3_growth_coin_change(top_coins)
    top_3_fall = top_3_fall_coin_change(top_coins)
    top_volume = top_1_total_volume(top_coins)
    capitalize_coins = capitalize_50_coin(top_coins)

    # pprint.pprint(top_coins)
    # pprint.pprint(top_3_grow)
    # pprint.pprint(top_3_fall)
    # pprint.pprint(top_volume)
    # pprint.pprint(capitalize_coins)




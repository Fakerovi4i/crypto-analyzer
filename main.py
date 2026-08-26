from datetime import datetime
from time import sleep
import functools
import json
from typing import Any

from rich.console import Console
from rich.table import Table
import requests


API_URL = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=50&page=1"
console = Console()


def retry(max_attempts: int, delay: int):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for _ in range(max_attempts):
                try:
                    result = func(*args, **kwargs)
                except requests.exceptions.RequestException:
                    with console.status("[yellow] Повторная попытка подключения...[/]"):
                        sleep(delay)
                else:
                    return result
            raise requests.exceptions.RequestException("Не удалось подключиться, возможно неверный URL")
        return wrapper
    return decorator

@retry(3, 2)
def top_50_coin() -> list[dict] | Any:
    with console.status("[green] Загрузка...[/]"):
        response = requests.get(API_URL)
        response.raise_for_status()
        return response.json()

def top_3_growth_coin_change(coins: list[dict]) -> list[dict]:
    sorted_coins = sorted(coins, key=lambda coin: coin.get("price_change_percentage_24h", 0), reverse=True)
    return sorted_coins[:3]

def top_3_fall_coin_change(coins: list[dict]) -> list[dict]:
    sorted_coins = sorted(coins, key=lambda coin: coin.get("price_change_percentage_24h", 0), reverse=False)
    return sorted_coins[:3]

def top_1_total_volume(coins: list[dict]) -> dict:
    return max(coins, key=lambda coin: coin["total_volume"])

def capitalize_coins(coins: list[dict]) -> float:
    return sum((coin["market_cap"] for coin in coins))

def show_table(growth: list[dict], fall: list[dict]):
    table = Table(title="Crypto Coins")
    keys_coins = (
        'id', 'name', 'symbol', 'price_change_percentage_24h', 'total_volume'
    )

    for k in keys_coins:
        table.add_column(k)

    for g in growth:
        table.add_row(*(str(g.get(k)) for k in keys_coins), style="green")

    for f in fall:
        table.add_row(*(str(f.get(k)) for k in keys_coins), style="red")

    console.print(table)

def to_entry(coin: dict, mapping: dict) -> dict:
    return {k: coin.get(v, None) for k, v in mapping.items()}


def make_dict(
        top_3: list[dict],
        lose_3: list[dict],
        high_volume: dict,
        total_market_cap: float,
        len_coins: int
) -> dict:
    result_dict = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_coins_analyzed": len_coins,
        "total_market_cap_usd": total_market_cap,
        "top_gainers": [],
        "top_losers": [],
        "highest_volume": {}
    }

    mapping_keys = {
        "name": "name",
        "symbol": "symbol",
        "change_24h": "price_change_percentage_24h"
    }

    result_dict["top_gainers"] = [to_entry(coin, mapping_keys) for coin in top_3]
    result_dict["top_losers"] = [to_entry(coin, mapping_keys) for coin in lose_3]

    mapping_keys = {
        "name": "name",
        "symbol": "symbol",
        "volume_usd": "total_volume"
    }

    result_dict["highest_volume"] = to_entry(high_volume, mapping_keys)

    return result_dict

def write_to_file(data: dict) -> None:
    with open("crypto_report.json", "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

def main():
    top_coins = top_50_coin()

    if not top_coins:
        console.print("Не удалось получить данные о криптовалютах.")
        return

    growth_coins = top_3_growth_coin_change(top_coins)
    fall_coins = top_3_fall_coin_change(top_coins)
    high_volume = top_1_total_volume(top_coins)
    total_market_cap = capitalize_coins(top_coins)
    len_coins = len(top_coins)
    data = make_dict(
        growth_coins,
        fall_coins,
        high_volume,
        total_market_cap,
        len_coins
    )

    show_table(growth=growth_coins, fall=fall_coins)
    write_to_file(data)


if __name__ == "__main__":
    main()





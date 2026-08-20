from datetime import datetime
from time import sleep
import functools
import json
from dataclasses import dataclass

from rich.console import Console
from rich.table import Table
import requests

import os
import dotenv

dotenv.load_dotenv()

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


@dataclass
class Coin:
    id: str
    name: str
    symbol: str
    price_change_percentage_24h: float
    total_volume: float
    market_cap: float

    def __str__(self):
        return f"class: {self.__class__.__name__} | name: {self.name} | id: {self.id}"

    def __lt__(self, other):
        return self.price_change_percentage_24h < other.price_change_percentage_24h


class Connector:
    def __init__(self, headers: dict | None = None):
        self.headers = headers
        self.session: requests.Session | None = None

    def __enter__(self):
        self.session = requests.Session()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    @retry(3, 2)
    def get(self, url, params) -> list[dict]:
        if self.session is None:
            raise RuntimeError("'Connector' должен использоваться как контекстный менеджер")
        response = self.session.get(url=url, params=params, headers=self.headers)
        response.raise_for_status()
        return response.json()






















@retry(3, 2)
def top_50_coin() -> list[dict]:
    url = os.getenv("API_1_URL") + "/api/v3/coins/markets"
    params = {"vs_currency": "usd", "order": "market_cap_desc", "per_page": 50, "page": 1}

    with requests.Session() as session:
        response = session.get(url=url, params=params)
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

def capitalize_coins(coins: list[dict]) -> float:
    return sum((coin["market_cap"] for coin in coins))

def show_table(growth: list[dict], fall: list[dict]):
    table = Table(title="Crypto Coins")

    with console.status("[green] Загрузка...[/]"):
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

def make_dict(coins: list[dict]):
    total_market_cap = capitalize_coins(coins)
    top_3 = top_3_growth_coin_change(coins)
    lose_3 = top_3_fall_coin_change(coins)
    high_volume = top_1_total_volume(coins)
    result_dict = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_coins_analyzed": len(coins),
        "total_market_cap_usd": total_market_cap,
        "top_gainers": [],
        "top_losers": [],
        "highest_volume": {}
    }

    keys = ["name", "symbol", "change_24h"]
    keys_values = ["name", "symbol", "price_change_percentage_24h"]

    for i in range(3):
        result_dict["top_gainers"].append({keys[j]: top_3[i][keys_values[j]] for j in range(3)})

    for i in range(3):
        result_dict["top_losers"].append({keys[j]: lose_3[i][keys_values[j]] for j in range(3)})

    keys = ["name", "symbol", "volume_usd"]
    keys_values = ["name", "symbol", "total_volume"]
    result_dict["highest_volume"] = {keys[i]: high_volume[keys_values[i]] for i in range(3)}

    return result_dict

def write_to_file(coins: list[dict]):
    data = make_dict(coins)
    with open("crypto_report.json", "w") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

def main():
    top_coins = top_50_coin()
    growth_coins = top_3_growth_coin_change(top_coins)
    fall_coins = top_3_fall_coin_change(top_coins)
    show_table(growth=growth_coins, fall=fall_coins)
    write_to_file(top_coins)


if __name__ == "__main__":
    main()





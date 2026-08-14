import datetime
import functools
from time import sleep
from datetime import datetime
import requests
from rich.console import Console
from rich.table import Table
import json


API_URL = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=50&page=1"
console = Console()
table = Table(title="Crypto Coins")


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

def capitalize_coins(coins: list[dict]) -> float:
    return sum((coin["market_cap"] for coin in coins))

def show_table(growth: list[dict], fall: list[dict]):
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
        sleep(2)
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
    keys_values = ["name", "symbol", "market_cap_change_percentage_24h"]

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

def print_and_write_data(coins: list[dict]):
    growth_coins = top_3_growth_coin_change(coins)
    fall_coins = top_3_fall_coin_change(coins)
    show_table(growth=growth_coins, fall=fall_coins)
    write_to_file(coins)

def main():
    top_coins = top_50_coin()
    print_and_write_data(top_coins)


if __name__ == "__main__":
    main()





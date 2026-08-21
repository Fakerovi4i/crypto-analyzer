from datetime import datetime
from time import sleep
import functools
import json
from dataclasses import dataclass, fields, asdict
from abc import ABC, abstractmethod

from rich.console import Console
from rich.table import Table
import requests

import os
import dotenv

import typer

dotenv.load_dotenv()


def retry(max_attempts: int, delay: int):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = None
            for i in range(1, max_attempts+1):
                try:
                    result =  func(*args, **kwargs)
                    break
                except requests.exceptions.RequestException as e:
                    if i == max_attempts:
                        raise requests.exceptions.RequestException(f"Connection Failed: {e}")

                    with Console().status(f"[yellow] Retrying connection [{i}]...[/]"):
                        sleep(delay)

            return result
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
        return f"class: {self.__class__.__name__} | name: {self.name} | id: {self.id} | price_change_24: {self.price_change_percentage_24h}"

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
    def get(self, url: str, params: dict) -> list[dict] | dict:
        if self.session is None:
            raise RuntimeError("'Connector' должен использоваться как контекстный менеджер")
        response = self.session.get(url=url, params=params, headers=self.headers)
        response.raise_for_status()
        return response.json()


class BaseProvider(ABC):
    @abstractmethod
    def get_coins(self, params: dict | None) -> list[Coin]:
        pass

    @abstractmethod
    def fetch_raw(self, params: dict) -> list[dict]:
        pass


class ProviderCoingecko(BaseProvider):
    def __init__(self, connector: Connector, host: str = "https://api.coingecko.com", path: str = "/api/v3/coins/markets/"):
        self.host = host
        self.path = path
        self.url = self.host + self.path
        self.connector = connector


    def get_coins(self, params: dict | None = None) -> list[Coin]:
        if params is None:
            params = {"vs_currency": "usd", "order": "market_cap_desc", "per_page": 50, "page": 1}

        raw_data = self.fetch_raw(params)
        coins = [
            Coin(
                item["id"],
                item["name"],
                item["symbol"],
                item["price_change_percentage_24h"],
                item["total_volume"],
                item["market_cap"],
            )
            for item in raw_data
        ]
        return coins


    def fetch_raw(self, params: dict) -> list[dict]:
        response: list[dict] = self.connector.get(url=self.url, params=params)
        return response

class ProviderCMC(BaseProvider):
    def __init__(self, connector: Connector, host: str = "https://pro-api.coinmarketcap.com", path: str = "/v3/cryptocurrency/listings/latest"):
        self.host = host
        self.path = path
        self.url = self.host + self.path
        self.connector = connector


    def get_coins(self, params: dict | None = None) -> list[Coin]:
        if params is None:
            params = {"sort": "market_cap", "sort_dir": "desc", "limit": "50"}

        raw_data: list[dict] = self.fetch_raw(params)
        coins = [
            Coin(
                id=item["id"],
                name=item["name"],
                symbol=item["symbol"],
                price_change_percentage_24h=item["quote"][0]["percent_change_24h"],
                total_volume=item["quote"][0]["volume_24h"],
                market_cap=item["quote"][0]["market_cap"],
            )
            for item in raw_data
        ]
        return coins


    def fetch_raw(self, params: dict) -> list[dict]:
        response: dict = self.connector.get(url=self.url, params=params)
        return response["data"]


class CoinCollection:
    def __init__(self, coins: list[Coin]):
        if not coins:
            raise ValueError("CoinCollection must have at least one coin")
        self.coins = coins

    def top_gainers(self, qty: int = 3) -> list[Coin]:
        sorted_coins = sorted(self.coins, reverse=True)
        return sorted_coins[:qty]

    def top_losers(self, qty: int = 3) -> list[Coin]:
        sorted_coins = sorted(self.coins, reverse=False)
        return sorted_coins[:qty]

    def top_volume(self) -> Coin:
        return max(self.coins, key=lambda coin: coin.total_volume)

    def total_market_cap(self) -> float:
        return sum(coin.market_cap for coin in self.coins)

class BaseOutput(ABC):
    @abstractmethod
    def output(self, collection: CoinCollection, qty: int = 3) -> None:
        pass

class ConsoleOutput(BaseOutput):
    def __init__(self, r_console: Console):
        self.console = r_console


    def output(self, collection: CoinCollection, qty: int = 3) -> None:
        table = Table(title="Crypto Coins")

        with self.console.status("[green] Загрузка...[/]"):
            top = collection.top_gainers(qty=qty)
            los = collection.top_losers(qty=qty)
            keys = [key.name for key in fields(Coin)]

            for key in keys:
                table.add_column(key)

            for coin in top:
                row = [str(getattr(coin, key)) for key in keys]
                table.add_row(*row, style="green")

            for coin in los:
                row = [str(getattr(coin, key)) for key in keys]
                table.add_row(*row, style="red")

        self.console.print(table)

class JsonOutput(BaseOutput):
    def __init__(self, path: str):
        self.path = path

    def output(self, collection: CoinCollection, qty: int = 3) -> None:
        result_dict = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_coins_analyzed": len(collection.coins),
            "total_market_cap_usd": collection.total_market_cap(),
            "top_gainers": [asdict(coin) for coin in collection.top_gainers(qty)],
            "top_losers": [asdict(coin) for coin in collection.top_losers(qty)],
            "highest_volume": asdict(collection.top_volume())
        }

        with open(self.path, "w", encoding="utf-8") as file:
            json.dump(result_dict, file, indent=4, ensure_ascii=False)










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


def main(source: str = "coingecko", output: str = "console", top: int = 3):
    console = Console()
    provider_factories = {
        "coingecko": lambda: ProviderCoingecko(Connector()),
        "cmc": lambda: ProviderCMC(Connector(headers={
            "Accept": "application/json",
            "X-CMC_PRO_API_KEY": os.getenv("API_KEY"),
        })),
    }

    output_factories = {
        "console": lambda: ConsoleOutput(console),
        # "csv": "...",
        "json": lambda: JsonOutput("crypto_report.json"),
    }

    prov_factory = provider_factories.get(source)
    if prov_factory is None:
        raise ValueError("Invalid '--source'")

    provider = prov_factory()
    with provider.connector:
        coins_top_50 = provider.get_coins()

    out_factory = output_factories.get(output)
    if out_factory is None:
        raise ValueError("Invalid '--output'")

    collection = CoinCollection(coins_top_50)
    if not collection.coins:
        raise ValueError("collection.coin must have value")
    output_source = out_factory()
    output_source.output(collection, top)



if __name__ == "__main__":
    typer.run(main)





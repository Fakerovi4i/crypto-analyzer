from datetime import datetime
from enum import Enum
from time import sleep
import functools
from dataclasses import dataclass, fields, asdict
from abc import ABC, abstractmethod
import json
import os
import csv

from rich.console import Console
from rich.table import Table
import requests
import dotenv
import typer

dotenv.load_dotenv()


def retry(max_attempts: int, delay: int):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            result = None
            for i in range(1, max_attempts+1):
                try:
                    result =  func(self, *args, **kwargs)
                    break
                except requests.exceptions.RequestException as e:
                    if i == max_attempts:
                        raise requests.exceptions.RequestException(f"Connection Failed: {e}")

                    with self.console.status(f"[yellow] Retrying connection [{i}]...[/]"):
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

    def __post_init__(self):
        str_fields = {"id": self.id, "name": self.name, "symbol": self.symbol}
        for name, value in str_fields.items():
            if not isinstance(value, str):
                raise ValueError(f"{name} must be a string")
            if not value.strip():
                raise ValueError(f"{name} must not be empty")

        num_fields = {
            "price_change_percentage_24h": self.price_change_percentage_24h,
            "total_volume": self.total_volume,
            "market_cap": self.market_cap,
        }
        for name, value in num_fields.items():
            if not isinstance(value, (int, float)):
                raise ValueError(f"{name} must be a number")

        if self.total_volume < 0:
            raise ValueError("total_volume must not be negative")
        if self.market_cap < 0:
            raise ValueError("market_cap must not be negative")

    def __str__(self):
        return (
            f"class: {self.__class__.__name__} | "
            f"name: {self.name} | "
            f"id: {self.id} | "
            f"price_change_24: {self.price_change_percentage_24h}"
        )

    def __lt__(self, other):
        return self.price_change_percentage_24h < other.price_change_percentage_24h


class Connector:
    def __init__(self, console: Console, headers: dict | None = None):
        self.headers = headers
        self.console = console
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


PROVIDER_REGISTRY = {}
def register_provider(name: str):
    def decorator(cls):
        PROVIDER_REGISTRY[name] = cls
        return cls
    return decorator


class BaseProvider(ABC):
    def __init__(
            self,
            connector: Connector,
            host: str,
            path: str
    ):
        self.connector = connector
        self.host = host
        self.path = path
        self.url = self.host + self.path

    def __enter__(self):
        self.connector.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.connector.__exit__(exc_type, exc_val, exc_tb)

    @abstractmethod
    def get_coins(self, params: dict | None) -> list[Coin]:
        pass

    @abstractmethod
    def fetch_raw(self, params: dict) -> list[dict]:
        pass

    @classmethod
    def build_headers(cls) -> dict | None:
        return None

@register_provider("coingecko")
class ProviderCoingecko(BaseProvider):
    def __init__(
            self,
            connector: Connector,
            host: str = "https://api.coingecko.com",
            path: str = "/api/v3/coins/markets/"
    ):
        super().__init__(connector, host, path)


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


@register_provider("coinmarketcap")
class ProviderCMC(BaseProvider):
    def __init__(
            self,
            connector: Connector,
            host: str = "https://pro-api.coinmarketcap.com",
            path: str = "/v3/cryptocurrency/listings/latest"
    ):
        super().__init__(connector, host, path)

    @classmethod
    def build_headers(cls) -> dict | None:
        return {
            "Accept": "application/json",
            "X-CMC_PRO_API_KEY": os.getenv("API_KEY")
        }

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


OUTPUT_REGISTRY = {}
def register_output(name: str):
    def decorator(cls):
        OUTPUT_REGISTRY[name] = cls
        return cls
    return decorator


class BaseOutput(ABC):
    def __init__(self, console: Console):
        self.console = console


    @abstractmethod
    def output(self, collection: CoinCollection, qty: int = 3) -> None:
        pass

    @classmethod
    def _column(cls) -> list:
        return [key.name for key in fields(Coin)]

    def _row(self, coin: Coin) -> list:
        return [str(getattr(coin, key)) for key in self._column()]




@register_output("console")
class ConsoleOutput(BaseOutput):
    def output(self, collection: CoinCollection, qty: int = 3) -> None:
        table = Table(title="Crypto Coins")

        with self.console.status("[green] Загрузка...[/]"):
            top = collection.top_gainers(qty=qty)
            los = collection.top_losers(qty=qty)

            for col in self._column():
                table.add_column(col)

            for coin in top:
                row = self._row(coin)
                table.add_row(*row, style="green")

            for coin in los:
                row = self._row(coin)
                table.add_row(*row, style="red")

        self.console.print(table)


@register_output("json")
class JsonOutput(BaseOutput):
    def __init__(self, console: Console, path: str = "crypto_report.json"):
        super().__init__(console)
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

        self.console.print(f"[green]Отчет сохранен в {self.path}[/]")

@register_output("csv")
class CsvOutput(BaseOutput):
    def __init__(self, console: Console, path: str = "crypto_report.csv"):
        super().__init__(console)
        self.path = path

    def output(self, collection: CoinCollection, qty: int = 3) -> None:
        result = []

        rows_top = [self._row(coin) for coin in collection.top_gainers(qty=qty)]
        rows_los = [self._row(coin) for coin in collection.top_losers(qty=qty)]

        result.append(self._column())
        result.extend(rows_top)
        result.extend(rows_los)

        with open(self.path, "w", newline='', encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerows(result)

        self.console.print(f"[green]Отчет сохранен в {self.path}[/]")


class Source(str, Enum):
    coingecko = "coingecko"
    coinmarketcap = "coinmarketcap"


class OutputFormat(str, Enum):
    console = "console"
    json = "json"
    csv = "csv"

def main(source: Source = Source.coingecko, output: OutputFormat = OutputFormat.console, top: int = 3):
    console = Console()

    provider_class = PROVIDER_REGISTRY.get(source)
    if provider_class is None:
        raise ValueError("Invalid '--source'")

    connector = Connector(console, headers=provider_class.build_headers())
    provider = provider_class(connector)

    try:
        with provider:
            coins_top_50 = provider.get_coins()
        collection = CoinCollection(coins_top_50)
    except requests.exceptions.RequestException as e:
        console.print(f"[red]Ошибка подключения к провайдеру: {e}[/]")
        raise
    except ValueError as e:
        console.print(f"[red]Ошибка данных: {e}[/]")
        raise

    output_class = OUTPUT_REGISTRY.get(output)
    output_source = output_class(console)
    output_source.output(collection, top)


if __name__ == "__main__":
    typer.run(main)
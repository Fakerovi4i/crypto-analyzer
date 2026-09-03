from contextlib import contextmanager
from datetime import datetime
from enum import Enum
from time import sleep
import functools
from dataclasses import dataclass, fields, asdict
from abc import ABC, abstractmethod
import sqlite3
import json
import os
import csv
from typing import Any

from rich.console import Console
from rich.table import Table
import requests
import typer

from settings import Settings as settings




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
    id: str | int
    name: str
    symbol: str
    price_change_percentage_24h: float
    total_volume: float
    market_cap: float
    price: float

    def __post_init__(self):
        if not isinstance(self.price, (int, float)):
            raise ValueError("price must be a number")
        if not isinstance(self.name, str):
            raise ValueError("name must be a string")
        if not isinstance(self.symbol, str):
            raise ValueError("symbol must be a string")
        if not isinstance(self.total_volume, (int, float)):
            raise ValueError("total_volume must be a number")
        if not isinstance(self.market_cap, (int, float)):
            raise ValueError("market_cap must be a number")
        if self.total_volume < 0:
            raise ValueError("total_volume must not be negative")
        if self.market_cap < 0:
            raise ValueError("market_cap must not be negative")
        if self.price_change_percentage_24h is None:
            self.price_change_percentage_24h = 0.0
        elif not isinstance(self.price_change_percentage_24h, (int, float)):
            raise ValueError("price_change_percentage_24h must be a number")


    def __str__(self):
        return (
            f"class: {self.__class__.__name__} | "
            f"name: {self.name} | "
            f"id: {self.id} | "
            f"price_change_24: {self.price_change_percentage_24h} | "
            f"price: {self.price}"
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
            path: str = "/api/v3/coins/markets"
    ):
        super().__init__(connector, host, path)


    def get_coins(self, params: dict | None = None) -> list[Coin]:
        if params is None:
            params = {"vs_currency": "usd", "order": "market_cap_desc", "per_page": 50, "page": 1}

        raw_data = self.fetch_raw(params)
        coins = [
            Coin(
                id=item["id"],
                name=item["name"],
                symbol=item["symbol"],
                price_change_percentage_24h=item["price_change_percentage_24h"],
                total_volume=item["total_volume"],
                market_cap=item["market_cap"],
                price=item["current_price"]
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
                price=item["quote"][0]["price"]
            )
            for item in raw_data
        ]
        return coins


    def fetch_raw(self, params: dict) -> list[dict]:
        response: dict = self.connector.get(url=self.url, params=params)
        return response["data"]


class CoinCollection:
    def __init__(self, coins: list[Coin]):
        if not coins or not isinstance(coins, list) or not all(isinstance(coin, Coin) for coin in coins):
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
    csv = "csv"


STORAGE_REGISTRY = {}
def register_storage(name: str):
    def decorator(cls):
        STORAGE_REGISTRY[name] = cls
        return cls
    return decorator


class BaseStorage(ABC):
    @abstractmethod
    def save(self, results: dict) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False



@register_storage("json")
class JsonStorage(BaseStorage):
    def __init__(self, path: str = "crypto_report.json"):
        self.path = path

    def save(self, results: dict) -> None:
        data_to_write = results.copy()
        del data_to_write["all_coins"]
        with open(self.path, "w", encoding="utf-8") as file:
            json.dump(data_to_write, file, indent=4, ensure_ascii=False)


@register_storage("sqlite")
class SqliteStorage(BaseStorage):
    def __init__(self, path: str = "crypto_report.db"):
        self.path = path
        self._conn: sqlite3.Connection | None = None

    def _init_schema_db(self):
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                source TEXT NOT NULL
            )
            """
        )

        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS coin_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL,
                coin_id TEXT,
                name TEXT,
                symbol TEXT,
                price_change_percentage_24h REAL,
                total_volume REAL,
                market_cap REAL,
                price REAL,
                FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
            )
            """
        )
        self._conn.commit()

    def save(self, results: dict) -> None:
        if self._conn is None:
            raise RuntimeError("Storage is not opened. Use 'with SqliteStorage(...)'")
        self._conn.execute("PRAGMA foreign_keys = ON")

        cursor = self._conn.cursor()
        cursor.execute(
            """
            INSERT INTO snapshots (created_at, source) VALUES (?, ?)
            """,
            (results.get("generated_at"), results.get("source"))

        )
        snapshot_id = cursor.lastrowid

        for coin in results.get("all_coins"):
            cursor.execute(
                """
                INSERT INTO coin_prices (
                snapshot_id, 
                coin_id, 
                name,
                symbol,
                price_change_percentage_24h, 
                total_volume, 
                market_cap,
                price
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    coin.get("id"),
                    coin.get("name"),
                    coin.get("symbol"),
                    coin.get("price_change_percentage_24h"),
                    coin.get("total_volume"),
                    coin.get("market_cap"),
                    coin.get("price"),
                )
            )

        self._conn.commit()


    def __enter__(self):
        self._conn = sqlite3.connect(self.path)
        self._init_schema_db()
        return self


    def __exit__(self, exc_type, exc_val, exc_tb):
        self._conn.close()

class SqliteAnalytics:
    def __init__(self, path: str = "crypto_report.db"):
        self.path = path

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.path)
        try:
            yield conn
        finally:
            conn.close()

    def coin_price_history(self, coin_id: str) -> list[tuple]:
        with self._get_connection() as conn:
            return conn.execute(
                """
                SELECT
                    snapshots.id, 
                    snapshots.created_at, 
                    coin_prices.price
                FROM snapshots
                JOIN coin_prices ON snapshots.id = coin_prices.snapshot_id
                WHERE coin_prices.coin_id = ?
                ORDER BY snapshots.created_at
                """,
                (coin_id,)
            ).fetchall()

    def list_snapshots(self):
        with self._get_connection() as conn:
            return conn.execute(
                """
                SELECT
                    snapshots.id, 
                    snapshots.created_at,
                    snapshots.source
                FROM snapshots
                ORDER BY snapshots.created_at
                """
            ).fetchall()

    def compare_snapshots(self, id_1: int, id_2: int) -> list[tuple]:
        with self._get_connection() as conn:
            return conn.execute(
                """
                SELECT
                    a.coin_id,
                    a.name,
                    ROUND(a.price, 4) as price_before,
                    ROUND(b.price, 4) as price_after,
                    ROUND((a.price - b.price), 4) as price_difference
                FROM coin_prices as a
                JOIN coin_prices as b ON a.coin_id = b.coin_id
                WHERE a.snapshot_id = ? AND b.snapshot_id = ?
                """,
                (id_1, id_2)
            ).fetchall()

    def top_5_gainers_losers(self, qty: int = 5) -> dict:
        last_snapshot = self.list_snapshots()[-1]
        if not last_snapshot:
            return {"top_gainers": [], "top_losers": []}

        last_snapshot_id = last_snapshot[0]

        with self._get_connection() as conn:
            gainers = conn.execute(
                """
                SELECT coin_id, price, price_change_percentage_24h
                FROM coin_prices
                WHERE snapshot_id = ?
                ORDER BY price_change_percentage_24h DESC
                LIMIT ?
                """,
                (last_snapshot_id, qty)
            ).fetchall()

            losers = conn.execute(
                """
                SELECT coin_id, price, price_change_percentage_24h
                FROM coin_prices
                WHERE snapshot_id = ?
                ORDER BY price_change_percentage_24h ASC
                LIMIT ?
                """,
                (last_snapshot_id, qty)
            ).fetchall()

        return {
            "top_gainers": gainers,
            "top_losers": losers,
        }


def create_report_data(collection: CoinCollection, qty: int, source: str) -> dict:
    return {
        "source": source,

        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_coins_analyzed": len(collection.coins),
        "total_market_cap_usd": collection.total_market_cap(),
        "top_gainers": [asdict(coin) for coin in collection.top_gainers(qty)],
        "top_losers": [asdict(coin) for coin in collection.top_losers(qty)],
        "highest_volume": asdict(collection.top_volume()),

        "all_coins": [asdict(coin) for coin in collection.coins], #для SqliteStorage

    }


def print_table(title: str, columns: list[str], rows: list[tuple]):
    table = Table(title=title, title_style="yellow bold")

    for column in columns:
        table.add_column(column, header_style="green bold", style="yellow", max_width=12, no_wrap=True, overflow="ellipsis")

    for row in rows:
        table.add_row(*(str(value) for value in row))

    console.print(table)



console = Console()
app = typer.Typer()

@app.callback(invoke_without_command=True)
def default(
        ctx: typer.Context,
        source: Source = Source.coingecko,
        output: OutputFormat = OutputFormat.console,
        top: int = 3):
    """Собрать данные с провайдера, показать и сохранить снимок (запускается по умолчанию)."""
    if ctx.invoked_subcommand is not None:
        # вызвана конкретная подкоманда (list-snapshots/compare-snapshots) — пропускаем
        return


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

    # Сохранение в json или sqlite (источник в .env)
    report = create_report_data(collection, top, source.value)
    storage_cls = STORAGE_REGISTRY.get(settings.storage)
    with storage_cls() as storage:
        storage.save(report)


@app.command(name="list-snapshots")
def list_snapshot():
    """Показать все снимки"""
    rows = SqliteAnalytics().list_snapshots()
    print_table(title="Снимки", columns=["id", "created_at", "source"], rows=rows)


@app.command(name="compare-snapshots")
def compare_snapshots(id_1: int, id_2: int):
    """Сравнить два снимка по ID и показать изменение цены каждой монеты."""
    rows = SqliteAnalytics().compare_snapshots(id_1, id_2)
    print_table(title="Сравнение снимков", columns=["coin_id", "name", "price_before", "price_after", "price_difference"], rows=rows)


@app.command(name="coin-history")
def coin_price_history(coin_id: str):
    """Показать историю цены монеты по всем снимкам."""
    rows = SqliteAnalytics().coin_price_history(coin_id)
    print_table(title=f"История цены: '{coin_id}'", columns=["snap_id", "created_at", "price"], rows=rows)

@app.command(name="top-5")
def top_5_last_snapshot():
    """Показать по 5 лидеров роста и падения цены из последнегго снимка"""
    gainers_losers = SqliteAnalytics().top_5_gainers_losers()
    table = Table(title="Топ роста/падения цены последнего снимка", title_style="yellow bold")
    columns = ["coin_id", "price", "price_change_24h"]
    for column in columns:
        table.add_column(column, header_style="green bold", style="yellow")

    for g in gainers_losers["top_gainers"]:
        table.add_row(*(str(value) for value in g), style="green")

    for l in gainers_losers["top_losers"]:
        table.add_row(*(str(value) for value in l), style="red")

    console.print(table)






if __name__ == "__main__":
    app()


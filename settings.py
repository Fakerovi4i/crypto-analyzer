import os
from enum import Enum
import dotenv

dotenv.load_dotenv()


class StorageType(str, Enum):
    JSON = "json"
    SQLITE = "sqlite"


class Settings:
    storage: StorageType = StorageType(os.getenv("STORAGE", "json"))

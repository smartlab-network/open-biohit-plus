import os
import sqlite3
from pathlib import Path

def get_db_dir():
    return Path("C:/ProgramData/biohit")

def get_db_path():
    return get_db_dir().joinpath("pipettor.db")

def create_db():
    os.makedirs(get_db_dir(), exist_ok=True)

    conn = sqlite3.connect(get_db_path())

    print("Created db in: ", get_db_path())

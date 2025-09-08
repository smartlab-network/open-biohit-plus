import json
from pathlib import Path
import os
import pickle

def get_json_dir():
    return Path("C:/ProgramData/biohit")

def get_json_path():
    return get_json_dir().joinpath("pipettor.kjson")

def create_json_file():
    pass

def write_json(id: str, info: dict):
    with(open(get_json_path()))

def read_json():
    pass

import json
from pathlib import Path
from .serializable import CLASS_REGISTRY, Serializable

def get_json_dir() -> Path:
    return Path("C:/ProgramData/biohit")

def get_json_path() -> Path:
    return get_json_dir().joinpath("pipettor.json")

def create_json_file():
    """Ensure the JSON file exists."""
    path = get_json_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with open(path, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4)

def write_json(obj):
    """
    Save any Serializable object to JSON file with ID index. class Serializable is defined in serializable
    """
    import json
    from pathlib import Path

    path = Path("C:/ProgramData/biohit/pipettor.json")
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {"_index": {}}

    obj_dict = obj.to_dict()
    obj_id_field = [k for k in obj_dict.keys() if k.endswith("_id")][0]
    obj_id = obj_dict[obj_id_field]
    obj_class = obj_dict["class"]

    # Save object itself
    data[obj_id] = obj_dict

    # Update index
    if obj_class not in data["_index"]:
        data["_index"][obj_class] = []
    if obj_id not in data["_index"][obj_class]:
        data["_index"][obj_class].append(obj_id)

    # Write back
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def list_ids(class_name: str = None):
    """List all stored IDs, optionally filtered by class."""
    import json
    from pathlib import Path

    path = Path("C:/ProgramData/biohit/pipettor.json")
    if not path.exists():
        return {}

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "_index" not in data:
        return {}

    if class_name:
        return data["_index"].get(class_name, [])
    return data["_index"]

def read_json(obj_id: str):
    """
    Load object by its id using the class registry.
    The object needs to be from class Serializable and needs the to_dict method.
    """
    import json
    from pathlib import Path

    path = Path("C:/ProgramData/biohit/pipettor.json")
    if not path.exists():
        raise FileNotFoundError("JSON file does not exist.")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if obj_id not in data:
        raise KeyError(f"Object id '{obj_id}' not found in JSON.")
    return Serializable.from_dict(data[obj_id])
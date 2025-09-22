import json
from pathlib import Path
from .serializable import CLASS_REGISTRY, Serializable


def get_json_dir() -> Path:
    """
    Returns the directory path where the JSON file will be stored.

    Returns
    -------
    Path
        Path object for the storage directory.
    """
    return Path("C:/ProgramData/biohit")


def get_json_path() -> Path:
    """
    Returns the full path to the JSON file.

    Returns
    -------
    Path
        Full file path for the JSON file.
    """
    return get_json_dir().joinpath("pipettor.json")


def create_json_file():
    """
    Ensure the JSON file exists. Creates directory and empty JSON if necessary.
    """
    path = get_json_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"_index": {}}, f, indent=4)


def write_json(obj: Serializable):
    """
    Save any Serializable object to JSON file with ID index.

    Parameters
    ----------
    obj : Serializable
        The object to store in JSON. Must implement to_dict() and have an ID field.
    """
    path = get_json_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {"_index": {}}

    # Convert object to dict
    obj_dict = obj.to_dict()

    # Detect object's ID field (assumes field ends with '_id')
    obj_id_field = [k for k in obj_dict.keys() if k.endswith("_id")][0]
    obj_id = obj_dict[obj_id_field]
    obj_class = obj_dict["class"]

    # Save the object under its ID
    data[obj_id] = obj_dict

    # Update the index for fast class-based lookup
    if obj_class not in data["_index"]:
        data["_index"][obj_class] = []
    if obj_id not in data["_index"][obj_class]:
        data["_index"][obj_class].append(obj_id)

    # Write back to JSON file
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def list_ids(class_name: str = None):
    """
    List all stored IDs, optionally filtered by class.

    Parameters
    ----------
    class_name : str, optional
        If provided, only return IDs for this class.

    Returns
    -------
    dict or list
        Dictionary of all IDs by class or list of IDs for the given class.
    """
    path = get_json_path()
    if not path.exists():
        return {}

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "_index" not in data:
        return {}

    if class_name:
        return data["_index"].get(class_name, [])
    return data["_index"]


def read_json(obj_id: str) -> Serializable:
    """
    Load object by its ID using the class registry.

    Parameters
    ----------
    obj_id : str
        Unique identifier of the object to load.

    Returns
    -------
    Serializable
        Reconstructed object.

    Raises
    ------
    FileNotFoundError
        If the JSON file does not exist.
    KeyError
        If the object ID is not found.
    """
    path = get_json_path()
    if not path.exists():
        raise FileNotFoundError("JSON file does not exist.")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if obj_id not in data:
        raise KeyError(f"Object id '{obj_id}' not found in JSON.")

    # Use the global Serializable.from_dict to reconstruct the object
    return Serializable.from_dict(data[obj_id])
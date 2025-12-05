import json
from pathlib import Path
from .serializable import Serializable


def get_json_dir() -> Path:
    """
    Returns the directory path where the JSON file will be stored.
    """
    return Path("../C:/ProgramData/biohit")


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


def save_deck_for_gui(deck_object: Serializable,
                      filename: str,
                      unplaced_labware: list = None,
                      unplaced_slots: list = None,
                      available_wells: list = None,
                      available_reservoirs: list = None,
                      available_individual_holders: list = None):
    """
    Saves a Deck object and its related components in the GUI-compatible format.

    This saves to a specific 'filename' (e.g., "deck1_for_gui.json")
    in the default directory (C:/ProgramData/biohit).

    It converts lists of objects into lists of dictionaries for JSON serialization.
    """
    # Get the directory path and join it with the desired filename
    if not filename.endswith(".json"):
        filename += ".json"

    path = get_json_dir().joinpath(filename)
    path.parent.mkdir(parents=True, exist_ok=True)

    # --- UPDATED SECTION ---
    # Default to empty lists if no arguments are passed
    if unplaced_labware is None:
        unplaced_labware = []
    if unplaced_slots is None:
        unplaced_slots = []
    if available_wells is None:
        available_wells = []
    if available_reservoirs is None:
        available_reservoirs = []
    if available_individual_holders is None:
        available_individual_holders = []

    # Prepare data for JSON, converting all objects in lists to dicts
    gui_data = {
        'deck': deck_object.to_dict(),
        'unplaced_labware': [lw.to_dict() for lw in unplaced_labware],
        'unplaced_slots': [slot.to_dict() for slot in unplaced_slots],
        'available_wells': [well.to_dict() for well in available_wells],
        'available_reservoirs': [res.to_dict() for res in available_reservoirs],
        'available_individual_holders': [holder.to_dict() for holder in available_individual_holders]
    }
    # --- END UPDATED SECTION ---

    try:
        with open(path, 'w') as f:
            json.dump(gui_data, f, indent=2)
        print(f"Deck configuration saved to {path} in GUI-compatible format.")
    except Exception as e:
        print(f"Failed to save deck: {str(e)}")

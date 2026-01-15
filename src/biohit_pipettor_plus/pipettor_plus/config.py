import json
from pathlib import Path
from biohit_pipettor_plus.pipettor_plus.pipettor_constants import (Pipettors_in_Multi, MAX_BATCH_SIZE, TIP_LENGTHS, Z_MAX,
                                                                   Spacing_Between_Adjacent_Pipettor)

CONFIG_PATH = Path.home() / ".pipettor_plus_config.json"

DEFAULTS = {
    "Pipettors_in_Multi": Pipettors_in_Multi,
    "Spacing_Between_Adjacent_Pipettor": Spacing_Between_Adjacent_Pipettor,
    "MAX_BATCH_SIZE": MAX_BATCH_SIZE,
    "TIP_LENGTHS": TIP_LENGTHS,
    "Z_MAX": Z_MAX,
}

def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r") as f:
            data = json.load(f)

        merged = {**DEFAULTS, **data}

        # fix TIP_LENGTHS key types if present
        if "TIP_LENGTHS" in merged:
            merged["TIP_LENGTHS"] = {int(k): int(v) for k, v in merged["TIP_LENGTHS"].items()}

        return merged

    return DEFAULTS.copy()


def save_config(new_cfg: dict) -> None:
    # start from existing saved config (if any)
    saved = {}
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r") as f:
            saved = json.load(f)

    # update saved overrides
    saved.update(new_cfg)

    # keep only values that differ from defaults
    cleaned = {k: v for k, v in saved.items() if DEFAULTS.get(k) != v}

    with open(CONFIG_PATH, "w") as f:
        json.dump(cleaned, f, indent=2)


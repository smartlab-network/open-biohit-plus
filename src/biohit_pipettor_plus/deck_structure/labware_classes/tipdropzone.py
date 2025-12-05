
from .labware import Labware
from ..serializable import register_class

@register_class
class TipDropzone(Labware):
    """
    Represents a Tip Dropzone labware with relative drop position and height.

    Attributes
    ----------
    drop_height_relative : float
        Drop height relative to the labware height.
    """

    def __init__(self, size_x: float,
                 size_y: float,
                 size_z: float,
                 can_be_stacked_upon: bool = False,
                 offset: tuple[float, float] = (0, 0),
                 drop_height_relative: float = 20,
                 position: tuple[float, float] = None,
                 labware_id: str = None
                 ):
        """
        Initialize a TipDropzone instance.

        Parameters
        ----------
        size_x : float
            Width of the drop zone in millimeters.
        size_y : float
            Depth of the drop zone in millimeters.
        size_z : float
            Height of the drop zone in millimeters.
        labware_id : str, optional
            Unique ID for the dropzone object.
        position : tuple[float, float], optional
            (x, y) position coordinates of the tip dropzone in millimeters.
            If None, position is not set.
        drop_height_relative : float, optional
            Height from which tips are dropped relative to the labware. Default is 20.
        """
        super().__init__(size_x=size_x, size_y=size_y, size_z=size_z, offset=offset, labware_id=labware_id,
                         position=position, can_be_stacked_upon=can_be_stacked_upon)
        self.drop_height_relative = drop_height_relative

    def get_state_snapshot(self) -> dict:
        """Return empty snapshot - TipDropzone has no mutable state"""
        return {}

    def restore_state_snapshot(self, snapshot: dict) -> None:
        """No-op - TipDropzone has no mutable state to restore"""
        pass

    def to_dict(self) -> dict:
        """
        Serialize the TipDropzone instance to a dictionary, extending the base Labware fields.

        Returns
        -------
        dict
            dictionary representation of the tip dropzone.
        """
        base_dict = super().to_dict()
        base_dict.update({
            "drop_height_relative": self.drop_height_relative,
        })
        return base_dict

    @classmethod
    def _from_dict(cls, data: dict) -> "TipDropzone":
        """
        Deserialize a TipDropzone instance from a dictionary using the base Labware _from_dict.

        Parameters
        ----------
        data : dict
            dictionary containing tip dropzone attributes.

        Returns
        -------
        TipDropzone
            Reconstructed TipDropzone instance.
        """
        # Safely handle position deserialization
        # Safely handle position deserialization
        position = tuple(data["position"]) if data.get("position") else None

        return cls(
            size_x=data["size_x"],
            size_y=data["size_y"],
            size_z=data["size_z"],
            offset=data["offset"],
            can_be_stacked_upon=data.get("can_be_stacked_upon", False),
            position=position,
            drop_height_relative=data["drop_height_relative"],
            labware_id=data["labware_id"]
        )

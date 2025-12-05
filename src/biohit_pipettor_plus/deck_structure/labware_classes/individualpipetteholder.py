
from .labware import Labware
from ..serializable import register_class


@register_class
class IndividualPipetteHolder(Labware):
    """
    Represents an individual pipette holder position within a PipetteHolder.
    Tracks occupancy status and pipette type.

    Attributes
    ----------
    is_occupied : bool
        Whether this holder position currently contains a pipette.
    """

    def __init__(
            self,
            size_x: float,
            size_y: float,
            size_z: float,
            offset: tuple[float, float] = (0, 0),
            is_occupied: bool = True,
            row: int = None,
            column: int = None,
            labware_id: str = None,
            can_be_stacked_upon: bool = False,
            position: tuple[float, float] = None
    ):
        """
        Initialize an IndividualPipetteHolder instance.

        Parameters
        ----------
        size_x : float
            Width of the individual holder position in millimeters.
        size_y : float
            Depth of the individual holder position in millimeters.
        size_z : float
            Height of the individual holder position in millimeters.
        is_occupied : bool, optional
            Whether a pipette is currently stored here. Default is False.
        labware_id : str, optional
            Unique identifier for this holder position. If None, a UUID will be generated.
        position : tuple[float, float], optional
            (x, y) absolute position coordinates in millimeters.
            If None, position is not set.
        """
        super().__init__(
            size_x=size_x,
            size_y=size_y,
            size_z=size_z,
            offset=offset,
            labware_id=labware_id,
            position=position,
            can_be_stacked_upon=can_be_stacked_upon
        )

        self.is_occupied = is_occupied
        self.row = row
        self.column = column

    def place_pipette(self) -> None:
        """
        Mark this holder position as occupied (pipette placed).
        Raises ValueError If the holder position is already occupied.
        """
        if self.is_occupied:
            raise ValueError(
                f"Holder position {self.labware_id} is already occupied"
            )

        self.is_occupied = True

    def remove_pipette(self) -> None:
        """
        Mark this holder position as available (pipette removed).

        Raises
        ------
        ValueError
            If the holder position is already empty.
        """
        if not self.is_occupied:
            raise ValueError(f"Holder position {self.labware_id} is already empty")

        self.is_occupied = False

    def is_available(self) -> bool:
        """
        Check if this holder position is available for placing a pipette.
        Returns bool.True if available (not occupied), False otherwise.
        """
        return not self.is_occupied

    def get_state_snapshot(self) -> dict:
        """Return deep copy of mutable state"""
        return {'is_occupied': self.is_occupied}

    def restore_state_snapshot(self, snapshot: dict) -> None:
        """Restore state from snapshot"""
        self.is_occupied = snapshot['is_occupied']

    def to_dict(self) -> dict:
        """
        Serialize the IndividualPipetteHolder to a dictionary.
        Returns dict
            Dictionary containing all holder attributes.
        """
        base = super().to_dict()
        base.update({
            "is_occupied": self.is_occupied,
            "row": self.row,
            "column": self.column,
        })
        return base

    @classmethod
    def _from_dict(cls, data: dict) -> "IndividualPipetteHolder":
        """
        Deserialize an IndividualPipetteHolder instance from a dictionary.

        Parameters
        data : dict
            Dictionary with IndividualPipetteHolder attributes.

        Returns IndividualPipetteHolder
            Reconstructed IndividualPipetteHolder instance.
        """
        # Safely handle position deserialization
        position = tuple(data["position"]) if data.get("position") else None

        return cls(
            size_x=data["size_x"],
            size_y=data["size_y"],
            size_z=data["size_z"],
            offset=data["offset"],
            labware_id=data["labware_id"],
            can_be_stacked_upon=data.get("can_be_stacked_upon", False),
            position=position,
            is_occupied=data.get("is_occupied", False),
            row=data.get("row"),
            column=data.get("column"),
        )
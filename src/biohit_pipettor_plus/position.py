class PositionCalculator:
    """
    General position calculator for labware (plates, reservoirs, tips).
    Provides dynamic computation instead of hardcoded offsets.
    """

    def __init__(self, x_corner: float, y_corner: float):
        self.x_corner = x_corner
        self.y_corner = y_corner

    def position_multi(self, count: int, step_x: float, offset: tuple[float, float]) -> dict:
        """
        In a multipipette setting, compute location of given labware and returns a dict.
        :param count: number of containers (along x-axis)
        :param step_x: spacing along X
        :param offset: (dx, dy) offset for first reservoir
        :return: dict {container_index: (x,y)}
        """
        dx, dy = offset
        temp_dict = {}
        for i in range(count):
            x = self.x_corner + dx + i * step_x
            y = self.y_corner + dy
            temp_dict[i + 1] = (x, y)
        return temp_dict


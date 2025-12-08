"""
Geometric calculations for liquid handling in different container shapes.

This module provides functions to calculate liquid heights based on volume
and container geometry for various common laboratory container shapes.
"""

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..deck_structure.labware_classes.labware import Labware


def calculate_liquid_height(item: 'Labware') -> float:
    """
    Calculate the current height of liquid in a container based on volume and shape.

    Uses proper geometric formulas for different container shapes.

    Parameters
    ---------
    item : Labware
        Well or Reservoir containing liquid

    Returns
    -------
    float
        Height of liquid surface from container bottom (mm)
    """
    # Check if item has volume tracking
    if not hasattr(item, 'get_total_volume') or not hasattr(item, 'capacity'):
        return 0

    current_volume = item.get_total_volume()  # µL

    if current_volume <= 0:
        return 0  # Empty container

    # Get shape, default to rectangular if not specified
    shape = getattr(item, 'shape', 'rectangular').lower()

    # Route to appropriate shape calculator
    if shape == "rectangular":
        return calculate_height_rectangular(item)
    elif shape == "circular":
        return calculate_height_circular(item)
    elif shape == "conical":
        return calculate_height_conical(item)
    elif shape == "u_bottom":
        return calculate_height_u_bottom(item)
    else:
        # Unknown shape - use rectangular as fallback
        print(f"  ⚠️ Warning: Unknown shape '{shape}', using rectangular calculation")
        return calculate_height_rectangular(item)


def calculate_height_rectangular(item: 'Labware') -> float:
    """
    Calculate liquid height for rectangular container.

    Volume = length × width × height
    Height = Volume / (length × width)

    Parameters
    ----------
    item : Labware
        Container with rectangular cross-section

    Returns
    -------
    float
        Liquid height (mm)

    Notes
    -----
    This is the most common shape for reservoirs and troughs.
    """
    current_volume = item.get_total_volume()  # µL

    # Convert µL to mm³ (1 µL = 1 mm³)
    volume_mm3 = current_volume

    # Cross-sectional area (mm²)
    area = item.size_x * item.size_y

    if area <= 0:
        return 0.0

    # Height = Volume / Area
    height = volume_mm3 / area

    # Don't exceed container height
    height = min(height, item.size_z)

    return height


def calculate_height_circular(item: 'Labware') -> float:
    """
    Calculate liquid height for cylindrical container.

    Volume = π × r² × height
    Height = Volume / (π × r²)

    Parameters
    ----------
    item : Labware
        Container with circular cross-section

    Returns
    -------
    float
        Liquid height (mm)

    Notes
    -----
    Common for tubes and some well plates. Assumes the diameter is the
    smaller of size_x or size_y (circular fits within square bounds).
    """
    current_volume = item.get_total_volume()  # µL
    volume_mm3 = current_volume  # 1 µL = 1 mm³

    # Use smaller dimension as diameter (assume circular fits in square bounds)
    diameter = min(item.size_x, item.size_y)
    radius = diameter / 2

    if radius <= 0:
        return 0.0

    # Cross-sectional area = π × r²
    area = math.pi * radius * radius

    # Height = Volume / Area
    height = volume_mm3 / area

    # Don't exceed container height
    height = min(height, item.size_z)

    return height


def calculate_height_conical(item: 'Labware') -> float:
    """
    Calculate liquid height for conical container (cone pointing down).

    For a cone with apex at bottom:
    V = (1/3) × π × r² × h
    where r varies linearly with h: r(h) = (R/H) × h
    (R = radius at top, H = total height)

    Solving for h: h = ∛(3V × H² / (π × R²))

    Parameters
    ----------
    item : Labware
        Container with conical shape (V-bottom)

    Returns
    -------
    float
        Liquid height (mm)

    Notes
    -----
    Common for centrifuge tubes and some specialized well plates.
    The cone apex is assumed to be at the bottom.
    """
    current_volume = item.get_total_volume()  # µL
    volume_mm3 = current_volume  # 1 µL = 1 mm³

    # Total height of cone
    H = item.size_z

    # Radius at top (use smaller dimension)
    R = min(item.size_x, item.size_y) / 2

    if R <= 0 or H <= 0:
        return 0.0

    # For a cone with volume V, solve for height h
    # V = (1/3) × π × (r(h))² × h
    # Where r(h) = (R/H) × h (radius varies linearly with height)
    # Substituting: V = (1/3) × π × ((R/H) × h)² × h
    # V = (1/3) × π × (R²/H²) × h³
    # Solving for h: h³ = 3V × H² / (π × R²)
    # h = ∛(3V × H² / (π × R²))

    numerator = 3 * volume_mm3 * H * H
    denominator = math.pi * R * R

    if denominator <= 0:
        return 0.0

    h_cubed = numerator / denominator
    height = h_cubed ** (1 / 3)  # Cube root

    # Don't exceed container height
    height = min(height, item.size_z)

    return height


def calculate_height_u_bottom(item: 'Labware') -> float:
    """
    Calculate liquid height for U-bottom (hemispherical bottom) container.

    Model: Hemisphere + Cylinder
    - Bottom portion is a hemisphere with radius R
    - Above the hemisphere is a cylinder

    Parameters
    ----------
    item : Labware
        Container with U-bottom (round-bottom)

    Returns
    -------
    float
        Liquid height (mm)

    Notes
    -----
    Very common for cell culture plates (96-well, 384-well).
    For liquid only in hemisphere: uses approximation based on fill ratio.
    For liquid above hemisphere: exact calculation using cylinder formula.
    """
    current_volume = item.get_total_volume()  # µL
    volume_mm3 = current_volume  # 1 µL = 1 mm³

    # Radius of hemisphere (use smaller dimension)
    R = min(item.size_x, item.size_y) / 2

    if R <= 0:
        return 0.0

    # Volume of full hemisphere: V = (2/3) × π × R³
    hemisphere_volume = (2 / 3) * math.pi * R * R * R

    if volume_mm3 <= hemisphere_volume:
        # Liquid is only in the hemispherical portion
        # For partial sphere filling, use approximation:
        # h ≈ (V / V_hemisphere) × R
        # This is an approximation; exact calculation requires solving
        # a cubic equation for spherical cap volume
        fill_ratio = volume_mm3 / hemisphere_volume
        height = fill_ratio * R
    else:
        # Liquid fills entire hemisphere + cylindrical portion above
        remaining_volume = volume_mm3 - hemisphere_volume

        # Cylindrical part: V = π × R² × h
        cylinder_area = math.pi * R * R
        cylinder_height = remaining_volume / cylinder_area

        # Total height = hemisphere radius + cylinder height
        height = R + cylinder_height

    # Don't exceed container height
    height = min(height, item.size_z)

    return height


def calculate_dynamic_remove_height(item: 'Labware', volume_to_remove: float) -> float:
    """
    Calculate optimal aspiration height based on current and final liquid levels.

    Strategy:
    - Aspirate from midpoint between current level and final level

    Parameters
    ----------
    item : Labware
        Well or Reservoir to aspirate from
    volume_to_remove : float
        Volume that will be aspirated (µL)

    Returns
    -------
    float
        Optimal aspiration height from container Top (mm)
    """
    # Get current liquid height
    current_height = calculate_liquid_height(item)

    if current_height <= 0:
        # Empty or no tracking - use default
        return 0

    # Calculate liquid height after removal
    current_volume = item.get_total_volume()
    final_volume = max(0, current_volume - volume_to_remove)

    # Temporarily adjust volume to calculate final height
    # Save current content
    original_content = item.content.copy()

    # Set content to final volume (proportionally)
    if current_volume > 0:
        scale_factor = final_volume / current_volume
        item.content = {k: v * scale_factor for k, v in original_content.items()}

    final_height = calculate_liquid_height(item)

    # Restore original content
    item.content = original_content

    # Aspirate from midpoint between current and final. Target_height is height from labware top
    target_height = ((current_height + final_height) / 2)
    return target_height

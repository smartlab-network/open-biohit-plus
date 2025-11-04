"""
Pipette Slot Position Finder
This script helps you manually find and record the correct slot positions
"""

from pipettor_plus import PipettorPlus
from deck import Deck
import json
from datetime import datetime

def find_slot_positions():
    """Interactive tool to find and save pipette holder slot positions"""

    # Initialize pipettor
    deck1 = Deck((0, 500), (0, 500), range_z=300, deck_id="trial")
    p = PipettorPlus(tip_volume=1000, multichannel=True, deck=deck1)
    p.home()  # Make sure it's homed

    print("=" * 60)
    print("SLOT POSITION FINDER")
    print("=" * 60)
    print("\nCommands:")
    print("  w/s: Move Y axis (forward/backward)")
    print("  a/d: Move X axis (left/right)")
    print("  W/S [distance]: Move Y axis (large steps, optional distance)")
    print("  A/D [distance]: Move X axis (large steps, optional distance)")
    print("  Examples: 'W' moves 100mm, 'W 50' moves 50mm")
    print("  g: Go to custom X,Y coordinates")
    print("  z: Move to custom Z position")
    print("  p: Save current position")
    print("  q: Quit and save all positions")
    print("  h: Go to home position")
    print("  c: Show current position")
    print("=" * 60)

    # Movement step sizes
    small_step = 10.0  # mm
    large_step = 100.0  # mm (default for W/A/S/D)

    # Get current position
    try:
        current_x, current_y = p.get_position()  # Check if this method exists
    except:
        # If get_position doesn't exist, start from home
        current_x, current_y = 0.0, 0.0
        print("\nWarning: Cannot read position. Starting from 0,0")

    saved_positions = []

    while True:
        try:
            user_input = input(f"\nCurrent: X={current_x:.2f}, Y={current_y:.2f} > ").strip()

            # Split command and optional argument
            parts = user_input.split()
            command = parts[0] if parts else ''

            # Get custom step size if provided
            custom_step = None
            if len(parts) > 1:
                try:
                    custom_step = float(parts[1])
                except ValueError:
                    print(f"Error: '{parts[1]}' is not a valid number")
                    continue

            if command == 'q':
                break

            elif command == 'w':
                current_y += small_step
                p.move_xy(current_x, current_y)
                print(f"Moved to X={current_x:.2f}, Y={current_y:.2f}")

            elif command == 's':
                current_y -= small_step
                p.move_xy(current_x, current_y)
                print(f"Moved to X={current_x:.2f}, Y={current_y:.2f}")

            elif command == 'a':
                current_x -= small_step
                p.move_xy(current_x, current_y)
                print(f"Moved to X={current_x:.2f}, Y={current_y:.2f}")

            elif command == 'd':
                current_x += small_step
                p.move_xy(current_x, current_y)
                print(f"Moved to X={current_x:.2f}, Y={current_y:.2f}")

            elif command == 'W':
                step = custom_step if custom_step is not None else large_step
                current_y += step
                p.move_xy(current_x, current_y)
                print(f"Moved {step}mm to X={current_x:.2f}, Y={current_y:.2f}")

            elif command == 'S':
                step = custom_step if custom_step is not None else large_step
                current_y -= step
                p.move_xy(current_x, current_y)
                print(f"Moved {step}mm to X={current_x:.2f}, Y={current_y:.2f}")

            elif command == 'A':
                step = custom_step if custom_step is not None else large_step
                current_x -= step
                p.move_xy(current_x, current_y)
                print(f"Moved {step}mm to X={current_x:.2f}, Y={current_y:.2f}")

            elif command == 'D':
                step = custom_step if custom_step is not None else large_step
                current_x += step
                p.move_xy(current_x, current_y)
                print(f"Moved {step}mm to X={current_x:.2f}, Y={current_y:.2f}")

            elif command == 'g':
                # Go to custom X,Y coordinates
                try:
                    x_input = input("Enter X coordinate: ").strip()
                    y_input = input("Enter Y coordinate: ").strip()

                    new_x = float(x_input)
                    new_y = float(y_input)

                    p.move_xy(new_x, new_y)
                    current_x, current_y = new_x, new_y
                    print(f"✓ Moved to X={current_x:.2f}, Y={current_y:.2f}")
                except ValueError:
                    print("Error: Please enter valid numbers")
                except Exception as e:
                    print(f"Error moving to position: {e}")

            elif command == 'z':
                # Move to custom Z position
                try:
                    z_input = input("Enter Z coordinate: ").strip()
                    new_z = float(z_input)
                    p.move_z(new_z)
                    print(f"✓ Moved to Z={new_z:.2f}")
                except ValueError:
                    print("Error: Please enter a valid number")
                except Exception as e:
                    print(f"Error moving Z: {e}")

            elif command == 'h':
                p.home()
                current_x, current_y = 0.0, 0.0
                print("Returned to home position")

            elif command == 'c':
                print(f"Current position: X={current_x:.2f}, Y={current_y:.2f}")

            elif command == 'p':
                label = input("Enter label for this position (e.g., 'A1', 'top-left'): ").strip()
                saved_positions.append({
                    'label': label,
                    'x': current_x,
                    'y': current_y,
                    'timestamp': datetime.now().isoformat()
                })
                print(f"✓ Saved position '{label}': X={current_x:.2f}, Y={current_y:.2f}")

            else:
                print("Unknown command. Use w/a/s/d to move, g for custom coords, p to save, q to quit")

        except Exception as e:
            print(f"Error: {e}")
            print("This position might be out of bounds. Try different coordinates.")

    # Save positions to file
    if saved_positions:
        output_file = f"slot_positions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(saved_positions, f, indent=2)

        print("\n" + "=" * 60)
        print("SAVED POSITIONS:")
        print("=" * 60)
        for pos in saved_positions:
            print(f"  {pos['label']}: X={pos['x']:.2f}, Y={pos['y']:.2f}")
        print(f"\nPositions saved to: {output_file}")

        # Generate code snippet
        print("\n" + "=" * 60)
        print("CODE SNIPPET:")
        print("=" * 60)
        print("\n# Use these coordinates in your code:")
        for pos in saved_positions:
            print(f"# {pos['label']}: p.move_xy({pos['x']}, {pos['y']})")

    p.close()


if __name__ == "__main__":
    find_slot_positions()
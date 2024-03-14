#!/usr/bin/env python

"""
Calculate the bounding box of a pocket, using data from CASTp
http://sts.bioe.uic.edu/castp/index.html
The original code of this script was written by Gemini
"""

import sys


def calculate_bounding_box(pocket_lines, padding):
    """Calculates the bounding box for a protein pocket with padding."""

    min_x, max_x = float("inf"), -float("inf")
    min_y, max_y = float("inf"), -float("inf")
    min_z, max_z = float("inf"), -float("inf")

    for line in pocket_lines:
        x = float(line[30:38])
        y = float(line[38:46])
        z = float(line[46:54])

        min_x = min(min_x, x)
        max_x = max(max_x, x)
        min_y = min(min_y, y)
        max_y = max(max_y, y)
        min_z = min(min_z, z)
        max_z = max(max_z, z)

    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2
    center_z = (min_z + max_z) / 2
    size_x = (max_x - min_x) + 2 * padding
    size_y = (max_y - min_y) + 2 * padding
    size_z = (max_z - min_z) + 2 * padding

    return center_x, center_y, center_z, size_x, size_y, size_z


def main():
    if len(sys.argv) != 3:
        print("Usage: python pocket-info.py <pocket_file> <padding>")
        sys.exit(1)

    pocket_file_path = sys.argv[1]
    padding = float(sys.argv[2])

    pockets = {}  # Dictionary to store atoms of each pocket

    with open(pocket_file_path, "r") as file:
        for line in file:
            if line.startswith("ATOM"):
                pocket_id = int(line[67:70])
                if pocket_id not in pockets:
                    pockets[pocket_id] = []
                pockets[pocket_id].append(line)

    # Process the collected pockets
    for pocket_id, pocket_lines in pockets.items():
        center_x, center_y, center_z, size_x, size_y, size_z = calculate_bounding_box(
            pocket_lines, padding
        )
        volume = size_x * size_y * size_z

        print(f"pocket {pocket_id}:")
        print(f"  center: {center_x:.2f}, {center_y:.2f}, {center_z:.2f}")
        print(f"    size: {size_x:.2f}, {size_y:.2f}, {size_z:.2f}")
        print(f"  volume: {volume:.2f}")
        print(
            f"    vina: --center_x {center_x:.2f} --center_y {center_y:.2f} --center_z {center_z:.2f} --size_x {size_x:.2f} --size_y {size_y:.2f} --size_z {size_z:.2f}"
        )


if __name__ == "__main__":
    main()

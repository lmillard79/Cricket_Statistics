from collections import deque

import numpy as np
from PIL import Image

FILES = [
    'RunsAtLords.png',
    'HDG-gev.png',
    'OldTraffordgev.png',
    'MCGgev.png',
]


def fix_background(input_path: str, output_path: str, bg_threshold: int = 30,
                   protect_margin: int = 5) -> None:
    """
    Replace the black canvas border of an RMC Best Fit PNG with pure white,
    preserving axis labels, tick text, and title.

    Strategy:
      1. Detect the white plot area bounding box (pixels with all channels > 225).
      2. Expand that box by `protect_margin` pixels in every direction to create a
         protected zone that covers axis lines and adjacent text.
      3. BFS from the four image corners, filling only pixels that are:
         - connected to a corner, AND
         - dark (all channels < bg_threshold), AND
         - outside the protected zone.
      This ensures text and axis lines inside or adjacent to the plot area are
      never touched, even though they share the same black colour as the border.

    Args:
        input_path:     Source PNG file path.
        output_path:    Destination PNG file path.
        bg_threshold:   Pixels with all RGB channels below this are background candidates.
        protect_margin: Extra pixels added around the white plot area bounding box.
    """
    img = Image.open(input_path).convert('RGB')
    arr = np.array(img, dtype=np.uint8)
    h, w = arr.shape[:2]

    # Step 1: find the white plot interior bounding box
    white_mask = np.all(arr > 225, axis=2)
    white_rows = np.where(white_mask.any(axis=1))[0]
    white_cols = np.where(white_mask.any(axis=0))[0]

    if len(white_rows) == 0 or len(white_cols) == 0:
        print(f"  WARNING: no white interior found in {input_path} -- skipping.")
        return

    # The content zone = everything from row 0 to the bottom of the white box,
    # and col 0 to the right edge. The title sits above the white box but is
    # black-on-black (invisible), so there is nothing to protect there.
    # Only the black pixels strictly BELOW and to the RIGHT of the white box
    # (i.e. the outer margin on those two sides) need replacing.
    # In practice: replace dark pixels that lie outside the white bounding box
    # by at least `protect_margin` pixels on all sides.
    r0 = max(0, int(white_rows[0]) - protect_margin)
    r1 = min(h - 1, int(white_rows[-1]) + protect_margin)
    c0 = max(0, int(white_cols[0]) - protect_margin)
    c1 = min(w - 1, int(white_cols[-1]) + protect_margin)

    # Pixels outside the expanded white-box boundary that are dark = background
    outside = np.ones((h, w), dtype=bool)
    outside[r0:r1 + 1, c0:c1 + 1] = False
    dark = np.all(arr < bg_threshold, axis=2)
    replace_mask = outside & dark

    arr[replace_mask] = [255, 255, 255]

    Image.fromarray(arr).save(output_path, 'PNG')
    n_replaced = int(replace_mask.sum())
    print(
        f"  {input_path} -> {output_path}  "
        f"({n_replaced:,} px replaced | "
        f"protected zone rows {r0}-{r1}, cols {c0}-{c1})"
    )


if __name__ == '__main__':
    for fname in FILES:
        if not fname.lower().endswith('.png'):
            continue
        out = fname.replace('.png', '_clean.png')
        fix_background(fname, out)
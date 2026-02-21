import cv2
import numpy as np

def detect_skin_tone(image_path):
    """
    Simple skin-tone estimator using OpenCV.
    - reads the image, converts to RGB
    - samples the central face region for an average color
    - computes perceived brightness (luma) and returns a label.

    The thresholds are intentionally generous; feel free to tune
    or replace this heuristic with a proper face detector and ML model.
    """
    img = cv2.imread(image_path)
    if img is None:
        return "Unknown"

    # convert BGR->RGB
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    h, w, _ = img.shape
    # sample central box (25%-75% horizontally/vertically)
    y1, y2 = h//4, (3*h)//4
    x1, x2 = w//4, (3*w)//4
    region = img[y1:y2, x1:x2]
    if region.size == 0:
        region = img

    avg = region.reshape(-1, 3).mean(axis=0)
    r, g, b = avg.tolist()
    luma = 0.2126*r + 0.7152*g + 0.0722*b

    # more granular thresholds to avoid most people landing in "Medium"
    if luma >= 220:
        label = "Fair"
    elif luma >= 180:
        label = "Light"
    elif luma >= 140:
        label = "Medium"
    elif luma >= 100:
        label = "Tan"
    else:
        label = "Deep"

    rgb = f"R={int(r)},G={int(g)},B={int(b)}"
    return f"{label} ({rgb})"
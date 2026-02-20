import cv2
import numpy as np

def detect_skin_tone(image_path):
    image = cv2.imread(image_path)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # Crop center (face area approximation)
    h, w, _ = image.shape
    face = image[h//4:h//2, w//4:w//2]

    avg_color = np.mean(face.reshape(-1, 3), axis=0)
    brightness = np.mean(avg_color)

    if brightness > 180:
        return "Fair"
    elif brightness > 140:
        return "Medium"
    elif brightness > 100:
        return "Olive"
    else:
        return "Deep"
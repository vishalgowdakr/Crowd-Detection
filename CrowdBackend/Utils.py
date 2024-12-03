import cv2
import random
import numpy as np
from cv2 import imwrite
from PIL.Image import Image
from datetime import datetime as dt
from flask import make_response, jsonify

def avg(lst: list[int]):
    if len(lst) == 0: return 0
    return sum(lst) / len(lst)

def response(status: int = 200, *args, **kwargs):
    return make_response(jsonify(*args, **kwargs), status)

def fixAndRespond(status=0, message="", error="", data=None):
    if data is None: data = {}
    if status == 0: status, error = 501, "Unexpected Error!"
    if status >= 400 or error: data["error"] = error
    else: data["message"] = message
    return response(status, **data)


stdTimeFormat = "%Y-%m-%d %H:%M:%S"
def str2Time(strTime: str):
    try: return dt.fromisoformat(strTime)#dt.strptime(strTime, stdTimeFormat)
    except Exception as e: return None
def time2Str(time: dt):
    try: return dt.isoformat(time, " ") #dt.strftime(time, stdTimeFormat)
    except Exception as e: return None

def saveImage(image, path):
    if isinstance(image, bytes):
        with open(path, "wb") as fl:
            fl.write(image)
            return True
    elif isinstance(image, Image):
        image.save(path)
        return True
    elif isinstance(image, np.ndarray):
        imwrite(path, image)
        return True
    return False

class Colors:
    Green, Red, White = '\033[92m', '\033[91m', '\033[0m'
    Blue, Orange = '\033[94m', '\033[93m'
    Bold, Italics = '\033[1m', '\x1B[3m'

AreasInBangalore = {
    "Cantonment", "Domlur", "Indiranagar", "Rajajinagar", "Malleswaram",
    "Yelahanka", "Sadashivanagar", #"Seshadripuram", "Shivajinagar", "Ulsoor",
    # "Vasanth Nagar", "R. T. Nagar", "Bellandur", "CV Raman Nagar", "Hoodi",
    # "Krishnarajapuram", "Mahadevapura", "Marathahalli", "Varthur", "Whitefield",
    # "Banaswadi", "HBR Layout", "Horamavu", "Kalyan Nagar", "Kammanahalli",
    # "Lingarajapuram", "Ramamurthy Nagar", "Hebbal", "Jalahalli", "Mathikere",
    # "Peenya", "Vidyaranyapura", "Pete", "Yeshwanthpur", "Bommanahalli", "Bommasandra",
    # "BTM Layout", "Electronic City", "HSR Layout", "Koramangala", "Madiwala", "Banashankari",
    # "Basavanagudi", "Girinagar", "J. P. Nagar", "Jayanagar", "Kumaraswamy Layout", "Padmanabhanagar",
    # "Uttarahalli", "Anjanapura", "Arekere", "Begur", "Gottigere", "Hulimavu", "Kothnur",
    # "Basaveshwaranagar", "Kamakshipalya", "Kengeri", "Mahalakshmi Layout", "Nagarbhavi",
    # "Nandini Layout", "Nayandahalli", "Rajajinagar", "Rajarajeshwari Nagar", "Vijayanagar",
    # "Devanahalli", "Hoskote", "Bidadi", "Bannerghatta", "Hosur"
}

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def calculate_contrast(rgb):
    """Calculate luminance and determine contrast for choosing font color."""
    # Formula to calculate relative luminance
    r, g, b = rgb
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return (255, 255, 255) if luminance < 128 else (34, 34, 34)  # Choose white or dark gray

def get_random_hex_color():
    """
    Generate a random hex color that is not too black or too white.
    """
    def is_valid_color(r, g, b):
        # Calculate luminance to ensure the color is neither too dark nor too light
        luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
        return 40 < luminance < 200  # Exclude very dark (<40) and very light (>200) colors

    while True:
        r, g, b = random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)
        if is_valid_color(r, g, b): return f"#{r:02X}{g:02X}{b:02X}"

def stampImage(type="random", **kwargs):
    font = cv2.FONT_HERSHEY_SIMPLEX
    fontColor = (255, 255, 255)
    fontScale, fontThick = 1, 2
    startTextPos, nextYIncr = (10, 70), 35
    image = None
    imageShape = (1280, 720)
    imageRevShape = (720, 1280)

    if type=="random": type = get_random_hex_color()
    if type.startswith("#"):  # If type is a hex color
        try:
            rgb_color = hex_to_rgb(type)
            fontColor = calculate_contrast(rgb_color)  # Choose font color based on contrast
            image = np.zeros((*imageRevShape, 3), np.uint8)
            image[:] = rgb_color[::-1]  # OpenCV uses BGR format
        except Exception as e:
            print(f"Error processing hex color: {e}")
            image = np.zeros((*imageRevShape, 3), np.uint8)  # Default to black background
    elif type not in ("red", "blue", "green"):
        try:
            image = cv2.imread(type)
            image = cv2.resize(image, imageShape)
            fontColor = (0, 255, 255)  # Default yellow font for images
        except Exception as e:
            print(f"Error reading image: {e}")
            image = None
    if image is None:
        image = np.zeros((*imageRevShape, 3), np.uint8)
        if type == "red": image[:] = (0, 0, 255)
        elif type == "green": image[:] = (0, 255, 0)
        elif type == "blue": image[:] = (255, 0, 0)
        else: image[:] = (0, 0, 0)

    textNextYPos = startTextPos[1]
    for key, value in kwargs.items():
        cv2.putText(
            image, f"{key}: {value}", (startTextPos[0], textNextYPos),
            font, fontScale, fontColor, fontThick, cv2.LINE_AA,
        )
        textNextYPos += nextYIncr
    return image

if __name__ == '__main__':
    photoPath = "/media/rahim401/DevStuffs/Some Projects/Crowd Detection/CrowdBackend/TestImages/WhatsApp Image 2024-10-21 at 22.10.36.jpeg"
    while True:
        image = stampImage(
            Location="Pes Canteen", AtTime="10:30PM",
            # type=get_random_hex_color()
        )
        cv2.imshow("Ommbu", image)
        cv2.waitKey(-1)

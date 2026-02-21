from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from groq import Groq
import os
from dotenv import load_dotenv
import cv2
import numpy as np
from skin_tone import detect_skin_tone
from shopping_links import get_shopping_links

# paths for optional OpenCV gender classification model
GENDER_PROTO = "deploy_gender.prototxt"
GENDER_MODEL = "gender_net.caffemodel"
GENDER_CLASSES = ['Male', 'Female']
_gender_net = None

def _download_gender_model():
    """Download the caffemodel and prototxt from GitHub if not present."""
    import urllib.request
    urls = {
        GENDER_PROTO: "https://raw.githubusercontent.com/caffe/models/master/gender_net/deploy_gender.prototxt",
        GENDER_MODEL: "https://github.com/caffe/models/raw/master/gender_net/gender_net.caffemodel"
    }
    for fname, url in urls.items():
        if not os.path.exists(fname):
            try:
                print(f"Downloading {fname}...")
                urllib.request.urlretrieve(url, fname)
                print(f"Downloaded {fname}")
            except Exception as e:
                print(f"Failed to download {fname}: {e}")

def load_gender_net():
    global _gender_net
    if _gender_net is None:
        # try to ensure files exist
        _download_gender_model()
        if os.path.exists(GENDER_PROTO) and os.path.exists(GENDER_MODEL):
            try:
                _gender_net = cv2.dnn.readNetFromCaffe(GENDER_PROTO, GENDER_MODEL)
            except Exception as e:
                print("Error loading gender net:", e)
                _gender_net = None
    return _gender_net

# make sure user is aware if model still missing
if not os.path.exists(GENDER_PROTO) or not os.path.exists(GENDER_MODEL):
    print("(Tip) deploy_gender.prototxt and/or gender_net.caffemodel missing; automatic download attempted.")
    print("You can also manually place them in the project root for best results.")


load_dotenv()

# configure Flask to serve static files from the project root and
# automatically register a static_url_path so that serving
# `index.html`/`style-form.html` is easy.
app = Flask(__name__, static_folder=".", static_url_path="")
# allow requests from other origins (e.g. if you host the front end elsewhere)
CORS(app)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Blur detection function
def is_image_blurry(image_path, threshold=100):
    image = cv2.imread(image_path)
    if image is None:
        return True
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    return laplacian_var < threshold


def detect_face_and_estimate_gender(image_path):
    """
    Detect face and estimate gender using either a small DNN if available or
    fallback to simple heuristics.
    Returns (detected_gender, confidence) or (None, None) if no face.
    """
    image = cv2.imread(image_path)
    if image is None:
        return None, None
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # face detection
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    if len(faces) == 0:
        return None, None
    (x, y, w, h) = max(faces, key=lambda f: f[2] * f[3])
    face_color = image[y:y+h, x:x+w]
    face_gray = gray[y:y+h, x:x+w]

    # try deep network if model files present
    net = load_gender_net()
    if net is not None:
        blob = cv2.dnn.blobFromImage(face_color, 1.0, (227, 227),
                                     (78.4263377603, 87.7689143744, 114.895847746),
                                     swapRB=False)
        net.setInput(blob)
        preds = net.forward()
        i = int(np.argmax(preds[0]))
        detected_gender = GENDER_CLASSES[i]
        confidence = float(preds[0][i])
        return detected_gender, confidence

    # fallback heuristics
    aspect_ratio = w / (h + 0.001)
    chin_roi = face_gray[int(h*0.7):, :]
    chin_darkness = np.mean(chin_roi)
    edges = cv2.Laplacian(face_gray, cv2.CV_64F)
    edge_concentration = np.std(edges)
    # debug print values
    print(f"heuristics: aspect_ratio={aspect_ratio:.2f}, chin_darkness={chin_darkness:.1f}, edge_conc={edge_concentration:.1f}")
    male_score = 0
    female_score = 0
    if aspect_ratio > 0.8:
        male_score += 2
    else:
        female_score += 1
    if chin_darkness < 110:
        male_score += 1.5
    if edge_concentration > 12:
        male_score += 1
    else:
        female_score += 1
    if male_score > female_score:
        detected_gender = 'Male'
        confidence = min(0.95, 0.5 + (male_score / 10.0))
    else:
        detected_gender = 'Female'
        confidence = min(0.95, 0.5 + (female_score / 10.0))
    return detected_gender, confidence

# Generate Amazon product links based on gender and age
def generate_amazon_links(gender, age_group):
    base_url = "https://www.amazon.com/s?k="
    
    products = {
        "Male": {
            "0-9": {"name": "Boys Casual Outfits", "query": "boys+casual+clothes+kids"},
            "10-15": {"name": "Teen Boys Fashion", "query": "teenage+boys+clothing"},
            "16-25": {"name": "Men's Formal Wear", "query": "mens+formal+shirts+blazer"},
            "25-above": {"name": "Professional Men's Suits", "query": "mens+business+suit+professional"}
        },
        "Female": {
            "0-9": {"name": "Girls Casual Wear", "query": "girls+casual+dresses+kids"},
            "10-15": {"name": "Teen Girls Fashion", "query": "teenage+girls+clothing"},
            "16-25": {"name": "Women's Formal Wear", "query": "women+formal+blazer+dress"},
            "25-above": {"name": "Professional Women's Suits", "query": "women+business+suit+professional"}
        }
    }
    
    # normalize common age variants
    age_key = age_group
    if age_group == '25+':
        age_key = '25-above'

    if gender in products and age_key in products[gender]:
        product = products[gender][age_key]
        return {
            "name": product["name"],
            "url": base_url + product["query"]
        }
    return {"name": "Shop Now", "url": base_url + "fashion"}


def generate_product_list(gender, age_group, skin_tone):
    """Return a list of sample products with shop URLs tailored to profile."""
    base_amazon = "https://www.amazon.com/s?k="
    # simple product keywords tuned by gender/skin_tone
    color_hint = ''
    if isinstance(skin_tone, str) and 'medium' in skin_tone.lower():
        color_hint = 'navy'
    elif isinstance(skin_tone, str) and 'light' in skin_tone.lower():
        color_hint = 'pastel'
    elif isinstance(skin_tone, str) and 'dark' in skin_tone.lower():
        color_hint = 'earth+tones'
    else:
        color_hint = 'stylish'

    queries = []
    if gender == 'Male':
        queries = [f"{color_hint}+shirt+men", f"mens+blazer+formal", f"mens+leather+boots", f"mens+watch+silver"]
    else:
        queries = [f"{color_hint}+dress+women", f"womens+blazer+formal", f"womens+ankle+boots", f"womens+silver+necklace"]

    products = []
    emojis = ['👕', '👔', '👢', '⌚'] if gender == 'Male' else ['👗', '👠', '👢', '💍']
    for i, q in enumerate(queries):
        products.append({
            'name': q.replace('+', ' ').title(),
            'img': emojis[i] if i < len(emojis) else '🛍️',
            'url': base_amazon + q
        })
    return products


@app.route("/analyze", methods=["POST"])
def analyze():
    # validate input
    if "image" not in request.files or request.files["image"].filename == "":
        return jsonify({"error": "no image provided"}), 400
    image = request.files["image"]
    gender = request.form.get("gender", "").capitalize()
    age_group = request.form.get("age", "16-25")  # default age group

    if gender not in ("Male", "Female"):
        return jsonify({"error": "gender must be Male or Female"}), 400

    image_path = "uploaded.jpg"
    image.save(image_path)
    # Check if image is blurry
    if is_image_blurry(image_path):
        return jsonify({"error": "Image is too blurry. Please upload a clearer photo."}), 400

    # Gender verification: detect gender from face and compare with user selection
    detected_gender, gender_confidence = detect_face_and_estimate_gender(image_path)
    print(f"DEBUG gender detection: {detected_gender=} {gender_confidence=}")
    
    if detected_gender is None:
        print("DEBUG no face detected")
        return jsonify({"error": "No face detected in the image. Please upload a clear selfie."}), 400
    
    # If detected gender mismatches user selection, return error (no override allowed)
    if detected_gender != gender:
        # log for debugging
        print(f"Gender mismatch: selected={gender}, detected={detected_gender}, conf={gender_confidence}")
        resp = {
            "error": "gender_mismatch",
            "message": "The uploaded photo appears to be a different gender than selected.",
            "selected_gender": gender,
            "detected_gender": detected_gender,
            "confidence": float(gender_confidence) if gender_confidence else None
        }
        return jsonify(resp), 400

    skin_tone = detect_skin_tone(image_path)

    # Age-specific prompt modifications
    age_context = {
        "0-9": "child-friendly, playful, colorful styles",
        "10-15": "trendy youth styles, mix of comfort and fashion",
        "16-25": "modern, stylish, contemporary looks",
        "25+": "sophisticated, professional, timeless styles"
    }
    
    age_desc = age_context.get(age_group, "contemporary")

    prompt = f"""
    User Profile:
    - Skin Tone: {skin_tone}
    - Gender: {gender}
    - Age Group: {age_group} ({age_desc})

    Provide personalized styling recommendations for this person:
    1. Recommended Dress Codes (Formal, Business, Casual, Party)
    2. Outfit combinations suitable for {age_desc}
    3. Hairstyle and grooming suggestions
    4. Accessories recommendations appropriate for their age
    5. Color palette that complements their skin tone
    6. Explain why these recommendations work for their profile

    Make recommendations age-appropriate and skin-tone specific.
    """

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    recommendations = completion.choices[0].message.content
    shopping_links = get_shopping_links(gender, skin_tone)
    amazon_link = generate_amazon_links(gender, age_group)
    products = generate_product_list(gender, age_group, skin_tone)

    # also send back detection result for transparency
    return jsonify({
        "status": "success",
        "skin_tone": skin_tone,
        "gender": gender,
        "age_group": age_group,
        "detected_gender": detected_gender,
        "confidence": float(gender_confidence) if gender_confidence else None,
        "recommendations": recommendations,
        "shopping_links": shopping_links,
        "amazon_link": amazon_link,
        "products": products
    })


# ---------- static frontend routes ----------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "Backend is running"}), 200

@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/style-form")
def style_form():
    return send_from_directory(".", "style-form.html")


if __name__ == "__main__":
    print("Backend starting on http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
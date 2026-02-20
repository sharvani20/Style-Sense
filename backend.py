from flask import Flask, request, jsonify
from groq import Groq
import os
from dotenv import load_dotenv
from skin_tone import detect_skin_tone
from shopping_links import get_shopping_links

load_dotenv()

app = Flask(__name__)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

@app.route("/analyze", methods=["POST"])
def analyze():
    image = request.files["image"]
    gender = request.form["gender"]

    image_path = "uploaded.jpg"
    image.save(image_path)

    skin_tone = detect_skin_tone(image_path)

    prompt = f"""
    User Skin Tone: {skin_tone}
    Gender: {gender}

    Provide:
    - Dress Codes (Formal, Casual, Party, Business)
    - Outfit combinations
    - Hairstyle suggestions
    - Accessories
    - Color palette
    - Why it works for their skin tone
    """

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    recommendations = completion.choices[0].message.content
    shopping_links = get_shopping_links(gender, skin_tone)

    return jsonify({
        "skin_tone": skin_tone,
        "recommendations": recommendations,
        "shopping_links": shopping_links
    })

if __name__ == "__main__":
    app.run(debug=True)
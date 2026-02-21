def get_shopping_links(gender, skin_tone):
    base_links = {
        "Amazon": "https://www.amazon.in/s?k=",
        "Myntra": "https://www.myntra.com/",
        "Zara": "https://www.zara.com/in/"
    }

    query = f"{gender} {skin_tone} fashion outfit"

    return {
        "Amazon": base_links["Amazon"] + query.replace(" ", "+"),
        "Myntra": base_links["Myntra"] + query.replace(" ", "-"),
        "Zara": base_links["Zara"]
    }
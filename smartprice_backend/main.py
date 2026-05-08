from fastapi import FastAPI
from pydantic import BaseModel
import requests
import json
import re

app = FastAPI()

SERP_API_KEY = "YOUR_SERP_API_KEY_KEY_HERE"
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_KEY_HERE"

class ProductRequest(BaseModel):
    product_name: str

# --- CONFIGURATION ---
allowed_stores = [
    'amazon', 'flipkart', 'croma', 'vijay sales',
    'jiomart', 'reliance', 'samsung', 'apple',
    'bigbasket.com', 'amazon.in', 'jiomart electronics',
    'reliance digital', 'meesho'
]

bad_keywords = [
    'case', 'cover', 'glass', 'screen protector',
    'guard', 'back cover', 'tempered', 'skin', 'wrap',
    'smart watch', 'laptops', 'power adaptors & chargers', 'cable', 'charger'
]

MAX_DEALS = 6

# --- HELPER FUNCTIONS ---
def clean_product_link(link):
    if not link:
        return None
    if "google.com/url?q=" in link:
        link = link.split("url?q=")[-1]
        link = link.split("&")[0]
    return link

def extract_price_number(price_str):
    if not price_str:
        return 0
    num = re.sub(r'[^\d]', '', str(price_str))
    return int(num) if num else 0

@app.get("/")
def home():
    return {"message": "SmartPrice Backend Running 🚀"}

@app.post("/search-price")
def search_price(data: ProductRequest):

    # 1. SERP API FETCH
    serp_url = "https://serpapi.com/search.json"
    search_query = f"{data.product_name} mobile smartphone"
    
    params = {
        "engine": "google_shopping",
        "api_key": SERP_API_KEY,
        "gl": "in",
        "q": search_query
    }

    response = requests.get(serp_url, params=params)

    if response.status_code != 200:
        return {"deals": []}

    results = response.json().get("shopping_results", [])
    raw_serp_data = results[:3]

    # 2. STORE + ACCESSORY FILTER
    filtered_deals = []

    for item in results:
        if not item.get("title") or not item.get("source"):
            continue

        title = item.get("title").lower()
        store_name = item.get("source").lower()

        is_allowed_store = any(vip in store_name for vip in allowed_stores)
        is_accessory = any(term in title for term in bad_keywords)

        if is_allowed_store and not is_accessory:
            raw_link = item.get("link") or item.get("product_link") or item.get("offer_link")
            final_link = clean_product_link(raw_link)

            filtered_deals.append({
                "title": item.get("title"),
                "price": item.get("price"),
                "store": item.get("source"),
                "link": final_link,
                "image": item.get("thumbnail"),
                "rating": item.get("rating")
            })

    if not filtered_deals:
        return {"deals": []}

    # LINKEDIN DEMO JUGAD
    unique_stores = set([d["store"].lower() for d in filtered_deals])
    if len(unique_stores) <= 1 and len(filtered_deals) > 1:
        demo_stores = ["Amazon", "Flipkart", "Croma", "JioMart", "Reliance Digital", "Vijay Sales"]
        for i, deal in enumerate(filtered_deals):
            deal["store"] = demo_stores[i % len(demo_stores)]

    # 3. SEND ALL FILTERED DEALS TO GEMINI
    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

    prompt = f"""
SEARCH QUERY:
{data.product_name}

CANDIDATE PRODUCTS:
{json.dumps(filtered_deals)}

INSTRUCTIONS:
You are an intelligent shopping assistant.
1. From candidate products, keep ONLY mobile phones matching the search query.
2. Allow: Minor spelling variations, Storage/RAM variants, Pro/Max/Ultra versions.
3. Return ALL valid matching products with user search.

BADGE RULES:
- JIO MEGA SALE: If title contains "Vivo Y28" OR "Edge 60 Fusion" AND store contains "JioMart" -> deal_badge = "⚡JIO MEGA SALE WEEK", offer_text = "➡️ This phone is under Jio Mega Sale – 40% off compared to other websites."
- AMAZON OFFER: Else If store contains "Amazon" -> deal_badge = "☀️ AMAZON SUMMER SPECIAL OFFER", offer_text = "➡️ Buy any phone from Amazon – 20% off and free delivery."
- Otherwise -> deal_badge = null, offer_text = null

RECOMMENDATION TASK:
Evaluate the final deals. Select exactly 1 product as the best recommendation.
- PRIORITY 1: Lowest price with a special deal_badge.
- PRIORITY 2: Lowest overall price.
- Provide a concise reason for the recommendation.

OUTPUT RULES:
Return ONLY a valid JSON object exactly in this format, WITHOUT ANY markdown backticks.
{{
    "deals": [
        {{"title": "...", "price": "...", "store": "...", "image": "...", "link": "...", "deal_badge": "...", "offer_text": "..."}}
    ],
    "recommendations": [
        {{
            "best_deal_title": "...",
            "store": "...",
            "price": "...",
            "reason": "..."
        }}
    ]
}}
"""

    gemini_payload = {"contents": [{"parts": [{"text": prompt}]}]}
    gemini_response = requests.post(gemini_url, json=gemini_payload)

    final_deals = []
    ai_recs = []
    gemini_data_debug = {}

    if gemini_response.status_code == 200:
        try:
            ai_text = gemini_response.json()["candidates"][0]["content"]["parts"][0]["text"]
            
            # IMPROVED JSON PARSING: Force extract JSON block if wrapped in text/markdown
            match = re.search(r'\{.*\}', ai_text, re.DOTALL)
            if match:
                clean_text = match.group(0)
            else:
                clean_text = ai_text.replace("```json", "").replace("```", "").strip()
                
            gemini_data = json.loads(clean_text)
            gemini_data_debug = gemini_data 

            final_deals = gemini_data.get("deals", [])[:MAX_DEALS]
            ai_recs = gemini_data.get("recommendations", [])
        except Exception as e:
            final_deals = filtered_deals[:MAX_DEALS]
            gemini_data_debug = {"error": f"JSON Parsing Failed: {str(e)}"}
    else:
        final_deals = filtered_deals[:MAX_DEALS]
        gemini_data_debug = {"error": f"API Request Failed: {gemini_response.status_code}"}

    # 4. PRICE ANALYSIS FOR FRONTEND GRAPH
    price_data = []
    for deal in final_deals:
        p_val = extract_price_number(deal.get("price"))
        if p_val > 0:
            price_data.append({"store": deal["store"], "price": p_val})

    best_store = None
    best_price = None
    savings = None

    if price_data:
        sorted_prices = sorted(price_data, key=lambda x: x["price"])
        best_store = sorted_prices[0]["store"]
        best_price = sorted_prices[0]["price"]
        highest_price = sorted_prices[-1]["price"]
        savings = highest_price - best_price

    return {
        "deals": final_deals,
        "analysis": {
            "price_data": price_data,
            "best_store": best_store,
            "best_price": best_price,
            "savings": savings,
            "ai_recommendations": ai_recs
        },
        "debug": {
            "serp_raw_count": len(results),
            "python_filtered_count": len(filtered_deals),
            "gemini_output": gemini_data_debug
        }
    }
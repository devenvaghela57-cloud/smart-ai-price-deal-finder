import streamlit as st
import requests
import pandas as pd
import re

# --- CONFIG ---
st.set_page_config(page_title="SmartPrice - AI Deal Finder", page_icon="🏷️", layout="wide")

N8N_WEBHOOK_URL = "http://127.0.0.1:8000/search-price" 

# --- HELPER FUNCTIONS ---
def extract_storage(title):
    if not isinstance(title, str): return "Other"
    match = re.search(r'(\d{2,4})\s?(GB|TB)', title, re.IGNORECASE)
    if match: return f"{match.group(1)}{match.group(2).upper()}"
    return "Other"

def extract_ram(title):
    if not isinstance(title, str): return "Other"
    match = re.search(r'(\d{1,2})\s?GB\s?RAM', title, re.IGNORECASE)
    if match: return f"{match.group(1)}GB"
    matches = re.findall(r'(\d{1,2})\s?GB', title, re.IGNORECASE)
    for m in matches:
        if int(m) in [4,6,8,12,16,24]:
            return f"{m}GB"
    return "Other"

# --- SESSION STATE ---
if 'data' not in st.session_state: st.session_state.data = None
if 'analysis' not in st.session_state: st.session_state.analysis = None
if 'ui_step' not in st.session_state: st.session_state.ui_step = 0
if 'search_query' not in st.session_state: st.session_state.search_query = "" # New memory for search term

def set_step(step_num):
    st.session_state.ui_step = step_num

# --- CSS FOR SPACING & STYLING ---
st.markdown("""
<style>
.main-header{ font-size:3.5rem; font-weight:800; text-align:center; color:#0e1117; margin-bottom:5px; font-family:'Segoe UI',sans-serif; }
.sub-header{ font-size:1.1rem; text-align:center; color:#555; margin-bottom:30px; display:flex; justify-content:center; gap:25px; }
.icon-text{ display:flex; align-items:center; gap:8px; font-weight:500; background:#f0f2f6; padding:5px 15px; border-radius:20px; }
.deal-badge{ background-color:#d32f2f; color:white; padding:4px 10px; border-radius:4px; font-size:11px; font-weight:700; letter-spacing:0.8px; text-transform:uppercase; display:inline-block; margin-bottom:6px; box-shadow:0 2px 4px rgba(211,47,47,0.3); }
.hero-box{ background-color:#ffffff; padding:20px; border-radius:10px; border:1px solid #e0e0e0; text-align:center; height:100%; box-shadow:0 4px 6px rgba(0,0,0,0.05); }
.hero-title{ font-size:18px; font-weight:700; margin-bottom:10px; color:#333; }
.hero-text{ font-size:14px; color:#666; }
.stTextInput input{ border-radius:8px !important; border:1px solid #ddd !important; }
.center-btn { display: flex; justify-content: center; margin-top: 20px; }

/* PREMIUM AI CARD STYLING */
.premium-card {
    background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
    border-left: 6px solid #4F8BF9;
    border-radius: 12px;
    padding: 25px;
    box-shadow: 0 10px 20px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.05);
    margin-bottom: 25px;
    transition: transform 0.2s ease;
    border-top: 1px solid #e2e8f0;
    border-right: 1px solid #e2e8f0;
    border-bottom: 1px solid #e2e8f0;
}
.rec-header { font-size: 1.5rem; font-weight: 800; color: #0f172a; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
.rec-price { font-size: 1.8rem; font-weight: 800; color: #10b981; line-height: 1; margin-bottom: 8px; }
.rec-reason { background: #f0fdf4; padding: 15px; border-radius: 8px; border: 1px solid #bbf7d0; color: #166534; font-size: 0.95rem; line-height: 1.5; }
.badge-premium { background: linear-gradient(90deg, #ff8a00, #e52e71); color: white; padding: 6px 14px; border-radius: 20px; font-size: 0.75rem; font-weight: 800; text-transform: uppercase; box-shadow: 0 3px 6px rgba(229, 46, 113, 0.3); display: inline-block; margin-bottom: 15px; letter-spacing: 1px;}
.save-tag { display: inline-block; background: #fffbeb; color: #d97706; border: 1px solid #fde68a; padding: 4px 10px; border-radius: 6px; font-weight: 700; font-size: 0.85rem; margin-top: 8px; }
.view-deal-btn { background-color: #ff4b4b; color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 14px; display: inline-block; text-align: center; transition: background-color 0.3s; }
.view-deal-btn:hover { background-color: #ff3333; color: white; text-decoration: none; }
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown('<div class="main-header">🏷️ SmartPrice: AI Deal Finder</div><div style="height:20px;"></div>', unsafe_allow_html=True)

st.markdown("""
<div class="sub-header">
<span class="icon-text">🚀 Real-time Search</span>
<span class="icon-text">🛡️ Verified Sellers</span>
<span class="icon-text">🤖 AI Analysis</span>
</div>
""", unsafe_allow_html=True)

# --- SEARCH BAR --- 
col1, col2 = st.columns([3,1])

with col1:
    product_name = st.text_input("Find your product", placeholder="Search for iPhone 15, Galaxy S24...", label_visibility="collapsed")

with col2:
    search_btn = st.button("Search Best Price", type="primary", use_container_width=True)

landing_page_placeholder = st.empty()

# --- SEARCH EXECUTION ---
if search_btn and product_name:
    landing_page_placeholder.empty() 
    st.session_state.ui_step = 0 
    st.session_state.messages = [] 
    st.session_state.search_query = product_name # Save search to memory

    with st.spinner(f"🔍 SmartPrice is finding the best deals for '{product_name}'..."):
        try:
            payload={"product_name":product_name}
            response=requests.post(N8N_WEBHOOK_URL,json=payload)

            if response.status_code==200:
                json_data=response.json()

                if isinstance(json_data,dict) and "analysis" in json_data:
                    st.session_state.analysis=json_data["analysis"]

                raw_data=[]
                if isinstance(json_data,list): raw_data=json_data
                elif isinstance(json_data,dict): raw_data=json_data.get('deals',json_data.get('data',[]))

                if raw_data:
                    df=pd.DataFrame(raw_data)
                    required_cols=['title','store','price','link','image','rating','deal_badge','offer_text']
                    for c in required_cols:
                        if c not in df.columns: df[c]=None

                    df['Storage']=df['title'].apply(extract_storage)
                    df['RAM']=df['title'].apply(extract_ram)
                    st.session_state.data=df
                else:
                    st.warning("No deals found.")
                    st.session_state.data=None
            else:
                st.error(f"Server Error: {response.status_code}")
        except Exception as e:
            st.error(f"Connection Error: {e}")

# --- DISPLAY RESULTS (PAGE 1) ---
if st.session_state.data is not None:
    df=st.session_state.data

    st.sidebar.header("Filter Results")
    available_stores=df['store'].dropna().unique().tolist()
    if available_stores:
        selected_stores=st.sidebar.multiselect("Select Store",available_stores,default=available_stores)
        if selected_stores: df=df[df['store'].isin(selected_stores)]

    available_ram=sorted(df['RAM'].unique().tolist())
    if 'Other' in available_ram:
        available_ram.remove('Other')
        available_ram.append('Other')
    selected_ram=st.sidebar.multiselect("Select RAM",available_ram,default=available_ram)
    if selected_ram:
        df=df[df['RAM'].isin(selected_ram)]

    available_storage=sorted(df['Storage'].unique().tolist())
    if 'Other' in available_storage:
        available_storage.remove('Other')
        available_storage.append('Other')
    selected_storage=st.sidebar.multiselect("Select Storage",available_storage,default=available_storage)
    if selected_storage:
        df=df[df['Storage'].isin(selected_storage)]

    st.sidebar.markdown("---")
    text_filter=st.sidebar.text_input("Refine Search",placeholder="e.g. Pro, Black")
    if text_filter: df=df[df['title'].str.contains(text_filter,case=False,na=False)]

    st.markdown(f"### Found {len(df)} Deals")

    for index,row in df.iterrows():
        title=row.get('title','No Title')
        price=row.get('price','Check Price')
        store=row.get('store','Online Store')
        link=row.get('link','#')
        img_url=row.get('image')
        
        if not img_url or str(img_url).lower() in ['none','','nan','null'] or not str(img_url).startswith('http'):
            img_url="https://placehold.co/400x400/png?text=No+Image"
            
        deal_badge = row.get('deal_badge')
        offer_text = row.get('offer_text')
        
        is_deal = False
        if pd.notna(deal_badge) and str(deal_badge).strip() != "" and str(deal_badge).lower() not in ['none', 'nan', 'null', 'false']:
            is_deal = True
            deal_badge = str(deal_badge).strip()

        with st.container(border=True):
            c1,c2,c3=st.columns([1.5,3,1.5])
            with c1: st.image(img_url,use_container_width=True)
            with c2:
                st.caption(f"🛍️ {store}")
                st.markdown(f"**{title}**")
                if is_deal:
                    st.markdown(f'<span class="deal-badge">{deal_badge}</span>',unsafe_allow_html=True)
                    if pd.notna(offer_text) and str(offer_text).strip() != "" and str(offer_text).lower() not in ['none','nan','null']:
                        st.caption(f"✨ {offer_text}")
                ram=row.get('RAM','')
                storage=row.get('Storage','')
                if ram!='Other' or storage!='Other':
                    st.caption(f"{ram} | {storage}")
            with c3:
                st.markdown(f"### {price}")
                final_link=f"https://{link}" if link and not str(link).startswith('http') else link
                if final_link and final_link!='#':
                    st.link_button("View Deal ❯",final_link,type="primary",use_container_width=True)

    if st.session_state.ui_step == 0 and st.session_state.analysis and st.session_state.analysis.get("price_data"):
        st.markdown("<div class='center-btn'>", unsafe_allow_html=True)
        st.button("📊 Show Price Comparison", on_click=set_step, args=(1,), type="primary")
        st.markdown("</div>", unsafe_allow_html=True)

    # --- STEP 1: PRICE GRAPH NATIVE (PAGE 2) ---
    if st.session_state.ui_step >= 1 and st.session_state.analysis:
        st.markdown("<div style='height: 15vh;'></div>", unsafe_allow_html=True)
        st.divider()
        st.markdown("<div style='height: 10vh;'></div>", unsafe_allow_html=True)
        
        price_data=st.session_state.analysis.get("price_data",[])
        if price_data:
            st.markdown("## 📊 Price Comparison Across Stores")
            price_df=pd.DataFrame(price_data)
            st.bar_chart(data=price_df, x='store', y='price', height=500, use_container_width=True)
        
        if st.session_state.ui_step == 1:
            st.markdown("<div class='center-btn'>", unsafe_allow_html=True)
            st.button("🤖 Get AI Recommendation", on_click=set_step, args=(2,), type="primary")
            st.markdown("</div>", unsafe_allow_html=True)

    # --- STEP 2: AI RECOMMENDATION PREMIUM UI (PAGE 3) ---
    if st.session_state.ui_step >= 2 and st.session_state.analysis:
        st.markdown("<div style='height: 15vh;'></div>", unsafe_allow_html=True)
        st.divider()
        st.markdown("<div style='height: 10vh;'></div>", unsafe_allow_html=True)
        
        ai_recs = st.session_state.analysis.get("ai_recommendations", [])
        best_store = st.session_state.analysis.get("best_store")
        best_price = st.session_state.analysis.get("best_price")
        savings = st.session_state.analysis.get("savings")

        if not ai_recs and best_store and best_price:
            ai_recs = [{
                "best_deal_title": "Best Value Deal",
                "store": best_store,
                "price": f"₹{best_price}",
                "reason": "This is the lowest confirmed price across all searched platforms."
            }]

        if ai_recs:
            st.markdown("## 🤖 SmartPrice Expert Pick")
            st.caption("Based on real-time data analysis and active offers, here is what AI suggests:")
            
            for rec in ai_recs:
                reason = rec.get("reason", "")
                display_store = rec.get("store", "Unknown Store")
                
                raw_price = str(rec.get("price", "Check Price"))
                if not raw_price.startswith("₹") and raw_price.replace(',', '').isdigit():
                    display_price = f"₹{raw_price}"
                else:
                    display_price = raw_price
                    
                display_title = rec.get("best_deal_title", "Recommended Phone")

                rec_badge = None
                rec_image = "https://placehold.co/400x400/png?text=No+Image" 
                rec_link = "#"
                
                # Fetch image and link from dataframe
                for _, r in df.iterrows():
                    if str(r.get('store')).lower() == str(display_store).lower() and str(raw_price).replace('₹', '') in str(r.get('price')):
                        rb = r.get('deal_badge')
                        if pd.notna(rb) and str(rb).strip() != "" and str(rb).lower() not in ['none', 'nan', 'null', 'false']:
                            rec_badge = str(rb).strip()
                        
                        img = r.get('image')
                        if img and str(img).startswith('http'):
                            rec_image = img
                            
                        raw_l = r.get('link', '#')
                        rec_link = f"https://{raw_l}" if raw_l and not str(raw_l).startswith('http') and raw_l != '#' else raw_l
                        break

                badge_html = f'<div class="badge-premium">🔥 {rec_badge}</div>' if rec_badge else ''
                savings_html = f'<div class="save-tag">💰 You Save ₹{savings} compared to the highest price!</div>' if savings and int(savings) > 0 else ''
                
                html_content = (
                    f'<div class="premium-card">'
                    f'<div style="display:flex; flex-direction:row; align-items:center; gap:25px;">'
                    f'<div style="width:120px; flex-shrink:0;"><img src="{rec_image}" style="width:100%; border-radius:8px; object-fit:contain; mix-blend-mode:multiply;"></div>'
                    f'<div style="flex-grow:1;">'
                    f'{badge_html}'
                    f'<div class="rec-header">✨ {display_title}</div>'
                    f'<div style="display:flex; justify-content:space-between; align-items:center; margin-top:15px; flex-wrap: wrap; gap: 15px;">'
                    f'<div><div style="font-size:0.85rem; color:#64748b; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">Recommended Store</div>'
                    f'<div style="font-size:1.3rem; font-weight:700; color:#334155; margin-top:4px;">🛍️ {display_store}</div></div>'
                    f'<div style="text-align:right;">'
                    f'<div class="rec-price">{display_price}</div>'
                    f'<a href="{rec_link}" target="_blank" class="view-deal-btn">View Deal ❯</a>'
                    f'</div></div>'
                    f'{savings_html}'
                    f'</div></div>'
                    f'<div class="rec-reason" style="margin-top:20px;"><strong style="color:#15803d; font-size:1rem;">💡 AI Assessment:</strong><br>{reason}</div>'
                    f'</div>'
                )
                
                st.markdown(html_content, unsafe_allow_html=True)

        st.markdown("<div style='height: 5vh;'></div>", unsafe_allow_html=True)

        # RE-ADDED BUTTON FOR CHATBOT REVEAL
        if st.session_state.ui_step == 2:
            st.markdown("<div class='center-btn'>", unsafe_allow_html=True)
            st.button("💬 Chat with SmartPrice Assistant", on_click=set_step, args=(3,), type="primary")
            st.markdown("</div>", unsafe_allow_html=True)

    # --- STEP 3: INTERACTIVE CHATBOT (NO REFRESH FRAGMENT WITH DYNAMIC CONTAINER) ---
    @st.fragment
    def chatbot_fragment():
        st.divider()
        st.markdown("## 💬 SmartPrice Shopping Assistant")
        st.caption("Answer a few quick questions to get a highly targeted recommendation!")

        if "messages" not in st.session_state or len(st.session_state.messages) == 0:
            st.session_state.messages = [
                {"role": "assistant", "content": "Hi! I am the SmartPrice AI Assistant. 👋\n\nI am here to guide you to the perfect mobile choice. Please tell me what primary specification you need in a mobile? (e.g., Gaming, Good Camera, or Work purpose)"}
            ]

        # Use an auto-expanding container for dynamic height based on content
        chat_container = st.container()
        
        with chat_container:
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        if prompt := st.chat_input("Type your response here..."):
            
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    with st.spinner("Analyzing..."):
                        import time
                        time.sleep(1.5) 
                        
                        user_replies_count = sum(1 for msg in st.session_state.messages if msg["role"] == "user")
                        
                        # Read the saved search query from memory safely
                        current_search = st.session_state.get("search_query", "")
                        if not current_search:
                            current_search = "the phone you searched for"
                        
                        if user_replies_count == 1:
                            reply = "Great choice. May I know your budget range?"
                        elif user_replies_count == 2:
                            reply = f"Understood. A budget around ₹20,000 for gaming requires a high-performance device. However, based on your initial search for **{current_search}**, it might not be the optimal fit for heavy gaming in this specific price bracket.\n\nWould you like me to suggest alternative phones that perfectly match your gaming requirement?"
                        elif user_replies_count == 3:
                            reply = "Excellent. For a gaming phone near the ₹20,000 budget, the iQOO series provides the best performance. Here are top options:\n\n1. **iQOO Z9 5G** - Approx ₹19,999\n2. **iQOO Z7 Pro** - Approx ₹21,999\n\nYou can type these models in the search bar above to find the lowest live deals!"
                        else:
                            reply = "If you need more suggestions, feel free to ask or use the search bar above to compare prices for these recommendations."
                        
                        st.markdown(reply)
            
            st.session_state.messages.append({"role": "assistant", "content": reply})

    # ONLY SHOW FRAGMENT IF STEP IS 3
    if st.session_state.ui_step >= 3 and st.session_state.analysis:
        chatbot_fragment()

else:
    # --- DEFAULT LANDING PAGE ---
    with landing_page_placeholder.container():
        st.markdown("<br><br>",unsafe_allow_html=True)
        st.markdown("<h3 style='text-align:center;color:#444;'>How it works?</h3><br>",unsafe_allow_html=True)
        hc1,hc2,hc3=st.columns(3)
        with hc1: st.markdown("""<div class="hero-box"><div style="font-size:40px;">🔍</div><div class="hero-title">1. Search Product</div><div class="hero-text">Enter the model name of any mobile phone you want to buy.</div></div>""",unsafe_allow_html=True)
        with hc2: st.markdown("""<div class="hero-box"><div style="font-size:40px;">🤖</div><div class="hero-title">2. AI Compare</div><div class="hero-text">Our AI scans Amazon, Flipkart & JioMart to find the lowest price.</div></div>""",unsafe_allow_html=True)
        with hc3: st.markdown("""<div class="hero-box"><div style="font-size:40px;">🎉</div><div class="hero-title">3. Grab the Deal</div><div class="hero-text">Click 'Buy Now' to purchase directly from the verified store.</div></div>""",unsafe_allow_html=True)
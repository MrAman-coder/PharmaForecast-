import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from serpapi import GoogleSearch
from datetime import datetime
import os

# ---------------- PAGE SETUP ----------------
st.set_page_config(page_title="E-Pharmacy Price Comparison", layout="wide")


# ---------------- PRICE HISTORY ----------------
def save_price_history(medicine, company, price):
    file = "price_history.csv"
    date = datetime.now().strftime("%Y-%m-%d")

    row = {
        "medicine": medicine.lower(),
        "company": company,
        "price": price,
        "date": date
    }

    if os.path.exists(file):
        df = pd.read_csv(file)
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    else:
        df = pd.DataFrame([row])

    df.to_csv(file, index=False)


# ---------------- GENERIC LOGIC ----------------
def find_generic(title):
    try:
        df = pd.read_csv("generic_db.csv")
        title_lower = title.lower()

        for _, row in df.iterrows():
            brand = row["brand"].lower()
            salt = row["salt"].lower()
            strength = row["strength"].lower()

            # Match by brand OR salt+strength
            if brand in title_lower or (salt in title_lower and strength in title_lower):
                return df[
                    (df["salt"] == row["salt"]) &
                    (df["strength"] == row["strength"])
                ]
    except:
        pass

    return None


# ---------------- NPPA CHECK ----------------
def check_nppa_price(title, price):
    try:
        df = pd.read_csv("nppa_prices.csv")
        title_lower = title.lower()

        for _, row in df.iterrows():
            salt = row["salt"].lower()
            strength = row["strength"].lower()

            if salt in title_lower and strength in title_lower:
                if price > row["ceiling_price"]:
                    return row["ceiling_price"]
    except:
        pass

    return None


# ---------------- SERPAPI ----------------
def compare(med_name):
    params = {
        "engine": "google_shopping",
        "q": med_name + " tablet",
        "hl": "en",
        "gl": "in",
        "api_key": "0d8a0a02653ca9cfa57f0c026d7e888c38bb11a34c2df69ad194b4c342b78574"
    }

    search = GoogleSearch(params)
    results = search.get_dict()

    return results.get("shopping_results", [])

# ---------------- UI HEADER (SAME) ----------------
c1, c2 = st.columns(2)
c1.image("e_pharmacy.png", width=200)
c2.header("E-Pharmacy Price Comparison System")

# ---------------- SIDEBAR ----------------
st.sidebar.title("🔍 Enter Medicine Details")
med_name = st.sidebar.text_input("Medicine name")
number = st.sidebar.number_input("Number of options", 1, 10, 5)

# ---------------- MAIN LOGIC ----------------
if st.sidebar.button("Price Compare"):

    shopping_results = compare(med_name)

    if not shopping_results:
        st.error("No data found. Try another medicine name.")
        st.stop()

    lowest_price = float(shopping_results[0]["price"][1:])
    lowest_price_index = 0

    medcine_comp = []
    med_price = []

    for i in range(min(number, len(shopping_results))):

        price_str = shopping_results[i].get("price", "₹0")
        current_price = float(price_str.replace("₹", "").replace(",", ""))

        save_price_history(
            med_name,
            shopping_results[i]["source"],
            current_price
        )

        if current_price < lowest_price:
            lowest_price = current_price
            lowest_price_index = i

        medcine_comp.append(shopping_results[i]["source"])
        med_price.append(current_price)

        # ---------------- OPTION DISPLAY ----------------
        st.title(f"Option {i+1}")
            
        c1, c2, c3 = st.columns([2, 2, 1])
        c1.write("Company:")
        c2.write(shopping_results[i].get('source'))
            
        c1.write("Title:")
        c2.write(shopping_results[i].get('title'))
            
        c1.write("Price:")
        c2.write(shopping_results[i].get('price'))
            
        url=shopping_results[i].get("product_link")
        c1.write("Buy Link :")
        c2.markdown(f"<a href='{url}' target='_blank'>Buy Now</a>", unsafe_allow_html=True)

        # -------- COLUMN 3 --------
        img_url = shopping_results[i].get("thumbnail")

        c3.markdown("### Image")
        if img_url:
            c3.image(img_url, width=170)
        else:
            c3.info("No image available")

        st.divider()

        # ---------------- NPPA WARNING ----------------
        ceiling = check_nppa_price(shopping_results[i]["title"], current_price)
        if ceiling:
            st.warning(f"⚠ Price above NPPA limit (₹{ceiling})")

        # ---------------- GENERIC SECTION (VISIBLE CHANGE) ----------------
        generic_df = find_generic(shopping_results[i]["title"])
        if generic_df is not None and not generic_df.empty:
            try:
                cheapest = generic_df.sort_values("avg_price").iloc[0]
                st.success(
                    f"💊 Cheaper Generic Available → {cheapest['brand']} "
                    f"(₹{cheapest.get('avg_price', 'N/A')})"
                )
                st.dataframe(generic_df)
            except Exception:
                st.info("Generic alternatives available but pricing unavailable.")

    # ---------------- BEST OPTION ----------------
    st.title("✅ Best Online Option")

    c1, c2 = st.columns(2)
    c1.write("Company:")
    c2.write(shopping_results[lowest_price_index]["source"])

    c1.write("Title:")
    c2.write(shopping_results[lowest_price_index]["title"])

    c1.write("Price:")
    c2.write(shopping_results[lowest_price_index]["price"])

    url = shopping_results[lowest_price_index]["product_link"]
    c2.markdown(f"<a href='{url}' target='_blank'>Buy Now</a>", unsafe_allow_html=True)

    # ---------------- SMART SUMMARY ----------------
    st.subheader("🔍 Smart Comparison Summary")
    st.markdown(
        f"""
        • Cheapest online price: **{shopping_results[lowest_price_index]['price']}**  
        • Cheapest pharmacy: **{shopping_results[lowest_price_index]['source']}**  
        • Generic alternatives can save **up to 60–70%**
        """
    )

    # ---------------- CHARTS ----------------
    df = pd.DataFrame(med_price, index=medcine_comp, columns=["Price"])
    st.title("📊 Price Comparison Chart")
    st.bar_chart(df)

    fig, ax = plt.subplots()
    ax.pie(med_price, labels=medcine_comp, autopct="%1.1f%%")
    ax.axis("equal")
    st.pyplot(fig)


    # ---------------- PRICE HISTORY ----------------
    st.title("📈 Price History")

    if os.path.exists("price_history.csv"):
        history_df = pd.read_csv("price_history.csv")

        history_df = history_df[
            history_df["medicine"] == med_name.lower()
        ]

        if not history_df.empty:
            st.line_chart(history_df.groupby("date")["price"].mean())
        else:
            st.info("No history available yet.")
    else:
        st.info("Price history file not found.")





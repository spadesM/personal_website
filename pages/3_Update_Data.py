import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
import time
from auth import check_password

check_password()

# --- File and Config Setup ---
CONFIG_PATH = "config.json"

DATA_FILES = {
    "Loto Data (loto.csv)": "loto.csv",
    "My Ratings (m_ratings.csv)": "m_ratings.csv"
}

if not os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "w") as f:
        json.dump({f: "Not updated yet" for f in DATA_FILES.values()}, f)

with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

# --- UI ---
st.title("📂 Update Lotto Data Files")

selected_file_label = st.selectbox("Select file to update", list(DATA_FILES.keys()))
selected_file_path = DATA_FILES[selected_file_label]

st.write(f"🕒 Last update: **{config.get(selected_file_path, 'Unknown')}**")

# --- File: m_ratings.csv Upload or URL ---
if selected_file_path == "m_ratings.csv":
    st.subheader("⬆️ Upload or Paste URL for My Ratings File")

    method = st.radio("Upload Method", ["Upload File", "Paste URL"])

    if method == "Upload File":
        uploaded_file = st.file_uploader("Upload a CSV file", type="csv")
        if uploaded_file and st.button("Update m_ratings.csv"):
            df = pd.read_csv(uploaded_file)
            df.to_csv("m_ratings.csv", index=False)
            config[selected_file_path] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(CONFIG_PATH, "w") as f:
                json.dump(config, f, indent=2)
            st.success("✅ m_ratings.csv updated successfully!")
            st.dataframe(df)
    else:
        url = st.text_input("Paste URL to CSV file")
        if url and st.button("Fetch and Save m_ratings.csv"):
            try:
                df = pd.read_csv(url)
                df.to_csv("m_ratings.csv", index=False)
                config[selected_file_path] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(CONFIG_PATH, "w") as f:
                    json.dump(config, f, indent=2)
                st.success("✅ m_ratings.csv fetched and updated!")
                st.dataframe(df)
            except Exception as e:
                st.error(f"Failed to load file from URL: {e}")

# --- File: loto.csv Preview & Update ---
elif selected_file_path == "loto.csv":
    st.subheader("📄 Current Data Preview")
    if os.path.exists("loto.csv"):
        try:
            df = pd.read_csv("loto.csv")
            if 'year' in df.columns and 'month_idx' in df.columns and 'game' in df.columns:
                latest_df = (
                    df.sort_values(by=["year", "month_idx", "draw_nr"], ascending=False)
                    .groupby("game")
                    .head(1)
                    .sort_values(["game", "year", "month_idx"], ascending=[True, False, False])
                )
                st.dataframe(latest_df)
            else:
                st.warning("The required columns `game`, `year`, and `month_idx` are missing.")
        except Exception as e:
            st.error(f"Could not read loto.csv: {e}")
    else:
        st.warning("loto.csv does not exist yet.")

    # --- Update button ---
    st.subheader("⬇️ Update Loto Data via Web")
    if st.button("Update data"):
        old_results = pd.read_csv('loto.csv')
        year_min = old_results.year.max()
        month_min = old_results[old_results["year"] == year_min].month_idx.max()

        driver = webdriver.Chrome()
        games = ["on-numara", "sayisal-loto", "super-loto", "sans-topu"]
        months = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
        years = list(range(year_min, datetime.now().year + 1))
        results = []

        for game in games:
            driver.get("https://www.millipiyangoonline.com/cekilis-sonuclari/" + game)
            for year in years:
                for month_idx, month in enumerate(months):
                    if year == year_min and month_idx + 1 < month_min:
                        continue
                    try:
                        month_select = Select(driver.find_element(By.ID, "draw-month"))
                        found_option = None
                        for option in month_select.options:
                            if option.text == month:
                                found_option = option
                                break
                        if not found_option or not found_option.is_enabled():
                            break
                        month_select.select_by_visible_text(month)

                        year_select = Select(driver.find_element(By.ID, "draw-year"))
                        year_select.select_by_visible_text(str(year))

                        filter_button = driver.find_element(By.CLASS_NAME, "draws-submit")
                        filter_button.click()
                        time.sleep(1)

                        items = driver.find_elements(By.CLASS_NAME, "draw_entry")
                        for item in items:
                            try:
                                draw_nr = int(item.find_element(By.CLASS_NAME, "draw_nr").text)
                                numbers = list(map(int, item.find_element(By.XPATH,
                                                                          ".//*[contains(@class, 'numbers')]").text.
                                                   splitlines()))
                                results.append({"game": game, "year": year, "month": month, "month_idx": month_idx + 1,
                                                "draw_nr": draw_nr, "numbers": numbers})
                            except:
                                pass
                    except:
                        continue

        driver.quit()
        results = pd.concat([old_results, pd.DataFrame(results)]).drop_duplicates(subset=["game", "year", "month", "draw_nr"])
        results.to_csv("loto.csv", index=False)
        config[selected_file_path] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)
        st.success("✅ loto.csv updated successfully!")

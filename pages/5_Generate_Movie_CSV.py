import streamlit as st
import pandas as pd
import requests
import time
import os
import gzip
import shutil
import urllib.parse
from bs4 import BeautifulSoup
import json
from auth import check_password

check_password()

st.set_page_config(page_title="Generate Movie CSV", layout="centered")
st.title("🎞️ Generate Movie Dataset")

# --- PARAMETERS ---
MIN_VOTES = 100_000
MIN_RATING = 6.5
OUTPUT_PATH = "movies_platform.csv"
STEP_FILE = "step_status.json"

# --- STATE ---
if "is_running" not in st.session_state:
    st.session_state.is_running = False


def write_step_status(message):
    with open(STEP_FILE, "w") as f:
        json.dump({"step": message}, f)


def read_step_status():
    if os.path.exists(STEP_FILE):
        with open(STEP_FILE, "r") as f:
            return json.load(f).get("step", "No step in progress.")
    return "No step in progress."


# --- Scraper Function ---
def get_movie_title_and_offers(title):
    base_url = "https://www.justwatch.com/tr/arama?q="
    url = f"{base_url}{urllib.parse.quote(title)}"
    time.sleep(0.3)
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        }
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return ""
        soup = BeautifulSoup(response.text, 'html.parser')
        title_element = soup.find(class_="title-list-row__row")
        offer_icons = title_element.find_all(class_="provider-icon") if title_element else []
        alt_texts = [icon.get('alt') for icon in offer_icons if icon.get('alt')]
        return ','.join(alt_texts)
    except Exception as e:
        return ""


# --- Start Process ---
def run_pipeline():
    st.session_state.is_running = True

    try:
        with st.status("🔄 Working...", expanded=True) as status:

            # Step 1 - Download basics
            write_step_status("📥 Downloading IMDb basics data...")
            status.write("📥 Downloading IMDb basics data...")
            basics_url = 'https://datasets.imdbws.com/title.basics.tsv.gz'
            with open("title.basics.tsv.gz", 'wb') as f:
                f.write(requests.get(basics_url).content)
            with gzip.open("title.basics.tsv.gz", 'rb') as f_in:
                with open('title.basics.tsv', 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            df = pd.read_csv('title.basics.tsv', sep='\t', na_values='\\N')
            os.remove('title.basics.tsv')
            os.remove('title.basics.tsv.gz')
            # Step 2 - Download ratings
            write_step_status("📥 Downloading IMDb ratings data...")
            status.write("📥 Downloading IMDb ratings data...")
            ratings_url = 'https://datasets.imdbws.com/title.ratings.tsv.gz'
            with open("title.ratings.tsv.gz", 'wb') as f:
                f.write(requests.get(ratings_url).content)
            with gzip.open("title.ratings.tsv.gz", 'rb') as f_in:
                with open('title.ratings.tsv', 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            ratings = pd.read_csv("title.ratings.tsv", sep="\t", na_values="\\N")
            os.remove('title.ratings.tsv')
            os.remove('title.ratings.tsv.gz')
            # Step 3 - Merge & Filter
            write_step_status("🔗 Merging and filtering movie data...")
            status.write("🔗 Merging and filtering movie data...")
            df = df[df["titleType"] == "movie"]
            df = pd.merge(df, ratings, on="tconst", how="left")

            m_ratings = pd.read_csv("m_ratings.csv")[["Const"]]
            m_ratings["m_rating"] = 1
            df = pd.merge(df, m_ratings, how='left', left_on='tconst', right_on='Const')
            df = df.drop('Const', axis=1)
            df['m_rating'].fillna(0, inplace=True)

            df = df[["tconst", "titleType", "originalTitle", "startYear", "genres", "averageRating", "numVotes",
                     "m_rating"]]
            df = df[(df["numVotes"] > MIN_VOTES) & (df["averageRating"] >= MIN_RATING) & (df["m_rating"] == 0)]

            # Step 4 - Scrape JustWatch
            write_step_status("🎬 Scraping streaming info from JustWatch...")
            status.write("🎬 Scraping streaming info from JustWatch...")
            titles = df["originalTitle"].tolist()

            results = []
            progress = st.progress(0)
            for i, title in enumerate(titles):
                offers = get_movie_title_and_offers(title)
                results.append(offers)
                progress.progress((i + 1) / len(titles))
            progress.empty()

            # Step 5 - Save file
            write_step_status("💾 Saving to result.csv...")
            status.write("💾 Saving to result.csv...")
            df["Streaming"] = results
            df[df["Streaming"] != ""].to_csv(OUTPUT_PATH, index=False)

            write_step_status("✅ Finished!")
            status.update(label="✅ Finished generating dataset!", state="complete")
            st.success("file is ready!")

    except Exception as e:
        error_msg = f"❌ Error: {e}"
        write_step_status(error_msg)
        st.error(error_msg)
    finally:
        st.session_state.is_running = False


# --- UI ---
current_step = read_step_status()

if "is_running" not in st.session_state:
    st.session_state.is_running = current_step != "✅ Finished!" and not current_step.startswith("❌")

# --- UI ---
if st.session_state.is_running:
    st.warning(f"⚙️ Process is currently running.\n\n**Step:** {current_step}")
    st.button("🚀 Start Generating Dataset", disabled=True)
else:
    st.info(f"🧩 Last step: {current_step}")
    if st.button("🚀 Start Generating Dataset"):
        run_pipeline()

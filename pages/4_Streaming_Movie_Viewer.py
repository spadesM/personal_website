import streamlit as st
import pandas as pd
import requests
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from auth import check_password

check_password()

st.set_page_config(page_title="Streaming Movie Viewer", layout="wide")
st.title("🎬 Streaming Movie Explorer")

# Load data
@st.cache_data
def load_data():
    df = pd.read_csv("movies_platform.csv")  # Your updated CSV
    df = df[df["Streaming"] != ""]
    df["startYear"] = df["startYear"].astype("Int64")
    return df

df = load_data()

# Filters
with st.sidebar:
    st.header("📂 Filters")
    years = st.slider("Select Year Range", int(df["startYear"].min()), int(df["startYear"].max()), (2000, 2025))
    platforms = st.selectbox("Streaming Platform", ["All"] + sorted(set(",".join(df["Streaming"]).split(","))))
    genres = st.multiselect("Genre", options=sorted(set(",".join(df["genres"]).split(","))), default=[])
    search = st.text_input("Search Title")

# Apply filters
filtered_df = df[
    df["startYear"].between(*years) &
    df["originalTitle"].str.contains(search, case=False)
]

if platforms != "All":
    filtered_df = filtered_df[filtered_df["Streaming"].str.contains(platforms, na=False)]

if genres:
    for genre in genres:
        filtered_df = filtered_df[filtered_df["genres"].str.contains(genre, na=False)]

# Display filtered DataFrame with AgGrid
st.subheader(f"🎞️ {len(filtered_df)} Movies Found")

gb = GridOptionsBuilder.from_dataframe(
    filtered_df[["originalTitle", "startYear", "genres", "averageRating", "numVotes", "Streaming"]]
)
gb.configure_selection("single", use_checkbox=True)
gb.configure_column("originalTitle", header_name="Title", width=250)
grid_options = gb.build()

grid_response = AgGrid(
    filtered_df,
    gridOptions=grid_options,
    update_mode=GridUpdateMode.SELECTION_CHANGED,
    height=400,
    theme="alpine"
)

selected = grid_response["selected_rows"]

# --- Show movie detail if selected ---
if selected is not None:
    movie = selected.to_dict('records')[0]
    imdb_id = movie["tconst"]

    st.divider()
    st.subheader("🎬 Movie Details")

    # TMDb fetch using IMDb ID
    def get_tmdb_info_by_imdb_id(imdb_id):
        api_key = st.secrets["TMDB_API_KEY"]
        find_url = f"https://api.themoviedb.org/3/find/{imdb_id}?api_key={api_key}&external_source=imdb_id"
        find_response = requests.get(find_url).json()

        movie_results = find_response.get("movie_results", [])
        if not movie_results:
            return None

        tmdb_id = movie_results[0]["id"]
        detail_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={api_key}"
        detail_response = requests.get(detail_url).json()

        return {
            "Title": detail_response.get("title", "Unknown"),
            "Year": detail_response.get("release_date", "Unknown")[:4],
            "Rating": detail_response.get("vote_average", "N/A"),
            "Overview": detail_response.get("overview", "No overview available.")[:300] + "...",
            "Poster": f"https://image.tmdb.org/t/p/w500{detail_response['poster_path']}" if detail_response.get("poster_path") else None,
            "Genres": ", ".join([g["name"] for g in detail_response.get("genres", [])])
        }

    tmdb = get_tmdb_info_by_imdb_id(imdb_id)
    if tmdb:
        col1, col2 = st.columns([1, 2])
        if tmdb["Poster"]:
            col1.image(tmdb["Poster"], use_column_width=True)
        col2.markdown(f"**Title:** {tmdb['Title']}")
        col2.markdown(f"**Original Title:** {movie['originalTitle']}")
        col2.markdown("IMDb Page: [link](%s)" % f'https://www.imdb.com/title/{imdb_id}/')
        col2.markdown(f"**Year:** {tmdb['Year']}")
        col2.markdown(f"**Rating:** ⭐ {tmdb['Rating']}")
        col2.markdown(f"**Genres (TMDb):** {tmdb['Genres']}")
        col2.markdown(f"**Overview:** {tmdb['Overview']}")
    else:
        st.warning("TMDb data not found for this IMDb ID.")

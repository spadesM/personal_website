import streamlit as st
import pandas as pd
import numpy as np
import ast
from auth import check_password

check_password()

def get_predictions(game_type):
    game_types = {
        'sayisal-loto': 7,
        'on-numara': 10,
        'super-loto': 6,
        'sans-topu': 6
    }

    df = pd.read_csv("loto.csv")
    df['numbers'] = df['numbers'].apply(ast.literal_eval)
    df = df[df['game'] == game_type]

    num_arms = max([max(c) for c in df["numbers"]])
    counts = np.zeros(num_arms)
    values = np.zeros(num_arms)

    for t, row in enumerate(df['numbers'], 1):
        for number in row:
            idx = number - 1
            counts[idx] += 1
            values[idx] += 1

    total_draws = np.sum(counts)
    ucb_scores = np.zeros(num_arms)

    for i in range(num_arms):
        if counts[i] > 0:
            avg_reward = values[i] / counts[i]
            confidence = np.sqrt((2 * np.log(total_draws)) / counts[i])
            ucb_scores[i] = avg_reward + confidence
        else:
            ucb_scores[i] = float('inf')

    top_k = game_types[game_type]
    predicted_numbers = np.argsort(ucb_scores)[-top_k:][::-1] + 1

    return predicted_numbers.tolist()


# Streamlit UI
st.title("🔢 Lotto Predictions")

_game_type = st.selectbox("Select Game Type", ['sayisal-loto', 'on-numara', 'super-loto', 'sans-topu'])

if st.button("Predict Numbers"):
    with st.spinner("Calculating predictions..."):
        result = get_predictions(_game_type)
        st.success("Here are your predicted numbers:")
        st.write(f"🎉 Predicted Numbers for **{_game_type}**: ")
        st.markdown(f"<h3 style='text-align: center; color: green;'>{' - '.join(map(str, result))}</h3>",
                    unsafe_allow_html=True)

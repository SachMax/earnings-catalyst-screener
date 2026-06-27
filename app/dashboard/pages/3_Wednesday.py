import streamlit as st
import duckdb

# ---------------------------------------------------------------------------
# Get MotherDuck connection string from Streamlit secrets
# (Works locally if you have .streamlit/secrets.toml, and on Streamlit Cloud)
# ---------------------------------------------------------------------------
DB_URL = st.secrets["motherduck_url"]

@st.cache_data(ttl=60)
def load_data():
    conn = duckdb.connect(DB_URL)
    df = conn.execute("""
    SELECT * FROM output_dataset
    WHERE CAST(earnings_date AS DATE) > CURRENT_DATE
      AND strftime('%w', CAST(earnings_date AS DATE)) == '3'
""").fetchdf()
    conn.close()
    return df

df = load_data()

def color_prob(val):
    color = 'green' if val > 0.35 else 'orange' if val > 0.25 else 'red'
    return f'color: {color}'

st.title(f"Wednesday : {df['earnings_date'].iloc[0]}")
if df.empty:
    st.title("Wednesday : No events")
else:
    display_df = df.drop(columns=['earnings_date'])
    styled_df = display_df.style.map(color_prob, subset=['predicted_win_prob'])
    st.dataframe(styled_df)
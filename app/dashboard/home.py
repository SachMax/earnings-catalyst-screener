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
    df = conn.execute("SELECT * FROM output_dataset ORDER BY earnings_date").fetchdf()
    conn.close()
    return df

df = load_data()

def color_prob(val):
    color = 'green' if val > 0.35 else 'orange' if val > 0.25 else 'red'
    return f'color: {color}'

st.set_page_config(page_title="Earnings Catalyst Screener", page_icon="📊", layout="wide")

st.title("📈 Earnings Catalyst Screener")
st.caption("AI‑powered post‑earnings drift prediction · Updated daily · Phase‑aware screening")

col1, col2, col3 = st.columns(3)
col1.metric("Candidates This Week", len(df))
col2.metric("Avg Predicted Win Prob", f"{df['predicted_win_prob'].mean():.2%}")
col3.metric("Guidance Raises Detected", (df['guidance_bert_raise_prob'] > 0.5).sum())

st.subheader("Next Upcoming Earnings Day")
if not df.empty:
    next_date = df['earnings_date'].min()
    next_df = df[df['earnings_date'] == next_date]
    st.metric("Next Day", str(next_date))
    display_df = next_df[['ticker','phase','predicted_win_prob']]
    styled_df = display_df.style.map(color_prob, subset=['predicted_win_prob'])
    st.dataframe(styled_df)

st.divider()
st.markdown("Built by Sachio Maximilliano Johan · [GitHub](https://github.com/yourusername) · [arXiv](https://arxiv.org/abs/XXXX.XXXXX)")
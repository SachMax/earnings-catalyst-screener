import streamlit as st
import pandas as pd
import sqlite3

conn = sqlite3.connect('data/universe.db')
df = pd.read_sql("SELECT * FROM output_dataset ORDER BY earnings_date", conn)
conn.close()

st.title("Earnings Catalyst Screener – Trade Candidates")
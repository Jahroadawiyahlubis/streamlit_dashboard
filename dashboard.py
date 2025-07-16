import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")

@st.cache_data
def load_data():
    df = pd.read_csv("online_retail.csv", encoding="ISO-8859-1")
    df.dropna(inplace=True)
    df["Total"] = df["Quantity"] * df["UnitPrice"]
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    df["Month"] = df["InvoiceDate"].dt.to_period("M")
    return df

df = load_data()

st.title("📊 Online Retail Dashboard")
st.dataframe(df.head())

# Penjualan per Negara
st.header("🌍 Total Penjualan per Negara")
country_sales = df.groupby("Country")["Total"].sum().sort_values(ascending=False)
st.bar_chart(country_sales.head(10))

# Produk Terlaris
st.header("🏆 Produk Terlaris")
top_products = df.groupby("Description")["Quantity"].sum().sort_values(ascending=False).head(10)
st.bar_chart(top_products)

# Penjualan Bulanan
st.header("📈 Penjualan Bulanan")
monthly_sales = df.groupby("Month")["Total"].sum()
st.line_chart(monthly_sales)

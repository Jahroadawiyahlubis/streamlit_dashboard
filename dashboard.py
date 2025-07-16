import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Online Retail Dashboard", layout="wide")

# Load Data
@st.cache_data
def load_data():
    df = pd.read_csv("online_retail.csv", encoding="ISO-8859-1")
    df.dropna(inplace=True)
    df["Total"] = df["Quantity"] * df["UnitPrice"]
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    df["Month"] = df["InvoiceDate"].dt.to_period("M").astype(str)
    return df

df = load_data()

# Sidebar Filter
st.sidebar.title("🔍 Filter")
selected_countries = st.sidebar.multiselect("Pilih Negara", options=sorted(df["Country"].unique()), default=["United Kingdom"])
selected_months = st.sidebar.multiselect("Pilih Bulan", options=sorted(df["Month"].unique()), default=sorted(df["Month"].unique())[:3])

filtered_df = df[(df["Country"].isin(selected_countries)) & (df["Month"].isin(selected_months))]

# Judul Dashboard
st.title("📊 Online Retail Business Dashboard")

# Ringkasan Bisnis
st.subheader("📌 Ringkasan Bisnis")
col1, col2, col3 = st.columns(3)
col1.metric("💰 Total Penjualan", f"${filtered_df['Total'].sum():,.2f}")
col2.metric("🧾 Jumlah Transaksi", f"{filtered_df['InvoiceNo'].nunique()}")
col3.metric("👥 Jumlah Pelanggan", f"{filtered_df['CustomerID'].nunique()}")

# Tabel Data
st.subheader("📄 Cuplikan Data")
st.dataframe(filtered_df.head(10), use_container_width=True)

# Produk Terlaris
st.subheader("🏆 Top 10 Produk Terlaris")
top_products = filtered_df.groupby("Description")["Quantity"].sum().sort_values(ascending=False).head(10)
fig_top_products = px.bar(
    top_products[::-1],
    x=top_products[::-1].values,
    y=top_products[::-1].index,
    orientation="h",
    labels={"x": "Jumlah Terjual", "y": "Produk"},
    title="Produk Terlaris Berdasarkan Kuantitas",
    text=top_products[::-1].values
)
fig_top_products.update_layout(yaxis=dict(tickfont=dict(size=11)))
st.plotly_chart(fig_top_products, use_container_width=True)

# Penjualan per Negara
st.subheader("🌍 Total Penjualan per Negara (Top 10)")
country_sales = filtered_df.groupby("Country")["Total"].sum().sort_values(ascending=False).head(10)
fig_country = px.bar(
    country_sales[::-1],
    x=country_sales[::-1].values,
    y=country_sales[::-1].index,
    orientation="h",
    labels={"x": "Total Penjualan", "y": "Negara"},
    title="Total Penjualan Negara (USD)",
    text=[f"${x:,.2f}" for x in country_sales[::-1].values]
)
st.plotly_chart(fig_country, use_container_width=True)

# Penjualan Bulanan
st.subheader("📈 Tren Penjualan Bulanan")
monthly_sales = filtered_df.groupby("Month")["Total"].sum().reset_index().sort_values("Month")
fig_monthly = px.line(
    monthly_sales,
    x="Month",
    y="Total",
    markers=True,
    title="Tren Penjualan Bulanan",
    labels={"Total": "Total Penjualan", "Month": "Bulan"},
    text=[f"${x:,.0f}" for x in monthly_sales["Total"]]
)
fig_monthly.update_traces(textposition="top center")
st.plotly_chart(fig_monthly, use_container_width=True)

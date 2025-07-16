import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Online Retail Dashboard", layout="wide")

@st.cache_data
def load_data():
    df = pd.read_csv("online_retail.csv", encoding="ISO-8859-1")
    df.dropna(inplace=True)
    df["Total"] = df["Quantity"] * df["UnitPrice"]
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    df["Month"] = df["InvoiceDate"].dt.to_period("M").astype(str)
    df["Profit"] = df["Total"] * 0.25  # Estimasi profit 25% dari penjualan
    return df

df = load_data()

# Sidebar Filter
st.sidebar.title("🔍 Filter")
selected_countries = st.sidebar.multiselect("Pilih Negara", sorted(df["Country"].unique()), default=["United Kingdom"])
selected_months = st.sidebar.multiselect("Pilih Bulan", sorted(df["Month"].unique()), default=sorted(df["Month"].unique())[:3])
selected_products = st.sidebar.multiselect("Pilih Kategori Produk", sorted(df["Description"].unique()))

filtered_df = df[
    (df["Country"].isin(selected_countries)) &
    (df["Month"].isin(selected_months))
]

if selected_products:
    filtered_df = filtered_df[filtered_df["Description"].isin(selected_products)]

# KPI Cards
st.title("📊 Online Retail Business Dashboard")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("💰 Total Penjualan", f"${filtered_df['Total'].sum():,.2f}")
col2.metric("💵 Estimasi Profit (25%)", f"${filtered_df['Profit'].sum():,.2f}")
col3.metric("📦 Jumlah Pesanan", f"{filtered_df['InvoiceNo'].nunique()}")
col4.metric("👥 Jumlah Pelanggan", f"{filtered_df['CustomerID'].nunique()}")
aov = filtered_df['Total'].sum() / filtered_df['InvoiceNo'].nunique()
col5.metric("📐 AOV", f"${aov:,.2f}")

st.info("📌 Estimasi profit dihitung sebagai 25% dari total penjualan karena data harga pokok tidak tersedia.")

# Data Preview
st.subheader("📄 Cuplikan Data")
st.dataframe(filtered_df.head(10), use_container_width=True)

# Produk Terlaris
st.subheader("🏆 Top 10 Produk Terlaris")
top_products = filtered_df.groupby("Description")["Quantity"].sum().sort_values(ascending=False).head(10)
fig_top_products = px.bar(
    x=top_products.values[::-1],
    y=top_products.index[::-1],
    orientation="h",
    title="Produk Terlaris Berdasarkan Kuantitas",
    labels={"x": "Jumlah Terjual", "y": "Produk"},
    text=top_products.values[::-1]
)
st.plotly_chart(fig_top_products, use_container_width=True)

# Komposisi Penjualan Produk (Grafik Donat)
st.subheader("🍩 Komposisi Penjualan Produk (Top 10)")
top_product_sales = filtered_df.groupby("Description")["Total"].sum().sort_values(ascending=False).head(10)
fig_donut = px.pie(
    names=top_product_sales.index,
    values=top_product_sales.values,
    title="Komposisi Penjualan Produk (Top 10)",
    hole=0.5
)
fig_donut.update_traces(textinfo='percent+label')
st.plotly_chart(fig_donut, use_container_width=True)

# Penjualan Negara
st.subheader("🌍 Total Penjualan per Negara (Top 10)")
country_sales = filtered_df.groupby("Country")["Total"].sum().sort_values(ascending=False).head(10)
fig_country = px.bar(
    x=country_sales.values[::-1],
    y=country_sales.index[::-1],
    orientation="h",
    title="Penjualan Negara (USD)",
    labels={"x": "Total", "y": "Negara"},
    text=[f"${v:,.2f}" for v in country_sales.values[::-1]]
)
st.plotly_chart(fig_country, use_container_width=True)

# Profit per Negara
st.subheader("💵 Estimasi Profit per Negara (Top 10)")
profit_country = filtered_df.groupby("Country")["Profit"].sum().sort_values(ascending=False).head(10)
fig_profit = px.bar(
    x=profit_country.values[::-1],
    y=profit_country.index[::-1],
    orientation="h",
    title="Profit Negara (USD)",
    labels={"x": "Profit", "y": "Negara"},
    text=[f"${v:,.2f}" for v in profit_country.values[::-1]]
)
st.plotly_chart(fig_profit, use_container_width=True)

# Tren Penjualan Bulanan
st.subheader("📈 Tren Penjualan Bulanan")
monthly_sales = filtered_df.groupby("Month")["Total"].sum().reset_index().sort_values("Month")
fig_trend = px.line(
    monthly_sales, x="Month", y="Total",
    markers=True,
    title="Tren Penjualan Bulanan",
    text=[f"${x:,.0f}" for x in monthly_sales["Total"]]
)
fig_trend.update_traces(textposition="top center")
st.plotly_chart(fig_trend, use_container_width=True)

# AOV per Negara
st.subheader("📐 AOV per Negara")
aov_country = df.groupby("Country").apply(lambda x: x["Total"].sum() / x["InvoiceNo"].nunique()).sort_values(ascending=False).head(10)
fig_aov = px.bar(
    x=aov_country.values[::-1],
    y=aov_country.index[::-1],
    orientation="h",
    title="Average Order Value per Negara",
    labels={"x": "AOV", "y": "Negara"},
    text=[f"${v:,.2f}" for v in aov_country.values[::-1]]
)
st.plotly_chart(fig_aov, use_container_width=True)

# Top 5 Pelanggan
st.subheader("👑 Top 5 Pelanggan")
top_customers = filtered_df.groupby("CustomerID")["Total"].sum().sort_values(ascending=False).head(5)
fig_customers = px.bar(
    x=top_customers.values[::-1],
    y=top_customers.index[::-1].astype(str),
    orientation="h",
    title="Top 5 Pelanggan Berdasarkan Total Belanja",
    labels={"x": "Total Belanja", "y": "ID Pelanggan"},
    text=[f"${v:,.2f}" for v in top_customers.values[::-1]]
)
st.plotly_chart(fig_customers, use_container_width=True)

# Insight Strategis
st.markdown("""
### 💡 Insight Strategis
- 🇬🇧 Inggris memiliki volume penjualan tertinggi.
- 🇩🇪 Jerman memiliki AOV tertinggi, menandakan potensi strategi bundling atau premium offer.
- 🍩 Produk-produk dengan kontribusi terbesar terhadap penjualan dapat diprioritaskan dalam promosi dan stok.
- 👑 Pelanggan top dapat menjadi target program loyalitas.
- 📈 Gunakan tren musiman untuk merancang kampanye waktu tertentu (misalnya promosi akhir tahun).
""")

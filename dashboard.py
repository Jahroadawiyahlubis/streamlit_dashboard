import streamlit as st
import pandas as pd
import plotly.express as px
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder
from operator import attrgetter
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

st.set_page_config(page_title="Online Retail Dashboard", layout="wide")

@st.cache_data
def load_data():
    df = pd.read_csv("online_retail.csv", encoding="ISO-8859-1")
    df.dropna(inplace=True)
    df = df[df['Quantity'] > 0]
    df["Total"] = df["Quantity"] * df["UnitPrice"]
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    df["Month"] = df["InvoiceDate"].dt.to_period("M").astype(str)
    df["Profit"] = df["Total"] * 0.25
    return df

df = load_data()

# Sidebar - Logo & Header
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/3/3f/Online_retail_logo.svg/512px-Online_retail_logo.svg.png", width=120)
st.sidebar.markdown("## 🛒 Online Retail Dashboard")

# Sidebar - Menu Navigasi dengan Tabs
tabs = st.tabs([
    "Dashboard Utama", 
    "Segmentasi RFM", 
    "Sistem Rekomendasi (Apriori)", 
    "Sistem Rekomendasi (CF)", 
    "Analisis Retensi", 
    "Insight Strategis"
])

# Sidebar - Filter
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔍 Filter Data")
selected_countries = st.sidebar.multiselect("🌍 Pilih Negara", sorted(df["Country"].unique()), default=["United Kingdom"])
selected_months = st.sidebar.multiselect("🗓️ Pilih Bulan", sorted(df["Month"].unique()), default=sorted(df["Month"].unique())[:3])
selected_products = st.sidebar.multiselect("📦 Pilih Produk", sorted(df["Description"].unique()))
st.sidebar.caption(f"✅ Negara: {len(selected_countries)} | Bulan: {len(selected_months)} | Produk: {len(selected_products)}")

# Filter DataFrame
filtered_df = df[(df["Country"].isin(selected_countries)) & (df["Month"].isin(selected_months))]
if selected_products:
    filtered_df = filtered_df[filtered_df["Description"].isin(selected_products)]

with tabs[0]:
    st.title("📊 Online Retail Business Dashboard")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("💰 Total Penjualan", f"${filtered_df['Total'].sum():,.2f}")
    col2.metric("💵 Estimasi Profit", f"${filtered_df['Profit'].sum():,.2f}")
    col3.metric("📦 Jumlah Pesanan", f"{filtered_df['InvoiceNo'].nunique()}")
    col4.metric("👥 Jumlah Pelanggan", f"{filtered_df['CustomerID'].nunique()}")
    aov = filtered_df['Total'].sum() / filtered_df['InvoiceNo'].nunique()
    col5.metric("📐 AOV", f"${aov:,.2f}")

    st.subheader("📈 Tren Penjualan Bulanan")
    monthly_sales = filtered_df.groupby("Month")["Total"].sum().reset_index().sort_values("Month")
    fig_trend = px.line(monthly_sales, x="Month", y="Total", markers=True)
    st.plotly_chart(fig_trend, use_container_width=True)
    st.caption("💡 Menunjukkan tren total penjualan bulanan berdasarkan filter.")

    st.subheader("🏆 Top 10 Produk Terlaris")
    top_products = filtered_df.groupby("Description")["Quantity"].sum().sort_values(ascending=False).head(10)
    fig_top = px.bar(x=top_products.values[::-1], y=top_products.index[::-1], orientation="h")
    st.plotly_chart(fig_top, use_container_width=True)
    st.caption("💡 Produk paling sering dibeli berdasarkan kuantitas.")

    st.subheader("🌍 Peta Penjualan per Negara")
    country_sales = filtered_df.groupby("Country")["Total"].sum().reset_index()
    fig_map = px.choropleth(country_sales, locations="Country", locationmode="country names", color="Total", title="Penjualan Global")
    st.plotly_chart(fig_map, use_container_width=True)
    st.caption("💡 Visualisasi distribusi penjualan berdasarkan negara.")

    st.subheader("💸 Komposisi Profit per Produk (Top 10)")
    profit_by_product = filtered_df.groupby("Description")["Profit"].sum().sort_values(ascending=False).head(10)
    fig_donut = px.pie(names=profit_by_product.index, values=profit_by_product.values, hole=0.5)
    st.plotly_chart(fig_donut, use_container_width=True)
    st.caption("💡 Kontribusi profit dari produk-produk teratas.")

    st.subheader("👑 Top 5 Pelanggan Berdasarkan Total Belanja")
    top_customers = filtered_df.groupby("CustomerID")["Total"].sum().sort_values(ascending=False).head(5)
    st.dataframe(top_customers.reset_index().rename(columns={"Total": "TotalBelanja"}))

with tabs[1]:
    st.title("📌 Segmentasi Pelanggan - RFM")
    rfm_df = df.groupby("CustomerID").agg({
        "InvoiceDate": lambda x: (df["InvoiceDate"].max() - x.max()).days,
        "InvoiceNo": "count",
        "Total": "sum"
    }).rename(columns={"InvoiceDate": "Recency", "InvoiceNo": "Frequency", "Total": "Monetary"})
    scaler = StandardScaler()
    rfm_scaled = scaler.fit_transform(rfm_df)
    kmeans = KMeans(n_clusters=4, random_state=42).fit(rfm_scaled)
    rfm_df["Cluster"] = kmeans.labels_

    cluster_labels = {
        0: "🟣 Cluster 0 - Baru / sesekali beli",
        1: "🔵 Cluster 1 - Pasif / risiko churn",
        2: "🟢 Cluster 2 - Setia & aktif",
        3: "🟡 Cluster 3 - Pelanggan Terbaik"
    }
    rfm_df["ClusterLabel"] = rfm_df["Cluster"].map(cluster_labels)
    fig_rfm = px.pie(rfm_df, names="ClusterLabel", title="Distribusi Klaster Pelanggan")
    st.plotly_chart(fig_rfm)
    st.dataframe(rfm_df.reset_index().head(10))
    st.caption("💡 Segmentasi berdasarkan Recency, Frequency, dan Monetary untuk memahami perilaku pelanggan.")

    st.markdown("""
    **Penjelasan Klaster:**
    - 🟡 Cluster 3 – Pelanggan Terbaik
    - 🟢 Cluster 2 – Setia & aktif
    - 🟣 Cluster 0 – Baru / sesekali beli
    - 🔵 Cluster 1 – Pasif / risiko churn
    """)

with tabs[2]:
    st.title("🛍️ Rekomendasi Produk - Market Basket (Apriori)")
    basket_df = df[df['Country'] == 'Germany'].groupby(['InvoiceNo', 'Description'])["Quantity"].sum().unstack().fillna(0)
    basket_df = basket_df.applymap(lambda x: 1 if x > 0 else 0)
    frequent_itemsets = apriori(basket_df, min_support=0.02, use_colnames=True)
    rules = association_rules(frequent_itemsets, metric="lift", min_threshold=1)
    st.dataframe(rules[["antecedents", "consequents", "support", "confidence", "lift"]].head(10))
    st.caption("💡 Aturan asosiasi produk untuk rekomendasi bundling.")

with tabs[3]:
    st.title("🤖 Sistem Rekomendasi - Collaborative Filtering")
    pivot = df.pivot_table(index='CustomerID', columns='Description', values='Total', aggfunc='sum').fillna(0)
    similarity = cosine_similarity(pivot)
    sim_df = pd.DataFrame(similarity, index=pivot.index, columns=pivot.index)
    selected_id = st.selectbox("Pilih CustomerID", pivot.index.astype(int))
    similar_scores = sim_df[selected_id].sort_values(ascending=False)[1:6]
    st.write("Customer serupa:")
    st.dataframe(similar_scores)
    rec_customer = pivot.loc[similar_scores.index].mean().sort_values(ascending=False).head(5)
    st.subheader("📦 Rekomendasi Produk Untuk Customer Ini")
    st.dataframe(rec_customer)
    st.caption("💡 Rekomendasi berdasarkan kemiripan perilaku pembelian pelanggan.")

with tabs[4]:
    st.title("⏳ Analisis Retensi Pelanggan")
    df['CohortMonth'] = df['InvoiceDate'].dt.to_period("M")
    cohort_data = df.groupby(['CustomerID']).agg({"InvoiceDate": "min"}).rename(columns={"InvoiceDate": "FirstPurchase"})
    df = df.join(cohort_data, on="CustomerID")
    df["CohortIndex"] = ((df['InvoiceDate'].dt.to_period("M") - df['FirstPurchase'].dt.to_period("M")).apply(attrgetter('n')))
    cohort = df.groupby(["CohortMonth", "CohortIndex"]).agg({"CustomerID": "nunique"}).unstack().fillna(0)
    st.dataframe(cohort.head(12))
    st.caption("💡 Menunjukkan pola retensi pelanggan berdasarkan waktu pembelian pertama mereka.")

with tabs[5]:
    st.title("💡 Insight dan Rekomendasi Strategis")
    st.markdown("""
    - 🇩🇪 Jerman memiliki AOV tertinggi → cocok untuk promosi bundling produk premium.
    - 🟡 Cluster 3 adalah pelanggan paling bernilai → beri loyalti atau reward.
    - 🔵 Cluster 1 = pelanggan pasif → buat kampanye reaktivasi.
    - 🛍️ Bundling produk dari Apriori bisa dijadikan rekomendasi eksplisit.
    - 📅 Optimalkan kampanye akhir tahun berdasarkan tren bulanan penjualan.
    """)

    aov_country = df.groupby("Country").agg({"Total": "sum", "InvoiceNo": "nunique"})
    aov_country["AOV"] = aov_country["Total"] / aov_country["InvoiceNo"]
    fig_heatmap = px.density_heatmap(aov_country.reset_index(), x="Country", y="AOV", color_continuous_scale="Blues")
    st.plotly_chart(fig_heatmap, use_container_width=True)
    st.caption("💡 Visualisasi negara dengan AOV tertinggi sebagai referensi strategi marketing.")

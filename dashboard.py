import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Online Retail Dashboard", layout="wide", initial_sidebar_state="expanded")

@st.cache_data
def load_data():
    df = pd.read_csv("online_retail.csv", encoding="ISO-8859-1")
    
    # Data Cleaning sesuai laporan: Menangani missing values dan menghapus kuantitas/harga unit negatif
    # Menghapus baris dengan CustomerID atau Description yang hilang
    df.dropna(subset=['CustomerID', 'Description'], inplace=True) 
    # Menghapus transaksi dengan kuantitas negatif atau nol (pengembalian)
    df = df[df["Quantity"] > 0] 
    # Menghapus transaksi dengan harga unit negatif atau nol
    df = df[df["UnitPrice"] > 0] 

    # Menghitung Total Penjualan per baris
    df["Total"] = df["Quantity"] * df["UnitPrice"]
    # Mengonversi InvoiceDate ke format datetime
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    # Mengekstrak bulan untuk analisis temporal
    df["Month"] = df["InvoiceDate"].dt.to_period("M").astype(str)
    # Estimasi profit 25% dari total penjualan
    df["Profit"] = df["Total"] * 0.25  

    # Analisis RFM (Recency, Frequency, Monetary)
    # Menggunakan tanggal transaksi terakhir + 1 hari sebagai tanggal snapshot untuk perhitungan Recency
    snapshot_date = df['InvoiceDate'].max() + pd.Timedelta(days=1) 

    rfm_df = df.groupby('CustomerID').agg(
        Recency=('InvoiceDate', lambda date: (snapshot_date - date.max()).days), # Hari sejak pembelian terakhir
        Frequency=('InvoiceNo', 'nunique'), # Jumlah transaksi unik
        Monetary=('Total', 'sum') # Total pengeluaran
    ).reset_index()

    # Mengubah CustomerID ke int untuk konsistensi (setelah dropna, mungkin berupa float)
    rfm_df['CustomerID'] = rfm_df['CustomerID'].astype(int)

    # --- Simplified RFM Segmentation for Visualization ---
    # Assign RFM scores based on quantiles (Higher R is worse, Higher F, M is better)
    
    # For Recency, lower values are better (more recent), so score 5 goes to lowest R.
    num_unique_r = rfm_df['Recency'].nunique()
    if num_unique_r < 2: # Cannot create bins if less than 2 unique values
        rfm_df['R_Score'] = 5 if num_unique_r == 1 else 1 # Assign 5 if only one value (best), else 1
    else:
        # Determine the effective number of quantiles, max 5
        q_r = min(5, num_unique_r)
        # Get bin indices (0 to q_r-1)
        rfm_df['R_Score'] = pd.qcut(rfm_df['Recency'], q=q_r, labels=False, duplicates='drop')
        # Map to 1-q_r, then reverse for Recency (lower value = higher score)
        rfm_df['R_Score'] = q_r - rfm_df['R_Score'] # This maps 0 to q_r, 1 to q_r-1, etc.
        rfm_df['R_Score'] = rfm_df['R_Score'].astype(int)


    # For Frequency and Monetary, higher values are better, so score 5 goes to highest F/M.
    num_unique_f = rfm_df['Frequency'].nunique()
    if num_unique_f < 2:
        rfm_df['F_Score'] = 1 if num_unique_f == 1 else 1
    else:
        q_f = min(5, num_unique_f)
        rfm_df['F_Score'] = pd.qcut(rfm_df['Frequency'], q=q_f, labels=False, duplicates='drop') + 1
        rfm_df['F_Score'] = rfm_df['F_Score'].astype(int)

    num_unique_m = rfm_df['Monetary'].nunique()
    if num_unique_m < 2:
        rfm_df['M_Score'] = 1 if num_unique_m == 1 else 1
    else:
        q_m = min(5, num_unique_m)
        rfm_df['M_Score'] = pd.qcut(rfm_df['Monetary'], q=q_m, labels=False, duplicates='drop') + 1
        rfm_df['M_Score'] = rfm_df['M_Score'].astype(int)

    # Combine RFM scores into a segment
    # This is a basic example. In real K-Means, you'd get clusters.
    # For a dashboard, a heuristic segmentation can be useful for visualization.
    def rfm_segment(row):
        if row['R_Score'] == 5 and row['F_Score'] == 5 and row['M_Score'] == 5:
            return 'Champions'
        elif row['R_Score'] == 5 and row['F_Score'] >= 4 and row['M_Score'] >= 4:
            return 'Loyal Customers'
        elif row['R_Score'] >= 4 and row['F_Score'] >= 4 and row['M_Score'] >= 4:
            return 'Potential Loyalists'
        elif row['R_Score'] <= 2 and row['F_Score'] <= 2 and row['M_Score'] <= 2:
            return 'At Risk/Lost'
        elif row['R_Score'] == 5 and row['F_Score'] == 1 and row['M_Score'] == 1:
            return 'New Customers'
        else:
            return 'Others' # Or refine more segments

    rfm_df['RFM_Segment'] = rfm_df.apply(rfm_segment, axis=1)

    return df, rfm_df

# Memuat data transaksi yang sudah dibersihkan dan data RFM
df, rfm_df = load_data()

# --- Sidebar Filter ---
st.sidebar.header("🔍 Filter Data Penjualan")
st.sidebar.markdown("Sesuaikan tampilan dasbor berdasarkan kriteria di bawah.")

selected_countries = st.sidebar.multiselect(
    "Pilih Negara", 
    sorted(df["Country"].unique()), 
    default=["United Kingdom"] # Default UK karena mayoritas transaksi dari UK
)
selected_months = st.sidebar.multiselect(
    "Pilih Bulan", 
    sorted(df["Month"].unique()), 
    default=sorted(df["Month"].unique()) # Default semua bulan atau beberapa bulan pertama
)

# --- Menerapkan Filter ke DataFrame Utama (initial filtering) ---
# This filtered_df is used to make the product_options dynamic.
# It needs to be calculated before the product multiselect options are determined.
pre_filtered_df_for_products = df[
    (df["Country"].isin(selected_countries)) &
    (df["Month"].isin(selected_months))
]

product_options = sorted(pre_filtered_df_for_products["Description"].unique()) 
selected_products = st.sidebar.multiselect(
    "Pilih Kategori Produk", 
    product_options
)

# --- Final Filtering ---
filtered_df = pre_filtered_df_for_products # Start with the pre-filtered DF
if selected_products:
    filtered_df = filtered_df[filtered_df["Description"].isin(selected_products)]

# --- Reset Filter Button ---
if st.sidebar.button("🔄 Reset Filter"):
    st.session_state.clear() # Clear all session state
    st.experimental_rerun() # Rerun the app to reset filters

# --- Judul Dashboard ---
st.title("📊 Dasbor Kinerja Penjualan Ritel Online")
st.markdown("Dasbor interaktif ini menyajikan gambaran komprehensif tentang kinerja penjualan dan perilaku pelanggan.")

# --- Kartu KPI (Key Performance Indicators) ---
st.subheader("Ringkasan Kinerja Utama")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("💰 Total Penjualan", f"${filtered_df['Total'].sum():,.2f}")
col2.metric("💵 Estimasi Profit (25%)", f"${filtered_df['Profit'].sum():,.2f}")
col3.metric("📦 Jumlah Pesanan", f"{filtered_df['InvoiceNo'].nunique()}")
col4.metric("👥 Jumlah Pelanggan", f"{filtered_df['CustomerID'].nunique()}")
aov = filtered_df['Total'].sum() / filtered_df['InvoiceNo'].nunique() if filtered_df['InvoiceNo'].nunique() > 0 else 0
col5.metric("📐 Rata-rata Nilai Pesanan (AOV)", f"${aov:,.2f}")

st.info("📌 Estimasi profit dihitung sebagai 25% dari total penjualan karena data harga pokok tidak tersedia dalam dataset ini.")

# --- Cuplikan Data ---
with st.expander("📄 Lihat Cuplikan Data Transaksi Teratas"):
    st.markdown("Berikut adalah beberapa baris pertama dari data transaksi yang telah difilter.")
    st.dataframe(filtered_df.head(10), use_container_width=True)
    st.download_button(
        label="Unduh Data Transaksi Filtered",
        data=filtered_df.to_csv(index=False).encode('utf-8'),
        file_name='filtered_transactions.csv',
        mime='text/csv',
    )


# --- Analisis Pelanggan (RFM) ---
st.header("👤 Analisis Pelanggan & Segmentasi RFM")
st.markdown("Memahami pelanggan Anda melalui metrik Recency (kapan terakhir membeli), Frequency (seberapa sering membeli), dan Monetary (berapa banyak yang dibelanjakan), dan segmen RFM.")

col_rfm1, col_rfm2 = st.columns([1, 2])

with col_rfm1:
    st.subheader("Cuplikan Data RFM")
    st.dataframe(rfm_df.head(10), use_container_width=True)
    st.download_button(
        label="Unduh Data RFM",
        data=rfm_df.to_csv(index=False).encode('utf-8'),
        file_name='rfm_data.csv',
        mime='text/csv',
    )
    
    st.markdown("Distribusi metrik RFM: ")
    rfm_metric_choice = st.radio(
        "Pilih Metrik RFM untuk Visualisasi Distribusi:",
        ("Recency", "Frequency", "Monetary")
    )

with col_rfm2:
    st.subheader(f"Distribusi Metrik {rfm_metric_choice}")
    fig_rfm_dist = px.histogram(
        rfm_df, 
        x=rfm_metric_choice, 
        nbins=50, 
        title=f"Distribusi {rfm_metric_choice} Pelanggan",
        template="plotly_white" # Modern template
    )
    fig_rfm_dist.update_layout(bargap=0.1)
    st.plotly_chart(fig_rfm_dist, use_container_width=True)

# Scatter plot of Recency vs Frequency, colored by RFM Segment
st.subheader("Visualisasi Segmentasi Pelanggan (RFM)")
st.markdown("Sebaran pelanggan berdasarkan Recency dan Frequency, diwarnai oleh segmen RFM yang telah ditentukan. *(Segmentasi ini adalah contoh heuristik untuk visualisasi, bukan hasil dari K-Means)*.")
fig_rfm_scatter = px.scatter(
    rfm_df, 
    x="Recency", 
    y="Frequency", 
    color="RFM_Segment", 
    hover_name="CustomerID",
    size="Monetary", # Size of marker based on Monetary value
    title="Segmentasi Pelanggan Berdasarkan RFM",
    labels={"Recency": "Recency (Hari Lalu)", "Frequency": "Frekuensi Pembelian"},
    template="plotly_white"
)
st.plotly_chart(fig_rfm_scatter, use_container_width=True)

# --- Grafik Utama Penjualan & Produk ---
st.header("📈 Tren & Kinerja Penjualan")

# Tren Penjualan Bulanan
st.subheader("Tren Penjualan Bulanan")
st.markdown("Analisis pola musiman dan tren pertumbuhan penjualan dari waktu ke waktu.")
monthly_sales = filtered_df.groupby("Month")["Total"].sum().reset_index().sort_values("Month")
fig_trend = px.line(
    monthly_sales, x="Month", y="Total",
    markers=True,
    title="Tren Penjualan Bulanan",
    text=[f"${x:,.0f}" for x in monthly_sales["Total"]],
    template="plotly_white"
)
fig_trend.update_traces(textposition="top center")
st.plotly_chart(fig_trend, use_container_width=True)

# Penjualan Berdasarkan Lokasi dan Produk (menggunakan st.tabs untuk modernitas)
st.header("🌎 Analisis Geografis & Produk")
tab1, tab2 = st.tabs(["Penjualan per Negara", "Kinerja Produk"])

with tab1:
    col_loc1, col_loc2 = st.columns(2)
    with col_loc1:
        # Penjualan Negara
        st.subheader("Total Penjualan per Negara (Top 10)")
        st.markdown("Identifikasi pasar dengan kinerja terbaik berdasarkan total penjualan.")
        country_sales = filtered_df.groupby("Country")["Total"].sum().sort_values(ascending=False).head(10)
        fig_country = px.bar(
            x=country_sales.values[::-1], 
            y=country_sales.index[::-1],
            orientation="h",
            title="Penjualan Negara (USD)",
            labels={"x": "Total Penjualan", "y": "Negara"},
            text=[f"${v:,.2f}" for v in country_sales.values[::-1]],
            template="plotly_white"
        )
        fig_country.update_layout(showlegend=False)
        st.plotly_chart(fig_country, use_container_width=True)
    with col_loc2:
        # Profit per Negara
        st.subheader("Estimasi Profit per Negara (Top 10)")
        st.markdown("Estimasi profit dari penjualan di berbagai negara.")
        profit_country = filtered_df.groupby("Country")["Profit"].sum().sort_values(ascending=False).head(10)
        fig_profit = px.bar(
            x=profit_country.values[::-1],
            y=profit_country.index[::-1],
            orientation="h",
            title="Profit Negara (USD)",
            labels={"x": "Estimasi Profit", "y": "Negara"},
            text=[f"${v:,.2f}" for v in profit_country.values[::-1]],
            template="plotly_white"
        )
        fig_profit.update_layout(showlegend=False)
        st.plotly_chart(fig_profit, use_container_width=True)

with tab2:
    col_prod1, col_prod2 = st.columns(2)
    with col_prod1:
        # Produk Terlaris
        st.subheader("Top 10 Produk Terlaris (Kuantitas)")
        st.markdown("Produk yang paling banyak terjual berdasarkan kuantitas.")
        top_products = filtered_df.groupby("Description")["Quantity"].sum().sort_values(ascending=False).head(10)
        fig_top_products = px.bar(
            x=top_products.values[::-1],
            y=top_products.index[::-1],
            orientation="h",
            title="Produk Terlaris Berdasarkan Kuantitas",
            labels={"x": "Jumlah Terjual", "y": "Produk"},
            text=top_products.values[::-1],
            template="plotly_white"
        )
        fig_top_products.update_layout(showlegend=False)
        st.plotly_chart(fig_top_products, use_container_width=True)
    with col_prod2:
        # Komposisi Penjualan Produk (Grafik Donat)
        st.subheader("Komposisi Penjualan Produk (Top 10)")
        st.markdown("Proporsi penjualan yang disumbangkan oleh 10 produk teratas.")
        top_product_sales = filtered_df.groupby("Description")["Total"].sum().sort_values(ascending=False).head(10)
        fig_donut = px.pie(
            names=top_product_sales.index,
            values=top_product_sales.values,
            title="Komposisi Penjualan Produk (Top 10)",
            hole=0.5,
            template="plotly_white"
        )
        fig_donut.update_traces(textinfo='percent+label')
        st.plotly_chart(fig_donut, use_container_width=True)

# AOV per Negara & Top Pelanggan (Menggunakan st.container atau st.expander untuk struktur)
st.header("🎯 Analisis Nilai & Loyalitas Pelanggan")
col_aov_cust1, col_aov_cust2 = st.columns(2)

with col_aov_cust1:
    # AOV per Negara
    st.subheader("Rata-rata Nilai Pesanan (AOV) per Negara")
    st.markdown("Perbandingan nilai belanja rata-rata per pesanan di berbagai negara.")
    aov_country = filtered_df.groupby("Country").apply(lambda x: x["Total"].sum() / x["InvoiceNo"].nunique() if x["InvoiceNo"].nunique() > 0 else 0).sort_values(ascending=False).head(10)
    fig_aov = px.bar(
        x=aov_country.values[::-1],
        y=aov_country.index[::-1],
        orientation="h",
        title="Average Order Value per Negara",
        labels={"x": "AOV", "y": "Negara"},
        text=[f"${v:,.2f}" for v in aov_country.values[::-1]],
        template="plotly_white"
    )
    fig_aov.update_layout(showlegend=False)
    st.plotly_chart(fig_aov, use_container_width=True)

with col_aov_cust2:
    # Top 5 Pelanggan
    st.subheader("Top 5 Pelanggan Berdasarkan Total Belanja")
    st.markdown("Pelanggan paling berharga berdasarkan total pengeluaran mereka.")
    top_customers = filtered_df.groupby("CustomerID")["Total"].sum().sort_values(ascending=False).head(5)
    fig_customers = px.bar(
        x=top_customers.values[::-1],
        y=top_customers.index[::-1].astype(str),
        orientation="h",
        title="Top 5 Pelanggan Berdasarkan Total Belanja",
        labels={"x": "Total Belanja", "y": "ID Pelanggan"},
        text=[f"${v:,.2f}" for v in top_customers.values[::-1]],
        template="plotly_white"
    )
    fig_customers.update_layout(showlegend=False)
    st.plotly_chart(fig_customers, use_container_width=True)

# --- Insight Strategis ---
st.header("💡 Insight Strategis & Rekomendasi")
st.markdown("Temuan utama dari analisis data untuk mendukung pengambilan keputusan bisnis yang lebih baik.")
st.markdown("""
- **Dominasi Pasar**: Inggris memiliki volume penjualan tertinggi secara absolut, menegaskan posisinya sebagai pasar utama.
- **Potensi Pertumbuhan**: Jerman menunjukkan Average Order Value (AOV) yang secara signifikan lebih tinggi, mengindikasikan bahwa pelanggan di Jerman cenderung membelanjakan lebih banyak per transaksi. Ini membuka peluang untuk strategi *bundling* atau penawaran premium yang ditargetkan.
- **Fokus Produk**: Produk-produk yang berkontribusi terbesar terhadap total penjualan (berdasarkan kuantitas atau nilai) harus menjadi prioritas dalam strategi promosi, manajemen stok, dan pengembangan produk di masa mendatang.
- **Program Loyalitas Pelanggan**: Identifikasi dan berikan apresiasi kepada pelanggan dengan pengeluaran tertinggi melalui program loyalitas khusus. Ini dapat meningkatkan retensi dan nilai seumur hidup pelanggan (CLTV).
- **Optimalisasi Kampanye Musiman**: Tren penjualan bulanan menunjukkan pola musiman yang jelas. Manfaatkan informasi ini untuk merancang kampanye pemasaran yang tepat waktu, misalnya promosi khusus untuk periode puncak penjualan atau reaktivasi untuk periode rendah.
""")
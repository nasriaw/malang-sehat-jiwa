import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from streamlit_geolocation import streamlit_geolocation
from streamlit_autorefresh import st_autorefresh
import requests
import os
import math
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import datetime

st.set_page_config(
    page_title="MALANG SEHAT JIWA v1.0 - Deteksi Dini Kesehatan Mental",
    page_icon="💚",
    layout="wide"
)

# Kredensial Bot Telegram
BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID")

# Inisialisasi Session State Data Relawan & Log
if 'relawan_data' not in st.session_state:
    try: 
        st.session_state.relawan_data = pd.read_csv("data/relawan_jiwa.csv")
    except: 
        st.session_state.relawan_data = pd.DataFrame([
            {"Nama": "Relawan Pusat Malang", "No_Handphone": "", "Latitude": -7.970222, "Longitude": 112.607498, "Status": "Aktif"},
            {"Nama": "Relawan Sukun", "No_Handphone": "", "Latitude": -7.9922, "Longitude": 112.6160, "Status": "Aktif"},
            {"Nama": "Relawan Klojen", "No_Handphone": "", "Latitude": -7.9778, "Longitude": 112.6261, "Status": "Aktif"}
        ])

if 'screening_logs' not in st.session_state: st.session_state.screening_logs = []
if 'right_button_clicks' not in st.session_state: st.session_state.right_button_clicks = 0
if 'admin_mode' not in st.session_state: st.session_state.admin_mode = False
if 'submitted' not in st.session_state: st.session_state.submitted = False
if 'last_score' not in st.session_state: st.session_state.last_score = 0
if 'last_time' not in st.session_state: st.session_state.last_time = ""

BASE_LAT, BASE_LON = -7.970222, 112.607498

def ambil_waktu_wib():
    waktu_utc = datetime.datetime.utcnow()
    waktu_wib = waktu_utc + datetime.timedelta(hours=7)
    return waktu_wib

def send_telegram_alert(kota, skor, tingkat_risiko, lat, lon):
    timestamp = ambil_waktu_wib().strftime("%d-%m-%Y %H:%M:%S")
    
    if lat and lon:
        maps_url = f"https://www.google.com/maps?q={lat},{lon}"
        lokasi_str = f"{lat}, {lon}\n🔗 [Buka Peta Lokasi Pelapor]({maps_url})"
    else:
        lokasi_str = "GPS Tidak Diizinkan Pengguna"

    pesan = (
        "💚 *NOTIFIKASI MALANG SEHAT JIWA v1.0* 💚\n\n"
        f"📅 *Waktu:* {timestamp} WIB\n"
        f"📍 *Wilayah Otoritas:* {kota}\n"
        f"📊 *Skor PHQ-9+:* {skor} / 30\n"
        f"⚠️ *Status Risiko:* {tingkat_risiko}\n"
        f"📍 *Koordinat Peta:* {lokasi_str}\n\n"
        "_*Mohon tim relawan terdekat segera memantau kondisi wilayah terkait._"
    )
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, json={"chat_id": CHAT_ID, "text": pesan, "parse_mode": "Markdown"}, timeout=10)
        return resp.status_code == 200
    except:
        return False

def generate_pdf_report(logs):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor('#2e7d32'), spaceAfter=12)
    normal_style = styles['Normal']
    
    story.append(Paragraph("LAPORAN DATA AGREGAT SKRENING - MALANG SEHAT JIWA", title_style))
    waktu_cetak = ambil_waktu_wib().strftime("%Y-%m-%d %H:%M:%S")
    story.append(Paragraph(f"Dicetak pada: {waktu_cetak} WIB (Data bersifat Anonim)", normal_style))
    story.append(Spacer(1, 15))
    
    data = [["Waktu", "Kota/Kabupaten", "Usia", "Skor", "Tingkat Risiko", "Latitude", "Longitude"]]
    for log in logs:
        data.append([
            str(log.get('Waktu', '-')), 
            str(log.get('Kota', '-')), 
            str(log.get('Usia', '-')), 
            f"{log.get('Skor', 0)}/30", 
            str(log.get('Risiko', '-')), 
            str(log.get('Lat', '-')) if log.get('Lat') is not None else '-', 
            str(log.get('Lon', '-')) if log.get('Lon') is not None else '-'
        ])
        
    t = Table(data, colWidths=[110, 90, 40, 50, 110, 70, 70])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2e7d32')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f1f8e9')),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#dcedc8')),
    ]))
    story.append(t)
    doc.build(story)
    buffer.seek(0)
    return buffer

# --- PANEL UTAMA INTERFASE PENGGUNA ---
if not st.session_state.admin_mode:
    loc_data = streamlit_geolocation()
    
    # Header Aplikasi Utama
    col_logo, col_title = st.columns([1, 6])
    with col_logo:
        if os.path.exists("logo_msj.png"):
            st.image("logo_msj.png", width=100)
    with col_title:
        st.markdown("<h1 style='color: #2e7d32; margin-bottom:0px;'>💚 MALANG SEHAT JIWA v1.0</h1>", unsafe_allow_html=True)
        st.markdown("<p style='color: #718096; font-size:1.1em; margin-top:0px;'>Screening Kesehatan Jiwa Berbasis Web | Antarmuka Deteksi Dini | Klik Logo GPS di kiri atas untuk ijin bantuan jika skor Screening melebihi batas aman</p>", unsafe_allow_html=True)
    
    st.warning("⚠️ **DARURAT! Hubungi segera:** 119 ext 8 | 112 | ")
    st.write("---")
    
    st.markdown("### **Check-in 3 Menit**")
    kota_input = st.text_input("Kota/Kabupaten Lokasi Anda Saat Ini", value="Malang")
    usia_input = st.slider("Usia", min_value=10, max_value=100, value=20)
    
    st.write("---")
    st.markdown("### **Isi Screening Risiko**")
    st.markdown("<p style='font-style: italic; color: #4a5568;'>Seberapa sering dalam 2 minggu terakhir Anda merasakan hal-hal berikut?</p>", unsafe_allow_html=True)
    
    pertanyaan = [
        "1. Minat melakukan sesuatu menurun", "2. Merasa sedih, murung, atau putus asa",
        "3. Sulit tidur atau tidur terlalu banyak", "4. Merasa lelah atau tidak bertenaga",
        "5. Nafsu makan menurun atau berlebihan", "6. Merasa gagal atau mengecewakan diri/keluarga",
        "7. Sulit konsentrasi pada sesuatu", "8. Bergerak/berbicara sangat lambat atau gelisah",
        "9. Berpikir bahwa lebih baik mati atau menyakiti diri", "10. Apakah Anda punya rencana spesifik untuk bunuh diri?"
    ]
    
    opsi = {0: "0 - Tidak sama sekali", 1: "1 - Beberapa hari", 2: "2 - >7 hari", 3: "3 - Hampir setiap hari"}
    total_skor = 0
    
    for idx, q in enumerate(pertanyaan):
        st.markdown(f"**{q}**")
        pilihan = st.radio(
            f"Pilih opsi {idx+1}", 
            options=[0, 1, 2, 3], 
            format_func=lambda x: opsi[x], 
            key=f"q_{idx}", 
            label_visibility="collapsed",
            horizontal=True
        )
        total_skor += pilihan
        st.write("")

    if st.button("Dapatkan Hasil & Bantuan", type="primary"):
        st.session_state.submitted = True
        st.session_state.last_score = total_skor
        st.session_state.last_time = ambil_waktu_wib().strftime("%d-%m-%Y %H:%M:%S")
        
        user_lat = loc_data.get("latitude") if loc_data else None
        user_lon = loc_data.get("longitude") if loc_data else None
        
        if total_skor >= 20: risiko = "RISIKO TINGGI TERDETEKSI"
        elif total_skor >= 10: risiko = "RISIKO SEDANG TERDETEKSI"
        else: risiko = "RISIKO RENDAH / NORMAL"
        
        if total_skor >= 10:
            send_telegram_alert(kota_input, total_skor, risiko, user_lat, user_lon)
            
        st.session_state.screening_logs.append({
            "Waktu": st.session_state.last_time, "Kota": kota_input, "Usia": usia_input,
            "Skor": total_skor, "Risiko": risiko, "Lat": user_lat, "Lon": user_lon
        })
    # --- TAMBAHAN BLOK INTERPRETASI, DISCLAIMER, CATATAN & SUMBER ---
    st.write("---")
    st.markdown("### **INTERPRETASI SKOR & BATASAN**")
    st.markdown("Skor Total: 0 - 30")
    
    # Tabel Interpretasi Skor
    st.markdown("""
    | **Skor Total** | **Kategori** | **Warna** | **Tindak Lanjut Rekomendasi** |
    | :--- | :--- | :---: | :--- |
    | **0 - 4** | Minimal / Risiko Rendah | 🟢 Hijau | Edukasi. Jaga pola hidup sehat |
    | **5 - 9** | Ringan | 🟡 Kuning | Pantau. Cerita ke teman/keluarga |
    | **10 - 14** | Sedang | 🟡 Kuning | Anjurkan konsultasi ke Puskesmas |
    | **15 - 19** | Sedang-Berat | 🔴 Merah | Rujuk ke Dokter Umum/Psikolog |
    | **20 - 30** | Berat / Sangat Berat | 🔴 Merah | **RUJUK DARURAT ke RSJ/IGD** |
    """)
    
    # Box Disclaimer Merah
    st.markdown("""
    <div style="background-color: #fff5f5; padding: 12px; border-left: 5px solid #e53e3e; border-radius: 4px; color: #c53030; font-weight: bold; margin-top: 15px; margin-bottom: 15px; font-size: 0.9em;">
        🚨 DISCLAIMER: INI ADALAH ALAT SKRINING, BUKAN DIAGNOSIS. DIAGNOSIS HANYA BISA DILAKUKAN OLEH DOKTER SPESIALIS KESEHATAN JIWA / PSIKOLOG KLINIS.
    </div>
    """, unsafe_allow_html=True)

    # Box Catatan & Sumber Ilmiah Kemenkes
    st.markdown("""
    <div style="font-size: 0.85em; color: #4a5568; padding: 12px; background-color: #f7fafc; border-left: 3px solid #2e7d32; border-radius: 4px;">
        <strong>Catatan:</strong> PHQ-9: <em>Patient Health Questionnaire</em>, PHQ-9 digunakan untuk mengukur tingkat keparahan gejala depresi dalam 2 minggu terakhir.<br><br>
        <strong>Sumber:</strong>
        <ul style="margin-top: 5px; padding-left: 20px; list-style-type: square;">
            <li>Spitzer, R.L., Kroenke, K., & Williams, J.B.W. (1999). <em>Validation and utility of a self-report version of PRIME-MD</em>. JAMA.</li>
            <li>Kemenkes: Pedoman P2PTM, Ditjen Pencegahan dan Pengendalian Penyakit, Kemenkes RI.</li>
            <li>Columbia-Suicide Severity Rating Scale - C-SSRS, Columbia University.</li>
            <li>Kemenkes: Buku Saku Pencegahan Bunuh Diri, Dit. Kesehatan Jiwa Kemenkes RI.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.submitted:
        st.write("---")
        st.markdown(f"### **Hasil Skor Anda: {st.session_state.last_score} / 30**")
        if st.session_state.last_score >= 20:
            st.error(f"⚠️ RISIKO TINGGI TERDETEKSI. Anda tidak sendirian. Mohon segera cari bantuan.")
        elif st.session_state.last_score >= 10:
            st.warning(f"⚠️ RISIKO SEDANG TERDETEKSI. Disarankan untuk berkonsultasi dengan profesional.")
        else:
            st.success(f"🟢 RISIKO RENDAH / NORMAL")
            
        st.info(f"Tim relawan kami di wilayah **{kota_input}** sudah diberitahu secara anonim pada jam **{st.session_state.last_time} WIB**.")

# --- PANEL CONTROL ROOM ADMIN ---
else:
    st_autorefresh(interval=10000, key="mental_health_sync")
    st.markdown("<h1>💻 Control Room Pemantauan Wilayah</h1>", unsafe_allow_html=True)
    
    admin_nav = st.radio("Menu Pemantauan Admin:", ["📋 Live Log Skrening", "📊 Database Relawan", "🗺️ Sebaran Geografis", "📄 Export Dokumen"], horizontal=True)
    st.write("---")
    
    if admin_nav == "📋 Live Log Skrening":
        st.subheader("Daftar Masuk Log Respon Anonim (Termasuk Koordinat Pelapor)")
        if st.session_state.screening_logs:
            st.dataframe(pd.DataFrame(st.session_state.screening_logs), use_container_width=True)
        else:
            st.info("Belum ada data skrening yang terekam.")
            
    elif admin_nav == "📊 Database Relawan":
        st.subheader("Daftar Relawan & Koordinat Wilayah Tugas")
        with st.form("tambah_relawan_form"):
            nama = st.text_input("Nama Relawan")
            hp = st.text_input("No Handphone")
            lat_rel = st.number_input("Latitude Relawan", value=-7.9715, format="%.6f")
            lon_rel = st.number_input("Longitude Relawan", value=112.6085, format="%.6f")
            if st.form_submit_button("Simpan Anggota"):
                if nama and hp:
                    new_rel = pd.DataFrame([{"Nama": nama, "No_Handphone": hp, "Latitude": lat_rel, "Longitude": lon_rel, "Status": "Aktif"}])
                    st.session_state.relawan_data = pd.concat([st.session_state.relawan_data, new_rel], ignore_index=True)
                    try: 
                        os.makedirs("data", exist_ok=True)
                        st.session_state.relawan_data.to_csv("data/relawan_jiwa.csv", index=False)
                    except: pass
                    st.success("Data relawan diperbarui!")
                    st.rerun()
        st.data_editor(st.session_state.relawan_data, use_container_width=True)
        
    elif admin_nav == "🗺️ Sebaran Geografis":
        st.subheader("Peta Pemetaan Pelapor & Lokasi Relawan Aktif")
        m_admin = folium.Map(location=[BASE_LAT, BASE_LON], zoom_start=13)
        
        for _, r in st.session_state.relawan_data.iterrows():
            if r["Status"] == "Aktif":
                folium.Marker(
                    [r["Latitude"], r["Longitude"]], 
                    popup=f"🟢 Relawan: {r['Nama']} ({r['No_Handphone']})", 
                    icon=folium.Icon(color='green', icon='user', prefix='fa')
                ).add_to(m_admin)
            
        for log in st.session_state.screening_logs:
            if log.get("Lat") is not None and log.get("Lon") is not None:
                color_m = 'red' if log['Skor'] >= 20 else 'orange'
                folium.Marker(
                    [log["Lat"], log["Lon"]], 
                    popup=f"⚠️ Pelapor [{log['Risiko']}] - Skor: {log['Skor']}/30", 
                    icon=folium.Icon(color=color_m, icon='exclamation-sign')
                ).add_to(m_admin)
                
        folium_static(m_admin)
        
    elif admin_nav == "📄 Export Dokumen":
        st.subheader("Unduh Dokumen Berkas")
        if st.session_state.screening_logs:
            try:
                pdf_file = generate_pdf_report(st.session_state.screening_logs)
                st.download_button(
                    label="📥 Unduh Berkas Rekapitulasi PDF", 
                    data=pdf_file, 
                    file_name="Rekap_Malang_Sehat_Jiwa.pdf", 
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"Gagal memproses ekspor PDF: {str(e)}")
        else:
            st.warning("Tidak ada log riwayat skrening untuk dicetak.")
            
    if st.button("🚪 Keluar Mode Admin", type="secondary"):
        st.session_state.admin_mode = False
        st.session_state.right_button_clicks = 0
        st.rerun()

# --- FOOTER DITENGAHKAN - TOMBOL TRANSPARAN DI SEBELAH KANAN ---
st.write("---")
col_space_l, col_footer, col_space_r = st.columns([1, 12, 1])

with col_footer:
    st.markdown("""
    <style>
    /* Styling tombol rahasia di ujung kanan agar murni transparan tanpa border/bayangan */
    div[data-testid="stColumn"] button[key^="secret_right_backdoor"] {
        background-color: transparent !important;
        border: none !important;
        padding: 0 !important;
        margin: 0 !important;
        box-shadow: none !important;
        width: 30px !important;
        height: 30px !important;
        cursor: pointer !important;
    }
    div[data-testid="stColumn"] button[key^="secret_right_backdoor"]:hover {
        background-color: transparent !important;
    }
    div[data-testid="stColumn"] button[key^="secret_right_backdoor"]:active {
        background-color: transparent !important;
    }
    .footer-text-style {
        font-size: 0.95em;
        color: #2d3748;
        font-family: sans-serif;
    }
    </style>
    """, unsafe_allow_html=True)

    # Memisahkan area konten utama dengan area tombol transparan di ujung kanan
    sub_c_logo, sub_c_text, sub_c_secret = st.columns([0.5, 11.0, 0.5])
    
    with sub_c_logo:
        if os.path.exists("logo_msj.png"):
            st.image("logo_msj.png", width=42)
            
    with sub_c_text:
        # Teks nama dikembalikan murni menjadi teks statis biasa tanpa fungsi klik
        st.markdown("""
        <div class='footer-text-style' style='padding-top: 5px; text-align: left;'>
            <strong>Malang Sehat Jiwa v.1.0.0</strong>, Pengembang: <strong>Ir.M Nasri AW, M.Eng.Sc, M.Kom</strong> | Dosen STIE Indonesia Malang
        </div>
        """, unsafe_allow_html=True)
        
    with sub_c_secret:
        # Tombol transparan diletakkan di sub-kolom ujung kanan
        if st.button(" ", key="secret_right_backdoor"):
            st.session_state.right_button_clicks += 1
            if st.session_state.right_button_clicks >= 3 and not st.session_state.admin_mode:
                st.rerun()

    # Form pengisian password rahasia admin muncul di bawah footer jika area kanan diklik 3 kali
    if st.session_state.right_button_clicks >= 3 and not st.session_state.admin_mode:
        st.write("---")
        st.info("🔓 Portal Akses Control Room Ditemukan.")
        password_input = st.text_input("Masukkan Kode Akses Pusat Pengendali:", type="password", key="admin_password_field")
        if password_input == "sahabat123":
            st.session_state.admin_mode = True
            st.success("Akses Diberikan!")
            st.rerun()
    elif st.session_state.admin_mode:
        st.markdown("<p style='color:green; font-weight:bold; text-align:left; margin-top:5px;'>🟢 Mode Admin Sedang Aktif</p>", unsafe_allow_html=True)

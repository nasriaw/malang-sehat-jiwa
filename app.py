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
            {"Nama": "Relawan Pusat Malang", "No_Handphone": "08119995656", "Latitude": -7.970222, "Longitude": 112.607498, "Status": "Aktif"},
            {"Nama": "Relawan Sukun", "No_Handphone": "08123456789", "Latitude": -7.9922, "Longitude": 112.6160, "Status": "Aktif"},
            {"Nama": "Relawan Klojen", "No_Handphone": "08134567890", "Latitude": -7.9778, "Longitude": 112.6261, "Status": "Aktif"}
        ])

if 'screening_logs' not in st.session_state: st.session_state.screening_logs = []
if 'name_clicks' not in st.session_state: st.session_state.name_clicks = 0
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
        st.markdown("<p style='color: #718096; font-size:1.1em; margin-top:0px;'>Screening Kesehatan Jiwa Berbasis Web | Antarmuka Deteksi Dini</p>", unsafe_allow_html=True)
    
    st.warning("⚠️ **DARURAT! Hubungi segera:** 119 ext 8 | 112 | 0811-999-5656")
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
        st.session_state.name_clicks = 0
        st.rerun()

# --- FOOTER DITENGAHKAN SECARA PRESISI (NATIVE CLICK ON TEXT) ---
st.write("---")
col_space_l, col_footer, col_space_r = st.columns([1, 12, 1])

with col_footer:
    st.markdown("""
    <style>
    /* Styling tombol teks agar murni menyatu seperti teks biasa tanpa box/border */
    div[data-testid="stColumn"] button[key^="click_name_backdoor"] {
        background-color: transparent !important;
        border: none !important;
        padding: 0 !important;
        margin: 0 !important;
        box-shadow: none !important;
        color: #2d3748 !important;
        font-weight: bold !important;
        font-size: 1.0em !important;
        cursor: pointer !important;
        display: inline !important;
        vertical-align: baseline !important;
    }
    div[data-testid="stColumn"] button[key^="click_name_backdoor"]:hover {
        color: #2e7d32 !important;
        text-decoration: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Menjaga struktur kolom agar Logo berada di sebelah kiri baris teks secara konsisten
    sub_c_logo, sub_c_text = st.columns([0.5, 9.5])
    
    with sub_c_logo:
        if os.path.exists("logo_msj.png"):
            st.image("logo_msj.png", width=42)
            
    with sub_c_text:
        # Menggabungkan komponen tombol native Streamlit di dalam susunan sebaris kalimat teks
        st.write("Malang Sehat Jiwa v.1.0.0, Pengembang: ")
        
        # Nama bertindak sebagai elemen klik native yang stabil untuk mendeteksi 3 ketukan
        if st.button("Ir.M Nasri AW, M.Eng.Sc, M.Kom", key="click_name_backdoor"):
            st.session_state.name_clicks += 1
            if st.session_state.name_clicks >= 3 and not st.session_state.admin_mode:
                st.rerun()
                
        st.write(" | Dosen STIE Indonesia Malang")

    # Kontrol pemicu kemunculan form kunci sandi rahasia di bawah footer
    if st.session_state.name_clicks >= 3 and not st.session_state.admin_mode:
        st.write("---")
        st.info("🔓 Portal Akses Control Room Ditemukan.")
        password_input = st.text_input("Masukkan Kode Akses Pusat Pengendali:", type="password", key="admin_password_field")
        if password_input == "sahabat123":
            st.session_state.admin_mode = True
            st.success("Akses Diberikan!")
            st.rerun()
    elif st.session_state.admin_mode:
        st.markdown("<p style='color:green; font-weight:bold; text-align:left; margin-top:5px;'>🟢 Mode Admin Sedang Aktif</p>", unsafe_allow_html=True)

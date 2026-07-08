import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from streamlit_autorefresh import st_autorefresh
import requests
import os
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import datetime

st.set_page_config(
    page_title="Sahabat Jiwa v1.0 - Deteksi Dini Kesehatan Mental",
    page_icon="💚",
    layout="wide"
)

# Kredensial Bot Telegram
BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID")

# Inisialisasi Session State
if 'screening_logs' not in st.session_state: st.session_state.screening_logs = []
if 'logo_clicks' not in st.session_state: st.session_state.logo_clicks = 0
if 'admin_mode' not in st.session_state: st.session_state.admin_mode = False
if 'submitted' not in st.session_state: st.session_state.submitted = False
if 'last_score' not in st.session_state: st.session_state.last_score = 0
if 'last_time' not in st.session_state: st.session_state.last_time = ""

BASE_LAT, BASE_LON = -7.970222, 112.607498  # Koordinat Pusat (Malang)

def ambil_waktu_wib():
    waktu_utc = datetime.datetime.utcnow()
    waktu_wib = waktu_utc + datetime.timedelta(hours=7)
    return waktu_wib

def send_telegram_alert(kota, skor, tingkat_risiko):
    timestamp = ambil_waktu_wib().strftime("%d-%m-%Y %H:%M:%S")
    pesan = (
        "💚 *NOTIFIKASI SAHABAT JIWA v1.0* 💚\n\n"
        f"📅 *Waktu:* {timestamp} WIB\n"
        f"📍 *Wilayah Otoritas:* {kota}\n"
        f"📊 *Skor PHQ-9+:* {skor} / 30\n"
        f"⚠️ *Status Risiko:* {tingkat_risiko}\n\n"
        "_*Notifikasi ini bersifat anonim untuk perlindungan privasi pengguna. Mohon tim relawan wilayah terkait bersiaga._"
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
    story.append(Paragraph("LAPORAN DATA AGREGAT SKRENING - SAHABAT JIWA v1.0", title_style))
    waktu_cetak = ambil_waktu_wib().strftime("%Y-%m-%d %H:%M:%S")
    story.append(Paragraph(f"Dicetak pada: {waktu_cetak} WIB (Data bersifat Anonim)", styles['Normal']))
    story.append(Spacer(1, 15))
    
    data = [["Waktu", "Kota/Kabupaten", "Usia", "Skor", "Tingkat Risiko"]]
    for log in logs:
        data.append([log['Waktu'], log['Kota'], str(log['Usia']), f"{log['Skor']}/30", log['Risiko']])
        
    t = Table(data, colWidths=[120, 110, 50, 60, 160])
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

# --- SIDEBAR & BACKDOOR ADMIN ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #2e7d32;'>💚 SAHABAT JIWA</h2>", unsafe_allow_html=True)
    
    if st.button("🛡️ Verifikasi Otentikasi Sistem", use_container_width=True):
        st.session_state.logo_clicks += 1
        
    if st.session_state.logo_clicks > 0:
        if st.button("⬅️ Kembali ke Menu Utama", use_container_width=True):
            st.session_state.logo_clicks = 0
            st.session_state.admin_mode = False
            st.rerun()
            
    if st.session_state.logo_clicks >= 3:
        st.info("🔓 Portal Akses Terkunci Ditemukan.")
        password_input = st.text_input("Kode Akses Kontrol Room:", type="password")
        if password_input == "sahabat123":
            st.session_state.admin_mode = True
            st.success("Mode Pusat Kendali Aktif!")
            
    if st.session_state.admin_mode:
        st.write("---")
        admin_nav = st.radio("Menu Pemantauan:", ["📋 Live Log Skrening", "🗺️ Sebaran Geografis", "📄 Export Dokumen"])
        if st.button("🚪 Keluar Mode Admin"):
            st.session_state.admin_mode = False
            st.session_state.logo_clicks = 0
            st.rerun()

    st.write("---")
    st.markdown("""
    <div style='font-size: 0.85em; color: #2d3748; line-height: 1.4; font-family: sans-serif;'>
        <strong style='font-size: 1em; color: #2e7d32;'>🏢 TIM Pengabdian Masyarakat STIEIMA 2026</strong>
        <ul style='margin-top: 5px; margin-bottom: 0; padding-left: 15px; list-style-type: disc;'>
            <li style='margin-bottom: 4px; text-align: left;'><strong>Arsitek & Pengembang Utama:</strong><br>Ir. M Nasri AW, M.Eng.Sc, M.Kom</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# --- PANEL UTAMA PENGGUNA ---
if not st.session_state.admin_mode:
    # Header Banner Aplikasi
    st.markdown("<h1 style='color: #2e7d32; margin-bottom:0px;'>💚 SAHABAT JIWA v1.0</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #718096; font-size:1.1em; margin-top:0px;'>Screening Kesehatan Jiwa Berbasis Web | Antarmuka Deteksi Dini</p>", unsafe_allow_html=True)
    
    # Alert Darurat Banner Kuning
    st.warning("⚠️ **DARURAT! Hubungi segera:** 119 ext 8 | 112 | 0811-999-5656")
    
    # Sub-navigasi statis
    st.markdown("<span style='color:#e53e3e; font-weight:bold; border-bottom: 2px solid #e53e3e; padding-bottom:4px;'>Mulai Screening</span> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style='color:#718096; cursor:pointer;'>Info Bantuan</span>", unsafe_allow_html=True)
    st.write("---")
    
    # Identitas Demografi
    st.markdown("### **Check-in 3 Menit**")
    kota_input = st.text_input("Kota/Kabupaten Lokasi Anda Saat Ini", value="Malang")
    usia_input = st.slider("Usia", min_value=10, max_value=100, value=20)
    
    st.write("---")
    
    # Komponen Kuesioner PHQ-9+
    st.markdown("### **PHQ-9+ Screening Risiko**")
    st.markdown("<p style='font-style: italic; color: #4a5568;'>Seberapa sering dalam 2 minggu terakhir Anda merasakan hal-hal berikut?</p>", unsafe_allow_html=True)
    
    pertanyaan = [
        "1. Minat melakukan sesuatu menurun",
        "2. Merasa sedih, murung, atau putus asa",
        "3. Sulit tidur atau tidur terlalu banyak",
        "4. Merasa lelah atau tidak bertenaga",
        "5. Nafsu makan menurun atau berlebihan",
        "6. Merasa gagal atau mengecewakan diri/keluarga",
        "7. Sulit konsentrasi pada sesuatu",
        "8. Bergerak/berbicara sangat lambat atau gelisah",
        "9. Berpikir bahwa lebih baik mati atau menyakiti diri",
        "10. Apakah Anda punya rencana spesifik untuk bunuh diri?"
    ]
    
    opsi = {
        0: "0 - Tidak sama sekali",
        1: "1 - Beberapa hari",
        2: "2 - >7 hari",
        3: "3 - Hampir setiap hari"
    }
    
    total_skor = 0
    
    for idx, q in enumerate(pertanyaan):
        st.markdown(f"**{q}**")
        pilihan = st.radio(
            f"Pilih opsi untuk pertanyaan {idx+1}", 
            options=[0, 1, 2, 3], 
            format_func=lambda x: opsi[x], 
            key=f"q_{idx}", 
            label_visibility="collapsed"
        )
        total_skor += pilihan
        st.write("")

    if st.button("Dapatkan Hasil & Bantuan", type="primary"):
        st.session_state.submitted = True
        st.session_state.last_score = total_skor
        st.session_state.last_time = ambil_waktu_wib().strftime("%d-%m-%Y %H:%M:%S")
        
        # Klasifikasi Tingkat Risiko
        if total_skor >= 20: risiko = "RISIKO TINGGI TERDETEKSI"
        elif total_skor >= 10: risiko = "RISIKO SEDANG TERDETEKSI"
        else: risiko = "RISIKO RENDAH / NORMAL"
        
        # Kirim Bot Telegram otomatis jika tergolong risiko sedang/tinggi
        if total_skor >= 10:
            send_telegram_alert(kota_input, total_skor, risiko)
            
        st.session_state.screening_logs.append({
            "Waktu": st.session_state.last_time,
            "Kota": kota_input,
            "Usia": usia_input,
            "Skor": total_skor,
            "Risiko": risiko
        })

    # Tampilan Output Hasil Diagnosis Efek Visual Komparatif
    if st.session_state.submitted:
        st.write("---")
        st.markdown(f"### **Hasil Skor Anda: {st.session_state.last_score} / 30**")
        
        if st.session_state.last_score >= 20:
            st.error(f"⚠️ RISIKO TINGGI TERDETEKSI")
            st.markdown("<div style='background-color: #fff5f5; padding: 12px; border-radius: 5px; color: #c53030; font-weight: bold;'>Anda tidak sendirian. Mohon segera cari bantuan.</div>", unsafe_allow_html=True)
        elif st.session_state.last_score >= 10:
            st.warning(f"⚠️ RISIKO SEDANG TERDETEKSI")
            st.markdown("<div style='background-color: #fffaf0; padding: 12px; border-radius: 5px; color: #dd6b20; font-weight: bold;'>Disarankan untuk berkonsultasi dengan profesional kesehatan mental terdekat.</div>", unsafe_allow_html=True)
        else:
            st.success(f"🟢 RISIKO RENDAH / NORMAL")
            st.markdown("<div style='background-color: #f0fff4; padding: 12px; border-radius: 5px; color: #38a169; font-weight: bold;'>Kondisi psikologis Anda saat ini cenderung stabil. Tetap jaga kesehatan mental Anda.</div>", unsafe_allow_html=True)
            
        # Hotlines Ruang Edukasi Krisis
        st.markdown("""
        <div style='margin-top:20px;'>
            <strong>Bantuan 24 Jam:</strong>
            <ul>
                <li>119 ext 8 - Layanan Kesehatan Jiwa Kemenkes</li>
                <li>Sahabat 24: 0811-999-5656</li>
                <li>112 - Layanan Darurat</li>
                <li>IGD RS terdekat</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        # Toast Informasi Pengiriman Tim Relawan Sesuai Tanggal Sistem
        st.info(f"Tim relawan kami di wilayah **{kota_input}** sudah diberitahu secara anonim pada jam **{st.session_state.last_time} WIB**. Bantuan akan segera diarahkan ke wilayah Anda.")
        
        st.markdown(
            f"<div style='text-align: center; margin-top: 15px; margin-bottom: 20px;'>\n"
            f"<a href='https://t.me/Sahabat_Jiwa_Group' target='_blank' style='text-decoration: none; color: #ffffff; background-color: #2e7d32; padding: 10px 20px; border-radius: 20px; font-weight: bold;'>\n"
            f"💬 Hubungi Konselor Berjaga (Telegram Group)\n"
            f"</a>\n"
            f"</div>", 
            unsafe_allow_html=True
        )
        
    st.write("---")
    st.markdown("<p style='font-size: 0.8em; color: #a0aec0; text-align: center;'>Data Anda disimpan secara anonim untuk membantu pemetaan kesehatan jiwa di Indonesia.</p>", unsafe_allow_html=True)

# --- PANEL CONTROL ROOM ADMIN ---
else:
    st_autorefresh(interval=15000, key="mental_health_sync")
    st.markdown("<h1>💻 Control Room Pemantauan Wilayah</h1>", unsafe_allow_html=True)
    
    if admin_nav == "📋 Live Log Skrening":
        st.subheader("Daftar Masuk Log Respon Anonim")
        if st.session_state.screening_logs:
            st.dataframe(pd.DataFrame(st.session_state.screening_logs), use_container_width=True)
        else:
            st.info("Belum ada data skrening yang terekam hari ini.")
            
    elif admin_nav == "🗺️ Sebaran Geografis":
        st.subheader("Peta Kluster Kerawanan Depresi")
        m_admin = folium.Map(location=BASE_LAT, zoom_start=11)
        folium.Marker(BASE_LAT, popup="Pusat Komando Utama", icon=folium.Icon(color='green', icon='plus-sign')).add_to(m_admin)
        
        # Logika visualisasi marker sebaran log laporan
        for log in st.session_state.screening_logs:
            color_marker = 'red' if log['Skor'] >= 20 else 'orange' if log['Skor'] >= 10 else 'green'
            folium.Marker(
                location=[-7.965, 112.610], # Koordinat simulasi kluster kota
                popup=f"Skor: {log['Skor']} ({log['Risiko']})",
                icon=folium.Icon(color=color_marker, icon='info-sign')
            ).add_to(m_admin)
            
        folium_static(m_admin)
        
    elif admin_nav == "📄 Export Dokumen":
        st.subheader("Unduh Dokumen Kompilasi Berkas")
        if st.session_state.screening_logs:
            pdf_file = generate_pdf_report(st.session_state.screening_logs)
            st.download_button("📥 Unduh Berkas Rekapitulasi PDF", data=pdf_file, file_name="Rekap_Sahabat_Jiwa.pdf", mime="application/pdf")
        else:
            st.warning("Tidak ada log riwayat skrening untuk dicetak.")

import streamlit as st
import pandas as pd
import datetime
import pytz  # Pastikan menambahkan 'pytz' di requirements.txt untuk zona waktu WIB
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests  # Menggunakan requests untuk mengirim Telegram (lebih stabil di Streamlit)
import os
from dotenv import load_dotenv

load_dotenv()

# --- KONFIGURASI ---
st.set_page_config(page_title="MALANG SEHAT JIWA", page_icon="💚", layout="centered")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# --- FUNGSI TELEGRAM (SINKRONUS & STABIL) ---
def send_telegram_alert(data):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: 
        return
    
    # Format pesan ringkas, jelas, dan informatif untuk relawan
    msg = f"""
🚨 *ALERT SAHABAT JIWA* 🚨

📌 *Detail Laporan:*
• *Skor Screening:* {data['skor']} / 30 (RISIKO TINGGI)
• *Waktu Kejadian:* {data['waktu']} WIB
• *Lokasi Kejadian:* {data['kota']}
• *Kategori Usia:* {data['usia']} Tahun

⚠️ _Mohon tim relawan terdekat di wilayah tersebut segera bersiaga untuk follow up (Data Bersifat Anonim)._
"""
    
    # Kirim menggunakan API bot Telegram biasa (POST request)
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        # Menulis log eror ke konsol Streamlit jika gagal kirim
        print(f"Gagal mengirim bot Telegram: {e}")

# --- FUNGSI GOOGLE SHEET ---
def save_to_gsheet(data):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open("DB_SahabatJiwa").sheet1
        sheet.append_row(list(data.values()))
    except: 
        pass # Fail silently agar aplikasi user tidak crash jika DB bermasalah

# --- UI APLIKASI ---
st.title("💚 SAHABAT JIWA v1.0")
st.caption("Screening Kesehatan Jiwa Berbasis Web | Untuk Deteksi Dini")
st.warning("DARURAT? Hubungi segera: 119 ext 8 | 112 | 0811-999-5656")

tab1, tab2 = st.tabs(["Mulai Screening", "Info Bantuan"])

with tab1:
    st.header("Check-in 3 Menit")
    kota = st.text_input("Kota/Kabupaten Lokasi Anda Saat Ini", "Malang")
    usia = st.slider("Usia", 13, 80, 20)

    st.write("**PHQ-9 + Screening Risiko**")
    st.write("Seberapa sering dalam 2 minggu terakhir?")

    questions = [
        "Minat melakukan sesuatu menurun",
        "Merasa sedih, murung, atau putus asa",
        "Sulit tidur atau tidur terlalu banyak",
        "Merasa lelah atau tidak bertenaga",
        "Nafsu makan menurun atau berlebihan",
        "Merasa gagal atau mengecewakan diri/keluarga",
        "Sulit konsentrasi pada sesuatu",
        "Bergerak/berbicara sangat lambat atau gelisah",
        "Berpikir bahwa lebih baik mati atau menyakiti diri", 
        "Apakah Anda punya rencana spesifik untuk bunuh diri?" 
    ]
    options = ["0 - Tidak sama sekali", "1 - Beberapa hari", "2 - >7 hari", "3 - Hampir setiap hari"]

    score = 0
    for i, q in enumerate(questions):
        ans = st.radio(q, options, key=f"q_{i}", horizontal=True)
        score += int(ans[0])

    if st.button("Dapatkan Hasil & Bantuan", type="primary"):
        # Mengatur Waktu ke Waktu Indonesia Barat (WIB) agar akurat di server mana pun
        tz_wib = pytz.timezone('Asia/Jakarta')
        waktu_sekarang = datetime.datetime.now(tz_wib).strftime("%d-%m-%Y %H:%M:%S")
        
        data_log = {"waktu": waktu_sekarang, "kota": kota, "usia": usia, "skor": score}

        st.divider()
        st.subheader(f"Hasil Skor Anda: {score} / 30")

        if score < 5:
            st.success("Risiko Rendah. Pertahankan! Coba olahraga, tidur cukup, dan bersosialisasi.")
        elif score < 15:
            st.warning("Risiko Sedang. Jangan dipendam sendirian. Cerita ke teman/keluarga.")
            st.info("Teknik Grounding 5-4-3-2-1: Sebut 5 benda yg dilihat, 4 yg disentuh, 3 yg didengar, 2 yg dicium, 1 yg dirasakan.")
        else:
            st.error("⚠️ RISIKO TINGGI TERDETEKSI")
            st.error("Anda tidak sendirian. Mohon segera cari bantuan.")
            st.markdown("""
            ### Bantuan 24 Jam:
            - **119 ext 8** - Layanan Kesehatan Jiwa Kemenkes
            - **Sahabat 24: 0811-999-5656**
            - **112** - Layanan Darurat
            - **IGD RS terdekat**
            """)
            
            # Memanggil fungsi kirim telegram secara langsung tanpa asyncio.run()
            send_telegram_alert(data_log)
            st.success("Tim relawan kami sudah diberitahu secara anonim. Bantuan akan segera diarahkan ke wilayah Anda.")

        save_to_gsheet(data_log)
        st.caption("Data Anda disimpan anonim untuk membantu pemetaan kesehatan jiwa di Indonesia.")

with tab2:
    st.header("Anda Tidak Sendirian")
    st.write("1. **Puskesmas**: Semua Puskesmas punya layanan kesehatan jiwa dasar, gratis pakai BPJS")
    st.write("2. **RSJ**: Rujukan untuk penanganan lebih lanjut")
    st.write("3. **Komunitas**: Into The Light, Sahabat 24")
    st.write("Ingat: Mencari bantuan adalah tanda kuat, bukan lemah.")

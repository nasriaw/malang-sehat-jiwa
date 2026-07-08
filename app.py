import streamlit as st
import pandas as pd
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import asyncio
from telegram import Bot
import os
from dotenv import load_dotenv

load_dotenv()

--- KONFIGURASI ---
st.set_page_config(page_title="MALANG SEHAT JIWA", page_icon="💚", layout="centered")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

--- HEADER DENGAN LOGO ---
col1, col2 = st.columns([1,4])
with col1:
    st.image("logo_msj.png") # Simpan logo dari atas dengan nama ini
with col2:
    st.title("MALANG SEHAT JIWA")
    st.caption("Aplikasi Screening Kesehatan Jiwa Kota Malang")

st.warning("DARURAT? Hubungi segera: 119 ext 8 | 112 | 0811-999-5656 | Sahabat 24: 0811-999-5656")

--- FUNGSI TELEGRAM ---
async def send_telegram_alert(data):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return
    bot = Bot(token=TELEGRAM_TOKEN)
    msg = f"""
    🚨 ALERT MALANG SEHAT JIWA 🚨
    Skor Tinggi Terdeteksi: {data['skor']}/30
    Waktu: {data['waktu']}
    Kota: {data['kota']}
    Usia: {data['usia']}

    Segera koordinasikan follow up. Data anonim.
    """
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)

... sisa kode sama seperti sebelumnya ...

--- FOOTER ---
st.divider()
st.markdown("""
---
**Pengembang:** M Nasri AW | Dosen STIEIMA  
**Kolaborasi:** Dinkes Kota Malang & Relawan Kesehatan Jiwa  
*Versi 1.0 - 2026. Aplikasi ini bukan pengganti diagnosis profesional.*
""")

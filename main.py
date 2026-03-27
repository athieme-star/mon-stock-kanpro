import streamlit as st
import requests
import base64
from PIL import Image
import io

# --- 1. CONFIGURATION ---
try:
    API_KEY = st.secrets["google"]["api_key"]
except:
    st.error("❌ CLÉ API MANQUANTE")
    st.stop()

FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdsdTn7Rgp2ujd6jAQkd5bqDLPVcHdwMxTLgy0j4e1ZUODqLw/formResponse"

st.title("📦 Scanner Kanpro v7.0")

# Initialisation de la mémoire (Session State)
if 'item' not in st.session_state: st.session_state.item = ""
if 'type' not in st.session_state: st.session_state.type = ""
if 'serial' not in st.session_state: st.session_state.serial = ""

photo = st.file_uploader("📸 SCANNER L'ÉTIQUETTE", type=['jpg', 'jpeg', 'png'])

if photo is not None:
    image = Image.open(photo)
    image.thumbnail((1000, 1000)) 
    st.image(image, use_container_width=True)

    if st.button("🔍 1. ANALYSER L'IMAGE"):
        try:
            buffered = io.BytesIO()
            image.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            api_url = f"https://vision.googleapis.com/v1/images:annotate?key={API_KEY}"
            payload = {"requests": [{"image": {"content": img_str}, "features": [{"type": "TEXT_DETECTION"}, {"type": "BARCODE_DETECTION"}]}]}
            
            with st.spinner("L'IA travaille..."):
                res = requests.post(api_url, json=payload, timeout=20)
                data = res.json()

            # --- EXTRACTION ET MISE EN MÉMOIRE ---
            codes = []
            if 'responses' in data and 'barcodeAnnotations' in data['responses'][0]:
                codes = [b.get('rawValue', '') for b in data['responses'][0]['barcodeAnnotations']]
            
            txt = ""
            if 'responses' in data and 'textAnnotations' in data['responses'][0]:
                txt = data['responses'][0]['textAnnotations'][0]['description']
            
            # On stocke dans la mémoire de l'appli
            st.session_state.item = codes[0] if len(codes) > 0 else (txt.split('\n')[0] if txt else "")
            st.session_state.serial = codes[1] if len(codes) > 1 else (txt.split('\n')[2] if len(txt.split('\n')) > 2 else "")
            
            for ligne in txt.split('\n'):
                if "TYPE" in ligne.upper():
                    st.session_state.type = ligne.upper().replace("TYPE", "").strip(": ").strip()
            
            st.success("Analyse terminée ! Regardez les cases ci-dessous.")

        except Exception as e:
            st.error(f"Erreur : {e}")

# --- AFFICHAGE DU FORMULAIRE (Toujours visible) ---
st.divider()
with st.form("form_kanpro"):
    st.write("### 📋 Données à envoyer")
    f_item = st.text_input("📦 Item No", value=st.session_state.item)
    f_type = st.text_input("🏷️ Type", value=st.session_state.type)
    f_serial = st.text_input("🔢 Serial No", value=st.session_state.serial)
    
    if st.form_submit_button("🚀 2. ENVOYER AU SHEET"):
        payload = {
            "entry.460943250": f_item,
            "entry.1132062078": f_type,
            "entry.823872688": f_serial,
            "entry.1220447242": "Scan Final v7"
        }
        requests.post(FORM_URL, data=payload)
        st.balloons()
        st.success("Enregistré !")
        # On vide la mémoire pour le prochain scan
        st.session_state.item = ""; st.session_state.type = ""; st.session_state.serial = ""

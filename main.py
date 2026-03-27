import streamlit as st
import requests
import base64
from PIL import Image
import io
import re

# --- 1. CONFIGURATION ---
try:
    API_KEY = st.secrets["google"]["api_key"]
except:
    st.error("❌ CLÉ API MANQUANTE dans les Secrets Streamlit.")
    st.stop()

# URL de réponse du formulaire (ne pas oublier le /formResponse à la fin)
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdsdTn7Rgp2ujd6jAQkd5bqDLPVcHdwMxTLgy0j4e1ZUODqLw/formResponse"

st.set_page_config(page_title="Scanner Kanpro", page_icon="📦")
st.title("📦 Scanner Kanpro v13.0")

# Mémoire pour conserver les données entre les clics
if 'item' not in st.session_state: st.session_state.item = ""
if 'type' not in st.session_state: st.session_state.type = ""
if 'serial' not in st.session_state: st.session_state.serial = ""

# --- 2. CAPTURE PHOTO ---
photo = st.file_uploader("📸 SCANNER L'ÉTIQUETTE", type=['jpg', 'jpeg', 'png'])

if photo is not None:
    image = Image.open(photo)
    image.thumbnail((1000, 1000)) 
    st.image(image, use_container_width=True)

    if st.button("🔍 ANALYSER L'ÉTIQUETTE"):
        try:
            buffered = io.BytesIO()
            image.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            api_url = f"https://vision.googleapis.com/v1/images:annotate?key={API_KEY}"
            payload = {
                "requests": [{
                    "image": {"content": img_str},
                    "features": [{"type": "TEXT_DETECTION"}]
                }]
            }
            
            with st.spinner("Analyse intelligente en cours..."):
                res = requests.post(api_url, json=payload, timeout=20)
                data = res.json()

            if 'responses' in data and 'textAnnotations' in data['responses'][0]:
                texte_brut = data['responses'][0]['textAnnotations'][0]['description']
                lignes = [l.strip() for l in texte_brut.split('\n') if l.strip()]
                
                # --- LOGIQUE DE TRI PAR SIGNATURE ---
                item_found = ""
                serial_found = ""
                type_found = ""

                for l in lignes:
                    # Format Item No : XXXXXXX.X (7 chiffres, point, 1 chiffre)
                    if re.match(r"^\d{7}\.\d{1}$", l):
                        item_found = l
                    # Format Serial No : 15 chiffres
                    elif re.match(r"^\d{15}$", l):
                        serial_found = l
                    # Format Type : Recherche de la ligne complexe
                    elif "/" in l and "-" in l and len(l) > 8:
                        type_found = l.upper().replace("TYPE", "").strip(": ").strip()

                # Mise à jour de la mémoire
                st.session_state.item = item_found
                st.session_state.type = type_found
                st.session_state.serial = serial_found
                
                st.success("Analyse terminée ! Vérifiez les cases.")
            else:
                st.warning("Aucun texte détecté. Essayez de vous rapprocher.")

        except Exception as e:
            st.error(f"Erreur technique : {e}")

# --- 3. FORMULAIRE D'ENVOI ---
st.divider()
with st.form("form_final"):
    st.subheader("📋 Données détectées")
    
    f_item = st.text_input("📦 Item No (XXXXXXX.X)", value=st.session_state.item)
    f_type = st.text_input("🏷️ Type produit", value=st.session_state.type)
    f_serial = st.text_input("🔢 Serial No (15 chiffres)", value=st.session_state.serial)
    
    submitted = st.form_submit_button("🚀 ENVOYER AU GOOGLE SHEET")
    
    if submitted:
        if not f_item or not f_serial:
            st.warning("⚠️ Attention, certaines cases sont vides.")
            
        # Payload basé sur TES identifiants exacts
        payload = {
            "entry.1132062078": f_item,
            "entry.460943250": f_type,
            "entry.823872688": f_serial,
            "entry.1220447242": "Scan Mobile App v13" # Note automatique
        }
        
        try:
            r = requests.post(FORM_URL, data=payload)
            if r.status_code == 200:
                st.balloons()
                st.success("✅ Enregistré avec succès dans le Google Sheet !")
                # Optionnel : réinitialiser après envoi
                st.session_state.item = ""; st.session_state.type = ""; st.session_state.serial = ""
            else:
                st.error(f"Erreur d'envoi. Code : {r.status_code}")
        except:
            st.error("Impossible de joindre Google Sheets.")

st.caption("Système Kanpro v13.0 - Opérationnel")

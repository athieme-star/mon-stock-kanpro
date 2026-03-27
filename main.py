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

st.title("📦 Scanner Kanpro v8.0")

# Mémoire de session
if 'item' not in st.session_state: st.session_state.item = ""
if 'type' not in st.session_state: st.session_state.type = ""
if 'serial' not in st.session_state: st.session_state.serial = ""

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
            payload = {"requests": [{"image": {"content": img_str}, "features": [{"type": "TEXT_DETECTION"}, {"type": "BARCODE_DETECTION"}]}]}
            
            with st.spinner("Décodage précis..."):
                res = requests.post(api_url, json=payload, timeout=20)
                data = res.json()

            # --- EXTRACTION INTELLIGENTE ---
            # 1. Récupération des codes-barres réels
            codes = []
            if 'responses' in data and 'barcodeAnnotations' in data['responses'][0]:
                codes = [b.get('rawValue', '') for b in data['responses'][0]['barcodeAnnotations']]
            
            # 2. Récupération du texte
            txt_brut = ""
            if 'responses' in data and 'textAnnotations' in data['responses'][0]:
                txt_brut = data['responses'][0]['textAnnotations'][0]['description']
            
            lignes = [l.strip() for l in txt_brut.split('\n') if l.strip()]

            # --- LOGIQUE DE TRI AFFINÉE ---
            # Type : on cherche la ligne qui contient "TYPE"
            type_final = ""
            for l in lignes:
                if "TYPE" in l.upper():
                    type_final = l.upper().replace("TYPE", "").strip(": ").strip()
                    break
            
            # Item No : Priorité au code-barre n°1, sinon ligne n°1 (si pas "Type")
            item_final = ""
            if len(codes) > 0:
                item_final = codes[0]
            elif len(lignes) > 0:
                item_final = lignes[0] if "TYPE" not in lignes[0].upper() else (lignes[1] if len(lignes)>1 else "")

            # Serial No : Priorité au code-barre n°2, sinon une ligne qui ressemble à un serial
            serial_final = ""
            if len(codes) > 1:
                serial_final = codes[1]
            else:
                # On prend la dernière ligne du texte (souvent le serial en bas)
                serial_final = lignes[-1] if len(lignes) > 1 else ""

            # Stockage
            st.session_state.item = item_final
            st.session_state.type = type_final
            st.session_state.serial = serial_final
            
            st.success("Analyse terminée !")

        except Exception as e:
            st.error(f"Erreur : {e}")

# --- FORMULAIRE ---
st.divider()
with st.form("form_v8"):
    f_item = st.text_input("📦 Item No (Code-barre haut/gauche)", value=st.session_state.item)
    f_type = st.text_input("🏷️ Type produit (Après le mot 'Type')", value=st.session_state.type)
    f_serial = st.text_input("🔢 Serial No (Code-barre droite)", value=st.session_state.serial)
    
    if st.form_submit_button("🚀 ENREGISTRER DANS LE SHEET"):
        p = {"entry.460943250": f_item, "entry.1132062078": f_type, "entry.823872688": f_serial, "entry.1220447242": "Scan v8"}
        requests.post(FORM_URL, data=p)
        st.balloons()
        st.success("Données envoyées !")
        st.session_state.item = ""; st.session_state.type = ""; st.session_state.serial = ""

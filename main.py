import streamlit as st
import requests
import base64
from PIL import Image
import io
import re  # Import pour la reconnaissance de formats (Regex)

# --- 1. CONFIGURATION ---
try:
    API_KEY = st.secrets["google"]["api_key"]
except:
    st.error("❌ CLÉ API MANQUANTE")
    st.stop()

FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdsdTn7Rgp2ujd6jAQkd5bqDLPVcHdwMxTLgy0j4e1ZUODqLw/formResponse"

st.title("📦 Scanner Kanpro v12.0 - Signature Numérique")

if 'item' not in st.session_state: st.session_state.item = ""
if 'type' not in st.session_state: st.session_state.type = ""
if 'serial' not in st.session_state: st.session_state.serial = ""

photo = st.file_uploader("📸 SCANNER L'ÉTIQUETTE", type=['jpg', 'jpeg', 'png'])

if photo is not None:
    image = Image.open(photo)
    image.thumbnail((1000, 1000)) 
    st.image(image, use_container_width=True)

    if st.button("🔍 ANALYSE PAR FORMAT"):
        try:
            buffered = io.BytesIO()
            image.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            api_url = f"https://vision.googleapis.com/v1/images:annotate?key={API_KEY}"
            payload = {"requests": [{"image": {"content": img_str}, "features": [{"type": "TEXT_DETECTION"}, {"type": "BARCODE_DETECTION"}]}]}
            
            res = requests.post(api_url, json=payload, timeout=20)
            data = res.json()

            # --- RÉCUPÉRATION GLOBALE ---
            # On mélange codes-barres et texte pour tout analyser
            toutes_les_valeurs = []
            if 'responses' in data and 'barcodeAnnotations' in data['responses'][0]:
                toutes_les_valeurs.extend([b.get('rawValue', '') for b in data['responses'][0]['barcodeAnnotations']])
            
            if 'responses' in data and 'textAnnotations' in data['responses'][0]:
                txt_brut = data['responses'][0]['textAnnotations'][0]['description']
                toutes_les_valeurs.extend(txt_brut.split('\n'))

            # --- FILTRAGE PAR SIGNATURE (REGEX) ---
            item_found = ""
            serial_found = ""
            type_found = ""

            for val in toutes_les_valeurs:
                v = val.strip()
                
                # 1. Format Item No : 7 chiffres + point + 1 chiffre (ex: 1234567.8)
                if re.match(r"^\d{7}\.\d{1}$", v):
                    item_found = v
                
                # 2. Format Serial No : Exactement 15 chiffres
                elif re.match(r"^\d{15}$", v):
                    serial_found = v
                
                # 3. Format Type : Contient des caractères spéciaux de ton exemple
                # On cherche une ligne qui a un "/" et un "-" et qui est assez longue
                elif "/" in v and "-" in v and len(v) > 5:
                    # On nettoie si le mot "TYPE" est resté collé
                    type_found = v.upper().replace("TYPE", "").strip(": ").strip()

            # Mise à jour de la mémoire
            st.session_state.item = item_found
            st.session_state.type = type_found
            st.session_state.serial = serial_found
            
            st.success("Analyse par signature terminée !")

        except Exception as e:
            st.error(f"Erreur : {e}")

# --- FORMULAIRE ---
st.divider()
with st.form("form_v12"):
    f_item = st.text_input("📦 Item No (Format XXXXXXX.X)", value=st.session_state.item)
    f_type = st.text_input("🏷️ Type produit (Format complexe)", value=st.session_state.type)
    f_serial = st.text_input("🔢 Serial No (15 chiffres)", value=st.session_state.serial)
    
    if st.form_submit_button("🚀 ENVOYER AU SHEET"):
        p = {"entry.460943250": f_item, "entry.1132062078": f_type, "entry.823872688": f_serial, "entry.1220447242": "Scan v12"}
        requests.post(FORM_URL, data=p)
        st.balloons()
        st.success("Données envoyées !")
        st.session_state.item = ""; st.session_state.type = ""; st.session_state.serial = ""

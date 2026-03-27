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

st.title("📦 Scanner Kanpro v11.0")

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
            
            res = requests.post(api_url, json=payload, timeout=20)
            data = res.json()

            # --- RÉCUPÉRATION DES DONNÉES ---
            barcodes = []
            if 'responses' in data and 'barcodeAnnotations' in data['responses'][0]:
                barcodes = [b.get('rawValue', '') for b in data['responses'][0]['barcodeAnnotations']]
            
            txt_brut = ""
            if 'responses' in data and 'textAnnotations' in data['responses'][0]:
                txt_brut = data['responses'][0]['textAnnotations'][0]['description']
            
            lignes = [l.strip() for l in txt_brut.split('\n') if l.strip()]

            # --- LOGIQUE DE TRI "NETTOYEUR" ---
            mots_interdits = ["SWEP", "COMPANY", "ITEM", "NO", "MADE IN", "PRODUCT"]
            
            # 1. On filtre les lignes de texte pour ne garder que les "vraies" valeurs
            lignes_propres = []
            for l in lignes:
                if not any(m in l.upper() for m in mots_interdits):
                    lignes_propres.append(l)

            # 2. Attribution TYPE (on cherche la ligne qui contient "TYPE")
            type_val = ""
            for l in lignes:
                if "TYPE" in l.upper():
                    type_val = l.upper().split("TYPE")[-1].strip(": ").strip()
                    break

            # 3. Attribution ITEM NO (Priorité au 1er barcode, sinon 1ère ligne propre)
            item_val = ""
            if len(barcodes) > 0:
                item_val = barcodes[0]
            elif len(lignes_propres) > 0:
                item_val = lignes_propres[0]

            # 4. Attribution SERIAL NO (Priorité au 2e barcode, sinon dernière ligne propre)
            serial_val = ""
            if len(barcodes) > 1:
                serial_val = barcodes[1]
            elif len(lignes_propres) > 1:
                serial_val = lignes_propres[-1]

            # --- MISE À JOUR MÉMOIRE ---
            st.session_state.item = item_val
            st.session_state.type = type_val
            st.session_state.serial = serial_val
            
            st.success("Analyse terminée !")

        except Exception as e:
            st.error(f"Erreur : {e}")

# --- FORMULAIRE ---
st.divider()
with st.form("form_v11"):
    f_item = st.text_input("📦 Item No / Barcode", value=st.session_state.item)
    f_type = st.text_input("🏷️ Type produit", value=st.session_state.type)
    f_serial = st.text_input("🔢 Serial No", value=st.session_state.serial)
    
    if st.form_submit_button("🚀 ENVOYER AU SHEET"):
        p = {"entry.460943250": f_item, "entry.1132062078": f_type, "entry.823872688": f_serial, "entry.1220447242": "Scan v11"}
        requests.post(FORM_URL, data=p)
        st.balloons()
        st.success("Données envoyées !")
        st.session_state.item = ""; st.session_state.type = ""; st.session_state.serial = ""

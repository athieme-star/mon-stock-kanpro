import streamlit as st
import requests
import base64
from PIL import Image
import io

# --- 1. CONFIGURATION ---
try:
    API_KEY = st.secrets["google"]["api_key"]
except:
    st.error("❌ CLÉ API MANQUANTE dans les Secrets.")
    st.stop()

FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdsdTn7Rgp2ujd6jAQkd5bqDLPVcHdwMxTLgy0j4e1ZUODqLw/formResponse"

st.title("📦 Scanner de Stock Kanpro")

# --- 2. CAPTURE ---
photo = st.file_uploader("📸 SCANNER L'ÉTIQUETTE", type=['jpg', 'jpeg', 'png'])

if photo is not None:
    image = Image.open(photo)
    image.thumbnail((1200, 1200)) 
    st.image(image, caption="Photo prête", use_container_width=True)

    if st.button("🔍 ANALYSER ET TRIER"):
        try:
            buffered = io.BytesIO()
            image.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            api_url = f"https://vision.googleapis.com/v1/images:annotate?key={API_KEY}"
            payload = {
                "requests": [{
                    "image": {"content": img_str},
                    "features": [{"type": "TEXT_DETECTION"}, {"type": "BARCODE_DETECTION"}]
                }]
            }
            
            with st.spinner("Tri des données en cours..."):
                res = requests.post(api_url, json=payload, timeout=20)
                data = res.json()

            # --- 3. LOGIQUE DE TRI (LE RANGEMENT) ---
            
            # A. Extraction des Codes-barres
            barcodes = []
            if 'responses' in data and 'barcodeAnnotations' in data['responses'][0]:
                for b in data['responses'][0]['barcodeAnnotations']:
                    barcodes.append(b.get('rawValue', ''))
            
            # On attribue selon ta description : Item No (1er), Serial No (2e)
            item_val = barcodes[0] if len(barcodes) > 0 else ""
            serial_val = barcodes[1] if len(barcodes) > 1 else ""

            # B. Extraction du "Type" dans le texte
            type_val = ""
            if 'responses' in data and 'textAnnotations' in data['responses'][0]:
                texte_brut = data['responses'][0]['textAnnotations'][0]['description']
                for ligne in texte_brut.split('\n'):
                    if "TYPE" in ligne.upper():
                        # On nettoie la ligne pour ne garder que la valeur
                        type_val = ligne.upper().replace("TYPE", "").strip(": ").strip()

            # --- 4. AFFICHAGE DES CHAMPS REMPLIS ---
            st.success("✅ Données extraites !")
            
            with st.form("form_final"):
                col1, col2 = st.columns(2)
                with col1:
                    f_item = st.text_input("📦 Item No / Barcode", value=item_no_val if 'item_no_val' in locals() else item_val)
                    f_type = st.text_input("🏷️ Type produit", value=type_val)
                with col2:
                    f_serial = st.text_input("🔢 Serial No (Unique)", value=serial_val)
                    f_note = st.text_input("📌 Note", value="Scan Mobile OK")

                if st.form_submit_button("🚀 ENVOYER AU GOOGLE SHEET"):
                    payload_form = {
                        "entry.460943250": f_item,
                        "entry.1132062078": f_type,
                        "entry.823872688": f_serial,
                        "entry.1220447242": f_note
                    }
                    r_send = requests.post(FORM_URL, data=payload_form)
                    if r_send.status_code == 200:
                        st.balloons()
                        st.success("Enregistré dans le tableau ! 🥳")
                    else:
                        st.error("Erreur d'envoi au Google Sheet.")

        except Exception as e:
            st.error(f"Erreur : {e}")

st.divider()
st.caption("Système de tri automatique Kanpro v5.0")

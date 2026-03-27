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

st.title("📦 Scanner Kanpro v6.0")

photo = st.file_uploader("📸 SCANNER L'ÉTIQUETTE", type=['jpg', 'jpeg', 'png'])

if photo is not None:
    image = Image.open(photo)
    image.thumbnail((1200, 1200)) 
    st.image(image, use_container_width=True)

    if st.button("🔍 ANALYSER ET REMPLIR"):
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
            
            with st.spinner("Tri des données..."):
                res = requests.post(api_url, json=payload, timeout=20)
                data = res.json()

            # --- EXTRACTION ROBUSTE ---
            barcodes = []
            if 'responses' in data and 'barcodeAnnotations' in data['responses'][0]:
                for b in data['responses'][0]['barcodeAnnotations']:
                    barcodes.append(b.get('rawValue', ''))
            
            texte_complet = ""
            type_detecte = ""
            if 'responses' in data and 'textAnnotations' in data['responses'][0]:
                texte_complet = data['responses'][0]['textAnnotations'][0]['description']
                # On cherche le Type de façon plus large
                for ligne in texte_complet.split('\n'):
                    if "TYPE" in ligne.upper():
                        type_detecte = ligne.upper().split("TYPE")[-1].strip(": ").strip()

            # --- RANGEMENT DANS LES VARIABLES ---
            # Si on a trouvé des codes barres, on les met dans l'ordre
            val_item = barcodes[0] if len(barcodes) > 0 else ""
            val_serial = barcodes[1] if len(barcodes) > 1 else ""
            
            # Si l'IA n'a pas vu de "Codes-barres" mais a lu du texte (chiffres)
            # On essaie de boucher les trous avec les premières lignes lues
            lignes = texte_complet.split('\n')
            if not val_item and len(lignes) > 0: val_item = lignes[0]
            if not val_serial and len(lignes) > 2: val_serial = lignes[2]

            # --- AFFICHAGE DU FORMULAIRE ---
            st.success("Analyse terminée !")
            
            with st.form("mon_formulaire"):
                f_item = st.text_input("📦 Item No / Barcode", value=val_item)
                f_type = st.text_input("🏷️ Type produit", value=type_detecte)
                f_serial = st.text_input("🔢 Serial No", value=val_serial)
                
                if st.form_submit_button("🚀 ENVOYER AU GOOGLE SHEET"):
                    donnees = {
                        "entry.460943250": f_item,
                        "entry.1132062078": f_type,
                        "entry.823872688": f_serial,
                        "entry.1220447242": "Scan Final"
                    }
                    requests.post(FORM_URL, data=donnees)
                    st.balloons()
                    st.success("C'est enregistré !")

        except Exception as e:
            st.error(f"Erreur : {e}")

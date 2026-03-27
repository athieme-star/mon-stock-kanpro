import streamlit as st
import requests
import base64
from datetime import datetime

# --- 1. CONFIGURATION ET SÉCURITÉ ---
try:
    API_KEY = st.secrets["google"]["api_key"]
except:
    st.error("❌ CLÉ API MANQUANTE : Vérifiez vos 'Secrets' sur Streamlit Cloud.")
    st.stop()

FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdsdTn7Rgp2ujd6jAQkd5bqDLPVcHdwMxTLgy0j4e1ZUODqLw/formResponse"

st.set_page_config(page_title="Diagnostic Scanner Kanpro", layout="centered")
st.title("📦 Scanner Kanpro - Mode Diagnostic")

# --- 2. CHARGEMENT DE LA PHOTO ---
photo = st.file_uploader("📸 PRENDRE UNE PHOTO (NETTE ET HORIZONTALE)", type=['jpg', 'jpeg', 'png'])

if photo is not None:
    st.info(f"Fichier reçu : {photo.name} ({round(photo.size/1024, 1)} KB)")
    
    if st.button("🔍 LANCER L'ANALYSE DE L'ÉTIQUETTE"):
        try:
            # Encodage de l'image
            base64_image = base64.b64encode(photo.getvalue()).decode('utf-8')
            
            # Appel Google Vision (Texte + Codes-barres)
            api_url = f"https://vision.googleapis.com/v1/images:annotate?key={API_KEY}"
            payload = {
                "requests": [{
                    "image": {"content": base64_image},
                    "features": [
                        {"type": "TEXT_DETECTION"},
                        {"type": "BARCODE_DETECTION"}
                    ]
                }]
            }
            
            with st.spinner("L'IA analyse l'image..."):
                res = requests.post(api_url, json=payload, timeout=20)
                data = res.json()

            # --- 3. ZONE DE DIAGNOSTIC (POUR VOIR CE QUI BLOQUE) ---
            st.subheader("🕵️ Rapport de l'IA")
            
            # Analyse des Codes-barres
            barcodes = []
            if 'responses' in data and 'barcodeAnnotations' in data['responses'][0]:
                for b in data['responses'][0]['barcodeAnnotations']:
                    barcodes.append(b.get('rawValue', ''))
            
            if barcodes:
                st.success(f"✅ {len(barcodes)} Codes-barres trouvés : {barcodes}")
            else:
                st.warning("⚠️ Aucun code-barre détecté.")

            # Analyse du Texte
            texte_brut = ""
            if 'responses' in data and 'textAnnotations' in data['responses'][0]:
                texte_brut = data['responses'][0]['textAnnotations'][0]['description']
                st.write("📄 **Texte brut détecté par l'IA :**")
                st.code(texte_brut) # Affiche tout le texte lu
            else:
                st.warning("⚠️ Aucun texte détecté sur l'image.")

            # --- 4. TENTATIVE DE REMPLISSAGE AUTOMATIQUE ---
            # On cherche "Type" dans le texte
            type_detecte = ""
            for ligne in texte_brut.split('\n'):
                if "TYPE" in ligne.upper():
                    type_detecte = ligne.upper().replace("TYPE", "").strip(": ").strip()

            # Attribution des codes-barres par position (hypothèse : Item en 1er, Serial en 2e)
            item_val = barcodes[0] if len(barcodes) > 0 else ""
            serial_val = barcodes[1] if len(barcodes) > 1 else ""

            st.divider()

            # --- 5. FORMULAIRE FINAL ---
            with st.form("envoi_sheet"):
                st.write("### ✅ Validez les données avant envoi")
                f_item = st.text_input("📦 Item No / Barcode", value=item_val)
                f_type = st.text_input("🏷️ Type produit", value=type_detecte)
                f_serial = st.text_input("🔢 Serial No (Unique)", value=serial_val)
                
                if st.form_submit_button("🚀 ENREGISTRER DANS LE GOOGLE SHEET"):
                    payload_form = {
                        "entry.460943250": f_item,
                        "entry.1132062078": f_type,
                        "entry.823872688": f_serial,
                        "entry.1220447242": "Scan OK"
                    }
                    r_send = requests.post(FORM_URL, data=payload_form)
                    if r_send.status_code == 200:
                        st.balloons()
                        st.success("Données envoyées avec succès !")
                    else:
                        st.error("Erreur lors de l'envoi au Google Sheet.")

        except Exception as e:
            st.error(f"Erreur technique : {e}")

st.divider()
st.caption("Mode Diagnostic Kanpro - v3.0")

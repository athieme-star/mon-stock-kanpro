import streamlit as st
import requests
import base64
from datetime import datetime

# --- CONFIGURATION ---
API_KEY = st.secrets["google"]["api_key"]

# Configuration du Google Form mis à jour
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdsdTn7Rgp2ujd6jAQkd5bqDLPVcHdwMxTLgy0j4e1ZUODqLw/formResponse"
ENTRY_REF = "entry.460943250"
ENTRY_CB1 = "entry.1132062078"
ENTRY_CB2 = "entry.823872688"
ENTRY_PHOTO = "entry.1220447242"

st.set_page_config(page_title="Stock Kanpro v2", layout="centered")

st.title("📦 Scanner de Stock Complet")
st.write("Scannez l'étiquette pour remplir les 3 codes + validation photo.")

photo_file = st.file_uploader("📸 CLIQUEZ ICI POUR SCANNER", type=['jpg', 'jpeg', 'png'])

if photo_file is not None:
    st.image(photo_file, caption="Photo capturée", use_container_width=True)
    
    with st.spinner('L\'IA analyse l\'étiquette...'):
        try:
            base64_image = base64.b64encode(photo_file.getvalue()).decode('utf-8')
            api_url = f"https://vision.googleapis.com/v1/images:annotate?key={API_KEY}"
            payload = {"requests": [{"image": {"content": base64_image}, "features": [{"type": "TEXT_DETECTION"}]}]}
            response = requests.post(api_url, json=payload)
            data = response.json()
            
            if 'textAnnotations' in data['responses'][0]:
                lignes = data['responses'][0]['textAnnotations'][0]['description'].split('\n')
                st.success("✅ Analyse terminée")

                # Formulaire d'édition
                with st.form("validation_complete"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        ref = st.text_input("Référence (Code)", value=lignes[0] if len(lignes) > 0 else "")
                        cb1 = st.text_input("Code-barre 1", value=lignes[1] if len(lignes) > 1 else "")
                    
                    with col2:
                        cb2 = st.text_input("Code-barre 2", value=lignes[2] if len(lignes) > 2 else "")
                        # Pour la photo, on envoie l'heure de prise de vue car le fichier est trop lourd pour le Form
                        info_photo = st.text_input("Info Photo", value=f"Photo prise le {datetime.now().strftime('%d/%m %H:%M')}", disabled=True)

                    submit = st.form_submit_button("🚀 ENREGISTRER TOUT LE STOCK")
                    
                    if submit:
                        # Envoi des 4 données au Google Form
                        form_data = {
                            ENTRY_REF: ref,
                            ENTRY_CB1: cb1,
                            ENTRY_CB2: cb2,
                            ENTRY_PHOTO: info_photo
                        }
                        res = requests.post(FORM_URL, data=form_data)
                        
                        if res.status_code == 200:
                            st.balloons()
                            st.success("Données envoyées avec succès au Google Sheet !")
                        else:
                            st.error("Erreur d'envoi. Vérifiez votre connexion.")
            else:
                st.warning("⚠️ L'IA n'a pas détecté de texte.")
        except Exception as e:
            st.error(f"Erreur technique : {e}")

st.divider()
st.caption("Système Kanpro - Connexion directe via Google Forms")

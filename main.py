import streamlit as st
import requests
import base64
import gspread
from google.oauth2.service_account import Credentials

# --- 1. CONFIGURATION ---
API_KEY = st.secrets["google"]["api_key"]
SHEET_ID = st.secrets["google"]["sheet_id"]

st.set_page_config(page_title="Stock Kanpro", layout="centered")

# Fonction pour envoyer les données vers Google Sheets
def save_to_google_sheets(ref, qte):
    try:
        # Utilisation des secrets pour s'authentifier sur Google Sheets
        # Note : Assure-toi que ton compte de service a accès au fichier Sheet
        scope = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID).worksheet(st.secrets["google"]["worksheet_name"])
        sheet.append_row([ref, qte]) # Ajoute une ligne à la fin
        return True
    except Exception as e:
        st.error(f"Erreur d'enregistrement Sheet : {e}")
        return False

st.title("📦 Scanner de Stock Kanpro")

# --- 2. PRISE DE PHOTO ---
photo_file = st.file_uploader("📸 CLIQUEZ ICI POUR SCANNER", type=['jpg', 'jpeg', 'png'])

if photo_file is not None:
    st.image(photo_file, caption="Photo capturée", use_container_width=True)
    
    with st.spinner('Analyse de l\'étiquette...'):
        try:
            # IA Google Vision
            base64_image = base64.b64encode(photo_file.getvalue()).decode('utf-8')
            url = f"https://vision.googleapis.com/v1/images:annotate?key={API_KEY}"
            payload = {
                "requests": [{"image": {"content": base64_image}, "features": [{"type": "TEXT_DETECTION"}]}]
            }
            response = requests.post(url, json=payload)
            data = response.json()
            
            if 'textAnnotations' in data['responses'][0]:
                resultat = data['responses'][0]['textAnnotations'][0]['description']
                st.success("✅ Texte lu avec succès !")
                
                # Formulaire de validation
                with st.form("valider_stock"):
                    ref = st.text_input("Référence détectée", value=resultat.split('\n')[0])
                    qte = st.number_input("Quantité", min_value=1, value=1)
                    
                    if st.form_submit_button("CONFIRMER L'ENREGISTREMENT"):
                        if save_to_google_sheets(ref, qte):
                            st.balloons()
                            st.success(f"Enregistré dans le Google Sheet : {qte} x {ref}")
            else:
                st.warning("⚠️ Impossible de lire le texte. Réessayez de plus près.")
        except Exception as e:
            st.error(f"Erreur : {e}")

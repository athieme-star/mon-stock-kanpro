import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from google.cloud import vision
from google_auth_oauthlib.flow import Flow
import os

# --- 1. CONFIGURATION STRICTE ET FORCEE ---
# On fixe les IDs et l'adresse pour que Google ne reçoive plus jamais "localhost"
PROJECT_ID = "coral-theme-491310-h9"
CLIENT_ID = "151899253789-em8il3hm5m72s96o8fvcmmbojfht7une.apps.googleusercontent.com"
REDIRECT_URI = "https://mon-stock-kanpro.streamlit.app"

st.set_page_config(page_title="Stock Kanpro", layout="centered")

# Configuration Google OAuth (Utilise le Secret stocké dans Streamlit Cloud)
client_config = {
    "web": {
        "client_id": CLIENT_ID,
        "project_id": PROJECT_ID,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_secret": st.secrets["google"]["client_secret"],
        "redirect_uris": [REDIRECT_URI],
    }
}

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly"
]

# --- 2. LOGIQUE DE CONNEXION ---
if 'auth_code' not in st.session_state:
    st.session_state.auth_code = None

# On récupère le code renvoyé par Google après la connexion
params = st.query_params
if "code" in params and not st.session_state.auth_code:
    st.session_state.auth_code = params["code"]

# Si l'utilisateur n'est pas connecté, on affiche le bouton
if not st.session_state.auth_code:
    flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=REDIRECT_URI)
    auth_url, _ = flow.authorization_url(prompt='consent')
    st.title("🔐 Accès au Stock")
    st.info("Veuillez vous identifier pour accéder au scanner.")
    st.link_button("Se connecter avec Google", auth_url)
    st.stop()

# --- 3. INTERFACE APRES CONNEXION ---
st.title("📦 Scanner de Stock")

st.subheader("📸 Prendre une photo de l'étiquette")
# Utilisation du composant natif pour activer la caméra du téléphone
photo = st.camera_input("Cadrez bien le texte de l'étiquette")

if photo is not None:
    with st.spinner('Analyse de l\'image en cours...'):
        try:
            # Envoi à l'IA Google Vision
            client = vision.ImageAnnotatorClient()
            image = vision.Image(content=photo.getvalue())
            response = client.text_detection(image=image)
            texts = response.text_annotations
            
            if texts:
                resultat = texts[0].description
                st.success("Texte détecté avec succès !")
                
                with st.form("form_stock"):
                    st.text_area("Résultat de l'analyse", resultat, height=150)
                    ref_finale = st.text_input("Référence à enregistrer")
                    quantite = st.number_input("Quantité", min_value=1, value=1)
                    
                    if st.form_submit_button("Valider l'entrée"):
                        st.balloons()
                        st.write(f"✅ Enregistré : {quantite} x {ref_finale}")
            else:
                st.warning("Aucun texte n'a été trouvé sur la photo. Essayez de vous rapprocher.")
        except Exception as e:
            st.error(f"Erreur technique : {e}")

st.divider()
st.caption(f"Connecté au projet Google : {PROJECT_ID}")

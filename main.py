import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from google.cloud import vision
from google_auth_oauthlib.flow import Flow
import os

# --- 1. CONFIGURATION FIXE (PLUS BESOIN DE CHERCHER DANS LES SECRETS) ---
PROJECT_ID = "coral-theme-491310-h9"
CLIENT_ID = "151899253789-em8il3hm5m72s96o8fvcmmbojfht7une.apps.googleusercontent.com"

st.set_page_config(page_title="Stock Kanpro", layout="centered")

# --- 2. GESTION DE L'URL DE REDIRECTION ---
if st.runtime.exists():
    try:
        addr = st.get_option("browser.serverAddress")
        if "localhost" in addr or "127.0.0.1" in addr:
            redirect_uri = "http://localhost:8501"
        else:
            redirect_uri = "https://mon-stock-kanpro.streamlit.app"
    except:
        redirect_uri = "https://mon-stock-kanpro.streamlit.app"
else:
    redirect_uri = "https://mon-stock-kanpro.streamlit.app"

# Configuration Google OAuth
client_config = {
    "web": {
        "client_id": CLIENT_ID,
        "project_id": PROJECT_ID,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_secret": st.secrets["google"]["client_secret"], # On garde le secret caché ici
        "redirect_uris": [redirect_uri],
    }
}

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly"
]

# --- 3. LOGIQUE DE CONNEXION ---
if 'auth_code' not in st.session_state:
    st.session_state.auth_code = None

params = st.query_params
if "code" in params and not st.session_state.auth_code:
    st.session_state.auth_code = params["code"]

if not st.session_state.auth_code:
    flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=redirect_uri)
    auth_url, _ = flow.authorization_url(prompt='consent')
    st.title("🔐 Connexion Stock")
    st.link_button("Se connecter avec Google", auth_url)
    st.stop()

# --- 4. INTERFACE APPLI (PHOTO & SCAN) ---
st.title("📦 Scanner de Stock")

st.subheader("📸 Prendre une photo de l'étiquette")
# Le composant officiel Streamlit pour la caméra du téléphone
photo = st.camera_input("Prendre une photo nette")

if photo is not None:
    with st.spinner('Analyse par l\'IA...'):
        try:
            # Envoi à Google Vision
            client = vision.ImageAnnotatorClient()
            image = vision.Image(content=photo.getvalue())
            response = client.text_detection(image=image)
            texts = response.text_annotations
            
            if texts:
                resultat = texts[0].description
                st.success("Lecture terminée !")
                
                with st.form("form_validation"):
                    st.text_area("Texte détecté :", resultat, height=150)
                    ref_input = st.text_input("Référence confirmée")
                    quantite = st.number_input("Quantité", min_value=1, value=1)
                    
                    if st.form_submit_button("Enregistrer en Stock"):
                        # Ici tu pourras ajouter ta logique gspread plus tard
                        st.balloons()
                        st.info(f"Enregistré : {quantite} x {ref_input}")
            else:
                st.warning("Aucun texte trouvé. Approchez l'appareil de l'étiquette.")
        except Exception as e:
            st.error(f"Erreur lors de l'analyse : {e}")

st.divider()
st.caption("Application connectée au projet : " + PROJECT_ID)

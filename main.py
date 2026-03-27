import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from google.cloud import vision
from google_auth_oauthlib.flow import Flow
import os

# --- 1. CONFIGURATION ET STYLE ---
PROJECT_ID = "coral-theme-491310-h9"
CLIENT_ID = "151899253789-em8il3hm5m72s96o8fvcmmbojfht7une.apps.googleusercontent.com"
REDIRECT_URI = "https://mon-stock-kanpro.streamlit.app"

st.set_page_config(page_title="Stock Kanpro", layout="centered")

# 🎨 FORCE L'APPAREIL PHOTO EN LARGEUR TOTALE
st.markdown("""
    <style>
    [data-testid="stCameraInput"] {
        width: 100% !important;
    }
    [data-testid="stCameraInput"] > div > div > div {
        width: 100% !important;
    }
    /* Agrandit la zone de prévisualisation */
    video {
        object-fit: cover !important;
        height: 400px !important; 
    }
    </style>
    """, unsafe_allow_html=True)

# Configuration Google OAuth
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

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.readonly"]

# --- 2. LOGIQUE DE CONNEXION ---
if 'auth_code' not in st.session_state:
    st.session_state.auth_code = None

params = st.query_params
if "code" in params and not st.session_state.auth_code:
    st.session_state.auth_code = params["code"]

if not st.session_state.auth_code:
    flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=REDIRECT_URI)
    auth_url, _ = flow.authorization_url(prompt='consent')
    st.title("🔐 Accès au Stock")
    st.link_button("Se connecter avec Google", auth_url)
    st.stop()

# --- 3. INTERFACE SCANNER ---
st.title("📦 Scanner de Stock")

# Utilisation du bouton photo (maintenant élargi par le CSS plus haut)
photo = st.camera_input("Prendre une photo de l'étiquette")

if photo is not None:
    with st.spinner('Analyse de l\'image...'):
        try:
            client = vision.ImageAnnotatorClient()
            image = vision.Image(content=photo.getvalue())
            response = client.text_detection(image=image)
            texts = response.text_annotations
            
            if texts:
                resultat = texts[0].description
                st.success("Texte détecté !")
                
                with st.form("form_stock"):
                    # On affiche le texte pour vérification
                    ref_detectee = st.text_area("Texte lu", resultat, height=100)
                    ref_finale = st.text_input("Référence (à corriger si besoin)", value=resultat.split('\n')[0])
                    quantite = st.number_input("Quantité", min_value=1, value=1)
                    
                    if st.form_submit_button("Enregistrer"):
                        st.balloons()
                        st.write(f"✅ Enregistré : {quantite} x {ref_finale}")
            else:
                st.warning("Aucun texte trouvé.")
        except Exception as e:
            st.error(f"Erreur technique : {e}")

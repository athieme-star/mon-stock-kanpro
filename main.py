import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from google.cloud import vision
from google_auth_oauthlib.flow import Flow
import os

# --- CONFIGURATION INITIALE ---
st.set_page_config(page_title="Stock Kanpro", layout="centered")

# --- GESTION DE LA CONNEXION (AUTO-DETECTION) ---
# Cette partie décide seule si elle utilise l'adresse locale ou l'adresse internet
if st.runtime.exists():
    try:
        # On tente de voir si on est en local
        addr = st.get_option("browser.serverAddress")
        if "localhost" in addr or "127.0.0.1" in addr:
            redirect_uri = "http://localhost:8501"
        else:
            redirect_uri = st.secrets["google"]["redirect_uri"]
    except:
        # Par défaut on prend l'adresse officielle des secrets
        redirect_uri = st.secrets["google"]["redirect_uri"]
else:
    redirect_uri = st.secrets["google"]["redirect_uri"]

client_config = {
    "web": {
        "client_id": st.secrets["google"]["client_id"],
        "project_id": st.secrets["google"]["project_id"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_secret": st.secrets["google"]["client_secret"],
        "redirect_uris": [redirect_uri],
    }
}

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly"
]

# --- LOGIQUE D'AUTHENTIFICATION ---
if 'auth_code' not in st.session_state:
    st.session_state.auth_code = None

# Récupération du code de retour de Google
params = st.query_params
if "code" in params and not st.session_state.auth_code:
    st.session_state.auth_code = params["code"]

if not st.session_state.auth_code:
    flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=redirect_uri)
    auth_url, _ = flow.authorization_url(prompt='consent')
    st.title("🔐 Connexion au Stock")
    st.write("Veuillez vous connecter pour accéder au scanner.")
    st.link_button("Se connecter avec Google", auth_url)
    st.stop()

# --- INTERFACE APRES CONNEXION ---
st.title("📦 Scanner de Stock")

# 📸 LE NOUVEAU BOUTON PHOTO
st.subheader("Prendre une photo de l'étiquette")
photo = st.camera_input("Cadrez bien l'étiquette et déclenchez")

if photo is not None:
    with st.spinner('Analyse de l\'image...'):
        # Envoi à Google Vision
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=photo.getvalue())
        response = client.text_detection(image=image)
        texts = response.text_annotations
        
        if texts:
            resultat = texts[0].description
            st.success("Texte lu avec succès !")
            
            with st.form("form_stock"):
                st.text_area("Texte détecté", resultat, height=150)
                ref = st.text_input("Confirmer la Référence")
                qte = st.number_input("Quantité", min_value=1, value=1)
                
                if st.form_submit_button("Valider l'entrée en stock"):
                    st.balloons()
                    st.info(f"Enregistré : {qte} x {ref}")
        else:
            st.warning("Aucun texte détecté. Essayez de vous rapprocher de l'étiquette.")

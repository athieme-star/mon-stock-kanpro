import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from google.cloud import vision
from google_auth_oauthlib.flow import Flow
import os

# --- CONFIGURATION DE L'APPLICATION ---
st.set_page_config(page_title="Gestionnaire de Stock Kanpro", layout="centered")

# 1. Gestion des URLs de redirection (Automatique)
if st.runtime.exists():
    # Détecte si on est en local ou sur le Web
    is_local = "localhost" in st.get_option("browser.serverAddress") or "127.0.0.1" in st.get_option("browser.serverAddress")
    redirect_uri = "http://localhost:8501" if is_local else st.secrets["google"]["redirect_uri"]
else:
    redirect_uri = st.secrets["google"]["redirect_uri"]

# 2. Configuration Google OAuth
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

# --- LOGIQUE DE CONNEXION ---
if 'auth_code' not in st.session_state:
    st.session_state.auth_code = None

query_params = st.query_params
if "code" in query_params and not st.session_state.auth_code:
    st.session_state.auth_code = query_params["code"]

if not st.session_state.auth_code:
    flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=redirect_uri)
    auth_url, _ = flow.authorization_url(prompt='consent')
    st.title("🔐 Connexion Requise")
    st.link_button("Se connecter avec Google", auth_url)
    st.stop()

# --- INTERFACE PRINCIPALE ---
st.title("📦 Gestionnaire de Stock")

# 📸 SECTION PHOTO (Remplacement du scanner live)
st.subheader("📸 Prendre une photo de l'étiquette")
img_file_buffer = st.camera_input("Prendre une photo nette")

if img_file_buffer is not None:
    with st.spinner('Analyse de l\'étiquette par Google Vision...'):
        content = img_file_buffer.getvalue()
        
        # Initialisation de l'IA Google Vision
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=content)
        
        # Détection du texte et des codes
        response = client.text_detection(image=image)
        texts = response.text_annotations
        
        if texts:
            resultat_brut = texts[0].description
            st.success("Lecture terminée !")
            
            # Formulaire de saisie avec les données lues
            with st.form("validation_stock"):
                st.text_area("Texte détecté :", resultat_brut, height=100)
                reference = st.text_input("Référence Produit (extraite ou manuelle)")
                quantite = st.number_input("Quantité", min_value=1, value=1)
                
                submitted = st.form_submit_button("Enregistrer dans Google Sheets")
                
                if submitted:
                    # Ici la logique d'envoi vers GSpread (à adapter selon tes colonnes)
                    st.info(f"Enregistrement de {quantite} x {reference}...")
                    # [Logique GSpread ici]
                    st.balloons()
        else:
            st.error("Impossible de lire l'étiquette. Essayez d'être plus stable ou d'avoir plus de lumière.")

st.divider()
st.info("Utilisez le bouton ci-dessus pour scanner vos produits. L'IA lira automatiquement les références.")

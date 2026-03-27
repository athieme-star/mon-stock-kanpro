import streamlit as st
import requests
import base64
from datetime import datetime

# --- CONFIGURATION ---
try:
    API_KEY = st.secrets["google"]["api_key"]
except:
    st.error("❌ Erreur : Clé API absente des Secrets.")
    st.stop()

FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdsdTn7Rgp2ujd6jAQkd5bqDLPVcHdwMxTLgy0j4e1ZUODqLw/formResponse"

st.title("📦 Scanner Kanpro")

# Utilisation d'un bouton de téléchargement plus simple
photo_file = st.file_uploader("📸 CHOISIR UNE PHOTO (GALERIE)", type=['jpg', 'jpeg', 'png'])

if photo_file is not None:
    # On affiche immédiatement le nom du fichier pour être sûr qu'il est chargé
    st.write(f"✅ Fichier chargé : {photo_file.name}")
    st.image(photo_file, use_container_width=True)
    
    # BOUTON DE FORÇAGE (Si l'analyse ne part pas toute seule)
    if st.button("🔍 LANCER L'ANALYSE MAINTENANT"):
        try:
            base64_image = base64.b64encode(photo_file.getvalue()).decode('utf-8')
            api_url = f"https://vision.googleapis.com/v1/images:annotate?key={API_KEY}"
            
            payload = {"requests": [{"image": {"content": base64_image}, "features": [{"type": "TEXT_DETECTION"}]}]}
            
            with st.spinner("Analyse..."):
                res = requests.post(api_url, json=payload)
                data = res.json()
            
            if 'textAnnotations' in data['responses'][0]:
                texte = data['responses'][0]['textAnnotations'][0]['description']
                lignes = texte.split('\n')
                
                with st.form("val_form"):
                    r = st.text_input("Référence", value=lignes[0] if len(lignes)>0 else "")
                    c1 = st.text_input("Code-barre 1", value=lignes[1] if len(lignes)>1 else "")
                    c2 = st.text_input("Code-barre 2", value=lignes[2] if len(lignes)>2 else "")
                    
                    if st.form_submit_button("🚀 ENVOYER AU SHEET"):
                        d = {"entry.460943250": r, "entry.1132062078": c1, "entry.823872688": c2, "entry.1220447242": "Photo OK"}
                        requests.post(FORM_URL, data=d)
                        st.balloons()
                        st.success("Enregistré !")
            else:
                st.warning("Rien lu sur l'image.")
        except Exception as e:
            st.error(f"Erreur : {e}")

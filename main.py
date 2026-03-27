import streamlit as st
import pandas as pd
from google.cloud import vision
import io

# --- CONFIGURATION ---
PROJECT_ID = "coral-theme-491310-h9"

st.set_page_config(page_title="Stock Kanpro", layout="centered")

# --- STYLE POUR GROS BOUTONS ---
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        height: 3em;
        font-size: 20px !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📦 Scanner de Stock")

# --- LE BOUTON MAGIQUE (NATIF) ---
# Ce bouton ouvre l'application photo réelle du téléphone
photo_file = st.file_uploader("📸 CLIQUEZ ICI POUR SCANNER", type=['jpg', 'png', 'jpeg'])

if photo_file is not None:
    # Affichage de la photo pour vérifier la qualité
    st.image(photo_file, caption="Photo capturée", use_container_width=True)
    
    with st.spinner('Analyse de l\'étiquette par l\'IA...'):
        try:
            # CONNEXION A L'IA (Utilise les secrets pour l'auth)
            # On crée les credentials à partir des secrets Streamlit
            import json
            from google.oauth2 import service_account
            
            # Récupération des infos de service_account dans les secrets
            info = json.loads(st.secrets["textkey"])
            creds = service_account.Credentials.from_service_account_info(info)
            client = vision.ImageAnnotatorClient(credentials=creds)
            
            content = photo_file.getvalue()
            image = vision.Image(content=content)
            
            response = client.text_detection(image=image)
            texts = response.text_annotations
            
            if texts:
                resultat = texts[0].description
                st.success("✅ Lecture réussie !")
                
                with st.form("validation"):
                    ref_finale = st.text_input("Référence détectée", value=resultat.split('\n')[0])
                    quantite = st.number_input("Quantité", min_value=1, value=1)
                    if st.form_submit_button("VALIDER L'ENTRÉE"):
                        st.balloons()
                        st.success(f"Enregistré : {quantite} x {ref_finale}")
            else:
                st.warning("⚠️ Aucun texte trouvé. Essayez de reprendre la photo plus près.")
                
        except Exception as e:
            st.error(f"Erreur technique : {e}")
            st.info("Avez-vous ajouté la 'textkey' dans les Secrets Streamlit ?")

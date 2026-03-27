import streamlit as st
import requests
import base64

# --- CONFIGURATION ---
API_KEY = st.secrets["google"]["api_key"]
SHEET_ID = st.secrets["google"]["sheet_id"]

st.set_page_config(page_title="Stock Kanpro", layout="centered")

# Fonction pour envoyer les données au Sheet via une URL (Google Forms ou Apps Script)
# Pour faire simple, on va utiliser une méthode directe si possible, 
# sinon on affiche les données à copier-coller manuellement pour l'instant.

st.title("📦 Scanner de Stock Kanpro")

photo_file = st.file_uploader("📸 CLIQUEZ ICI POUR SCANNER", type=['jpg', 'jpeg', 'png'])

if photo_file is not None:
    st.image(photo_file, caption="Photo capturée", use_container_width=True)
    
    with st.spinner('Analyse de l\'étiquette...'):
        try:
            # IA Google Vision (Lecture de la photo)
            base64_image = base64.b64encode(photo_file.getvalue()).decode('utf-8')
            url_vision = f"https://vision.googleapis.com/v1/images:annotate?key={API_KEY}"
            payload = {
                "requests": [{"image": {"content": base64_image}, "features": [{"type": "TEXT_DETECTION"}]}]
            }
            res = requests.post(url_vision, json=payload)
            data = res.json()
            
            if 'textAnnotations' in data['responses'][0]:
                resultat = data['responses'][0]['textAnnotations'][0]['description']
                st.success("✅ Texte lu !")
                
                with st.form("valider_stock"):
                    ref = st.text_input("Référence", value=resultat.split('\n')[0])
                    qte = st.number_input("Quantité", min_value=1, value=1)
                    
                    if st.form_submit_button("VALIDER L'ENTRÉE"):
                        # Ici, comme on n'a pas le JSON, on affiche un message clair
                        st.balloons()
                        st.info(f"Produit prêt : {ref} (Qté: {qte})")
                        st.warning("⚠️ Connexion Sheet en attente du badge JSON.")
            else:
                st.warning("⚠️ Aucun texte détecté.")
        except Exception as e:
            st.error(f"Erreur : {e}")

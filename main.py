import streamlit as st
import requests
import base64
from PIL import Image
import io

# --- 1. CONFIGURATION ---
try:
    API_KEY = st.secrets["google"]["api_key"]
except:
    st.error("❌ CLÉ API MANQUANTE dans les Secrets.")
    st.stop()

st.title("📦 Scanner Kanpro - Force Brute")

# --- 2. CAPTURE ---
photo = st.file_uploader("📸 PRENDRE LA PHOTO", type=['jpg', 'jpeg', 'png'])

if photo is not None:
    # --- OPTIMISATION DE L'IMAGE ---
    # On ouvre l'image avec PIL pour s'assurer qu'elle existe vraiment
    image = Image.open(photo)
    
    # On la redimensionne légèrement pour qu'elle passe mieux sur le réseau
    image.thumbnail((1200, 1200)) 
    
    # On l'affiche sur l'écran pour CONFIRMER que le site la voit
    st.image(image, caption="Image prête pour l'analyse", use_container_width=True)

    if st.button("🔍 ANALYSER L'IMAGE MAINTENANT"):
        try:
            # Conversion de l'image traitée en Base64
            buffered = io.BytesIO()
            image.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            # Appel Google Vision
            api_url = f"https://vision.googleapis.com/v1/images:annotate?key={API_KEY}"
            payload = {
                "requests": [{
                    "image": {"content": img_str},
                    "features": [{"type": "TEXT_DETECTION"}, {"type": "BARCODE_DETECTION"}]
                }]
            }
            
            with st.spinner("L'IA déchiffre..."):
                res = requests.post(api_url, json=payload, timeout=20)
                data = res.json()

            # --- RÉSULTATS ---
            st.divider()
            
            # Récupération texte
            texte_final = ""
            if 'responses' in data and 'textAnnotations' in data['responses'][0]:
                texte_final = data['responses'][0]['textAnnotations'][0]['description']
                st.success("✅ Texte détecté !")
                st.code(texte_final)
            else:
                st.error("❌ L'IA ne voit toujours aucun texte.")
                st.write("DEBUG DATA:", data) # Pour voir si Google renvoie une erreur

        except Exception as e:
            st.error(f"Erreur technique : {e}")

st.divider()
st.caption("Version 4.0 - Image Optimization Enabled")

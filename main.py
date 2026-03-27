import streamlit as st
import requests
import base64

# 1. Sécurité Clé API
try:
    API_KEY = st.secrets["google"]["api_key"]
except:
    st.error("Clé API introuvable dans les Secrets.")
    st.stop()

st.title("🚀 Scanner Kanpro Rapide")

# On limite la taille pour éviter que le téléphone ne sature
photo = st.file_uploader("Prendre une photo", type=['jpg', 'jpeg', 'png'])

if photo is not None:
    st.write(f"📸 Image reçue ({round(photo.size/1024/1024, 2)} Mo)")
    
    # Bouton manuel pour éviter les bugs de chargement automatique
    if st.button("🔍 ANALYSER MAINTENANT"):
        try:
            # Encodage
            base64_image = base64.b64encode(photo.getvalue()).decode('utf-8')
            
            # Appel Google Vision
            api_url = f"https://vision.googleapis.com/v1/images:annotate?key={API_KEY}"
            payload = {"requests": [{"image": {"content": base64_image}, "features": [{"type": "TEXT_DETECTION"}]}]}
            
            with st.spinner("Lecture de l'étiquette..."):
                res = requests.post(api_url, json=payload, timeout=15)
                data = res.json()
            
            if 'responses' in data and 'textAnnotations' in data['responses'][0]:
                texte = data['responses'][0]['textAnnotations'][0]['description']
                lignes = texte.split('\n')
                
                # Affichage direct des résultats
                st.success("Texte lu !")
                ref = st.text_input("Référence", value=lignes[0] if len(lignes)>0 else "")
                cb1 = st.text_input("Code-barre 1", value=lignes[1] if len(lignes)>1 else "")
                cb2 = st.text_input("Code-barre 2", value=lignes[2] if len(lignes)>2 else "")
                
                if st.button("🚀 ENVOYER AU GOOGLE SHEET"):
                    form_url = "https://docs.google.com/forms/d/e/1FAIpQLSdsdTn7Rgp2ujd6jAQkd5bqDLPVcHdwMxTLgy0j4e1ZUODqLw/formResponse"
                    payload_form = {
                        "entry.460943250": ref,
                        "entry.1132062078": cb1,
                        "entry.823872688": cb2,
                        "entry.1220447242": "Mobile OK"
                    }
                    requests.post(form_url, data=payload_form)
                    st.balloons()
                    st.success("C'est dans le tableau !")
            else:
                st.error("L'IA n'a pas trouvé de texte. Réessayez de plus près.")
        except Exception as e:
            st.error(f"Erreur technique : {e}")

st.caption("Version Commando - Direct Vision API")

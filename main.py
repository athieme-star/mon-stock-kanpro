import streamlit as st
import requests
import base64
from datetime import datetime

# --- 1. VÉRIFICATION DES SECRETS ---
try:
    API_KEY = st.secrets["google"]["api_key"]
except Exception:
    st.error("❌ ERREUR : La clé API est introuvable dans les Secrets de Streamlit Cloud.")
    st.info("Allez dans Settings > Secrets et vérifiez que vous avez bien écrit : [google] (à la ligne) api_key = 'VOTRE_CLE'")
    st.stop()

# --- 2. CONFIGURATION GOOGLE FORM ---
# On utilise tes identifiants vérifiés
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdsdTn7Rgp2ujd6jAQkd5bqDLPVcHdwMxTLgy0j4e1ZUODqLw/formResponse"
ENTRY_REF = "entry.460943250"
ENTRY_CB1 = "entry.1132062078"
ENTRY_CB2 = "entry.823872688"
ENTRY_PHOTO = "entry.1220447242"

st.set_page_config(page_title="Scanner Kanpro V2", layout="centered")

st.title("📦 Scanner de Stock Kanpro")
st.write("Prenez une photo de l'étiquette pour remplir le Google Sheet.")

# --- 3. ZONE DE TÉLÉCHARGEMENT ---
photo_file = st.file_uploader("📸 CLIQUEZ ICI POUR SCANNER", type=['jpg', 'jpeg', 'png'])

if photo_file:
    # On affiche l'image immédiatement pour confirmer la réception
    st.image(photo_file, caption="Photo reçue ! Analyse en cours...", use_container_width=True)
    
    # --- 4. ANALYSE PAR L'IA (GOOGLE VISION) ---
    try:
        base64_image = base64.b64encode(photo_file.getvalue()).decode('utf-8')
        api_url = f"https://vision.googleapis.com/v1/images:annotate?key={API_KEY}"
        
        payload = {
            "requests": [{
                "image": {"content": base64_image},
                "features": [{"type": "TEXT_DETECTION"}]
            }]
        }
        
        with st.spinner("L'IA déchiffre l'étiquette..."):
            response = requests.post(api_url, json=payload)
            data = response.json()
        
        if 'responses' in data and 'textAnnotations' in data['responses'][0]:
            # On récupère tout le texte lu
            texte_complet = data['responses'][0]['textAnnotations'][0]['description']
            lignes = texte_complet.split('\n')
            
            st.success("✅ Analyse terminée ! Vérifiez les informations ci-dessous :")
            
            # --- 5. FORMULAIRE DE VALIDATION ---
            with st.form("form_confirmation"):
                col1, col2 = st.columns(2)
                
                with col1:
                    # On met la 1ère ligne dans Référence, la 2ème dans Code-barre 1
                    ref_detectee = lignes[0] if len(lignes) > 0 else ""
                    cb1_detecte = lignes[1] if len(lignes) > 1 else ""
                    
                    final_ref = st.text_input("Référence (Code)", value=ref_detectee)
                    final_cb1 = st.text_input("Code-barre 1", value=cb1_detecte)
                
                with col2:
                    # On met la 3ème ligne dans Code-barre 2
                    cb2_detecte = lignes[2] if len(lignes) > 2 else ""
                    
                    final_cb2 = st.text_input("Code-barre 2", value=cb2_detecte)
                    # Info photo (Horodatage)
                    horodatage = f"Scan du {datetime.now().strftime('%d/%m/%Y à %H:%M')}"
                    st.text_input("Info Photo", value=horodatage, disabled=True)

                submit = st.form_submit_button("🚀 ENREGISTRER DANS LE GOOGLE SHEET")

                if submit:
                    # --- 6. ENVOI AU GOOGLE SHEET ---
                    donnees = {
                        ENTRY_REF: final_ref,
                        ENTRY_CB1: final_cb1,
                        ENTRY_CB2: final_cb2,
                        ENTRY_PHOTO: horodatage
                    }
                    
                    envoi = requests.post(FORM_URL, data=donnees)
                    
                    if envoi.status_code == 200:
                        st.balloons()
                        st.success(f"Bravo ! La référence {final_ref} a été ajoutée.")
                    else:
                        st.error("Erreur lors de l'envoi au Google Sheet. Vérifiez votre connexion.")
        else:
            st.warning("⚠️ L'IA n'a pas réussi à lire de texte sur cette image. Essayez de prendre la photo de plus près.")
            
    except Exception as e:
        st.error(f"Une erreur technique est survenue : {e}")

st.divider()
st.caption("Application connectée au Google Sheet via Google Forms")

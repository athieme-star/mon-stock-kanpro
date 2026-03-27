import streamlit as st
import requests
import base64
import json

# 1. Sécurité Clé API
try:
    API_KEY = st.secrets["google"]["api_key"]
except:
    st.error("❌ Clé API introuvable dans les Secrets.")
    st.stop()

st.set_page_config(page_title="Scanner Expert Kanpro", layout="centered")
st.title("📦 Scanner Expert Kanpro")
st.write("Structure complexe : Item, Type, Serial No.")

# 2. Zone de téléchargement
photo = st.file_uploader("📸 Scanner l'étiquette complète", type=['jpg', 'jpeg', 'png'])

if photo is not None:
    st.write(f"✅ Image reçue ({round(photo.size/1024/1024, 2)} Mo)")
    
    if st.button("🔍 LANCER L'ANALYSE DÉTAILLÉE"):
        try:
            base64_image = base64.b64encode(photo.getvalue()).decode('utf-8')
            api_url = f"https://vision.googleapis.com/v1/images:annotate?key={API_KEY}"
            
            # CONFIGURATION AVANCÉE : On demande Texte ET Codes-barres
            payload = {
                "requests": [{
                    "image": {"content": base64_image},
                    "features": [
                        {"type": "TEXT_DETECTION"},
                        {"type": "BARCODE_DETECTION"} # <--- Ajout crucial
                    ]
                }]
            }
            
            with st.spinner("L'IA cartographie l'étiquette..."):
                res = requests.post(api_url, json=payload, timeout=20)
                data = res.json()
            
            # --- TRAITEMENT DES RÉSULTATS ---
            
            # A. Récupération des Codes-barres (Item No et Serial No)
            codes_detectes = []
            if 'responses' in data and 'barcodeAnnotations' in data['responses'][0]:
                for barcode in data['responses'][0]['barcodeAnnotations']:
                    codes_detectes.append(barcode.get('rawValue', ''))
            
            # Déduction des codes (on prend les 2 premiers trouvés)
            # Rappel : Item No est répété, Serial No est unique.
            item_no = codes_detectes[0] if len(codes_detectes) > 0 else ""
            serial_no = codes_detectes[1] if len(codes_detectes) > 1 else ""

            # B. Récupération du Texte (pour le Type)
            type_produit = ""
            if 'responses' in data and 'textAnnotations' in data['responses'][0]:
                texte_brut = data['responses'][0]['textAnnotations'][0]['description']
                st.info(f"🔍 Texte détecté : {texte_brut[:100]}...") # Pour debug
                
                # Recherche de la ligne "Type"
                for ligne in texte_brut.split('\n'):
                    if ligne.upper().startswith("TYPE"):
                        # On prend tout ce qui est après "Type" (et on enlève les espaces en trop)
                        type_produit = ligne.upper().replace("TYPE", "").strip()
                        break

            # --- AFFICHAGE DU FORMULAIRE DE VALIDATION ---
            st.success("✅ Analyse terminée ! Vérifiez les champs.")
            
            with st.form("form_kanpro"):
                col1, col2 = st.columns(2)
                
                with col1:
                    final_item = st.text_input("📦 Item No / Barcode", value=item_no)
                    final_type = st.text_input("🏷️ Type (détecté sous 'Type')", value=type_produit)
                
                with col2:
                    final_serial = st.text_input("🔢 Serial No / Barcode (Code unique)", value=serial_no)
                    st.text_input("📌 Note", value="Scan Mobile", disabled=True)

                if st.form_submit_button("🚀 ENVOYER AU GOOGLE SHEET"):
                    # URL de ton formulaire Google Form (à vérifier si c'est tjs le bon)
                    form_url = "https://docs.google.com/forms/d/e/1FAIpQLSdsdTn7Rgp2ujd6jAQkd5bqDLPVcHdwMxTLgy0j4e1ZUODqLw/formResponse"
                    
                    # Mapping avec tes entry.XXXX (Il faudra peut-être les ajuster)
                    payload_form = {
                        "entry.460943250": final_item,   # Item No
                        "entry.1132062078": final_type,  # Type
                        "entry.823872688": final_serial, # Serial No
                        "entry.1220447242": "Scan Expert" # Note photo
                    }
                    
                    requests.post(form_url, data=payload_form)
                    st.balloons()
                    st.success(f"Référence {final_item} enregistrée !")

        except Exception as e:
            st.error(f"Une erreur est survenue lors de l'analyse : {e}")

st.divider()
st.caption("Version Expert - Détection Mixte Texte/Barcode")

import streamlit as st
import re
import io
import pdfkit
import tempfile 
import base64 
import json
from datetime import datetime
from pathlib import Path
import platform
import subprocess
import os

def get_logo_from_file():
    # Get the absolute path to the logo file
    current_dir = Path(__file__).parent
    logo_path = current_dir / 'assets' / 'logo_br.jpg'
    
    try:
        with open(logo_path, 'rb') as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"Error loading logo: {e}")
        return None

# Load the logo once when the app starts
LOGO_BR_BASE64 = get_logo_from_file()

def check_required_fields(adresse, conducteur, chef_chantier, contact_chantier, redacteur_rapport):
    return all([adresse.strip(), conducteur.strip(), chef_chantier.strip(), contact_chantier.strip(), redacteur_rapport.strip()])

st.set_page_config(page_title="RAPPORT DE VISITE BR CONSULT", layout="wide")

# Dictionnaire des critères par catégorie
categories = {
    "Administratif": [
        "PPSPS ou Plan de Prévention disponible(s) sur chantier",
        "Rapport(s) de vérification échafaudage / appareils de levage établi(s)",
        "Rapport(s) de vérification des machine(s) utilisées établi(s)",
        "Affichage",
        "Autres documents disponibles"
    ],
    "Sécurité": [
        "Locaux de vie",
        "Port des EPI et vêtements de travail classiques",
        "Échafaudage / protection collective",
        "Risques de chute",
        "Risque électrique",
        "Risques liés aux produits chimiques",
        "Risques incendie, explosion",
        "Connaissance situation d'urgence",
        "Risques liés à l'activité physique  - manutention manuelle et mécanique",
        "Prise en compte demandes CARSAT / Direction",
        "Organisation chantier",
        "Réalisation des actions précédentes",
        "Autres risques"
    ],
    "Environnement": [
        "Propreté générale du chantier",
        "Protection sol, pelouse, flore",
        "Gestion des déchets",
        "Impact riverains",
        "Autres"
    ]
}

# Initialize session state for all form fields if they don't exist
def init_session_state():
    if 'initialized' not in st.session_state:
        defaults = {
            'nom_client': '',  # New field for client name
            'date': datetime.now().date(),
            'heure': '',
            'adresse': '',
            'presence_sst': 'Non',
            'effectif': 0,            
            'conducteur': '',
            'chef_chantier': '',
            'contact_chantier': '',
            'redacteur_rapport': '',
            'travaux_selectionnes': [],
            'travaux_autres': '',
            'theme_visite': '',
            'evaluation_generale': '',
            'lien_photos': ''  # Nouveau champ pour le lien Dropbox
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
                
        # Initialize criteria fields
        for cat in ['Administratif', 'Sécurité', 'Environnement']:
            for critere in categories[cat]:
                eval_key = f"{cat}_{critere}"
                obs_key = f"obs_{cat}_{critere}"
                if eval_key not in st.session_state:
                    st.session_state[eval_key] = "Non Applicable"
                if obs_key not in st.session_state:
                    st.session_state[obs_key] = ""
                    
        st.session_state['initialized'] = True

# Initialize session state
if "file_processed" not in st.session_state:
    st.session_state.file_processed = False
    init_session_state()

# Add file loader at the top
uploaded_json = st.file_uploader("📂 Charger une fiche sauvegardée", type=['json'])

if uploaded_json is not None and not st.session_state.file_processed:
    try:
        # Load the JSON content with proper UTF-8 encoding
        content = uploaded_json.read().decode('utf-8-sig')
        saved_data = json.loads(content)        # Validate required fields (excluding nom_client for backward compatibility)
        required_fields = ['date', 'adresse', 'conducteur', 'chef_chantier', 'contact_chantier']
        missing_fields = [field for field in required_fields if field not in saved_data]
        if missing_fields:
            st.error(f"❌ Champs requis manquants dans le fichier : {', '.join(missing_fields)}")
            st.stop()
              # Handle nom_client field for backward compatibility
        if 'nom_client' not in saved_data:
            saved_data['nom_client'] = ''  # Set empty string for older files
            st.session_state['nom_client'] = ''  # Ensure it's set in session state
            
        # Convert date string to datetime.date object
        if 'date' in saved_data:
            try:
                date_str = saved_data['date']
                parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                st.session_state['date'] = parsed_date
            except ValueError:
                st.error("❌ Format de date invalide dans le fichier")
                st.stop()
                  # Set all basic form fields from saved data        
        basic_fields = [
            'nom_client', 'heure', 'adresse', 'presence_sst', 'effectif', 'conducteur',
            'chef_chantier', 'contact_chantier', 'redacteur_rapport', 'travaux_selectionnes',
            'travaux_autres', 'theme_visite', 'evaluation_generale', 'lien_photos'
        ]
        for field in basic_fields:
            if field in saved_data:
                st.session_state[field] = saved_data[field]
        
        # Set criteria evaluations and observations
        for cat in ['Administratif', 'Sécurité', 'Environnement']:
            for key, value in saved_data.items():
                if key.startswith(f"{cat}_") or key.startswith(f"obs_{cat}_"):
                    st.session_state[key] = value
                    
        # Show summary of loaded data
        loaded_fields = len([k for k in saved_data.keys() if saved_data[k]])
        st.session_state.file_processed = True
        st.success(f"✅ Fiche chargée avec succès ! - Date de visite : {saved_data['date']} - Adresse : {saved_data['adresse']} - {loaded_fields} champs chargés au total")
        
        st.rerun()
        
    except json.JSONDecodeError:
        st.error("""❌ Le fichier n'est pas un fichier JSON valide. 
        Assurez-vous que le fichier a été généré par cette application.""")
    except ValueError as e:
        st.error(f"❌ Format de données invalide : {str(e)}")
    except Exception as e:
        st.error(f"""❌ Erreur lors du chargement du fichier : {str(e)}
        Si le problème persiste, contactez le support technique.""")

# Clear the processed flag when no file is uploaded
if uploaded_json is None:
    st.session_state.file_processed = False

st.title("🏗️ Rapport de Visite – BR CONSULT")

st.subheader("🧱 Informations générales")

col1, col2 = st.columns(2)

with col1:
    st.date_input("Date de la visite", key='date')
    st.text_input("Nom du client*", key='nom_client')
    st.text_input("Adresse du chantier*", key='adresse')

with col2:
    st.text_input("Heure de la visite (format HH:MM)", 
                  placeholder="08:30", 
                  key='heure')
    
    if st.session_state['heure'] and not re.match(r"^\d{2}:\d{2}$", st.session_state['heure']):
        st.warning("⏰ Merci d'utiliser le format HH:MM, par exemple 14:45.")

st.radio("Présence de sous-traitant :", 
         ["Oui", "Non"], 
         horizontal=True,
         key='presence_sst')

st.number_input("Effectif sur site", 
                min_value=0, 
                step=1, 
                format="%d", 
                help="Nombre d'ouvriers présents sur le chantier",
                key='effectif')

st.text_input("Conducteur de travaux*", key='conducteur')
st.text_input("Chef de chantier*", key='chef_chantier')
st.text_input("Contact chantier*", key='contact_chantier')
st.text_input("Rédacteur du rapport*", key='redacteur_rapport')

# Type de travaux
st.subheader("🔨 Type de travaux")

travaux_types = [
    "Ravalement", "Gros œuvre", "Maçonnerie", "Décapage", "Serrurerie", "Ponçage", "Carrelage",
    "Couverture", "Intérieur", "Point", "Lavage", "Sablage", "Étanchéité", "Découpe",
    "ITE", "Peinture", "Bardage", "Zinguerie", "Piochage"
]

st.multiselect(
    "Sélectionnez les travaux effectués :", 
    travaux_types,
    key='travaux_selectionnes'
)

st.text_input("Autres travaux (si non listés)", key='travaux_autres')

# Thématique de la visite + évaluation générale
st.subheader("📌 Thème de la visite")
st.text_input("Quel est le thème principal de cette visite ?", key='theme_visite')

st.subheader("📝 Évaluation générale du chantier")
st.text_area(
    "Commentaires et observations générales sur l'état du chantier",
    height=200,
    placeholder="Rédigez ici vos remarques générales : sécurité, ambiance, organisation…",
    key='evaluation_generale'
)

# Fonction gestion critères d'évaluation
def afficher_critere(categorie, nom_critere):
    col1, col2 = st.columns([1, 2])
    with col1:
        options = ["Non Applicable", "Non Satisfaisant", "Partiellement Satisfaisant", "Satisfaisant"]
        st.selectbox(
            f"{nom_critere}",
            options,
            key=f"{categorie}_{nom_critere}"
        )
    with col2:
        st.text_input(f"Observations", 
                      key=f"obs_{categorie}_{nom_critere}")

# Afficher les critères dynamiquement et stocker les notes
st.subheader("🧪 Évaluation par critère")

# Stockage des notes
notes_par_categorie = {}

for cat, criteres in categories.items():
    st.markdown(f"### 🔹 {cat}")
    notes = []
    for crit in criteres:
        afficher_critere(cat, crit)
        note = st.session_state.get(f"{cat}_{crit}", "Non Applicable")
        notes.append(note)
    notes_par_categorie[cat] = notes

# Pondérations par catégorie
pondérations = {
    "Administratif": 0.5,
    "Sécurité": 3,
    "Environnement": 1
}

# Valeurs pondérées des notes
valeurs = {
    "Satisfaisant": 1,
    "Partiellement Satisfaisant": 2/3,
    "Non Satisfaisant": 1/3,
    "Non Applicable": None
}

notes_finales = {}
note_globale_pondérée = 0
somme_pondérations = 0

for cat, notes in notes_par_categorie.items():
    total = 0
    count = 0
    for note in notes:
        valeur = valeurs.get(note)
        if valeur is not None:
            total += valeur
            count += 1
    if count > 0:
        moyenne = total / count
        note_pourcentage = round(moyenne * 100)
        notes_finales[cat] = note_pourcentage
        note_globale_pondérée += note_pourcentage * pondérations[cat]
        somme_pondérations += pondérations[cat]
    else:
        notes_finales[cat] = "NA"

# Calcul de la note chantier
if somme_pondérations > 0:
    note_chantier = round(note_globale_pondérée / somme_pondérations, 1)
else:
    note_chantier = "NA"

# Section Photos du chantier - NOUVEAU
st.subheader("📸 Photos du chantier")
st.text_input(
    "Lien Dropbox vers les photos du chantier", 
    placeholder="https://www.dropbox.com/sh/...",
    help="Collez ici le lien de partage Dropbox contenant toutes les photos du chantier",
    key='lien_photos'
)

# Affichage des résultats
st.subheader("📊 Résultat de l'évaluation")

for cat, note in notes_finales.items():
    if isinstance(note, int):
        st.progress(note / 100)
        st.write(f"**{cat}** : {note}%")
    else:
        st.write(f"**{cat}** : NA")

st.markdown("---")
st.markdown(f"### 🧮 **Note globale du chantier : {note_chantier}%**")

# Ajout feuille d'émargement
st.subheader("📝 Feuille d'émargement")

emargement = st.file_uploader(
    "Ajoutez une photo ou scan de la feuille d'émargement",
    type=["jpg", "jpeg", "png", "pdf"],
    key="emargement"
)

if emargement:
    if emargement.type != "application/pdf":
        st.image(emargement, width=300)
    else:
        st.info("PDF chargé. Il sera inclus dans le rapport final.")

# Configuration pour la génération PDF
def configure_wkhtmltopdf():
    # On Streamlit Cloud, wkhtmltopdf is installed via packages.txt
    if os.path.exists('/usr/bin/wkhtmltopdf'):
        return pdfkit.configuration(wkhtmltopdf='/usr/bin/wkhtmltopdf')
    
    # For Windows local development
    if platform.system() == 'Windows':
        windows_paths = [
            r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe',
            r'C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe'
        ]
        for path in windows_paths:
            if os.path.exists(path):
                return pdfkit.configuration(wkhtmltopdf=path)
    
    # Default configuration
    try:
        return pdfkit.configuration()
    except Exception as e:
        st.warning("Note: PDF generation requires wkhtmltopdf to be installed")
        return None

# Initialize wkhtmltopdf configuration
config = configure_wkhtmltopdf()

st.subheader("💾 Sauvegarde de l'avancement")

# Bouton de sauvegarde
if st.button("💾 Sauvegarder l'avancement"):
    if not check_required_fields(st.session_state['adresse'], st.session_state['conducteur'], 
            st.session_state['chef_chantier'], st.session_state['contact_chantier'],
            st.session_state['redacteur_rapport']):
        st.error("❌ Veuillez remplir tous les champs obligatoires (*) avant de sauvegarder")
        st.stop()
        
    try:
        save_data = {
            'date': str(st.session_state['date']),
            'heure': st.session_state['heure'],
            'nom_client': st.session_state['nom_client'],
            'adresse': st.session_state['adresse'],
            'presence_sst': st.session_state['presence_sst'],
            'effectif': st.session_state['effectif'],
            'conducteur': st.session_state['conducteur'],
            'chef_chantier': st.session_state['chef_chantier'],
            'contact_chantier': st.session_state['contact_chantier'],
            'redacteur_rapport': st.session_state['redacteur_rapport'],
            'travaux_selectionnes': st.session_state['travaux_selectionnes'],
            'travaux_autres': st.session_state['travaux_autres'],
            'theme_visite': st.session_state['theme_visite'],
            'evaluation_generale': st.session_state['evaluation_generale'],
            'lien_photos': st.session_state['lien_photos'],
            'note_chantier': note_chantier if isinstance(note_chantier, (int, float)) else "NA"
        }
        
        for cat in ['Administratif', 'Sécurité', 'Environnement']:
            for critere in categories[cat]:
                eval_key = f"{cat}_{critere}"
                obs_key = f"obs_{cat}_{critere}"
                save_data[eval_key] = st.session_state[eval_key]
                save_data[obs_key] = st.session_state[obs_key]

        now = datetime.now()
        filename = f"visite_chantier_{now.strftime('%Y%m%d_%H%M%S')}.json"
        json_str = json.dumps(save_data, ensure_ascii=False, indent=2)
        json_bytes = json_str.encode('utf-8-sig')
        
        st.download_button(
            label="📥 Télécharger la fiche",
            data=json_bytes,
            file_name=filename,
            mime="application/json",
        )
        
        st.success("✅ Données sauvegardées avec succès ! Cliquez sur le bouton ci-dessus pour télécharger le fichier.")
        
    except Exception as e:
        st.error(f"❌ Erreur lors de la sauvegarde : {str(e)}")

st.subheader("📄 Export PDF")

# Add validation before allowing PDF generation
if not check_required_fields(st.session_state['adresse'], st.session_state['conducteur'], 
                            st.session_state['chef_chantier'], st.session_state['contact_chantier'],
                            st.session_state['redacteur_rapport']):
    st.warning("⚠️ Merci de remplir tous les champs obligatoires marqués par une astérisque.")
else:
    if st.button("📤 Générer le PDF"):
        current_date = datetime.now().strftime("%d-%m-%Y")
        
        # Enhanced HTML with BR CONSULT branding and page breaks
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600;700&family=Open+Sans:wght@300;400;600&display=swap');
                
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                @page {{
                    size: A4;
                    margin: 5mm 5mm 5mm 5mm;
                }}
                
                body {{
                    font-family: 'Open Sans', Arial, sans-serif;
                    line-height: 1.6;
                    color: #2c2c2c;
                    background: #ffffff;
                    width: 100%;
                    margin: 0;
                    padding: 0;
                }}
                
                .container {{
                    width: 100%;
                    margin: 0 auto;
                    background: white;
                    padding: 0;
                }}
                
                /* Wrapper for page content with borders */
                .page-wrapper {{
                    border: 2px solid #dc2626;
                    border-radius: 8px;
                    margin: 5mm;
                    padding: 15px;
                    min-height: calc(297mm - 20mm);
                    position: relative;
                    page-break-inside: avoid;
                    page-break-after: always;
                }}
                
                .page-wrapper:last-child {{
                    page-break-after: avoid;
                }}
                
                /* Header with title for first page only */
                .header-with-title {{
                    background: #ffffff;
                    color: #000000;
                    padding: 15px 30px 20px 30px;
                    position: relative;
                    min-height: 120px;
                    margin: -15px -15px 20px -15px;
                    border-bottom: 3px solid #dc2626;
                    border-radius: 6px 6px 0 0;
                }}
                
                /* Header with logo only for other pages */
                .header-logo-only {{
                    position: absolute;
                    top: 15px;
                    left: 30px;
                    z-index: 10;
                }}
                
                .logo-container {{
                    position: absolute;
                    left: 30px;
                    top: 15px;
                }}
                
                .logo-container img {{
                    width: 60px;
                    height: auto;
                    display: block;
                }}
                
                .page-title {{
                    font-family: 'Montserrat', sans-serif;
                    font-size: 2em;
                    font-weight: 700;
                    letter-spacing: 1px;
                    color: #000000;
                    text-transform: uppercase;
                    text-align: center;
                    padding-top: 60px;
                }}
                
                /* Content sections */
                .content {{
                    padding: 0 10px;
                }}
                
                .content-with-logo {{
                    padding: 80px 10px 10px 10px;
                }}
                
                .section {{
                    margin-bottom: 15px;
                    padding: 15px;
                    background: #fafafa;
                    border-radius: 6px;
                    border: 1px solid #e5e5e5;
                    position: relative;
                    page-break-inside: avoid;
                }}
                
                .section::before {{
                    content: '';
                    position: absolute;
                    left: 0;
                    top: 0;
                    bottom: 0;
                    width: 3px;
                    background: #dc2626;
                    border-radius: 6px 0 0 6px;
                }}
                
                .section-title {{
                    color: #000000;
                    font-family: 'Montserrat', sans-serif;
                    font-size: 1.4em;
                    font-weight: 600;
                    margin-bottom: 20px;
                    padding-bottom: 10px;
                    border-bottom: 2px solid #dc2626;
                    display: flex;
                    align-items: center;
                }}
                
                .icon {{
                    margin-right: 10px;
                    font-size: 1em;
                    color: #dc2626;
                }}
                
                /* Info grid */
                .info-grid {{
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 15px;
                    margin-bottom: 15px;
                }}
                
                .info-item {{
                    padding: 12px;
                    background: white;
                    border-radius: 5px;
                    border: 1px solid #e5e5e5;
                }}
                
                .info-label {{
                    font-weight: 600;
                    color: #666666;
                    font-size: 0.8em;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    margin-bottom: 4px;
                }}
                
                .info-value {{
                    color: #000000;
                    font-size: 1em;
                    font-weight: 500;
                }}
                
                /* Photos link section */
                .photos-link-box {{
                    background: #e3f2fd;
                    border: 2px solid #1976d2;
                    border-radius: 6px;
                    padding: 15px;
                    margin: 15px 0;
                    text-align: center;
                }}
                
                .photos-link-box a {{
                    color: #1976d2;
                    font-weight: 600;
                    text-decoration: none;
                    font-size: 0.85em;
                    word-break: break-all;
                    display: inline-block;
                    max-width: 100%;
                }}
                
                /* Results presentation style */
                .results-grid {{
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 20px;
                    margin: 20px 0;
                    text-align: center;
                }}
                
                .result-item {{
                    padding: 25px 15px;
                    background: white;
                    border-radius: 6px;
                    border: 2px solid #e5e5e5;
                }}
                
                .result-category {{
                    font-family: 'Montserrat', sans-serif;
                    font-size: 0.95em;
                    font-weight: 700;
                    text-transform: uppercase;
                    letter-spacing: 0.8px;
                    color: #2c2c2c;
                    margin-bottom: 10px;
                }}
                
                .result-score {{
                    font-family: 'Montserrat', sans-serif;
                    font-size: 2.8em;
                    font-weight: 700;
                    color: #dc2626;
                    line-height: 1;
                }}
                
                /* Global score - BR CONSULT style */
                .global-score {{
                    text-align: center;
                    padding: 30px;
                    background: #000000;
                    color: white;
                    border-radius: 8px;
                    margin: 30px 0;
                    position: relative;
                }}
                
                .score-value {{
                    font-family: 'Montserrat', sans-serif;
                    font-size: 3.5em;
                    font-weight: 700;
                    margin: 0;
                    color: white;
                    display: inline;
                }}
                
                .score-label {{
                    font-family: 'Open Sans', sans-serif;
                    font-size: 1.1em;
                    font-weight: 400;
                    letter-spacing: 1px;
                    text-transform: uppercase;
                    margin-bottom: 15px;
                }}
                
                /* Category headers */
                .category-header {{
                    font-family: 'Montserrat', sans-serif;
                    color: #000000;
                    margin: 10px 0 10px 0;
                    font-size: 1.3em;
                    font-weight: 600;
                    padding-left: 12px;
                    border-left: 3px solid #dc2626;
                }}
                
                /* Criteria table - BR CONSULT style */
                .criteria-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 10px;
                    margin-bottom: 15px;
                    background: white;
                    border-radius: 6px;
                    overflow: hidden;
                    box-shadow: 0 1px 5px rgba(0,0,0,0.05);
                }}
                
                .criteria-table th {{
                    background: #2c2c2c;
                    color: white;
                    padding: 15px 12px;
                    text-align: left;
                    font-weight: 600;
                    font-size: 0.9em;
                    letter-spacing: 0.5px;
                }}
                
                .criteria-table th:first-child {{
                    border-left: 3px solid #dc2626;
                }}
                
                .criteria-table td {{
                    padding: 12px;
                    border-bottom: 1px solid #f0f0f0;
                    background: white;
                    font-size: 0.9em;
                }}
                
                .criteria-table tr:last-child td {{
                    border-bottom: none;
                }}
                
                /* Status badges - BR CONSULT style */
                .status {{
                    display: inline-block;
                    padding: 5px 12px;
                    border-radius: 15px;
                    font-size: 0.8em;
                    font-weight: 600;
                    text-align: center;
                    min-width: 120px;
                    letter-spacing: 0.2px;
                }}
                
                .status-satisfaisant {{
                    background: #dcfce7;
                    color: #166534;
                    border: 1px solid #bbf7d0;
                }}
                
                .status-partiellement {{
                    background: #fef3c7;
                    color: #92400e;
                    border: 1px solid #fde68a;
                }}
                
                .status-non-satisfaisant {{
                    background: #fee2e2;
                    color: #991b1b;
                    border: 1px solid #fecaca;
                }}
                
                .status-na {{
                    background: #f3f4f6;
                    color: #4b5563;
                    border: 1px solid #e5e7eb;
                }}
                
                /* Observations */
                .observation {{
                    font-style: italic;
                    color: #6b7280;
                    font-size: 0.85em;
                    margin-top: 3px;
                    line-height: 1.3;
                }}
                
                /* Work types - BR CONSULT style */
                .work-tags {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 8px;
                    margin-top: 12px;
                }}
                
                .work-tag {{
                    background: #fee2e2;
                    color: #dc2626;
                    padding: 6px 15px;
                    border-radius: 20px;
                    font-size: 0.85em;
                    font-weight: 600;
                    border: 1px solid #fecaca;
                }}
                
                /* Print styles */
                @media print {{
                    body {{
                        background: white;
                        margin: 0;
                        padding: 0;
                    }}
                    
                    .page-wrapper {{
                        border: 2px solid #dc2626;
                        margin: 5mm;
                        page-break-inside: avoid;
                    }}
                    
                    .container {{
                        width: 100%;
                    }}
                    
                    .section {{
                        page-break-inside: avoid;
                    }}
                    
                    .criteria-table {{
                        page-break-inside: auto;
                    }}
                    
                    .criteria-table tr {{
                        page-break-inside: avoid;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <!-- Page 1 -->
                <div class="page-wrapper">
                    <!-- Header with title -->
                    <div class="header-with-title">
                        {'''
                        <div class="logo-container">
                            <img src="data:image/jpeg;base64,''' + str(LOGO_BR_BASE64) + '''" alt="BR CONSULT Logo" />
                        </div>
                        ''' if LOGO_BR_BASE64 else ''}
                        <div class="page-title">RAPPORT DE VISITE CHANTIER</div>
                    </div>
                    
                    <!-- Content -->
                    <div class="content">
                        <!-- General Information -->
                        <div class="section">
                            <h2 class="section-title">
                                <span class="icon">📋</span>
                                Informations Générales
                            </h2>
                            <div class="info-grid">
                                <div class="info-item">
                                    <div class="info-label">Nom du client</div>
                                    <div class="info-value">{st.session_state['nom_client']}</div>
                                </div>
                                <div class="info-item">
                                    <div class="info-label">Date de visite</div>
                                    <div class="info-value">{st.session_state['date'].strftime('%d/%m/%Y')}</div>
                                </div>
                                <div class="info-item">
                                    <div class="info-label">Heure de visite</div>
                                    <div class="info-value">{st.session_state['heure'] or 'Non renseignée'}</div>
                                </div>
                                <div class="info-item">
                                    <div class="info-label">Adresse du chantier</div>
                                    <div class="info-value">{st.session_state['adresse']}</div>
                                </div>
                                <div class="info-item">
                                    <div class="info-label">Effectif sur site</div>
                                    <div class="info-value">{st.session_state['effectif']} personnes</div>
                                </div>
                                <div class="info-item">
                                    <div class="info-label">Conducteur de travaux</div>
                                    <div class="info-value">{st.session_state['conducteur']}</div>
                                </div>
                                <div class="info-item">
                                    <div class="info-label">Chef de chantier</div>
                                    <div class="info-value">{st.session_state['chef_chantier']}</div>
                                </div>
                                <div class="info-item">
                                    <div class="info-label">Contact chantier</div>
                                    <div class="info-value">{st.session_state['contact_chantier']}</div>
                                </div>
                                <div class="info-item">
                                    <div class="info-label">Rédacteur du rapport</div>
                                    <div class="info-value">{st.session_state['redacteur_rapport']}</div>
                                </div>
                                <div class="info-item">
                                    <div class="info-label">Présence sous-traitant</div>
                                    <div class="info-value">{st.session_state['presence_sst']}</div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Work Types -->
                        <div class="section">
                            <h2 class="section-title">
                                <span class="icon">🔨</span>
                                Type de Travaux
                            </h2>
                            <div class="work-tags">
        """
        
        # Add selected works
        for travail in st.session_state['travaux_selectionnes']:
            html += f'<span class="work-tag">{travail}</span>'
        
        if st.session_state['travaux_autres']:
            html += f'<span class="work-tag">{st.session_state["travaux_autres"]}</span>'
        
        html += f"""
                            </div>
                        </div>
                        
                        <!-- Visit Theme -->
                        {f'''
                        <div class="section">
                            <h2 class="section-title">
                                <span class="icon">🎯</span>
                                Thème de la Visite
                            </h2>
                            <p>{st.session_state["theme_visite"] or "Non spécifié"}</p>
                        </div>
                        ''' if st.session_state['theme_visite'] else ''}
                        
                        <!-- General Evaluation -->
                        {f'''
                        <div class="section">
                            <h2 class="section-title">
                                <span class="icon">📝</span>
                                Évaluation Générale
                            </h2>
                            <p>{st.session_state["evaluation_generale"] or "Aucune observation générale"}</p>
                        </div>
                        ''' if st.session_state['evaluation_generale'] else ''}
                        
                        <!-- Photos Link Section -->
                        {f'''
                        <div class="section">
                            <h2 class="section-title">
                                <span class="icon">📸</span>
                                Photos du Chantier
                            </h2>
                            <div class="photos-link-box">
                                <p style="margin-bottom: 8px;">Les photos du chantier sont disponibles via le lien suivant :</p>
                                <a href="{st.session_state["lien_photos"]}" target="_blank">{st.session_state["lien_photos"]}</a>
                            </div>
                        </div>
                        ''' if st.session_state['lien_photos'] else ''}
                    </div>
                </div>
                
                <!-- Page 2 - Scores -->
                <div class="page-wrapper">
                    {'''
                    <div class="header-logo-only">
                        <img src="data:image/jpeg;base64,''' + str(LOGO_BR_BASE64) + '''" alt="BR CONSULT Logo" style="width: 60px; height: auto;" />
                    </div>
                    ''' if LOGO_BR_BASE64 else ''}
                    
                    <div class="content-with-logo">
                        <div class="section">
                            <h2 class="section-title">
                                <span class="icon">📊</span>
                                Résultats de l'Évaluation
                            </h2>
                            <div class="results-grid">
        """
        
        # Add results in grid format
        for cat, note in notes_finales.items():
            score_display = f"{note}%" if isinstance(note, int) else "N/A"
            html += f"""
                                <div class="result-item">
                                    <div class="result-category">{cat.upper()}</div>
                                    <div class="result-score">{score_display}</div>
                                </div>
            """
        
        html += f"""
                            </div>
                            
                            <!-- Global Score -->
                            <div class="global-score">
                                <div class="score-label">Note Globale du Chantier</div>
                                <div class="score-value">{note_chantier}%</div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Page 3 - Detailed Criteria -->
                <div class="page-wrapper">
                    {'''
                    <div class="header-logo-only">
                        <img src="data:image/jpeg;base64,''' + str(LOGO_BR_BASE64) + '''" alt="BR CONSULT Logo" style="width: 60px; height: auto;" />
                    </div>
                    ''' if LOGO_BR_BASE64 else ''}
                    
                    <div class="content-with-logo">
                        <div class="section">
                            <h2 class="section-title">
                                <span class="icon">🔍</span>
                                Détail des Critères d'Évaluation
                            </h2>
        """
        
        # Add detailed criteria for each category
        for idx, (cat, criteres) in enumerate(categories.items()):
            # Start a new page for each category except the first one
            if idx > 0:
                html += f"""
                        </div>
                    </div>
                </div>
                
                <div class="page-wrapper">
                    {'''
                    <div class="header-logo-only">
                        <img src="data:image/jpeg;base64,''' + str(LOGO_BR_BASE64) + '''" alt="BR CONSULT Logo" style="width: 60px; height: auto;" />
                    </div>
                    ''' if LOGO_BR_BASE64 else ''}
                    
                    <div class="content-with-logo">
                        <div class="section" style="margin-bottom: 10px;">
                """
            
            html += f"""
                            <h3 class="category-header" style="margin-top: 10px; margin-bottom: 10px;">{cat}</h3>
                            <table class="criteria-table">
                                <thead>
                                    <tr>
                                        <th style="width: 40%;">Critère</th>
                                        <th style="width: 25%;">Évaluation</th>
                                        <th style="width: 35%;">Observations</th>
                                    </tr>
                                </thead>
                                <tbody>
            """
            
            for crit in criteres:
                note_key = f"{cat}_{crit}"
                obs_key = f"obs_{cat}_{crit}"
                note = st.session_state.get(note_key, "Non noté")
                obs = st.session_state.get(obs_key, "")
                
                # Determine status class
                status_class = ""
                if note == "Satisfaisant":
                    status_class = "status-satisfaisant"
                elif note == "Partiellement Satisfaisant":
                    status_class = "status-partiellement"
                elif note == "Non Satisfaisant":
                    status_class = "status-non-satisfaisant"
                else:
                    status_class = "status-na"
                
                html += f"""
                                    <tr>
                                        <td>{crit}</td>
                                        <td><span class="status {status_class}">{note}</span></td>
                                        <td><span class="observation">{obs if obs else '-'}</span></td>
                                    </tr>
                """
            
            html += """
                                </tbody>
                            </table>
            """
            
            # Add attendance sheet section directly after Environment criteria
            if cat == "Environnement":
                html += """
                            <!-- Attendance Sheet -->
                            <div style="margin-top: 20px;">
                                <h2 class="section-title" style="margin-bottom: 15px;">
                                    <span class="icon">✍️</span>
                                    Feuille d'Émargement - Sensibilisation
                                </h2>
                """
                
                feuille = st.session_state.get("emargement")
                if feuille and feuille.type.startswith("image"):
                    feuille.seek(0)  # Reset file pointer
                    img_base64 = base64.b64encode(feuille.read()).decode()
                    html += f"""
                                <div style="text-align: center; margin: 15px 0;">
                                    <img src="data:image/jpeg;base64,{img_base64}" style="max-width: 100%; max-height: 400px; border-radius: 6px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                                </div>
                    """
                elif feuille and feuille.type == "application/pdf":
                    html += """
                                <p style="text-align: center; padding: 20px; background: #f8f9fa; border-radius: 6px;">
                                    <span style="font-size: 1.1em;">📎 Un fichier PDF a été joint comme feuille d'émargement</span>
                                </p>
                    """
                else:
                    html += """
                                <p style="text-align: center; padding: 20px; background: #f8f9fa; border-radius: 6px; color: #6c757d;">
                                    Aucune feuille d'émargement ajoutée
                                </p>
                    """
                
                html += """
                            </div>
                """
        
        html += """
                        </div>
                    </div>
                </div>
            </div>
        </body>
    </html>
"""        # Generate PDF
        if config is None:
            st.error("PDF generation is not available. Please make sure wkhtmltopdf is installed.")
            st.stop()
            
        try:

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
                pdfkit.from_string(html, f.name, configuration=config, options={
                    'enable-local-file-access': None,
                    'encoding': 'UTF-8',
                    'page-size': 'A4',
                    'margin-top': '0mm',
                    'margin-right': '0mm',
                    'margin-bottom': '0mm',
                    'margin-left': '0mm',
                    'no-outline': None,
                    'print-media-type': None,
                    'dpi': 300
                })
                
                with open(f.name, "rb") as file:
                    st.download_button(
                        label="📥 Télécharger le PDF",
                        data=file,
                        file_name=f"rapport_visite_chantier_{current_date}.pdf",
                        mime="application/pdf"
                    )
                    
            st.success("✅ PDF généré avec succès !")
            
        except Exception as e:
            st.error(f"❌ Erreur lors de la génération du PDF : {str(e)}")
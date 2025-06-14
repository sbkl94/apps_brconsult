import streamlit as st
import re
import io
import pdfkit
import tempfile 
import base64 
import json
from datetime import datetime

def check_required_fields(adresse, conducteur, chef_chantier, contact_chantier, redacteur_rapport):
    return all([adresse.strip(), conducteur.strip(), chef_chantier.strip(), contact_chantier.strip(), redacteur_rapport.strip()])

st.set_page_config(page_title="FICHE DE VISITE BR CONSULT", layout="wide")

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
        "Manutention manuelle et mécanique",
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
        saved_data = json.loads(content)
        
        # Validate required fields
        required_fields = ['date', 'adresse', 'conducteur', 'chef_chantier', 'contact_chantier']
        missing_fields = [field for field in required_fields if field not in saved_data]
        if missing_fields:
            st.error(f"❌ Champs requis manquants dans le fichier : {', '.join(missing_fields)}")
            st.stop()
            
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
            'heure', 'adresse', 'presence_sst', 'effectif', 'conducteur',
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

st.title("🏗️ Fiche de Visite – BR CONSULT")

st.subheader("🧱 Informations générales")

col1, col2 = st.columns(2)

with col1:
    st.date_input("Date de la visite", key='date')
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

# Configuration pour Windows
config = pdfkit.configuration(wkhtmltopdf="C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe")

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
                
                body {{
                    font-family: 'Open Sans', Arial, sans-serif;
                    line-height: 1.6;
                    color: #2c2c2c;
                    background: #ffffff;
                    min-height: 100vh;
                    display: flex;
                    flex-direction: column;
                }}
                
                .container {{
                    flex: 1;
                    max-width: 800px;
                    margin: 0 auto;
                    background: white;
                    box-shadow: 0 0 30px rgba(0,0,0,0.1);
                    display: flex;
                    flex-direction: column;
                }}
                
                /* Header - BR CONSULT style */
                .header {{
                    background: #ffffff;
                    color: #000000;
                    padding: 50px 40px 30px 40px;
                    text-align: center;
                    position: relative;
                }}
                
                .header::after {{
                    content: '';
                    position: absolute;
                    bottom: 0;
                    left: 0;
                    right: 0;
                    height: 5px;
                    background: #dc2626;
                }}
                
                .page-title {{
                    font-family: 'Montserrat', sans-serif;
                    font-size: 2.5em;
                    font-weight: 700;
                    margin-bottom: 30px;
                    letter-spacing: 1px;
                    color: #000000;
                    text-transform: uppercase;
                }}
                
                /* Content sections */
                .content {{
                    flex: 1;
                    padding: 40px;
                }}
                
                .section {{
                    margin-bottom: 35px;
                    padding: 30px;
                    background: #fafafa;
                    border-radius: 8px;
                    border: 1px solid #e5e5e5;
                    position: relative;
                    page-break-inside: avoid;
                    break-inside: avoid;
                }}
                
                .section::before {{
                    content: '';
                    position: absolute;
                    left: 0;
                    top: 0;
                    bottom: 0;
                    width: 4px;
                    background: #dc2626;
                    border-radius: 8px 0 0 8px;
                }}
                
                .section-title {{
                    color: #000000;
                    font-family: 'Montserrat', sans-serif;
                    font-size: 1.6em;
                    font-weight: 600;
                    margin-bottom: 25px;
                    padding-bottom: 12px;
                    border-bottom: 2px solid #dc2626;
                    display: flex;
                    align-items: center;
                    page-break-after: avoid;
                    break-after: avoid;
                }}
                
                .icon {{
                    margin-right: 12px;
                    font-size: 1.1em;
                    color: #dc2626;
                }}
                
                /* Info grid */
                .info-grid {{
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 20px;
                    margin-bottom: 20px;
                }}
                
                .info-item {{
                    padding: 15px;
                    background: white;
                    border-radius: 6px;
                    border: 1px solid #e5e5e5;
                    transition: all 0.3s ease;
                }}
                
                .info-item:hover {{
                    border-color: #dc2626;
                    box-shadow: 0 2px 8px rgba(220, 38, 38, 0.1);
                }}
                
                .info-label {{
                    font-weight: 600;
                    color: #666666;
                    font-size: 0.85em;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    margin-bottom: 5px;
                }}
                
                .info-value {{
                    color: #000000;
                    font-size: 1.1em;
                    font-weight: 500;
                }}
                
                /* Photos link section */
                .photos-link-box {{
                    background: #e3f2fd;
                    border: 2px solid #1976d2;
                    border-radius: 8px;
                    padding: 20px;
                    margin: 20px 0;
                    text-align: center;
                }}
                
                .photos-link-box a {{
                    color: #1976d2;
                    font-weight: 600;
                    text-decoration: none;
                    font-size: 0.9em;
                    word-break: break-all;
                    display: inline-block;
                    max-width: 100%;
                }}
                
                .photos-link-box a:hover {{
                    text-decoration: underline;
                }}
                
                /* Results presentation style */
                .results-grid {{
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 30px;
                    margin: 30px 0;
                    text-align: center;
                }}
                
                .result-item {{
                    padding: 30px 20px;
                    background: white;
                    border-radius: 8px;
                    border: 2px solid #e5e5e5;
                    transition: all 0.3s ease;
                }}
                
                .result-item:hover {{
                    border-color: #dc2626;
                    transform: translateY(-5px);
                    box-shadow: 0 5px 20px rgba(220, 38, 38, 0.15);
                }}
                
                .result-category {{
                    font-family: 'Montserrat', sans-serif;
                    font-size: 1.1em;
                    font-weight: 700;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    color: #2c2c2c;
                    margin-bottom: 15px;
                }}
                
                .result-score {{
                    font-family: 'Montserrat', sans-serif;
                    font-size: 3.5em;
                    font-weight: 700;
                    color: #dc2626;
                    line-height: 1;
                    text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
                }}
                
                /* Global score - BR CONSULT style */
                .global-score {{
                    text-align: center;
                    padding: 40px;
                    background: #000000;
                    color: white;
                    border-radius: 12px;
                    margin: 40px 0;
                    position: relative;
                    page-break-inside: avoid;
                    break-inside: avoid;
                }}
                
                .score-value {{
                    font-family: 'Montserrat', sans-serif;
                    font-size: 4.5em;
                    font-weight: 700;
                    margin: 0;
                    color: white;
                    display: inline;
                }}
                
                .score-label {{
                    font-family: 'Open Sans', sans-serif;
                    font-size: 1.2em;
                    font-weight: 400;
                    letter-spacing: 1px;
                    text-transform: uppercase;
                    margin-bottom: 20px;
                }}
                
                /* Page breaks */
                .page-break {{
                    page-break-after: always;
                    break-after: always;
                }}
                
                .page-break-before {{
                    page-break-before: always;
                    break-before: always;
                }}
                
                /* Criteria sections with page break control */
                .criteria-section {{
                    page-break-inside: avoid;
                    break-inside: avoid;
                    margin-bottom: 30px;
                }}
                
                .criteria-section.new-page {{
                    page-break-before: always;
                    break-before: always;
                }}
                
                /* Category headers */
                .category-header {{
                    font-family: 'Montserrat', sans-serif;
                    color: #000000;
                    margin: 30px 0 20px 0;
                    font-size: 1.5em;
                    font-weight: 600;
                    padding-left: 15px;
                    border-left: 4px solid #dc2626;
                    page-break-after: avoid;
                    break-after: avoid;
                }}
                
                /* Criteria table - BR CONSULT style */
                .criteria-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 25px;
                    background: white;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
                    page-break-inside: auto;
                }}
                
                .criteria-table th {{
                    background: #2c2c2c;
                    color: white;
                    padding: 18px 15px;
                    text-align: left;
                    font-weight: 600;
                    font-size: 0.95em;
                    letter-spacing: 0.5px;
                    page-break-after: avoid;
                    break-after: avoid;
                }}
                
                .criteria-table th:first-child {{
                    border-left: 4px solid #dc2626;
                }}
                
                .criteria-table td {{
                    padding: 15px;
                    border-bottom: 1px solid #f0f0f0;
                    background: white;
                    page-break-inside: avoid;
                    break-inside: avoid;
                }}
                
                .criteria-table tr:hover td {{
                    background: #fafafa;
                }}
                
                .criteria-table tr:last-child td {{
                    border-bottom: none;
                }}
                
                /* Status badges - BR CONSULT style */
                .status {{
                    display: inline-block;
                    padding: 6px 14px;
                    border-radius: 20px;
                    font-size: 0.85em;
                    font-weight: 600;
                    text-align: center;
                    min-width: 140px;
                    letter-spacing: 0.3px;
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
                    font-size: 0.9em;
                    margin-top: 5px;
                    line-height: 1.4;
                }}
                
                /* Work types - BR CONSULT style */
                .work-tags {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 10px;
                    margin-top: 15px;
                }}
                
                .work-tag {{
                    background: #fee2e2;
                    color: #dc2626;
                    padding: 8px 18px;
                    border-radius: 25px;
                    font-size: 0.9em;
                    font-weight: 600;
                    border: 1px solid #fecaca;
                }}
                
                /* Footer - BR CONSULT style */
                .footer {{
                    background: #000000;
                    color: white;
                    text-align: center;
                    padding: 30px;
                    font-size: 0.9em;
                    position: relative;
                    margin-top: auto;
                    page-break-inside: avoid;
                    break-inside: avoid;
                }}
                
                .footer::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 5px;
                    background: #dc2626;
                }}
                
                .footer-tagline {{
                    font-style: italic;
                    color: #cccccc;
                    margin-top: 10px;
                }}
                
                /* Print styles */
                @media print {{
                    body {{
                        background: white;
                    }}
                    .container {{
                        box-shadow: none;
                    }}
                    .section {{
                        border: 1px solid #ddd;
                        page-break-inside: avoid;
                    }}
                    .category-header {{
                        page-break-after: avoid;
                    }}
                    .criteria-table {{
                        page-break-inside: auto;
                    }}
                    .criteria-table tr {{
                        page-break-inside: avoid;
                    }}
                    .footer {{
                        position: fixed;
                        bottom: 0;
                        left: 0;
                        right: 0;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <!-- Header -->
                <div class="header">
                    <div class="page-title">FICHE DE VISITE CHANTIER</div>
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
                                <div class="info-label">Date de visite</div>
                                <div class="info-value">{st.session_state['date'].strftime('%d/%m/%Y')}</div>
                            </div>
                            <div class="info-item">
                                <div class="info-label">Heure</div>
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
                            <p style="margin-bottom: 10px;">Les photos haute définition du chantier sont disponibles via le lien suivant :</p>
                            <a href="{st.session_state["lien_photos"]}" target="_blank">{st.session_state["lien_photos"]}</a>
                        </div>
                    </div>
                    ''' if st.session_state['lien_photos'] else ''}
                    
                    <!-- Page break before results -->
                    <div class="page-break"></div>
                    
                    <!-- Scores -->
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
                    
                    <!-- Page break before detailed criteria -->
                    <div class="page-break"></div>
                    
                    <!-- Detailed Criteria -->
                    <div class="section">
                        <h2 class="section-title">
                            <span class="icon">🔍</span>
                            Détail des Critères d'Évaluation
                        </h2>
        """
        
        # Add detailed criteria for each category with page breaks
        for idx, (cat, criteres) in enumerate(categories.items()):
            # Add page break before Sécurité and Environnement sections
            page_class = "criteria-section new-page" if idx > 0 else "criteria-section"
            
            html += f"""
                        <div class="{page_class}">
                            <h3 class="category-header">
                                {cat}
                            </h3>
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
                        </div>
            """
        
        html += """
                    </div>
        """
        
        # Attendance sheet section
        html += """
                    <!-- Attendance Sheet -->
                    <div class="section">
                        <h2 class="section-title">
                            <span class="icon">✍️</span>
                            Feuille d'Émargement - Sensibilisation
                        </h2>
        """
        
        feuille = st.session_state.get("emargement")
        if feuille and feuille.type.startswith("image"):
            feuille.seek(0)  # Reset file pointer
            img_base64 = base64.b64encode(feuille.read()).decode()
            html += f"""
                        <div style="text-align: center; margin: 20px 0;">
                            <img src="data:image/jpeg;base64,{img_base64}" style="max-width: 500px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                        </div>
            """
        elif feuille and feuille.type == "application/pdf":
            html += """
                        <p style="text-align: center; padding: 20px; background: #f8f9fa; border-radius: 8px;">
                            <span style="font-size: 1.1em;">📎 Un fichier PDF a été joint comme feuille d'émargement</span>
                        </p>
            """
        else:
            html += """
                        <p style="text-align: center; padding: 20px; background: #f8f9fa; border-radius: 8px; color: #6c757d;">
                            Aucune feuille d'émargement ajoutée
                        </p>
            """
        
        html += """
                    </div>
                </div>
            </div>
            
            <!-- Footer -->
            <div class="footer">
                <p><strong>BR CONSULT</strong> - Rapport généré le {}</p>
                <p class="footer-tagline">© 2025 Tous droits réservés</p>
            </div>
        </body>
        </html>
        """.format(datetime.now().strftime("%d/%m/%Y à %H:%M"))
        
        # Generate PDF
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
                pdfkit.from_string(html, f.name, configuration=config, options={
                    'enable-local-file-access': None,
                    'encoding': 'UTF-8',
                    'page-size': 'A4',
                    'margin-top': '10mm',
                    'margin-right': '10mm',
                    'margin-bottom': '10mm',
                    'margin-left': '10mm',
                    'no-outline': None
                })
                
                with open(f.name, "rb") as file:
                    st.download_button(
                        label="📥 Télécharger le PDF",
                        data=file,
                        file_name=f"fiche_visite_chantier_{current_date}.pdf",
                        mime="application/pdf"
                    )
                    
            st.success("✅ PDF généré avec succès !")
            
        except Exception as e:
            st.error(f"❌ Erreur lors de la génération du PDF : {str(e)}")
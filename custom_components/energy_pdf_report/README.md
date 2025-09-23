# Energy PDF Report

Ce composant personnalisé Home Assistant ajoute un service `energy_pdf_report.generate` permettant de générer un rapport PDF à partir des statistiques du tableau de bord Énergie. Le fichier PDF inclut une synthèse par catégorie ainsi qu'un détail de toutes les statistiques utilisées.

## Installation rapide
1. Copier le dossier `energy_pdf_report` dans le répertoire `custom_components` de votre installation Home Assistant.
2. Redémarrer Home Assistant.
3. Appeler le service `energy_pdf_report.generate` depuis l'interface ou via une automatisation.

## Paramètres du service
- `start_date` *(optionnel)* : date locale de début (format `YYYY-MM-DD`). Par défaut la période courante (jour, semaine ou mois) est utilisée.
- `end_date` *(optionnel)* : date locale de fin (format `YYYY-MM-DD`). Si omis, la fin est déduite de la granularité.
- `period` *(optionnel)* : granularité des statistiques (`day`, `week` ou `month`).
- `filename` *(optionnel)* : nom du fichier PDF à générer (l'extension `.pdf` est ajoutée automatiquement si nécessaire).
- `output_dir` *(optionnel)* : répertoire de sortie relatif au dossier de configuration ou chemin absolu. Par défaut `www/energy_reports`.

Le fichier généré est également signalé via une notification persistante dans Home Assistant.

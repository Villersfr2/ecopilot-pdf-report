# Energy PDF Report

Ce composant personnalisé Home Assistant ajoute un service `energy_pdf_report.generate` permettant de générer un rapport PDF à partir des statistiques du tableau de bord Énergie. Le fichier PDF inclut une synthèse par catégorie ainsi qu'un détail de toutes les statistiques utilisées.

## Installation rapide
1. Copier le dossier `energy_pdf_report` dans le répertoire `custom_components` de votre installation Home Assistant.
2. Redémarrer Home Assistant.
3. Depuis **Paramètres → Appareils et services → Ajouter une intégration**, sélectionner **Energy PDF Report** pour créer l'entrée de configuration.
4. Le service `energy_pdf_report.generate` devient alors disponible dans l'outil Développeur > Services et peut être utilisé dans vos automatisations.


## Paramètres du service
- `start_date` *(optionnel)* : date locale de début (format `YYYY-MM-DD`). Par défaut la période courante (jour, semaine ou mois) est utilisée.
- `end_date` *(optionnel)* : date locale de fin (format `YYYY-MM-DD`). Si omis, la fin est déduite de la granularité.
- `period` *(optionnel)* : granularité des statistiques (`day`, `week` ou `month`).
- `filename` *(optionnel)* : nom du fichier PDF à générer (l'extension `.pdf` est ajoutée automatiquement si nécessaire).
- `output_dir` *(optionnel)* : répertoire de sortie relatif au dossier de configuration ou chemin absolu. Par défaut `www/energy_reports`.

Le fichier généré est également signalé via une notification persistante dans Home Assistant.

## Support Unicode

Le rapport PDF est généré avec la police DejaVu Sans fournie dans le dossier
`fonts/`, ce qui garantit l'affichage correct des caractères accentués et des
symboles internationaux directement dans le document.

## Script de vérification
Pour valider rapidement que l'intégration, y compris la compatibilité avec le recorder,
fonctionne correctement dans votre instance Home Assistant, un exemple de script est
fourni dans [`examples/test_energy_pdf_report_script.yaml`](examples/test_energy_pdf_report_script.yaml).

1. Copiez le contenu du fichier dans votre `scripts.yaml` (ou créez un nouveau script via l'interface en mode YAML).
2. Enregistrez et rechargez les scripts si nécessaire.
3. Exécutez le script **Test – Energy PDF Report** depuis l'interface.

Le script appelle le service `energy_pdf_report.generate`, attend la notification
persistante `energy_pdf_report_last_report` et consigne le message du rapport dans le
Journal. En cas d'absence de notification dans la minute, une alerte supplémentaire
est créée pour vous inviter à consulter les logs.

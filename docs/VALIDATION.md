# Validation de la version 0.2

Date : 21 octobre 2026. Environnement exécuté : Linux, Python 3.12. Le code cible Python 3.10+, sa syntaxe a été analysée en mode Python 3.10 et la CI fournie prévoit 3.10/3.12. Une exécution locale sous Windows/Python 3.10 n'a pas été réalisée ici.

## Essais effectués

- 24 tests historiques conservés.
- Tests d'intégration API FastAPI : page d'accueil, JavaScript servi, recherche, contrôle de saisie, fiche absente et LLM désactivé.
- MCP : processus stdio et SDK client officiels, initialisation, découverte, appel de recherche, erreur sur fiche inconnue. Essai supplémentaire sur Streamable HTTP avec serveur Uvicorn et client SDK, protocole négocié 2025-11-25.
- A2A : découverte de carte 0.3.0 et requête JSON-RPC `message/send` via le serveur SDK 0.3.22.
- DID/VC : création/résolution, signature, vérification, rejet d'émetteur non attendu, empreinte incorrecte, jeton altéré et refus d'écrasement d'une clé. Filtrage du catalogue par attestation d'un émetteur de confiance.
- IPFS : test du transport Kubo simulé, correspondance du CID raw avec les octets, rejet d'un mauvais CID. Aucune publication à un nœud externe effectuée.
- ERC-8004 : encodage réel de l'ABI via Web3.py, transaction Sepolia préparée sans signature ni envoi, rejet d'un autre réseau.
- LLM : requête HTTP Ollama simulée, comptage de jetons, rejet de faux extrait/identifiant, repli extractif. Aucun modèle Ollama n'a été lancé dans ces essais.
- Recherche dense : test de logique avec encodeur déterministe, puis chargement et exécution réels de `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` en mode hybride sur les 17 questions de démonstration. Le rapport `validation/metrics.hybrid.demo.json` mesure précision/rappel/MRR et latences, sans validation de généralisation au kabyle.
- Import : données en attente de revue, doublons et écrasement de fichier refusés.
- Benchmark : métriques et latences mesurées, fidélité non inventée ; annotation liée au reçu d'une réponse sauvegardée.

Suite exécutée : `python -m pytest tests integration -q` → **37 tests réussis**. Des avertissements de dépréciation internes à Starlette/A2A/WebSockets ont été observés, sans échec.

Le fichier `validation/metrics.demo.json` contient une mesure locale du jeu de 17 questions, en mode lexical sans LLM : rappel, précision, MRR et validité technique des citations à 1.0 sur ce jeu seulement. Latence et couverture d'annotation sont décrites dans le JSON. Les coûts sans tarifs et la fidélité sans annotateurs sont null.

## À valider sur le poste utilisateur

- Docker build/compose : configuration fournie mais Docker indisponible dans l'environnement de réalisation.
- Interface dans un navigateur réel : routes et JavaScript vérifiés, rendu visuel non validé ici (moteur Chromium indisponible après échec du téléchargement).
- Embeddings : qualité sur le catalogue réel, calibration des seuils et sous-groupes kabyle/tifinagh restent à mesurer. Le chargement du modèle et le mode hybride ont été exécutés sur la démonstration.
- Ollama réel et qualité de synthèse en trois langues.
- Kubo réel : publication, récupération et disponibilité durable.
- Interopérabilité VC avec un vérificateur externe et politique de révocation.
- Contrat ERC-8004 effectivement déployé sur Sepolia, signature et transaction avec un portefeuille de test.
- Catalogue complet réel, licences, questions indépendantes et annotations humaines.

Les intégrations optionnelles ne sont pas remplacées par une simulation en production. Les doubles de test sont utilisés uniquement dans les tests et ne peuvent pas être sélectionnés comme un vrai modèle dans l'interface.

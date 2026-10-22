# Architecture v0.2

Le cœur d'origine conserve cinq rôles Python : détection de langue, compréhension de requête, recherche, rédaction extractive et vérification des citations. `ResearchService` est partagé par l'API, MCP, A2A et le benchmark.

## Exécution

- `web.py` : API FastAPI et fichiers statiques ; JavaScript appelle `/api/ask`.
- `service.py` : configuration, catalogue, filtre optionnel d'attestations, choix de l'index, appel du cœur, synthèse optionnelle et reçu complet de réponse.
- `semantic.py` : vecteurs Sentence Transformers et fusion RRF ; modèle chargé une fois par processus. La couverture combine besoins lexicaux et scores cosinus ; elle reste heuristique.
- `llm.py` : Ollama HTTP, preuves par affirmation, contrôle technique et repli extractif dans le service. Une preuve citée n'est pas une validation d'implication sémantique.
- `mcp_server.py` : deux outils exposés via le SDK officiel MCP 1.x.
- `a2a_server.py` : coordinateur exposé via le SDK officiel A2A 0.3.22, requêtes synchrones `message/send`, pas de streaming annoncé.
- `identity.py` : did:key Ed25519 et sous-ensemble d'attestations VC-JWT. Les émetteurs de confiance sont configurés séparément.
- `web3.py` : CID raw, Kubo add/cat et préparation ABI non signée ERC-8004.
- `importer.py` et `benchmark.py` : import contrôlé, mesures et annotation de fidélité.

## Stockage et confiance

Textes, index, questions et sorties restent hors chaîne. Les clés privées restent dans `.secrets`, jamais dans une réponse HTTP ou dans Git. La publication IPFS est une commande explicite, distincte du calcul d'empreinte. Aucun enregistrement blockchain n'est déclenché à la recherche.

Le vérificateur historique vérifie fiche, URL, empreinte et extrait. Le reçu historique ne couvre que les citations ; `response_receipt` lie aussi la synthèse et le mode de recherche. Les annotations humaines s'attachent à ce second reçu.

## Frontières

Le déploiement local n'a pas d'authentification. Les endpoints de consultation peuvent lancer un modèle si l'administrateur l'active. Avant un accès public : authentification, limitation de débit, limites de ressources et proxy TLS. L'application n'expose aucune route HTTP d'import, de publication IPFS, d'émission de clés ou de transaction.

Les SDK réseau sont opérationnels, mais les cinq rôles ne communiquent pas chacun via A2A : le coordinateur expose leur service commun. Aucun paiement x402, registre de réputation ni distribution multi-nœuds n'est livré.

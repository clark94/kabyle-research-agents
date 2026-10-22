# Limites après l'implémentation v0.2

Les limitations de v0.1 ont conduit à des ajouts de code : web/API, adaptateurs MCP/A2A, embeddings, LLM, DID/VC, IPFS, préparation ERC-8004, import et benchmark. Elles ne doivent plus être décrites comme « uniquement conçues ». En revanche, les limites suivantes restent réelles :

- Catalogue du stage de plusieurs centaines de fiches non fourni. Les 12 fiches de démonstration restent fictives ; six notices scientifiques réelles sont proposées séparément comme candidates non approuvées.
- SDK A2A 0.3.22, protocole 0.3.0 explicitement ciblé. Pas d'A2A 1.0, pas de cinq services agents distribués, pas de certification d'interopérabilité.
- Embeddings implémentés mais modèle multilingue non validé sur le kabyle et le tifinagh. Cosinus et couverture sont des heuristiques.
- LLM Ollama implémenté mais modèle à installer/configurer. La fidélité d'une affirmation générée n'est pas prouvée par l'existence d'une citation. La synthèse est marquée à relire ; le repli extractif est conservé.
- DID/VC : sous-ensemble Ed25519/JWT testé localement, sans révocation, rotation des clés ou audit indépendant. La gouvernance de la liste d'émetteurs reste humaine.
- IPFS : connecteur réel, essai sur transport simulé ; nœud Kubo nécessaire pour publication effective et test de disponibilité.
- ERC-8004 : document et encodage ABI du registre d'identité ; pas d'enregistrement diffusé, ni de registres réputation/validation intégrés.
- x402 reste une étude, aucun paiement implémenté.
- Mesures et annotations implémentées, mais aucun benchmark scientifique ou mesure de fidélité sur le vrai catalogue absent ne peut être annoncé. Les tarifs non renseignés restent null.
- État de l'art spécifique au kabyle ajouté avec sources primaires vérifiées, sans prétendre à une revue exhaustive.
- Web/API local fonctionnel ; authentification, quotas et exploitation HTTPS publique restent à mettre en place avant ouverture.

Les périmètres testés figurent dans [VALIDATION.md](VALIDATION.md). L'intégration d'un composant ne vaut pas validation scientifique ni certification d'un standard.

---

# Écart entre l'offre de stage et l'état du prototype (v0.2)

Cette matrice rapproche chaque exigence de l'offre « Assistant multi-agents décentralisé pour les ressources d'une langue peu dotée » (Cnam / Efrei, 2027) de l'état réel du dépôt. Elle distingue ce qui est **implémenté**, ce qui est **implémenté mais non validé** et ce qui reste **à réaliser**. Un composant intégré n'est pas un composant validé scientifiquement.

| Exigence de l'offre | État | Écart restant | Prochaine étape |
|---|---|---|---|
| **Protocoles d'agents : MCP, A2A** | Implémentés (SDK MCP 1.x ; SDK A2A 0.3.22, protocole 0.3.0) | Pas de certification d'interopérabilité ; pas d'A2A 1.0 ; les cinq rôles restent des modules Python internes, seul le coordinateur est exposé | Tester avec des clients tiers ; évaluer la migration vers A2A 1.0 ; exposer les rôles comme services distincts si l'étude le justifie |
| **Web3 : DID et attestations vérifiables** | Sous-ensemble `did:key` Ed25519 et VC-JWT, testé localement | Ni révocation, ni rotation de clés, ni audit indépendant ; pas de conformité W3C certifiée | Définir la gouvernance de la liste d'émetteurs ; ajouter révocation et rotation |
| **Web3 : IPFS (provenance)** | CID raw réel, empreinte `sha256`, connecteur Kubo (essai sur transport simulé) | Aucun nœud Kubo réel testé ; fichiers limités à 256 KiB ; disponibilité non mesurée | Déployer un nœud Kubo ; publier un échantillon et mesurer la disponibilité |
| **Web3 : registre ERC-8004** | Document de déclaration d'agent et encodage ABI `register(string)` pour Sepolia | Transaction non signée et non diffusée ; registres de réputation et de validation non intégrés | Enregistrer un agent sur Sepolia ; intégrer les registres de réputation et de validation |
| **Web3 : micropaiements x402** | Étude documentée uniquement (piste, réseau de test) | Aucun paiement implémenté | Prototype sur réseau de test si le calendrier le permet |
| **Recherche sémantique (RAG)** | BM25 + embeddings Sentence Transformers, fusion RRF (mode `hybrid`) | Modèle multilingue non validé sur le kabyle ni le tifinagh ; seuils de similarité heuristiques | Comparer plusieurs modèles sur un jeu annoté en kabyle (graphie latine et tifinagh) |
| **LLM et génération** | Connecteur Ollama, sorties JSON avec preuves, repli extractif conservé | Aucun modèle validé pour le kabyle ; une citation valide ne prouve pas que l'affirmation découle de l'extrait ; synthèse marquée « à relire » | Annotation humaine de fidélité ; comparaison de modèles |
| **Prototype web open source** | API FastAPI et interface HTML/JS locales ; Docker ; CI | Usage local : ni authentification, ni quotas, ni HTTPS public | Sécuriser et déployer avant toute ouverture publique |
| **Données : plusieurs centaines de fiches** | 12 fiches fictives (10 chargées après filtrage de sécurité) ; 6 notices réelles candidates non approuvées ; import CSV/JSONL avec approbation explicite | **Catalogue réel du stage non fourni** | Importer le catalogue, puis revue humaine des sources et des licences |
| **Évaluation (trois langues, pertinence, fidélité, coût)** | Outils de mesure : précision, rappel, MRR, abstention, latences, coûts configurables, annotation de fidélité | Les 17 questions sont un garde-fou de non-régression, pas un benchmark ; fidélité et coût non mesurés sur données réelles ; tarifs non renseignés = `null` | Constituer un jeu de questions en kabyle, français et anglais sur le vrai catalogue ; annoter ; mesurer |
| **État de l'art** | Revue ciblée kabyle avec sources primaires vérifiées | Revue courte, non exhaustive ; références à revérifier avant toute publication | Extension systématique de la revue ; revérification des références |

## Lecture de ce tableau

- **Résultats que le projet peut annoncer** : un prototype fonctionnel de bout en bout sur données de démonstration, une réponse extractive traçable, des interfaces MCP et A2A opérationnelles, des primitives de provenance (empreinte, CID, DID, VC) testées localement.
- **Résultats que le projet ne peut pas annoncer** : une performance mesurée sur le kabyle, un benchmark scientifique, une fidélité ou un coût mesurés sur le catalogue réel, un enregistrement ERC-8004 sur chaîne, une conformité certifiée à un standard.
- **Dépendance critique** : la quasi-totalité des écarts d'évaluation découle de l'absence du catalogue réel. Son obtention est le prérequis des travaux de validation scientifique.

# État de l'art ciblé : ressources kabyles et recherche multilingue

Revue courte, non exhaustive, réalisée le 21 octobre 2026. Les références ci-dessous ont été vérifiées dans les publications originales ou leurs notices éditoriales. Elles justifient des choix de prototype ; elles ne valident pas ses performances. Les notices réelles candidates sont séparées du catalogue de démonstration.

## Ressources, structuration et spécificités du kabyle

**Loikkanen (2007), Étiquetage morpho-syntaxique de textes kabyles.** Ce travail présente un étiqueteur, un analyseur morphologique et des règles de désambiguïsation pour un corpus kabyle. Il montre que les ressources et outils kabyles ne sont pas inexistants. Pour notre catalogue, la morphologie peut affecter la correspondance entre une requête et une description. Le prototype ne reprend pas cet analyseur ; il conserve une normalisation légère. Source : https://aclanthology.org/2007.jeptalnrecital-poster.19/ .

**Mahtout (2014), Méthodologie pour la structuration semi-automatique du corpus… : le cas du dictionnaire français-kabyle.** L'article traite de la transformation d'un dictionnaire ancien en données structurées. Il rappelle qu'un PDF numérisé n'est pas directement une base lexicale fiable. Conséquence pour le projet : séparer source originale, description, contrôle éditorial et index ; ne pas transformer une sortie OCR non revue en validation. Source : https://aclanthology.org/W14-6503/ ; PDF : https://aclanthology.org/W14-6503.pdf .

**Haberland et Lao (2021), Orthographic Transliteration for Kabyle Speech Recognition.** Les auteurs étudient l'effet de graphies latines et tifinagh en reconnaissance vocale. Ce n'est pas une étude de recherche documentaire. Elle motive néanmoins, comme hypothèse à tester ici, une évaluation séparée des graphies et des variantes de translittération, plutôt qu'un score kabyle unique. Source : https://aclanthology.org/2021.icnlsp-1.3/ ; PDF consulté.

**Lichouri et Abbas (2021), Machine Translation for Zero and Low-resourced Dialects using a New Extended Version of the Dialectal Parallel Corpus (Padic v2.0).** Ce travail étend un corpus parallèle avec du kabyle et compare des méthodes de traduction. Il suggère une piste pour préparer des requêtes alignées, sous réserve de droits et de validation. Les résultats de traduction présentés ne constituent pas une mesure de pertinence documentaire ni une preuve de fiabilité d'un LLM. Source : https://aclanthology.org/2021.icnlsp-1.4/ ; PDF consulté.

**Ardila et al. (2020 ; prépublication 2019), Common Voice: A Massively-Multilingual Speech Corpus.** Les auteurs décrivent un corpus vocal participatif et incluent des expériences concernant le kabyle. Ce type de ressource justifie de conserver le type de média, la langue, la version et la licence dans les fiches. Les fichiers vocaux ne sont pas collectés par le prototype. Source primaire consultée : https://arxiv.org/abs/1912.06670 .

## Recherche, embeddings et génération

**Reimers et Gurevych (2020), Making Monolingual Sentence Embeddings Multilingual using Knowledge Distillation.** La méthode aligne des représentations de phrases de plusieurs langues par distillation. Elle soutient le choix d'un espace vectoriel partagé pour comparer des formulations multilingues. Ce principe général ne prouve pas la qualité du modèle livré pour le kabyle. Le module doit être comparé à BM25 et testé sur les variantes graphiques. Source : https://aclanthology.org/2020.emnlp-main.365/ ; DOI : 10.18653/v1/2020.emnlp-main.365.

**Lewis et al. (2020), Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.** Le travail combine recherche de documents et génération. Notre module applique le principe d'un contexte récupéré avant rédaction, sans reproduire l'entraînement ni les résultats des auteurs. L'ajout de sources ne suffit pas à garantir la fidélité de chaque phrase générée. Source : https://arxiv.org/abs/2005.11401 .

Le prototype compare trois modes : BM25 lexical, vecteurs seuls et fusion réciproque des rangs. Les besoins de requête restent visibles. Le seuil cosinus initial est une valeur de démarrage à calibrer, pas un résultat scientifique. Le passage à un moteur vectoriel sur disque ou une base dédiée n'est pas nécessaire pour quelques centaines de fiches, mais devra être évalué si le volume croît.

## Agents, confiance et frontière des garanties

MCP donne accès aux outils du catalogue ; A2A expose le coordinateur à un client agent. Cette version cible explicitement MCP SDK 1.x et A2A 0.3, sans prétendre implémenter les versions plus récentes. Les cinq rôles de raisonnement restent des objets internes : leur distribution en cinq services n'est pas démontrée.

Les signatures lient une attestation à une clé ; les CIDs lient un identifiant aux octets. Ni une signature, ni un hash, ni un registre d'agent ne garantissent la vérité du contenu. La confiance envers l'émetteur doit être définie séparément par la gouvernance communautaire. Références techniques primaires : [TRUST.md](TRUST.md), https://py.sdk.modelcontextprotocol.io/v1/ et https://a2a-protocol.org/v0.3.0/tutorials/python/5-start-server/ .

## Hypothèses à évaluer durant le stage

1. La recherche hybride améliore-t-elle le rappel pour les requêtes multilingues sans augmenter les réponses hors sujet ?
2. Les normalisations Latin/tifinagh aident-elles chaque sous-groupe de questions ou masquent-elles des distinctions utiles ?
3. Une reformulation LLM apporte-t-elle une valeur suffisante pour son coût et ses erreurs par rapport à une réponse extractive ?
4. Les attestations signées améliorent-elles l'audit de la validation, et quel coût de gestion introduisent-elles pour le comité ?

Préparer les questions avec des locuteurs et réserver un jeu de test indépendant. Les six notices candidates ne constituent pas un corpus d'évaluation ni les centaines de fiches du catalogue attendu.

# Kabyle Research Agents · v0.2

Assistant de recherche pour un catalogue de ressources kabyles : API FastAPI, interface HTML/CSS/JavaScript, recherche lexicale ou hybride, génération Ollama optionnelle, serveurs MCP/A2A et provenance vérifiable.

**Cette version ajoute du code fonctionnel aux interfaces prévues dans v0.1.** Le catalogue réel du stage n'a pas été fourni. Le démarrage utilise donc les 12 fiches fictives existantes, dont 2 sont mises en quarantaine par le filtre de sécurité : 10 fiches sont chargées. Les exemples de démonstration ne sont pas des ressources réelles.

## Démarrer dans VS Code / Windows

Extraire le ZIP et ouvrir le dossier qui contient ce README et `pyproject.toml`. Ouvrir Terminal → Nouveau terminal, puis utiliser PowerShell :

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[web,protocols,trust,dev]"
.\.venv\Scripts\python.exe -m uvicorn kabyle_agents.web:app --host 127.0.0.1 --port 8000
```

Ouvrir **http://127.0.0.1:8000**. API interactive : http://127.0.0.1:8000/docs . Arrêt : Ctrl+C. L'activation PowerShell de l'environnement n'est pas nécessaire.

L'interface utilise JavaScript pour les recherches asynchrones, la sélection des exemples, les états de chargement, l'affichage des citations, des traces et l'export JSON. Les contenus des fiches sont affichés avec `textContent`, sans HTML injecté. Elle ne nécessite ni Node ni compilation.

La commande initiale reste disponible :

```powershell
.\.venv\Scripts\python.exe -m kabyle_agents ask "amawal n ddwa" --trace
```

## Ce qui est livré et ce qui nécessite une configuration

| Besoin | Implémentation | Limite à connaître |
|---|---|---|
| MCP | Serveur officiel SDK 1.x, outils `search_catalog` et `get_fiche`, transports stdio et Streamable HTTP | Pas de certification globale de conformité ; déploiement local sans OAuth |
| A2A | Serveur officiel SDK **0.3.22**, découverte et `message/send` JSON-RPC | Protocole **0.3.0**, pas A2A 1.0 ; coordinateur exposé, cinq rôles internes Python |
| Sémantique | Embeddings Sentence Transformers, cosinus par besoin, fusion RRF avec BM25 | Modèle à télécharger ; seuil expérimental ; qualité kabyle à mesurer |
| LLM / RAG | Appel HTTP Ollama sur les fiches retrouvées, sorties JSON avec preuves, repli extractif | Modèle à installer ; fidélité des reformulations à faire annoter |
| Web | FastAPI et interface JavaScript adaptative | Usage local ; accès public à protéger avant exposition |
| DID / attestations | did:key Ed25519, résolution locale, émission/vérification VC-JWT, filtre optionnel du catalogue par émetteurs de confiance | Sous-ensemble documenté, sans révocation ni certification d'interopérabilité W3C |
| IPFS | CIDv1 raw réel et connecteur Kubo add/cat avec contrôle des octets | Nœud Kubo requis ; fichiers ≤ 256 KiB par publication |
| ERC-8004 | Encodage ABI `register(string)` pour Sepolia et document de déclaration d'agent | Transaction non signée, non envoyée ; registres de réputation/validation non intégrés |
| x402 | Étude documentée | Aucun paiement implémenté |
| Données | Import CSV/JSONL avec contrôle, empreinte et approbation explicite ; 6 notices scientifiques réelles candidates | Catalogue existant de plusieurs centaines de fiches toujours manquant |
| Évaluation | Précision, rappel, MRR, abstention, latences, jetons/coûts configurables, annotation humaine de fidélité | Le jeu de 17 questions reste une démonstration |
| État de l'art | Revue ciblée kabyle et bibliographie de sources primaires vérifiées | Revue courte, non exhaustive |

Les essais effectués et non effectués sont consignés dans [docs/VALIDATION.md](docs/VALIDATION.md).

## Activer les embeddings

Arrêter le serveur, installer le module puis relancer :

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[semantic]"
$env:KABYLE_RETRIEVAL = "hybrid"
$env:KABYLE_SEMANTIC_THRESHOLD = "0.60"
.\.venv\Scripts\python.exe -m uvicorn kabyle_agents.web:app --host 127.0.0.1 --port 8000
```

Le premier chargement télécharge le modèle `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` et ses dépendances, dont PyTorch. Le mode `semantic` compare uniquement les vecteurs ; `hybrid` fusionne les classements. Une couverture sémantique est une heuristique expérimentale, pas une preuve de pertinence. Une performance multilingue générale ne garantit pas le kabyle ou le tifinagh. Pour revenir au fonctionnement sans modèle : `$env:KABYLE_RETRIEVAL = "lexical"`.

## Activer le LLM local

Installer Ollama depuis https://ollama.com/download/windows . Dans son terminal :

```powershell
ollama pull qwen2.5:3b
```

Dans le terminal du projet, avant de relancer le serveur :

```powershell
$env:KABYLE_LLM_ENABLED = "1"
$env:OLLAMA_URL = "http://127.0.0.1:11434"
$env:OLLAMA_MODEL = "qwen2.5:3b"
```

### Variante : API OpenAI

```powershell
$env:KABYLE_LLM_ENABLED = "1"
$env:KABYLE_LLM_PROVIDER = "openai"
$env:OPENAI_API_KEY = "sk-..."
$env:OPENAI_MODEL = "gpt-4o-mini"
```

La clé ne doit jamais être écrite dans un fichier du dépôt. Les fiches retrouvées sont envoyées à un service tiers : ne l'utiliser qu'avec des données partageables (fiches de démonstration ou ressources sous licence ouverte). Les mêmes contrôles de citation s'appliquent ; la fidélité reste à relire.

### Préparer l'évaluation avec OpenAI

`scripts/openai_workflow.py` (clé lue dans `OPENAI_API_KEY`, jamais dans un fichier) propose trois commandes :

```powershell
python scripts/openai_workflow.py draft-questions --corpus data/catalog.demo.jsonl
python scripts/openai_workflow.py compare-models --models gpt-4o-mini --rate gpt-4o-mini=0.15:0.60
python scripts/openai_workflow.py prejudge --responses reports/openai/responses.gpt-4o-mini.jsonl
```

Ce sont des brouillons : les questions générées doivent être relues (surtout le kabyle), les tarifs `--rate` (USD par million de jetons) sont à vérifier chez le fournisseur, et le pré-jugement laisse `supported` à `null` jusqu'à confirmation humaine. Les sorties vont dans `reports/`, ignoré par Git.

Cocher « Synthèse LLM » dans l'interface. Sans preuves ou en cas de sortie invalide/erreur, les résultats extractifs restent disponibles. Chaque affirmation doit citer une fiche trouvée et un extrait exact ; ce contrôle ne prouve pas que l'affirmation découle de l'extrait. Le statut `requires_human_review` reste affiché.

L'utilisation d'Ollama local n'appelle aucune API payante du projet ; les coûts matériels restent à mesurer. Le modèle choisi est un point de départ configurable, pas un modèle validé pour le kabyle.

## Utiliser les protocoles

Chaque serveur se lance dans un terminal distinct, depuis la racine du dépôt.

```powershell
# MCP HTTP : endpoint http://127.0.0.1:8001/mcp
.\.venv\Scripts\python.exe -m kabyle_agents.mcp_server --transport streamable-http
# A2A : découverte /.well-known/agent-card.json ; JSON-RPC sur /
.\.venv\Scripts\python.exe -m kabyle_agents.a2a_server
```

Pour un client MCP stdio, configurer la commande absolue de `.venv\Scripts\python.exe`, les arguments `-m kabyle_agents.mcp_server` et le dossier de travail du dépôt. Ne pas écrire de messages de diagnostic sur stdout dans un serveur stdio.

Exemple A2A PowerShell :

```powershell
$body = @{jsonrpc="2.0";id="q1";method="message/send";params=@{message=@{role="user";messageId="m1";parts=@(@{kind="text";text="amawal n ddwa"})}}} | ConvertTo-Json -Depth 8
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8002/" -ContentType "application/json" -Body $body
```

## Charger le vrai catalogue

L'import prend du CSV à virgules ou du JSONL. Champs : `id,title,type,description,url,languages,keywords,license`. En CSV, séparer les langues/mots-clés par `|`. En JSONL, utiliser des listes JSON. Il n'y a pas de téléchargement automatique des pages et pas d'invention de fiches.

```powershell
.\.venv\Scripts\python.exe -m kabyle_agents.toolbox import data/catalogue_source.jsonl data/catalog.real.pending.jsonl
```

Les fiches importées restent non validées. **Après revue humaine effective** des sources et licences, produire un autre fichier :

```powershell
.\.venv\Scripts\python.exe -m kabyle_agents.toolbox import data/catalogue_source.jsonl data/catalog.real.reviewed.jsonl --approve-reviewed
$env:KABYLE_CATALOG = "data/catalog.real.reviewed.jsonl"
```

Relancer les services. `data/research.references.pending.jsonl` contient 6 notices de publications réelles, décrites à partir des sources primaires vérifiées ; elles ne sont pas approuvées par le comité et ne remplacent pas le catalogue du stage.

## Provenance et confiance

Voir [docs/TRUST.md](docs/TRUST.md) pour les commandes DID, VC, IPFS, ERC-8004 et leurs limites. Ne jamais versionner `.secrets`, clés privées, jetons ou données non autorisées. Une signature prouve le contrôle d'une clé, pas la véracité d'une fiche ni l'identité civile d'un contributeur.

## Évaluer

```powershell
.\.venv\Scripts\python.exe -m pytest tests integration -q
.\.venv\Scripts\python.exe -m kabyle_agents.toolbox benchmark --out reports/demo-01
```

Chaque répertoire de sortie doit être vide. Les résultats comprennent `responses.jsonl` et `metrics.json`. Pour le vrai catalogue : utiliser `--questions eval/questions.real.jsonl`. Pour une génération locale : ajouter `--llm`. Les tarifs par million de jetons (`--input-rate`, `--output-rate`) et le coût horaire d'infrastructure (`--hourly-cost`) sont optionnels : une valeur non renseignée reste **null**, pas un coût nul inventé. Les coûts sont des estimations et excluent le démarrage et les téléchargements.

Une annotation de fidélité porte sur une réponse sauvegardée précise :

```json
{"question_id":"q1","response_receipt":"sha256:...","claim_index":0,"supported":true}
```

```powershell
.\.venv\Scripts\python.exe -m kabyle_agents.toolbox fidelity reports/run-01/responses.jsonl eval/annotations.real.jsonl
```

La fidélité reste `null` sans annotation humaine. Les 17 questions ne forment pas un benchmark de production. Lire [docs/EVALUATION.md](docs/EVALUATION.md).

## Docker

```powershell
docker compose up --build -d
```

Interface : http://localhost:8000 ; MCP HTTP : http://localhost:8001/mcp ; A2A : http://localhost:8002 . Voir le guide [docs/DEMARRAGE_WINDOWS.md](docs/DEMARRAGE_WINDOWS.md). Pour un hébergement HTTPS, déployer le conteneur web derrière le proxy TLS de l'hébergeur ; protéger les services avant une exposition publique. Un dépôt GitHub ou un hébergement statique Netlify seul n'exécute pas cette API Python.

## Documentation

- [Architecture et périmètre](docs/ARCHITECTURE.md)
- [État de l'art kabyle et bibliographie](docs/ETAT_DE_L_ART.md)
- [Évaluation](docs/EVALUATION.md)
- [Limites restantes et écart avec l'offre de stage](docs/LIMITES_ET_TRAVAUX_RESTANTS.md)
- [Validation effectuée](docs/VALIDATION.md)
- [Gouvernance](docs/GOVERNANCE.md)

Code sous licence MIT ; les ressources et leurs licences restent distinctes.

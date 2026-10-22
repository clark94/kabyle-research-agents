# VS Code, PowerShell, Docker et GitHub

## Interface web

1. Extraire le ZIP dans un nouveau dossier, pour garder la version précédente.
2. Dans VS Code : Fichier → Ouvrir un dossier ; choisir celui qui contient pyproject.toml.
3. Terminal → Nouveau terminal ; choisir PowerShell.
4. Exécuter les trois commandes du début du README : création du venv, installation des extras, lancement Uvicorn.
5. Ouvrir http://127.0.0.1:8000 dans le navigateur ; garder le terminal ouvert.

Si `py -3.10` ne trouve pas Python, vérifier `py -0p` et installer Python 3.10. Si le port 8000 est occupé, utiliser `--port 8010` et ouvrir http://127.0.0.1:8010 . Ne pas lancer `streamlit run` : cette application utilise FastAPI.

Le mode lexical démarre sans modèle. Les fonctions embeddings et LLM nécessitent les étapes dédiées du README. Un fichier .env n'est pas chargé automatiquement ; utiliser les variables PowerShell indiquées.

## Docker Desktop

Depuis ce même dossier :

```powershell
docker compose up --build -d
docker compose ps
docker compose logs -f web
```

Ouvrir http://localhost:8000 . Ctrl+C quitte seulement l'affichage des logs si le lancement a été effectué avec -d.

```powershell
docker compose down
```

Le compose fourni démarre le mode lexical avec le catalogue de démonstration. Il ne démarre pas automatiquement un modèle, Ollama ou Kubo. L'image n'installe pas PyTorch ; ajouter l'extra semantic à l'installation Docker si ce mode doit y fonctionner. Les réglages d'environnement de PowerShell ne sont pas transmis automatiquement aux conteneurs : les ajouter explicitement dans compose.yaml. Pour un Ollama sur l'hôte Windows depuis Docker Desktop, utiliser son adresse d'hôte adaptée (`host.docker.internal`) et configurer Ollama pour accepter cette connexion.

## GitHub

Créer un dépôt vide sur GitHub, sans ajouter README, licence ni .gitignore, car ces fichiers sont fournis. Depuis le terminal :

```powershell
git init
git add .
git status
```

Vérifier que `.secrets`, `.venv`, `.env`, clés et données non autorisées ne sont pas ajoutés, puis :

```powershell
git commit -m "Add web, RAG, agent protocols and provenance integrations"
git branch -M main
git remote add origin https://github.com/TON_COMPTE/kabyle-research-agents.git
git push -u origin main
```

Remplacer TON_COMPTE. Si origin existe déjà : `git remote -v`, puis corriger l'adresse avec `git remote set-url origin ...` si nécessaire. Les workflows GitHub vérifient le cœur et les intégrations sous Python 3.10 et 3.12 lors des prochains push. Leur présence ne signifie pas qu'ils ont déjà été exécutés sur ton compte.

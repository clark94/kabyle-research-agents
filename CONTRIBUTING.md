# Contribuer

```bash
git clone https://github.com/clark94/kabyle-research-agents.git && cd kabyle-research-agents
pip install -e ".[dev]"
make test && make eval && make lint
```

Règles du projet :

1. **Ne jamais affaiblir la règle d'or.** Toute modification de `agents.py`, `retrieval.py` ou `verifier.py` doit garder `citation_validity == 1.0` et `results_on_unanswerable == 0` dans `kabyle-agents eval`.
2. **Pas de forme kabyle sans validation humaine.** Pour ajouter un terme au glossaire, indiquez une source ou le nom du relecteur dans la PR.
3. **Un bug = un test.** Ajoutez le cas qui échoue avant de corriger.
4. **Pas de dépendance dans le cœur** sans discussion préalable.
5. Les nouvelles fiches de démo restent fictives (`[DEMO]`, `example.org`).

Sécurité : pour un contournement du vérificateur ou de la quarantaine, ouvrez une issue privée plutôt que publique.

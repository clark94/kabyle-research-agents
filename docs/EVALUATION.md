# Évaluation

`kabyle-agents eval` lit `eval/questions.jsonl` (une question par ligne) :

```json
{"question": "amawal n ddwa", "lang": "kab", "status": "answered", "expected_ids": ["demo-001"]}
```

| Métrique | Définition |
|---|---|
| `language_accuracy` | Langue détectée = langue attendue (si renseignée) |
| `status_accuracy` | `answered` / `partial` / `no_answer` conforme à l'attendu |
| `recall` | Part des fiches attendues retrouvées dans la réponse |
| `abstention_rate_on_unanswerable` | Part des questions sans réponse où le système s'abstient |
| `results_on_unanswerable` | Nombre de fiches renvoyées à tort (doit rester **0**) |
| `citation_validity` | Citations valides / citations vérifiées (doit rester **1.0**) |

La commande retourne un code de sortie non nul si une question échoue ou si une citation est invalide : elle sert de garde-fou en CI.

## Pour passer du démonstrateur à une évaluation scientifique

1. Constituer un jeu de plusieurs dizaines de questions **par langue** avec des locuteurs, sur le vrai catalogue (questions répondables, partielles, sans réponse).
2. Ajouter la **fidélité aux sources** (chaque énoncé d'une réponse LLM est-il soutenu par la fiche citée ?) et le **taux d'hallucination**.
3. Mesurer le **coût** (jetons, latence) par réponse.
4. Comparer BM25 seul, recherche sémantique seule et fusion, **avec le même seuil de couverture**.
5. Mesurer la robustesse : variantes d'orthographe, tifinagh, injections cachées dans des documents indexés.

## Limites du jeu actuel

Les 17 questions sur les 12 fiches fictives sont un garde-fou, pas un benchmark. Aucun score de coût ou de fidélité sur de vraies données n'est disponible. La validité technique d'une citation ne mesure pas à elle seule le soutien sémantique de chaque affirmation. Voir [les critères de passage à une évaluation réelle](LIMITES_ET_TRAVAUX_RESTANTS.md).

## v0.2 : mesures exécutables

Le module `benchmark.py`, lancé par `kabyle-tools benchmark`, mesure précision, rappel, MRR, abstention, validité technique des citations et latences p50/p95. Les compteurs Ollama permettent de calculer un coût de jetons uniquement si des tarifs sont fournis. Une estimation de coût matériel peut utiliser un tarif horaire explicite. Rien n'est présenté comme une facture réelle.

Les rapports contiennent la version du catalogue par empreinte et les réponses complètes. `kabyle-tools fidelity` évalue des annotations humaines liées au reçu et à l'indice d'affirmation, sans refaire l'inférence. Il rejette une annotation portant sur une autre réponse. Sans annotations : fidélité null, jamais 100 % supposé.

Une mesure de démonstration effectuée sur cette version est conservée dans `docs/validation/metrics.demo.json`. Elle n'utilise ni LLM ni embeddings et ne mesure pas un catalogue réel. Le temps de chargement du modèle n'est pas inclus dans les latences du benchmark ; le relever séparément lors d'un test à froid.

Pour un vrai benchmark : plusieurs questions par langue et type de ressource, jeu de réglage distinct du test, variantes Latin/tifinagh, questions sans réponse et réponses partielles, double annotation avec arbitrage. Comparer les trois moteurs sur les mêmes questions, avec des seuils réglés hors du jeu de test. Les notices bibliographiques candidates ne fournissent pas ce jeu annoté.

Un second rapport `validation/metrics.hybrid.demo.json` utilise réellement les embeddings multilingues sur ce même jeu de démonstration. Les scores de pertinence sont identiques au lexical sur ces 17 questions : cela ne démontre aucun gain scientifique du mode hybride. Les latences et le démarrage ont été mesurés séparément sur le poste de réalisation.

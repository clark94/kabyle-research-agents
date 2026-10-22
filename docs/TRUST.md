# DID, attestations, IPFS et ERC-8004

Ces commandes nécessitent l'extra `trust`. Elles s'exécutent depuis la racine du projet. Les secrets restent hors du dépôt. Le code n'effectue aucune transaction blockchain ni aucun paiement automatiquement.

## DID Ed25519 et attestations signées

```powershell
.\.venv\Scripts\python.exe -m kabyle_agents.toolbox keygen --key .secrets/issuer.pem
```

Copier le DID affiché. Il est dérivé de la clé publique, sans blockchain. Le fichier PEM contient la clé privée : permissions utilisateur uniquement ; ne pas le publier. Windows nécessite aussi de protéger le dossier par ses permissions locales.

```powershell
.\.venv\Scripts\python.exe -m kabyle_agents.toolbox resolve "did:key:REMPLACER"
```

L'attestation porte sur une fiche et son empreinte complète affichée dans `/api/fiches/demo-001` :

```powershell
.\.venv\Scripts\python.exe -m kabyle_agents.toolbox issue --key .secrets/issuer.pem --subject "urn:fiche:demo-001" --hash "sha256:REMPLACER_PAR_EMPREINTE_COMPLETE" --out .secrets/fiche-001.jwt
.\.venv\Scripts\python.exe -m kabyle_agents.toolbox verify .secrets/fiche-001.jwt --issuer "did:key:REMPLACER" --hash "sha256:REMPLACER_PAR_EMPREINTE_COMPLETE"
```

Le module implémente un sous-ensemble : `did:key` Ed25519, document DID avec clé JWK, VC Data Model 2.0 avec preuve enveloppante JWT `vc+jwt`/EdDSA. Le contenu couvre émetteur, sujet, empreinte et dates. Le vérificateur exige un émetteur fourni explicitement, contrôle la signature et les dates. Pas de révocation, de rotation des clés, de présentation sélective, de certification W3C ni de contrôle d'identité civile.

### Faire appliquer les signatures au catalogue

Créer `.secrets/attestations.json` :

```json
{"demo-001":"COLLER_LE_JWT_COMPLET"}
```

Puis avant de lancer le serveur :

```powershell
$env:KABYLE_REQUIRE_ATTESTATIONS = "1"
$env:KABYLE_ATTESTATIONS_FILE = ".secrets/attestations.json"
$env:KABYLE_TRUSTED_ISSUERS = "did:key:REMPLACER"
```

Seules les fiches munies d'une attestation valide d'un émetteur de cette liste sont alors conservées. Le sujet doit être `urn:fiche:IDENTIFIANT` et l'empreinte doit correspondre. Le filtre éditorial `validated=true` reste nécessaire pour les recherches. Plusieurs émetteurs sont séparés par une virgule. Sans cette option, les métadonnées de validation locales ne constituent pas une identité vérifiée.

## IPFS

Le module calcule un vrai CIDv1 pour un bloc `raw` à partir des octets JSON canoniques. **Calculer le CID ne publie rien**. Le connecteur Kubo ajoute les octets, demande leur pinning et compare le CID retourné. `fetch` contrôle les octets récupérés. Limite : 256 KiB pour cette représentation monobloc.

Pour tester avec Docker Desktop :

```powershell
docker run -d --name kabyle-ipfs -p 127.0.0.1:5001:5001 ipfs/kubo
```

Ce nœud peut rejoindre le réseau IPFS public. N'y publier que des métadonnées autorisées à être publiques ; un hash et IPFS ne chiffrent pas les données. Pour une expérimentation totalement privée, configurer un réseau Kubo privé avant tout ajout.

Enregistrer une fiche en JSON, par exemple à partir de l'API, puis :

```powershell
.\.venv\Scripts\python.exe -m kabyle_agents.toolbox ipfs-publish data/fiche.export.json
```

La sortie n'est déclarée publiée qu'après réponse Kubo et correspondance des octets. Le module n'assimile pas `sha256:...` à un CID. La disponibilité durable dépend du nœud et du pinning.

## ERC-8004

Le code fournit un document de déclaration via `registration_document` et l'encodage ABI d'un appel au registre d'identité `register(string)` sur **Sepolia (11155111)** :

```powershell
.\.venv\Scripts\python.exe -m kabyle_agents.toolbox erc8004-prepare --sender "0xADRESSE_DU_PORTEFEUILLE" --registry "0xADRESSE_VERIFIEE_DU_REGISTRE" --uri "ipfs://CID_DU_DOCUMENT_AGENT"
```

Les exemples sont des paramètres à remplacer, pas des adresses de contrats. Aucune adresse de registre n'est inventée. Vérifier son déploiement et son ABI sur le réseau cible. La sortie contient `from`, `to`, `chainId`, `value` et `data`, sans nonce, gas ni frais : les compléter et les vérifier dans un portefeuille avant signature. Le code ne signe et ne diffuse rien. L'enregistrement effectif et les registres réputation/validation restent non testés et non intégrés.

## x402

L'étude reste ouverte : identifier un service effectivement facturable, choisir un environnement de test, analyser consentement, rejeu, budgets et panne du facilitateur. Aucun en-tête ou paiement simulé n'est présenté comme une transaction réelle. Pas de flux x402 implémenté dans cette version.

Références primaires consultées le 21/10/2026 :

- did:key : https://w3c-ccg.github.io/did-key-spec/
- VC JOSE/COSE : https://www.w3.org/TR/vc-jose-cose/
- Kubo RPC : https://docs.ipfs.tech/reference/kubo/rpc/
- CID : https://docs.ipfs.tech/concepts/content-addressing/
- ERC-8004 : https://eips.ethereum.org/EIPS/eip-8004

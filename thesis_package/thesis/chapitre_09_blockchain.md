# Chapitre 9 — Intégration blockchain

## 9.1 Rôle de la blockchain dans le système

Le registre implémenté (`blockchain/poa_ledger.py`) répond à un besoin
précis, énoncé au Chapitre 2.4 : garantir qu'une détection d'anomalie
confirmée, une fois enregistrée, ne peut être modifiée ou supprimée sans
que cette altération soit détectable. Il ne s'agit **pas** d'une blockchain
au sens des cryptomonnaies (pas de consensus distribué entre pairs
inconnus, pas de preuve de travail) mais d'un registre à **Preuve
d'Autorité (PoA)** — un choix architectural délibéré et justifié : le
contexte d'un opérateur de réseau électrique unique ne présente pas le
problème de confiance décentralisée entre parties inconnues que
résolvent Bitcoin ou Ethereum ; en revanche, la traçabilité inviolable et
l'auditabilité sont directement nécessaires.

## 9.2 Modèle de confiance : Preuve d'Autorité à 4 nœuds

Quatre autorités désignées, représentant des rôles organisationnels
distincts au sein d'un opérateur de réseau :
1. **Utility Operator** — l'exploitant du réseau.
2. **Grid Supervisor** — supervision technique du réseau.
3. **Security Auditor** — audit de sécurité indépendant.
4. **Data Custodian** — gardien des données.

Le proposeur d'un bloc est déterminé par rotation round-robin
(`autorités[index_bloc % 4]`), garantissant qu'aucune autorité unique ne
contrôle la totalité de la chaîne de production des blocs. Chaque autorité
dispose d'un secret dérivé de son étiquette
(`sha256(label + "|smart-grid-poa-secret")`), utilisé pour sceller
(`seal()`) le hachage du bloc qu'elle propose.

## 9.3 Structure d'un bloc

Chaque bloc (`PoABlock`, diagramme de classes `04_class_diagram.png`)
contient : un index, un horodatage, le hachage du bloc précédent (chaînage),
l'identité du proposeur, sa signature, une racine de transactions (hachage
agrégé des enregistrements du bloc), le nombre de transactions, le compte
d'alertes et de lectures normales, et la liste des transactions elles-mêmes.
Le bloc de genèse a un `previous_hash` conventionnellement fixé à
64 zéros.

## 9.4 Cycle de vie d'une notarisation

Référence : diagramme d'activité (`06_activity_diagram.png`) et diagramme
de séquence (`05_sequence_diagram.png`, étapes 6-7). Lorsqu'une anomalie
est confirmée par le pipeline IA et n'est **pas** une duplication d'une
alerte déjà notariée pour ce compteur, l'API construit un enregistrement
(identifiant du compteur, type d'attaque, score, horodatage, hachage de
ligne SHA-256) et l'ajoute au registre via `ingest_records()`. Le registre
calcule la racine de transactions, sélectionne le proposeur par rotation,
signe et chaîne le nouveau bloc.

**Constat d'implémentation important, découvert lors du profilage
(Chapitre 16)** : le paramètre `block_size=10` configuré dans le code
suggère un regroupement de 10 transactions par bloc, mais en pratique,
`ingest_records()` est systématiquement appelée avec une liste d'un seul
enregistrement (`ingest_records([record])`) à chaque anomalie confirmée —
le regroupement en lots de 10 ne se produit donc jamais dans le
fonctionnement observé du système : **chaque anomalie confirmée produit
son propre bloc**. Ce n'est pas un défaut fonctionnel (l'intégrité et le
chaînage restent corrects), mais un écart entre l'intention apparente du
paramètre et le comportement réel, documenté ici par souci d'exhaustivité.

## 9.5 Validation d'intégrité

`validate()` revérifie, pour chaque bloc de la chaîne : la cohérence entre
le nombre de transactions déclaré et la liste réelle, la racine de
transactions recalculée, l'identité et la signature du proposeur, et le
chaînage correct des hachages (`previous_hash` du bloc N = `block_hash` du
bloc N-1). Cette validation est appelée par les endpoints
`/api/blockchain/status` et `/health/detailed`.

**Coût de la validation à l'échelle** (mesuré au Chapitre 16, Figure
`06_blockchain_validate_scaling.png`) : le coût de `validate()` croît
linéairement avec le nombre total d'enregistrements jamais notariés (0,03ms
à 10 enregistrements, 8,86ms à 5000), car chaque appel revérifie
l'intégralité de la chaîne depuis la genèse. Le registre en production ne
contenant qu'un seul bloc au moment du profilage, ce coût est aujourd'hui
négligeable, mais croîtra avec la durée de vie opérationnelle du système —
un point à surveiller plutôt qu'un problème actuel, discuté au
Chapitre 16.3.

## 9.6 Ce qui n'est PAS implémenté (périmètre assumé)

Conformément au Chapitre 1.3, ce registre PoA est une implémentation
**locale et Python native** — il n'ancre pas ses preuves sur une blockchain
publique (Ethereum, Polygon) ni ne s'appuie sur un Smart Contract Solidity.
L'ancrage périodique du hachage de tête de chaîne sur une blockchain
publique, pour bénéficier d'une horodatation externe non répudiable, est
une extension naturelle non réalisée (Chapitre 19).

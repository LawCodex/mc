# LawCodex — Monaco (mc)

Legislation of the Principality of Monaco as Markdown (French), generated from
**Légimonaco** (https://legimonaco.mc), the official legal database of the Principality
(Direction des Affaires Juridiques), which publishes **consolidated** versions of the texts.

Retrieved: **2026-10-13**. Every file is the version in force on that date (the version path
`@YYYY.MM.DD` on Légimonaco is recorded as `last_amended`).

## Coverage

**7,638 Markdown files** — every text of the following kinds that Légimonaco lists as
*currently applicable and not repealed* (texts flagged *abrogé*, versions that have ended and
versions not yet in force are excluded):

| Directory | Content | Files |
|---|---|---|
| `constitution/` | Constitution du 17 décembre 1962 (as revised by loi n° 1.249 of 2 April 2002) | 1 |
| `codes/` | The 10 Monegasque codes: civil, commerce, droit international privé, environnement, mer, pénal, procédure civile, procédure pénale, route, taxes sur le chiffre d'affaires | 10 |
| `lois/<year>/` | Lois (636) and ordonnances-lois (35) | 671 |
| `ordonnances-souveraines/<year>/` | Ordonnances souveraines (Sovereign Ordinances) | 2,558 |
| `decisions-souveraines/<year>/` | Décisions souveraines | 7 |
| `arretes-ministeriels/<year>/` | Arrêtés ministériels | 3,120 |
| `decisions-ministerielles/<year>/` | Décisions ministérielles | 249 |
| `arretes-municipaux/<year>/` | Arrêtés municipaux (Mairie de Monaco) | 211 |
| `arretes-directoriaux/<year>/` | Arrêtés directoriaux | 38 |
| `autres-textes-reglementaires/<year>/` | Other regulatory texts | 116 |
| `decisions/<year>/` | Other decisions | 2 |
| `traites/<year>/` | International treaties and agreements (*Traités et accords internationaux*) | 655 |

`<year>` is the year of the text (signature/enactment date).

### Not covered

- Repealed texts (43 lois/ordonnances-lois and 1,446 regulatory texts flagged *abrogé* by
  Légimonaco) and historical versions.
- Case law, parliamentary works (*travaux législatifs*) and news, which Légimonaco also hosts.
- The *Journal de Monaco* itself (the official gazette); each file links to the issue in which
  the text was published (`publication_url`).
- Images (a few forms / maps) are not copied; text only.

## Structure and format

```
constitution/constitution.md
codes/code-civil.md
lois/1922/1922-01-29-loi-56.md                       <date>-<nature>-<number>.md
ordonnances-souveraines/2026/2026-10-02-ordonnance-12167.md
arretes-ministeriels/2026/2026-09-30-arrete-ministeriel-2026-555.md
traites/2010/2010-06-23-accord-tai1l019009.md
```

Front matter:

```yaml
title: "Loi n° 56 du 29 janvier 1922 sur les fondations"
identifier: "56"                    # official number
type: act                          # constitution | code | act | ordinance_law | sovereign_ordinance | ministerial_order | ... | treaty
jurisdiction: mc
language: fr
date: 1922-01-29                   # date of the text
last_amended: 2024-03-02           # start date of the consolidated version
status: in_force
publication: "Journal de Monaco du 14 février 1922"
publication_url: "https://journaldemonaco.gouv.mc/Journaux/1922/Journal-3345"
thematic: "Associations et fondations"
source: "https://legimonaco.mc/tnc/loi/1922/01-29-56"
source_version: "https://legimonaco.mc/tnc/loi/1922/01-29-56@2024.03.02/"
retrieved: 2026-10-13
```

The hierarchy of the codes and laws (Livre / Titre / Chapitre / Section...) is mapped to Markdown
headings, articles being the deepest heading level (bold labels beyond `######`). Légimonaco's
consolidation notes attached to a division or an article (e.g. «Remplacé par la loi n° 1.440 du
5 décembre 2016», «Abrogé par…») are kept as `>` block quotes right under the heading; editorial
notes (*Notes de la rédaction*) become Markdown footnotes. The large codes are single files
(up to ~0.8 MB).

## Sources

- Document lists: Légimonaco's public search endpoint (`https://legimonaco.mc/~~search/depot/_search`,
  the same query its *Types de contenu* explorer issues) for the content types `tc` (codes),
  `legislation`, `regulation` and `tai`, excluding repealed texts and ended / future versions.
- Texts: the HTML page of each current version, `https://legimonaco.mc/<path>@<version>/`.

## Licence / copyright

Official texts are not protected by copyright in Monaco: **Loi n° 491 du 24 novembre 1948** on
the protection of literary and artistic works, **art. 38**: «Les lois, ordonnances, arrêtés,
décisions et publications administratives, judiciaires ou officielles ne bénéficient pas de la
protection instituée par la présente loi.» Only the *Journal de Monaco* is authentic; Légimonaco
and this mirror are for information.

## Regenerate

```sh
pip install -r scripts/requirements.txt
python scripts/mc_fetch.py      # list + download current versions into ../_raw/mc/ (cached)
python scripts/mc_convert.py    # write Markdown into this repository
```

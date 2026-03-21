# MangoBrain — Workflow Integration

MangoBrain fornisce memoria persistente e associativa tra sessioni Claude Code. Questa rule descrive come e quando usarla nel flusso di lavoro quotidiano.

## Overview

MangoBrain non e' un file da leggere all'inizio. E' un sistema di retrieval attivo: chiedi quello che ti serve, quando ti serve. Le memorie contengono bug passati, decisioni architetturali, pattern, gotcha, riferimenti a utility e componenti — conoscenza che il codice da solo non comunica.

## Integrazione con /discuss

**INTAKE** (inizio discussione):
1. `remember(mode="recent")` — contesto recente, WIP, decisioni
2. Identifica 2-3 aree tecniche del topic
3. `remember(mode="deep", query="[topic in max 10 keyword]")` — quadro generale
4. 1-2x `remember(mode="quick", query="[nomi specifici per area]")` — dettagli mirati
5. Mostra all'utente le memorie rilevanti come contesto

**EXPLORE** (analisi codice):
- L'analyzer esplora il codice, arricchito dal contesto delle memorie
- Se emerge un'area non ancora esplorata, fai una quick query prima di rispondere

**BRAINSTORM** (discussione):
- Le memorie informano il brainstorm:
  - Bug passati nella stessa area: "attenzione, l'ultima volta..."
  - Decisioni architetturali: "questo era stato deciso perche'..."
  - Pattern consolidati: "il pattern usato altrove e'..."

## Integrazione con /task

**ANALYZE** (inizio task):
1. `remember(mode="recent")` — WIP, contesto
2. Strategia multi-query (1 deep + N quick) — vedi mangobrain-remember.md
3. Le memorie guidano l'analisi: sai gia' i gotcha, i pattern, le utility disponibili

**Mid-task** (durante lo sviluppo):
- Prima di toccare un'area nuova: quick query
- Quando trovi un bug: quick query per pattern noti
- Prima di creare un componente: quick query per verificare se esiste gia'

**CLOSE** (fine task):
Il main orchestrator spawna il **mem-manager** come sub-agent con:
- Summary del lavoro fatto
- Lista file modificati (git diff)
- Decisioni prese
- WIP/blocker

Il mem-manager autonomamente:
1. Crea memorie per il lavoro significativo (memorize)
2. Sincronizza file cambiati con memorie esistenti (sync_codebase + update_memory)
3. Registra WIP se presente (memorize con tag "state", "wip")

## Sessioni libere (senza /task)

Per sessioni senza /task (discussioni, esplorazioni, fix rapidi):
- Usa `remember` durante la sessione come descritto sopra
- A fine sessione, usa **/memorize** per sincronizzare il lavoro in memoria
- /memorize prepara un summary e spawna il mem-manager

## Manutenzione periodica

| Attivita | Cadenza | Skill | Cosa fa |
|----------|---------|-------|---------|
| Elaboration | Settimanale | /elaborate | Consolida, crea edge, astrazioni, depreca duplicati |
| Health check | Mensile | /health-check | Diagnosi struttura + contenuto, fix mirati |
| Smoke test | Post-init, post-elaboration | /smoke-test | Verifica qualita' retrieval con query test |

## Il mem-manager agent

Il mem-manager e' un sub-agent specializzato nella gestione della memoria. Non e' un agente interattivo — viene spawnato dal main con un contesto preciso e opera autonomamente.

**Cosa fa:**
- Crea memorie atomiche (2-5 righe, inglese, self-contained)
- Classifica: episodic (eventi), semantic (fatti), procedural (how-to)
- Tagga: 3-6 tag lowercase
- Aggiunge relazioni tra memorie (relates_to, depends_on, caused_by)
- Sincronizza file cambiati con memorie esistenti
- Registra WIP per la prossima sessione

**Cosa NON fa:**
- Non interagisce con l'utente
- Non prende decisioni architetturali

## Quando NON usare la memoria

- **Task puramente meccanici**: "rinomina questa variabile", "aggiungi un import"
- **Fix di una riga**: se il fix e' ovvio e non c'e' nessuna lezione da imparare
- **Operazioni di routine**: npm install, docker restart, git merge
- **Quando il contesto e' gia' tutto nel task**: se il task e' auto-contenuto e non tocca aree complesse

La regola: se il lavoro non produce conoscenza riutilizzabile, non serve memorizzarlo.

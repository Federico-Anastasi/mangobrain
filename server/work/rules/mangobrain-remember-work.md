# MangoBrain Work — Query Strategy

Hai accesso al tool MCP `remember` per recuperare informazioni dal progetto.
Usalo spesso. La memoria contiene decisioni di brand, feedback, pattern, insight sul target e riferimenti che i documenti da soli non comunicano.

## Quando usare remember

- **Inizio sessione**: contesto recente + quadro progetto
- **Prima di creare contenuto**: query su brand, tone, audience per quel canale
- **Quando l'utente chiede qualcosa di nuovo**: verifica se ci sono decisioni passate
- **Quando l'utente dà feedback**: verifica se è un pattern (ha già detto la stessa cosa?)
- **Fine sessione**: `remember(mode="recent")` per confermare cosa salvare

## Strategia multi-query (inizio sessione)

### 1. Recent — dove eravamo
```
remember(mode="recent", project="{PROJECT}", limit=10, k_neighbors=2)
```

### 2. Deep — contesto ampio sul topic
```
remember(query="[5-10 keyword dal topic richiesto]", mode="deep", project="{PROJECT}")
```

### 3. Quick — aree specifiche
```
remember(query="[brand tone voice guidelines]", mode="quick", project="{PROJECT}")
remember(query="[Instagram format carousel content rules]", mode="quick", project="{PROJECT}")
```

## Come formulare le query

### Keyword > frasi naturali
```
BENE: "Instagram carousel CTA engagement caption hashtags"
MALE: "come dovrei scrivere i post per Instagram"
```

### Nomi propri del dominio
```
BENE: "target musician band rehearsal studio booking"
MALE: "il nostro pubblico di riferimento"
```

### Mix area + specifico
```
BENE: "competitor pricing studio booking platform market"
MALE: "analisi della concorrenza"
```

## Cross-project (se disponibile)

Se il progetto ha una memoria Code associata, puoi pescare informazioni sul prodotto:
```
remember(query="feature booking user flow value proposition", project="{CODE_PROJECT}", mode="quick")
```

**REGOLA**: traduci sempre in linguaggio non tecnico prima di usare o mostrare queste informazioni all'utente.

## Quick vs Deep vs Recent

| Mode | Risultati | Quando |
|------|-----------|--------|
| deep | ~20 | Inizio sessione, strategia, analisi ampia |
| quick | ~6 | Mid-session, area specifica, lookup veloce |
| recent | ~15 | Inizio sessione, capire WIP e stato |

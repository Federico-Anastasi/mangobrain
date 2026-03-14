# MangoBrain — Come fare query remember

Hai accesso al tool MCP `remember` per recuperare memorie rilevanti dal progetto.
Usalo spesso, non solo all'inizio del task. Le memorie contengono gotcha, pattern, decisioni e riferimenti che il codice da solo non ti dice.

## Quando usare remember

- **Inizio task/sessione**: contesto ampio (vedi strategia multi-query sotto)
- **Prima di toccare un'area che non conosci**: quick query mirata
- **Quando trovi un bug**: quick query per capire se e' un pattern noto
- **Prima di creare un componente/utility**: quick query per verificare se esiste gia' qualcosa di simile
- **Quando prendi una decisione architetturale**: quick query per capire se ci sono precedenti
- **Fine task**: remember(mode="recent") per verificare WIP e contesto da passare al librarian

## Strategia multi-query (inizio task)

NON fare una singola query generica. Usa **1 deep + N quick**:

### 1. Leggi il task e identifica 2-4 aree tecniche distinte

### 2. 1x deep — quadro generale
```
remember(query="[max 10 keyword dal task]", mode="deep", project="{PROJECT}")
```
Cattura: pattern cross-cutting, convenzioni, gotcha ricorrenti. ~20 risultati.

### 3. 2-4x quick — una per area tecnica
```
remember(query="[nomi specifici: componenti, hook, service, file]", mode="quick", project="{PROJECT}")
```
Cattura: dettagli specifici di ogni cluster. ~6 risultati ciascuna.

### Perche' funziona
Ogni query pesca da un cluster diverso del grafo associativo. Una singola deep generica tira risultati da 1-2 cluster e perde gli altri. 3 quick mirate coprono 3 cluster diversi.

## Come formulare le query

### Keyword > frasi naturali
```
BENE: "formatPrice cents euros conversion gotcha"
MALE: "come funziona la formattazione dei prezzi nel sistema"
```

### Nomi propri sempre
Usa nomi di componenti, hook, service, file, utility quando li conosci:
```
BENE: "useStripeConnect ConnectAccountManagement onboarding embedded"
MALE: "sistema di onboarding per i pagamenti Stripe"
```

### Mix tecnico + dominio
```
BENE: "booking wizard localStorage state persistence gotcha"
MALE: "problemi con il wizard di prenotazione"
```

## Quick vs Deep vs Recent

| Mode | Risultati | Grafo | Quando |
|------|-----------|-------|--------|
| deep | ~20 | pieno (alpha=0.3) | Inizio task, quadro generale |
| quick | ~6 | leggero (alpha=0.15) | Mid-task, aree specifiche, lookup |
| recent | ~15 + vicini | per tempo | Inizio sessione, capire WIP |

## Strategia per contesto di lavoro

### Inizio sessione (sempre)
```
remember(mode="recent", project="{PROJECT}", limit=15, k_neighbors=2)
```
Ti da: ultime 15 memorie + contesto collegato dal grafo. Capisci WIP, blocker, decisioni recenti.

### Mid-task: stai per toccare un'area nuova
```
remember(query="[nomi file, componenti, concetti dell'area]", mode="quick", project="{PROJECT}")
```

### Mid-task: hai trovato un bug
```
remember(query="[keyword del bug + area + pattern]", mode="quick", project="{PROJECT}")
```

### Fine task / pre-librarian
```
remember(mode="recent", project="{PROJECT}")
```
Verifica WIP e contesto da passare al librarian per il sync.

## Esempi reali

### Task: "Fix prezzo sbagliato nel booking wizard"
```
deep:  "booking wizard UX fix price bug mobile layout"
quick: "formatPrice cents euros conversion serializeBooking gotcha"
quick: "BookingWizard steps BookingPaymentStep BookingSummaryStep"
```

### Task: "Refactor profilo + pagamenti condivisi"
```
deep:  "account profilo refactor shared components owner teacher payments Stripe"
quick: "ProfiloPage TeacherAccountPage structure password removal"
quick: "Stripe Connect onboarding useStripeConnect ConnectAccountManagement"
quick: "User model schema getMe provider stripeAccountId Prisma"
quick: "Google Calendar routes sync disconnect auth calendarSyncJob"
```

### Mid-task: stai per toccare il sistema di email
```
quick: "email Resend templates transactional React Email service"
```

### Mid-task: hai trovato un bug con i prezzi
```
quick: "price double-division cents euros formatPrice formatMoneyValue"
```

### Inizio sessione generica
```
recent: limit=15, k_neighbors=2
deep:   "project overview architecture current state WIP"
```

# Note di rilascio — v7.11

Prima release pubblica dei sorgenti dell'applicazione desktop v7.11.

- Ricerca Spansh: la tabella pianeti riporta `volcanism_type` in **Volcanism**; STOP interrompe la ricerca prima della scrittura finale dei risultati.
- Fogli: collega il modello ufficiale, copia le schede di riferimento mancanti e conserva quelle già presenti; mantiene le funzioni di riparazione e stile.
- Finestra: rendering DPI nativo, permanenza in primo piano e modalità Compact/Expand con controllo compatto nell'angolo inferiore destro della scheda di scansione.
- Distribuzione: metadati Windows allineati a **0.7.11.0**; verifica preliminare di risorse e credenziali OAuth Desktop; script Windows per creare EXE, cartella di release, ZIP e impronta SHA-256.
- Pulizia: esclusi mockup e screenshot del prototipo, cronologia di test e dati personali; conservata una copia di riferimento dell'Apps Script v9 in `docs/`.

## Verifica Windows — 13 settembre 2026

L'EXE è stato compilato ed eseguito su Windows 11. La prova delle funzioni dell'interfaccia è stata confermata e il log documenta:

- collegamento a `ED Hotspots & Landables Finder`; le schede `Minerals Table` e `Volcanism Table` erano già presenti e sono state lasciate invariate;
- scansione manuale di un sistema completata, con 8 pianeti e 8 righe di dati scritte nel foglio;
- ricerca di 361 sistemi `Edmund Mahon / Stronghold`, interrotta con STOP durante il sesto di 15 lotti: la scansione risulta annullata e la tabella parziale non è stata scritta.

La build di prova Windows usava credenziali OAuth proprie e non è inclusa nella release pubblica dei sorgenti. Per compilare un EXE con il proprio client Google, seguire `README.md`.

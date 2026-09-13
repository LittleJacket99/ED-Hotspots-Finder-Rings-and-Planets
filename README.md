# ED Hotspots & Landables Finder — v7.11

Applicazione Windows per cercare hotspot e pianeti atterrabili tramite Spansh e scrivere i risultati in Google Sheets. La tabella dei pianeti include il campo **Volcanism**. Il modello Google Sheets è accessibile con **Open Template** nell'app.

Questa repository distribuisce i **sorgenti** della release v7.11. L'EXE va compilato sul proprio Windows con il proprio client OAuth Desktop; non sono incluse credenziali o token personali.

## Creare l'EXE su Windows 11

1. Installa Python 3.10 con il launcher `py` e connettiti a Internet.
2. Estrai lo ZIP dei sorgenti in una cartella normale.
3. Metti nella stessa cartella un file `credentials.json` del tuo **client OAuth Google di tipo Applicazione desktop**. Il file non è incluso nello ZIP.
4. Avvia `build_windows.bat` con un doppio clic. Lo script controlla il formato delle credenziali e le risorse, installa le dipendenze, compila e prepara la release.
5. Trovi il programma in `dist\ED Hotspots & Landables Finder.exe` e il pacchetto pronto in `release\HotspotsFinder-v7.11-Windows.zip`.

Non serve installare Python sul PC che esegue l'EXE. L'eseguibile incorpora `credentials.json` e `logo.png` al momento della build; usa `app.ico` per l'icona e `version_info.txt` per la versione Windows. Il token OAuth e il collegamento al foglio restano separati in `%APPDATA%\HotspotsFinder\token.json` e `config.json`. Una nuova build non dovrebbe quindi cancellare autorizzazione, configurazione o fogli già collegati.

**Distribuzione:** l'EXE contiene il client OAuth con cui lo hai compilato, recuperabile da chi riceve il file. Usa credenziali destinate alla distribuzione se intendi pubblicarlo. Non inserire mai `credentials.json`, `token.json`, `config.json` o la release compilata con credenziali personali in un repository pubblico. `.gitignore` esclude questi file dalle normali aggiunte Git; controlla comunque `git status` prima di un push.

## Prima verifica su Windows

- Avvia l'EXE e verifica icona, logo, nitidezza e permanenza sopra una finestra normale, anche dopo minimizzazione e ripristino.
- Usa **Open Template** oppure **Connect / Change Sheet**, poi **Open My Sheet**. Un foglio senza le schede `Minerals Table` e `Volcanism Table` deve ricevere solo quelle mancanti; riconnettendolo, eventuali modifiche alle schede devono restare.
- Prova **Repair Sheet**, **Save Current Style** e **Restore Official Style**.
- Esegui una scansione piccola: controlla la colonna **Volcanism** (T) e **LS Distance** (U) nella tabella dei pianeti.
- Esegui una scansione più lunga e premi **STOP** prima della scrittura finale: il risultato parziale non deve essere pubblicato e lo stato deve diventare “Scan cancelled”.
- Prova **Compact/Expand** prima e durante una scansione; in modalità compatta devono restare visibili SCAN, STOP durante l'esecuzione, avanzamento e stato. Se i dettagli erano aperti, Expand deve ripristinarli.

L'EXE non è firmato: Windows SmartScreen potrebbe mostrare un avviso per editore sconosciuto. Il file `SHA256.txt` nella release Windows contiene l'impronta dell'EXE per controllarne l'integrità.

## Contenuto dei sorgenti

`hotspots_finder_gui.py` e `hotspots_engine.py` contengono l'app; `HotspotsFinder.spec`, `build_windows.bat`, `package_release.ps1` e `validate_release.py` gestiscono la build. `docs/HotspotsFinder_Template_AppsScript_v9.gs` è una copia di riferimento dello script associato al modello Sheets: non viene incorporata nell'EXE. Anteprime HTML/PNG e cronologia dei prototipi sono state tolte dal pacchetto di distribuzione.

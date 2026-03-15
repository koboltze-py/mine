# Einsatzbericht Manager

Ein professionelles Python-Programm mit PySide6 GUI zur Verwaltung und Erstellung von Einsatzberichten mit Claude AI Integration.

## Features

- ✨ **Claude AI Integration**: Automatische Erstellung von Einsatzberichten mit KI
- 📝 **Berichtsverwaltung**: Erstellen, Bearbeiten, Lesen und Löschen von Berichten
- 💾 **SQLite Datenbank**: Übersichtliche Verwaltung aller Berichte
- 📄 **Export**: Berichte als PDF und Word-Dokumente exportieren
- 🔍 **Suche**: Durchsuchen Sie alle Berichte nach Titel, Thema oder Inhalt
- 🎨 **Moderne GUI**: Benutzerfreundliche Oberfläche mit PySide6

## Installation

1. **Repository klonen oder herunterladen**

2. **Python-Umgebung einrichten** (empfohlen: Python 3.9+)
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Abhängigkeiten installieren**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Claude API Key setzen**
   
   Setzen Sie Ihren Anthropic API Key als Umgebungsvariable:
   
   **Windows PowerShell:**
   ```powershell
   $env:ANTHROPIC_API_KEY = "ihr-claude-api-key"
   ```
   
   **Windows CMD:**
   ```cmd
   set ANTHROPIC_API_KEY=ihr-claude-api-key
   ```
   
   Oder dauerhaft in den Systemumgebungsvariablen setzen.

## Verwendung

### Programm starten

```powershell
python main.py
```

### Funktionen

#### 1. Übersicht
- Zeigt alle gespeicherten Einsatzberichte in einer Tabelle
- Suche nach Berichten
- Öffnen, Löschen und Exportieren von Berichten

#### 2. Neuer Bericht
- Titel und Thema eingeben
- Zusätzliche Informationen hinzufügen (optional)
- Mit Claude AI generieren lassen
- Vorschau des generierten Berichts
- Speichern in der Datenbank

#### 3. Ansehen/Bearbeiten
- Berichte aus der Übersicht öffnen
- Titel, Thema und Inhalt bearbeiten
- Änderungen speichern
- Als PDF oder Word exportieren

## Projektstruktur

```
E:\mines schummel\
├── main.py                 # Hauptprogramm
├── requirements.txt        # Python-Abhängigkeiten
├── README.md              # Diese Datei
├── src/                   # Source-Code
│   ├── database.py        # SQLite Datenbank-Handler
│   ├── claude_api.py      # Claude API Integration
│   ├── report_generator.py # PDF/Word Generator
│   └── gui.py             # PySide6 GUI
├── data/                  # Datenbank-Dateien
│   └── einsatzberichte.db # SQLite Datenbank
├── reports/               # Generierte Berichte (PDF/Word)
└── examples/              # Beispiel-Einsatzberichte
    ├── beispiel_brand.txt
    ├── beispiel_verkehrsunfall.txt
    └── beispiel_technische_hilfeleistung.txt
```

## Beispielberichte

Im `examples/` Ordner finden Sie drei Beispiel-Einsatzberichte:
- Brand in einem Mehrfamilienhaus
- Verkehrsunfall mit eingeklemmter Person
- Technische Hilfeleistung (Person in Maschine eingeklemmt)

Diese können als Vorlage oder Referenz verwendet werden.

## Datenbank-Schema

```sql
CREATE TABLE einsatzberichte (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titel TEXT NOT NULL,
    thema TEXT NOT NULL,
    inhalt TEXT NOT NULL,
    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    aktualisiert_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    pdf_pfad TEXT,
    word_pfad TEXT,
    erstellt_von TEXT DEFAULT 'Claude AI'
)
```

## Technologie-Stack

- **GUI**: PySide6 (Qt for Python)
- **AI**: Anthropic Claude API
- **PDF**: ReportLab
- **Word**: python-docx
- **Datenbank**: SQLite3
- **Python**: 3.9+

## Fehlerbehebung

### API Key Fehler
Wenn Sie die Fehlermeldung "Claude API Key nicht gefunden" erhalten:
- Stellen Sie sicher, dass die Umgebungsvariable `ANTHROPIC_API_KEY` gesetzt ist
- Überprüfen Sie, ob der API Key gültig ist
- Das Programm startet auch ohne API Key, aber AI-Funktionen sind deaktiviert

### Import Fehler
Falls Module fehlen:
```powershell
pip install -r requirements.txt --upgrade
```

### Datenbankfehler
Falls die Datenbank beschädigt ist:
- Löschen Sie `data/einsatzberichte.db`
- Das Programm erstellt beim nächsten Start eine neue Datenbank

## Lizenz

Dieses Projekt ist für den internen Gebrauch bestimmt.

## Kontakt

Bei Fragen oder Problemen wenden Sie sich bitte an den Entwickler.

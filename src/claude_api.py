"""
Claude API Handler für Einsatzberichte
"""
import anthropic
import os
from typing import Optional, List


class ClaudeAPIHandler:
    def __init__(self, api_key: Optional[str] = None, beispiele_pfad: str = "examples"):
        """
        Initialisiert den Claude API Handler

        Args:
            api_key: Claude API Key (falls nicht angegeben, wird ANTHROPIC_API_KEY aus env verwendet)
            beispiele_pfad: Pfad zum Ordner mit Beispielberichten (für Stilvorlage)
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Claude API Key nicht gefunden. Bitte setzen Sie ANTHROPIC_API_KEY als Umgebungsvariable oder übergeben Sie den Key.")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.beispiele = self._load_beispiele(beispiele_pfad)

    def _load_beispiele(self, pfad: str) -> List[str]:
        """Lädt Beispielberichte aus dem angegebenen Ordner als Stilvorlagen (.txt, .docx, .odt, .pdf, .pages)."""
        beispiele = []
        if not os.path.isdir(pfad):
            return beispiele
        for fname in sorted(os.listdir(pfad)):
            fpath = os.path.join(pfad, fname)
            ext = fname.lower().rsplit('.', 1)[-1]
            try:
                if ext == 'txt':
                    with open(fpath, 'r', encoding='utf-8') as f:
                        text = f.read().strip()
                elif ext == 'docx':
                    from docx import Document
                    doc = Document(fpath)
                    text = '\n'.join(p.text for p in doc.paragraphs if p.text.strip())
                elif ext == 'odt':
                    from odf.opendocument import load
                    from odf.text import P
                    from odf import teletype
                    doc = load(fpath)
                    text = '\n'.join(
                        teletype.extractText(p)
                        for p in doc.text.getElementsByType(P)
                        if teletype.extractText(p).strip()
                    )
                elif ext == 'pdf':
                    from pypdf import PdfReader
                    reader = PdfReader(fpath)
                    lines = []
                    for page in reader.pages:
                        t = page.extract_text()
                        if t:
                            lines.append(t)
                    text = '\n'.join(lines).strip()
                elif ext == 'pages':
                    import zipfile, xml.etree.ElementTree as ET, re as _re
                    text = ''
                    try:
                        with zipfile.ZipFile(fpath, 'r') as zf:
                            names = zf.namelist()
                            if 'index.xml' in names:
                                with zf.open('index.xml') as f:
                                    content = f.read().decode('utf-8', errors='ignore')
                                try:
                                    root = ET.fromstring(content)
                                    parts = []
                                    for elem in root.iter():
                                        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                                        if tag == 'content' and elem.text and elem.text.strip():
                                            parts.append(elem.text.strip())
                                    text = '\n'.join(parts)
                                except ET.ParseError:
                                    text = ' '.join(t.strip() for t in _re.findall(r'>([^<]+)<', content) if t.strip())
                            else:
                                # Neues Pages-Format (post-2013): .iwa Binärdateien
                                # Textfragmente mittels Byte-Scan extrahieren (nur Dateien die Fließtext enthalten)
                                import re as _re2
                                parts = []
                                # IWA-Dateien die bekanntermaßen keinen lesbaren Text enthalten überspringen
                                _SKIP_IWA = ('stylesheet', 'chart', 'table', 'thumbnail',
                                             'preview', 'annotation', 'datalist', 'data-list')
                                for iwa_name in names:
                                    if not iwa_name.endswith('.iwa'):
                                        continue
                                    lower_iwa = iwa_name.lower()
                                    if any(skip in lower_iwa for skip in _SKIP_IWA):
                                        continue
                                    raw = zf.read(iwa_name)
                                    # Nur UTF-8-Sequenzen extrahieren die mindestens ein Leerzeichen enthalten
                                    # (echte Sätze bestehen aus mehreren durch Leerzeichen getrennten Wörtern)
                                    for m in _re2.finditer(
                                        rb'[\x20-\x7e\xc0-\xff]{12,}',
                                        raw
                                    ):
                                        s = m.group().decode('utf-8', 'replace').strip()
                                        # Mindestens 2 Leerzeichen → mindestens 3 Wörter
                                        if s.count(' ') < 2:
                                            continue
                                        s = _re2.sub(r'[^\w\s\.\,\!\?\-\:\;\(\)äöüÄÖÜß]', ' ', s)
                                        s = _re2.sub(r'\s{2,}', ' ', s).strip()
                                        if len(s) >= 12 and _re2.search(r'[a-zA-ZäöüÄÖÜß]{4}', s):
                                            parts.append(s)
                                text = '\n'.join(parts)
                    except zipfile.BadZipFile:
                        pass
                    text = text.strip()
                else:
                    continue
                if text:
                    beispiele.append(text)
            except Exception:
                pass
        return beispiele

    # Regex-Muster die typische Apple-Pages-Metadaten und Formatierungs-IDs matchen
    _PAGES_JUNK_RE = None  # wird beim ersten Aufruf initialisiert

    @classmethod
    def _get_junk_re(cls):
        import re as _re
        if cls._PAGES_JUNK_RE is None:
            cls._PAGES_JUNK_RE = _re.compile(
                r'paragraphStyle|shapestyle|categoryaxis|referenceLine|valueaxi|'
                r'footerRow|footerCol|headerColumn|headerRow|stickyComment|'
                r'tocentry|svgimport|drawingline|HelveticaN|DocumentStyle|'
                r'ViewState|StorageBucket|TPMac|TSC[A-Z]|TaePP|'
                r'tile_paper|bullet_circle|_theme\b|hardcover|'
                r'Directional\s+Key|Fill\s+(Right|Left|Center)|Formal\s+Shadow|'
                r'Note\s+Tak|DataList|AnnotationAuthor|'
                r'\w+[-_]\d+[-_]\w|'   # Bezeichner wie chart-1-paragraphStyle
                r'\w+_\d{1,3}\b|'      # Bezeichner wie paragraphStyle_19
                r'\.[a-z]{2,4}[\s\)]|' # Dateiendungen wie .jpg .png .pdf
                r'[A-Za-z]+:[a-z]{0,3}[A-Z]',  # Fontname-Suffixe wie HelveticaNeue:bW
                _re.IGNORECASE
            )
        return cls._PAGES_JUNK_RE

    def _bereinige_zeilen(self, text: str) -> str:
        """Entfernt Apple-Pages-Metadaten und technische Bezeichner aus IWA-extrahiertem Text."""
        import re as _re
        junk_re = self._get_junk_re()
        gute = []
        for zeile in text.splitlines():
            z = zeile.strip()
            if not z or len(z) < 8:
                continue
            # Bekannte Apple-Metadaten-Muster sofort verwerfen
            if junk_re.search(z):
                continue
            # Reine Datum-/Zahlen-/Formatstrings ohne echtes Wort überspringen
            if _re.fullmatch(r'[\w\.\#,\s:;\-/%±°]+', z) and not _re.search(r'[a-zA-ZäöüÄÖÜß]{5}', z):
                continue
            # CamelCase-Bezeichner (mehrere Großbuchstaben in einem Wort ohne Leerzeichen → technisch)
            woerter = z.split()
            if len(woerter) == 1:
                gross = _re.findall(r'[A-Z]', z)
                if len(gross) > 2:  # einzelnes Wort mit 3+ Großbuchstaben = CamelCase-ID
                    continue
            # Mindestens 3 durch Leerzeichen getrennte Tokens (echte Sätze oder Abschnittsköpfe)
            if len(woerter) < 3:
                # Ausnahme: Abschnittsüberschriften (kurzes Wort + Doppelpunkt, z.B. "Alarmierung:")
                ist_header = (len(woerter) <= 2
                              and _re.fullmatch(r'[A-ZÄÖÜ][a-zA-ZäöüÄÖÜß\s/]+:?', z)
                              and len(z) <= 30)
                if not ist_header:
                    continue
            # Buchstabenanteil muss dominant sein (kein Zeichensalat)
            buchstaben = sum(1 for c in z if c.isalpha())
            if buchstaben / len(z) < 0.55:
                continue
            gute.append(z)
        return '\n'.join(gute)

    def _stil_kontext(self) -> str:
        """Baut den Stilkontext-Block aus den Beispielberichten auf."""
        if not self.beispiele:
            return ""
        teile = [
            "STILVORLAGEN – Diese Berichte dienen NUR als Stil- und Formatreferenz.\n"
            "Analysiere und übernimm daraus AUSSCHLIESSLICH:\n"
            "  • Schreibstil, Ton, Erzählperspektive (Ich-Form etc.)\n"
            "  • Gliederung und Abschnittsüberschriften\n"
            "  • Fachbegriffe und Abkürzungen (RTW, NEF, Pat., GCS etc.)\n"
            "Den INHALT (Namen, Orte, Diagnosen, Medikamente) aus den Vorlagen NICHT übernehmen.\n"
        ]
        for i, b in enumerate(self.beispiele, 1):
            bereinigt = self._bereinige_zeilen(b)
            if bereinigt:
                teile.append(f"--- Beispielbericht {i} ---\n{bereinigt}\n")
        teile.append("--- Ende der Stilvorlagen ---")
        teile.append(
            "\nSTIL-REGELN (zwingend einhalten):\n"
            "- Identische Abschnittsüberschriften wie in den Vorlagen (z.B. Alarmierung, Vor Ort, Maßnahmen, Fazit)\n"
            "- Gleiche Abkürzungen übernehmen (RTW, NEF, Pat., GCS, EG, UH, KH usw.)\n"
            "- Gleiche Erzählperspektive (Ich-Form wenn Vorlage Ich-Form nutzt)\n"
            "- Gleiche Detailtiefe: konkrete Uhrzeiten, Straßen, Befunde, Vitalwerte\n"
            "- Gleiche medizinischen/fachlichen Schemata (ABCDE, OPQRST, SAMPLER etc.) falls in Vorlage vorhanden\n"
            "- Gleicher informeller aber fachlicher Ton\n"
        )
        return "\n".join(teile)
    
    def einsatzbericht_erstellen(self, thema: str, zusaetzliche_infos: str = "",
                                 seitenzahl: int = 2, datum: str = "",
                                 uhrzeit: str = "", stichwort: str = "",
                                 schemata: list = None, medikamente: str = "",
                                 rettungsmittel: str = "",
                                 vitalwerte: dict = None) -> str:
        """
        Erstellt einen Einsatzbericht.
        Schreibstil und Format werden NUR aus den Beispielberichten abgeleitet (nicht der Inhalt).

        Args:
            thema: Einsatzstichwort / Thema
            zusaetzliche_infos: Eigener Kontext / Zusatzinfos
            seitenzahl: Gewünschter Umfang in DIN A4-Seiten
            datum: Einsatzdatum (dd.MM.yyyy)
            uhrzeit: Alarmierungszeit (HH:mm)
            stichwort: Alarmierungsstichwort
            schemata: Liste der anzuwendenden Schemata (ABCDE, OPQRST, SAMPLER…)
            medikamente: Verabreichte Medikamente
            rettungsmittel: Beteiligte Rettungsmittel
        """
        if vitalwerte is None:
            vitalwerte = {}
        if schemata is None:
            schemata = []
        stil = self._stil_kontext()
        seiten_info = f"Umfang: ca. {seitenzahl} DIN A4-Seite(n) – bitte entsprechend ausführlich formulieren."

        # Einsatz-Detailblock aufbauen
        details = []
        if datum:
            details.append(f"Datum: {datum}")
        if uhrzeit:
            details.append(f"Alarmierungszeit: {uhrzeit} Uhr")
        if stichwort:
            details.append(f"Alarmierungsstichwort: {stichwort}")
        if rettungsmittel:
            details.append(f"Beteiligte Rettungsmittel: {rettungsmittel}")
        if vitalwerte:
            vw_label = {
                'rr': ('RR', 'mmHg'), 'hf': ('HF', '/min'), 'spo2': ('SpO2', '%'),
                'spco': ('SpCO', '%'), 'af': ('AF', '/min'), 'bz': ('BZ', 'mmol/l'),
                'temp': ('Temp', '\u00b0C'), 'gcs': ('GCS', ''), 'etco2': ('EtCO2', 'mmHg'),
            }
            vw_lines = []
            for k, v in vitalwerte.items():
                if str(v).strip():
                    lbl, unit = vw_label.get(k, (k, ''))
                    vw_lines.append(f"  {lbl}: {v} {unit}".strip())
            if vw_lines:
                details.append(f"Vitalwerte / Messwerte (im Bericht nat\u00fcrlich erw\u00e4hnen):\n" + "\n".join(vw_lines))
        if medikamente:
            # Medikamente als nummerierte Liste formatieren
            med_lines = [l.strip() for l in medikamente.splitlines() if l.strip()]
            if med_lines:
                med_block = "\n".join(f"  {i+1}. {l}" for i, l in enumerate(med_lines))
                details.append(f"Verabreichte Medikamente (im Bericht als eigene Sektion mit je Medikament: "
                                f"Arzneimittelgruppe, Indikation, Kontraindikation, UAW, Dosierung/Durchführung):\n{med_block}")
            else:
                details.append(f"Verabreichte Medikamente: {medikamente}")
        if schemata:
            # Schemata nach Typ aufteilen für klare Claude-Instruktionen
            abcde_entries, opqrst_entries, sampler_entries, simple_entries = [], [], [], []
            for s in schemata:
                first = s.split('\n')[0].strip().lower()
                if first.startswith('xabcde') or first.startswith('abcde'):
                    abcde_entries.append(s)
                elif first.startswith('opqrst'):
                    opqrst_entries.append(s)
                elif first.startswith('sampler'):
                    sampler_entries.append(s)
                else:
                    simple_entries.append(s)
            if abcde_entries:
                details.append(
                    f"xABCDE-Schema (NUR qualitative Befunde, KEINE Messwerte – diese stehen in Vitalwerte):\n"
                    + "\n".join(f"  {s}" for s in abcde_entries)
                )
            if opqrst_entries:
                details.append(
                    f"OPQRST-Schmerzanamnese (im Bericht als eigene Anamnese-Sektion einbauen):\n"
                    + "\n".join(f"  {s}" for s in opqrst_entries)
                )
            if sampler_entries:
                details.append(
                    f"SAMPLER-Anamnese (im Bericht als eigene Anamnese-Sektion einbauen):\n"
                    + "\n".join(f"  {s}" for s in sampler_entries)
                )
            if simple_entries:
                details.append(
                    f"Weitere Befunde / Scores (im Bericht natürlich erwähnen):\n"
                    + "\n".join(f"  {s}" for s in simple_entries)
                )
        if zusaetzliche_infos:
            details.append(f"Zusätzliche Informationen / Kontext: {zusaetzliche_infos}")
        detail_block = "\n".join(details)

        if stil:
            prompt = (
                f"{stil}\n\n"
                f"AUFGABE: Schreibe einen NEUEN, originellen Einsatzbericht.\n"
                f"WICHTIG: Übernimm aus den Stilvorlagen AUSSCHLIESSLICH:\n"
                f"  • Schreibstil, Ton, Perspektive (Ich-Form etc.)\n"
                f"  • Gliederung / Abschnittsüberschriften\n"
                f"  • Fachbegriffe und Abkürzungen (RTW, NEF, Pat., GCS etc.)\n"
                f"  • Detailtiefe und Erzählweise\n"
                f"NICHT übernehmen: Namen, Orte, Diagnosen, Medikamente aus den Vorlagen.\n\n"                f"FORMATIERUNGSREGELN (zwingend einhalten):\n"
                f"  - KEIN Markdown: keine Sternchen (*/**), keine #-Überschriften, kein __Fett__\n"
                f"  - Abschnittsüberschriften als normalen Text ohne Sonderzeichen\n"
                f"  - Schema-Einträge im Format: Buchstabe= Text  (Beispiel: 'A= Atemweg frei')\n"
                f"  - Messwerte im Format: Kürzel- Wert  (Beispiel: 'RR- 130/85; HF- 92')\n"
                f"  - Fließtext ohne Aufzählungszeichen außer für Medikamentenlisten\n"
                f"  - Jedes Medikament bekommt eine eigene Sektion mit: Arzneimittelgruppe, Indikation,\n"
                f"    Kontraindikation, Unerwünschte Arzneimittelwirkung (UAW), Dosierung/Durchführung\n"
                f"  - OPQRST-Einträge als Schmerzanamnese-Abschnitt einbauen (O=/P=/Q=/R=/S=/T=)\n"
                f"  - SAMPLER-Einträge als Anamnese-Abschnitt einbauen (S=/A=/M=/P=/L=/E=/R=)\n\n"                f"EINSATZ-DATEN (diese konkret verwenden):\n{detail_block}\n\n"
                f"{seiten_info}\n\n"
                f"Erfinde realistische, stimmige Details für alles was nicht angegeben wurde "
                f"(Straße, Hausnummer, Patientenalter/-geschlecht, Vitalwerte, Verlauf)."
            )
        else:
            prompt = (
                f"Erstelle einen professionellen Einsatzbericht für den Rettungsdienst.\n\n"
                f"FORMATIERUNGSREGELN (zwingend einhalten):\n"
                f"  - KEIN Markdown: keine Sternchen (*/**), keine #-Überschriften, kein __Fett__\n"
                f"  - Schema-Eintr\u00e4ge im Format: Buchstabe= Text  (Beispiel: 'A= Atemweg frei')\n"
                f"  - ABCDE-Schema im Bericht NUR qualitative Befunde (kein RR/HF/SpO2/BZ/Temp/GCS)\n"
                f"  - Vitalwerte trotzdem nat\u00fcrlich im Flie\u00dftext erw\u00e4hnen\n"
                f"  - OPQRST-Einträge als Schmerzanamnese-Abschnitt einbauen (O=/P=/Q=/R=/S=/T=)\n"
                f"  - SAMPLER-Einträge als Anamnese-Abschnitt einbauen (S=/A=/M=/P=/L=/E=/R=)\n"
                f"  - Jedes Medikament bekommt eine eigene Sektion mit: Arzneimittelgruppe, Indikation,\n"
                f"    Kontraindikation, UAW, Dosierung/Durchführung\n\n"
                f"EINSATZ-DATEN:\n{detail_block}\n\n"
                f"{seiten_info}\n\n"
                f"Struktur: Alarmierung (Uhrzeit/Stichwort), Einsatzort, Lage bei Ankunft, "
                f"Durchgeführte Maßnahmen (xABCDE-Schema), Medikamente/Therapie, Transport/Übergabe, Fazit.\n"
                f"Erfinde realistische Details für fehlende Angaben."
            )

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            return message.content[0].text

        except Exception as e:
            raise Exception(f"Fehler beim Erstellen des Einsatzberichts: {str(e)}")

    def medikament_details_abrufen(self, medikament_namen: list) -> list:
        """
        Fragt bei Claude-KI Wirkweise, Nebenwirkungen und Kontraindikation
        für eine Liste von Medikamenten ab.

        Returns:
            Liste von dicts: [{'name', 'wirkweise', 'nebenwirkungen', 'kontraindikation'}, ...]
        """
        if not medikament_namen:
            return []
        namen_block = "\n".join(f"- {n}" for n in medikament_namen)
        prompt = (
            f"Du bist ein medizinischer Fachinformationsdienst für den Rettungsdienst.\n"
            f"Gib für jedes der folgenden Notfallmedikamente eine kompakte, fachlich korrekte "
            f"Übersicht in DEUTSCH aus.\n\n"
            f"Medikamente:\n{namen_block}\n\n"
            f"Antworte AUSSCHLIESSLICH als JSON-Array in diesem Format (kein Markdown, keine Erklärungen):\n"
            f'[\n'
            f'  {{\n'
            f'    "name": "<exakter Name wie eingegeben>",\n'
            f'    "wirkweise": "<Kurzform: Wirkstoffklasse + Wirkprinzip, max 1-2 Sätze>",\n'
            f'    "nebenwirkungen": "<häufigste/relevanteste NW im Notfall, max 1-2 Sätze>",\n'
            f'    "kontraindikation": "<wichtigste KI im Notfallbereich, max 1-2 Sätze>",\n'
            f'    "indikation": "<Kurzform: wofür eingesetzt im RD, max 1 Satz>",\n'
            f'    "dosierung": "<typische Notfalldosierung laut AWMF/AHA, max 1-2 Sätze>",\n'
            f'    "applikation": "<mögliche Applikationswege im Notfall>",\n'
            f'    "arzneimittelgruppe": "<Wirkstoffklasse/Gruppe>",\n'
            f'    "inkubationszeit": "<Wirkungseintritt nach Gabe, max 1 Satz>"\n'
            f'  }}\n'
            f']\n\n'
            f"Halte dich STRIKT an das JSON-Format. Antworte mit nichts außer dem JSON-Array."
        )
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )
            import json as _json, re as _re
            raw = message.content[0].text.strip()
            # JSON aus Antwort extrahieren (falls doch Markdown-Fence dabei)
            m = _re.search(r'\[.*\]', raw, _re.DOTALL)
            if m:
                raw = m.group()
            return _json.loads(raw)
        except Exception as e:
            raise Exception(f"Fehler beim Abrufen der Medikamenten-Details: {str(e)}")
    
    def stil_analysieren(self) -> dict:
        """
        Lässt Claude die geladenen Beispielberichte analysieren und empfiehlt
        Schriftart, Schriftgröße und liefert eine Stil-Beschreibung.

        Returns:
            dict mit Schlüsseln:
              'schriftart'     – z.B. "Arial" | "Times New Roman" | "Courier New"
              'schriftgroesse' – int, z.B. 11
              'beschreibung'   – kurzer Freitext zur Stil-Analyse
        """
        if not self.beispiele:
            return {
                'schriftart': 'Arial',
                'schriftgroesse': 11,
                'beschreibung': 'Keine Stilvorlagen vorhanden – Standardwerte verwendet.'
            }

        vorlagen_text = '\n\n'.join(
            f"--- Vorlage {i+1} ---\n{b}" for i, b in enumerate(self.beispiele)
        )

        prompt = (
            "Analysiere die folgenden Einsatzberichte und beantworte diese drei Fragen:\n\n"
            "1. SCHRIFTART: Welche Schriftart passt am besten zum Stil dieser Berichte? "
            "Wähle genau eine aus: Arial, Times New Roman, Courier New\n"
            "2. SCHRIFTGRÖSSE: Welche Schriftgröße (in Punkt, ganzzahlig, zwischen 8 und 16) "
            "ist für diesen Berichtsstil angemessen?\n"
            "3. STIL-BESCHREIBUNG: Beschreibe den Schreibstil dieser Berichte in 2-3 Sätzen "
            "(Ton, Struktur, Fachlichkeit).\n\n"
            "Antworte AUSSCHLIESSLICH in diesem exakten Format (keine weiteren Texte):\n"
            "SCHRIFTART: <name>\n"
            "SCHRIFTGROESSE: <zahl>\n"
            "STIL: <beschreibung>\n\n"
            "Hier sind die Berichte:\n\n"
            f"{vorlagen_text}"
        )

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}]
            )
            antwort = message.content[0].text.strip()
        except Exception as e:
            raise Exception(f"Fehler bei der Stil-Analyse: {str(e)}")

        # Parsen
        result = {'schriftart': 'Arial', 'schriftgroesse': 11, 'beschreibung': antwort}
        allowed_fonts = ['Arial', 'Times New Roman', 'Courier New']
        for line in antwort.splitlines():
            line = line.strip()
            if line.upper().startswith('SCHRIFTART:'):
                val = line.split(':', 1)[1].strip()
                if val in allowed_fonts:
                    result['schriftart'] = val
            elif line.upper().startswith('SCHRIFTGROESSE:') or line.upper().startswith('SCHRIFTGRÖẞE:'):
                try:
                    result['schriftgroesse'] = max(8, min(24, int(''.join(filter(str.isdigit, line.split(':', 1)[1])))))
                except ValueError:
                    pass
            elif line.upper().startswith('STIL:'):
                result['beschreibung'] = line.split(':', 1)[1].strip()
        return result

    def bericht_verbessern(self, original_bericht: str, verbesserungshinweise: str = "") -> str:
        """
        Verbessert einen bestehenden Einsatzbericht
        
        Args:
            original_bericht: Der ursprüngliche Bericht
            verbesserungshinweise: Spezifische Hinweise zur Verbesserung
        
        Returns:
            Der verbesserte Einsatzbericht
        """
        stil = self._stil_kontext()
        stil_block = f"{stil}\n\n" if stil else ""
        hinweis = f'Bitte beachte folgende Verbesserungshinweise: {verbesserungshinweise}' if verbesserungshinweise else 'Verbessere Grammatik, Struktur und Professionalität.'
        prompt = (
            f"{stil_block}"
            f"Verbessere den folgenden Einsatzbericht:\n\n{original_bericht}\n\n"
            f"{hinweis}\n"
            f"{'Halte dabei denselben Schreibstil, Ton und dieselbe Gliederung wie in den Stilvorlagen.' if stil else ''}\n\n"
            f"Gib den vollständigen verbesserten Bericht zurück."
        )

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=2048,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return message.content[0].text
        
        except Exception as e:
            raise Exception(f"Fehler beim Verbessern des Einsatzberichts: {str(e)}")
    
    def bericht_zusammenfassen(self, bericht: str) -> str:
        """
        Erstellt eine Zusammenfassung eines Einsatzberichts
        
        Args:
            bericht: Der vollständige Einsatzbericht
        
        Returns:
            Eine kurze Zusammenfassung
        """
        prompt = f"""Erstelle eine kurze Zusammenfassung (max. 3-4 Sätze) des folgenden Einsatzberichts:

{bericht}"""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=256,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return message.content[0].text
        
        except Exception as e:
            raise Exception(f"Fehler beim Zusammenfassen des Einsatzberichts: {str(e)}")

    def reflexion_ausformulieren(self, stichwoerter: str) -> str:
        """
        Formuliert aus kurzen Stichwörtern eine vollständige Einsatzreflexion.

        Args:
            stichwoerter: Kurze Stichpunkte / Stichwörter zur Reflexion

        Returns:
            Ausformulierter Reflexionstext (3-6 Sätze, professionell)
        """
        prompt = (
            "Du bist ein erfahrener Rettungsdienstmitarbeiter und schreibst eine Einsatzreflexion.\n\n"
            "Formuliere aus den folgenden Stichwörtern eine professionelle, ausformulierte "
            "Einsatzreflexion in 3–6 Sätzen. Schreibe in der Ich-Perspektive oder Wir-Perspektive. "
            "KEIN Markdown, keine Aufzählungszeichen, kein Fettdruck.\n\n"
            f"Stichwörter: {stichwoerter}"
        )
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text.strip()
        except Exception as e:
            raise Exception(f"Fehler beim Ausformulieren der Reflexion: {str(e)}")

    def vitalwerte_generieren(self, kontext: str) -> dict:
        """
        Generiert plausible Vitalwerte basierend auf dem gegebenen Einsatzkontext.

        Returns:
            dict mit Schlüsseln: rr, hf, spo2, spco, af, bz, temp, gcs, etco2
        """
        import json, re as _re
        prompt = (
            "Du bist ein erfahrener Notfallsanitäter. "
            "Generiere REALISTISCH und LEITLINIENGERECHT passende Vitalwerte für folgenden Einsatzkontext:\n\n"
            f"{kontext}\n\n"
            "Antworte AUSSCHLIESSLICH mit einem gültigen JSON-Objekt, ohne Markdown, ohne weiteren Text:\n"
            '{\n'
            '  "rr": "sys/dia z.B. 130/85",\n'
            '  "hf": "z.B. 92",\n'
            '  "spo2": "z.B. 94",\n'
            '  "spco": "z.B. 0",\n'
            '  "af": "z.B. 18",\n'
            '  "bz": "z.B. 5.8",\n'
            '  "temp": "z.B. 36.8",\n'
            '  "gcs": "z.B. A4 V5 M6 = 15",\n'
            '  "etco2": "z.B. 38 oder leer"\n'
            '}'
        )
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )
            text = message.content[0].text.strip()
            m = _re.search(r'\{.*\}', text, _re.DOTALL)
            if m:
                return json.loads(m.group(0))
            return json.loads(text)
        except Exception as e:
            raise Exception(f"Fehler beim Generieren der Vitalwerte: {str(e)}")

    def schemata_generieren(self, kontext: str) -> dict:
        """
        Generiert plausible xABCDE-, OPQRST- und SAMPLER-Schemata basierend auf dem Kontext.

        Returns:
            dict mit Schlüsseln 'xABCDE', 'OPQRST', 'SAMPLER', je ein dict mit Buchstaben-Schlüsseln
        """
        import json, re as _re
        prompt = (
            "Du bist ein erfahrener Notfallsanitäter. "
            "Fülle die klinischen Schemata REALISTISCH und LEITLINIENGERECHT für folgenden Einsatzkontext:\n\n"
            f"{kontext}\n\n"
            "Regeln:\n"
            "- xABCDE NUR qualitative Befunde, KEINE Messwerte (kein RR, HF, SpO2, BZ, GCS-Zahl, Temp)\n"
            "- X-Feld nur wenn relevante Blutung/Tourniquet vorhanden, sonst leer lassen\n"
            "- Felder kurz halten (max. 12 Wörter je Buchstabe)\n"
            "- KEIN Markdown, keine Aufzählungszeichen\n\n"
            "Antworte AUSSCHLIESSLICH mit einem gültigen JSON-Objekt:\n"
            '{\n'
            '  "xABCDE": {"x":"","a":"","b":"","c":"","d":"","e":""},\n'
            '  "OPQRST": {"o":"","p":"","q":"","r":"","s":"","t":""},\n'
            '  "SAMPLER": {"s":"","a":"","m":"","p":"","l":"","e":"","r":""}\n'
            '}'
        )
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}]
            )
            text = message.content[0].text.strip()
            m = _re.search(r'\{.*\}', text, _re.DOTALL)
            if m:
                return json.loads(m.group(0))
            return json.loads(text)
        except Exception as e:
            raise Exception(f"Fehler beim Generieren der Schemata: {str(e)}")

    def scenario_erfinden(self, krankheitsbild: str) -> dict:
        """
        Erfindet ein realistisches Rettungsdienst-Einsatzszenario und prüft
        die medizinische Korrektheit gegen aktuelle EMS-Leitlinien.

        Args:
            krankheitsbild: Bezeichnung des Krankheitsbilds / Einsatzszenarios

        Returns:
            dict mit allen Einsatz-Feldern (stichwort, abcde, opqrst, sampler, medikamente etc.)
        """
        prompt = (
            f"Du bist ein erfahrener Rettungsassistent/Notfallsanitäter. "
            f"Erfinde ein REALISTISCHES und MEDIZINISCH KORREKTES Rettungsdienst-Einsatzszenario "
            f"für folgendes Krankheitsbild:\n\n{krankheitsbild}\n\n"
            f"ANFORDERUNGEN:\n"
            f"- Alle Vitalwerte, Laborwerte und Befunde müssen für dieses Krankheitsbild typisch und realistisch sein\n"
            f"- Medikamente und Dosierungen müssen den aktuellen Leitlinien entsprechen "
            f"(ERC-Leitlinien 2021, ACLS, DGAI-SOPs, Bundeseinheitlicher Curriculum Notfallsanitäter)\n"
            f"- NACA-Score, GCS und VAS müssen zur klinischen Situation passen\n"
            f"- Das EKG-Befund (falls relevant) muss zum Krankheitsbild passen\n"
            f"- Realistische Patientendemographie (Alter, Geschlecht, Vorerkrankungen)\n"
            f"- ABCDE/OPQRST/SAMPLER-Felder KURZ halten: max. 10\u201312 W\u00f6rter je Buchstabe (Stichworte, keine langen S\u00e4tze)\n"
            f"- ABCDE NUR qualitative Befunde (A/B/C/D/E): KEINE Zahlen wie RR, HF, SpO2, BZ, Temp, GCS – diese kommen ausschließlich in 'vitalwerte'\n"
            f"- X-Feld (Exsanguination): nur ausfüllen wenn relevante Blutung / Maßnahmen (Tourniquet etc.) vorhanden, sonst leer lassen\n\n"
            f"Antworte AUSSCHLIEßLICH mit einem gültigen JSON-Objekt, ohne Markdown, ohne weiteren Text:\n"
            f'{{\n'
            f'  "krankheitsbild": "{krankheitsbild}",\n'
            f'  "stichwort": "RTW X – Kategorie: Kurzbezeichnung",\n'
            f'  "datum": "TT.MM.JJJJ",\n'
            f'  "uhrzeit": "HH:MM",\n'
            f'  "rettungsmittel": "z.B. RTW, NEF",\n'
            f'  "medikamente": "Wirkstoff Dosis Route, ...",\n'
            f'  "abcde": {{\n'
            f'    "x": "Exsanguination / Maßnahme bei Blutung oder leer lassen",\n'
            f'    "a": "Atemweg qualitativ (frei/verlegt/gesichert) - KEINE Messwerte",\n'
            f'    "b": "Atemger\u00e4usch, Ventilationsqualit\u00e4t - KEIN SpO2/AF",\n'
            f'    "c": "Kreislaufbefund qualitativ, Rekapillarisierung - KEIN RR/HF",\n'
            f'    "d": "Bewusstsein, Neurologie, Pupillen - KEIN GCS/BZ",\n'
            f'    "e": "Haut, Bodycheck - KEINE Temperaturzahl"\n'
            f'  }},\n'
            f'  "opqrst": {{\n'
            f'    "o": "Onset",\n'
            f'    "p": "Provocation",\n'
            f'    "q": "Quality",\n'
            f'    "r": "Radiation",\n'
            f'    "s": "X/10",\n'
            f'    "t": "Time"\n'
            f'  }},\n'
            f'  "sampler": {{\n'
            f'    "s": "Symptome",\n'
            f'    "a": "Allergien",\n'
            f'    "m": "Dauermedikation",\n'
            f'    "p": "Vorerkrankungen",\n'
            f'    "l": "Letzte Mahlzeit",\n'
            f'    "e": "Ereignisanamnese",\n'
            f'    "r": "Risikofaktoren"\n'
            f'  }},\n'
            f'  "naca": "Ziffer – Begründung",\n'
            f'  "gcs": "AX VX MX = XX",\n'
            f'  "vas": "X/10",\n'
            f'  "ekg": "EKG-Befund oder nicht erhoben",\n'
            f'  "zusatz": "Patientenalter, Geschlecht, besondere Situation, Angehörige etc.",\n'            f'  "vitalwerte": {{\n'
            f'    "rr": "sys/dia z.B. 130/85",\n'
            f'    "hf": "z.B. 92",\n'
            f'    "spo2": "z.B. 94",\n'
            f'    "spco": "z.B. 0",\n'
            f'    "af": "z.B. 18",\n'
            f'    "bz": "z.B. 5.8",\n'
            f'    "temp": "z.B. 36.8",\n'
            f'    "gcs": "z.B. A4 V5 M6 = 15",\n'
            f'    "etco2": "z.B. 38 oder leer"\n'
            f'  }},\n'            f'  "verifikation": "Kurze Bestätigung der medizinischen Korrektheit inkl. Leitlinienreferenz"\n'
            f'}}'
        )
        import json, re
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )
            text = message.content[0].text.strip()
            # JSON aus Antwort extrahieren (auch wenn Markdown-Blöcke vorhanden)
            m = re.search(r'\{.*\}', text, re.DOTALL)
            if m:
                text = m.group()
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise Exception(f"Fehler beim Parsen der KI-Antwort: {str(e)}")
        except Exception as e:
            raise Exception(f"Fehler beim Erfinden des Szenarios: {str(e)}")

"""
PySide6 GUI für Einsatzbericht-Manager
"""
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QPushButton, QTextEdit, QLineEdit, QLabel,
                              QTableWidget, QTableWidgetItem, QMessageBox,
                              QDialog, QDialogButtonBox, QFormLayout, QTabWidget,
                              QFileDialog, QProgressDialog, QApplication, QSpinBox,
                              QComboBox, QGroupBox, QCheckBox, QScrollArea)
from PySide6.QtCore import Qt, QThread, Signal, QDate, QTime
from PySide6.QtWidgets import QDateEdit, QTimeEdit
from PySide6.QtGui import QFont, QIcon
import sys
import os


class ClaudeWorker(QThread):
    """Worker Thread für Claude API Aufrufe"""
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, claude_handler, einsatz_daten: dict):
        super().__init__()
        self.claude_handler = claude_handler
        self.einsatz_daten = einsatz_daten

    def run(self):
        try:
            result = self.claude_handler.einsatzbericht_erstellen(**self.einsatz_daten)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class StilAnalyseWorker(QThread):
    """Worker Thread für Claude Stil-Analyse"""
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, claude_handler):
        super().__init__()
        self.claude_handler = claude_handler

    def run(self):
        try:
            result = self.claude_handler.stil_analysieren()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class ImportDialog(QDialog):
    """Dialog zum Überprüfen und Bestätigen eines importierten Berichts"""
    def __init__(self, daten: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bericht importieren – Überprüfen")
        self.setMinimumSize(650, 450)

        layout = QVBoxLayout()
        form = QFormLayout()

        self.titel_input = QLineEdit(daten.get('titel', ''))
        self.thema_input = QLineEdit(daten.get('thema', ''))
        form.addRow("Titel:", self.titel_input)
        form.addRow("Thema:", self.thema_input)
        layout.addLayout(form)

        layout.addWidget(QLabel("Inhalt:"))
        self.inhalt_view = QTextEdit(daten.get('inhalt', ''))
        layout.addWidget(self.inhalt_view)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def get_data(self):
        return {
            'titel': self.titel_input.text(),
            'thema': self.thema_input.text(),
            'inhalt': self.inhalt_view.toPlainText()
        }


class NeuerBerichtDialog(QDialog):
    """Dialog zum Erstellen eines neuen Berichts"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Neuer Einsatzbericht")
        self.setMinimumWidth(500)
        
        layout = QFormLayout()
        
        self.titel_input = QLineEdit()
        self.thema_input = QLineEdit()
        self.zusatz_input = QTextEdit()
        self.zusatz_input.setMaximumHeight(100)
        
        layout.addRow("Titel:", self.titel_input)
        layout.addRow("Thema:", self.thema_input)
        layout.addRow("Zusätzliche Infos:", self.zusatz_input)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addWidget(buttons)
        
        self.setLayout(main_layout)
    
    def get_data(self):
        return {
            'titel': self.titel_input.text(),
            'thema': self.thema_input.text(),
            'zusatz': self.zusatz_input.toPlainText()
        }


class BerichtBearbeitenDialog(QDialog):
    """Dialog zum Bearbeiten eines Berichts"""
    def __init__(self, bericht_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Einsatzbericht bearbeiten")
        self.setMinimumSize(700, 500)
        
        layout = QVBoxLayout()
        
        # Titel
        titel_layout = QHBoxLayout()
        titel_layout.addWidget(QLabel("Titel:"))
        self.titel_input = QLineEdit(bericht_data['titel'])
        titel_layout.addWidget(self.titel_input)
        layout.addLayout(titel_layout)
        
        # Thema
        thema_layout = QHBoxLayout()
        thema_layout.addWidget(QLabel("Thema:"))
        self.thema_input = QLineEdit(bericht_data['thema'])
        thema_layout.addWidget(self.thema_input)
        layout.addLayout(thema_layout)
        
        # Inhalt
        layout.addWidget(QLabel("Inhalt:"))
        self.inhalt_input = QTextEdit(bericht_data['inhalt'])
        layout.addWidget(self.inhalt_input)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def get_data(self):
        return {
            'titel': self.titel_input.text(),
            'thema': self.thema_input.text(),
            'inhalt': self.inhalt_input.toPlainText()
        }


# ──────────────────────────────────────────────────────────────────────────────
class SchemaWidget(QGroupBox):
    """Einklappbares Schema-Widget mit einzelnen Unterfeldern."""
    def __init__(self, schema_name: str, sub_fields: list, parent=None):
        super().__init__(schema_name, parent)
        self.setCheckable(True)
        self.setChecked(False)
        self._defs = sub_fields  # [(key, label, placeholder), ...]
        form = QFormLayout()
        form.setContentsMargins(6, 4, 6, 6)
        self.setLayout(form)
        self.inputs = {}
        for key, label, ph in sub_fields:
            inp = QLineEdit()
            inp.setPlaceholderText(ph)
            form.addRow(label + ":", inp)
            self.inputs[key] = inp

    def schema_text(self):
        if not self.isChecked():
            return None
        parts = []
        for key, label, _ in self._defs:
            val = self.inputs[key].text().strip()
            parts.append(f"{key.upper()}: {val}" if val else f"{key.upper()}: —")
        return self.title() + "\n" + "\n".join(parts)

    def set_values(self, data: dict):
        for key, val in data.items():
            if key in self.inputs and val:
                self.inputs[key].setText(str(val))
        self.setChecked(True)

    def clear_values(self):
        for inp in self.inputs.values():
            inp.clear()
        self.setChecked(False)


# ──────────────────────────────────────────────────────────────────────────────
class ErfindenWorker(QThread):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, claude_handler, krankheitsbild: str):
        super().__init__()
        self.claude_handler = claude_handler
        self.krankheitsbild = krankheitsbild

    def run(self):
        try:
            self.finished.emit(self.claude_handler.scenario_erfinden(self.krankheitsbild))
        except Exception as e:
            self.error.emit(str(e))


KRANKHEITSBILDER = [
    "Reanimation – Asystolie",
    "Reanimation – Kammerflimmern (VF / pulslose VT)",
    "Reanimation – PEA (pulslose elektrische Aktivität)",
    "STEMI – Hinterwandinfarkt",
    "STEMI – Vorderwandinfarkt",
    "NSTEMI / Instabile Angina pectoris",
    "Schlaganfall – ischämisch",
    "Schlaganfall – hämorrhagisch / TIA",
    "Akutes Lungenödem / dekompensierte Herzinsuffizienz",
    "Hypertensiver Notfall (RR > 180/110 + Symptome)",
    "Hypoglykämie (BZ < 3.0 mmol/l)",
    "Hyperglykämie / Diabetische Ketoazidose",
    "Anaphylaxie Grad III–IV",
    "Asthmaanfall (schwer / lebensbedrohlich)",
    "COPD-Exazerbation mit akuter Ateminsuffizienz",
    "Krampfanfall / Status epilepticus",
    "Synkope / Bewusstlosigkeit (unklare Ursache)",
    "Polytrauma (Verkehrsunfall)",
    "Sturz / Schädel-Hirn-Trauma",
    "Sepsis / septischer Schock",
    "Intoxikation / Vergiftung (Alkohol / Medikamente / Drogen)",
    "Psychiatrischer Notfall / Suizidalität",
    "Verbrennungen Grad IIa–IIIb",
    "Hitzschlag / schwere Hyperthermie",
    "Eigene Eingabe...",
]


class BerichtErfindenDialog(QDialog):
    """Dialog zum vollautomatischen Erfinden + Prüfen eines Einsatzszenarios"""
    def __init__(self, claude_handler, parent=None):
        super().__init__(parent)
        self.claude_handler = claude_handler
        self._data = {}
        self.setWindowTitle("Einsatzszenario erfinden (KI)")
        self.setMinimumSize(660, 580)

        layout = QVBoxLayout()
        self.setLayout(layout)

        auswahl_group = QGroupBox("Krankheitsbild / Einsatzszenario")
        auswahl_form = QFormLayout()
        auswahl_group.setLayout(auswahl_form)
        self.kbild_combo = QComboBox()
        self.kbild_combo.addItems(KRANKHEITSBILDER)
        self.kbild_combo.currentTextChanged.connect(
            lambda t: self.kbild_custom.setVisible(t == "Eigene Eingabe...")
        )
        self.kbild_custom = QLineEdit()
        self.kbild_custom.setPlaceholderText("z.B. Akute Appendizitis mit Peritonitiszeichen")
        self.kbild_custom.setVisible(False)
        auswahl_form.addRow("Szenario:", self.kbild_combo)
        auswahl_form.addRow("Eigene Eingabe:", self.kbild_custom)
        layout.addWidget(auswahl_group)

        self.erfinden_btn = QPushButton("🎲 Einsatzszenario erfinden + medizinisch prüfen (KI)")
        self.erfinden_btn.clicked.connect(self._erfinden)
        layout.addWidget(self.erfinden_btn)

        layout.addWidget(QLabel("Erfundenes Szenario (Vorschau):"))
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setPlaceholderText(
            "Hier erscheint das von Claude erfundene und geprüfte Szenario.\n"
            "Claude prüft die Werte gegen aktuelle EMS-Leitlinien (ERC, ACLS, DGAI-SOPs)."
        )
        layout.addWidget(self.preview)

        self.verif_label = QLabel("")
        self.verif_label.setWordWrap(True)
        self.verif_label.setStyleSheet("color: #4caf50; font-style: italic; padding: 4px;")
        layout.addWidget(self.verif_label)

        btn_row = QHBoxLayout()
        self.uebernehmen_btn = QPushButton("✅ Ins Formular übernehmen")
        self.uebernehmen_btn.setEnabled(False)
        self.uebernehmen_btn.clicked.connect(self.accept)
        abbrechen_btn = QPushButton("Abbrechen")
        abbrechen_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.uebernehmen_btn)
        btn_row.addWidget(abbrechen_btn)
        layout.addLayout(btn_row)

    def _get_krankheitsbild(self):
        txt = self.kbild_combo.currentText()
        if txt == "Eigene Eingabe...":
            return self.kbild_custom.text().strip() or "Unbekannter Notfall"
        return txt

    def _erfinden(self):
        self.erfinden_btn.setEnabled(False)
        self.uebernehmen_btn.setEnabled(False)
        self.preview.setPlainText("⏳ Claude erfindet und prüft das Szenario gegen EMS-Leitlinien...")
        self.verif_label.setText("")
        self._worker = ErfindenWorker(self.claude_handler, self._get_krankheitsbild())
        self._worker.finished.connect(self._on_fertig)
        self._worker.error.connect(self._on_fehler)
        self._worker.start()

    def _on_fertig(self, data: dict):
        self._data = data
        self.erfinden_btn.setEnabled(True)
        self.uebernehmen_btn.setEnabled(True)
        ab = data.get('abcde', {})
        op = data.get('opqrst', {})
        sa = data.get('sampler', {})
        zeilen = [
            f"📋 SZENARIO: {data.get('krankheitsbild', '')}",
            f"🚨 Stichwort:      {data.get('stichwort', '')}",
            f"📅 Datum / Zeit:   {data.get('datum', '')}  {data.get('uhrzeit', '')} Uhr",
            f"🚑 Rettungsmittel: {data.get('rettungsmittel', '')}",
            f"💊 Medikamente:    {data.get('medikamente', '')}",
            "",
            "─ ABCDE ─",
            f"  A: {ab.get('a','')}",
            f"  B: {ab.get('b','')}",
            f"  C: {ab.get('c','')}",
            f"  D: {ab.get('d','')}",
            f"  E: {ab.get('e','')}",
            "",
            "─ OPQRST ─",
            f"  O: {op.get('o','')}",
            f"  P: {op.get('p','')}",
            f"  Q: {op.get('q','')}",
            f"  R: {op.get('r','')}",
            f"  S: {op.get('s','')}",
            f"  T: {op.get('t','')}",
            "",
            "─ SAMPLER ─",
            f"  S: {sa.get('s','')}",
            f"  A: {sa.get('a','')}",
            f"  M: {sa.get('m','')}",
            f"  P: {sa.get('p','')}",
            f"  L: {sa.get('l','')}",
            f"  E: {sa.get('e','')}",
            f"  R: {sa.get('r','')}",
            "",
            f"NACA:   {data.get('naca','')}",
            f"GCS:    {data.get('gcs','')}",
            f"VAS:    {data.get('vas','')}",
            f"EKG:    {data.get('ekg','')}",
            "",
            f"Zusatz: {data.get('zusatz','')}",
        ]
        self.preview.setPlainText("\n".join(zeilen))
        verif = data.get('verifikation', '')
        if verif:
            self.verif_label.setText(f"✅ Medizinische Prüfung: {verif}")

    def _on_fehler(self, error: str):
        self.erfinden_btn.setEnabled(True)
        self.preview.setPlainText(f"❌ Fehler: {error}")

    def get_invented_data(self) -> dict:
        return self._data


class MainWindow(QMainWindow):
    def __init__(self, db_handler, claude_handler, report_generator, beispiele_pfad: str = "data/beispiele"):
        super().__init__()

        self.db = db_handler
        self.claude = claude_handler
        self.report_gen = report_generator
        self.beispiele_pfad = beispiele_pfad

        self.setWindowTitle("Einsatzbericht Manager")
        self.setMinimumSize(1000, 700)

        self.setup_ui()
        self.load_berichte()
    
    def setup_ui(self):
        """Erstellt die Benutzeroberfläche"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Titel
        title_label = QLabel("Einsatzbericht Manager")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # Export-Schrifteinstellungen (gilt für alle Exporte)
        font_bar = QHBoxLayout()
        font_bar.addWidget(QLabel("Schriftart (Export):"))
        self.font_family_combo = QComboBox()
        self.font_family_combo.addItems(["Arial", "Times New Roman", "Courier New"])
        self.font_family_combo.setFixedWidth(180)
        font_bar.addWidget(self.font_family_combo)
        font_bar.addWidget(QLabel("Schriftgröße:"))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setValue(11)
        self.font_size_spin.setFixedWidth(60)
        font_bar.addWidget(self.font_size_spin)
        font_bar.addStretch()
        main_layout.addLayout(font_bar)

        # Tab Widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Tab 1: Berichte Übersicht
        self.setup_overview_tab()
        
        # Tab 2: Neuer Bericht
        self.setup_new_report_tab()
        
        # Tab 3: Bericht Ansehen/Bearbeiten
        self.setup_view_edit_tab()

        # Tab 4: Stilvorlagen (Beispiele)
        self.setup_beispiele_tab()
    
    def setup_overview_tab(self):
        """Erstellt den Übersichts-Tab"""
        overview_widget = QWidget()
        layout = QVBoxLayout()
        overview_widget.setLayout(layout)
        
        # Suche
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Suche:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Titel, Thema oder Inhalt durchsuchen...")
        self.search_input.textChanged.connect(self.search_berichte)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        
        # Tabelle
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Titel", "Thema", "Erstellt am", "Aktualisiert am"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.doubleClicked.connect(self.open_bericht)
        layout.addWidget(self.table)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Aktualisieren")
        refresh_btn.clicked.connect(self.load_berichte)
        button_layout.addWidget(refresh_btn)
        
        open_btn = QPushButton("Öffnen")
        open_btn.clicked.connect(self.open_bericht)
        button_layout.addWidget(open_btn)
        
        delete_btn = QPushButton("Löschen")
        delete_btn.clicked.connect(self.delete_bericht)
        button_layout.addWidget(delete_btn)
        
        export_pdf_btn = QPushButton("Als PDF exportieren")
        export_pdf_btn.clicked.connect(lambda: self.export_bericht('pdf'))
        button_layout.addWidget(export_pdf_btn)

        export_word_btn = QPushButton("Als Word exportieren")
        export_word_btn.clicked.connect(lambda: self.export_bericht('word'))
        button_layout.addWidget(export_word_btn)

        export_odf_btn = QPushButton("Als ODF exportieren")
        export_odf_btn.clicked.connect(lambda: self.export_bericht('odf'))
        button_layout.addWidget(export_odf_btn)

        export_pages_btn = QPushButton("Als Pages exportieren")
        export_pages_btn.clicked.connect(lambda: self.export_bericht('pages'))
        button_layout.addWidget(export_pages_btn)

        import_btn = QPushButton("Bericht importieren")
        import_btn.clicked.connect(self.import_bericht)
        button_layout.addWidget(import_btn)

        layout.addLayout(button_layout)

        self.tabs.addTab(overview_widget, "Übersicht")
    
    def setup_new_report_tab(self):
        """Erstellt den Tab für neue Berichte"""
        new_report_widget = QWidget()
        outer_layout = QVBoxLayout()
        new_report_widget.setLayout(outer_layout)

        # Scrollbarer Formularbereich
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(420)
        form_widget = QWidget()
        layout = QVBoxLayout()
        form_widget.setLayout(layout)
        scroll.setWidget(form_widget)
        outer_layout.addWidget(scroll)

        # Info
        info_label = QLabel("Erstellen Sie einen neuen Einsatzbericht mit Hilfe von Claude AI")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # ── Einsatz-Grunddaten ──────────────────────────────────────────
        grunddaten_group = QGroupBox("Einsatz-Grunddaten")
        grunddaten_form = QFormLayout()
        grunddaten_group.setLayout(grunddaten_form)

        self.new_titel = QLineEdit()
        self.new_titel.setPlaceholderText("z.B. Einsatzbericht Nr. 6")

        self.new_stichwort = QLineEdit()
        self.new_stichwort.setPlaceholderText("z.B. RTW 2 – Internistisch 1: Verdacht Schlaganfall")

        datum_uhrzeit_layout = QHBoxLayout()
        self.new_datum = QDateEdit(QDate.currentDate())
        self.new_datum.setDisplayFormat("dd.MM.yyyy")
        self.new_datum.setCalendarPopup(True)
        self.new_uhrzeit = QTimeEdit(QTime.currentTime())
        self.new_uhrzeit.setDisplayFormat("HH:mm")
        datum_uhrzeit_layout.addWidget(self.new_datum)
        datum_uhrzeit_layout.addWidget(QLabel("Uhr"))
        datum_uhrzeit_layout.addWidget(self.new_uhrzeit)
        datum_uhrzeit_layout.addStretch()
        datum_uhrzeit_widget = QWidget()
        datum_uhrzeit_widget.setLayout(datum_uhrzeit_layout)

        self.new_seitenzahl = QSpinBox()
        self.new_seitenzahl.setRange(1, 20)
        self.new_seitenzahl.setValue(2)

        grunddaten_form.addRow("Titel (intern):", self.new_titel)
        grunddaten_form.addRow("Alarmierungsstichwort:", self.new_stichwort)
        grunddaten_form.addRow("Datum / Alarmierungszeit:", datum_uhrzeit_widget)
        grunddaten_form.addRow("Seitenzahl (ca.):", self.new_seitenzahl)
        layout.addWidget(grunddaten_group)

        # ── Beteiligte Rettungsmittel ───────────────────────────────────
        rm_group = QGroupBox("Beteiligte Rettungsmittel")
        rm_form = QFormLayout()
        rm_group.setLayout(rm_form)
        self.new_rettungsmittel = QLineEdit()
        self.new_rettungsmittel.setPlaceholderText("z.B. RTW, NEF, RTW 3, FW Löschzug")
        rm_form.addRow("Rettungsmittel:", self.new_rettungsmittel)
        layout.addWidget(rm_group)

        # ── Medikamente ─────────────────────────────────────────────────
        med_group = QGroupBox("Verabreichte Medikamente")
        med_form = QFormLayout()
        med_group.setLayout(med_form)
        self.new_medikamente = QLineEdit()
        self.new_medikamente.setPlaceholderText("z.B. Adrenalin 1mg i.v., Amiodaron 300mg")
        med_form.addRow("Medikamente:", self.new_medikamente)
        layout.addWidget(med_group)

        # ── Schemata ────────────────────────────────────────────────────
        schemata_outer = QGroupBox("Schemata – Checkbox aktivieren und Befunde eintragen")
        schemata_vlayout = QVBoxLayout()
        schemata_outer.setLayout(schemata_vlayout)

        # Komplexe Schemata mit Sub-Feldern
        self.schema_widgets = {}  # name -> SchemaWidget
        komplex_defs = [
            ("ABCDE", [
                ("a", "A – Atemweg", "frei / verlegt / gesichert mit Larynxtubus / Intubation"),
                ("b", "B – Beatmung / SpO\u2082 / AF", "z.B. SpO\u2082 94%, AF 18/min, vesikuläres Atemgeräusch bds."),
                ("c", "C – Kreislauf / RR / HF", "z.B. RR 130/85 mmHg, HF 92/min, rhythmisch"),
                ("d", "D – Neurologie / GCS / BZ", "z.B. GCS 15 (4+5+6), BZ 5.8 mmol/l, Pupillen isocor"),
                ("e", "E – Bodycheck / Temperatur", "z.B. Temp 36.8 °C, kühl-schweißige Haut, keine äußerl. Verletzungen"),
            ]),
            ("OPQRST", [
                ("o", "O – Onset / Beginn", "z.B. plötzlich beim Frühstück"),
                ("p", "P – Provocation / Verstärkung", "z.B. verstärkt bei Belastung, gebessert in Ruhe"),
                ("q", "Q – Quality / Schmerzcharakter", "z.B. drückend, brennend, stechend, kolikartig"),
                ("r", "R – Radiation / Ausstrahlung", "z.B. in linken Arm, Kiefer, Schulterblatt"),
                ("s", "S – Severity / VAS 0–10", "z.B. 8/10"),
                ("t", "T – Time / Zeitverlauf", "z.B. seit 30 Minuten anhaltend, zunehmend"),
            ]),
            ("SAMPLER", [
                ("s", "S – Symptoms / Hauptbeschwerden", "z.B. Brustschmerz, Atemnot, Schweißausbruch"),
                ("a", "A – Allergies / Allergien", "z.B. keine bekannten Allergien / Penicillin"),
                ("m", "M – Medications / Medikamente", "z.B. ASS 100 mg, Bisoprolol 5 mg, Metformin"),
                ("p", "P – Past history / Vorerkrankungen", "z.B. KHK seit 2019, art. Hypertonie, DM Typ 2"),
                ("l", "L – Last meal / Letzte Mahlzeit", "z.B. vor 2 Stunden, Mittagessen"),
                ("e", "E – Events / Ereignisanamnese", "z.B. Schmerz begann plötzlich beim Aufstehen"),
                ("r", "R – Risk factors / Risikofaktoren", "z.B. Raucher 30 py, Übergewicht BMI 29"),
            ]),
        ]
        for name, sub in komplex_defs:
            w = SchemaWidget(name, sub)
            if name == "ABCDE":
                w.setChecked(True)
            schemata_vlayout.addWidget(w)
            self.schema_widgets[name] = w

        # Einfache Schemata (eine Zeile je Schema)
        self.schema_simple = {}  # name -> (QCheckBox, QLineEdit)
        simple_form = QFormLayout()
        simple_defs = [
            ("NACA-Score", "z.B. IV – lebensbedrohliche Erkrankung, stationäre Behandlung erforderlich"),
            ("GCS",        "z.B. A4 V5 M6 = 15  (orientiert, befolgt Aufforderungen)"),
            ("VAS",        "Schmerzstärke 0–10"),
            ("12-Kanal-EKG", "z.B. SR HF 72/min, ST-Hebung II/III/aVF, Pardée-Q III"),
        ]
        for name, ph in simple_defs:
            row_w = QWidget()
            row_l = QHBoxLayout()
            row_l.setContentsMargins(0, 0, 0, 0)
            row_w.setLayout(row_l)
            cb = QCheckBox()
            inp = QLineEdit()
            inp.setPlaceholderText(ph)
            inp.setEnabled(False)
            cb.toggled.connect(inp.setEnabled)
            row_l.addWidget(cb)
            row_l.addWidget(inp)
            self.schema_simple[name] = (cb, inp)
            simple_form.addRow(name + ":", row_w)
        simple_w = QWidget()
        simple_w.setLayout(simple_form)
        schemata_vlayout.addWidget(simple_w)
        layout.addWidget(schemata_outer)

        # ── Zusätzlicher Kontext ────────────────────────────────────────
        kontext_group = QGroupBox("Zusätzlicher Kontext / eigene Angaben")
        kontext_form = QFormLayout()
        kontext_group.setLayout(kontext_form)
        self.new_zusatz = QTextEdit()
        self.new_zusatz.setMaximumHeight(80)
        self.new_zusatz.setPlaceholderText(
            "Weitere Informationen, z.B. Patientendaten, Vorerkrankungen, besondere Umstände..."
        )
        kontext_form.addRow("Kontext:", self.new_zusatz)
        layout.addWidget(kontext_group)

        # ── Vorschau + Buttons ──────────────────────────────────────────
        outer_layout.addWidget(QLabel("Vorschau (generierter Bericht):"))
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        outer_layout.addWidget(self.preview_text)

        button_layout = QHBoxLayout()
        generate_btn = QPushButton("🤖 Mit Claude AI generieren")
        generate_btn.clicked.connect(self.generate_report)
        button_layout.addWidget(generate_btn)
        erfinden_btn_main = QPushButton("🎲 Bericht erfinden (KI)")
        erfinden_btn_main.setToolTip("Claude erfindet ein medizinisch korrektes Szenario und füllt alle Felder aus.")
        erfinden_btn_main.clicked.connect(self.erfinden_bericht)
        button_layout.addWidget(erfinden_btn_main)
        save_btn = QPushButton("Speichern")
        save_btn.clicked.connect(self.save_new_report)
        button_layout.addWidget(save_btn)
        clear_btn = QPushButton("Zurücksetzen")
        clear_btn.clicked.connect(self.clear_new_report)
        button_layout.addWidget(clear_btn)
        outer_layout.addLayout(button_layout)

        self.tabs.addTab(new_report_widget, "Neuer Bericht")
    
    def setup_view_edit_tab(self):
        """Erstellt den Tab zum Ansehen/Bearbeiten"""
        view_edit_widget = QWidget()
        layout = QVBoxLayout()
        view_edit_widget.setLayout(layout)
        
        # Info
        info_label = QLabel("Wählen Sie einen Bericht aus der Übersicht, um ihn hier zu bearbeiten")
        layout.addWidget(info_label)
        
        # Formular
        form_layout = QFormLayout()
        
        self.edit_id = QLabel("-")
        self.edit_titel = QLineEdit()
        self.edit_thema = QLineEdit()
        self.edit_seitenzahl = QSpinBox()
        self.edit_seitenzahl.setRange(1, 20)
        self.edit_seitenzahl.setValue(2)
        self.edit_kontext = QTextEdit()
        self.edit_kontext.setMaximumHeight(70)
        self.edit_kontext.setPlaceholderText("Kontext für KI-Neugenerierung (optional)...")

        form_layout.addRow("Bericht-ID:", self.edit_id)
        form_layout.addRow("Titel:", self.edit_titel)
        form_layout.addRow("Thema:", self.edit_thema)
        form_layout.addRow("Seitenzahl (KI):", self.edit_seitenzahl)
        form_layout.addRow("Kontext (KI):", self.edit_kontext)
        
        layout.addLayout(form_layout)
        
        # Inhalt
        layout.addWidget(QLabel("Inhalt:"))
        self.edit_inhalt = QTextEdit()
        layout.addWidget(self.edit_inhalt)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        save_edit_btn = QPushButton("Änderungen speichern")
        save_edit_btn.clicked.connect(self.save_edit)
        button_layout.addWidget(save_edit_btn)

        regen_btn = QPushButton("Mit KI neu generieren")
        regen_btn.clicked.connect(self.regenerate_edit_report)
        button_layout.addWidget(regen_btn)

        export_pdf_btn = QPushButton("Als PDF exportieren")
        export_pdf_btn.clicked.connect(lambda: self.export_current_bericht('pdf'))
        button_layout.addWidget(export_pdf_btn)

        export_word_btn = QPushButton("Als Word exportieren")
        export_word_btn.clicked.connect(lambda: self.export_current_bericht('word'))
        button_layout.addWidget(export_word_btn)

        export_odf_btn = QPushButton("Als ODF exportieren")
        export_odf_btn.clicked.connect(lambda: self.export_current_bericht('odf'))
        button_layout.addWidget(export_odf_btn)

        export_pages_btn = QPushButton("Als Pages exportieren")
        export_pages_btn.clicked.connect(lambda: self.export_current_bericht('pages'))
        button_layout.addWidget(export_pages_btn)

        layout.addLayout(button_layout)

        self.tabs.addTab(view_edit_widget, "Ansehen/Bearbeiten")

    def setup_beispiele_tab(self):
        """Erstellt den Tab für Stilvorlagen (Beispielberichte)"""
        import os
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)

        info = QLabel(
            f"Stilvorlagen für die KI – Pfad: {self.beispiele_pfad}\n"
            "Alle .txt / .docx / .odt Dateien hier werden als Schreibstil-Vorlage an Claude übergeben."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self.beispiele_list = QTableWidget()
        self.beispiele_list.setColumnCount(2)
        self.beispiele_list.setHorizontalHeaderLabels(["Dateiname", "Pfad"])
        self.beispiele_list.horizontalHeader().setStretchLastSection(True)
        self.beispiele_list.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.beispiele_list)

        btn_layout = QHBoxLayout()

        upload_btn = QPushButton("Beispiel hochladen")
        upload_btn.clicked.connect(self.beispiel_hochladen)
        btn_layout.addWidget(upload_btn)

        delete_btn = QPushButton("Ausgewähltes löschen")
        delete_btn.clicked.connect(self.beispiel_loeschen)
        btn_layout.addWidget(delete_btn)

        reload_btn = QPushButton("Liste aktualisieren")
        reload_btn.clicked.connect(self.load_beispiele_list)
        btn_layout.addWidget(reload_btn)

        analyse_btn = QPushButton("🔍 Stil analysieren (KI)")
        analyse_btn.setToolTip(
            "Claude liest alle Stilvorlagen und empfiehlt Schriftart, "
            "Schriftgröße und beschreibt den Schreibstil. "
            "Die empfohlene Schriftart und -größe werden automatisch übernommen."
        )
        analyse_btn.clicked.connect(self.stil_analysieren)
        btn_layout.addWidget(analyse_btn)

        layout.addLayout(btn_layout)

        # Analyse-Ergebnis Anzeige
        self.stil_ergebnis = QTextEdit()
        self.stil_ergebnis.setReadOnly(True)
        self.stil_ergebnis.setMaximumHeight(100)
        self.stil_ergebnis.setPlaceholderText(
            "Hier erscheint das Ergebnis der KI-Stil-Analyse..."
        )
        layout.addWidget(self.stil_ergebnis)

        self.tabs.addTab(widget, "Stilvorlagen")
        self.load_beispiele_list()

    def load_beispiele_list(self):
        """Lädt die Liste der vorhandenen Beispieldateien"""
        import os
        self.beispiele_list.setRowCount(0)
        if not os.path.isdir(self.beispiele_pfad):
            return
        for fname in sorted(os.listdir(self.beispiele_pfad)):
            if fname.lower().endswith(('.txt', '.docx', '.odt', '.pdf', '.pages')):
                row = self.beispiele_list.rowCount()
                self.beispiele_list.insertRow(row)
                self.beispiele_list.setItem(row, 0, QTableWidgetItem(fname))
                self.beispiele_list.setItem(
                    row, 1, QTableWidgetItem(os.path.join(self.beispiele_pfad, fname))
                )

    def beispiel_hochladen(self):
        """Kopiert eine Datei in den Beispiele-Ordner und lädt die KI-Vorlagen neu"""
        import os
        import shutil
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Stilvorlage auswählen", "",
            "Unterstützte Formate (*.txt *.docx *.odt *.pdf *.pages);;"
            "Text (*.txt);;Word (*.docx);;ODF (*.odt);;PDF (*.pdf);;Apple Pages (*.pages)"
        )
        if not filepath:
            return
        fname = os.path.basename(filepath)
        os.makedirs(self.beispiele_pfad, exist_ok=True)
        ziel = os.path.join(self.beispiele_pfad, fname)
        try:
            src_abs = os.path.abspath(filepath)
            dst_abs = os.path.abspath(ziel)
            if src_abs == dst_abs:
                QMessageBox.information(self, "Hinweis", f"\"{fname}\" ist bereits in den Stilvorlagen.")
                return
            shutil.copy2(filepath, ziel)
            self.load_beispiele_list()
            # KI-Handler neu laden, damit neue Vorlage sofort wirkt
            if self.claude:
                self.claude.beispiele = self.claude._load_beispiele(self.beispiele_pfad)
            QMessageBox.information(self, "Erfolg", f"Stilvorlage \"{fname}\" wurde hinzugefügt.")
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Hochladen:\n{str(e)}")

    def beispiel_loeschen(self):
        """Löscht die ausgewählte Stilvorlage"""
        import os
        row = self.beispiele_list.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warnung", "Bitte eine Datei auswählen.")
            return
        pfad = self.beispiele_list.item(row, 1).text()
        fname = self.beispiele_list.item(row, 0).text()
        reply = QMessageBox.question(
            self, "Bestätigung",
            f'Stilvorlage "{fname}" wirklich löschen?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                os.remove(pfad)
                self.load_beispiele_list()
                if self.claude:
                    self.claude.beispiele = self.claude._load_beispiele(self.beispiele_pfad)
                QMessageBox.information(self, "Erfolg", f'"{fname}" wurde gelöscht.')
            except Exception as e:
                QMessageBox.critical(self, "Fehler", f"Fehler beim Löschen:\n{str(e)}")

    def stil_analysieren(self):
        """Schickt die Stilvorlagen an Claude und übernimmt Schriftart + -größe."""
        if not self.claude:
            QMessageBox.warning(self, "Warnung", "Claude API nicht verfügbar.")
            return
        if not self.claude.beispiele:
            QMessageBox.warning(self, "Warnung", "Keine Stilvorlagen geladen. Bitte zuerst Beispiele hochladen.")
            return

        progress = QProgressDialog("Claude analysiert die Stilvorlagen...", None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.show()

        self.stil_worker = StilAnalyseWorker(self.claude)
        self.stil_worker.finished.connect(lambda r: self._on_stil_analysiert(r, progress))
        self.stil_worker.error.connect(lambda e: self._on_stil_fehler(e, progress))
        self.stil_worker.start()

    def _on_stil_analysiert(self, result: dict, progress):
        progress.close()
        schriftart = result.get('schriftart', 'Arial')
        groesse = result.get('schriftgroesse', 11)
        beschreibung = result.get('beschreibung', '')

        # Schriftart übernehmen
        idx = self.font_family_combo.findText(schriftart)
        if idx >= 0:
            self.font_family_combo.setCurrentIndex(idx)

        # Schriftgröße übernehmen
        self.font_size_spin.setValue(groesse)

        self.stil_ergebnis.setPlainText(
            f"Empfohlene Schriftart: {schriftart}\n"
            f"Empfohlene Schriftgröße: {groesse} pt\n\n"
            f"Stil: {beschreibung}"
        )

    def _on_stil_fehler(self, error: str, progress):
        progress.close()
        QMessageBox.critical(self, "Fehler", f"Fehler bei der Stil-Analyse:\n{error}")

    def load_berichte(self):
        """Lädt alle Berichte in die Tabelle"""
        self.table.setRowCount(0)
        berichte = self.db.alle_berichte_abrufen()
        
        for bericht in berichte:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(str(bericht['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(bericht['titel']))
            self.table.setItem(row, 2, QTableWidgetItem(bericht['thema']))
            self.table.setItem(row, 3, QTableWidgetItem(bericht['erstellt_am']))
            self.table.setItem(row, 4, QTableWidgetItem(bericht['aktualisiert_am']))
    
    def search_berichte(self):
        """Sucht Berichte basierend auf der Sucheingabe"""
        search_term = self.search_input.text()
        
        if not search_term:
            self.load_berichte()
            return
        
        self.table.setRowCount(0)
        berichte = self.db.berichte_suchen(search_term)
        
        for bericht in berichte:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(str(bericht['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(bericht['titel']))
            self.table.setItem(row, 2, QTableWidgetItem(bericht['thema']))
            self.table.setItem(row, 3, QTableWidgetItem(bericht['erstellt_am']))
            self.table.setItem(row, 4, QTableWidgetItem(bericht['aktualisiert_am']))
    
    def open_bericht(self):
        """Öffnet den ausgewählten Bericht zum Bearbeiten"""
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Warnung", "Bitte wählen Sie einen Bericht aus.")
            return
        
        row = self.table.currentRow()
        bericht_id = int(self.table.item(row, 0).text())
        
        bericht = self.db.bericht_abrufen(bericht_id)
        if bericht:
            self.edit_id.setText(str(bericht['id']))
            self.edit_titel.setText(bericht['titel'])
            self.edit_thema.setText(bericht['thema'])
            self.edit_inhalt.setPlainText(bericht['inhalt'])
            
            self.tabs.setCurrentIndex(2)  # Wechsle zu Tab "Ansehen/Bearbeiten"
    
    def delete_bericht(self):
        """Löscht den ausgewählten Bericht"""
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Warnung", "Bitte wählen Sie einen Bericht aus.")
            return
        
        row = self.table.currentRow()
        bericht_id = int(self.table.item(row, 0).text())
        
        reply = QMessageBox.question(
            self, 'Bestätigung',
            'Möchten Sie diesen Bericht wirklich löschen?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.db.bericht_loeschen(bericht_id)
            self.load_berichte()
            QMessageBox.information(self, "Erfolg", "Bericht wurde gelöscht.")
    
    def generate_report(self):
        """Generiert einen Bericht mit Claude AI"""
        if not self.claude:
            QMessageBox.warning(self, "Warnung", "Claude API nicht verfügbar. Bitte API Key in config.ini eintragen.")
            return

        thema = self.new_stichwort.text().strip()
        if not thema:
            QMessageBox.warning(self, "Warnung", "Bitte geben Sie ein Alarmierungsstichwort ein.")
            return

        zusatz = self.new_zusatz.toPlainText()
        seitenzahl = self.new_seitenzahl.value()
        datum = self.new_datum.date().toString("dd.MM.yyyy")
        uhrzeit = self.new_uhrzeit.time().toString("HH:mm")
        schemata = []
        for name, widget in self.schema_widgets.items():
            text = widget.schema_text()
            if text:
                schemata.append(text)
        for name, (cb, inp) in self.schema_simple.items():
            if cb.isChecked():
                val = inp.text().strip()
                schemata.append(f"{name}: {val}" if val else name)
        medikamente = self.new_medikamente.text().strip()
        rettungsmittel = self.new_rettungsmittel.text().strip()

        # Progress Dialog
        progress = QProgressDialog("Bericht wird mit Claude AI erstellt...", None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.show()

        # Worker Thread
        einsatz_daten = {
            'thema': thema,
            'zusaetzliche_infos': zusatz,
            'seitenzahl': seitenzahl,
            'datum': datum,
            'uhrzeit': uhrzeit,
            'stichwort': thema,
            'schemata': schemata,
            'medikamente': medikamente,
            'rettungsmittel': rettungsmittel,
        }
        self.worker = ClaudeWorker(self.claude, einsatz_daten)
        self.worker.finished.connect(lambda text: self.on_report_generated(text, progress))
        self.worker.error.connect(lambda err: self.on_report_error(err, progress))
        self.worker.start()
    
    def erfinden_bericht(self):
        """Öffnet den Erfinden-Dialog und überträgt das Szenario ins Formular"""
        if not self.claude:
            QMessageBox.warning(self, "Warnung", "Claude API nicht verfügbar.")
            return
        dialog = BerichtErfindenDialog(self.claude, self)
        if dialog.exec() != QDialog.Accepted:
            return
        data = dialog.get_invented_data()
        if not data:
            return
        # Basis-Felder füllen
        self.new_stichwort.setText(data.get('stichwort', ''))
        self.new_medikamente.setText(data.get('medikamente', ''))
        self.new_rettungsmittel.setText(data.get('rettungsmittel', ''))
        self.new_zusatz.setPlainText(data.get('zusatz', ''))
        # Datum / Uhrzeit
        if data.get('datum'):
            qd = QDate.fromString(data['datum'], "dd.MM.yyyy")
            if qd.isValid():
                self.new_datum.setDate(qd)
        if data.get('uhrzeit'):
            qt = QTime.fromString(data['uhrzeit'].replace(' Uhr', '').strip(), "HH:mm")
            if qt.isValid():
                self.new_uhrzeit.setTime(qt)
        # Komplexe Schema-Widgets füllen
        for name, widget in self.schema_widgets.items():
            sub = data.get(name.lower(), {})
            widget.clear_values()
            if sub:
                widget.set_values(sub)
        # Einfache Schema-Widgets füllen
        key_map = {'NACA-Score': 'naca', 'GCS': 'gcs', 'VAS': 'vas', '12-Kanal-EKG': 'ekg'}
        for name, (cb, inp) in self.schema_simple.items():
            val = data.get(key_map.get(name, name.lower()), '')
            if val:
                cb.setChecked(True)
                inp.setText(str(val))
            else:
                cb.setChecked(False)
                inp.clear()
        # Tab aktivieren und Info anzeigen
        self.tabs.setCurrentIndex(1)
        QMessageBox.information(self, "Szenario übernommen",
            "Das erfundene Szenario wurde ins Formular übernommen.\n"
            "Klicken Sie auf '🤖 Mit Claude AI generieren' um den vollständigen Bericht zu erstellen.")

    def on_report_generated(self, text, progress):
        """Wird aufgerufen, wenn der Bericht generiert wurde"""
        progress.close()
        self.preview_text.setPlainText(text)
        QMessageBox.information(self, "Erfolg", "Bericht wurde erfolgreich generiert!")
    
    def on_report_error(self, error, progress):
        """Wird aufgerufen, wenn ein Fehler auftritt"""
        progress.close()
        QMessageBox.critical(self, "Fehler", f"Fehler beim Generieren: {error}")
    
    def save_new_report(self):
        """Speichert den neuen Bericht"""
        titel = self.new_titel.text()
        thema = self.new_stichwort.text().strip()
        inhalt = self.preview_text.toPlainText()

        if not titel or not thema or not inhalt:
            QMessageBox.warning(self, "Warnung", "Bitte Titel, Alarmierungsstichwort und generierten Inhalt ausfüllen.")
            return
        
        bericht_id = self.db.bericht_erstellen(titel, thema, inhalt)

        # Optional: PDF und Word generieren
        ff = self.font_family_combo.currentText()
        fs = self.font_size_spin.value()
        try:
            pdf_path = self.report_gen.generate_pdf(titel, thema, inhalt, bericht_id, ff, fs)
            word_path = self.report_gen.generate_word(titel, thema, inhalt, bericht_id, ff, fs)
            self.db.bericht_aktualisieren(bericht_id, pdf_pfad=pdf_path, word_pfad=word_path)
        except Exception as e:
            print(f"Fehler beim Generieren der Dokumente: {e}")
        
        QMessageBox.information(self, "Erfolg", f"Bericht wurde gespeichert (ID: {bericht_id})")
        self.clear_new_report()
        self.load_berichte()
        self.tabs.setCurrentIndex(0)
    
    def clear_new_report(self):
        """Setzt das Formular für neue Berichte zurück"""
        self.new_titel.clear()
        self.new_zusatz.clear()
        self.new_seitenzahl.setValue(2)
        self.new_datum.setDate(QDate.currentDate())
        self.new_uhrzeit.setTime(QTime.currentTime())
        self.new_stichwort.clear()
        self.new_medikamente.clear()
        self.new_rettungsmittel.clear()
        for widget in self.schema_widgets.values():
            widget.clear_values()
        if 'ABCDE' in self.schema_widgets:
            self.schema_widgets['ABCDE'].setChecked(True)
        for cb, inp in self.schema_simple.values():
            cb.setChecked(False)
            inp.clear()
        self.preview_text.clear()
    
    def save_edit(self):
        """Speichert die Änderungen am Bericht"""
        bericht_id_text = self.edit_id.text()
        if bericht_id_text == "-":
            QMessageBox.warning(self, "Warnung", "Kein Bericht geladen.")
            return
        
        bericht_id = int(bericht_id_text)
        titel = self.edit_titel.text()
        thema = self.edit_thema.text()
        inhalt = self.edit_inhalt.toPlainText()
        
        self.db.bericht_aktualisieren(bericht_id, titel=titel, thema=thema, inhalt=inhalt)

        # Optional: Neue Dokumente generieren
        ff = self.font_family_combo.currentText()
        fs = self.font_size_spin.value()
        try:
            pdf_path = self.report_gen.generate_pdf(titel, thema, inhalt, bericht_id, ff, fs)
            word_path = self.report_gen.generate_word(titel, thema, inhalt, bericht_id, ff, fs)
            self.db.bericht_aktualisieren(bericht_id, pdf_pfad=pdf_path, word_pfad=word_path)
        except Exception as e:
            print(f"Fehler beim Generieren der Dokumente: {e}")
        
        QMessageBox.information(self, "Erfolg", "Änderungen wurden gespeichert.")
        self.load_berichte()
    
    def export_bericht(self, format_type):
        """Exportiert den ausgewählten Bericht"""
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Warnung", "Bitte wählen Sie einen Bericht aus.")
            return
        
        row = self.table.currentRow()
        bericht_id = int(self.table.item(row, 0).text())

        bericht = self.db.bericht_abrufen(bericht_id)
        if not bericht:
            return

        ff = self.font_family_combo.currentText()
        fs = self.font_size_spin.value()

        try:
            if format_type == 'pdf':
                filepath = self.report_gen.generate_pdf(
                    bericht['titel'], bericht['thema'], bericht['inhalt'], bericht_id, ff, fs
                )
            elif format_type == 'word':
                filepath = self.report_gen.generate_word(
                    bericht['titel'], bericht['thema'], bericht['inhalt'], bericht_id, ff, fs
                )
            elif format_type == 'odf':
                filepath = self.report_gen.generate_odf(
                    bericht['titel'], bericht['thema'], bericht['inhalt'], bericht_id, ff, fs
                )
            elif format_type == 'pages':
                filepath = self.report_gen.generate_pages(
                    bericht['titel'], bericht['thema'], bericht['inhalt'], bericht_id
                )
            else:
                filepath = self.report_gen.generate_word(
                    bericht['titel'], bericht['thema'], bericht['inhalt'], bericht_id, ff, fs
                )

            QMessageBox.information(self, "Erfolg", f"Bericht exportiert nach:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Exportieren: {str(e)}")
    
    def export_current_bericht(self, format_type):
        """Exportiert den aktuell angezeigten Bericht"""
        bericht_id_text = self.edit_id.text()
        if bericht_id_text == "-":
            QMessageBox.warning(self, "Warnung", "Kein Bericht geladen.")
            return
        
        bericht_id = int(bericht_id_text)
        titel = self.edit_titel.text()
        thema = self.edit_thema.text()
        inhalt = self.edit_inhalt.toPlainText()

        ff = self.font_family_combo.currentText()
        fs = self.font_size_spin.value()

        try:
            if format_type == 'pdf':
                filepath = self.report_gen.generate_pdf(titel, thema, inhalt, bericht_id, ff, fs)
            elif format_type == 'word':
                filepath = self.report_gen.generate_word(titel, thema, inhalt, bericht_id, ff, fs)
            elif format_type == 'odf':
                filepath = self.report_gen.generate_odf(titel, thema, inhalt, bericht_id, ff, fs)
            elif format_type == 'pages':
                filepath = self.report_gen.generate_pages(titel, thema, inhalt, bericht_id)
            else:
                filepath = self.report_gen.generate_word(titel, thema, inhalt, bericht_id, ff, fs)

            QMessageBox.information(self, "Erfolg", f"Bericht exportiert nach:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Exportieren: {str(e)}")

    def import_bericht(self):
        """Öffnet einen Dateidialog zum Importieren eines Berichts"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Bericht importieren", "",
            "Unterstützte Formate (*.docx *.odt *.pages);;"
            "Word (*.docx);;ODF (*.odt);;Apple Pages (*.pages)"
        )
        if not filepath:
            return
        try:
            daten = self.report_gen.import_datei(filepath)
            dialog = ImportDialog(daten, self)
            if dialog.exec() == QDialog.Accepted:
                final = dialog.get_data()
                if not final['titel']:
                    QMessageBox.warning(self, "Warnung", "Bitte einen Titel angeben.")
                    return
                bericht_id = self.db.bericht_erstellen(
                    final['titel'], final['thema'], final['inhalt']
                )
                QMessageBox.information(self, "Erfolg", f"Bericht importiert (ID: {bericht_id})")
                self.load_berichte()
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Importieren:\n{str(e)}")

    def regenerate_edit_report(self):
        """Generiert den aktuell bearbeiteten Bericht neu mit Claude AI"""
        if not self.claude:
            QMessageBox.warning(self, "Warnung", "Claude API nicht verfügbar.")
            return
        thema = self.edit_thema.text()
        if not thema:
            QMessageBox.warning(self, "Warnung", "Kein Thema angegeben.")
            return
        kontext = self.edit_kontext.toPlainText()
        seitenzahl = self.edit_seitenzahl.value()

        progress = QProgressDialog("Bericht wird mit Claude AI erstellt...", None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.show()

        self.edit_worker = ClaudeWorker(self.claude, {
            'thema': thema,
            'zusaetzliche_infos': kontext,
            'seitenzahl': seitenzahl,
        })
        self.edit_worker.finished.connect(lambda text: self.on_edit_regenerated(text, progress))
        self.edit_worker.error.connect(lambda err: self.on_report_error(err, progress))
        self.edit_worker.start()

    def on_edit_regenerated(self, text, progress):
        """Wird aufgerufen, wenn der Bericht im Edit-Tab neu generiert wurde"""
        progress.close()
        self.edit_inhalt.setPlainText(text)
        QMessageBox.information(self, "Erfolg", "Bericht wurde neu generiert!")

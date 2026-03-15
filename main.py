"""
Einsatzbericht Manager - Hauptprogramm
Ein PySide6 GUI-Programm zur Verwaltung und Erstellung von Einsatzberichten
mit Claude AI Integration
"""
import sys
import os
import configparser
from PySide6.QtWidgets import QApplication, QMessageBox

# Importiere Module
from src.database import DatabaseHandler
from src.claude_api import ClaudeAPIHandler
from src.report_generator import ReportGenerator
from src.gui import MainWindow


def app_base_dir() -> str:
    """Gibt das Basisverzeichnis zurück – bei EXE neben der EXE, sonst Projektordner."""
    if getattr(sys, 'frozen', False):
        # PyInstaller: neben der EXE (nicht im _MEIXXXXXX-Temp-Ordner)
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def main():
    """Hauptfunktion"""
    # Qt Application
    app = QApplication(sys.argv)
    app.setApplicationName("Einsatzbericht Manager")

    base = app_base_dir()

    # Konfiguration laden
    config = configparser.ConfigParser()
    config_path = os.path.join(base, 'config.ini')
    # Falls config.ini noch nicht existiert (Erststart nach EXE-Verteilung), Example kopieren
    if not os.path.exists(config_path):
        example_path = os.path.join(base, 'config.ini.example')
        if os.path.exists(example_path):
            import shutil
            shutil.copy(example_path, config_path)
    config.read(config_path, encoding='utf-8')

    # API Key: Umgebungsvariable hat Vorrang, dann config.ini
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        api_key = config.get('API', 'anthropic_api_key', fallback='').strip() or None

    if not api_key or api_key == 'DEIN_API_KEY_HIER':
        api_key = None
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("API Key fehlt")
        msg.setText("Claude API Key nicht gefunden!")
        msg.setInformativeText(
            "Bitte tragen Sie Ihren API Key in die Datei config.ini ein "
            "(anthropic_api_key = sk-ant-...).\n\n"
            "Das Programm wird trotzdem gestartet, aber die AI-Funktionen sind nicht verfügbar."
        )
        msg.exec()

    try:
        # Datenbankpfad immer neben der EXE / im Projektordner
        db_path = os.path.join(base, 'data', 'einsatzberichte.db')
        db_handler = DatabaseHandler(db_path)

        # Beispiele-Pfad aus config (relativ zu base auflösen)
        beispiele_pfad_raw = config.get('BEISPIELE', 'path', fallback='data/beispiele').strip()
        if not os.path.isabs(beispiele_pfad_raw):
            beispiele_pfad = os.path.join(base, beispiele_pfad_raw)
        else:
            beispiele_pfad = beispiele_pfad_raw
        os.makedirs(beispiele_pfad, exist_ok=True)

        # Reports-Ordner ebenfalls neben EXE
        reports_dir = os.path.join(base, 'reports')

        # Claude Handler (kann None sein, wenn kein API Key)
        try:
            claude_handler = ClaudeAPIHandler(api_key, beispiele_pfad) if api_key else None
        except Exception as e:
            claude_handler = None
            print(f"Claude API konnte nicht initialisiert werden: {e}")

        report_generator = ReportGenerator(reports_dir)

        # Hauptfenster erstellen
        window = MainWindow(db_handler, claude_handler, report_generator, beispiele_pfad)
        window.show()

        # Event Loop starten
        sys.exit(app.exec())

    except Exception as e:
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("Fehler")
        msg.setText(f"Ein Fehler ist aufgetreten: {str(e)}")
        msg.exec()
        sys.exit(1)


if __name__ == "__main__":
    main()

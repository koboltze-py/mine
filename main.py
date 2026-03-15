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


def main():
    """Hauptfunktion"""
    # Qt Application
    app = QApplication(sys.argv)
    app.setApplicationName("Einsatzbericht Manager")

    # Konfiguration laden (immer, nicht nur wenn kein Env-Key)
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')
    config.read(config_path, encoding='utf-8')

    # API Key: Umgebungsvariable hat Vorrang, dann config.ini
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        api_key = config.get('API', 'anthropic_api_key', fallback='').strip() or None

    if not api_key:
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("API Key fehlt")
        msg.setText("Claude API Key nicht gefunden!")
        msg.setInformativeText(
            "Bitte setzen Sie die Umgebungsvariable ANTHROPIC_API_KEY oder tragen Sie den Key in config.ini ein.\n\n"
            "Das Programm wird trotzdem gestartet, aber die AI-Funktionen sind nicht verfügbar."
        )
        msg.exec()

    try:
        # Initialisiere Handler
        db_handler = DatabaseHandler("data/einsatzberichte.db")

        # Beispiele-Pfad aus config
        beispiele_pfad = config.get('BEISPIELE', 'path', fallback='data/beispiele').strip()
        os.makedirs(beispiele_pfad, exist_ok=True)

        # Claude Handler (kann None sein, wenn kein API Key)
        try:
            claude_handler = ClaudeAPIHandler(api_key, beispiele_pfad) if api_key else None
        except Exception as e:
            claude_handler = None
            print(f"Claude API konnte nicht initialisiert werden: {e}")
        
        report_generator = ReportGenerator("reports")
        
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

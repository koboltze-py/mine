"""
Datenbank-Handler für Einsatzberichte
"""
import sqlite3
import os
from datetime import datetime
from typing import List, Optional, Dict


class DatabaseHandler:
    def __init__(self, db_path: str = "data/einsatzberichte.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialisiert die Datenbank und erstellt Tabellen"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS einsatzberichte (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    titel TEXT NOT NULL,
                    thema TEXT NOT NULL,
                    inhalt TEXT NOT NULL,
                    reflexion TEXT DEFAULT '',
                    abcde_json TEXT DEFAULT '',
                    vitalwerte_json TEXT DEFAULT '',
                    medikamente_json TEXT DEFAULT '',
                    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    aktualisiert_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    pdf_pfad TEXT,
                    word_pfad TEXT,
                    erstellt_von TEXT DEFAULT 'Claude AI'
                )
            ''')
            conn.commit()
            # Migration: neue Spalten zu bestehenden DBs hinzufügen
            for col_sql in [
                "ALTER TABLE einsatzberichte ADD COLUMN reflexion TEXT DEFAULT ''",
                "ALTER TABLE einsatzberichte ADD COLUMN abcde_json TEXT DEFAULT ''",
                "ALTER TABLE einsatzberichte ADD COLUMN vitalwerte_json TEXT DEFAULT ''",
                "ALTER TABLE einsatzberichte ADD COLUMN medikamente_json TEXT DEFAULT ''",
            ]:
                try:
                    cursor.execute(col_sql)
                    conn.commit()
                except sqlite3.OperationalError:
                    pass  # Spalte existiert bereits
    
    def bericht_erstellen(self, titel: str, thema: str, inhalt: str,
                         reflexion: str = "",
                         abcde_json: str = "",
                         vitalwerte_json: str = "",
                         medikamente_json: str = "",
                         pdf_pfad: Optional[str] = None,
                         word_pfad: Optional[str] = None) -> int:
        """Erstellt einen neuen Einsatzbericht"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO einsatzberichte
                    (titel, thema, inhalt, reflexion, abcde_json, vitalwerte_json, medikamente_json, pdf_pfad, word_pfad)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (titel, thema, inhalt, reflexion, abcde_json, vitalwerte_json, medikamente_json, pdf_pfad, word_pfad))
            conn.commit()
            return cursor.lastrowid
    
    def bericht_aktualisieren(self, bericht_id: int, titel: Optional[str] = None,
                             thema: Optional[str] = None, inhalt: Optional[str] = None,
                             reflexion: Optional[str] = None,
                             abcde_json: Optional[str] = None,
                             vitalwerte_json: Optional[str] = None,
                             medikamente_json: Optional[str] = None,
                             pdf_pfad: Optional[str] = None, word_pfad: Optional[str] = None):
        """Aktualisiert einen bestehenden Einsatzbericht"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            updates = []
            params = []
            
            if titel is not None:
                updates.append("titel = ?")
                params.append(titel)
            if thema is not None:
                updates.append("thema = ?")
                params.append(thema)
            if inhalt is not None:
                updates.append("inhalt = ?")
                params.append(inhalt)
            if reflexion is not None:
                updates.append("reflexion = ?")
                params.append(reflexion)
            if abcde_json is not None:
                updates.append("abcde_json = ?")
                params.append(abcde_json)
            if vitalwerte_json is not None:
                updates.append("vitalwerte_json = ?")
                params.append(vitalwerte_json)
            if medikamente_json is not None:
                updates.append("medikamente_json = ?")
                params.append(medikamente_json)
            if pdf_pfad is not None:
                updates.append("pdf_pfad = ?")
                params.append(pdf_pfad)
            if word_pfad is not None:
                updates.append("word_pfad = ?")
                params.append(word_pfad)
            
            updates.append("aktualisiert_am = CURRENT_TIMESTAMP")
            params.append(bericht_id)
            
            query = f"UPDATE einsatzberichte SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            conn.commit()
    
    def bericht_abrufen(self, bericht_id: int) -> Optional[Dict]:
        """Ruft einen Einsatzbericht ab"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM einsatzberichte WHERE id = ?', (bericht_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def alle_berichte_abrufen(self) -> List[Dict]:
        """Ruft alle Einsatzberichte ab"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM einsatzberichte ORDER BY erstellt_am DESC')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def bericht_loeschen(self, bericht_id: int):
        """Löscht einen Einsatzbericht"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM einsatzberichte WHERE id = ?', (bericht_id,))
            conn.commit()
    
    def berichte_suchen(self, suchbegriff: str) -> List[Dict]:
        """Sucht Einsatzberichte nach einem Begriff"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            query = '''
                SELECT * FROM einsatzberichte 
                WHERE titel LIKE ? OR thema LIKE ? OR inhalt LIKE ?
                ORDER BY erstellt_am DESC
            '''
            search_pattern = f'%{suchbegriff}%'
            cursor.execute(query, (search_pattern, search_pattern, search_pattern))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

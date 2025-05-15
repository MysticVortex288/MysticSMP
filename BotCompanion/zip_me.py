import zipfile
import os
import time

def zipdir(path, ziph):
    # Aktuelle Zeit für alle Dateien verwenden (nach 1980)
    now = time.localtime(time.time())[:6]
    
    for root, dirs, files in os.walk(path):
        for file in files:
            if file == "mybot.zip" or file.endswith(".zip"):
                continue  # überspringe alte ZIPs
            
            file_path = os.path.join(root, file)
            archive_path = os.path.relpath(file_path, path)
            
            try:
                # Manuell das ZipInfo-Objekt erstellen mit korrektem Datum
                info = zipfile.ZipInfo(archive_path)
                info.date_time = now
                info.compress_type = zipfile.ZIP_DEFLATED
                
                # Datei lesen und zum ZIP hinzufügen
                with open(file_path, 'rb') as f:
                    data = f.read()
                ziph.writestr(info, data)
                
                print(f"  Hinzugefügt: {archive_path}")
            except Exception as e:
                print(f"  Fehler bei {file_path}: {e}")
                continue

print("ZIP-Erstellung gestartet...")
with zipfile.ZipFile("mybot.zip", 'w', zipfile.ZIP_DEFLATED) as zipf:
    zipdir(".", zipf)

print("✅ ZIP-Datei erstellt: mybot.zip")

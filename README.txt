CDSS Penyakit Jantung (prototype, Streamlit + SQLite)

Isi folder (harus satu folder):
  app.py            tampilan web
  cdss_db.py        database dan aturan (R01-R04)
  requirements.txt  daftar paket

Cara menjalankan:
1. Buka folder ini di VS Code (File > Open Folder).
2. Buka Terminal (Ctrl + `).
3. Pasang paket (sekali saja):  python -m pip install -r requirements.txt
4. Jalankan:                    python -m streamlit run app.py
   Kalau diminta email, tekan Enter saja. Browser terbuka otomatis di http://localhost:8501

File database cdss_jantung.db dibuat otomatis. Data simulasi, bukan alat diagnosis.

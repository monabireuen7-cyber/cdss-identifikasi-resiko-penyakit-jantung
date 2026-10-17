"""Lapisan database CDSS penyakit jantung (SQLite, bawaan Python).

Strukturnya mengikuti file Excel prototype:
  - tabel `pasien`      : ID, nama, usia, jenis kelamin   (sheet Data_Pasien)
  - tabel `pemeriksaan` : tekanan darah, kolesterol, faktor risiko, gejala (sheet Hasil_CDSS)
Hasil identifikasi TIDAK disimpan, tapi dihitung dari data lewat `hitung_hasil()`
dengan rule yang sama seperti rumus Excel, jadi selalu konsisten.

Data simulasi untuk latihan, bukan alat diagnosis.
"""
import os
import sqlite3
from contextlib import contextmanager

# File database disimpan di folder yang sama dengan skrip ini (bisa diganti lewat variabel lingkungan CDSS_DB_PATH).
DB_PATH = os.environ.get("CDSS_DB_PATH") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "cdss.db")

# Kolom check box (0 = Tidak, 1 = Ya)
FAKTOR = ["merokok", "diabetes", "riwayat_keluarga", "obesitas"]
GEJALA = ["nyeri_dada", "sesak_napas", "mudah_lelah", "jantung_berdebar", "pusing"]

_KOLOM_CENTANG = ",\n  ".join(f"{k} INTEGER NOT NULL DEFAULT 0 CHECK ({k} IN (0, 1))" for k in FAKTOR + GEJALA)
SKEMA = f"""
CREATE TABLE IF NOT EXISTS pasien (
  id_pasien     TEXT PRIMARY KEY,
  nama          TEXT NOT NULL,
  usia          INTEGER NOT NULL CHECK (usia >= 0),
  jenis_kelamin TEXT NOT NULL CHECK (jenis_kelamin IN ('Laki-laki', 'Perempuan'))
);
CREATE TABLE IF NOT EXISTS pemeriksaan (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  id_pasien     TEXT NOT NULL REFERENCES pasien(id_pasien),
  tanggal       TEXT NOT NULL DEFAULT (date('now')),
  tekanan_darah TEXT NOT NULL CHECK (tekanan_darah IN ('Normal', 'Tinggi')),
  kolesterol    TEXT NOT NULL CHECK (kolesterol IN ('Normal', 'Tinggi')),
  {_KOLOM_CENTANG}
);
"""


@contextmanager
def koneksi(path=None):
    """Buka koneksi, commit otomatis kalau sukses, rollback kalau error."""
    con = sqlite3.connect(path or DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def init_db(path=None):
    with koneksi(path) as con:
        con.executescript(SKEMA)


# ---------- rule (sama dengan kolom P:S di Excel) ----------
def hitung_hasil(p):
    """p = baris pemeriksaan (dict/sqlite3.Row). Mengembalikan dict hasil identifikasi."""
    faktor = (p["tekanan_darah"] == "Tinggi") + (p["kolesterol"] == "Tinggi") + sum(p[k] for k in FAKTOR)
    gejala = sum(p[k] for k in GEJALA)
    if p["nyeri_dada"] and p["sesak_napas"]:
        hasil, saran = "PERINGATAN: EVALUASI SEGERA", "Segera cari pertolongan medis untuk evaluasi gejala."
    elif faktor >= 4:
        hasil, saran = "Kategori Prototype Tinggi", "Perlu penilaian lebih lanjut oleh tenaga kesehatan."
    elif faktor >= 2:
        hasil, saran = "Kategori Prototype Sedang", "Konsultasikan faktor risiko dengan tenaga kesehatan."
    else:
        hasil, saran = "Kategori Prototype Rendah", "Edukasi kesehatan dan pemantauan rutin."
    return {"jumlah_faktor_risiko": faktor, "jumlah_gejala": gejala, "hasil": hasil, "rekomendasi": saran}


# ---------- operasi data ----------
def tambah_pasien(id_pasien, nama, usia, jenis_kelamin, path=None):
    with koneksi(path) as con:
        con.execute("INSERT INTO pasien VALUES (?, ?, ?, ?)", (id_pasien, nama, usia, jenis_kelamin))


def daftar_pasien(path=None):
    """Untuk isi dropdown ID. Nama dan usia diambil lewat `ambil_pasien()`."""
    with koneksi(path) as con:
        return [dict(r) for r in con.execute("SELECT * FROM pasien ORDER BY id_pasien")]


def ambil_pasien(id_pasien, path=None):
    with koneksi(path) as con:
        r = con.execute("SELECT * FROM pasien WHERE id_pasien = ?", (id_pasien,)).fetchone()
        return dict(r) if r else None


def simpan_pemeriksaan(id_pasien, tekanan_darah, kolesterol, centang=(), path=None):
    """`centang` = nama kolom yang dicentang, mis. ['merokok', 'nyeri_dada']."""
    tidak_dikenal = set(centang) - set(FAKTOR + GEJALA)
    if tidak_dikenal:
        raise ValueError(f"Kolom check box tidak dikenal: {sorted(tidak_dikenal)}")
    nilai = {k: int(k in centang) for k in FAKTOR + GEJALA}
    kolom = ["id_pasien", "tekanan_darah", "kolesterol"] + list(nilai)
    with koneksi(path) as con:
        con.execute(
            f"INSERT INTO pemeriksaan ({', '.join(kolom)}) VALUES ({', '.join('?' * len(kolom))})",
            [id_pasien, tekanan_darah, kolesterol] + list(nilai.values()),
        )


def tabel_hasil(path=None):
    """Satu baris per pemeriksaan: data pasien + centang + hasil (setara sheet Hasil_CDSS)."""
    with koneksi(path) as con:
        rows = con.execute(
            "SELECT p.id_pasien, p.nama, p.usia, p.jenis_kelamin, m.* "
            "FROM pemeriksaan m JOIN pasien p USING (id_pasien) ORDER BY m.id"
        ).fetchall()
    return [{**dict(r), **hitung_hasil(r)} for r in rows]


# ---------- data contoh (sama dengan 5 pasien di Excel) ----------
CONTOH = [
    ("P001", "Andi", 55, "Laki-laki", "Tinggi", "Tinggi", ["merokok", "riwayat_keluarga", "obesitas", "nyeri_dada", "sesak_napas", "mudah_lelah"]),
    ("P002", "Siti", 35, "Perempuan", "Normal", "Normal", []),
    ("P003", "Budi", 48, "Laki-laki", "Tinggi", "Normal", ["merokok", "riwayat_keluarga", "nyeri_dada", "mudah_lelah", "jantung_berdebar"]),
    ("P004", "Rina", 62, "Perempuan", "Tinggi", "Tinggi", ["diabetes", "riwayat_keluarga", "obesitas"] + GEJALA),
    ("P005", "Dedi", 42, "Laki-laki", "Normal", "Tinggi", ["merokok", "mudah_lelah"]),
]


def isi_data_contoh(path=None):
    for id_, nama, usia, jk, td, kol, centang in CONTOH:
        tambah_pasien(id_, nama, usia, jk, path)
        simpan_pemeriksaan(id_, td, kol, centang, path)


if __name__ == "__main__":
    init_db()
    if not daftar_pasien():
        isi_data_contoh()
    for r in tabel_hasil():
        print(f"{r['id_pasien']} {r['nama']:<5} faktor={r['jumlah_faktor_risiko']} "
              f"gejala={r['jumlah_gejala']} -> {r['hasil']}")

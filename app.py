"""Aplikasi web CDSS penyakit jantung (Streamlit + SQLite).

Menjalankan:   streamlit run app.py
Alurnya sama dengan file Excel prototype:
  Form CDSS   -> pilih ID pasien (Nama & Usia terisi otomatis), combo box, check list, hasil langsung muncul
  Hasil CDSS  -> tabel semua pemeriksaan beserta hasil identifikasi
  Data Pasien -> daftar induk pasien (tambah pasien baru)
  Petunjuk    -> tujuan, rule, dan peringatan keselamatan
Data simulasi untuk latihan, bukan alat diagnosis.
"""
import sqlite3

import pandas as pd
import streamlit as st

import cdss_db as db

st.set_page_config(page_title="CDSS Penyakit Jantung (Prototype)", page_icon="🫀", layout="wide")

# Siapkan database; isi 5 pasien contoh (sama seperti di Excel) hanya saat database masih kosong.
db.init_db()
if not db.daftar_pasien():
    db.isi_data_contoh()

LABEL = {
    "merokok": "Merokok", "diabetes": "Diabetes", "riwayat_keluarga": "Riwayat Keluarga", "obesitas": "Obesitas",
    "nyeri_dada": "Nyeri Dada", "sesak_napas": "Sesak Napas", "mudah_lelah": "Mudah Lelah",
    "jantung_berdebar": "Jantung Berdebar", "pusing": "Pusing",
}
PILIHAN_KATEGORI = ["Normal", "Tinggi"]


def ikon(hasil):
    if hasil.startswith("PERINGATAN"):
        return "🔴"
    if hasil.endswith("Tinggi"):
        return "🟠"
    if hasil.endswith("Sedang"):
        return "🟡"
    return "🟢"


def tampil_hasil(h):
    teks = f"**{ikon(h['hasil'])} {h['hasil']}**\n\n{h['rekomendasi']}"
    if h["hasil"].startswith("PERINGATAN"):
        st.error(teks)
    elif h["hasil"].endswith("Tinggi"):
        st.warning(teks)
    elif h["hasil"].endswith("Sedang"):
        st.info(teks)
    else:
        st.success(teks)


st.title("🫀 CDSS Penyakit Jantung")
st.caption("Prototype rule-based untuk latihan. Data simulasi, bukan alat diagnosis atau penilaian risiko klinis tervalidasi.")

tab_form, tab_hasil, tab_pasien, tab_info = st.tabs(["Form CDSS", "Hasil CDSS", "Data Pasien", "Petunjuk & Rule"])

# ======================= Form CDSS =======================
with tab_form:
    daftar = db.daftar_pasien()
    kiri, kanan = st.columns(2)

    with kiri:
        st.subheader("1. Pilih pasien")
        id_terpilih = st.selectbox(
            "ID Pasien", [p["id_pasien"] for p in daftar],
            index=None, placeholder="Pilih ID pasien...",
        )
        info = db.ambil_pasien(id_terpilih) if id_terpilih else None
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Nama", info["nama"] if info else "-")
        with m2:
            st.metric("Usia (tahun)", info["usia"] if info else "-")
        with m3:
            st.metric("Jenis Kelamin", info["jenis_kelamin"] if info else "-")

        st.subheader("2. Kategori")
        tekanan_darah = st.selectbox("Tekanan Darah", PILIHAN_KATEGORI, index=None, placeholder="Pilih...")
        kolesterol = st.selectbox("Kolesterol", PILIHAN_KATEGORI, index=None, placeholder="Pilih...")

    cek = {}
    with kanan:
        st.subheader("3. Faktor risiko")
        for k in db.FAKTOR:
            cek[k] = st.checkbox(LABEL[k], key=f"cek_{k}")
        st.subheader("4. Gejala")
        for k in db.GEJALA:
            cek[k] = st.checkbox(LABEL[k], key=f"cek_{k}")

    st.divider()
    st.subheader("Hasil identifikasi")
    if not (id_terpilih and tekanan_darah and kolesterol):
        st.info("Pilih ID Pasien, Tekanan Darah, dan Kolesterol terlebih dahulu. Hasil muncul otomatis.")
    else:
        nilai = {"tekanan_darah": tekanan_darah, "kolesterol": kolesterol, **{k: int(v) for k, v in cek.items()}}
        h = db.hitung_hasil(nilai)
        h1, h2 = st.columns(2)
        with h1:
            st.metric("Jumlah Faktor Risiko", h["jumlah_faktor_risiko"])
        with h2:
            st.metric("Jumlah Gejala", h["jumlah_gejala"])
        tampil_hasil(h)

        if st.button("Simpan pemeriksaan ke database", type="primary"):
            db.simpan_pemeriksaan(id_terpilih, tekanan_darah, kolesterol, [k for k, v in cek.items() if v])
            st.success(f"Pemeriksaan {id_terpilih} tersimpan. Lihat di tab Hasil CDSS.")

# ======================= Hasil CDSS =======================
with tab_hasil:
    st.subheader("Hasil identifikasi semua pemeriksaan")
    baris = db.tabel_hasil()
    if not baris:
        st.info("Belum ada pemeriksaan tersimpan.")
    else:
        df = pd.DataFrame(baris)
        for k in db.FAKTOR + db.GEJALA:
            df[k] = df[k].astype(bool)  # tampil sebagai kotak centang
        df["status"] = [f"{ikon(x)} {x}" for x in df["hasil"]]
        kolom = {
            "id_pasien": "ID Pasien", "nama": "Nama", "usia": "Usia", "jenis_kelamin": "Jenis Kelamin",
            "tanggal": "Tanggal", "tekanan_darah": "Tekanan Darah", "kolesterol": "Kolesterol",
            **LABEL,
            "jumlah_faktor_risiko": "Jumlah Faktor Risiko", "jumlah_gejala": "Jumlah Gejala",
            "status": "Hasil Identifikasi", "rekomendasi": "Rekomendasi",
        }
        tabel = df[list(kolom)].rename(columns=kolom)
        st.dataframe(tabel, hide_index=True)
        st.download_button(
            "Unduh sebagai CSV", tabel.to_csv(index=False).encode("utf-8-sig"),
            file_name="hasil_cdss.csv", mime="text/csv",
        )

# ======================= Data Pasien =======================
with tab_pasien:
    st.subheader("Daftar induk pasien")
    if "pesan_pasien" in st.session_state:
        st.success(st.session_state.pop("pesan_pasien"))
    with st.expander("Tambah pasien baru"):
        with st.form("form_pasien", clear_on_submit=True):
            f1, f2 = st.columns(2)
            with f1:
                id_baru = st.text_input("ID Pasien", placeholder="contoh: P006")
                nama_baru = st.text_input("Nama")
            with f2:
                usia_baru = st.number_input("Usia (tahun)", min_value=0, max_value=120, step=1, value=None, placeholder="Isi usia")
                jk_baru = st.selectbox("Jenis Kelamin", ["Laki-laki", "Perempuan"], index=None, placeholder="Pilih...")
            kirim = st.form_submit_button("Tambah pasien")
        if kirim:
            if not (id_baru.strip() and nama_baru.strip() and usia_baru is not None and jk_baru):
                st.error("Lengkapi ID, Nama, Usia, dan Jenis Kelamin.")
            else:
                try:
                    db.tambah_pasien(id_baru.strip(), nama_baru.strip(), int(usia_baru), jk_baru)
                    st.session_state["pesan_pasien"] = f"Pasien {id_baru.strip()} ditambahkan. Pilihannya sudah muncul di Form CDSS."
                    st.rerun()  # muat ulang agar daftar ID di Form CDSS ikut diperbarui
                except sqlite3.IntegrityError:
                    st.error("ID Pasien sudah dipakai. Gunakan ID lain.")
    tabel_pasien = pd.DataFrame(db.daftar_pasien())
    tabel_pasien = tabel_pasien.rename(columns={"id_pasien": "ID Pasien", "nama": "Nama", "usia": "Usia (tahun)", "jenis_kelamin": "Jenis Kelamin"})
    st.dataframe(tabel_pasien, hide_index=True)

# ======================= Petunjuk & Rule =======================
with tab_info:
    st.subheader("Tujuan")
    st.write("Mendemonstrasikan input data, penghitungan sederhana, pencocokan IF–THEN, dan keluaran rekomendasi "
             "untuk identifikasi awal berdasarkan faktor risiko dan gejala.")
    st.subheader("Cara pakai")
    st.write("Di tab Form CDSS, pilih ID pasien (Nama dan Usia terisi otomatis), pilih Tekanan Darah dan Kolesterol, "
             "lalu centang faktor risiko dan gejala yang ada. Hasil muncul langsung; klik Simpan untuk menyimpannya ke database. "
             "Pasien baru ditambahkan di tab Data Pasien.")
    st.subheader("Rule (prioritas dari atas)")
    st.table(pd.DataFrame([
        ["R01", 'Nyeri dada = "Ya" DAN Sesak napas = "Ya"', "Peringatan: evaluasi segera", "Peringatan gejala, bukan kategori risiko."],
        ["R02", "Jumlah faktor risiko ≥ 4", "Kategori prototype tinggi", "Ambang simulasi, bukan cut-off klinis."],
        ["R03", "Jumlah faktor risiko 2–3", "Kategori prototype sedang", "Ambang simulasi, bukan cut-off klinis."],
        ["R04", "Jumlah faktor risiko 0–1", "Kategori prototype rendah", "Tidak berarti bebas penyakit."],
    ], columns=["Kode", "Kondisi IF", "Keluaran THEN", "Catatan"]))
    st.write("Jumlah faktor risiko = Tekanan Darah Tinggi + Kolesterol Tinggi + Merokok + Diabetes + Riwayat Keluarga + Obesitas.")
    st.warning("Ambang kategori di aplikasi ini adalah aturan simulasi untuk latihan logika, bukan kriteria medis. "
               "Untuk penelitian, rule harus dirujuk pada pedoman klinis dan divalidasi tenaga kesehatan.")
    st.error("Keselamatan: jika seseorang mengalami nyeri dada baru/berat, sesak napas berat, pingsan, atau gejala "
             "mengkhawatirkan, jangan menunggu hasil aplikasi; segera cari pertolongan medis.")

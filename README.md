# Optimasi Penjadwalan Kuliah dengan Algoritma Genetika (Tahap UTS)

## 1. Tugas ini tentang apa?

Program ini menyusun **jadwal kuliah otomatis** memakai **Algoritma Genetika (AG)**. Tugasnya: menempatkan setiap sesi kuliah ke satu **hari + jam + ruang** sehingga **tidak ada bentrok**.

Data berasal dari **daftar hadir asli semester Gasal 2026, Prodi Teknik Informatika** (folder PDF dari Drive), lalu disederhanakan:

- **4 kelas** (angkatan 2024 dan 2025 x kelas A/B): TI-A24, TI-B24, TI-A25, TI-B25
- 5 mata kuliah per kelas = **20 sesi kuliah**. Kode mata kuliah, dosen pengampu (tim 2 dosen per kelas), dan jumlah mahasiswa (peserta di daftar hadir = KRS) adalah **data asli**
- 20 dosen (kode = nama depan; daftar lengkap di `data/dosen.csv`)
- 5 ruang: FT5, FT7, FT8, FT9, AUDITORIUM
- 5 hari x 5 slot waktu = 25 slot (S1-S4 = blok 150 menit sesuai jadwal asli; **S5 17:00-19:30 adalah tambahan hipotetis**)

**Yang BUKAN data resmi (perlu diganti jika ada data aslinya):**
- Kapasitas ruang = ESTIMASI (peserta terbanyak yang tercatat memakai ruang itu di daftar hadir).
- Preferensi hari dosen (kendala lunak) = CONTOH/simulasi.
- Pada angkatan 2025 ada 6 mata kuliah paralel A/B; **Kompleksitas Algoritma dikeluarkan** agar total 20 sesi (ubah lewat `EXCLUDE` di `ekstrak_data.py`).

AG ditulis **dari nol** (tanpa DEAP/PyGAD). Library yang dipakai hanya pandas, matplotlib, openpyxl untuk olah hasil, grafik, dan ekspor Excel.

## 2. Cara menjalankan (langkah demi langkah)

### Prasyarat
- Python 3.9 atau lebih baru (cek: `python --version`)

### Langkah

```bash
# 1. Masuk ke folder proyek
cd ga-penjadwalan

# 2. (Disarankan) buat virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3. Pasang library
pip install -r requirements.txt

# 4. Jalankan unit test (harus tampil "Semua test lulus.")
python test_fitness.py

# 5. Jalankan eksperimen penuh (4 konfigurasi x 10 seed, sekitar 30 detik)
python main.py

# 6. (Opsional) eksperimen tambahan dengan populasi kecil agar proses evolusi terlihat
python main.py --pop 10 --out hasil_pop10
```

Data sudah ada di folder `data/`. Untuk membuat ulang dari PDF daftar hadir: `python ekstrak_data.py <folder_pdf>` (butuh `pdftotext` dari poppler-utils).

Jika `python` tidak dikenali, coba `python3`.

### Opsi tambahan

```bash
python main.py --runs 10 --generations 200 --pop 100 --pc 0.8 --pm 0.05 --out hasil
```

| Opsi | Arti | Default |
|---|---|---|
| `--runs` | jumlah run (seed 0, 1, 2, ...) per konfigurasi | 10 |
| `--generations` | jumlah generasi | 200 |
| `--pop` | ukuran populasi | 100 |
| `--pc` | probabilitas crossover | 0.8 |
| `--pm` | probabilitas mutasi per gen | 0.05 |
| `--out` | folder keluaran | hasil |

## 3. Apa yang keluar?

Setelah `python main.py` selesai, terminal menampilkan ringkasan, dan folder `hasil/` berisi:

| File | Isi |
|---|---|
| `jadwal_terbaik.xlsx` | Excel: sheet Daftar Sesi, Tabel Hari x Slot, Ringkasan Run, Ringkasan Konfigurasi |
| `jadwal_terbaik.csv` | Daftar sesi (kode, mata kuliah, dosen, kelas, hari, slot, jam, ruang) |
| `tabel_jadwal.csv` | Tabel jadwal hari x slot |
| `ringkasan_run.csv` | Per run: fitness terbaik, rata-rata akhir, generasi valid pertama, kendala lunak, waktu |
| `ringkasan_konfigurasi.csv` | Rata-rata per konfigurasi |
| `konvergensi.png` | Grafik konvergensi fitness per generasi |

`hasil_pop10/` berisi keluaran eksperimen tambahan (populasi 10) dengan struktur sama.

Data masukan ada di folder `data/`: `mata_kuliah.csv`, `ruang.csv`, `dosen.csv`, `preferensi_dosen.csv`, dan `sumber_daftar_hadir.csv` (ringkasan semua PDF).

## 4. Penjelasan cara kerja

### 4.1 Kromosom (representasi jadwal)
Satu kromosom = satu jadwal lengkap berupa **array 20 bilangan bulat** (satu gen per sesi kuliah, urutannya mengikuti daftar mata kuliah). Nilai gen `g` (0-124) dikodekan sebagai pasangan (slot waktu, ruang):

```
slot_waktu = g // jumlah_ruang     # 0..24  -> hari = slot_waktu // 5, jam = slot_waktu % 5
ruang      = g %  jumlah_ruang     # 0..4
```

Alasan memilih encoding integer: setiap mata kuliah pasti terjadwal tepat satu kali, satu gen sudah memuat keputusan kapan dan di mana, dan operator standar bisa dipakai tanpa perbaikan khusus. Bentrok dibiarkan muncul lalu dihukum oleh fitness.

### 4.2 Fungsi fitness

```
fitness = 1 / (1 + V)
```

`V` = total pelanggaran **kendala keras**:

1. **Dosen**: satu dosen mengajar dua sesi di slot yang sama (tiap kelas diampu tim 2 dosen; keduanya dicek)
2. **Ruang**: satu ruang dipakai dua sesi di slot yang sama
3. **Kelas**: satu kelas mahasiswa punya dua sesi di slot yang sama
4. **Kapasitas**: ruang lebih kecil dari jumlah mahasiswa

Fitness = 1,0 berarti jadwal **tanpa bentrok**.

**Kendala lunak** (dosen menghindari hari tertentu, jeda antar sesi satu kelas) dihitung dan dilaporkan saja; belum masuk fitness (sesuai ketentuan UTS).

### 4.3 Alur AG (per generasi)

1. Hitung fitness semua individu, catat terbaik dan rata-rata
2. **Elitisme**: salin 2 individu terbaik langsung ke generasi berikutnya
3. **Seleksi** dua induk (roulette wheel atau turnamen k=3)
4. **Crossover** dengan peluang `pc` (satu titik atau uniform)
5. **Mutasi**: tiap gen diganti nilai acak dengan peluang `pm`
6. Ulangi sampai populasi baru penuh, lalu lanjut generasi berikutnya sampai batas generasi

### 4.4 Eksperimen yang dijalankan
`main.py` menguji 4 kombinasi (roulette/turnamen x satu titik/uniform), masing-masing 10 run dengan seed 0-9. Untuk seed yang sama, populasi awal identik di semua konfigurasi sehingga perbandingannya adil. Jadwal terbaik diambil dari run dengan fitness tertinggi (seri: generasi valid paling awal).

### 4.5 Hasil singkat (dari run kami)
- Populasi 100: 40 dari 40 run menemukan jadwal tanpa bentrok; generasi valid pertama rata-rata 0,60 (paling lambat generasi 2); 20 dari 40 run sudah valid di populasi awal.
- Populasi 10: 40 dari 40 run valid; generasi valid pertama rata-rata 5,2 (paling lambat generasi 23).
- Pada skala data ini masalahnya relatif longgar (20 sesi untuk 125 posisi), sehingga perbedaan antar konfigurasi kecil dan tidak bisa disimpulkan dari 10 run. Data yang lebih besar (UAS) diperlukan untuk membedakannya.

## 5. Struktur kode

| File | Isi |
|---|---|
| `data.py` | Membaca data dari `data/*.csv` |
| `ekstrak_data.py` | Membuat CSV di `data/` dari PDF daftar hadir |
| `problem.py` | Dekode kromosom, hitung pelanggaran keras dan lunak, fitness |
| `ga.py` | Inisialisasi, seleksi, crossover, mutasi, elitisme, loop evolusi |
| `main.py` | Eksperimen 4 konfigurasi x 10 seed, ekspor CSV/Excel, grafik |
| `test_fitness.py` | Unit test pengecekan bentrok (5 tes) |

## 6. Mengganti data atau parameter

- **Ganti data**: edit CSV di `data/` (misalnya kapasitas resmi di `ruang.csv`), lalu jalankan ulang `python main.py`. Kolom `dosen` di `mata_kuliah.csv` berisi kode dosen dipisah `;`. `ekstrak_data.py` menimpa `mata_kuliah.csv`, `dosen.csv`, `ruang.csv`; `preferensi_dosen.csv` hanya dibuat jika belum ada.
- **Ganti parameter**: pakai opsi di bagian 2, atau ubah nilai default di `GAConfig` (`ga.py`).
- Jika menambah mata kuliah, pastikan jumlah sesi tidak melebihi jumlah slot x ruang.

## 7. Masalah umum

| Masalah | Solusi |
|---|---|
| `ModuleNotFoundError` | Jalankan `pip install -r requirements.txt` |
| `python` tidak ditemukan | Pakai `python3` |
| File Excel gagal tersimpan | Tutup `jadwal_terbaik.xlsx` jika sedang terbuka, lalu ulangi |

## 8. Anggota kelompok

(isi nama, NIM, dan peran masing-masing)

## 9. Tautan repositori

(isi tautan GitHub/GitLab; dosen `noverara@gmail.com` ditambahkan sebagai kolaborator)

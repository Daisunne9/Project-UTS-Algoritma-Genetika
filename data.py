"""Data penjadwalan kuliah. SUMBER DATA = file CSV di folder data/ (lihat ekstrak_data.py).

Model: 4 kelas (TI-A24, TI-B24, TI-A25, TI-B25) x 5 mata kuliah = 20 sesi,
5 hari x 5 slot waktu = 25 slot, 5 ruang (FT5, FT7, FT8, FT9, AUDITORIUM).

Untuk mengganti data (mis. kapasitas ruang resmi) cukup edit CSV di data/ lalu jalankan ulang main.py.
"""
import csv
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

DAYS = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat"]
# Slot 1-4 mengikuti blok 150 menit (3 SKS) pada jadwal asli; slot 5 TAMBAHAN (hipotetis) agar total 5 slot/hari sesuai soal.
SLOTS = ["07:00-09:30", "09:30-12:00", "12:00-14:30", "14:30-17:00", "17:00-19:30"]


def _rows(name):
    path = os.path.join(DATA_DIR, name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} tidak ada. Jalankan `python ekstrak_data.py <folder_pdf>` atau isi CSV secara manual.")
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _load():
    courses = [(r["kode"].strip(), r["nama"].strip(), r["dosen"].strip(), r["kelas"].strip(), int(r["jumlah_mhs"]))
               for r in _rows("mata_kuliah.csv")]
    rooms = [(r["ruang"].strip(), int(r["kapasitas"])) for r in _rows("ruang.csv")]
    avoid = {}
    for r in _rows("preferensi_dosen.csv"):
        names = [x.strip() for x in r["hari_dihindari"].split(";") if x.strip()]
        avoid[r["dosen"].strip()] = [DAYS.index(x) for x in names]
    return courses, rooms, avoid


COURSES, ROOMS, AVOID_DAYS = _load()
LECTURERS = sorted({d for c in COURSES for d in c[2].split(";")})   # 1 sesi bisa punya >1 dosen
CLASSES = sorted({c[3] for c in COURSES})

if __name__ == "__main__":
    print(f"{len(COURSES)} sesi, {len(LECTURERS)} dosen, {len(CLASSES)} kelas {CLASSES}, {len(ROOMS)} ruang")

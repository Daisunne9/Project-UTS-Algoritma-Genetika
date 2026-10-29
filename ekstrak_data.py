"""Ekstrak data penjadwalan dari PDF "Daftar Hadir Mahasiswa dan Dosen" (DPNA) per mata kuliah.

Pemakaian:  python ekstrak_data.py <folder_berisi_pdf>
Butuh: perintah `pdftotext` (poppler-utils).

Keluaran di folder data/:
  sumber_daftar_hadir.csv : ringkasan SEMUA PDF (mata kuliah, kode, kelas, ruang, dosen, jumlah peserta, komposisi angkatan)
  mata_kuliah.csv         : sesi yang dipakai model (kolom dosen: kode dosen dipisah ';' karena 1 kelas = tim 2 dosen) (kelas TI-A24, TI-B24, TI-A25, TI-B25)
  dosen.csv               : kode singkat dosen -> nama
  ruang.csv               : 5 ruang + kapasitas (ESTIMASI, lihat catatan)
  preferensi_dosen.csv    : hari yang dihindari dosen (CONTOH, bukan data asli) -> hanya dibuat jika belum ada

Hanya JUMLAH peserta (dari daftar NIM unik) yang dipakai; nama/NIM mahasiswa tidak disimpan.
Aturan pemilihan sesi: mata kuliah yang punya kelas paralel A dan B dengan angkatan dominan
2024 atau 2025. Mata kuliah di EXCLUDE dikeluarkan agar total tepat 20 sesi (5 per kelas).
"""
import collections
import csv
import glob
import os
import re
import subprocess
import sys

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
ROOMS = {"FT-5": "FT5", "FT-7": "FT7", "FT-8": "FT8", "FT-9": "FT9", "AUDITORIUM-FT": "AUDITORIUM"}
EXCLUDE = {"KOMPLEKSITAS ALGORITMA"}   # angkatan 2025 punya 6 mata kuliah A/B; satu dikeluarkan -> 5
DEFAULT_PREF_DAYS = ["Jumat", "Senin", "Rabu", "Kamis", "Selasa"]


def short(name_full):
    toks = [t for t in re.split(r"\s+", name_full.strip()) if t.upper().strip(".") not in ("DRS", "DR", "IR")]
    return toks[0].capitalize()


def parse_pdf(path):
    t = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True).stdout
    one = lambda pat: (re.search(pat, t).group(1).strip() if re.search(pat, t) else "")
    head = t.split("No  ")[0].split("\n")
    dos = []   # tiap kelas punya tim 2 dosen: baris di bawah "Hari / Jam" (tanpa label) + baris "Dosen Pengampu"
    for i, l in enumerate(head):
        if "Hari / Jam" in l and i + 1 < len(head):
            m = re.match(r"\s{20,}([A-Z][^\n]*?)(?:\s{3,}|$)", head[i + 1])
            if m:
                dos.append(m.group(1))
        if "Dosen Pengampu" in l:
            first = re.split(r"\s{3,}", l.split("Dosen Pengampu")[1].strip())[0]
            if first:
                dos.append(first)
    nims = list(dict.fromkeys(re.findall(r"^\s*\d+\s+(\d{12,13})\s", t, re.M)))   # NIM lama = 12 digit
    ang = collections.Counter("20" + n[:2] for n in nims)
    return {
        "matakuliah": one(r"Matakuliah\s{2,}(.+?)(?:\s{3,}|\n)"),
        "kode": one(r"Kode\s{2,}(\S+)"),
        "kelas": one(r"Nama Kelas\s{2,}(\S+)"),
        "hari_jam": one(r"Hari / Jam\s{2,}(.+?)(?:\s{3,}|\n)"),
        "ruang": one(r"Ruang\s{2,}(\S+)"),
        "dosen_nama": " & ".join(dict.fromkeys(d.split(",")[0].strip() for d in dos)),
        "jumlah": len(nims),
        "angkatan": ang,
    }


def main(folder):
    rows = [parse_pdf(p) for p in sorted(glob.glob(os.path.join(folder, "*.pdf")))]
    os.makedirs(OUT, exist_ok=True)
    for r in rows:
        r["dominan"] = r["angkatan"].most_common(1)[0][0] if r["angkatan"] else ""
        r["dosen"] = ";".join(dict.fromkeys(short(n) for n in r["dosen_nama"].split(" & ") if n))

    with open(os.path.join(OUT, "sumber_daftar_hadir.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["matakuliah", "kode", "kelas", "hari_jam", "ruang", "dosen", "jumlah_peserta", "komposisi_angkatan"])
        for r in rows:
            w.writerow([r["matakuliah"], r["kode"], r["kelas"], r["hari_jam"], r["ruang"], r["dosen_nama"],
                        r["jumlah"], ";".join(f"{k}:{v}" for k, v in sorted(r["angkatan"].items()))])

    # ---- pilih sesi untuk model ----
    by_mk = collections.defaultdict(dict)
    for r in rows:
        if r["kelas"] in ("A", "B") and r["dominan"] in ("2024", "2025") and r["matakuliah"] not in EXCLUDE:
            by_mk[(r["matakuliah"], r["dominan"])][r["kelas"]] = r
    sessions = []
    for (mk, ang), d in sorted(by_mk.items(), key=lambda x: (x[0][1], x[0][0])):
        if set(d) == {"A", "B"}:
            for kl in ("A", "B"):
                r = d[kl]
                sessions.append((r["kode"], mk, r["dosen"], f"TI-{kl}{ang[2:]}", r["jumlah"]))
    order = {"TI-A24": 0, "TI-B24": 1, "TI-A25": 2, "TI-B25": 3}
    sessions.sort(key=lambda s: (order.get(s[3], 9), s[1]))
    with open(os.path.join(OUT, "mata_kuliah.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["kode", "nama", "dosen", "kelas", "jumlah_mhs"])
        w.writerows(sessions)

    names = {}
    for r in rows:
        for c, n in zip(r["dosen"].split(";"), r["dosen_nama"].split(" & ")):
            if c:
                assert names.setdefault(c, n) == n, f"kode dosen ganda: {c}"
    used = sorted({d for s in sessions for d in s[2].split(";")})
    with open(os.path.join(OUT, "dosen.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["kode", "nama"])
        w.writerows((d, names[d].title().replace("Drs. ", "").rstrip(".")) for d in used)

    # kapasitas ruang: batas bawah = peserta terbanyak yang tercatat di ruang itu (ESTIMASI)
    cap = {v: 0 for v in ROOMS.values()}
    for r in rows:
        if r["ruang"] in ROOMS:
            cap[ROOMS[r["ruang"]]] = max(cap[ROOMS[r["ruang"]]], r["jumlah"])
    with open(os.path.join(OUT, "ruang.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ruang", "kapasitas", "status"])
        for v in ROOMS.values():
            w.writerow([v, cap[v], "ESTIMASI: peserta terbanyak yang tercatat di ruang ini; ganti dengan kapasitas resmi"])

    p = os.path.join(OUT, "preferensi_dosen.csv")
    if not os.path.exists(p):
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["dosen", "hari_dihindari", "status"])
            for i, d in enumerate(used):
                w.writerow([d, DEFAULT_PREF_DAYS[i % 5], "CONTOH (bukan data asli)"])

    print(f"{len(rows)} PDF dibaca -> {len(sessions)} sesi, {len(used)} dosen, kelas: {sorted({s[3] for s in sessions})}")
    for s in sessions:
        print(" ", s)
    print("Kapasitas ruang (estimasi):", cap)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])

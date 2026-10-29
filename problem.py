"""Model masalah: dekode kromosom, hitung pelanggaran kendala keras & lunak.

Encoding kromosom (integer): panjang = jumlah sesi kuliah (1 gen = 1 sesi).
Nilai gen g in [0, n_slot_total * n_ruang):
    slot_index = g // n_ruang   (0..24 -> hari = slot_index // 5, jam = slot_index % 5)
    ruang_index = g %  n_ruang
"""
from collections import Counter

import data as D


class Problem:
    def __init__(self, courses=None, rooms=None, n_days=5, n_slots=5, avoid_days=None):
        self.courses = courses or D.COURSES
        self.rooms = rooms or D.ROOMS
        self.n_days = n_days
        self.n_slots = n_slots
        self.avoid_days = avoid_days if avoid_days is not None else D.AVOID_DAYS
        self.n_rooms = len(self.rooms)
        self.n_ts = n_days * n_slots              # jumlah slot waktu total
        self.n_genes = len(self.courses)
        self.max_gene = self.n_ts * self.n_rooms  # domain nilai gen: 0..max_gene-1

    # ---------- dekode ----------
    def decode(self, g):
        ts, room = divmod(g, self.n_rooms)
        day, slot = divmod(ts, self.n_slots)
        return day, slot, room

    # ---------- kendala keras ----------
    def hard_violations(self, chrom):
        """Mengembalikan dict jumlah pelanggaran per jenis kendala keras."""
        lec, room, cls = Counter(), Counter(), Counter()
        cap = 0
        for gene, (_, _, dosen, kelas, size) in zip(chrom, self.courses):
            ts, r = divmod(gene, self.n_rooms)
            for d in dosen.split(";"):      # tim dosen: tiap dosen dicek
                lec[(d, ts)] += 1
            cls[(kelas, ts)] += 1
            room[(r, ts)] += 1
            if self.rooms[r][1] < size:
                cap += 1
        pairs = lambda c: sum(n * (n - 1) // 2 for n in c.values())
        return {"dosen": pairs(lec), "ruang": pairs(room), "kelas": pairs(cls), "kapasitas": cap}

    def total_hard(self, chrom):
        return sum(self.hard_violations(chrom).values())

    # ---------- kendala lunak (hanya dilaporkan di UTS) ----------
    def soft_penalties(self, chrom):
        pref = 0
        per_class = {}
        for gene, (_, _, dosen, kelas, _) in zip(chrom, self.courses):
            day, slot, _ = self.decode(gene)
            pref += sum(1 for d in dosen.split(";") if day in self.avoid_days.get(d, []))
            per_class.setdefault((kelas, day), []).append(slot)
        gaps = 0
        for slots in per_class.values():
            slots = sorted(set(slots))
            gaps += sum(max(0, b - a - 1) for a, b in zip(slots, slots[1:]))
        return {"preferensi_dosen": pref, "jeda_kelas": gaps}

    # ---------- fitness ----------
    def fitness(self, chrom):
        return 1.0 / (1.0 + self.total_hard(chrom))

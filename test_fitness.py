"""Unit test pengecekan bentrok (tidak bergantung pada isi data). Jalankan: python test_fitness.py"""
from problem import Problem

P = Problem()
BIG = max(range(P.n_rooms), key=lambda r: P.rooms[r][1])   # ruang terbesar
C = P.courses


def gene(day, slot, room):
    return (day * P.n_slots + slot) * P.n_rooms + room


def conflict_free():
    """Jadwal valid manual: tiap sesi di slot berbeda, di ruang terbesar."""
    assert P.n_genes <= P.n_ts, "jumlah sesi melebihi jumlah slot"
    assert all(P.rooms[BIG][1] >= c[4] for c in C), "ruang terbesar tidak muat semua kelas"
    return [gene(i // P.n_slots, i % P.n_slots, BIG) for i in range(P.n_genes)]


def L(c):
    return set(c[2].split(";"))


def pair(pred):
    for i in range(len(C)):
        for j in range(len(C)):
            if i != j and pred(C[i], C[j]):
                return i, j
    return None


def test_valid_schedule():
    ch = conflict_free()
    assert P.total_hard(ch) == 0 and P.fitness(ch) == 1.0


def test_room_clash():
    # dua sesi beda dosen & beda kelas, slot dan ruang sama -> hanya bentrok ruang
    i, j = pair(lambda a, b: not (L(a) & L(b)) and a[3] != b[3])
    ch = conflict_free(); ch[j] = ch[i]
    v = P.hard_violations(ch)
    assert v == {"dosen": 0, "ruang": 1, "kelas": 0, "kapasitas": 0}, v


def test_lecturer_clash():
    # dosen sama, kelas beda, slot sama, ruang beda -> hanya bentrok dosen
    i, j = pair(lambda a, b: (L(a) & L(b)) and a[3] != b[3])
    ch = conflict_free()
    ch[j] = (ch[i] // P.n_rooms) * P.n_rooms + (BIG + 1) % P.n_rooms
    v = P.hard_violations(ch)
    assert v["dosen"] == len(L(C[i]) & L(C[j])) and v["ruang"] == 0 and v["kelas"] == 0, v


def test_class_clash():
    # kelas sama, dosen beda, slot sama, ruang beda -> hanya bentrok kelas
    i, j = pair(lambda a, b: a[3] == b[3] and not (L(a) & L(b)))
    ch = conflict_free()
    ch[j] = (ch[i] // P.n_rooms) * P.n_rooms + (BIG + 1) % P.n_rooms
    v = P.hard_violations(ch)
    assert v["kelas"] == 1 and v["dosen"] == 0 and v["ruang"] == 0, v


def test_capacity():
    small = min(range(P.n_rooms), key=lambda r: P.rooms[r][1])
    k = max(range(P.n_genes), key=lambda i: C[i][4])
    if P.rooms[small][1] >= C[k][4]:
        print("  (dilewati: semua ruang muat semua kelas)")
        return
    ch = conflict_free(); ch[k] = gene(*divmod(k, P.n_slots), small)
    assert P.hard_violations(ch)["kapasitas"] == 1


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("OK", name)
    print("Semua test lulus.")

"""Menjalankan eksperimen UTS: 4 konfigurasi (seleksi x crossover) x 10 seed.

Output (folder hasil/):
  ringkasan_run.csv        -> hasil tiap run
  ringkasan_konfigurasi.csv-> rata-rata per konfigurasi
  jadwal_terbaik.csv/.xlsx -> daftar sesi kuliah hasil terbaik
  tabel_jadwal.csv         -> tabel hari x slot
  konvergensi.png          -> grafik konvergensi fitness per generasi
"""
import argparse
import os
import statistics as st

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import data as D
from ga import GAConfig, run_ga
from problem import Problem


def schedule_dataframe(problem, chrom):
    rows = []
    for gene, (kode, nama, dosen, kelas, size) in zip(chrom, problem.courses):
        day, slot, r = problem.decode(gene)
        rows.append({
            "Kode": kode, "Mata Kuliah": nama, "Dosen": dosen, "Kelas": kelas,
            "Jml Mhs": size, "Hari": D.DAYS[day], "Slot": slot + 1, "Jam": D.SLOTS[slot],
            "Ruang": problem.rooms[r][0], "Kapasitas": problem.rooms[r][1],
            "_day": day, "_slot": slot,
        })
    return pd.DataFrame(rows).sort_values(["_day", "_slot", "Ruang"]).reset_index(drop=True)


def timetable_dataframe(df):
    table = pd.DataFrame("", index=[f"S{i+1} {s}" for i, s in enumerate(D.SLOTS)], columns=D.DAYS)
    for _, r in df.iterrows():
        cell = f"{r['Kode']} {r['Mata Kuliah']} ({r['Dosen']}, {r['Ruang']}, {r['Kelas']})"
        cur = table.iat[r["_slot"], r["_day"]]
        table.iat[r["_slot"], r["_day"]] = (cur + "\n" + cell) if cur else cell
    return table


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--generations", type=int, default=200)
    ap.add_argument("--pop", type=int, default=100)
    ap.add_argument("--pc", type=float, default=0.8)
    ap.add_argument("--pm", type=float, default=0.05)
    ap.add_argument("--out", default="hasil")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    problem = Problem()   # data dibaca dari data/*.csv (tidak ditimpa)

    configs = [GAConfig(pop_size=args.pop, generations=args.generations, pc=args.pc, pm=args.pm,
                        selection=s, crossover=c)
               for s in ("roulette", "tournament") for c in ("one_point", "uniform")]

    run_rows, results = [], {}
    for cfg in configs:
        results[cfg.name()] = []
        for seed in range(args.runs):
            res = run_ga(problem, cfg, seed)
            results[cfg.name()].append(res)
            soft = problem.soft_penalties(res["best_chrom"])
            run_rows.append({
                "konfigurasi": cfg.name(), "seed": seed,
                "fitness_terbaik": res["best_fitness"],
                "fitness_rata2_akhir": round(res["final_avg_fitness"], 4),
                "gen_valid_pertama": res["first_valid_gen"] if res["first_valid_gen"] is not None else "tidak ada",
                "pelanggaran_keras": problem.total_hard(res["best_chrom"]),
                "preferensi_dosen_dilanggar": soft["preferensi_dosen"],
                "jeda_kelas": soft["jeda_kelas"],
                "waktu_s": round(res["time_s"], 3),
            })
    runs = pd.DataFrame(run_rows)
    runs.to_csv(os.path.join(args.out, "ringkasan_run.csv"), index=False)

    # ringkasan per konfigurasi
    summ = []
    for name, rs in results.items():
        valid_gens = [r["first_valid_gen"] for r in rs if r["first_valid_gen"] is not None]
        bests = [r["best_fitness"] for r in rs]
        summ.append({
            "konfigurasi": name,
            "run_valid": f"{len(valid_gens)}/{len(rs)}",
            "fitness_terbaik_max": max(bests),
            "fitness_terbaik_rata2": round(st.mean(bests), 4),
            "fitness_rata2_populasi_akhir": round(st.mean(r["final_avg_fitness"] for r in rs), 4),
            "gen_valid_pertama_rata2": round(st.mean(valid_gens), 1) if valid_gens else None,
            "gen_valid_pertama_sd": round(st.stdev(valid_gens), 1) if len(valid_gens) > 1 else None,
            "waktu_rata2_s": round(st.mean(r["time_s"] for r in rs), 3),
        })
    summary = pd.DataFrame(summ)
    summary.to_csv(os.path.join(args.out, "ringkasan_konfigurasi.csv"), index=False)

    # jadwal terbaik: fitness tertinggi, tie-break generasi valid paling awal
    all_res = [(name, r) for name, rs in results.items() for r in rs]
    name, best = max(all_res, key=lambda x: (x[1]["best_fitness"], -(x[1]["first_valid_gen"] or 10**9)))
    df = schedule_dataframe(problem, best["best_chrom"])
    tt = timetable_dataframe(df)
    out_df = df.drop(columns=["_day", "_slot"])
    out_df.to_csv(os.path.join(args.out, "jadwal_terbaik.csv"), index=False)
    tt.to_csv(os.path.join(args.out, "tabel_jadwal.csv"))
    with pd.ExcelWriter(os.path.join(args.out, "jadwal_terbaik.xlsx")) as xw:
        out_df.to_excel(xw, sheet_name="Daftar Sesi", index=False)
        tt.to_excel(xw, sheet_name="Tabel Hari x Slot")
        runs.to_excel(xw, sheet_name="Ringkasan Run", index=False)
        summary.to_excel(xw, sheet_name="Ringkasan Konfigurasi", index=False)

    # grafik konvergensi
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for cname, rs in results.items():
        n = len(rs[0]["best_hist"])
        mean_best = [st.mean(r["best_hist"][g] for r in rs) for g in range(n)]
        mean_avg = [st.mean(r["avg_hist"][g] for r in rs) for g in range(n)]
        axes[0].plot(mean_best, label=cname)
        axes[1].plot(mean_avg, label=cname)
    axes[0].set_title("Fitness terbaik (rata-rata 10 run)")
    axes[1].set_title("Fitness rata-rata populasi (rata-rata 10 run)")
    for ax in axes:
        ax.set_xlabel("Generasi"); ax.set_ylabel("Fitness"); ax.grid(alpha=0.3); ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(args.out, "konvergensi.png"), dpi=150)

    print(summary.to_string(index=False))
    print(f"\nJadwal terbaik dari konfigurasi {name}, seed {best['seed']}, fitness {best['best_fitness']:.4f}")
    print(f"Pelanggaran keras: {problem.hard_violations(best['best_chrom'])}")
    print(f"Kendala lunak    : {problem.soft_penalties(best['best_chrom'])}")
    print(f"File tersimpan di folder '{args.out}/'")


if __name__ == "__main__":
    main()

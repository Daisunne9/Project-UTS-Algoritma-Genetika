"""Algoritma Genetika dari nol (tanpa DEAP/PyGAD).

Operator: inisialisasi acak, seleksi roulette wheel & turnamen,
crossover satu titik & uniform, mutasi acak (reset gen), elitisme.
"""
import random
import time
from dataclasses import dataclass


@dataclass
class GAConfig:
    pop_size: int = 100
    generations: int = 200
    pc: float = 0.8            # probabilitas crossover
    pm: float = 0.05           # probabilitas mutasi per gen
    selection: str = "tournament"   # "tournament" | "roulette"
    crossover: str = "uniform"      # "uniform" | "one_point"
    tournament_k: int = 3
    elitism: int = 2

    def name(self):
        return f"{self.selection}+{self.crossover}"


# ---------------- operator ----------------
def init_population(problem, size, rng):
    return [[rng.randrange(problem.max_gene) for _ in range(problem.n_genes)] for _ in range(size)]


def roulette_select(pop, fits, rng):
    total = sum(fits)
    r = rng.uniform(0, total)
    acc = 0.0
    for ind, f in zip(pop, fits):
        acc += f
        if acc >= r:
            return ind
    return pop[-1]


def tournament_select(pop, fits, rng, k):
    idx = rng.sample(range(len(pop)), k)
    best = max(idx, key=lambda i: fits[i])
    return pop[best]


def one_point_crossover(p1, p2, rng):
    point = rng.randrange(1, len(p1))
    return p1[:point] + p2[point:], p2[:point] + p1[point:]


def uniform_crossover(p1, p2, rng):
    c1, c2 = [], []
    for a, b in zip(p1, p2):
        if rng.random() < 0.5:
            c1.append(a); c2.append(b)
        else:
            c1.append(b); c2.append(a)
    return c1, c2


def mutate(chrom, pm, max_gene, rng):
    return [rng.randrange(max_gene) if rng.random() < pm else g for g in chrom]


# ---------------- loop evolusi ----------------
def run_ga(problem, cfg, seed):
    rng = random.Random(seed)
    t0 = time.time()
    pop = init_population(problem, cfg.pop_size, rng)
    best_hist, avg_hist = [], []
    first_valid_gen = None
    best_ind, best_fit = None, -1.0

    for gen in range(cfg.generations):
        fits = [problem.fitness(ind) for ind in pop]
        gi = max(range(len(pop)), key=lambda i: fits[i])
        if fits[gi] > best_fit:
            best_fit, best_ind = fits[gi], list(pop[gi])
        best_hist.append(best_fit)
        avg_hist.append(sum(fits) / len(fits))
        if first_valid_gen is None and best_fit == 1.0:
            first_valid_gen = gen

        # elitisme: salin individu terbaik langsung ke generasi berikutnya
        order = sorted(range(len(pop)), key=lambda i: fits[i], reverse=True)
        new_pop = [list(pop[i]) for i in order[:cfg.elitism]]

        def select():
            if cfg.selection == "roulette":
                return roulette_select(pop, fits, rng)
            return tournament_select(pop, fits, rng, cfg.tournament_k)

        cross = uniform_crossover if cfg.crossover == "uniform" else one_point_crossover
        while len(new_pop) < cfg.pop_size:
            p1, p2 = select(), select()
            if rng.random() < cfg.pc:
                c1, c2 = cross(p1, p2, rng)
            else:
                c1, c2 = list(p1), list(p2)
            new_pop.append(mutate(c1, cfg.pm, problem.max_gene, rng))
            if len(new_pop) < cfg.pop_size:
                new_pop.append(mutate(c2, cfg.pm, problem.max_gene, rng))
        pop = new_pop

    return {
        "seed": seed,
        "best_chrom": best_ind,
        "best_fitness": best_fit,
        "final_avg_fitness": avg_hist[-1],
        "first_valid_gen": first_valid_gen,
        "best_hist": best_hist,
        "avg_hist": avg_hist,
        "time_s": time.time() - t0,
    }

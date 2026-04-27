# test_wordle_entropy.py
# Wordle entropy AI için toplu test dosyası
# 100 oyunu kendi kendine oynar ve her turda detaylı metrikleri terminale basar.
# Bu dosya, wordle.py ile aynı klasörde çalıştırılmalıdır.

import math
import time
from collections import Counter, defaultdict
from pathlib import Path

from wordle import WORDS, MAX_GUESSES, evaluate_guess

FIRST_GUESS = "SOARE"
N_GAMES = 100
OUTPUT_FILE = "wordle_entropy_test_results.txt"


class WordleEntropyTester:
    def __init__(self, words, output_file=OUTPUT_FILE):
        self.words = sorted(set(words))
        self.feedback_cache = {}
        self.cache_hits = 0
        self.cache_misses = 0
        self.output_file = Path(output_file)
        self.log_lines = []

    # -----------------------------
    # Logging helpers
    # -----------------------------
    def log(self, message=""):
        print(message)
        self.log_lines.append(message)

    def save_log_file(self):
        self.output_file.write_text("\n".join(self.log_lines), encoding="utf-8")

    # -----------------------------
    # Core helpers
    # -----------------------------
    def feedback_pattern(self, guess: str, target: str):
        key = (guess, target)
        if key in self.feedback_cache:
            self.cache_hits += 1
            return self.feedback_cache[key]

        self.cache_misses += 1
        pattern = tuple(evaluate_guess(guess, target))
        self.feedback_cache[key] = pattern
        return pattern

    def get_candidates(self, history):
        candidates = []
        for word in self.words:
            is_valid = True
            for past_guess, past_states in history:
                if self.feedback_pattern(past_guess, word) != tuple(past_states):
                    is_valid = False
                    break
            if is_valid:
                candidates.append(word)
        return candidates

    def entropy_score_with_stats(self, guess: str, candidates):
        buckets = defaultdict(int)
        comparisons = 0

        for target in candidates:
            pattern = self.feedback_pattern(guess, target)
            buckets[pattern] += 1
            comparisons += 1

        total = len(candidates)
        entropy = 0.0
        for count in buckets.values():
            p = count / total
            entropy -= p * math.log2(p)

        largest_bucket = max(buckets.values()) if buckets else 0
        return {
            "entropy": entropy,
            "bucket_count": len(buckets),
            "largest_bucket": largest_bucket,
            "comparisons": comparisons,
        }

    def best_entropy_guess(self, candidates):
        if not candidates:
            return None, None
        if len(candidates) == 1:
            return candidates[0], {
                "entropy": 0.0,
                "bucket_count": 1,
                "largest_bucket": 1,
                "comparisons": 0,
                "evaluated_guesses": 0,
                "candidate_count": 1,
                "total_comparisons": 0,
            }

        best_guess = None
        best_meta = None
        best_entropy = -1.0
        evaluated_guesses = 0
        total_comparisons = 0

        for guess in self.words:
            meta = self.entropy_score_with_stats(guess, candidates)
            evaluated_guesses += 1
            total_comparisons += meta["comparisons"]
            entropy = meta["entropy"]

            if entropy > best_entropy:
                best_entropy = entropy
                best_guess = guess
                best_meta = meta
            elif math.isclose(entropy, best_entropy, rel_tol=1e-12, abs_tol=1e-12):
                if best_guess is None:
                    best_guess = guess
                    best_meta = meta
                else:
                    guess_in_candidates = guess in candidates
                    best_in_candidates = best_guess in candidates
                    if guess_in_candidates and not best_in_candidates:
                        best_guess = guess
                        best_meta = meta
                    elif guess_in_candidates == best_in_candidates and guess < best_guess:
                        best_guess = guess
                        best_meta = meta

        best_meta = dict(best_meta)
        best_meta["evaluated_guesses"] = evaluated_guesses
        best_meta["candidate_count"] = len(candidates)
        best_meta["total_comparisons"] = total_comparisons
        return best_guess, best_meta

    # -----------------------------
    # Simulation
    # -----------------------------
    def play_one_game(self, answer: str, game_index: int):
        history = []
        solved = False
        per_turn = []
        game_start = time.perf_counter()

        self.log("=" * 90)
        self.log(f"OYUN {game_index:03d} | Hedef kelime: {answer}")
        self.log("=" * 90)

        for turn in range(1, MAX_GUESSES + 1):
            turn_start = time.perf_counter()
            cache_hits_before = self.cache_hits
            cache_misses_before = self.cache_misses

            if not history:
                guess = FIRST_GUESS
                selection_meta = {
                    "entropy": None,
                    "bucket_count": None,
                    "largest_bucket": None,
                    "evaluated_guesses": 0,
                    "candidate_count": len(self.words),
                    "total_comparisons": 0,
                }
                candidates_before = len(self.words)
            else:
                candidates = self.get_candidates(history)
                candidates_before = len(candidates)
                guess, selection_meta = self.best_entropy_guess(candidates)
                if guess is None:
                    turn_time = time.perf_counter() - turn_start
                    self.log(f"Tur {turn}: Tahmin üretilemedi | süre={turn_time:.6f}s")
                    per_turn.append({
                        "turn": turn,
                        "guess": None,
                        "states": None,
                        "candidates_before": candidates_before,
                        "candidates_after": 0,
                        "turn_time": turn_time,
                        "selection_meta": selection_meta,
                        "cache_hits": self.cache_hits - cache_hits_before,
                        "cache_misses": self.cache_misses - cache_misses_before,
                    })
                    break

            states = tuple(evaluate_guess(guess, answer))
            history.append((guess, states))
            candidates_after = len(self.get_candidates(history))

            turn_time = time.perf_counter() - turn_start
            cache_hits_delta = self.cache_hits - cache_hits_before
            cache_misses_delta = self.cache_misses - cache_misses_before
            cpu_work_estimate = selection_meta["total_comparisons"]

            turn_record = {
                "turn": turn,
                "guess": guess,
                "states": states,
                "candidates_before": candidates_before,
                "candidates_after": candidates_after,
                "turn_time": turn_time,
                "selection_meta": selection_meta,
                "cache_hits": cache_hits_delta,
                "cache_misses": cache_misses_delta,
                "cpu_work_estimate": cpu_work_estimate,
            }
            per_turn.append(turn_record)

            state_str = ",".join(states)
            entropy_str = (
                "N/A" if selection_meta["entropy"] is None
                else f"{selection_meta['entropy']:.6f}"
            )
            bucket_str = "N/A" if selection_meta["bucket_count"] is None else str(selection_meta["bucket_count"])
            largest_bucket_str = "N/A" if selection_meta["largest_bucket"] is None else str(selection_meta["largest_bucket"])

            self.log(
                f"Tur {turn} | guess={guess} | states=[{state_str}] | "
                f"aday önce={candidates_before} | aday sonra={candidates_after} | "
                f"süre={turn_time:.6f}s | entropy={entropy_str} | "
                f"bucket={bucket_str} | max_bucket={largest_bucket_str} | "
                f"guess_eval={selection_meta['evaluated_guesses']} | "
                f"hesap_yuku≈{cpu_work_estimate} pattern karşılaştırması | "
                f"cache_hit={cache_hits_delta} | cache_miss={cache_misses_delta}"
            )

            if guess == answer:
                solved = True
                break

        game_time = time.perf_counter() - game_start
        total_guesses = len(per_turn)
        avg_turn_time = sum(t["turn_time"] for t in per_turn) / total_guesses if total_guesses else 0.0
        total_cpu_work = sum(t.get("cpu_work_estimate", 0) for t in per_turn)

        self.log("-" * 90)
        self.log(
            f"OYUN SONUCU | solved={solved} | deneme_sayısı={total_guesses} | "
            f"toplam_süre={game_time:.6f}s | ort_tur_süresi={avg_turn_time:.6f}s | "
            f"toplam_hesap_yuku≈{total_cpu_work} pattern karşılaştırması"
        )
        self.log()

        return {
            "answer": answer,
            "solved": solved,
            "guesses_used": total_guesses,
            "game_time": game_time,
            "avg_turn_time": avg_turn_time,
            "total_cpu_work": total_cpu_work,
            "turns": per_turn,
        }

    def run_batch(self, n_games=100):
        results = []

        # Deterministic test için sözlük sırasına göre hedef seçiliyor.
        for game_index in range(1, n_games + 1):
            answer = self.words[(game_index - 1) % len(self.words)]
            result = self.play_one_game(answer, game_index)
            results.append(result)

        self.print_summary(results)
        self.log()
        self.log(f"Sonuçlar dosyaya kaydedildi: {self.output_file.resolve()}")
        self.save_log_file()
        return results

    # -----------------------------
    # Summary
    # -----------------------------
    def print_summary(self, results):
        total_games = len(results)
        solved_games = sum(1 for r in results if r["solved"])
        failed_games = total_games - solved_games
        total_guesses = sum(r["guesses_used"] for r in results)
        total_time = sum(r["game_time"] for r in results)
        total_cpu_work = sum(r["total_cpu_work"] for r in results)

        guesses_distribution = Counter(r["guesses_used"] for r in results if r["solved"])
        all_turns = [turn for r in results for turn in r["turns"]]
        avg_turn_time = sum(t["turn_time"] for t in all_turns) / len(all_turns) if all_turns else 0.0
        max_turn_time = max((t["turn_time"] for t in all_turns), default=0.0)
        avg_candidates_before = (
            sum(t["candidates_before"] for t in all_turns) / len(all_turns)
            if all_turns else 0.0
        )

        self.log("#" * 90)
        self.log("GENEL ÖZET")
        self.log("#" * 90)
        self.log(f"Toplam oyun: {total_games}")
        self.log(f"Çözülen oyun: {solved_games}")
        self.log(f"Çözülemeyen oyun: {failed_games}")
        self.log(f"Başarı oranı: {solved_games / total_games * 100:.2f}%")
        self.log(f"Ortalama deneme sayısı: {total_guesses / total_games:.4f}")
        self.log(f"Toplam süre: {total_time:.6f}s")
        self.log(f"Ortalama oyun süresi: {total_time / total_games:.6f}s")
        self.log(f"Ortalama tur süresi: {avg_turn_time:.6f}s")
        self.log(f"Maksimum tek tur süresi: {max_turn_time:.6f}s")
        self.log(f"Ortalama aday sayısı (tur başı): {avg_candidates_before:.2f}")
        self.log(f"Toplam hesap yükü≈ {total_cpu_work} pattern karşılaştırması")
        self.log(f"Toplam cache hit: {self.cache_hits}")
        self.log(f"Toplam cache miss: {self.cache_misses}")
        hit_rate = self.cache_hits / (self.cache_hits + self.cache_misses) * 100 if (self.cache_hits + self.cache_misses) else 0.0
        self.log(f"Cache hit oranı: {hit_rate:.2f}%")
        self.log("Çözüm dağılımı (kaç denemede bulundu):")
        for guesses_used in sorted(guesses_distribution):
            self.log(f"  {guesses_used} deneme: {guesses_distribution[guesses_used]} oyun")


def main():
    tester = WordleEntropyTester(WORDS)
    tester.run_batch(N_GAMES)


if __name__ == "__main__":
    main()

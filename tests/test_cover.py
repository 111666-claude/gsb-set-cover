import io
import itertools
import random
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout

from setcover.cli import main
from setcover.cover import CoverError, exact_cover, greedy, parse_sets, total_cost, universe_of


def run_cli(argv):
    out = io.StringIO()
    err = io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


def brute_force(sets, universe):
    """枚举所有子集取最小成本，成本相同按集合名字典序取最小。"""
    universe_set = set(universe)
    best = None
    for mask in range(1 << len(sets)):
        covered = set()
        cost = 0
        chosen = []
        for i, (name, set_cost, elements) in enumerate(sets):
            if mask >> i & 1:
                covered.update(elements)
                cost += set_cost
                chosen.append(name)
        if covered >= universe_set:
            key = (cost, sorted(chosen))
            if best is None or key < best:
                best = key
    return best


class ParseTest(unittest.TestCase):
    def test_two_sets(self):
        self.assertEqual(
            parse_sets("a=2:1,2;b=1:3"),
            [("a", 2, ["1", "2"]), ("b", 1, ["3"])],
        )

    def test_blank_items_are_skipped(self):
        self.assertEqual(parse_sets("a=1:1;"), [("a", 1, ["1"])])

    def test_duplicate_elements_ignored(self):
        self.assertEqual(parse_sets("a=1:1,1,2,2,1"), [("a", 1, ["1", "2"])])

    def test_bad_cost(self):
        with self.assertRaises((ValueError, CoverError)):
            parse_sets("a=x:1")

    def test_cost_not_a_number_reports_index(self):
        with self.assertRaises(CoverError) as ctx:
            parse_sets("a=1:1;b=x:2")
        self.assertIn("第 2 项", str(ctx.exception))

    def test_cost_must_be_positive(self):
        for text in ("a=0:1", "a=-3:1"):
            with self.assertRaises(CoverError) as ctx:
                parse_sets(text)
            self.assertIn("第 1 项", str(ctx.exception))

    def test_missing_equals(self):
        with self.assertRaises(CoverError) as ctx:
            parse_sets("a=1:1;b2:3")
        self.assertIn("第 2 项", str(ctx.exception))

    def test_missing_colon(self):
        with self.assertRaises(CoverError) as ctx:
            parse_sets("ok=1:1;bad=2")
        self.assertIn("第 2 项", str(ctx.exception))

    def test_empty_name(self):
        with self.assertRaises(CoverError) as ctx:
            parse_sets("=1:1")
        self.assertIn("第 1 项", str(ctx.exception))

    def test_duplicate_name(self):
        with self.assertRaises(CoverError) as ctx:
            parse_sets("a=1:1;b=1:2;a=2:3")
        self.assertIn("第 3 项", str(ctx.exception))


class UniverseTest(unittest.TestCase):
    def test_first_appearance_order(self):
        self.assertEqual(universe_of(parse_sets("a=1:3,1;b=1:2")), ["3", "1", "2"])


class GreedyTest(unittest.TestCase):
    def test_single_set(self):
        sets = parse_sets("a=1:1")
        chosen = greedy(sets, ["1"])
        self.assertEqual(chosen, ["a"])
        self.assertEqual(total_cost(sets, chosen), 1)

    def test_two_singletons(self):
        sets = parse_sets("a=1:1;b=1:2")
        chosen = greedy(sets, ["1", "2"])
        self.assertEqual(sorted(chosen), ["a", "b"])

    def test_cost_ratio_beats_element_count(self):
        sets = parse_sets("a=2:1,2;b=2:3,4;c=5:1,2,3,4")
        chosen = greedy(sets, ["1", "2", "3", "4"])
        self.assertEqual(sorted(chosen), ["a", "b"])
        self.assertEqual(total_cost(sets, chosen), 4)

    def test_ratio_tie_breaks_by_name(self):
        sets = parse_sets("b=2:1;a=2:1")
        self.assertEqual(greedy(sets, ["1"]), ["a"])

    def test_uncovered_raises_with_elements(self):
        sets = parse_sets("a=1:1")
        with self.assertRaises(CoverError) as ctx:
            greedy(sets, ["1", "2"])
        self.assertIn("2", str(ctx.exception))

    def test_deterministic(self):
        sets = parse_sets("a=2:1,2;b=2:3,4;c=5:1,2,3,4")
        self.assertEqual(greedy(sets, ["1", "2", "3", "4"]), greedy(sets, ["1", "2", "3", "4"]))


class ExactTest(unittest.TestCase):
    def test_minimum_cost(self):
        sets = parse_sets("a=2:1,2;b=2:3,4;c=5:1,2,3,4")
        chosen = exact_cover(sets, ["1", "2", "3", "4"])
        self.assertEqual(sorted(chosen), ["a", "b"])
        self.assertEqual(total_cost(sets, chosen), 4)

    def test_tie_breaks_by_sorted_names(self):
        sets = parse_sets("b=1:1;a=1:1")
        self.assertEqual(exact_cover(sets, ["1"]), ["a"])

    def test_uncovered_raises_with_elements(self):
        sets = parse_sets("a=1:1")
        with self.assertRaises(CoverError) as ctx:
            exact_cover(sets, ["1", "2"])
        self.assertIn("2", str(ctx.exception))

    def test_too_many_sets(self):
        sets = [("s%d" % i, 1, [str(i)]) for i in range(17)]
        with self.assertRaises(CoverError):
            exact_cover(sets, [str(i) for i in range(17)])

    def test_empty_universe(self):
        self.assertEqual(exact_cover(parse_sets("a=1:1"), []), [])


class ExactVsBruteForceTest(unittest.TestCase):
    def random_instance(self, rng, count):
        pool = ["e%d" % i for i in range(rng.randint(2, 8))]
        sets = []
        for i in range(count):
            elements = [e for e in pool if rng.random() < 0.4]
            sets.append(("s%02d" % i, rng.randint(1, 9), elements))
        return sets, universe_of(sets)

    def check(self, sets, universe):
        expected = brute_force(sets, universe)
        chosen = exact_cover(sets, universe)
        self.assertIsNotNone(expected)
        self.assertEqual((total_cost(sets, chosen), sorted(chosen)), expected)

    def test_matches_brute_force_small(self):
        rng = random.Random(20260928)
        for _ in range(60):
            sets, universe = self.random_instance(rng, rng.randint(1, 12))
            self.check(sets, universe)

    def test_matches_brute_force_at_16(self):
        rng = random.Random(121)
        for _ in range(3):
            sets, universe = self.random_instance(rng, 16)
            self.check(sets, universe)


class InvariantTest(unittest.TestCase):
    def check_invariants(self, sets, universe, chosen):
        covered = set()
        costs = {}
        for name, cost, elements in sets:
            costs[name] = cost
        for name in chosen:
            covered.update(dict((n, e) for n, _, e in sets)[name])
        self.assertEqual(covered, set(universe))
        self.assertEqual(total_cost(sets, chosen), sum(costs[n] for n in chosen))

    def test_greedy_and_exact_invariants(self):
        rng = random.Random(7)
        for _ in range(20):
            pool = ["e%d" % i for i in range(6)]
            sets = [("s%d" % i, rng.randint(1, 9), [e for e in pool if rng.random() < 0.5]) for i in range(8)]
            universe = universe_of(sets)
            for chosen in (greedy(sets, universe), exact_cover(sets, universe)):
                self.check_invariants(sets, universe, chosen)
            self.assertEqual(greedy(sets, universe), greedy(sets, universe))
            self.assertEqual(exact_cover(sets, universe), exact_cover(sets, universe))


class PerformanceTest(unittest.TestCase):
    def test_greedy_5000_sets_100k_elements(self):
        rng = random.Random(3)
        elements = ["e%d" % i for i in range(100000)]
        sets = []
        for i in range(5000):
            cover = elements[20 * i:20 * i + 20] + rng.sample(elements, 5)
            sets.append(("s%04d" % i, rng.randint(1, 9), cover))
        start = time.monotonic()
        chosen = greedy(sets, elements)
        elapsed = time.monotonic() - start
        self.assertLess(elapsed, 1.0)
        covered = set()
        for name, _, cover in sets:
            if name in set(chosen):
                covered.update(cover)
        self.assertEqual(covered, set(elements))


class CliTest(unittest.TestCase):
    def test_single_set_output(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["--sets", "a=1:1", "--universe", "1"])
        self.assertEqual(code, 0)
        self.assertEqual(buffer.getvalue().split(), ["cost=1", "sets=a"])

    def test_missing_sets(self):
        self.assertEqual(main([]), 2)

    def test_greedy_readme_sample(self):
        code, out, _ = run_cli(["--sets", "a=2:1,2;b=2:3,4;c=5:1,2,3,4", "--universe", "1,2,3,4"])
        self.assertEqual(code, 0)
        self.assertEqual(out.split(), ["cost=4", "sets=a,b"])

    def test_exact_readme_sample(self):
        code, out, _ = run_cli(["--sets", "a=2:1,2;b=2:3,4", "--universe", "1,2,3,4", "--exact"])
        self.assertEqual(code, 0)
        self.assertEqual(out.split(), ["cost=4", "sets=a,b"])

    def test_uncovered_reports_element(self):
        code, _, err = run_cli(["--sets", "a=1:1", "--universe", "1,2"])
        self.assertEqual(code, 1)
        self.assertIn("2", err)

    def test_bad_input_reports_item(self):
        code, _, err = run_cli(["--sets", "a=1:1;b=x:2"])
        self.assertEqual(code, 1)
        self.assertIn("第 2 项", err)


if __name__ == "__main__":
    unittest.main()

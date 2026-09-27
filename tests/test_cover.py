import io
import unittest
from contextlib import redirect_stdout

from setcover.cli import main
from setcover.cover import CoverError, greedy, parse_sets, total_cost, universe_of


class ParseTest(unittest.TestCase):
    def test_two_sets(self):
        self.assertEqual(
            parse_sets("a=2:1,2;b=1:3"),
            [("a", 2, ["1", "2"]), ("b", 1, ["3"])],
        )

    def test_blank_items_are_skipped(self):
        self.assertEqual(parse_sets("a=1:1;"), [("a", 1, ["1"])])

    def test_bad_cost(self):
        with self.assertRaises((ValueError, CoverError)):
            parse_sets("a=x:1")


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


class CliTest(unittest.TestCase):
    def test_single_set_output(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["--sets", "a=1:1", "--universe", "1"])
        self.assertEqual(code, 0)
        self.assertEqual(buffer.getvalue().split(), ["cost=1", "sets=a"])

    def test_missing_sets(self):
        self.assertEqual(main([]), 2)


if __name__ == "__main__":
    unittest.main()

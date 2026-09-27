"""命令行入口：覆盖集合、打印成本与所选集合。"""

import argparse
import sys

from .cover import CoverError, exact_cover, greedy, parse_sets, total_cost, universe_of


def build_parser():
    parser = argparse.ArgumentParser(prog="set-cover", description="带成本的集合覆盖")
    parser.add_argument("--sets", help="分号分隔的 名字=成本:元素,元素")
    parser.add_argument("--universe", help="全集，逗号分隔；默认取所有元素的并集")
    parser.add_argument("--exact", action="store_true", help="求最小成本覆盖")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if not args.sets:
        print("错误：需要 --sets", file=sys.stderr)
        return 2
    try:
        sets = parse_sets(args.sets)
        if args.universe:
            universe = [part.strip() for part in args.universe.split(",") if part.strip()]
        else:
            universe = universe_of(sets)
        names = exact_cover(sets, universe) if args.exact else greedy(sets, universe)
        names = sorted(names)
        print("cost=%d" % total_cost(sets, names))
        print("sets=%s" % ",".join(names))
    except (CoverError, ValueError) as error:
        print("错误：%s" % error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

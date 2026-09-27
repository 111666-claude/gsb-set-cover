"""集合覆盖：解析校验、堆优化贪心、分支限界精确解。只用标准库。"""

import heapq
from fractions import Fraction


class CoverError(Exception):
    """输入不合法或无法覆盖全集。"""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


def parse_sets(text):
    """解析 "a=2:1,2;b=1:3"，逐项校验，元素去重（保留首次出现顺序）。"""
    parsed = []
    seen_names = set()
    for index, item in enumerate(text.split(";"), start=1):
        item = item.strip()
        if not item:
            continue
        if "=" not in item:
            raise CoverError("第 %d 项 %r：缺少 '='" % (index, item))
        name, _, rest = item.partition("=")
        name = name.strip()
        if not name:
            raise CoverError("第 %d 项：集合名为空" % index)
        if name in seen_names:
            raise CoverError("第 %d 项：集合名 %r 重复" % (index, name))
        if ":" not in rest:
            raise CoverError("第 %d 项：缺少 ':'" % index)
        cost_text, _, elements_text = rest.partition(":")
        cost_text = cost_text.strip()
        if not cost_text.isascii() or not cost_text.isdigit():
            raise CoverError("第 %d 项：成本 %r 不是正整数" % (index, cost_text))
        cost = int(cost_text)
        if cost <= 0:
            raise CoverError("第 %d 项：成本必须是正整数" % index)
        elements = []
        seen_elements = set()
        for part in elements_text.split(","):
            part = part.strip()
            if part and part not in seen_elements:
                seen_elements.add(part)
                elements.append(part)
        seen_names.add(name)
        parsed.append((name, cost, elements))
    return parsed


def universe_of(sets):
    """按第一次出现的顺序收集所有元素。"""
    seen = set()
    order = []
    for _, _, elements in sets:
        for element in elements:
            if element not in seen:
                seen.add(element)
                order.append(element)
    return order


def _uncovered_error(remaining):
    return CoverError("无法覆盖全集，未覆盖元素：%s" % ",".join(sorted(remaining)))


def greedy(sets, universe):
    """每轮挑「成本 ÷ 新增覆盖元素数」最小的集合，等价按名字字典序。

    用堆做懒删除：集合的新增覆盖只会减少，比率只会变大，
    弹出的过期条目重算后放回，不必每轮重扫全部集合。
    """
    remaining = set(universe)
    pool = []
    for name, cost, elements in sets:
        cover = frozenset(elements) & remaining
        if cover:
            heapq.heappush(pool, (Fraction(cost, len(cover)), name, cost, cover, len(cover)))
    chosen = []
    while remaining:
        if not pool:
            raise _uncovered_error(remaining)
        _, name, cost, cover, gain = heapq.heappop(pool)
        fresh = cover & remaining
        if len(fresh) == gain:
            chosen.append(name)
            remaining -= fresh
        elif fresh:
            heapq.heappush(pool, (Fraction(cost, len(fresh)), name, cost, frozenset(fresh), len(fresh)))
    return chosen


def exact_cover(sets, universe):
    """分支限界求最小成本覆盖；成本相同按集合名字典序取最小的一组。"""
    universe_set = set(universe)
    covered = set()
    for _, _, elements in sets:
        covered.update(elements)
    missing = universe_set - covered
    if missing:
        raise _uncovered_error(missing)
    if len(sets) > 16:
        raise CoverError("精确解只支持不超过 16 个集合，当前 %d 个" % len(sets))
    if not universe_set:
        return []

    names = [name for name, _, _ in sets]
    costs = [cost for _, cost, _ in sets]
    covers = [set(elements) & universe_set for _, _, elements in sets]
    count = len(sets)
    index_of = {name: i for i, name in enumerate(names)}

    element_to_sets = {}
    for index, cover in enumerate(covers):
        for element in cover:
            element_to_sets.setdefault(element, []).append(index)

    # 先用贪心拿一个上界，加速剪枝。
    greedy_names = sorted(greedy(sets, universe))
    best = {"cost": sum(costs[index_of[name]] for name in greedy_names), "names": greedy_names}

    def search(remaining, chosen_cost, chosen_names):
        if not remaining:
            candidate = sorted(chosen_names)
            if chosen_cost < best["cost"] or (chosen_cost == best["cost"] and candidate < best["names"]):
                best["cost"] = chosen_cost
                best["names"] = candidate
            return
        if chosen_cost >= best["cost"]:
            return
        useful = [i for i in range(count) if covers[i] & remaining]
        min_cost = min(costs[i] for i in useful)
        max_gain = max(len(covers[i] & remaining) for i in useful)
        need = -(-len(remaining) // max_gain)
        if chosen_cost + need * min_cost > best["cost"]:
            return
        element = min(remaining, key=lambda e: (len(element_to_sets[e]), e))
        candidates = sorted(
            element_to_sets[element],
            key=lambda i: (Fraction(costs[i], len(covers[i] & remaining)), names[i]),
        )
        for i in candidates:
            search(remaining - covers[i], chosen_cost + costs[i], chosen_names + [names[i]])

    search(set(universe_set), 0, [])
    return best["names"]


def total_cost(sets, names):
    """所选集合的成本之和。"""
    costs = {}
    for name, cost, _ in sets:
        costs[name] = cost
    return sum(costs[name] for name in names)

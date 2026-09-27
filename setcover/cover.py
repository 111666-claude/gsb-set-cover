"""集合覆盖。只用标准库。缺陷：贪心不看成本，精确解没实现。"""


class CoverError(Exception):
    """输入不合法。缺陷：不带集合下标。"""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


def parse_sets(text):
    """解析 "a=2:1,2;b=1:3"。缺陷：不查重、不校验成本。"""
    parsed = []
    for item in text.split(";"):
        item = item.strip()
        if not item:
            continue
        name, _, rest = item.partition("=")
        cost_text, _, elements = rest.partition(":")
        parsed.append((name.strip(), int(cost_text), [part.strip() for part in elements.split(",") if part.strip()]))
    return parsed


def universe_of(sets):
    """按第一次出现的顺序收集所有元素。"""
    seen = []
    for _, _, elements in sets:
        for element in elements:
            if element not in seen:
                seen.append(element)
    return seen


def greedy(sets, universe):
    """缺陷：每轮只看覆盖了几个未覆盖元素，成本完全不看。"""
    remaining = set(universe)
    chosen = []
    while remaining:
        best = None
        for name, cost, elements in sets:
            gain = len(set(elements) & remaining)
            if gain == 0:
                continue
            if best is None or gain > best[0]:
                best = (gain, name, cost, elements)
        if best is None:
            break
        _, name, _, elements = best
        chosen.append(name)
        remaining -= set(elements)
    return chosen


def exact_cover(sets, universe):
    """缺陷：还没实现。"""
    raise CoverError("精确解还没实现")


def total_cost(sets, names):
    """所选集合的成本之和。"""
    costs = {}
    for name, cost, _ in sets:
        costs[name] = cost
    return sum(costs[name] for name in names)

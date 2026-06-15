# Round 13 — final push to 10k
from typing import Optional, List
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, validator

Base = declarative_base()

class Paste(Base):
    __tablename__ = "pastes"
    id = Column(Integer, primary_key=True)
    short_code = Column(String(8), unique=True, index=True)
    title = Column(String(200), nullable=True)
    content = Column(Text, nullable=False)
    language = Column(String(50), default="plaintext")
    password_hash = Column(String(200), nullable=True)
    views = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

class PasteCreate(BaseModel):
    title: Optional[str] = None
    content: str
    language: str = "plaintext"
    password: Optional[str] = None
    expiry: str = "never"
    class Config:
        str_strip_whitespace = True
    @validator("content")
    def content_not_empty(cls, v):
        if not v.strip():
            raise ValueError("content cannot be empty")
        return v

class PasteOut(BaseModel):
    short_code: str
    title: Optional[str]
    content: str
    language: str
    views: int
    created_at: datetime
    expires_at: Optional[datetime]
    class Config:
        from_attributes = True

SEED_PASTES = [
    (
        "R13_001",
        "python",
        "Trie Data Structure",
        "class TrieNode:\n    def __init__(self): self.children = {}; self.is_end = False\nclass Trie:\n    def __init__(self): self.root = TrieNode()\n    def insert(self, word):\n        node = self.root\n        for c in word: node = node.children.setdefault(c, TrieNode())\n        node.is_end = True\n    def search(self, word):\n        node = self.root\n        for c in word:\n            if c not in node.children: return False\n            node = node.children[c]\n        return node.is_end\n    def starts_with(self, prefix):\n        node = self.root\n        for c in prefix:\n            if c not in node.children: return False\n            node = node.children[c]\n        return True",
    ),
    (
        "R13_002",
        "python",
        "Segment Tree",
        "class SegmentTree:\n    def __init__(self, nums):\n        self.n = len(nums)\n        self.tree = [0] * (2 * self.n)\n        for i in range(self.n): self.tree[self.n + i] = nums[i]\n        for i in range(self.n - 1, 0, -1): self.tree[i] = self.tree[2*i] + self.tree[2*i+1]\n    def update(self, i, val):\n        i += self.n\n        self.tree[i] = val\n        while i > 1:\n            i //= 2\n            self.tree[i] = self.tree[2*i] + self.tree[2*i+1]\n    def query(self, l, r):\n        l += self.n; r += self.n + 1\n        res = 0\n        while l < r:\n            if l & 1: res += self.tree[l]; l += 1\n            if r & 1: r -= 1; res += self.tree[r]\n            l >>= 1; r >>= 1\n        return res",
    ),
    (
        "R13_003",
        "python",
        "Union Find",
        "class UnionFind:\n    def __init__(self, n):\n        self.parent = list(range(n))\n        self.rank = [0] * n\n        self.components = n\n    def find(self, x):\n        if self.parent[x] != x:\n            self.parent[x] = self.find(self.parent[x])\n        return self.parent[x]\n    def union(self, x, y):\n        px, py = self.find(x), self.find(y)\n        if px == py: return False\n        if self.rank[px] < self.rank[py]: px, py = py, px\n        self.parent[py] = px\n        if self.rank[px] == self.rank[py]: self.rank[px] += 1\n        self.components -= 1\n        return True\n    def connected(self, x, y): return self.find(x) == self.find(y)",
    ),
    (
        "R13_004",
        "python",
        "Fenwick Tree",
        "class BIT:\n    def __init__(self, n):\n        self.n = n\n        self.tree = [0] * (n + 1)\n    def update(self, i, delta):\n        while i <= self.n:\n            self.tree[i] += delta\n            i += i & (-i)\n    def prefix_sum(self, i):\n        total = 0\n        while i > 0:\n            total += self.tree[i]\n            i -= i & (-i)\n        return total\n    def range_sum(self, l, r): return self.prefix_sum(r) - self.prefix_sum(l - 1)",
    ),
    (
        "R13_005",
        "python",
        "KMP String Search",
        "def kmp_search(text, pattern):\n    def build_lps(p):\n        lps = [0] * len(p)\n        length = 0; i = 1\n        while i < len(p):\n            if p[i] == p[length]: length += 1; lps[i] = length; i += 1\n            elif length: length = lps[length-1]\n            else: lps[i] = 0; i += 1\n        return lps\n    lps = build_lps(pattern)\n    matches = []; j = 0\n    for i, c in enumerate(text):\n        while j > 0 and c != pattern[j]: j = lps[j-1]\n        if c == pattern[j]: j += 1\n        if j == len(pattern): matches.append(i - j + 1); j = lps[j-1]\n    return matches",
    ),
    (
        "R13_006",
        "python",
        "Topological Sort",
        "from collections import deque\ndef topo_sort(n, edges):\n    graph = [[] for _ in range(n)]\n    in_degree = [0] * n\n    for u, v in edges:\n        graph[u].append(v)\n        in_degree[v] += 1\n    queue = deque(i for i in range(n) if in_degree[i] == 0)\n    order = []\n    while queue:\n        node = queue.popleft()\n        order.append(node)\n        for nei in graph[node]:\n            in_degree[nei] -= 1\n            if in_degree[nei] == 0: queue.append(nei)\n    return order if len(order) == n else []  # empty = cycle",
    ),
    (
        "R13_007",
        "python",
        "Bellman-Ford",
        "def bellman_ford(n, edges, src):\n    dist = [float('inf')] * n\n    dist[src] = 0\n    for _ in range(n - 1):\n        for u, v, w in edges:\n            if dist[u] + w < dist[v]:\n                dist[v] = dist[u] + w\n    for u, v, w in edges:\n        if dist[u] + w < dist[v]:\n            return None  # negative cycle\n    return dist",
    ),
    (
        "R13_008",
        "python",
        "Floyd Warshall",
        "def floyd_warshall(graph):\n    n = len(graph)\n    dist = [row[:] for row in graph]\n    for k in range(n):\n        for i in range(n):\n            for j in range(n):\n                if dist[i][k] + dist[k][j] < dist[i][j]:\n                    dist[i][j] = dist[i][k] + dist[k][j]\n    return dist",
    ),
    (
        "R13_009",
        "python",
        "Knapsack 0/1",
        "def knapsack(weights, values, capacity):\n    n = len(weights)\n    dp = [[0] * (capacity + 1) for _ in range(n + 1)]\n    for i in range(1, n + 1):\n        for w in range(capacity + 1):\n            dp[i][w] = dp[i-1][w]\n            if weights[i-1] <= w:\n                dp[i][w] = max(dp[i][w], dp[i-1][w-weights[i-1]] + values[i-1])\n    return dp[n][capacity]",
    ),
    (
        "R13_010",
        "python",
        "Minimum Spanning Tree Kruskal",
        "def kruskal(n, edges):\n    edges.sort(key=lambda x: x[2])\n    uf = UnionFind(n)\n    mst_cost = 0; mst_edges = []\n    for u, v, w in edges:\n        if uf.union(u, v):\n            mst_cost += w\n            mst_edges.append((u, v, w))\n        if len(mst_edges) == n - 1: break\n    return mst_cost, mst_edges",
    ),
    (
        "R13_011",
        "python",
        "Prim's MST",
        "import heapq\ndef prim(n, graph):\n    visited = [False] * n\n    heap = [(0, 0)]  # (weight, node)\n    total = 0\n    while heap:\n        w, u = heapq.heappop(heap)\n        if visited[u]: continue\n        visited[u] = True\n        total += w\n        for v, weight in graph[u]:\n            if not visited[v]:\n                heapq.heappush(heap, (weight, v))\n    return total",
    ),
    (
        "R13_012",
        "python",
        "Articulation Points",
        "def find_articulation_points(graph, n):\n    visited = [False] * n\n    disc = [0] * n; low = [0] * n\n    parent = [-1] * n; ap = set()\n    timer = [0]\n    def dfs(u):\n        children = 0\n        visited[u] = True\n        disc[u] = low[u] = timer[0]; timer[0] += 1\n        for v in graph[u]:\n            if not visited[v]:\n                children += 1; parent[v] = u; dfs(v)\n                low[u] = min(low[u], low[v])\n                if parent[u] == -1 and children > 1: ap.add(u)\n                if parent[u] != -1 and low[v] >= disc[u]: ap.add(u)\n            elif v != parent[u]: low[u] = min(low[u], disc[v])\n    for i in range(n):\n        if not visited[i]: dfs(i)\n    return ap",
    ),
    (
        "R13_013",
        "python",
        "Maximum Flow Ford-Fulkerson",
        "from collections import defaultdict, deque\ndef max_flow(graph, source, sink):\n    def bfs(parent):\n        visited = {source}\n        queue = deque([source])\n        while queue:\n            u = queue.popleft()\n            for v in graph[u]:\n                if v not in visited and graph[u][v] > 0:\n                    visited.add(v); parent[v] = u\n                    if v == sink: return True\n                    queue.append(v)\n        return False\n    flow = 0\n    while True:\n        parent = {}\n        if not bfs(parent): break\n        path_flow = float('inf')\n        v = sink\n        while v != source: u = parent[v]; path_flow = min(path_flow, graph[u][v]); v = u\n        v = sink\n        while v != source: u = parent[v]; graph[u][v] -= path_flow; graph[v][u] += path_flow; v = u\n        flow += path_flow\n    return flow",
    ),
    (
        "R13_014",
        "python",
        "Convex Hull Graham Scan",
        "def cross(O, A, B): return (A[0]-O[0])*(B[1]-O[1]) - (A[1]-O[1])*(B[0]-O[0])\ndef convex_hull(points):\n    points = sorted(set(points))\n    if len(points) <= 1: return points\n    lower = []\n    for p in points:\n        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0: lower.pop()\n        lower.append(p)\n    upper = []\n    for p in reversed(points):\n        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0: upper.pop()\n        upper.append(p)\n    return lower[:-1] + upper[:-1]",
    ),
    (
        "R13_015",
        "python",
        "Rabin Karp Rolling Hash",
        "def rabin_karp(text, pattern):\n    BASE, MOD = 31, 10**9+7\n    n, m = len(text), len(pattern)\n    if m > n: return []\n    def char_val(c): return ord(c) - ord('a') + 1\n    pat_hash = sum(char_val(pattern[i]) * pow(BASE, i, MOD) for i in range(m)) % MOD\n    window = sum(char_val(text[i]) * pow(BASE, i, MOD) for i in range(m)) % MOD\n    matches = []\n    inv_base = pow(BASE, MOD-2, MOD)\n    for i in range(n - m + 1):\n        if window == pat_hash and text[i:i+m] == pattern: matches.append(i)\n        if i + m < n:\n            window = (window - char_val(text[i])) * inv_base % MOD\n            window = (window + char_val(text[i+m]) * pow(BASE, m-1, MOD)) % MOD\n    return matches",
    ),
    (
        "R13_016",
        "python",
        "Matrix Chain Multiplication",
        "def matrix_chain_order(dims):\n    n = len(dims) - 1\n    dp = [[0]*n for _ in range(n)]\n    for length in range(2, n+1):\n        for i in range(n - length + 1):\n            j = i + length - 1\n            dp[i][j] = float('inf')\n            for k in range(i, j):\n                cost = dp[i][k] + dp[k+1][j] + dims[i]*dims[k+1]*dims[j+1]\n                dp[i][j] = min(dp[i][j], cost)\n    return dp[0][n-1]",
    ),
    (
        "R13_017",
        "python",
        "Bridges in Graph",
        "def find_bridges(graph, n):\n    visited = [False]*n; disc = [0]*n; low = [0]*n\n    parent = [-1]*n; bridges = []\n    timer = [0]\n    def dfs(u):\n        visited[u] = True\n        disc[u] = low[u] = timer[0]; timer[0] += 1\n        for v in graph[u]:\n            if not visited[v]:\n                parent[v] = u; dfs(v)\n                low[u] = min(low[u], low[v])\n                if low[v] > disc[u]: bridges.append((u, v))\n            elif v != parent[u]: low[u] = min(low[u], disc[v])\n    for i in range(n):\n        if not visited[i]: dfs(i)\n    return bridges",
    ),
    (
        "R13_018",
        "python",
        "Longest Increasing Subsequence",
        "import bisect\ndef lis(nums):\n    tails = []\n    for num in nums:\n        pos = bisect.bisect_left(tails, num)\n        if pos == len(tails): tails.append(num)\n        else: tails[pos] = num\n    return len(tails)\ndef lis_sequence(nums):\n    n = len(nums)\n    dp = [1]*n; parent = [-1]*n\n    for i in range(1, n):\n        for j in range(i):\n            if nums[j] < nums[i] and dp[j]+1 > dp[i]:\n                dp[i] = dp[j]+1; parent[i] = j\n    idx = dp.index(max(dp))\n    seq = []\n    while idx != -1: seq.append(nums[idx]); idx = parent[idx]\n    return seq[::-1]",
    ),
    (
        "R13_019",
        "python",
        "Kadane Maximum Subarray",
        "def max_subarray(nums):\n    max_sum = cur_sum = nums[0]\n    start = end = temp_start = 0\n    for i in range(1, len(nums)):\n        if cur_sum + nums[i] < nums[i]:\n            cur_sum = nums[i]\n            temp_start = i\n        else:\n            cur_sum += nums[i]\n        if cur_sum > max_sum:\n            max_sum = cur_sum\n            start = temp_start\n            end = i\n    return max_sum, nums[start:end+1]",
    ),
    (
        "R13_020",
        "python",
        "Subset Sum",
        "def subset_sum(nums, target):\n    dp = {0}\n    for num in nums:\n        dp = dp | {x + num for x in dp}\n    return target in dp\ndef count_subsets(nums, target):\n    dp = [0] * (target + 1)\n    dp[0] = 1\n    for num in nums:\n        for j in range(target, num-1, -1):\n            dp[j] += dp[j-num]\n    return dp[target]",
    ),
    (
        "R13_021",
        "python",
        "Interval Merge and Insert",
        "def merge_intervals(intervals):\n    if not intervals: return []\n    intervals.sort()\n    merged = [intervals[0]]\n    for start, end in intervals[1:]:\n        if start <= merged[-1][1]: merged[-1][1] = max(merged[-1][1], end)\n        else: merged.append([start, end])\n    return merged\ndef insert_interval(intervals, new):\n    res = []; i = 0\n    while i < len(intervals) and intervals[i][1] < new[0]:\n        res.append(intervals[i]); i += 1\n    while i < len(intervals) and intervals[i][0] <= new[1]:\n        new[0] = min(new[0], intervals[i][0])\n        new[1] = max(new[1], intervals[i][1])\n        i += 1\n    res.append(new)\n    return res + intervals[i:]",
    ),
    (
        "R13_022",
        "python",
        "Sliding Window Maximum",
        "from collections import deque\ndef sliding_window_max(nums, k):\n    dq = deque()  # decreasing indices\n    result = []\n    for i, num in enumerate(nums):\n        while dq and nums[dq[-1]] < num: dq.pop()\n        dq.append(i)\n        if dq[0] == i - k: dq.popleft()\n        if i >= k - 1: result.append(nums[dq[0]])\n    return result",
    ),
    (
        "R13_023",
        "python",
        "String Compression",
        "def compress(s):\n    if not s: return ''\n    result = []; count = 1\n    for i in range(1, len(s)):\n        if s[i] == s[i-1]: count += 1\n        else:\n            result.append(s[i-1])\n            if count > 1: result.append(str(count))\n            count = 1\n    result.append(s[-1])\n    if count > 1: result.append(str(count))\n    compressed = ''.join(result)\n    return compressed if len(compressed) < len(s) else s",
    ),
    (
        "R13_024",
        "python",
        "Median of Two Sorted Arrays",
        "def find_median_sorted_arrays(nums1, nums2):\n    if len(nums1) > len(nums2): nums1, nums2 = nums2, nums1\n    m, n = len(nums1), len(nums2)\n    lo, hi = 0, m\n    while lo <= hi:\n        i = (lo + hi) // 2\n        j = (m + n + 1) // 2 - i\n        max_l1 = float('-inf') if i == 0 else nums1[i-1]\n        min_r1 = float('inf') if i == m else nums1[i]\n        max_l2 = float('-inf') if j == 0 else nums2[j-1]\n        min_r2 = float('inf') if j == n else nums2[j]\n        if max_l1 <= min_r2 and max_l2 <= min_r1:\n            if (m + n) % 2 == 0: return (max(max_l1, max_l2) + min(min_r1, min_r2)) / 2\n            return max(max_l1, max_l2)\n        elif max_l1 > min_r2: hi = i - 1\n        else: lo = i + 1",
    ),
    (
        "R13_025",
        "python",
        "Expression Evaluator",
        "def eval_expr(s):\n    stack = []; num = 0; sign = 1; result = 0\n    for c in s:\n        if c.isdigit(): num = num * 10 + int(c)\n        elif c in '+-':\n            result += sign * num; num = 0\n            sign = 1 if c == '+' else -1\n        elif c == '(':\n            stack.append(result); stack.append(sign)\n            result = 0; sign = 1\n        elif c == ')':\n            result += sign * num; num = 0\n            result *= stack.pop(); result += stack.pop()\n    return result + sign * num",
    ),
    (
        "R13_026",
        "python",
        "Decode Ways",
        "def num_decodings(s):\n    if not s or s[0] == '0': return 0\n    n = len(s)\n    dp = [0] * (n + 1)\n    dp[0] = dp[1] = 1\n    for i in range(2, n + 1):\n        one = int(s[i-1])\n        two = int(s[i-2:i])\n        if one != 0: dp[i] += dp[i-1]\n        if 10 <= two <= 26: dp[i] += dp[i-2]\n    return dp[n]",
    ),
    (
        "R13_027",
        "python",
        "Next Permutation",
        "def next_permutation(nums):\n    n = len(nums)\n    i = n - 2\n    while i >= 0 and nums[i] >= nums[i+1]: i -= 1\n    if i >= 0:\n        j = n - 1\n        while nums[j] <= nums[i]: j -= 1\n        nums[i], nums[j] = nums[j], nums[i]\n    nums[i+1:] = reversed(nums[i+1:])\n    return nums",
    ),
    (
        "R13_028",
        "python",
        "Regular Expression Match",
        "def is_match(s, p):\n    m, n = len(s), len(p)\n    dp = [[False]*(n+1) for _ in range(m+1)]\n    dp[0][0] = True\n    for j in range(2, n+1):\n        if p[j-1] == '*': dp[0][j] = dp[0][j-2]\n    for i in range(1, m+1):\n        for j in range(1, n+1):\n            if p[j-1] == '*':\n                dp[i][j] = dp[i][j-2]\n                if p[j-2] == '.' or p[j-2] == s[i-1]:\n                    dp[i][j] = dp[i][j] or dp[i-1][j]\n            elif p[j-1] == '.' or p[j-1] == s[i-1]:\n                dp[i][j] = dp[i-1][j-1]\n    return dp[m][n]",
    ),
    (
        "R13_029",
        "python",
        "Skyline Problem",
        "import heapq\nfrom collections import defaultdict\ndef get_skyline(buildings):\n    events = []\n    for l, r, h in buildings:\n        events.append((l, -h, r))\n        events.append((r, 0, 0))\n    events.sort()\n    result = []\n    heap = [(0, float('inf'))]\n    for x, neg_h, r in events:\n        while heap[0][1] <= x: heapq.heappop(heap)\n        if neg_h: heapq.heappush(heap, (neg_h, r))\n        if not result or result[-1][1] != -heap[0][0]:\n            result.append([x, -heap[0][0]])\n    return result",
    ),
    (
        "R13_030",
        "python",
        "Minimum Window Substring",
        "from collections import Counter\ndef min_window(s, t):\n    need = Counter(t); missing = len(t)\n    best_l = best_r = None; l = 0\n    for r, c in enumerate(s):\n        if need[c] > 0: missing -= 1\n        need[c] -= 1\n        if missing == 0:\n            while need[s[l]] < 0: need[s[l]] += 1; l += 1\n            if best_l is None or r - l < best_r - best_l: best_l, best_r = l, r\n            need[s[l]] += 1; missing += 1; l += 1\n    return s[best_l:best_r+1] if best_l is not None else ''",
    ),
    (
        "R13_031",
        "python",
        "Task Scheduler",
        "from collections import Counter\nimport heapq\ndef least_interval(tasks, n):\n    count = Counter(tasks)\n    heap = [-c for c in count.values()]\n    heapq.heapify(heap)\n    time = 0\n    queue = []\n    while heap or queue:\n        time += 1\n        if heap:\n            cnt = heapq.heappop(heap) + 1\n            if cnt: queue.append((cnt, time + n))\n        if queue and queue[0][1] == time:\n            heapq.heappush(heap, queue.pop(0)[0])\n    return time",
    ),
    (
        "R13_032",
        "python",
        "Alien Dictionary",
        "from collections import defaultdict, deque\ndef alien_order(words):\n    graph = defaultdict(set)\n    in_degree = {c: 0 for w in words for c in w}\n    for i in range(len(words)-1):\n        w1, w2 = words[i], words[i+1]\n        for c1, c2 in zip(w1, w2):\n            if c1 != c2:\n                if c2 not in graph[c1]:\n                    graph[c1].add(c2)\n                    in_degree[c2] += 1\n                break\n        else:\n            if len(w1) > len(w2): return ''\n    queue = deque(c for c in in_degree if in_degree[c] == 0)\n    order = ''\n    while queue:\n        c = queue.popleft(); order += c\n        for nei in graph[c]:\n            in_degree[nei] -= 1\n            if in_degree[nei] == 0: queue.append(nei)\n    return order if len(order) == len(in_degree) else ''",
    ),
    (
        "R13_033",
        "python",
        "Account Merge",
        "from collections import defaultdict\ndef accounts_merge(accounts):\n    parent = {}\n    def find(x):\n        if parent.setdefault(x, x) != x: parent[x] = find(parent[x])\n        return parent[x]\n    def union(x, y): parent[find(x)] = find(y)\n    email_to_name = {}\n    for acc in accounts:\n        name = acc[0]\n        for email in acc[1:]:\n            email_to_name[email] = name\n            union(acc[1], email)\n    groups = defaultdict(list)\n    for email in email_to_name:\n        groups[find(email)].append(email)\n    return [[email_to_name[root]] + sorted(emails) for root, emails in groups.items()]",
    ),
    (
        "R13_034",
        "python",
        "Smallest Range Covering K Lists",
        "import heapq\ndef smallest_range(nums):\n    heap = [(row[0], i, 0) for i, row in enumerate(nums)]\n    heapq.heapify(heap)\n    cur_max = max(row[0] for row in nums)\n    best = [float('-inf'), float('inf')]\n    while heap:\n        cur_min, row, col = heapq.heappop(heap)\n        if cur_max - cur_min < best[1] - best[0]:\n            best = [cur_min, cur_max]\n        if col + 1 == len(nums[row]): break\n        next_val = nums[row][col+1]\n        heapq.heappush(heap, (next_val, row, col+1))\n        cur_max = max(cur_max, next_val)\n    return best",
    ),
    (
        "R13_035",
        "python",
        "Find Duplicate Number",
        "def find_duplicate(nums):\n    # Floyd's cycle detection - O(n) time, O(1) space\n    slow = fast = nums[0]\n    while True:\n        slow = nums[slow]\n        fast = nums[nums[fast]]\n        if slow == fast: break\n    slow = nums[0]\n    while slow != fast:\n        slow = nums[slow]\n        fast = nums[fast]\n    return slow",
    ),
    (
        "R13_036",
        "python",
        "Count of Smaller After Self",
        "def count_smaller(nums):\n    result = [0] * len(nums)\n    sorted_list = []\n    def bisect_left_custom(arr, val):\n        lo, hi = 0, len(arr)\n        while lo < hi:\n            mid = (lo + hi) // 2\n            if arr[mid] < val: lo = mid + 1\n            else: hi = mid\n        return lo\n    for i in range(len(nums)-1, -1, -1):\n        pos = bisect_left_custom(sorted_list, nums[i])\n        result[i] = pos\n        sorted_list.insert(pos, nums[i])\n    return result",
    ),
    (
        "R13_037",
        "python",
        "Paint House III",
        "def min_cost(houses, cost, m, n, target):\n    INF = float('inf')\n    dp = [[[INF]*( target+1) for _ in range(n+1)] for _ in range(m)]\n    for j in range(1, n+1):\n        c = cost[0][j-1]\n        if houses[0] == 0: dp[0][j][1] = c\n        elif houses[0] == j: dp[0][j][1] = 0\n    for i in range(1, m):\n        for j in range(1, n+1):\n            if houses[i] != 0 and houses[i] != j: continue\n            paint_cost = 0 if houses[i] != 0 else cost[i][j-1]\n            for k in range(1, target+1):\n                for pj in range(1, n+1):\n                    prev = dp[i-1][pj][k] if pj == j else dp[i-1][pj][k-1]\n                    dp[i][j][k] = min(dp[i][j][k], prev + paint_cost)\n    return min(dp[m-1][j][target] for j in range(1, n+1)) if min(dp[m-1][j][target] for j in range(1, n+1)) < INF else -1",
    ),
    (
        "R13_038",
        "python",
        "Russian Doll Envelopes",
        "import bisect\ndef max_envelopes(envelopes):\n    envelopes.sort(key=lambda x: (x[0], -x[1]))\n    tails = []\n    for _, h in envelopes:\n        pos = bisect.bisect_left(tails, h)\n        if pos == len(tails): tails.append(h)\n        else: tails[pos] = h\n    return len(tails)",
    ),
    (
        "R13_039",
        "python",
        "Jump Game III",
        "from collections import deque\ndef can_reach(arr, start):\n    n = len(arr); visited = set()\n    queue = deque([start])\n    while queue:\n        i = queue.popleft()\n        if arr[i] == 0: return True\n        if i in visited: continue\n        visited.add(i)\n        for ni in (i + arr[i], i - arr[i]):\n            if 0 <= ni < n and ni not in visited:\n                queue.append(ni)\n    return False",
    ),
    (
        "R13_040",
        "python",
        "Number of Ways to Stay Same Place",
        "def num_ways(steps, arr_len):\n    MOD = 10**9+7\n    max_pos = min(steps//2, arr_len-1)\n    dp = [0]*(max_pos+1); dp[0] = 1\n    for _ in range(steps):\n        new_dp = [0]*(max_pos+1)\n        for i in range(max_pos+1):\n            if dp[i] == 0: continue\n            new_dp[i] = (new_dp[i] + dp[i]) % MOD\n            if i > 0: new_dp[i-1] = (new_dp[i-1] + dp[i]) % MOD\n            if i < max_pos: new_dp[i+1] = (new_dp[i+1] + dp[i]) % MOD\n        dp = new_dp\n    return dp[0]",
    ),
    (
        "R13_041",
        "python",
        "Longest Path in DAG",
        "from collections import defaultdict, deque\ndef longest_path(n, edges):\n    graph = defaultdict(list)\n    in_deg = [0]*n\n    for u, v in edges:\n        graph[u].append(v); in_deg[v] += 1\n    dist = [0]*n\n    queue = deque(i for i in range(n) if in_deg[i] == 0)\n    while queue:\n        u = queue.popleft()\n        for v in graph[u]:\n            dist[v] = max(dist[v], dist[u]+1)\n            in_deg[v] -= 1\n            if in_deg[v] == 0: queue.append(v)\n    return max(dist)",
    ),
    (
        "R13_042",
        "python",
        "Maximal Square",
        "def maximal_square(matrix):\n    if not matrix: return 0\n    m, n = len(matrix), len(matrix[0])\n    dp = [[0]*n for _ in range(m)]\n    side = 0\n    for i in range(m):\n        for j in range(n):\n            if matrix[i][j] == '1':\n                if i == 0 or j == 0: dp[i][j] = 1\n                else: dp[i][j] = min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1]) + 1\n                side = max(side, dp[i][j])\n    return side * side",
    ),
    (
        "R13_043",
        "python",
        "Find All Anagrams",
        "from collections import Counter\ndef find_anagrams(s, p):\n    need = Counter(p); window = Counter()\n    result = []; k = len(p)\n    for i, c in enumerate(s):\n        window[c] += 1\n        if i >= k:\n            old = s[i-k]\n            if window[old] == 1: del window[old]\n            else: window[old] -= 1\n        if window == need: result.append(i - k + 1)\n    return result",
    ),
    (
        "R13_044",
        "python",
        "Course Schedule II",
        "from collections import defaultdict, deque\ndef find_order(n, prerequisites):\n    graph = defaultdict(list); in_deg = [0]*n\n    for a, b in prerequisites:\n        graph[b].append(a); in_deg[a] += 1\n    queue = deque(i for i in range(n) if in_deg[i] == 0)\n    order = []\n    while queue:\n        u = queue.popleft(); order.append(u)\n        for v in graph[u]:\n            in_deg[v] -= 1\n            if in_deg[v] == 0: queue.append(v)\n    return order if len(order) == n else []",
    ),
    (
        "R13_045",
        "python",
        "Number of Provinces",
        "def find_circle_num(matrix):\n    n = len(matrix)\n    visited = [False]*n\n    count = 0\n    def dfs(i):\n        for j in range(n):\n            if matrix[i][j] == 1 and not visited[j]:\n                visited[j] = True; dfs(j)\n    for i in range(n):\n        if not visited[i]:\n            visited[i] = True; dfs(i); count += 1\n    return count",
    ),
    (
        "R13_046",
        "python",
        "Word Ladder",
        "from collections import deque\ndef ladder_length(begin, end, word_list):\n    word_set = set(word_list)\n    if end not in word_set: return 0\n    queue = deque([(begin, 1)])\n    visited = {begin}\n    while queue:\n        word, length = queue.popleft()\n        for i in range(len(word)):\n            for c in 'abcdefghijklmnopqrstuvwxyz':\n                next_word = word[:i] + c + word[i+1:]\n                if next_word == end: return length + 1\n                if next_word in word_set and next_word not in visited:\n                    visited.add(next_word); queue.append((next_word, length+1))\n    return 0",
    ),
    (
        "R13_047",
        "python",
        "Palindrome Partitioning",
        "def partition(s):\n    res = []; path = []\n    def is_palindrome(sub): return sub == sub[::-1]\n    def backtrack(start):\n        if start == len(s): res.append(path[:]); return\n        for end in range(start+1, len(s)+1):\n            if is_palindrome(s[start:end]):\n                path.append(s[start:end])\n                backtrack(end)\n                path.pop()\n    backtrack(0)\n    return res",
    ),
    (
        "R13_048",
        "python",
        "Restore IP Addresses",
        "def restore_ip(s):\n    res = []\n    def backtrack(start, parts):\n        if len(parts) == 4 and start == len(s):\n            res.append('.'.join(parts)); return\n        if len(parts) == 4 or start == len(s): return\n        for length in range(1, 4):\n            if start + length > len(s): break\n            segment = s[start:start+length]\n            if len(segment) > 1 and segment[0] == '0': break\n            if int(segment) > 255: break\n            backtrack(start+length, parts + [segment])\n    backtrack(0, [])\n    return res",
    ),
    (
        "R13_049",
        "python",
        "Generalized Abbreviation",
        "def generate_abbreviations(word):\n    res = []\n    def backtrack(i, cur, count):\n        if i == len(word):\n            res.append(cur + (str(count) if count else ''))\n            return\n        backtrack(i+1, cur, count+1)  # abbreviate\n        backtrack(i+1, cur + (str(count) if count else '') + word[i], 0)  # keep\n    backtrack(0, '', 0)\n    return res",
    ),
    (
        "R13_050",
        "python",
        "Letter Combinations",
        "from typing import List\ndef letter_combinations(digits: str) -> List[str]:\n    if not digits: return []\n    phone = {'2':'abc','3':'def','4':'ghi','5':'jkl','6':'mno','7':'pqrs','8':'tuv','9':'wxyz'}\n    res = []; path = []\n    def backtrack(i):\n        if i == len(digits): res.append(''.join(path)); return\n        for c in phone[digits[i]]:\n            path.append(c); backtrack(i+1); path.pop()\n    backtrack(0)\n    return res",
    ),
]

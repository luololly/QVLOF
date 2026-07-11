from __future__ import annotations

import math

try:
    import torch
except ImportError:  # pragma: no cover - optional runtime dependency
    torch = None

from .cov import torch_device


def farthest_point_sampling(x, k: int):
    n = x.shape[0]
    k = min(k, n)
    idx = torch.zeros(k, dtype=torch.long, device=x.device)
    idx[0] = torch.randint(0, n, (1,), device=x.device)
    dist = torch.full((n,), float("inf"), device=x.device)

    for i in range(1, k):
        last = x[idx[i - 1]].unsqueeze(0)
        d = torch.cdist(x, last).squeeze(1)
        dist = torch.minimum(dist, d)
        idx[i] = torch.argmax(dist)
    return x[idx]


def get_query_anchors(query, c: float = 4.0, k_min: int = 8, k_max: int = 128):
    q = query.shape[0]
    kq = int(math.ceil(c * math.log(max(q, 2))))
    kq = max(k_min, min(kq, k_max))
    kq = min(kq, q)
    return farthest_point_sampling(query, kq)


def newdata(query, data, size=None, k: int = 3, t: float = 0.3, chunk_size: int = 4096):
    if torch is None:  # pragma: no cover - guarded by caller
        raise RuntimeError("torch is required for query-aware LGPF transforms.")

    q = torch.as_tensor(query, dtype=torch.float32, device=torch_device())
    x = torch.as_tensor(data, dtype=torch.float32, device=torch_device())

    if q.dim() == 1:
        q = q.unsqueeze(0)
    if x.dim() == 1:
        x = x.unsqueeze(0)

    if q.shape[1] != x.shape[1]:
        raise ValueError("query and data must share the same feature dimension.")
    if size is not None and size != x.shape[1]:
        raise ValueError(f"size={size} does not match data dimension {x.shape[1]}")

    q_anchor = get_query_anchors(q)
    if q_anchor.shape[0] > 1:
        qd = torch.cdist(q_anchor, q_anchor)
        dc = qd[qd > 0].mean()
    else:
        dc = torch.tensor(1.0, device=torch_device())

    updated_chunks = []
    eps = 1e-8
    for start in range(0, x.shape[0], chunk_size):
        end = min(start + chunk_size, x.shape[0])
        x_chunk = x[start:end]
        dist = torch.cdist(x_chunk, q_anchor)
        k_eff = min(k, q_anchor.shape[0])
        topk_dists, idx = torch.topk(dist, k=k_eff, largest=False, dim=1)
        q_sel = q_anchor[idx]
        denom = (topk_dists**2).clamp_min(eps)
        delta = q_sel - x_chunk.unsqueeze(1)
        factor = (dc / denom).unsqueeze(-1)
        f_sum = (factor * delta).sum(dim=1)
        updated_chunks.append(x_chunk + t * (torch.ones_like(x_chunk) + f_sum))

    return torch.cat(updated_chunks, dim=0)

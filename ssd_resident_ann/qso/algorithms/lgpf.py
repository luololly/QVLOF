from __future__ import annotations

import math

try:
    import torch
except ImportError:  # pragma: no cover - optional runtime dependency
    torch = None

from .cov import has_torch, torch_device


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


def get_dc_anchor_torch(data, m: int, c: float = 4.0, k_min: int = 16, k_max: int = 256):
    k_anchor = int(math.ceil(c * math.log(max(data.shape[0], 2))))
    k_anchor = max(k_min, min(k_anchor, k_max))
    k_anchor = min(k_anchor, data.shape[0])

    anchors = farthest_point_sampling(data, k_anchor)
    dists = torch.cdist(data, anchors)
    k_eff = min(m + 1, k_anchor)
    sorted_dists, idx = torch.topk(dists, k=k_eff, largest=False, dim=1)
    topk_pts = anchors[idx]
    dc = sorted_dists[:, 1].mean() if k_eff > 1 else torch.tensor(0.0, device=data.device)
    return topk_pts, dc, sorted_dists


def newdata(data, size=None, k: int = 3, t: float = 0.3):
    if torch is None:  # pragma: no cover - guarded by caller
        raise RuntimeError("torch is required for LGPF transforms.")

    x = torch.as_tensor(data, dtype=torch.float32, device=torch_device())
    if x.dim() == 1:
        x = x.unsqueeze(0)

    if size is not None and size != x.shape[1]:
        raise ValueError(f"size={size} does not match data dimension {x.shape[1]}")

    topk_pts, dc, topk_dists = get_dc_anchor_torch(x, m=k)
    self_pts = topk_pts[:, 0:1, :]
    neighbors = topk_pts[:, 1:, :]

    if neighbors.numel() == 0:
        return x

    nearest1 = topk_dists[:, 1]
    dist_js = topk_dists[:, 1:]
    denom = (dist_js**2).clamp_min(1e-8)
    factor = (dc * nearest1.unsqueeze(1)) / denom
    factor = factor.unsqueeze(-1)
    delta = neighbors - self_pts
    f_sum = (factor * delta).sum(dim=1)
    updated = topk_pts[:, 0, :] + t * (torch.ones_like(x) + f_sum)
    return updated

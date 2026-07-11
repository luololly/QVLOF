from __future__ import annotations

import numpy as np

try:
    import torch
except ImportError:  # pragma: no cover - optional runtime dependency
    torch = None


def has_torch() -> bool:
    return torch is not None


def torch_device():
    if torch is None:  # pragma: no cover - guarded by caller
        raise RuntimeError("torch is required for covariance-based QSO transforms.")
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def covariance_eigen_decomposition(input_data):
    if torch is None:  # pragma: no cover - guarded by caller
        raise RuntimeError("torch is required for covariance-based QSO transforms.")

    if isinstance(input_data, np.ndarray):
        tensor_data = torch.from_numpy(input_data.astype(np.float32)).to(torch_device())
    elif isinstance(input_data, torch.Tensor):
        tensor_data = input_data.to(torch_device()).float()
    else:
        raise TypeError("input_data must be np.ndarray or torch.Tensor")

    if tensor_data.dim() == 1:
        tensor_data = tensor_data.unsqueeze(0)
    if tensor_data.dim() != 2:
        raise ValueError("input_data must be 2D")

    x_centered = tensor_data - torch.mean(tensor_data, dim=0)
    cov_matrix = (x_centered.T @ x_centered) / max(1, tensor_data.shape[0] - 1)
    eigenvalues, eigenvectors = torch.linalg.eigh(cov_matrix)
    sqrt_eigen_matrix = torch.diag_embed(torch.sqrt(torch.clamp(eigenvalues, min=0.0)))
    return cov_matrix, sqrt_eigen_matrix, eigenvectors


def transform_matrix(cov_mat, scale_mat, rotation_mat) -> np.ndarray:
    if torch is None:  # pragma: no cover - guarded by caller
        raise RuntimeError("torch is required for covariance-based QSO transforms.")

    sqrt_mat = scale_mat.to(torch_device())
    eigvecs = rotation_mat.to(torch_device())
    transformed = torch.matmul(cov_mat, eigvecs)
    transformed = torch.matmul(transformed, sqrt_mat)
    return transformed.cpu().numpy()

# CPU vs GPU Performance Benchmark

## Overview

This benchmark compares the computational performance of the CPU and GPU implementations of the fully decoupled Scalar Auxiliary Variable (SAV) scheme for the Cahn–Hilliard–Darcy system.

The CPU implementation uses an AMD Ryzen 7 7800X3D 8-core processor, while the GPU implementation uses an NVIDIA GeForce RTX 4070 SUPER with 12 GB of memory.

The GPU implementation uses CUDA acceleration through CuPy and cuFFT, allowing FFT operations, pointwise operations, and time-stepping computations to be performed directly on the GPU.

---

## Hardware Configuration

| Component | Specification |
|---|---|
| CPU | AMD Ryzen 7 7800X3D (8-core) |
| GPU | NVIDIA GeForce RTX 4070 SUPER |
| GPU Memory | 12 GB |
| GPU Framework | CUDA + CuPy |
| Spatial Discretization | Fourier spectral method |
| Time Integration | Fully decoupled SAV scheme with BDF2 |

---

## Benchmark Results

The following table summarizes the measured wall-clock times.

| Test Case | Resolution / Workload | CPU Time | GPU Time | Speedup |
|---|---|---:|---:|---:|
| Coarsening | 8000 steps, 128×128 | 34 s | 42 s | ~0.8× |
| Spinodal decomposition | 40k–50k steps, 512×512 | ~2 h | ~9 min | ~13× |
| Convergence study | 25 runs, varying Δt | ~13 h | ~11 h | ~1.2× |

---

## Discussion

The GPU acceleration strongly depends on the size and duration of the simulation.

For the small 128×128 coarsening test, the GPU does not provide an advantage because initialization overhead, FFT planning, and kernel launch costs represent a significant fraction of the total runtime.

For the large 512×512 spinodal decomposition simulations, the computational workload is sufficiently large to utilize GPU parallelism effectively. The GPU reduces the runtime from approximately two hours to nine minutes, achieving a speedup of approximately 13×.

The convergence study consists of many short simulations. Since each run requires initialization and setup overhead, the GPU advantage is more limited.

---

## Interpretation

GPU acceleration is most beneficial for:

- high-resolution simulations,
- long-time integrations,
- large parameter studies.

For small-scale simulations, CPU execution may remain competitive due to lower overhead.

---

## Reproducibility

The benchmark results correspond to the numerical experiments presented in:

**Master's Thesis**

*"On a Novel Fully Decoupled, Linear and Second-Order Accurate Numerical Scheme for the Cahn–Hilliard–Darcy System of Two-Phase Hele–Shaw Flow"*

University of Koblenz, 2026.

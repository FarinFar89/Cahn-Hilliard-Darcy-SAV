from pathlib import Path
import sys

import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from chd_sav import CahnHilliardDarcySolver


def main():
    output_dir = PROJECT_ROOT / "output"
    output_dir.mkdir(exist_ok=True)

    solver = CahnHilliardDarcySolver(
        Nx=64,
        Ny=64,
        dt=0.005,
        epsilon=0.05,
        S=2.0,
    )
    solver.init_two_circles()

    n_steps = 100
    for _ in range(n_steps):
        solver.step()

    fig, ax = plt.subplots(figsize=(5, 4))
    im = ax.imshow(
        solver.phi.T,
        origin="lower",
        extent=[0, solver.Lx, 0, solver.Ly],
        cmap="RdBu_r",
        vmin=-1,
        vmax=1,
    )
    ax.set_title(f"Quick coarsening demo, t = {solver.t:.3f}")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    fig.colorbar(im, ax=ax, label="phase field")

    outfile = output_dir / "quick_coarsening_demo.png"
    fig.tight_layout()
    fig.savefig(outfile, dpi=150)
    plt.close(fig)

    print(f"Saved {outfile}")


if __name__ == "__main__":
    main()

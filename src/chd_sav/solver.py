import os

import numpy as np

try:
    import pyfftw
    from pyfftw.interfaces.numpy_fft import (
        fft2 as fft2_base,
        ifft2 as ifft2_base,
        fftfreq,
    )

    pyfftw.interfaces.cache.enable()
    USE_PYFFTW = True
except ImportError:
    from scipy.fft import fft2 as fft2_base, ifft2 as ifft2_base, fftfreq

    USE_PYFFTW = False


FFT_THREADS = max(1, min(8, os.cpu_count() or 1))


def fft2_wrap(a):
    return fft2_base(a, threads=FFT_THREADS) if USE_PYFFTW else fft2_base(a)


def ifft2_wrap(a):
    return ifft2_base(a, threads=FFT_THREADS) if USE_PYFFTW else ifft2_base(a)


class CahnHilliardDarcySolver:
    """
    CPU solver for the Cahn-Hilliard-Darcy system using the SAV scheme
    described by Yang (2021).
    """

    def __init__(
        self,
        Lx=2 * np.pi,
        Ly=2 * np.pi,
        Nx=512,
        Ny=512,
        dt=0.001,
        alpha=100.0,
        M=1.0,
        lambda_param=0.01,
        epsilon=0.025,
        S=10.0,
        tau=1.0,
        B=10.0,
    ):
        self.Lx, self.Ly = Lx, Ly
        self.Nx, self.Ny = Nx, Ny
        self.dt = dt
        self.alpha = alpha
        self.M = M
        self.lam = lambda_param
        self.eps = epsilon
        self.S = S
        self.tau = tau
        self.B = B

        self.dx = Lx / Nx
        self.dy = Ly / Ny
        self.x = np.linspace(0, Lx, Nx, endpoint=False)
        self.y = np.linspace(0, Ly, Ny, endpoint=False)
        self.X, self.Y = np.meshgrid(self.x, self.y, indexing="ij")

        self.kx = 2 * np.pi * fftfreq(Nx, d=self.dx)
        self.ky = 2 * np.pi * fftfreq(Ny, d=self.dy)
        self.KX, self.KY = np.meshgrid(self.kx, self.ky, indexing="ij")
        self.K2 = self.KX**2 + self.KY**2
        self.K2[0, 0] = 1e-10

        self.phi = np.zeros((Nx, Ny))
        self.phi_old = np.zeros((Nx, Ny))
        self.u = np.zeros((Nx, Ny))
        self.v = np.zeros((Nx, Ny))
        self.p = np.zeros((Nx, Ny))
        self.mu = np.zeros((Nx, Ny))

        self.U = 0.0
        self.t = 0.0

    def init_two_circles(self):
        """Initial condition with two tanh-profile disks."""
        x1, y1 = np.pi - 0.8, np.pi
        x2, y2 = np.pi + 1.7, np.pi
        r1, r2 = 1.4, 0.5

        dist1 = np.sqrt((self.X - x1) ** 2 + (self.Y - y1) ** 2)
        dist2 = np.sqrt((self.X - x2) ** 2 + (self.Y - y2) ** 2)

        self.phi = (
            1.0
            + np.tanh((r1 - dist1) / (1.5 * self.eps))
            + np.tanh((r2 - dist2) / (1.5 * self.eps))
        )
        self.phi_old = self.phi.copy()
        self._init_sav()

    def init_spinodal(self, phi_avg, noise_amp=0.001, seed=None):
        """Initial condition for spinodal decomposition."""
        rng = np.random.default_rng(seed)
        noise = noise_amp * (2 * rng.random((self.Nx, self.Ny)) - 1)
        self.phi = phi_avg + noise
        self.phi_old = self.phi.copy()
        self._init_sav()

    def _init_sav(self):
        F = (0.25 / self.eps**2) * (self.phi**2 - 1) ** 2
        E_bulk = np.sum(F) * self.dx * self.dy
        self.U = np.sqrt(E_bulk + self.B)

    def save_state(self, path):
        """Save the current solver state to an .npz file."""
        np.savez(
            path,
            phi=self.phi,
            phi_old=self.phi_old,
            u=self.u,
            v=self.v,
            p=self.p,
            mu=self.mu,
            U=self.U,
            t=self.t,
        )

    def load_state(self, path):
        """Load a solver state from an .npz file."""
        data = np.load(path)
        self.phi = data["phi"]
        self.phi_old = data["phi_old"]
        self.u = data["u"]
        self.v = data["v"]
        self.p = data["p"]
        self.mu = data["mu"]
        self.U = float(data["U"])
        self.t = float(data["t"])

    def step(self):
        """Advance the solution by one SAV time step."""
        phi_star = 2.0 * self.phi - self.phi_old

        f_phi = (1.0 / self.eps**2) * (phi_star**3 - phi_star)
        F_term = (0.25 / self.eps**2) * (phi_star**2 - 1) ** 2
        E_integral = np.sum(F_term) * self.dx * self.dy
        H = f_phi / np.sqrt(E_integral + self.B)

        phi_hat = fft2_wrap(self.phi)
        phi_old_hat = fft2_wrap(self.phi_old)

        grad_phi_x = np.real(ifft2_wrap(1j * self.KX * phi_hat))
        grad_phi_y = np.real(ifft2_wrap(1j * self.KY * phi_hat))
        advection = self.u * grad_phi_x + self.v * grad_phi_y
        adv_hat = fft2_wrap(advection)

        stab_coeff = self.S / self.eps**2

        lhs_op = (
            (1.5 / self.dt)
            + self.M * self.lam * self.K2**2
            + self.M * self.lam * stab_coeff * self.K2
        )

        rhs_time = (2.0 * phi_hat - 0.5 * phi_old_hat) / self.dt

        forcing_spatial = self.lam * (H * self.U - stab_coeff * phi_star)
        forcing_hat = fft2_wrap(forcing_spatial)
        rhs_spatial = -self.M * self.K2 * forcing_hat

        rhs_total = rhs_time - adv_hat + rhs_spatial

        phi_new_hat = rhs_total / lhs_op
        phi_new = np.real(ifft2_wrap(phi_new_hat))

        diff_phi = phi_new - self.phi
        integral_update = 0.5 * np.sum(H * diff_phi) * self.dx * self.dy
        self.U = self.U + integral_update

        lap_phi_new = np.real(ifft2_wrap(-self.K2 * fft2_wrap(phi_new)))

        f_phi_new = (1.0 / self.eps**2) * (phi_new**3 - phi_new)
        F_new = (0.25 / self.eps**2) * (phi_new**2 - 1) ** 2
        E_new = np.sum(F_new) * self.dx * self.dy
        H_new = f_phi_new / np.sqrt(E_new + self.B)

        self.mu = self.lam * (-lap_phi_new + H_new * self.U)

        mu_hat = fft2_wrap(self.mu)
        grad_mu_x = np.real(ifft2_wrap(1j * self.KX * mu_hat))
        grad_mu_y = np.real(ifft2_wrap(1j * self.KY * mu_hat))

        force_x = -phi_new * grad_mu_x
        force_y = -phi_new * grad_mu_y

        coeff_u = (self.tau / self.dt) + self.alpha
        rhs_u = (self.tau / self.dt) * self.u + force_x
        rhs_v = (self.tau / self.dt) * self.v + force_y

        div_rhs = 1j * self.KX * fft2_wrap(rhs_u) + 1j * self.KY * fft2_wrap(rhs_v)
        p_hat = div_rhs / (-self.K2)
        p_hat[0, 0] = 0.0

        grad_p_x = np.real(ifft2_wrap(1j * self.KX * p_hat))
        grad_p_y = np.real(ifft2_wrap(1j * self.KY * p_hat))

        self.u = (rhs_u - grad_p_x) / coeff_u
        self.v = (rhs_v - grad_p_y) / coeff_u

        self.phi_old = self.phi.copy()
        self.phi = phi_new
        self.t += self.dt

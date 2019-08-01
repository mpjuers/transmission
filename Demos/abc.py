# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.2'
#       jupytext_version: 1.1.2
#   kernelspec:
#     display_name: transmission
#     language: python
#     name: transmission3
# ---

# %% markdown [markdown]
# # Demonstration of parameter estimation using Approximate Bayesian Computation
#
#
#
#
#


# %% [markdown]
# This is a live document. Install Jupytext and open as a Jupyter notebook.

# %% {"node_exists": true, "node_name": "8b3d4268f1de4428874f8852f23e58fe"}
from __future__ import print_function, division

import itertools
import pickle

from joblib import Memory
import msprime as ms
import matplotlib.pyplot as plt
import transmission as txmn
import numpy as np
import pandas as pd
from scipy import stats

memory = Memory('./Cache', verbose=0)
# Use memory() as a decorator to cache

# Show all output, not just last command.
from IPython.core.interactiveshell import InteractiveShell
InteractiveShell.ast_node_interactivity = "all"

# %matplotlib inline

# Automatically reload transmission. Remove after debugging.
# %reload_ext autoreload
# %autoreload 2
# %aimport transmission

# Show all output, not just last command.
from IPython.core.interactiveshell import InteractiveShell
InteractiveShell.ast_node_interactivity = "all"

memory = Memory(location="./Cache", verbose=0)


# %% markdown [markdown]
#  First, simulate a data set. The `sim()` function in Transmission is the
#  workhorse function that simulates a geneaology given a set of parameters.
#  Generally, it is called by `generate_priors()` and there is no reason to call
#  it directly, but here we can use it for a proof of concept.

# %% {"node_exists": true, "node_name": "e5bcf2f5d92446df854eeb3cc4eadbd5"}
eta = 0.15  # Exponent of 10 representing the multiplicative difference
            # between the host's mutation rate and the symbiont's.
tau = 0.75  # The fraction of new infections that result from vertical
            # transmission.
rho = 0.55  # The fraction of the population that is female.


prior_seed = 3
random_seed = 3
host_theta = 1        # Estimated from the host mitochondria.
npop = 10             # Number of populations
nchrom = 10           # Number of chromosomes sampled from each population.
host_Nm = 2
num_replicates = 25

# Create populations using msprime API
population_config = [ms.PopulationConfiguration(nchrom)
                     for _ in range(npop)]
# Gives population identity (0 -- npop - 1) to each sampled 
# chromosome, 0, 1, 2, ...
populations = np.repeat(range(npop), nchrom)

# The following takes a minute or so. We are generating a target using the
# above parameters.
simulated_target = memory.cache(txmn.sim)(
    (eta, tau, rho),
    host_theta=host_theta,
    host_Nm=host_Nm,
    population_config=population_config,
    populations=populations,
    stats=("fst_mean", "fst_sd", "pi_h"),
    num_replicates=num_replicates,
    random_seed=random_seed
)
                          
target_df = pd.DataFrame(simulated_target.reshape((1, 6)), 
                         columns=("fst_mean", "fst_sd", "pi_h",
                                  "eta", "tau", "rho"))
target_df

# %% [markdown]
# Generate priors. Default is a uniform prior for
# $\tau$, $\rho \sim \mathrm{Beta}(10, 10)$, and $\eta \sim \mathrm{N}(0, 0.1)$.
# This can be generated by the included command line tool `transmission-priorgen`
# according to whatever priors you wish. Use the Docker image with Singularity for painless priors on a compute cluster!

# %%
priors = pd.DataFrame.from_records(
    memory.cache(txmn.generate_priors)(
        nchrom=nchrom,
        num_populations=npop,
        host_theta=host_theta,
        host_Nm=host_Nm,
        num_simulations=100,
        num_replicates=num_replicates,
        prior_seed=3,
        progress_bar=True,
        random_seed=random_seed
    )
)

# %%
abc_out = txmn.Abc(
    target=simulated_target[0:3],  # Get only the summary statistics from
                                   # target.
    # For now, Transmission isn't made to work directly with DataFrames,
    # instead, they must be changed to record arrays.
    param = priors[['eta', 'tau', 'rho']].to_records(index=False),
    sumstat = priors[['fst_mean', 'fst_sd', 'pi_h']].to_records(index=False),
    tol=0.40
)

# %% [markdown]
# We can check out some summary statistics.

# %% {"node_exists": false, "node_name": "e03cd28f35364313a34971a5b578a442"}
print(abc_out.summary())

# %% {"node_exists": false, "node_name": "e25571adfba84e018fa8273819f5e51d"}
density_fig, (ax1, ax2, ax3) = plt.subplots(nrows=1, ncols=3, figsize=(10, 8))

_ = ax1.set_xlim(-1, 1)
_ = x_eta = np.linspace(-1, 1, 100)
_ = eta_posterior_density = stats.gaussian_kde(abc_out.adj_values['eta'])
_ = ax1.plot(x_eta, stats.norm.pdf(x_eta, scale=0.1), 'r-')
_ = ax1.plot(x_eta, eta_posterior_density(x_eta), 'b-')
_ = ax1.set(xlabel=r'$\eta$', ylabel='Density')

_ = ax2.set_xlim(0, 1)
_ = x_tau = np.linspace(0, 1, 100)
_ = tau_posterior_density = stats.gaussian_kde(abc_out.adj_values['tau'])
_ = ax2.plot(x_tau, stats.beta.pdf(x_tau, a=1, b=1), 'r-')
_ = ax2.plot(x_tau, tau_posterior_density(x_tau), 'b-')
_ = ax2.set(xlabel=r'$\tau$')

_ = ax3.set_xlim(0, 1)
_ = x_rho = np.linspace(0, 1, 100)
_ = rho_posterior_density = stats.gaussian_kde(abc_out.adj_values['rho'])
_ = ax3.plot(x_rho, stats.beta.pdf(x_rho, a=10, b=10), 'r-')
_ = ax3.plot(x_rho, rho_posterior_density(x_rho), 'b-')
_ = ax3.set(xlabel=r'$\rho$')


density_fig.savefig('Figures/density.pdf')
density_fig.savefig('Figures/density.png')

# %%

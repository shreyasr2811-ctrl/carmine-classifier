"""
Group a specimen using the fitted Gaussian mixture.

This replaces the hand-weighted index that preceded it. The difference that
matters is where the numbers come from. The old version applied a formula we
chose to boundaries we chose, and smoothed the result into something that
looked like probabilities. This asks a generative model fitted to 274 real
specimens which of its components most likely produced this one, and the
numbers it returns are genuine posteriors.

WHAT THE GROUPS ARE NOT
-----------------------
Not cancer stages. Staging is TNM, and none of tumour size on the gross
specimen, lymph node involvement or distant metastasis has any correlate in
the measurements fed to this model. An unsupervised method cannot recover a
label that is absent from its inputs, and a small integer is not a stage
merely because stages are also small integers.

The groups are types of specimen appearance: how much tissue was flagged, how
densely nucleated it is, and how variable those nuclei are.

WHAT THE REPORTED PROBABILITY IS
--------------------------------
It is the posterior averaged over a bootstrap ensemble of refits, not the
posterior of one fitted mixture. A single fit answers "assuming these four
components are exactly right, which one produced this specimen?", and that
question has a near-certain answer for most inputs. Averaging over mixtures
refitted on resampled cohorts adds the uncertainty in the components
themselves, which is real: the fit came from 274 patients and would move under
a different 274. Specimens deep inside a component stay confident; specimens
near a boundary do not, because the resamples disagree about them.

MISSING MEASUREMENTS
--------------------
Not every input supports every feature. A single uploaded patch has no
involvement fraction -- one patch cannot be a proportion of itself. Rather
than substituting a neutral value, which is what an earlier version did for
focality and which ended up producing groups that differed by whether a
measurement had been possible, the unobserved dimensions are marginalised out
of each Gaussian exactly. The posterior then answers the narrower question
the input can actually support, and reports how many features it used.

ON THE OVERLAP
--------------
Silhouette at the fitted k is about 0.2, which is weak: the groups genuinely
overlap and many specimens sit between them. That is an argument for reporting
the full posterior rather than a hard assignment, not an argument against the
model. A specimen splitting 45/40/15 across three groups is being described
honestly.
"""

from __future__ import annotations

import json
import os

import numpy as np
from joblib import load

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models",
                          "cluster_model.joblib")
META_PATH = os.path.join(os.path.dirname(__file__), "..", "models",
                         "cluster_metadata.json")

_CACHE: dict = {}


def available() -> bool:
    return os.path.exists(MODEL_PATH) and os.path.exists(META_PATH)


def load_model():
    """Returns (bundle, metadata) or (None, None). Never raises."""
    if "bundle" in _CACHE:
        return _CACHE["bundle"], _CACHE["meta"]
    try:
        bundle = load(MODEL_PATH)
        with open(META_PATH, "r", encoding="utf-8") as fh:
            meta = json.load(fh)
        _CACHE["bundle"], _CACHE["meta"] = bundle, meta
        return bundle, meta
    except Exception:
        return None, None


# --------------------------------------------------------------------------
# Posterior with marginalisation
# --------------------------------------------------------------------------

def _member_logprob(z, weights, means, covs, idx):
    """
    log w_k + log N(z_obs ; mu_k[obs], Sigma_k[obs, obs]) for one mixture.

    Marginalising a Gaussian over a subset of its dimensions is exact and
    costs nothing: the marginal of a multivariate normal is the multivariate
    normal on the retained rows and columns. So an input that cannot supply a
    feature is scored on the features it does have, rather than on a made-up
    value for the one it does not.
    """
    k = means.shape[0]
    m = len(idx)
    out = np.empty((z.shape[0], k))
    for c in range(k):
        mu = means[c][idx]
        cov = covs[c][np.ix_(idx, idx)]
        inv = np.linalg.inv(cov)
        _sign, logdet = np.linalg.slogdet(cov)
        dz = z - mu
        maha = np.einsum("ij,jk,ik->i", dz, inv, dz)
        out[:, c] = (np.log(max(float(weights[c]), 1e-300))
                     - 0.5 * (maha + logdet + m * np.log(2.0 * np.pi)))
    return out


def ensemble_posteriors(ens, Z, observed=None):
    """
    Bootstrap-averaged posterior and mean log-likelihood.

    `Z` is already in the scaled space of the reference fit; `observed` lists
    the feature indices actually measured. Members are stored in presentation
    order, so nothing is reordered here.
    """
    W, M, C = ens["weights"], ens["means"], ens["covariances"]
    B, K, d = M.shape
    idx = list(range(d)) if observed is None else list(observed)
    z = np.atleast_2d(np.asarray(Z, dtype=float))[:, idx]

    post = np.zeros((z.shape[0], K))
    ll = np.zeros(z.shape[0])
    for b in range(B):
        lp = _member_logprob(z, W[b], M[b], C[b], idx)
        mx = lp.max(axis=1, keepdims=True)
        ex = np.exp(lp - mx)
        tot = ex.sum(axis=1, keepdims=True)
        post += ex / tot
        ll += (mx[:, 0] + np.log(tot[:, 0]))
    return post / B, ll / B


def _member_posteriors(ens, Z, observed=None):
    """Per-member top-group probability, for reporting how much they disagree."""
    W, M, C = ens["weights"], ens["means"], ens["covariances"]
    B, K, d = M.shape
    idx = list(range(d)) if observed is None else list(observed)
    z = np.atleast_2d(np.asarray(Z, dtype=float))[:, idx]
    out = np.empty((B, z.shape[0], K))
    for b in range(B):
        lp = _member_logprob(z, W[b], M[b], C[b], idx)
        lp -= lp.max(axis=1, keepdims=True)
        e = np.exp(lp)
        out[b] = e / e.sum(axis=1, keepdims=True)
    return out


# --------------------------------------------------------------------------
# Inference
# --------------------------------------------------------------------------

def feature_vector(profile: dict, involvement: float | None = None):
    """
    Assemble the patient-level measurements, in the order the mixture was
    fitted on, together with the indices that are actually observed.

    `involvement` is None for a single patch: one patch is not a fraction of
    itself, and inventing a value for it would decide the answer.
    """
    if not profile or not profile.get("available"):
        return None, None
    x = np.array([[np.nan if involvement is None
                   else float(np.clip(involvement, 0.0, 1.0)),
                   float(profile["nuclear_fraction"]),
                   float(profile["size_cv"])]], dtype=float)
    observed = [j for j in range(x.shape[1]) if np.isfinite(x[0, j])]
    return x, observed


def assign(involvement: float | None, profile: dict) -> dict | None:
    """
    Posterior membership across the fitted groups.

    Components are re-indexed into the presentation order stored at fit time,
    so group 1 is always the least affected regardless of how the mixture
    happened to number its components internally.
    """
    bundle, meta = load_model()
    if bundle is None:
        return None
    x, observed = feature_vector(profile, involvement)
    if x is None or not observed:
        return None

    try:
        fs = bundle["feature_scaler"]
        z = (x - fs.mean_) / fs.scale_          # column-wise, so NaNs stay put
        ens = bundle.get("ensemble")
        if ens is not None:
            post, ll = ensemble_posteriors(ens, z, observed)
            probs = post[0].tolist()
            logp = float(ll[0])
            members = _member_posteriors(ens, z, observed)[:, 0, :]
            spread = float(members.max(axis=1).std())
            n_boot = int(ens["means"].shape[0])
        else:                                   # older bundle, no ensemble
            order = bundle["order"]
            zz = np.nan_to_num(z)
            raw = bundle["gmm"].predict_proba(zz)[0]
            probs = [float(raw[c]) for c in order]
            logp = float(bundle["gmm"].score_samples(zz)[0])
            spread, n_boot = 0.0, 0
    except Exception:
        return None

    total = float(sum(probs))
    probs = [p / total for p in probs] if total > 0 else [1 / len(probs)] * len(probs)

    profiles = meta.get("profiles", [])
    labels = [p.get("label", f"Group {i + 1}") for i, p in enumerate(profiles)] \
        or [f"Group {i + 1}" for i in range(len(probs))]
    descriptors = [p.get("descriptor", "") for p in profiles] or [""] * len(probs)

    names = meta.get("feature_names", [])
    i = int(np.argmax(probs))
    return {
        "labels": labels,
        "descriptors": descriptors,
        "probs": probs,
        "group": labels[i],
        "descriptor": descriptors[i],
        "confidence": float(probs[i]),
        "confidence_spread": spread,
        "log_likelihood": logp,
        "features": {names[j] if j < len(names) else str(j): float(x[0, j])
                     for j in observed},
        "observed": [names[j] if j < len(names) else str(j) for j in observed],
        "n_observed": len(observed),
        "n_features": int(x.shape[1]),
        "marginalised": [names[j] for j in range(x.shape[1])
                         if j not in observed and j < len(names)],
        "n_boot": n_boot,
        "k": len(probs),
        "cohort": int(meta.get("n_patients", 0)),
        "silhouette": meta.get("silhouette_at_k"),
        "bic_preferred_k": meta.get("bic_preferred_k"),
        "profiles": profiles,
    }


def is_outlier(result: dict, meta_threshold: float = -9.0) -> bool:
    """
    Flag a specimen the mixture fits poorly.

    A low log-likelihood means the specimen does not resemble anything in the
    cohort, in which case the posterior is still a valid ranking of bad
    options and should be presented with that caveat. The threshold is per
    fitted dimension, so it scales when features are marginalised out.
    """
    if not result:
        return False
    n = max(int(result.get("n_observed", 1)), 1)
    return bool(result.get("log_likelihood", 0.0) < meta_threshold * n / 3.0)

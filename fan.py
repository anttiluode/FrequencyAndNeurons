"""
FrequencyAndNeurons — what sets gamma frequency: the loop's physics, or how many slots are needed?

Emergent PING gamma: excitatory (E) LIF cells drive fast-spiking basket (I) LIF cells, which inhibit
E back through GABA_A. There is NO pacemaker; the rhythm is whatever the loop does.

Sweeps
  S1  GABA_A decay time tau_I              (mainstream: frequency falls as tau_I grows)
  S2  excitatory drive                     (mainstream: frequency rises with drive)
  S3  number of multiplexed input streams  at FIXED total drive (mainstream: no change)
  S4  admission window per tau_I           (does the open window scale WITH the period?)
"""
import json, numpy as np

DT = 0.05
EL, TH, VR, EINH = -65.0, -50.0, -65.0, -80.0


def simulate(tau_i=5.0, drive=30.0, T=1500.0, NE=400, NI=100, seed=0, streams=1, stream_sd=0.0,
             pings=(), ping_mv=0.0, g_ie=0.9, g_ei=2.0):
    rng = np.random.default_rng(seed)
    n = int(T / DT)
    VE = rng.uniform(EL, TH, NE); VI = rng.uniform(EL, TH, NI)
    rE = np.zeros(NE); rI = np.zeros(NI)
    sE = 0.0; sI = 0.0                      # population synaptic gates (all-to-all, mean field)
    eE, eI = np.exp(-DT / 2.0), np.exp(-DT / tau_i)
    group = np.arange(NE) % streams
    # each stream: slow independent fluctuation of its drive, total mean fixed
    k_ou = np.exp(-DT / 20.0); ou = np.zeros(streams)
    ping_steps = {int(p / DT) for p in pings}
    spE = np.zeros(n); spI = np.zeros(n)
    sq = np.sqrt(2 * DT / 10.0)
    for t in range(n):
        ou = k_ou * ou + np.sqrt(1 - k_ou ** 2) * rng.standard_normal(streams)
        IE = drive + stream_sd * ou[group]
        VE += DT / 20.0 * (-(VE - EL) + IE) + g_ie * sI * (EINH - VE) * DT / 20.0 * 20 + 2.0 * sq * rng.standard_normal(NE)
        VI += DT / 10.0 * (-(VI - EL) + 8.0) + g_ei * sE * (0.0 - VI) * DT / 10.0 * 10 + 1.0 * sq * rng.standard_normal(NI)
        if t in ping_steps:
            VE += ping_mv
        rE -= DT; rI -= DT
        fE = (VE > TH) & (rE <= 0); fI = (VI > TH) & (rI <= 0)
        VE[fE] = VR; VI[fI] = VR; rE[fE] = 2.0; rI[fI] = 1.0
        sE = sE * eE + fE.sum() / NE; sI = sI * eI + fI.sum() / NI
        spE[t] = fE.sum(); spI[t] = fI.sum()
    return spE, spI


def spectrum_peak(sp, T, skip=300.0):
    b = int(1 / DT); x = sp[int(skip / DT):]
    x = x[:len(x) // b * b].reshape(-1, b).sum(1); x = x - x.mean()
    f = np.fft.rfftfreq(len(x), 1e-3); P = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    band = (f > 10) & (f < 200)
    i = np.argmax(P[band]); fpk = f[band][i]
    q = P[band][i] / np.median(P[band])
    return float(fpk), float(q)


def volley_times(spI, skip=300.0):
    """Basket-cell volleys = local maxima of the I population rate (1-ms bins) above 30% of max."""
    b = int(1 / DT); x = spI[:len(spI) // b * b].reshape(-1, b).sum(1).astype(float)
    x = np.convolve(x, np.ones(3) / 3, 'same')
    pk = [i for i in range(1, len(x) - 1) if x[i] >= x[i - 1] and x[i] > x[i + 1] and x[i] > 0.3 * x.max()]
    return np.array([p for p in pk if p > skip], float)


def summary(tau_i=5.0, drive=30.0, seeds=(0, 1, 2), **kw):
    fs, qs, rates, irate, cv = [], [], [], [], []
    for s in seeds:
        spE, spI = simulate(tau_i, drive, seed=s, **kw)
        _, q = spectrum_peak(spI, 1500.0)
        iv = np.diff(volley_times(spI))
        fs.append(1000.0 / np.median(iv)); qs.append(q); cv.append(float(np.std(iv) / np.mean(iv)))
        rates.append(spE[int(300 / DT):].sum() / 400 / 1.2); irate.append(spI[int(300 / DT):].sum() / 100 / 1.2)
    return dict(freq_hz=float(np.mean(fs)), freq_sd=float(np.std(fs)), period_cv=float(np.mean(cv)),
                peak_quality=float(np.mean(qs)),
                E_rate_hz=float(np.mean(rates)), I_rate_hz=float(np.mean(irate)))


def admission_window(tau_i, drive=30.0, seed=5, T=8000.0, n_ping=500, ping_mv=3.0):
    """Tiny pings at random times; response = extra E spikes 1-4 ms later vs the same phase without a ping.
    Phase = time since the last basket (I) volley, as a fraction of the local period."""
    rng = np.random.default_rng(seed + 100)
    pings = np.sort(rng.uniform(300, T - 20, n_ping))
    spE, spI = simulate(tau_i, drive, T=T, seed=seed, pings=pings, ping_mv=ping_mv)
    spE0, spI0 = simulate(tau_i, drive, T=T, seed=seed + 50)                       # reference, no pings
    volleys = lambda spI: volley_times(spI, skip=0.0)
    def phase_of(t_ms, vol):
        j = np.searchsorted(vol, t_ms) - 1
        if j < 0 or j + 1 >= len(vol): return None
        return (t_ms - vol[j]) / (vol[j + 1] - vol[j])
    # baseline E spikes in a 3-ms window as a function of phase, from the no-ping run
    vol0 = volleys(spI0); cum0 = np.cumsum(spE0)
    bins = np.linspace(0, 1, 11); base = [[] for _ in range(10)]
    for t0 in np.arange(300, T - 20, 0.5):
        ph = phase_of(t0, vol0)
        if ph is None: continue
        a, c = int((t0 + 1) / DT), int((t0 + 4) / DT)
        base[min(int(ph * 10), 9)].append(cum0[c] - cum0[a])
    base = np.array([np.mean(b) if b else 0 for b in base])
    vol = volleys(spI); cum = np.cumsum(spE); resp = [[] for _ in range(10)]
    for tp in pings:
        ph = phase_of(tp, vol)
        if ph is None: continue
        a, c = int((tp + 1) / DT), int((tp + 4) / DT)
        resp[min(int(ph * 10), 9)].append(cum[c] - cum[a] - base[min(int(ph * 10), 9)])
    curve = np.array([np.mean(r) if r else np.nan for r in resp])
    period = float(np.nanmedian(np.diff(vol)))
    open_frac = float(np.nanmean(curve > 0.5 * np.nanmax(curve)))
    # primary, model-free window: when in the cycle do E cells actually fire? (no-ping run)
    ph = []
    for t_ms in np.nonzero(spE0)[0] * DT:
        p = phase_of(t_ms, vol0)
        if p is not None: ph += [p] * int(spE0[int(t_ms / DT)])
    ph = np.sort(np.array(ph))
    # shortest circular arc containing 80% of E spikes
    n = len(ph); k = int(0.8 * n); ext = np.r_[ph, ph + 1]
    arc = float(np.min(ext[k:k + n] - ext[:n]))
    return dict(period_ms=period, ping_curve=[None if np.isnan(c) else float(c) for c in curve],
                ping_open_fraction=open_frac, ping_open_ms=open_frac * period,
                E_firing_arc_fraction=arc, E_firing_arc_ms=arc * period,
                E_phase_hist=np.histogram(ph, bins=20, range=(0, 1))[0].tolist())


def main():
    R = {}
    R['S1_tau_gaba'] = {t: summary(tau_i=t) for t in [2.0, 3.0, 5.0, 8.0, 12.0, 16.0]}
    for k, v in R['S1_tau_gaba'].items(): print('S1 tau', k, {a: round(b, 2) for a, b in v.items()}, flush=True)
    R['S2_drive'] = {d: summary(drive=d) for d in [24.0, 27.0, 30.0, 35.0, 40.0, 50.0]}
    for k, v in R['S2_drive'].items(): print('S2 drive', k, {a: round(b, 2) for a, b in v.items()}, flush=True)
    R['S3_streams_fixed_total_drive'] = {n: summary(streams=n, stream_sd=4.0) for n in [1, 2, 4, 8, 16]}
    for k, v in R['S3_streams_fixed_total_drive'].items(): print('S3 streams', k, {a: round(b, 2) for a, b in v.items()}, flush=True)
    R['S4_window'] = {t: admission_window(t) for t in [2.0, 5.0, 8.0, 12.0, 16.0]}
    for k, v in R['S4_window'].items(): print('S4 tau', k, {a: round(b, 3) for a, b in v.items() if isinstance(b, float)}, flush=True)
    json.dump(R, open('results.json', 'w'), indent=1)


if __name__ == '__main__':
    main()

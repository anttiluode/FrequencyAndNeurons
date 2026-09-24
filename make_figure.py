import json, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
R = json.load(open('results.json'))
fig, ax = plt.subplots(1, 4, figsize=(18, 4.2))
S1 = R['S1_tau_gaba']; t = np.array([float(k) for k in S1]); f = np.array([v['freq_hz'] for v in S1.values()])
P = 1000 / f; b, a = np.polyfit(t, P, 1)
ax[0].plot(t, f, 'o-'); ax[0].set_xlabel('GABA_A decay time (ms)'); ax[0].set_ylabel('gamma frequency (Hz)')
ax[0].set_title(f'S1 inhibition decay sets the period\nperiod = {a:.1f} ms + {b:.2f} x tau_GABA', fontsize=9)
S2 = R['S2_drive']; d = [float(k) for k in S2]
ax[1].errorbar(d, [v['freq_hz'] for v in S2.values()], yerr=[v['freq_sd'] for v in S2.values()], fmt='o-')
for x, v in zip(d, S2.values()):
    if v['period_cv'] > 0.15: ax[1].annotate('irregular', (x, v['freq_hz']), fontsize=7, xytext=(-10, -14), textcoords='offset points')
ax[1].set_xlabel('excitatory drive (mV)'); ax[1].set_title('S2 more drive, faster rhythm', fontsize=9)
S3 = R['S3_streams_fixed_total_drive']; n = [int(k) for k in S3]
ax[2].plot(n, [v['freq_hz'] for v in S3.values()], 'o-'); ax[2].set_xscale('log', base=2); ax[2].set_ylim(0, 60)
ax[2].set_xlabel('independent input streams (total drive fixed)'); ax[2].set_title('S3 slot demand alone does not move it', fontsize=9)
S4 = R['S4_window']; per = np.array([v['period_ms'] for v in S4.values()]); win = np.array([v['E_firing_arc_ms'] for v in S4.values()])
ax[3].plot(per, win, 'o-', label='measured E firing window (80% of spikes)')
ax[3].plot(per, win[0] * per / per[0], '--', label='if the window scaled with the period')
ax[3].set_xlabel('period (ms)'); ax[3].set_ylabel('window (ms)'); ax[3].legend(fontsize=8)
ax[3].set_title('S4 window stays ~2-3 ms while the period grows 3.6x', fontsize=9)
fig.tight_layout(); fig.savefig('frequency_and_neurons.png', dpi=110)
print(f'period = {a:.2f} + {b:.3f} tau')

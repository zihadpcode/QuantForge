import zipfile

import numpy as np
import pytest

from quantforge.alpha import evaluation as ev
from quantforge.alpha import signals as sg
from quantforge.alpha.data import AGGTRADES_COLS, BOOKTICKER_COLS, book_from_events, load_binance
from quantforge.alpha.market_making import simulate_market_maker
from quantforge.alpha.simulate import simulate_book


@pytest.fixture(scope="module")
def planted():
    return simulate_book(n_steps=200_000, seed=1)


# ---------------------------------------------------------------- signals ----
def test_imbalance_and_microprice_formulas():
    bid, ask, qb, qa = np.array([99.0]), np.array([101.0]), np.array([3.0]), np.array([1.0])
    assert sg.book_imbalance(qb, qa)[0] == pytest.approx(0.5)
    # heavy bid queue pulls the microprice toward the ask
    assert sg.microprice(bid, ask, qb, qa)[0] == pytest.approx((101 * 3 + 99 * 1) / 4)
    dev = sg.microprice_deviation_bps(bid, ask, qb, qa)[0]
    assert dev == pytest.approx(0.5 * 1.0 / 100 * 1e4)  # I * half-spread / mid


def test_order_flow_imbalance_hand_computed():
    # t1: bid queue +3; t2: bid improves (new queue 2) and ask queue -3; t3: bid level wiped, ask improves
    pb = np.array([10.0, 10.0, 10.5, 10.0])
    qb = np.array([5.0, 8.0, 2.0, 6.0])
    pa = np.array([11.0, 11.0, 11.0, 10.8])
    qa = np.array([7.0, 7.0, 4.0, 1.0])
    ofi = sg.order_flow_imbalance(pb, pa, qb, qa, window=1, normalize=False)
    assert np.isnan(ofi[0])
    np.testing.assert_allclose(ofi[1:], [3.0, 5.0, -3.0])
    np.testing.assert_allclose(sg.order_flow_imbalance(pb, pa, qb, qa, window=2, normalize=False)[2:], [8.0, 2.0])


def test_signals_never_look_ahead(planted):
    b, t0 = planted, 150_000
    rng = np.random.default_rng(0)

    def compute(bid, ask, qb, qa, buy, sell):
        mid = 0.5 * (bid + ask)
        return [
            sg.book_imbalance(qb, qa), sg.microprice_deviation_bps(bid, ask, qb, qa),
            sg.order_flow_imbalance(bid, ask, qb, qa, 20), sg.trade_flow_imbalance(buy, sell, 50),
            sg.past_return_bps(mid, 50), sg.ewma(sg.book_imbalance(qb, qa), 20.0),
            sg.zscore_trailing(sg.past_return_bps(mid, 5), 500),
        ]

    base = compute(b.bid, b.ask, b.bid_qty, b.ask_qty, b.buy_vol, b.sell_vol)
    arrs = [a.copy() for a in (b.bid, b.ask, b.bid_qty, b.ask_qty, b.buy_vol, b.sell_vol)]
    for a in arrs:
        a[t0 + 1:] = a[t0 + 1:] * rng.uniform(0.5, 1.5, a.size - t0 - 1)
    pert = compute(*arrs)
    for x, y in zip(base, pert):
        # guard against a vacuous pass: NaN == NaN under assert_array_equal
        assert np.isfinite(x[t0 - 1000: t0 + 1]).all()
        np.testing.assert_array_equal(x[: t0 + 1], y[: t0 + 1])
        assert not np.array_equal(x[t0 + 1:], y[t0 + 1:], equal_nan=True) or x is base[0]


def test_rolling_helpers():
    x = np.arange(1.0, 7.0)
    np.testing.assert_array_equal(sg.rolling_sum(x, 3)[2:], [6, 9, 12, 15])
    assert np.all(np.isnan(sg.rolling_sum(x, 3)[:2]))
    # a NaN poisons only the windows that contain it
    np.testing.assert_array_equal(sg.rolling_sum(np.array([np.nan, 1, 2, 3, 4]), 2), [np.nan, np.nan, 3, 5, 7])
    z = sg.zscore_trailing(sg.past_return_bps(100 + np.cumsum(np.ones(2000)) * 0.01, 5), 500)
    assert np.isfinite(z[600:]).all()
    e = sg.ewma(np.r_[np.zeros(5), np.ones(200)], halflife=10)
    # the step enters at index 5, so after 10 observations (index 14) half the gap is closed
    assert e[5 + 9] == pytest.approx(0.5, abs=1e-12)


# ------------------------------------------------------------- simulator -----
def test_simulator_ground_truth_is_consistent(planted):
    b = planted
    dm = np.diff(b.mid) / b.tick
    # realised moves are unbiased for the planted conditional mean
    resid = dm - b.true_alpha_ticks[:-1]
    assert abs(resid.mean()) < 4 * resid.std() / np.sqrt(resid.size)
    assert set(np.unique(np.round(dm))) <= {-1.0, 0.0, 1.0}
    np.testing.assert_allclose(b.ask - b.bid, b.tick)


# ------------------------------------------------------------- inference -----
def test_newey_west_matches_statsmodels():
    sm = pytest.importorskip("statsmodels.api")
    rng = np.random.default_rng(3)
    n = 5000
    x = np.cumsum(rng.standard_normal(n)) * 0.01 + rng.standard_normal(n)
    e = np.convolve(rng.standard_normal(n + 9), np.ones(10), "valid")  # MA(9) errors
    y = 0.3 + 0.2 * x + e
    ours = ev.ols_newey_west(y, x, lags=10)
    res = sm.OLS(y, sm.add_constant(x)).fit(cov_type="HAC", cov_kwds={"maxlags": 10, "use_correction": False})
    assert ours.slope == pytest.approx(res.params[1], rel=1e-10)
    assert ours.se_nw == pytest.approx(res.bse[1], rel=1e-8)


def test_recovers_planted_alpha(planted):
    b = planted
    imb = sg.book_imbalance(b.bid_qty, b.ask_qty)
    fwd_ticks = np.diff(b.mid) / b.tick
    est = ev.ols_newey_west(fwd_ticks, imb[:-1], lags=1)
    # the population slope is that of the (clipped) true alpha on the signal
    truth = ev.ols_newey_west(b.true_alpha_ticks[:-1], imb[:-1], lags=1).slope
    assert abs(est.slope - truth) < 4 * est.se_nw
    assert est.t_nw > 10


def test_null_world_false_positive_control():
    """No alpha: Newey-West keeps false positives near nominal; naive OLS t-stats do not."""
    fp_nw = fp_naive = 0
    r2 = []
    for sd in range(40):
        b = simulate_book(n_steps=50_000, beta=0, gamma=0, kappa=0, seed=500 + sd)
        tfi = sg.trade_flow_imbalance(b.buy_vol, b.sell_vol, 50)
        row = ev.ic_decay(tfi, b.mid, [50])[0]
        fp_nw += abs(row["t_nw"]) > 1.96
        fp_naive += abs(row["t_naive"]) > 1.96
        imb = sg.book_imbalance(b.bid_qty, b.ask_qty)
        y = ev.forward_return_bps(b.mid, 10)
        yhat, _ = ev.walk_forward_ridge(np.column_stack([imb, tfi]), y, 10)
        r2.append(ev.oos_r2(y, yhat))
    assert fp_nw <= 6  # nominal 2 of 40; Bartlett NW is mildly undersized in finite samples
    assert fp_naive >= 25  # ignoring overlap "discovers" alpha most of the time
    assert max(r2) < 0.002 and np.mean(r2) < 0.0005


# ------------------------------------------------------------ walk-forward ---
def test_walk_forward_splits_are_purged():
    for tr, te in ev.walk_forward_splits(1000, 4, embargo=25, min_train=200):
        assert tr.max() + 25 < te.min()
        assert te.min() - tr.max() == 26
    with pytest.raises(ValueError):
        ev.walk_forward_ridge(np.zeros((100, 1)), np.zeros(100), horizon=10, embargo=5)


def test_combined_alpha_beats_components_out_of_sample(planted):
    b = planted
    imb = sg.book_imbalance(b.bid_qty, b.ask_qty)
    tfi = sg.trade_flow_imbalance(b.buy_vol, b.sell_vol, 50)
    y = ev.forward_return_bps(b.mid, 10)
    r2 = {}
    for name, X in {"imb": imb[:, None], "tfi": tfi[:, None], "combo": np.column_stack([imb, tfi])}.items():
        yhat, _ = ev.walk_forward_ridge(X, y, 10)
        r2[name] = ev.oos_r2(y, yhat)
    assert r2["combo"] > max(r2["imb"], r2["tfi"]) > 0


# ----------------------------------------------------------------- costs -----
def test_taker_backtest_hand_example():
    mid = np.array([100.0, 101.0, 101.0, 100.0, 100.0])
    bid, ask = mid - 0.05, mid + 0.05
    f = np.array([1.0, np.nan, -1.0, np.nan, 0.0])  # long, then short, horizon 2
    r = ev.taker_backtest(f, bid, ask, horizon=2, threshold_bps=0.0, fee_bps=1.0)
    hs = lambda m: 0.05 / m * 1e4  # half-spread in bps
    # period 0: long 100 -> 101 ; period 1: short 101 -> 100 ; final flatten at t=4
    g0, g1 = 1 / 100 * 1e4, 1 / 101 * 1e4
    np.testing.assert_allclose(r.gross_bps, [g0, g1])
    exp0 = g0 - (hs(100) + 1.0)
    exp1 = g1 - 2 * (hs(101) + 1.0) - (hs(100) + 1.0)
    np.testing.assert_allclose(r.pnl_bps, [exp0, exp1])
    assert r.turnover == 4 and r.n_trades == 2 and r.hit_rate == 1.0
    assert r.breakeven_fee_bps == pytest.approx((g0 + g1 - hs(100) - 2 * hs(101) - hs(100)) / 4)


# ----------------------------------------------------------- Sharpe tests ----
def test_psr_is_uniform_under_the_null():
    rng = np.random.default_rng(7)
    psr = np.array([ev.probabilistic_sharpe_ratio(rng.standard_normal(250)) for _ in range(4000)])
    assert np.mean(psr > 0.95) == pytest.approx(0.05, abs=0.012)
    assert np.mean(psr > 0.5) == pytest.approx(0.5, abs=0.03)


def test_expected_max_sharpe_and_deflation():
    rng = np.random.default_rng(1)
    for n in (10, 100, 1000):
        mc = rng.standard_normal((20_000, n)).max(axis=1).mean()
        assert ev.expected_max_sharpe(n, 1.0) == pytest.approx(mc, rel=0.03)
    r = rng.standard_normal(500) * 0.01 + 0.002
    psr = ev.probabilistic_sharpe_ratio(r)
    d10, d1000 = ev.deflated_sharpe_ratio(r, 10, 0.004), ev.deflated_sharpe_ratio(r, 1000, 0.004)
    assert psr > d10 > d1000


# ------------------------------------------------------------- data I/O ------
def test_binance_loader_as_of_sampling(tmp_path):
    book = [
        [1, 99.9, 2.0, 100.1, 3.0, 1000, 1001],
        [2, 100.0, 1.0, 100.2, 4.0, 1150, 1151],
        [3, 100.0, 5.0, 100.2, 4.0, 1200, 1201],  # exactly on a grid point: visible at 1200
        [4, 100.1, 5.0, 100.3, 1.0, 1250, 1251],
    ]
    trades = [
        [1, 100.1, 0.5, 1, 1, 1050, "false"],  # buyer-aggressor, bucket (1000,1100]
        [2, 100.0, 0.7, 2, 2, 1100, "true"],  # seller-aggressor, still (1000,1100]
        [3, 100.2, 1.0, 3, 3, 1201, "false"],  # (1200,1300]
    ]
    bp, tp = tmp_path / "bt.csv", tmp_path / "at.zip"
    bp.write_text(",".join(BOOKTICKER_COLS) + "\n" + "\n".join(",".join(map(str, r)) for r in book))
    with zipfile.ZipFile(tp, "w") as zf:  # no header row, zipped
        zf.writestr("at.csv", "\n".join(",".join(map(str, r)) for r in trades))
    s = load_binance(bp, tp, step_ms=100)
    np.testing.assert_array_equal(s.time_ms, [1000, 1100, 1200])
    np.testing.assert_array_equal(s.bid, [99.9, 99.9, 100.0])
    np.testing.assert_array_equal(s.bid_qty, [2.0, 2.0, 5.0])
    np.testing.assert_allclose(s.buy_vol, [0.0, 0.5, 0.0])
    np.testing.assert_allclose(s.sell_vol, [0.0, 0.7, 0.0])
    assert s.tick == pytest.approx(0.1)


def test_trades_before_first_quote_are_dropped():
    s = book_from_events([1050, 1150, 1250], [1, 1, 1], [2, 2, 2], [1, 1, 1], [1, 1, 1],
                         trade_time_ms=[10, 500, 1080, 1100], trade_qty=[5, 5, 1, 1],
                         trade_is_buyer_maker=[False] * 4, step_ms=100)
    np.testing.assert_array_equal(s.time_ms, [1100, 1200])
    np.testing.assert_allclose(s.buy_vol, [2.0, 0.0])  # only the trades in (1000, 1100]


def test_book_from_events_handles_unsorted_input():
    s = book_from_events([300, 100, 200], [3, 1, 2], [4, 2, 3], [1, 1, 1], [1, 1, 1], step_ms=100)
    np.testing.assert_array_equal(s.bid, [1, 2, 3])


# --------------------------------------------------------- market making -----
def test_avellaneda_stoikov_replication():
    inv = simulate_market_maker("inventory", n_sims=2000, seed=1).summary()
    sym = simulate_market_maker("symmetric", n_sims=2000, seed=1).summary()
    # AS (2008), gamma = 0.1: inventory 62.94 / 5.89 / q-sd 2.80; symmetric 67.21 / 13.43 / q-sd 8.66
    assert sym["mean_pnl"] == pytest.approx(67.21, rel=0.03)
    assert sym["std_pnl"] == pytest.approx(13.43, rel=0.10)
    assert inv["std_final_q"] == pytest.approx(2.80, rel=0.10)
    assert inv["mean_pnl"] == pytest.approx(62.94, rel=0.04)  # we get ~64.8; see docs/ALPHA.md
    assert inv["std_pnl"] < 0.6 * sym["std_pnl"]
    assert inv["sharpe"] > 1.5 * sym["sharpe"]


def test_alpha_strategy_reduces_to_inventory_without_alpha():
    a = simulate_market_maker("alpha", n_sims=300, seed=4)
    b = simulate_market_maker("inventory", n_sims=300, seed=4)
    np.testing.assert_array_equal(a.pnl, b.pnl)


def test_alpha_skew_defends_against_informed_flow():
    kw = dict(n_sims=2000, seed=2, alpha_sd=2.0, informed=0.5)
    res = {s: simulate_market_maker(s, **kw) for s in ("symmetric", "inventory", "alpha")}
    assert res["alpha"].sharpe > res["inventory"].sharpe > res["symmetric"].sharpe
    # a noisier signal helps less
    weak = simulate_market_maker("alpha", signal_corr=0.3, **kw)
    assert res["inventory"].sharpe < weak.sharpe < res["alpha"].sharpe

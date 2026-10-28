"""Interactive replay of a simulation run.

    PYTHONPATH=src uv run streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from ers.config import assumptions, hospitals_cfg  # noqa: E402
from ers.data.call_text import load as load_call_notes  # noqa: E402
from ers.data.generate import build_scenario  # noqa: E402

# ---------- palette (reference palette: status colours for triage, categorical slots for series) ----------
SEVERITY = {"red": "#d03b3b", "yellow": "#fab219", "green": "#0ca30c", "black": "#52514e"}
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
POLICY_ORDER = ["B0", "B1", "MA-NoNeg", "MA"]
POLICY_COLOR = dict(zip(POLICY_ORDER, SERIES))
UNIT_STATUS = ["idle", "en_route", "on_scene", "transporting", "handover", "working"]
STATUS_COLOR = dict(zip(UNIT_STATUS, SERIES))
AGENTS = ["IncidentAssessment", "Dispatch", "HospitalCoordination", "H1", "H2", "H3", "ResourceAllocation", "CAD"]
GRID, AXIS, MUTED = "#e1e0d9", "#c3c2b7", "#898781"

st.set_page_config(page_title="Emergency Response MAS", layout="wide")


# ---------- data loading ----------
@st.cache_data
def list_runs() -> pd.DataFrame:
    rows = []
    for m in sorted((ROOT / "runs").glob("*/*/manifest.json")):
        d = json.loads(m.read_text())
        rows.append({"experiment": m.parent.parent.name, "run_id": d["run_id"], "scenario": d["scenario"],
                     "seed": d["seed"], "policy": d["policy"], "path": str(m.parent)})
    return pd.DataFrame(rows)


@st.cache_data
def load_run(path: str):
    p = Path(path)
    read = lambda f: [json.loads(l) for l in open(p / f, encoding="utf-8")] if (p / f).exists() else []  # noqa: E731
    return (read("events.jsonl"), read("snapshots.jsonl"), read("decisions.jsonl"),
            json.loads((p / "metrics.json").read_text()), json.loads((p / "manifest.json").read_text()))


@st.cache_data
def call_log(scenario: str, seed: int) -> pd.DataFrame:
    notes = load_call_notes(scenario, seed)
    return pd.DataFrame([{"t": i.t_call, "Incident": i.id, "Code": i.dispatch_code, "Reported": i.reported_victims,
                          "Call-taker note": notes.get(i.id, "")} for i in build_scenario(scenario, seed).incidents])


@st.cache_data
def patient_table(scenario: str, seed: int) -> pd.DataFrame:
    sc = build_scenario(scenario, seed)
    return pd.DataFrame([{"patient": p.id, "incident": i.id, "t_call": i.t_call, "color": p.true_color.value,
                          "category": p.category, "type": i.type} for i in sc.incidents for p in i.patients])


def kpis_at(events, patients: pd.DataFrame, t: int) -> dict:
    cfg, hcfg = assumptions(), hospitals_cfg()
    ids = list(hcfg["hospitals"])
    win = cfg["outcomes"]["window_min"]
    color = dict(zip(patients.patient, patients.color))
    deter = {e["patient"]: e["t"] for e in events if e["type"] == "deteriorated" and e["t"] <= t}
    for p in deter:
        color[p] = "red"
    info = patients.set_index("patient")
    served = arrived = 0
    for e in events:
        if e["type"] != "arrive_hospital" or e["t"] > t:
            continue
        for p in e["patients"]:
            arrived += 1
            lvl = hcfg["capability"][info.at[p, "category"]][ids.index(e["hospital_id"])]
            c = color[p]
            start = deter.get(p, info.at[p, "t_call"]) if c == "red" else info.at[p, "t_call"]
            ok = lvl >= 1 if c == "green" else lvl == 2 and e["t"] <= start + win.get(c, 10**6)
            served += ok
    calls = [e for e in events if e["type"] == "call" and e["t"] <= t]
    first = {}
    for e in events:
        if e["type"] == "unit_on_scene" and e["t"] <= t:
            first.setdefault(e["incident_id"], e["t"])
    resp = [first[c["incident_id"]] - c["t"] for c in calls if c["incident_id"] in first]
    rejected = sum(1 for e in events if e["type"] == "action" and not e["ok"] and e["t"] <= t)
    msgs = [e for e in events if e["type"] == "message" and e["t"] <= t]
    conflicts = sum(1 for m in msgs if m["recipient"] == "ResourceAllocation" and m["message_type"] == "REQUEST")
    return {"calls": len(calls), "arrived": arrived, "served": served,
            "response": round(sum(resp) / len(resp), 1) if resp else None,
            "waiting": len(calls) - len(first), "rejected": rejected, "conflicts": conflicts, "messages": len(msgs)}


def fig_style(fig, height=420):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=30, b=10), plot_bgcolor="rgba(0,0,0,0)",
                      legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0), font=dict(size=12))
    fig.update_xaxes(gridcolor=GRID, linecolor=AXIS, zeroline=False)
    fig.update_yaxes(gridcolor=GRID, linecolor=AXIS, zeroline=False)
    return fig


# ---------- sidebar ----------
runs = list_runs()
st.sidebar.title("Emergency response MAS")
if runs.empty:
    st.info("No runs yet. Run `PYTHONPATH=src uv run python -m ers.eval.run_experiments --config configs/exp_smoke.yaml`.")
    st.stop()
exps = sorted(runs.experiment.unique())
default_exp = next((e for e in ("mvp", "smoke") if e in exps and "MA" in set(runs[runs.experiment == e].policy)), exps[0])
exp = st.sidebar.selectbox("Experiment", exps, index=exps.index(default_exp))
r = runs[runs.experiment == exp]
scenario = st.sidebar.selectbox("Scenario", sorted(r.scenario.unique()))
seed = st.sidebar.selectbox("Seed", sorted(r[r.scenario == scenario].seed.unique()))
pols = [p for p in POLICY_ORDER if p in set(r[(r.scenario == scenario) & (r.seed == seed)].policy)]
policy = st.sidebar.radio("Decision method", pols, index=len(pols) - 1, horizontal=True)
row = r[(r.scenario == scenario) & (r.seed == seed) & (r.policy == policy)].iloc[0]
events, snaps, decisions, metrics, manifest = load_run(row.path)
patients = patient_table(scenario, int(seed))
t_max = snaps[-1]["t"] if snaps else 0

if "t" not in st.session_state or st.session_state.get("run") != row.run_id:
    st.session_state.t, st.session_state.run, st.session_state.playing = 0, row.run_id, False
if "_next_t" in st.session_state:              # set by the play loop before the slider is drawn
    st.session_state.t = st.session_state.pop("_next_t")
c1, c2 = st.sidebar.columns(2)
if c1.button("▶ Play" if not st.session_state.playing else "⏸ Pause", width="stretch"):
    st.session_state.playing = not st.session_state.playing
step = c2.selectbox("Step (min)", [1, 2, 5, 10], index=2, label_visibility="collapsed")
t = st.sidebar.slider("Simulated minute", 0, t_max, key="t")
st.sidebar.caption(f"Model: {manifest.get('model', {}).get('backend', 'rules')} · git {manifest.get('git')}")
snap = next((s for s in snaps if s["t"] == t), snaps[min(t, len(snaps) - 1)])

st.title(f"{metrics['scenario']} — {policy}")
k = kpis_at(events, patients, t)
cols = st.columns(7)
cols[0].metric("Calls received", k["calls"])
cols[1].metric("Incidents waiting for a unit", k["waiting"])
cols[2].metric("Mean response (min)", k["response"] if k["response"] is not None else "–")
cols[3].metric("Patients at hospital", k["arrived"])
cols[4].metric("Served in window", k["served"])
cols[5].metric("Escalated conflicts", k["conflicts"])
cols[6].metric("CAD-blocked actions", k["rejected"])

tab_map, tab_agents, tab_neg, tab_kpi, tab_cmp = st.tabs(
    ["Map & resources", "Agent activity", "Allocation & negotiation", "Performance", "Method comparison"])

# ---------- map & resources ----------
with tab_map:
    left, right = st.columns([3, 2])
    with left:
        fig = go.Figure()
        a = assumptions()["map"]
        n, size = a["zone_grid"], a["size_km"]
        fig.add_vline(x=a["river_x"], line=dict(color="#86b6ef", width=6), opacity=0.5)
        fig.add_trace(go.Scatter(x=[a["bridge"][0]], y=[a["bridge"][1]], mode="markers+text", text=["bridge"],
                                 textposition="top right", marker=dict(symbol="line-ew", size=18, color=AXIS,
                                                                       line=dict(width=4, color=AXIS)),
                                 name="Bridge", hoverinfo="skip"))
        for h in snap["hospitals"]:
            loc = hospitals_cfg()["hospitals"][h["id"]]["location"]
            fig.add_trace(go.Scatter(x=[loc[0]], y=[loc[1]], mode="markers+text", text=[h["id"]],
                                     textposition="bottom center", showlegend=h["id"] == "H1", name="Hospital",
                                     legendgroup="hosp", marker=dict(symbol="square", size=16, color="#52514e"),
                                     hovertemplate=f"{h['id']}: beds {h['beds_used']}/{h['beds']}<extra></extra>"))
        for c in ["red", "yellow", "green"]:
            xs, ys, txt, sz = [], [], [], []
            for i in snap["incidents"]:
                left_n = sum(v for s, v in i["patients"].items() if s in ("waiting", "trapped", "extricating", "ready"))
                if left_n == 0:
                    continue
                worst = next((cc for cc in ["red", "yellow", "green"] if i["colors"].get(cc, 0)), "green")
                if worst != c:
                    continue
                xs.append(i["pos"][0]); ys.append(i["pos"][1]); sz.append(10 + 2 * min(left_n, 15))
                txt.append(f"{i['id']} {i['type']} code {i['code']} · priority {i['priority']}<br>"
                           f"{'triaged' if i['triaged'] else 'reported'}: {i['colors']}<br>left on scene: {left_n}")
            fig.add_trace(go.Scatter(x=xs, y=ys, mode="markers", name=f"Incident ({c})", hovertext=txt,
                                     hoverinfo="text", marker=dict(size=sz, color=SEVERITY[c],
                                                                   line=dict(width=2, color="#fcfcfb"))))
        targets = {i["id"]: i["pos"] for i in snap["incidents"]}
        for s in UNIT_STATUS[:5]:
            us = [u for u in snap["ambulances"] if u["status"] == s]
            if not us:
                continue
            for u in us:
                dest = (hospitals_cfg()["hospitals"][u["hospital"]]["location"] if s == "transporting" and u["hospital"]
                        else targets.get(u["incident"]) if s == "en_route" else None)
                if dest:
                    fig.add_trace(go.Scatter(x=[u["pos"][0], dest[0]], y=[u["pos"][1], dest[1]], mode="lines",
                                             line=dict(color=STATUS_COLOR[s], width=2, dash="dot"),
                                             showlegend=False, hoverinfo="skip"))
            fig.add_trace(go.Scatter(x=[u["pos"][0] for u in us], y=[u["pos"][1] for u in us], mode="markers+text",
                                     text=[u["id"] for u in us], textposition="top center", name=f"Ambulance {s}",
                                     marker=dict(symbol="triangle-up", size=12, color=STATUS_COLOR[s],
                                                 line=dict(width=2, color="#fcfcfb")),
                                     hovertext=[f"{u['id']} {'ALS' if u['als'] else 'BLS'} · {s} · {u['incident'] or ''} "
                                                f"{u['hospital'] or ''}" for u in us], hoverinfo="text"))
        ts = snap["teams"]
        fig.add_trace(go.Scatter(x=[u["pos"][0] for u in ts], y=[u["pos"][1] for u in ts], mode="markers",
                                 name="Rescue team", marker=dict(symbol="diamond", size=11, color=SERIES[6],
                                                                 line=dict(width=2, color="#fcfcfb")),
                                 hovertext=[f"{u['id']} · {u['status']} · {u['incident'] or ''}" for u in ts],
                                 hoverinfo="text"))
        fig.update_xaxes(range=[0, size], title="km", dtick=size / n)
        fig.update_yaxes(range=[0, size], title="km", dtick=size / n, scaleanchor="x")
        st.plotly_chart(fig_style(fig, 620), width="stretch")
        st.caption("Schematic map. Grid lines mark the congestion zones; the blue band is the river, crossed only at the bridge.")
        st.subheader("911 calls received")
        calls_df = call_log(scenario, int(seed))
        calls_df = calls_df[calls_df.t <= t].iloc[::-1]
        if calls_df.empty:
            st.caption("No calls yet.")
        else:
            st.dataframe(calls_df, hide_index=True, width="stretch", height=240,
                         column_config={"Call-taker note": st.column_config.TextColumn(width="large")})
            st.caption("Code = protocol dispatch code (E most urgent). Reported = head count as the caller gave it "
                       "(may differ from the truth). Notes were written once by the local LLM and cached.")
    with right:
        st.subheader("Hospitals (ED)")
        hs = pd.DataFrame([{"Hospital": h["id"], "Beds used": h["beds_used"], "Beds": h["beds"],
                            "Doctors": h["doctors"], "Doctor load": h["doctor_load"], "Nurses": h["nurses"],
                            "Nurse load": h["nurse_load"], "Can take R/Y/G": f"{h['limits']['red']}/{h['limits']['yellow']}/{h['limits']['green']}",
                            "Diversion": "yes" if h["diversion"] else ""} for h in snap["hospitals"]])
        bar = go.Figure()
        bar.add_trace(go.Bar(y=hs.Hospital, x=hs["Beds used"], orientation="h", name="ER beds used",
                             marker=dict(color=SERIES[0], cornerradius=4), hovertemplate="%{x} beds used<extra></extra>"))
        bar.add_trace(go.Bar(y=hs.Hospital, x=hs.Beds - hs["Beds used"], orientation="h", name="free",
                             marker=dict(color=GRID, cornerradius=4), hovertemplate="%{x} beds free<extra></extra>"))
        bar.update_layout(barmode="stack", bargap=0.35)
        st.plotly_chart(fig_style(bar, 200), width="stretch")
        st.dataframe(hs, hide_index=True, width="stretch")
        st.caption(f"Regional reserve pool left: {snap['pool']['nurses']} nurses, {snap['pool']['doctors']} doctors")
        st.subheader("Units")
        counts = pd.DataFrame([{"Unit": "Ambulances", "Status": u["status"]} for u in snap["ambulances"]] +
                              [{"Unit": "Rescue teams", "Status": u["status"]} for u in snap["teams"]])
        ub = go.Figure()
        for s in UNIT_STATUS:
            sub = counts[counts.Status == s].groupby("Unit").size()
            if sub.empty:
                continue
            ub.add_trace(go.Bar(y=sub.index, x=sub.values, orientation="h", name=s,
                                marker=dict(color=STATUS_COLOR[s], line=dict(width=2, color="#fcfcfb"))))
        ub.update_layout(barmode="stack", bargap=0.35)
        st.plotly_chart(fig_style(ub, 180), width="stretch")

# ---------- agent activity ----------
msgs = pd.DataFrame([e for e in events if e["type"] == "message" and e["t"] <= t])
with tab_agents:
    if msgs.empty:
        st.info("No agent messages yet (baseline runs have none).")
    else:
        thread_last = msgs.dropna(subset=["thread_id"]).groupby("thread_id").tail(1)
        open_threads = thread_last[thread_last.message_type.isin(["REQUEST", "PROPOSE", "COUNTER"])]
        cols = st.columns(4)
        for k_, ag in enumerate(AGENTS[:7]):
            sent = msgs[msgs.sender == ag]
            recv = msgs[msgs.recipient == ag]
            last = sent.iloc[-1] if not sent.empty else None
            pending = open_threads[open_threads.recipient == ag]
            with cols[k_ % 4].container(border=True):
                active = last is not None and last.t == t
                st.markdown(f"**{ag}** {'🟢 acting now' if active else '⚪ idle'}")
                st.caption(f"sent {len(sent)} · received {len(recv)} · pending {len(pending)}")
                if last is not None:
                    st.write(f"t={last.t}: `{last.message_type}` → {last.recipient}: {last.proposed_action[:90]}")
        st.subheader("Recent messages")
        show = msgs.tail(40).iloc[::-1][["t", "sender", "recipient", "message_type", "incident_id", "proposed_action",
                                         "reason_code", "round", "thread_id"]]
        st.dataframe(show, hide_index=True, width="stretch", height=420)

# ---------- negotiation ----------
with tab_neg:
    if msgs.empty:
        st.info("No negotiation in this run.")
    else:
        th = msgs.dropna(subset=["thread_id"])
        summ = th.groupby("thread_id").agg(start=("t", "min"), incident=("incident_id", "first"),
                                            messages=("message_id", "count"), rounds=("round", "max"),
                                            outcome=("message_type", "last"),
                                            escalated=("recipient", lambda s: "yes" if (s == "ResourceAllocation").any() else ""))
        c1, c2 = st.columns([2, 3])
        with c1:
            vc = th[th.message_type.isin(["ACCEPT", "REJECT", "COUNTER"])].groupby("message_type").size()
            fb = go.Figure(go.Bar(x=vc.index, y=vc.values, marker=dict(color=SERIES[0], cornerradius=4),
                                  text=vc.values, textposition="outside", hovertemplate="%{x}: %{y}<extra></extra>"))
            st.plotly_chart(fig_style(fb, 260), width="stretch")
            st.dataframe(summ.sort_values("start", ascending=False), width="stretch", height=360)
        with c2:
            pick = st.selectbox("Thread", summ.sort_values("start", ascending=False).index)
            st.dataframe(th[th.thread_id == pick][["t", "round", "sender", "recipient", "message_type",
                                                    "proposed_action", "reason_code"]],
                         hide_index=True, width="stretch")
            d = next((d for d in decisions if d.get("thread") == pick), None)
            if d:
                st.markdown(f"**Decision record** — dispatch proposed `{d['dispatch_proposal']}`, final "
                            f"`{d['final_destination']}` (decided by {d['decided_by']}); rule reference "
                            f"`{d['rule_reference']}`, nearest-hospital baseline `{d['baseline']}`")
                st.dataframe(pd.DataFrame(d["candidates"]), hide_index=True, width="stretch")
    if decisions:
        dd = pd.DataFrame(decisions)
        dd = dd[dd.time_min <= t]
        if not dd.empty:
            st.subheader("Destination decisions vs references")
            agree = (dd.final_destination == dd.rule_reference).mean()
            st.caption(f"{len(dd)} transport decisions so far · same as the rule reference in {agree:.0%} · "
                       f"same as the nearest-hospital baseline in {(dd.final_destination == dd.baseline).mean():.0%}")
            st.dataframe(dd[["time_min", "incident_id", "ambulance", "lead_color", "dispatch_proposal",
                             "final_destination", "decided_by", "rounds", "rule_reference", "baseline"]].iloc[::-1],
                         hide_index=True, width="stretch", height=300)

# ---------- performance over time ----------
with tab_kpi:
    ts_ = list(range(0, t + 1, max(1, t // 60 or 1)))
    series = pd.DataFrame([{"t": x, **kpis_at(events, patients, x)} for x in ts_])
    c1, c2 = st.columns(2)
    for col, (fields, title) in zip([c1, c2, c1, c2], [
            (["arrived", "served"], "Patients at hospital / served in window"),
            (["waiting"], "Incidents waiting for a first unit"),
            (["response"], "Mean response time so far (min)"),
            (["conflicts", "rejected"], "Escalated conflicts / CAD-blocked actions")]):
        f = go.Figure()
        for j, fld in enumerate(fields):
            f.add_trace(go.Scatter(x=series.t, y=series[fld], mode="lines", name=fld, line=dict(width=2, color=SERIES[j]),
                                   hovertemplate=f"t=%{{x}}: %{{y}} {fld}<extra></extra>"))
        f.update_layout(title=title, hovermode="x unified", showlegend=len(fields) > 1)
        col.plotly_chart(fig_style(f, 260), width="stretch")
    st.subheader("Final metrics of this run")
    st.dataframe(pd.DataFrame({"metric": list(metrics), "value": [str(v) for v in metrics.values()]}), hide_index=True, width="stretch")

# ---------- comparison ----------
with tab_cmp:
    summ_path = ROOT / "runs" / exp / "summary.csv"
    if not summ_path.exists():
        st.info("This experiment has no summary.csv yet.")
    else:
        df = pd.read_csv(summ_path)
        metric = st.selectbox("Metric", ["served_rate", "red_in_window_rate", "unserved_critical_incidents",
                                         "capability_match_rate", "response_time_mean", "time_critical_response_mean",
                                         "ambulance_utilisation"])
        g = df.groupby(["scenario", "policy"])[metric].agg(["mean", "std", "count"]).reset_index()
        fc = go.Figure()
        for p in [p for p in POLICY_ORDER if p in set(g.policy)]:
            s = g[g.policy == p]
            fc.add_trace(go.Bar(x=s.scenario, y=s["mean"], name=p, marker=dict(color=POLICY_COLOR[p], cornerradius=4),
                                error_y=dict(type="data", array=s["std"].fillna(0), color=MUTED, thickness=1),
                                hovertemplate=f"{p}: %{{y:.3f}} (n=%{{customdata}})<extra></extra>", customdata=s["count"]))
        fc.update_layout(barmode="group", bargap=0.25, bargroupgap=0.08)
        st.plotly_chart(fig_style(fc, 420), width="stretch")
        st.dataframe(g.pivot(index="scenario", columns="policy", values="mean").round(3), width="stretch")

if st.session_state.playing:
    time.sleep(0.6)
    if st.session_state.t < t_max:
        st.session_state._next_t = min(t_max, st.session_state.t + step)
    else:
        st.session_state.playing = False
    st.rerun()

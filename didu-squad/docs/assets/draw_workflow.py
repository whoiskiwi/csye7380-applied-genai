"""Draw the system workflow figure.

Usage:
    python3 docs/assets/draw_workflow.py en docs/assets/workflow.png
    python3 docs/assets/draw_workflow.py zh docs/assets/workflow_zh.png
"""
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, PathPatch
from matplotlib.path import Path

for f in ["/Library/Fonts/Arial Unicode.ttf", "/System/Library/Fonts/Hiragino Sans GB.ttc",
          "/System/Library/Fonts/STHeiti Medium.ttc"]:
    try:
        fm.fontManager.addfont(f)
    except Exception:
        pass

LANG = sys.argv[1] if len(sys.argv) > 1 else "en"
OUT = sys.argv[2] if len(sys.argv) > 2 else "workflow.png"

if LANG == "zh":
    LBL = ["Hiragino Sans GB", "Arial Unicode MS"]
    TTL = ["Heiti TC", "Hiragino Sans GB", "Arial Unicode MS"]
else:
    LBL = ["Arial Unicode MS"]
    TTL = ["Arial", "Arial Unicode MS"]

T = {
    "en": dict(
        call=("911 call + call-taker", "Human, simulated by code; noisy record"),
        ia=("Incident Assessment Agent", "(duty supervisor)\nRanks incidents, sets priority"),
        dsp=("Dispatch Agent", "(dispatcher + transport)\nUnits, teams, patient destinations"),
        tri=("On-scene triage", "(START rules, code)\nReal severity per patient"),
        ho=("Handover", "ER team; unit back in service"),
        ra=("Resource Allocation Agent", "(incident commander)\nCalled on escalation or conflict"),
        hc=("Hospital Coordination Agent", "(regional hospital coordination)\nAccept / reject admissions, share staff"),
        ha=("Hospital agent ×3", "(ED charge nurse)\nReport limits, divert, request staff"),
        cad_title="CAD + hospital\nstatus board",
        cad_body="(Python code, no model)\n\nRecords all facts:\nambulances, rescue teams,\nincidents, ER beds,\ndoctors & nurses\n(skills, workload),\nregional staff pool\n\nChecks every PROPOSE /\nCOMMIT, then executes\n(no double booking,\nno over-capacity,\nno refusal after departure)",
        e1="① incident record: location, type,\n    reported victims, dispatch code",
        e2="② INFORM incident\n+ priority",
        e3="③ INFORM pre-alert:\nexpected patients, priority",
        e4="④ PROPOSE units + teams\n⑫ COMMIT transport",
        e5="⑤ units on scene",
        e6a="⑥ scene report",
        e6b="⑥ scene report →\nre-assess priority",
        e7="⑦ patients to\ntransport",
        e8="⑧ PROPOSE\nadmission",
        e11="⑪ ACCEPT /\nREJECT /\nCOUNTER\n(≤ 3 rounds)",
        e9="⑨ REQUEST\ncapacity",
        e10="⑩ R/Y/G limits,\nstaff needs,\ndiversion\n(before departure)",
        e13="⑬ COMMIT pool staff",
        e14="⑭ arrives at hospital",
        e15="⑮ unit free; beds,\nstaff updated",
        ea="Ⓐ REQUEST\nunit conflict",
        eb="Ⓑ INFORM\nescalation",
        ec="Ⓒ REQUEST\nno deal after\n3 rounds\n(admission or\nstaff pool)",
        ed="Ⓓ COMMIT ruling",
        ee="Ⓔ result",
        lg=("Strong model (costly)", "Small model (cheap)", "Python code, no model",
            "main flow, every incident", "escalation or conflict only"),
    ),
    "zh": dict(
        call=("911 来电 + 接线员", "（人工，代码模拟）结构化记录，有误差"),
        ia=("事故评估 Agent", "（值班主管）\n多起事故排优先级"),
        dsp=("调度 Agent", "（调度员 + 转运）\n派车和小队，提出送院方案"),
        tri=("现场分诊", "（START 规则，代码）\n每个伤员的真实伤情"),
        ho=("交接", "急诊团队接手，车辆恢复可用"),
        ra=("资源分配 Agent", "（总指挥）\n升级上报或有冲突时调用"),
        hc=("医院协调 Agent", "（区域医院协调中心）\n审批收治，协调人员共享"),
        ha=("医院 Agent ×3", "（急诊负责护士）\n报接收上限、分流、申请人手"),
        cad_title="CAD 系统\n+ 医院状态看板",
        cad_body="（Python 代码，不用模型）\n\n记录所有事实：\n救护车、救援小队、\n事故、急诊床位、\n医生和护士\n（技能、工作量）、\n区域后备人员池\n\n检查每个提议和决定\n后再执行：\n不重复派车\n不超床位和工作量\n出发后不能拒收",
        e1="① 事故记录：地点、类型、\n    报告伤员数、调度代码",
        e2="② INFORM\n事故信息 + 优先级",
        e3="③ INFORM 预先通知：\n预计伤员数、优先级",
        e4="④ PROPOSE 派车和小队\n⑫ COMMIT 转运",
        e5="⑤ 单位到场",
        e6a="⑥ 现场报告",
        e6b="⑥ 现场报告 →\n重新评估优先级",
        e7="⑦ 待送院\n伤员",
        e8="⑧ PROPOSE\n送院方案",
        e11="⑪ ACCEPT /\nREJECT /\nCOUNTER\n（≤3 轮）",
        e9="⑨ REQUEST\n询问容量",
        e10="⑩ 红/黄/绿\n接收上限、\n人手需求、分流\n（仅限出发前）",
        e13="⑬ COMMIT 后备人员分配",
        e14="⑭ 到达医院",
        e15="⑮ 车辆空出，\n床位和人员更新",
        ea="Ⓐ REQUEST\n抢车或小队",
        eb="Ⓑ INFORM\n事故升级",
        ec="Ⓒ REQUEST\n3 轮没谈拢\n（收治或\n后备人员）",
        ed="Ⓓ COMMIT 裁决",
        ee="Ⓔ 结果",
        lg=("贵模型（strong）", "便宜模型（fast）", "Python 代码，不用模型",
            "实线：主流程，每起事故都走", "虚线：只在升级或冲突时走"),
    ),
}[LANG]

RED, GREEN, GREY, EDGE, INK, MUTED = "#b3132b", "#2f7f6d", "#f2f0f1", "#5c6370", "#1f2328", "#5c6370"
FS_T, FS_S, FS_L = 14, 10.5, 10.5

fig, ax = plt.subplots(figsize=(17.4, 12.4))
ax.set_xlim(0, 17.4)
ax.set_ylim(3.6, 15.0)
ax.axis("off")


def box(cx, cy, w, h, title, sub, kind):
    fc, ec, tc, sc = {"strong": (RED, RED, "white", "white"),
                      "fast": (GREEN, GREEN, "white", "white"),
                      "code": (GREY, EDGE, INK, MUTED)}[kind]
    ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h, boxstyle="round,pad=0,rounding_size=0.15",
                                fc=fc, ec=ec, lw=1.6, zorder=2))
    ax.text(cx, cy + 0.2, title, ha="center", va="center", fontsize=FS_T, fontweight="bold",
            color=tc, family=TTL, zorder=3)
    ax.text(cx, cy - 0.2, sub, ha="center", va="center", fontsize=FS_S, color=sc, family=LBL,
            zorder=3, linespacing=1.3)


def arrow(pts, label=None, lpos=None, dashed=False, ha="center", va="bottom"):
    c = RED if dashed else EDGE
    ls = (0, (4, 3)) if dashed else "-"
    if len(pts) > 2:
        ax.add_patch(PathPatch(Path(pts[:-1]), fill=False, ec=c, lw=1.6, ls=ls, zorder=1))
    ax.add_patch(FancyArrowPatch(pts[-2], pts[-1], arrowstyle="-|>", mutation_scale=16, color=c,
                                 lw=1.6, ls=ls, zorder=1, shrinkA=0, shrinkB=0))
    if label:
        ax.text(*lpos, label, ha=ha, va=va, fontsize=FS_L, color=(RED if dashed else INK), family=LBL,
                zorder=4, linespacing=1.25, bbox=dict(fc="white", ec="none", pad=1.2))


# ---------------- layout ----------------
H = 1.0
CADX, CADW = 1.75, 2.7
MX, MW = 7.6, 4.4
RX, RW = 13.6, 4.4
CL, CR = CADX - CADW / 2, CADX + CADW / 2
ML, MR = MX - MW / 2, MX + MW / 2
RL, RR = RX - RW / 2, RX + RW / 2
gx = (CR + ML) / 2          # label x between CAD and main column

r0, r1, r2, r3, r4 = 14.2, 12.4, 10.4, 8.2, 5.8   # 911, IA, DSP, TRI, Handover
yRA, yHC, yHA = 11.4, r3, r4

# CAD column
cad_top, cad_bot = r1 + H / 2, r4 - H / 2
ax.add_patch(FancyBboxPatch((CL, cad_bot), CADW, cad_top - cad_bot, boxstyle="round,pad=0,rounding_size=0.15",
                            fc=GREY, ec=EDGE, lw=1.6, zorder=2))
ax.text(CADX, cad_top - 1.25, T["cad_title"], ha="center", va="center", fontsize=15, fontweight="bold",
        color=INK, family=TTL, linespacing=1.2)
ax.text(CADX, (cad_top + cad_bot) / 2 - 0.55, T["cad_body"], ha="center", va="center", fontsize=10,
        color=MUTED, family=LBL, linespacing=1.35)

box(MX, r0, MW, H * 0.85, *T["call"], "code")
box(MX, r1, MW, H, *T["ia"], "fast")
box(MX, r2, MW, H, *T["dsp"], "fast")
box(MX, r3, MW, H, *T["tri"], "code")
box(MX, r4, MW, H, *T["ho"], "code")
box(RX, yRA, RW, H, *T["ra"], "strong")
box(RX, yHC, RW, H, *T["hc"], "strong")
box(RX, yHA, RW, H, *T["ha"], "fast")

o = 0.22
# ---------------- main flow (solid) ----------------
arrow([(MX, r0 - H * 0.425), (MX, r1 + H / 2)], T["e1"], (MX + 0.12, (r0 + r1) / 2 + 0.05), ha="left", va="center")
arrow([(MX - 0.9, r1 - H / 2), (MX - 0.9, r2 + H / 2)], T["e2"], (MX - 0.78, (r1 + r2) / 2 + 0.25), ha="left", va="center")
# ③ pre-alert: IA -> HC via the right-hand channel
chx = RR + 0.45
arrow([(MR, r1 + 0.25), (chx, r1 + 0.25), (chx, yHC + 0.2), (RR, yHC + 0.2)],
      T["e3"], ((MR + RR) / 2 + 0.6, r1 + 0.31))
# ④ / ⑫ dispatch -> CAD, Ⓔ CAD -> dispatch
arrow([(ML, r2 + o), (CR, r2 + o)], T["e4"], (gx, r2 + o + 0.06))
arrow([(CR, r2 - o), (ML, r2 - o)], T["ee"], (gx, r2 - o - 0.06), dashed=True, va="top")
# ⑤ / ⑥ with triage, ⑥ back to IA
arrow([(CR, r3 + o), (ML, r3 + o)], T["e5"], (gx, r3 + o + 0.06))
arrow([(ML, r3 - o), (CR, r3 - o)], T["e6a"], (gx, r3 - o - 0.06), va="top")
arrow([(CR, r1), (ML, r1)], T["e6b"], (gx, r1 + 0.06))
# ⑦ triage -> dispatch
arrow([(MX - 0.9, r3 + H / 2), (MX - 0.9, r2 - H / 2)], T["e7"], (MX - 0.78, (r2 + r3) / 2), ha="left", va="center")
# ⑧ / ⑪ dispatch <-> hospital coordination (orthogonal pair)
xa, xb = MR + 0.35, MR + 0.85
arrow([(MR, r2 - 0.05), (xb, r2 - 0.05), (xb, yHC + 0.3), (RL, yHC + 0.3)], T["e8"],
      (xb + 0.12, (r2 + yHC) / 2 + 0.25), ha="left", va="center")
arrow([(RL, yHC - 0.05), (xa, yHC - 0.05), (xa, r2 - 0.35), (MR, r2 - 0.35)], T["e11"],
      (xa - 0.12, (r2 + yHC) / 2 - 0.35), ha="right", va="center")
# ⑨ / ⑩ hospital coordination <-> hospitals
arrow([(RX + 0.2, yHC - H / 2), (RX + 0.2, yHA + H / 2)], T["e9"], (RX + 0.08, (yHC + yHA) / 2), ha="right", va="center")
arrow([(RX + 1.2, yHA + H / 2), (RX + 1.2, yHC - H / 2)], T["e10"], (RX + 1.32, (yHC + yHA) / 2), ha="left", va="center")
# ⑬ hospital coordination -> CAD (staff pool) through the gap between triage and handover
yg = (r3 + r4) / 2 + 0.25
arrow([(RL + 0.35, yHC - H / 2), (RL + 0.35, yg), (CR, yg)], T["e13"], (MX, yg + 0.06))
# Ⓔ CAD -> hospital coordination
yg2 = yg - 0.45
arrow([(CR, yg2), (RL + 0.75, yg2), (RL + 0.75, yHC - H / 2)], T["ee"], (MX, yg2 - 0.06), dashed=True, va="top")
# ⑭ / ⑮ with handover
arrow([(CR, r4 + o), (ML, r4 + o)], T["e14"], (gx, r4 + o + 0.06))
arrow([(ML, r4 - o), (CR, r4 - o)], T["e15"], (gx, r4 - o - 0.06), va="top")

# ---------------- escalation / conflicts (dashed) ----------------
arrow([(MR, r2 + 0.3), (RL, yRA - 0.3)], T["ea"], ((MR + RL) / 2 + 0.1, r2 + 0.62), dashed=True, va="top")
arrow([(MR, r1 - 0.2), (RL, yRA + 0.3)], T["eb"], ((MR + RL) / 2, r1 - 0.02), dashed=True)
arrow([(RX, yHC + H / 2), (RX, yRA - H / 2)], T["ec"], (RX + 0.12, (yHC + yRA) / 2), dashed=True, ha="left", va="center")
# Ⓓ ruling -> CAD: through the gap between IA and dispatch
yd = (r1 + r2) / 2 - 0.15
arrow([(RL, yd), (CR, yd)], T["ed"],
      (gx, yd + 0.06), dashed=True)

# ---------------- legend ----------------
ly = 4.25
x = 0.4
for (fc, ec), t in zip([(RED, RED), (GREEN, GREEN), (GREY, EDGE)], T["lg"][:3]):
    ax.add_patch(FancyBboxPatch((x, ly - 0.15), 0.32, 0.3, boxstyle="round,pad=0,rounding_size=0.05",
                                fc=fc, ec=ec, lw=1.4))
    ax.text(x + 0.45, ly, t, va="center", fontsize=12, color=INK, family=LBL)
    x += 3.5
ax.plot([x, x + 0.7], [ly + 0.18, ly + 0.18], color=EDGE, lw=1.6)
ax.text(x + 0.85, ly + 0.18, T["lg"][3], va="center", fontsize=12, color=INK, family=LBL)
ax.plot([x, x + 0.7], [ly - 0.22, ly - 0.22], color=RED, lw=1.6, ls=(0, (4, 3)))
ax.text(x + 0.85, ly - 0.22, T["lg"][4], va="center", fontsize=12, color=RED, family=LBL)

fig.savefig(OUT, dpi=150, bbox_inches="tight", facecolor="white")

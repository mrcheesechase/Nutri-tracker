import io
import json
from datetime import datetime, date, timedelta

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import numpy as np

BG = '#0d1117'
BG2 = '#161b22'
ACCENT = '#58a6ff'
GREEN = '#3fb950'
RED = '#f85149'
YELLOW = '#d29922'
WHITE = '#c9d1d9'
MUTED = '#8b949e'

plt.rcParams.update({
    'figure.facecolor': BG,
    'axes.facecolor': BG2,
    'axes.edgecolor': MUTED,
    'axes.labelcolor': WHITE,
    'xtick.color': WHITE,
    'ytick.color': WHITE,
    'text.color': WHITE,
    'grid.color': '#21262d',
    'grid.linewidth': 0.8,
    'font.family': 'DejaVu Sans',
    'font.size': 10,
})


def _buf(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=BG)
    buf.seek(0)
    plt.close(fig)
    return buf


def weight_progress_chart(weight_logs, user):
    if not weight_logs:
        return None

    logs_asc = list(reversed(weight_logs))
    dates = [datetime.strptime(l['log_date'], '%Y-%m-%d') for l in logs_asc]
    weights = [l['weight_kg'] for l in logs_asc]

    fig, ax = plt.subplots(figsize=(11, 5.5))

    # Actual weight
    ax.plot(dates, weights, 'o-', color=ACCENT, linewidth=2.2, markersize=5,
            markerfacecolor=ACCENT, label='Actual weight', zorder=3)

    # Target trajectory line
    goal_w = user['goal_weight_kg']
    start_w = user['start_weight_kg']
    goal_date = datetime.strptime(user['created_at'][:10], '%Y-%m-%d') + timedelta(weeks=user['goal_weeks'])
    ax.plot([dates[0], goal_date], [start_w, goal_w], '--', color=YELLOW,
            linewidth=1.5, alpha=0.7, label=f'Target trajectory')

    # Goal line
    ax.axhline(goal_w, color=GREEN, linestyle=':', linewidth=1.2, alpha=0.8,
               label=f'Goal: {goal_w:.1f} kg')

    # Fill under curve
    ax.fill_between(dates, weights, min(weights + [goal_w]) - 0.5,
                    alpha=0.08, color=ACCENT)

    # Stats annotation
    if len(weights) > 0:
        lost = start_w - weights[-1]
        rem = weights[-1] - goal_w
        stats = f'Lost: {max(lost,0):.1f} kg\nRemaining: {max(rem,0):.1f} kg\nEntries: {len(weights)}'
        ax.text(0.02, 0.97, stats, transform=ax.transAxes, va='top', fontsize=9,
                color=WHITE, bbox=dict(boxstyle='round,pad=0.5', facecolor=BG, alpha=0.85, edgecolor=MUTED))

    ax.set_title(f"Weight Progress — {user['name']}", fontsize=13, pad=14, color=WHITE)
    ax.set_xlabel('Date', color=MUTED)
    ax.set_ylabel('Weight (kg)', color=MUTED)
    ax.legend(facecolor=BG, edgecolor=MUTED, fontsize=9)
    ax.grid(True, alpha=0.5)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    fig.autofmt_xdate()
    fig.tight_layout()
    return _buf(fig)


def nutrition_summary_chart(food_logs, user):
    if not food_logs:
        return None

    cal = sum(l['calories'] or 0 for l in food_logs)
    pro = sum(l['protein_g'] or 0 for l in food_logs)
    fat = sum(l['fat_g'] or 0 for l in food_logs)
    carb = sum(l['carbs_g'] or 0 for l in food_logs)
    fiber = sum(l['fiber_g'] or 0 for l in food_logs)

    t_cal = user['daily_calorie_target']
    t_pro = user['protein_target_g']
    t_fat = user['fat_target_g']
    t_carb = user['carb_target_g']

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # --- Calorie donut ---
    ax = axes[0]
    pct = min(cal / t_cal, 1.0)
    remaining = max(1 - pct, 0)
    color = GREEN if 0.8 <= pct <= 1.15 else (YELLOW if pct < 0.8 else RED)
    wedge_colors = [color, '#21262d']
    ax.pie([pct, remaining], colors=wedge_colors, startangle=90,
           wedgeprops=dict(width=0.55, edgecolor=BG))
    ax.text(0, 0.12, f'{cal:.0f}', ha='center', va='center', fontsize=18,
            color=WHITE, fontweight='bold')
    ax.text(0, -0.18, 'kcal', ha='center', va='center', fontsize=11, color=MUTED)
    ax.text(0, -0.55, f'Target: {t_cal:.0f}', ha='center', fontsize=9, color=MUTED)
    pct_lbl = f'{pct*100:.0f}% of goal'
    ax.set_title(f'🔥 Calories\n{pct_lbl}', fontsize=11, pad=10)

    # --- Macro bars ---
    ax2 = axes[1]
    labels = ['Protein', 'Fat', 'Carbs', 'Fiber']
    actuals = [pro, fat, carb, fiber]
    targets = [t_pro, t_fat, t_carb, 25]  # 25g fiber standard
    x = np.arange(len(labels))
    w = 0.38

    def bar_color(a, t):
        p = a / t if t > 0 else 0
        return GREEN if 0.8 <= p <= 1.2 else (YELLOW if p < 0.8 else RED)

    b_colors = [bar_color(a, t) for a, t in zip(actuals, targets)]
    bars1 = ax2.bar(x - w/2, actuals, w, color=b_colors, alpha=0.85, label='Actual')
    bars2 = ax2.bar(x + w/2, targets, w, color=MUTED, alpha=0.4, label='Target')

    for bar, val in zip(bars1, actuals):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                 f'{val:.0f}g', ha='center', va='bottom', fontsize=8, color=WHITE)
    for bar, val in zip(bars2, targets):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                 f'{val:.0f}g', ha='center', va='bottom', fontsize=8, color=MUTED)

    ax2.set_xticks(x)
    ax2.set_xticklabels(labels)
    ax2.set_ylabel('Grams')
    ax2.set_title('Macronutrients vs Target', fontsize=11, pad=10)
    ax2.legend(facecolor=BG, edgecolor=MUTED, fontsize=9)
    ax2.grid(True, axis='y', alpha=0.4)

    today_str = date.today().strftime('%B %d, %Y')
    fig.suptitle(f"Today's Nutrition  —  {today_str}", fontsize=13, color=WHITE, y=1.01)
    fig.tight_layout()
    return _buf(fig)


def micronutrient_chart(food_logs, rda, chart_type='vitamins'):
    if not food_logs:
        return None

    aggregated = {}
    for log in food_logs:
        raw = log.get(chart_type, '{}') or '{}'
        try:
            data = json.loads(raw)
        except Exception:
            data = {}
        for k, v in data.items():
            aggregated[k] = aggregated.get(k, 0) + (v or 0)

    rda_section = rda.get(chart_type, {})
    if not rda_section:
        return None

    labels, pcts, colors_list = [], [], []
    for nutrient, rda_val in rda_section.items():
        if not rda_val:
            continue
        actual = aggregated.get(nutrient, 0)
        pct = (actual / rda_val) * 100
        label = (nutrient
                 .replace('vitamin_', 'Vit ')
                 .replace('_mcg', ' (mcg)')
                 .replace('_mg', ' (mg)')
                 .replace('_g', ' (g)')
                 .replace('_', ' ')
                 .title())
        labels.append(label)
        pcts.append(min(pct, 200))
        if pct >= 80:
            colors_list.append(GREEN)
        elif pct >= 40:
            colors_list.append(YELLOW)
        else:
            colors_list.append(RED)

    if not labels:
        return None

    height = max(5, len(labels) * 0.52)
    fig, ax = plt.subplots(figsize=(11, height))

    y = np.arange(len(labels))
    bars = ax.barh(y, pcts, color=colors_list, alpha=0.85, height=0.7)

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    ax.axvline(100, color=WHITE, linestyle='--', alpha=0.4, linewidth=1)
    ax.set_xlabel('% of Daily Recommended Amount')
    ax.set_xlim(0, 210)
    ax.grid(True, axis='x', alpha=0.3)

    for bar, pct_val in zip(bars, pcts):
        ax.text(min(pct_val + 2, 195), bar.get_y() + bar.get_height()/2,
                f'{pct_val:.0f}%', va='center', fontsize=8, color=WHITE)

    titles = {'vitamins': 'Vitamins', 'minerals': 'Minerals', 'amino_acids': 'Amino Acids'}
    ax.set_title(f"{titles.get(chart_type, 'Nutrients')} — % of Daily Recommended Amount",
                 fontsize=12, pad=12)

    patches = [
        mpatches.Patch(color=GREEN, label='Adequate (≥80%)'),
        mpatches.Patch(color=YELLOW, label='Low (40-80%)'),
        mpatches.Patch(color=RED, label='Deficient (<40%)'),
    ]
    ax.legend(handles=patches, loc='lower right', facecolor=BG, edgecolor=MUTED, fontsize=8)
    fig.tight_layout()
    return _buf(fig)


def calorie_history_chart(daily_data, calorie_target):
    if not daily_data:
        return None

    dates = [datetime.strptime(d['log_date'], '%Y-%m-%d') for d in daily_data]
    cals = [d['cal'] or 0 for d in daily_data]

    fig, ax = plt.subplots(figsize=(11, 4.5))
    bar_colors = [GREEN if 0.8 * calorie_target <= c <= 1.1 * calorie_target else
                  (YELLOW if c < 0.8 * calorie_target else RED) for c in cals]
    ax.bar(dates, cals, color=bar_colors, alpha=0.8, width=0.7)
    ax.axhline(calorie_target, color=ACCENT, linestyle='--', linewidth=1.5,
               label=f'Target: {calorie_target:.0f} kcal')

    ax.set_title('Calorie History (Last 14 days)', fontsize=12, pad=12)
    ax.set_ylabel('Calories (kcal)')
    ax.legend(facecolor=BG, edgecolor=MUTED, fontsize=9)
    ax.grid(True, axis='y', alpha=0.4)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    fig.autofmt_xdate()
    fig.tight_layout()
    return _buf(fig)

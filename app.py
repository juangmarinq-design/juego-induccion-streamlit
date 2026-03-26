import copy
import os
import random
from collections import deque
from datetime import datetime, timezone

import pandas as pd
import requests
import streamlit as st

# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================
ROWS = 12
COLS = 16
CELL_SIZE = 42
MAX_SCENARIO_ATTEMPTS = 220
ANIMATION_STEPS = 20

POWER_COLOR = "#DC2626"
GAS_COLOR = "#2563EB"
ROAD_COLOR = "#CBD5E1"
SIDEWALK_COLOR = "#E5E7EB"
CARD_BG = "#FFFFFF"
BG = "#F4F8FB"
TEXT = "#0F172A"
MUTED = "#475569"
SUCCESS = "#16A34A"
WARNING = "#D97706"
DANGER = "#DC2626"

OBSTACLE_WEIGHTS = {"building": 38, "house": 28, "park": 22, "substation": 12}

# ============================================================
# ESTADO DE SESIÓN
# ============================================================

def init_state() -> None:
    defaults = {
        "scenario": None,
        "previous_scenario": None,
        "power_path": [],
        "gas_path": [],
        "mode": "power",
        "done": False,
        "current_score": None,
        "last_message": "Haz clic en A para iniciar la red eléctrica.",
        "selected_current": 800,
        "team_name": "",
        "auto_refresh": True,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ============================================================
# UTILIDADES DE TABLERO
# ============================================================

def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def get_neighbors(cell):
    r, c = cell
    candidates = [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]
    return [(rr, cc) for rr, cc in candidates if 0 <= rr < ROWS and 0 <= cc < COLS]


def free_neighbors_count(cell, obstacles):
    return sum(1 for n in get_neighbors(cell) if n not in obstacles)


def path_exists(start, end, obstacles):
    if start in obstacles or end in obstacles:
        return False
    queue = deque([start])
    visited = {start}
    while queue:
        current = queue.popleft()
        if current == end:
            return True
        for neighbor in get_neighbors(current):
            if neighbor in visited or neighbor in obstacles:
                continue
            visited.add(neighbor)
            queue.append(neighbor)
    return False


def path_segments(path):
    return [(path[i], path[i + 1]) for i in range(len(path) - 1)]


def segment_orientation(seg):
    (r1, c1), (r2, c2) = seg
    if r1 == r2:
        return "horizontal"
    if c1 == c2:
        return "vertical"
    return "other"


def are_parallel(seg1, seg2):
    return segment_orientation(seg1) == segment_orientation(seg2)


def segment_distance(seg1, seg2):
    return min(manhattan(p1, p2) for p1 in seg1 for p2 in seg2)


# ============================================================
# GENERACIÓN DE ESCENARIOS
# ============================================================

def generate_city_map():
    obstacles = {}
    road_cells = set()
    sidewalk_cells = set()
    road_rows = {2, 5, 8, 10}
    road_cols = {3, 7, 11, 14}

    for r in range(ROWS):
        for c in range(COLS):
            if r in road_rows or c in road_cols:
                road_cells.add((r, c))
            else:
                sidewalk_cells.add((r, c))

    target_obstacles = random.randint(34, 50)
    attempts = 0
    while len(obstacles) < target_obstacles and attempts < 900:
        attempts += 1
        kind = random.choices(list(OBSTACLE_WEIGHTS), weights=list(OBSTACLE_WEIGHTS.values()), k=1)[0]
        if kind == "building":
            h = random.choice([1, 2])
            w = random.choice([1, 2])
        elif kind == "house":
            h = 1
            w = 1
        elif kind == "park":
            h = random.choice([1, 2])
            w = random.choice([1, 2])
        else:
            h = 1
            w = random.choice([1, 2])

        r = random.randint(0, ROWS - h)
        c = random.randint(0, COLS - w)
        cells = {(rr, cc) for rr in range(r, r + h) for cc in range(c, c + w)}
        if cells & road_cells:
            continue
        if any(cell in obstacles for cell in cells):
            continue
        for cell in cells:
            obstacles[cell] = kind

    return obstacles, road_cells, sidewalk_cells


def generate_random_points_anywhere(obstacles):
    valid_cells = [(r, c) for r in range(ROWS) for c in range(COLS) if (r, c) not in obstacles]
    random.shuffle(valid_cells)

    power_start = power_end = gas_start = gas_end = None

    for a in valid_cells:
        bs = [x for x in valid_cells if x != a and manhattan(a, x) >= 9]
        if bs:
            power_start = a
            power_end = random.choice(bs)
            break

    remaining = [x for x in valid_cells if x not in {power_start, power_end}]
    for c in remaining:
        ds = [
            x for x in remaining
            if x != c
            and manhattan(c, x) >= 9
            and manhattan(c, power_start) >= 4
            and manhattan(c, power_end) >= 4
            and manhattan(x, power_start) >= 4
            and manhattan(x, power_end) >= 4
        ]
        if ds:
            gas_start = c
            gas_end = random.choice(ds)
            break

    return power_start, power_end, gas_start, gas_end


def generate_valid_scenario():
    for _ in range(MAX_SCENARIO_ATTEMPTS):
        obstacles, road_cells, sidewalk_cells = generate_city_map()
        power_start, power_end, gas_start, gas_end = generate_random_points_anywhere(obstacles)
        points = [power_start, power_end, gas_start, gas_end]
        if any(p is None for p in points):
            continue
        if not path_exists(power_start, power_end, obstacles):
            continue
        if not path_exists(gas_start, gas_end, obstacles):
            continue
        if min(free_neighbors_count(power_start, obstacles), free_neighbors_count(power_end, obstacles),
               free_neighbors_count(gas_start, obstacles), free_neighbors_count(gas_end, obstacles)) < 2:
            continue
        return {
            "obstacles": obstacles,
            "road_cells": road_cells,
            "sidewalk_cells": sidewalk_cells,
            "power_start": power_start,
            "power_end": power_end,
            "gas_start": gas_start,
            "gas_end": gas_end,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    raise RuntimeError("No fue posible generar un escenario jugable.")


def new_scenario(save_previous: bool = True):
    if save_previous and st.session_state.scenario is not None:
        st.session_state.previous_scenario = copy.deepcopy(st.session_state.scenario)
    st.session_state.scenario = generate_valid_scenario()
    reset_paths(message="Nuevo escenario generado. Haz clic en A para iniciar la red eléctrica.")


def reset_paths(message: str = "Reintenta el trazado desde A."):
    s = st.session_state.scenario
    st.session_state.power_path = [s["power_start"]]
    st.session_state.gas_path = [s["gas_start"]]
    st.session_state.mode = "power"
    st.session_state.done = False
    st.session_state.current_score = None
    st.session_state.last_message = message


def retry_same_scenario():
    reset_paths("Mismo escenario. Intenta un nuevo trazado desde A.")


def restore_previous_scenario():
    if st.session_state.previous_scenario is None:
        st.session_state.last_message = "No hay un escenario anterior guardado."
        return
    current = copy.deepcopy(st.session_state.scenario)
    st.session_state.scenario = copy.deepcopy(st.session_state.previous_scenario)
    st.session_state.previous_scenario = current
    reset_paths("Se recuperó el escenario anterior. Haz clic en A para iniciar.")


# ============================================================
# PUNTAJE
# ============================================================

def compute_induction_score(power_path, gas_path, current, road_cells):
    base = 0.0
    close_penalty = 0.0
    parallel_penalty = 0.0
    road_bonus = 0.0

    for p in power_path:
        for g in gas_path:
            d = manhattan(p, g)
            if d == 0:
                base += 1000.0
            else:
                base += 1.0 / (d ** 2)
            if d == 1:
                close_penalty += 8.0
            elif d == 2:
                close_penalty += 3.5
            elif d == 3:
                close_penalty += 1.2

    for ps in path_segments(power_path):
        for gs in path_segments(gas_path):
            if are_parallel(ps, gs):
                dist = segment_distance(ps, gs)
                if dist == 1:
                    parallel_penalty += 9.0
                elif dist == 2:
                    parallel_penalty += 4.0

    road_count = sum(1 for p in power_path if p in road_cells) + sum(1 for g in gas_path if g in road_cells)
    road_bonus = -0.04 * road_count
    total = current * (base + close_penalty + parallel_penalty + road_bonus) / 100.0
    return max(total, 0.0)


def score_style(score):
    if score < 80:
        return SUCCESS, "Inducción baja"
    if score < 150:
        return WARNING, "Inducción moderada"
    return DANGER, "Inducción alta"


# ============================================================
# BACKEND DE RANKING EN VIVO CON SUPABASE (OPCIONAL)
# ============================================================

def live_backend_enabled() -> bool:
    return bool(st.secrets.get("SUPABASE_URL") and st.secrets.get("SUPABASE_KEY"))


def supabase_headers():
    return {
        "apikey": st.secrets["SUPABASE_KEY"],
        "Authorization": f"Bearer {st.secrets['SUPABASE_KEY']}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def fetch_live_ranking(round_id: str) -> pd.DataFrame:
    if not live_backend_enabled():
        return pd.DataFrame(columns=["grupo", "puntaje", "corriente_A", "timestamp"])
    url = (
        f"{st.secrets['SUPABASE_URL'].rstrip('/')}/rest/v1/ranking_scores"
        f"?round_id=eq.{round_id}&select=grupo,puntaje,corriente_A,timestamp"
        f"&order=puntaje.asc,timestamp.asc"
    )
    response = requests.get(url, headers=supabase_headers(), timeout=10)
    response.raise_for_status()
    data = response.json()
    return pd.DataFrame(data)


def submit_live_score(round_id: str, grupo: str, puntaje: float, corriente_A: int):
    if not live_backend_enabled():
        return False, "Backend en vivo no configurado."
    payload = {
        "round_id": round_id,
        "grupo": grupo,
        "puntaje": round(float(puntaje), 4),
        "corriente_A": int(corriente_A),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    url = f"{st.secrets['SUPABASE_URL'].rstrip('/')}/rest/v1/ranking_scores"
    response = requests.post(url, headers=supabase_headers(), json=payload, timeout=10)
    if response.ok:
        return True, "Resultado enviado al ranking en vivo."
    return False, f"No se pudo enviar el resultado: {response.text}"


# ============================================================
# INTERACCIÓN DE TABLERO
# ============================================================

def handle_click(pos):
    s = st.session_state.scenario
    if pos in s["obstacles"]:
        st.session_state.last_message = "Ese espacio está ocupado por un obstáculo."
        return

    if st.session_state.mode == "power":
        path = st.session_state.power_path
        target = s["power_end"]
        start = s["power_start"]
        label = "red eléctrica"
    else:
        path = st.session_state.gas_path
        target = s["gas_end"]
        start = s["gas_start"]
        label = "red de gas"

    if len(path) == 0:
        if pos == start:
            path.append(pos)
            st.session_state.last_message = f"Iniciaste la {label}."
        else:
            st.session_state.last_message = f"Debes iniciar en el punto {('A' if st.session_state.mode == 'power' else 'C')}."
        return

    if pos in path:
        st.session_state.last_message = "No puedes repetir celdas en la misma ruta."
        return

    if pos not in get_neighbors(path[-1]):
        st.session_state.last_message = "Solo puedes avanzar a una celda vecina."
        return

    path.append(pos)
    if pos == target:
        if st.session_state.mode == "power":
            st.session_state.mode = "gas"
            st.session_state.last_message = "Ruta A→B completa. Ahora construye la red de gas desde C hasta D."
        else:
            st.session_state.done = True
            current = st.session_state.selected_current
            st.session_state.current_score = compute_induction_score(
                st.session_state.power_path,
                st.session_state.gas_path,
                current,
                s["road_cells"],
            )
            st.session_state.last_message = "Ruta C→D completa. Puntaje calculado."
    else:
        st.session_state.last_message = f"Trazando {label}."


# ============================================================
# INTERFAZ
# ============================================================

def inject_css():
    st.markdown(
        f"""
        <style>
        .stApp {{ background: {BG}; color: {TEXT}; }}
        .main-title {{ font-size: 2.2rem; font-weight: 800; margin-bottom: .2rem; }}
        .subtitle {{ color: {MUTED}; margin-bottom: 1rem; }}
        .card {{ background: {CARD_BG}; border-radius: 18px; padding: 1rem 1.2rem; box-shadow: 0 8px 24px rgba(15,23,42,.08); margin-bottom: 1rem; }}
        .score-box {{ text-align: center; border-radius: 20px; padding: 1rem; background: linear-gradient(135deg, #ffffff 0%, #eef6ff 100%); box-shadow: 0 10px 28px rgba(15,23,42,.08); }}
        .score-number {{ font-size: 3rem; font-weight: 800; line-height: 1; }}
        .tiny {{ font-size: .88rem; color: {MUTED}; }}
        .legend-pill {{ display: inline-block; margin: .15rem .25rem .15rem 0; padding: .28rem .55rem; border-radius: 999px; background: #EFF6FF; font-size: .86rem; }}
        div.stButton > button {{ width: 100%; min-height: 42px; border-radius: 12px; font-weight: 600; }}
        .board-note {{ color: {MUTED}; font-size: .93rem; margin-bottom: .6rem; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header():
    st.markdown('<div class="main-title">⚡ Evita la Inducción</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">Juego didáctico para explicar tensiones inducidas entre red eléctrica subterránea y red de gas. Diseñado para clase virtual, con modo presentación y ranking en vivo.</div>',
        unsafe_allow_html=True,
    )


def icon_for_cell(pos, scenario):
    if pos == scenario["power_start"]:
        return "🟢", "A"
    if pos == scenario["power_end"]:
        return "🟣", "B"
    if pos == scenario["gas_start"]:
        return "🟦", "C"
    if pos == scenario["gas_end"]:
        return "🟧", "D"
    if pos in st.session_state.power_path:
        return "🔴", "PE"
    if pos in st.session_state.gas_path:
        return "🔵", "PG"
    if pos in scenario["obstacles"]:
        kind = scenario["obstacles"][pos]
        return {"building": "🏢", "house": "🏠", "park": "🌳", "substation": "⚙️"}.get(kind, "⬛"), kind
    if pos in scenario["road_cells"]:
        return "▫️", "calle"
    return "◻️", "libre"


def render_board():
    scenario = st.session_state.scenario
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="board-note"><b>Cómo jugar:</b> haz clic en A y luego en celdas vecinas hasta llegar a B. Después repite desde C hasta D.</div>', unsafe_allow_html=True)
    for r in range(ROWS):
        cols = st.columns(COLS, gap="small")
        for c in range(COLS):
            pos = (r, c)
            icon, help_text = icon_for_cell(pos, scenario)
            if cols[c].button(icon, key=f"cell_{r}_{c}", help=help_text):
                handle_click(pos)
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


def render_sidebar_controls():
    scenario = st.session_state.scenario
    with st.sidebar:
        st.markdown("## 🎛️ Control de clase")
        st.session_state.selected_current = st.slider("Corriente de la red eléctrica [A]", 100, 1500, st.session_state.selected_current, 50)
        round_id = st.text_input("Código de ronda", value="clase-01", help="Usa el mismo código para toda la clase y así todos reportan al mismo ranking.")
        team_name = st.text_input("Nombre del grupo", value=st.session_state.team_name, max_chars=40)
        st.session_state.team_name = team_name
        st.session_state.auto_refresh = st.toggle("Actualizar ranking automáticamente", value=st.session_state.auto_refresh)

        if st.button("🔁 Reintentar trazado"):
            retry_same_scenario()
            st.rerun()
        if st.button("🆕 Nuevo escenario"):
            new_scenario(save_previous=True)
            st.rerun()
        if st.button("⏮️ Recuperar escenario anterior"):
            restore_previous_scenario()
            st.rerun()

        st.markdown("---")
        st.markdown(f"**Modo actual:** {'Red eléctrica A→B' if st.session_state.mode == 'power' else ('Red de gas C→D' if not st.session_state.done else 'Puntaje calculado')} ")
        st.markdown(f"**Mensaje:** {st.session_state.last_message}")
        st.markdown("---")
        st.markdown("**Leyenda**")
        for pill in ["🟢 A inicio eléctrico", "🟣 B fin eléctrico", "🟦 C inicio gas", "🟧 D fin gas", "🔴 ruta eléctrica", "🔵 ruta gas", "🏢/🏠/🌳/⚙️ obstáculos"]:
            st.markdown(f'<span class="legend-pill">{pill}</span>', unsafe_allow_html=True)

        return round_id


def render_score_panel():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    if st.session_state.current_score is None:
        score_color, score_label = MUTED, "Aún no calculado"
        score_number = "--"
    else:
        score_color, score_label = score_style(st.session_state.current_score)
        score_number = f"{st.session_state.current_score:.1f}"
    st.markdown('<div class="score-box">', unsafe_allow_html=True)
    st.markdown(f'<div class="tiny">PUNTAJE</div><div class="score-number" style="color:{score_color};">{score_number}</div><div style="font-weight:700;color:{score_color};">{score_label}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def render_live_ranking(round_id: str):
    st.markdown('<div class="card">', unsafe_allow_html=True)
    top_left, top_right = st.columns([1, 1])
    with top_left:
        st.subheader("🏁 Ranking en vivo")
    with top_right:
        if st.button("Actualizar ranking"):
            st.rerun()

    if st.session_state.done and st.session_state.current_score is not None:
        with st.form("submit_score_form", clear_on_submit=False):
            submitted = st.form_submit_button("Enviar mi puntaje al ranking")
            if submitted:
                if not st.session_state.team_name.strip():
                    st.warning("Escribe el nombre del grupo antes de enviar el resultado.")
                else:
                    ok, msg = submit_live_score(round_id, st.session_state.team_name.strip(), st.session_state.current_score, st.session_state.selected_current)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

    if live_backend_enabled():
        try:
            ranking_df = fetch_live_ranking(round_id)
            if ranking_df.empty:
                st.info("Aún no hay resultados cargados para esta ronda.")
            else:
                ranking_df = ranking_df.rename(columns={"grupo": "Grupo", "puntaje": "Puntaje", "corriente_A": "Corriente [A]", "timestamp": "Fecha UTC"})
                ranking_df.insert(0, "Puesto", range(1, len(ranking_df) + 1))
                st.dataframe(ranking_df, use_container_width=True, hide_index=True)
        except Exception as exc:
            st.error(f"No se pudo leer el ranking en vivo: {exc}")
    else:
        st.info("El ranking en vivo se activa cuando configures Supabase en `st.secrets`.")
        example = pd.DataFrame([
            {"Puesto": 1, "Grupo": "Ejemplo A", "Puntaje": 72.4, "Corriente [A]": 800},
            {"Puesto": 2, "Grupo": "Ejemplo B", "Puntaje": 95.1, "Corriente [A]": 800},
        ])
        st.dataframe(example, use_container_width=True, hide_index=True)

    st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# APP PRINCIPAL
# ============================================================

def main():
    st.set_page_config(page_title="Evita la Inducción", page_icon="⚡", layout="wide")
    init_state()
    inject_css()
    render_header()

    if st.session_state.scenario is None:
        new_scenario(save_previous=False)

    round_id = render_sidebar_controls()

    col_board, col_right = st.columns([3.2, 1.8], gap="large")
    with col_board:
        render_board()
    with col_right:
        render_score_panel()
        st.markdown('<div class="card"><b>Estado del trazado</b><br>', unsafe_allow_html=True)
        st.write(f"Ruta eléctrica: {len(st.session_state.power_path)} celdas")
        st.write(f"Ruta de gas: {len(st.session_state.gas_path)} celdas")
        st.write(f"Escenario creado: {st.session_state.scenario['created_at'][:19].replace('T',' ')} UTC")
        st.markdown('</div>', unsafe_allow_html=True)

    render_live_ranking(round_id)

    if st.session_state.auto_refresh and live_backend_enabled():
        # refresco suave para ranking vivo
        st.caption("Actualización automática activa. La página se refresca cada 15 segundos.")
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=15000, key="ranking_autorefresh")


if __name__ == "__main__":
    main()

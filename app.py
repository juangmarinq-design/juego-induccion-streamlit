import random
from collections import deque

import streamlit as st

st.set_page_config(
    page_title="Evita la Inducción",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# CONFIGURACIÓN
# ============================================================

ROWS = 10
COLS = 14
OBSTACLE_DENSITY = 0.16
MIN_DIST = 7
MAX_SCENARIO_ATTEMPTS = 400

# ============================================================
# ESTILOS
# ============================================================

st.markdown(
    """
    <style>
    .block-container {
        max-width: 1480px;
        padding-top: 0.8rem;
        padding-bottom: 1rem;
    }

    .title-main {
        font-size: 2.35rem;
        font-weight: 900;
        color: #0f172a;
        margin-bottom: 0.15rem;
        letter-spacing: -0.02em;
    }

    .subtitle-main {
        font-size: 1.05rem;
        color: #475569;
        margin-bottom: 1rem;
    }

    .card {
        background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
        border: 1px solid #cbd5e1;
        border-radius: 18px;
        padding: 1rem 1rem 0.9rem 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.05);
    }

    .card-title {
        font-size: 1.12rem;
        font-weight: 800;
        color: #0f172a;
        margin-bottom: 0.75rem;
        letter-spacing: -0.01em;
    }

    .status-box {
        background: linear-gradient(90deg, #eff6ff 0%, #dbeafe 100%);
        border: 1px solid #93c5fd;
        color: #1d4ed8;
        border-radius: 14px;
        padding: 0.85rem 1rem;
        font-size: 1rem;
        font-weight: 700;
        margin-bottom: 0.9rem;
        box-shadow: 0 2px 8px rgba(37, 99, 235, 0.08);
    }

    .board-legend {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px 14px;
    }

    .legend-item {
        font-size: 0.95rem;
        color: #1e293b;
        background: rgba(255,255,255,0.65);
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 0.45rem 0.6rem;
    }

    .score-box {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        border: 2px solid #cbd5e1;
        border-radius: 20px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
    }

    .score-label {
        font-size: 1rem;
        color: #64748b;
        font-weight: 800;
        margin-bottom: 0.45rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }

    .score-value {
        font-size: 3rem;
        font-weight: 900;
        line-height: 1;
        margin-bottom: 0.2rem;
    }

    .score-low { color: #15803d; }
    .score-mid { color: #d97706; }
    .score-high { color: #dc2626; }

    .mini-note {
        font-size: 0.92rem;
        color: #64748b;
        margin-top: 0.35rem;
    }

    .footer-tip {
        color: #64748b;
        font-size: 0.9rem;
        text-align: center;
        margin-top: 0.3rem;
    }

    .info-strip {
        background: #fff7ed;
        color: #9a3412;
        border: 1px solid #fdba74;
        border-radius: 12px;
        padding: 0.75rem 0.9rem;
        font-size: 0.95rem;
        font-weight: 700;
        margin-top: 0.9rem;
    }

    div[data-testid="stButton"] > button {
        width: 100%;
        min-height: 3rem;
        border-radius: 12px;
        font-weight: 800;
        font-size: 1rem;
        border: 1px solid #cbd5e1;
        box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04);
        transition: all 0.12s ease-in-out;
        white-space: nowrap;
        padding: 0.2rem 0.1rem;
    }

    div[data-testid="stButton"] > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 12px rgba(15, 23, 42, 0.08);
    }

    div[data-testid="stButton"] > button:disabled {
        opacity: 0.55;
        border: 1px solid #cbd5e1;
        background: #e5e7eb;
        color: #6b7280;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# UTILIDADES
# ============================================================

def neighbors(r, c):
    for dr, dc in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        rr, cc = r + dr, c + dc
        if 0 <= rr < ROWS and 0 <= cc < COLS:
            yield rr, cc


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def path_exists(start, end, obstacles):
    queue = deque([start])
    visited = {start}

    while queue:
        current = queue.popleft()
        if current == end:
            return True

        for n in neighbors(*current):
            if n not in visited and n not in obstacles:
                visited.add(n)
                queue.append(n)

    return False


def free_neighbors_count(cell, obstacles):
    return sum(1 for n in neighbors(*cell) if n not in obstacles)


def score_path(power_path, gas_path, current):
    base = 0.0
    close_penalty = 0.0
    parallel_penalty = 0.0

    for a in power_path:
        for b in gas_path:
            d = manhattan(a, b)

            if d == 0:
                base += 1000
            else:
                base += 1 / (d ** 2)

            if d == 1:
                close_penalty += 8.0
            elif d == 2:
                close_penalty += 3.5
            elif d == 3:
                close_penalty += 1.2

    power_segments = list(zip(power_path[:-1], power_path[1:]))
    gas_segments = list(zip(gas_path[:-1], gas_path[1:]))

    def orientation(seg):
        (r1, c1), (r2, c2) = seg
        if r1 == r2:
            return "h"
        if c1 == c2:
            return "v"
        return "o"

    for ps in power_segments:
        for gs in gas_segments:
            if orientation(ps) == orientation(gs):
                dmin = min(manhattan(p1, p2) for p1 in ps for p2 in gs)
                if dmin == 1:
                    parallel_penalty += 9.0
                elif dmin == 2:
                    parallel_penalty += 4.0

    total = current * (base + close_penalty + parallel_penalty) / 100.0
    return max(total, 0.0)


def score_class(score):
    if score < 80:
        return "score-low", "Inducción baja"
    if score < 150:
        return "score-mid", "Inducción moderada"
    return "score-high", "Inducción alta"


def cell_style(pos, scenario, power_path, gas_path):
    if pos in scenario["obstacles"]:
        kind = scenario["obstacles"][pos]
        if kind == "building":
            return "🏢", "Edificio (bloque urbano)"
        if kind == "park":
            return "🌿", "Zona verde"
        return "🟫", "Infraestructura crítica"

    if pos == scenario["A"]:
        return "🟢A", "Inicio eléctrico"

    if pos == scenario["B"]:
        return "🟢B", "Fin eléctrico"

    if pos == scenario["C"]:
        return "🔵C", "Inicio gas"

    if pos == scenario["D"]:
        return "🔵D", "Fin gas"

    if pos in power_path:
        return "🔴━", "Red eléctrica"

    if pos in gas_path:
        return "🔵━", "Red de gas"

    return " ", "Celda libre"

# ============================================================
# ESCENARIO
# ============================================================

def generate_obstacles():
    obstacles = {}
    for r in range(ROWS):
        for c in range(COLS):
            if random.random() < OBSTACLE_DENSITY:
                kind = random.choices(
                    ["building", "park", "substation"],
                    weights=[65, 20, 15],
                    k=1,
                )[0]
                obstacles[(r, c)] = kind
    return obstacles


def generate_valid_scenario():
    for _ in range(MAX_SCENARIO_ATTEMPTS):
        obstacles = generate_obstacles()
        free = [(r, c) for r in range(ROWS) for c in range(COLS) if (r, c) not in obstacles]
        random.shuffle(free)

        A = B = C = D = None

        for a in free:
            candidates_b = [x for x in free if x != a and manhattan(a, x) >= MIN_DIST]
            if candidates_b:
                A = a
                B = random.choice(candidates_b)
                break

        if A is None or B is None:
            continue

        remaining = [x for x in free if x not in {A, B}]
        for c in remaining:
            candidates_d = [
                x for x in remaining
                if x != c
                and manhattan(c, x) >= MIN_DIST
                and manhattan(c, A) >= 4
                and manhattan(c, B) >= 4
                and manhattan(x, A) >= 4
                and manhattan(x, B) >= 4
            ]
            if candidates_d:
                C = c
                D = random.choice(candidates_d)
                break

        if None in [A, B, C, D]:
            continue
        if not path_exists(A, B, obstacles):
            continue
        if not path_exists(C, D, obstacles):
            continue
        if free_neighbors_count(A, obstacles) < 2:
            continue
        if free_neighbors_count(B, obstacles) < 2:
            continue
        if free_neighbors_count(C, obstacles) < 2:
            continue
        if free_neighbors_count(D, obstacles) < 2:
            continue

        return {
            "obstacles": obstacles,
            "A": A,
            "B": B,
            "C": C,
            "D": D,
        }

    raise RuntimeError("No fue posible generar un escenario válido.")

# ============================================================
# ESTADO
# ============================================================

def init_state():
    if "scenario" not in st.session_state:
        st.session_state.scenario = generate_valid_scenario()
        st.session_state.previous_scenario = None
        st.session_state.power_path = []
        st.session_state.gas_path = []
        st.session_state.mode = "power"
        st.session_state.done = False
        st.session_state.current_score = None
        st.session_state.current_a = 800


def reset_same_scenario():
    st.session_state.power_path = []
    st.session_state.gas_path = []
    st.session_state.mode = "power"
    st.session_state.done = False
    st.session_state.current_score = None


def new_scenario():
    st.session_state.previous_scenario = st.session_state.scenario
    st.session_state.scenario = generate_valid_scenario()
    reset_same_scenario()


def restore_previous():
    if st.session_state.previous_scenario is not None:
        current = st.session_state.scenario
        st.session_state.scenario = st.session_state.previous_scenario
        st.session_state.previous_scenario = current
        reset_same_scenario()

# ============================================================
# INTERACCIÓN
# ============================================================

def handle_cell_click(pos):
    scenario = st.session_state.scenario

    if pos in scenario["obstacles"]:
        return

    if st.session_state.mode == "power":
        path = st.session_state.power_path
        start = scenario["A"]
        target = scenario["B"]
    else:
        path = st.session_state.gas_path
        start = scenario["C"]
        target = scenario["D"]

    if len(path) == 0:
        if pos == start:
            path.append(pos)
        return

    if pos in path:
        return

    if pos not in neighbors(*path[-1]):
        return

    path.append(pos)

    if pos == target:
        if st.session_state.mode == "power":
            st.session_state.mode = "gas"
        else:
            st.session_state.done = True
            st.session_state.current_score = score_path(
                st.session_state.power_path,
                st.session_state.gas_path,
                st.session_state.current_a,
            )

# ============================================================
# APP
# ============================================================

init_state()
scenario = st.session_state.scenario

st.markdown('<div class="title-main">⚡ Evita la Inducción</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle-main">Diseña el trazado de una red eléctrica y una red de gas minimizando la tensión inducida entre ambas.</div>',
    unsafe_allow_html=True,
)

left, right = st.columns([3.4, 1.3], gap="large")

with left:
    if st.session_state.mode == "power":
        status_msg = "Paso 1. Traza la red eléctrica desde A hasta B. Debes iniciar haciendo clic sobre A."
    elif not st.session_state.done:
        status_msg = "Paso 2. Traza la red de gas desde C hasta D. Debes iniciar haciendo clic sobre C."
    else:
        status_msg = "Ejercicio completado. Revisa el puntaje obtenido o reintenta el mismo escenario."

    st.markdown(f'<div class="status-box">{status_msg}</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Tablero</div>', unsafe_allow_html=True)

    power_path = set(st.session_state.power_path)
    gas_path = set(st.session_state.gas_path)

    for r in range(ROWS):
        cols = st.columns(COLS, gap="small")
        for c in range(COLS):
            pos = (r, c)
            label, help_text = cell_style(pos, scenario, power_path, gas_path)

            disabled = pos in scenario["obstacles"]

            button_type = "secondary"
            if pos in {scenario["A"], scenario["B"], scenario["C"], scenario["D"]}:
                button_type = "primary"

            if cols[c].button(
                label,
                key=f"cell_{r}_{c}",
                help=help_text,
                disabled=disabled,
                use_container_width=True,
                type=button_type,
            ):
                handle_cell_click(pos)
                st.rerun()

    st.markdown(
        '<div class="info-strip">💡 Evita trayectorias paralelas y muy cercanas entre redes para reducir la inducción.</div>',
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Controles</div>', unsafe_allow_html=True)

    current = st.slider(
        "Corriente de la red eléctrica [A]",
        min_value=100,
        max_value=1500,
        value=st.session_state.current_a,
        step=50,
    )
    st.session_state.current_a = current

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔁 Reintentar", use_container_width=True):
            reset_same_scenario()
            st.rerun()
    with c2:
        if st.button("🆕 Nuevo", use_container_width=True):
            new_scenario()
            st.rerun()

    if st.button("↩ Recuperar anterior", use_container_width=True):
        restore_previous()
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Leyenda</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="board-legend">
            <div class="legend-item">🟢 <b>A</b>: inicio de la red eléctrica</div>
            <div class="legend-item">🟢 <b>B</b>: fin de la red eléctrica</div>
            <div class="legend-item">🔵 <b>C</b>: inicio de la red de gas</div>
            <div class="legend-item">🔵 <b>D</b>: fin de la red de gas</div>
            <div class="legend-item">🔴━ red eléctrica</div>
            <div class="legend-item">🔵━ red de gas</div>
            <div class="legend-item">🏢 edificio</div>
            <div class="legend-item">🌿 zona verde</div>
            <div class="legend-item">🟫 infraestructura crítica</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Interpretación del trazado</div>', unsafe_allow_html=True)
    st.write("🔴 Red eléctrica → fuente de campo magnético")
    st.write("🔵 Red de gas → conductor susceptible")
    st.write("⚠️ Cercanía y paralelismo aumentan la inducción")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Estado del ejercicio</div>', unsafe_allow_html=True)

    st.write(f"**Ruta eléctrica:** {len(st.session_state.power_path)} celdas")
    st.write(f"**Ruta de gas:** {len(st.session_state.gas_path)} celdas")

    if st.session_state.done and st.session_state.current_score is not None:
        score = st.session_state.current_score
        cls, desc = score_class(score)
        st.markdown(
            f"""
            <div class="score-box">
                <div class="score-label">Puntaje obtenido</div>
                <div class="score-value {cls}">{score:.1f}</div>
                <div class="{cls}" style="font-weight:900; font-size:1.08rem;">{desc}</div>
                <div class="mini-note">Menor puntaje = menor interacción electromagnética</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="score-box">
                <div class="score-label">Puntaje obtenido</div>
                <div class="score-value" style="color:#94a3b8;">--</div>
                <div style="color:#64748b; font-weight:800;">Aún no calculado</div>
                <div class="mini-note">Completa ambas rutas para obtener el resultado</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        '<div class="footer-tip">Actividad didáctica para analizar interacción entre infraestructuras subterráneas.</div>',
        unsafe_allow_html=True,
    )

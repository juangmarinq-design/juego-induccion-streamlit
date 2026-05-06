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
        max-width: 1600px;
        padding-top: 0.8rem;
        padding-bottom: 1rem;
    }

    .title-main {
        font-size: 2.4rem;
        font-weight: 900;
        color: #0f172a;
        margin-bottom: 0.15rem;
    }

    .subtitle-main {
        font-size: 1.05rem;
        color: #475569;
        margin-bottom: 1rem;
    }

    .card {
        background: #f8fafc;
        border: 1px solid #cbd5e1;
        border-radius: 18px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 3px 10px rgba(15, 23, 42, 0.04);
    }

    .card-title {
        font-size: 1.1rem;
        font-weight: 800;
        margin-bottom: 0.6rem;
        color: #0f172a;
    }

    .status-box {
        background: linear-gradient(90deg, #e0f2fe 0%, #f0f9ff 100%);
        border: 1px solid #7dd3fc;
        color: #0369a1;
        border-radius: 12px;
        padding: 0.8rem;
        font-weight: 700;
        margin-bottom: 0.8rem;
    }

    .score-box {
        border: 2px solid #cbd5e1;
        border-radius: 18px;
        padding: 1rem;
        text-align: center;
        background: white;
    }

    .score-value {
        font-size: 3rem;
        font-weight: 900;
    }

    .score-low { color: #16a34a; }
    .score-mid { color: #d97706; }
    .score-high { color: #dc2626; }

    .info-strip {
        background: #fff7ed;
        border: 1px solid #fdba74;
        padding: 0.7rem;
        border-radius: 10px;
        margin-top: 1rem;
        font-weight: 600;
        color: #9a3412;
    }

    .legend-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px 10px;
    }

    .legend-item {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 0.45rem 0.55rem;
        font-size: 0.93rem;
        color: #1e293b;
    }

    .small-note {
        color: #64748b;
        font-size: 0.9rem;
        margin-top: 0.35rem;
    }

    div[data-testid="stButton"] > button {
        width: 100%;
        min-height: 4.1rem;
        border-radius: 14px;
        font-weight: 800;
        font-size: 1.28rem;
        border: 1px solid #cbd5e1;
        white-space: nowrap;
        padding: 0.25rem 0.05rem;
        transition: all 0.08s ease-in-out;
        box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04);
    }

    div[data-testid="stButton"] > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 10px rgba(15, 23, 42, 0.07);
    }

    div[data-testid="stButton"] > button:disabled {
        opacity: 0.52;
        background: #e5e7eb;
        color: #6b7280;
        border: 1px solid #cbd5e1;
    }

    .footer-tip {
        color: #64748b;
        font-size: 0.9rem;
        text-align: center;
        margin-top: 0.3rem;
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

    FIXED_SCENARIO = {
        "A": (1, 1),
        "B": (8, 12),

        "C": (8, 1),
        "D": (1, 12),

        "obstacles": {

            # Bloque urbano superior
            (1,4): "building",
            (1,5): "building",
            (1,6): "building",

            (2,4): "building",
            (2,5): "building",

            # Bloque central
            (4,5): "building",
            (4,6): "building",
            (4,7): "building",

            (5,5): "building",
            (5,6): "building",

            # Infraestructura crítica
            (3,10): "substation",
            (4,10): "substation",

            # Zona verde
            (7,4): "park",
            (7,5): "park",

            # Corredor inferior
            (8,7): "building",
            (8,8): "building",

            # Zona derecha
            (6,11): "building",
            (7,11): "building",

            # Obstáculos aislados
            (2,8): "building",
            (6,3): "building",
            (3,2): "park",
        }
    }

    if "scenario" not in st.session_state:
        st.session_state.scenario = FIXED_SCENARIO

        st.session_state.previous_scenario = None
        st.session_state.power_path = []
        st.session_state.gas_path = []
        st.session_state.mode = "power"
        st.session_state.done = False
        st.session_state.current_score = None
        st.session_state.I = 800

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

def undo_step():
    if st.session_state.mode == "power":
        if st.session_state.power_path:
            st.session_state.power_path.pop()
    elif st.session_state.mode == "gas":
        if st.session_state.gas_path:
            st.session_state.gas_path.pop()

    st.session_state.done = False
    st.session_state.current_score = None

# ============================================================
# GUÍA INTELIGENTE
# ============================================================

def valid_next_cells():
    scenario = st.session_state.scenario

    if st.session_state.mode == "power":
        path = st.session_state.power_path
        start = scenario["A"]
    else:
        path = st.session_state.gas_path
        start = scenario["C"]

    if len(path) == 0:
        return {start}

    return {n for n in neighbors(*path[-1]) if n not in scenario["obstacles"] and n not in path}

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
                st.session_state.I,
            )

# ============================================================
# VISUALIZACIÓN DE CELDAS
# ============================================================

def cell_style(pos, scenario, power_path, gas_path, valid_cells):
    if pos in scenario["obstacles"]:
        kind = scenario["obstacles"][pos]
        if kind == "building":
            return "🏢", "Edificio"
        if kind == "park":
            return "🌳", "Zona verde"
        return "⚡", "Infraestructura crítica"

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

    if pos in valid_cells:
        return "▫️", "Movimiento válido"

    return "·", "Celda libre"

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

left, right = st.columns([4.2, 1.1], gap="large")

with left:
    if st.session_state.mode == "power":
        status_msg = "Paso 1. Traza la red eléctrica desde A hasta B."
        progress = len(st.session_state.power_path) / max(1, manhattan(scenario["A"], scenario["B"]))
    elif not st.session_state.done:
        status_msg = "Paso 2. Traza la red de gas desde C hasta D."
        progress = len(st.session_state.gas_path) / max(1, manhattan(scenario["C"], scenario["D"]))
    else:
        status_msg = "Ejercicio completado. Revisa el puntaje o reintenta."
        progress = 1.0

    st.markdown(f'<div class="status-box">{status_msg}</div>', unsafe_allow_html=True)
    st.progress(min(progress, 1.0))

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Mapa tipo ciudad</div>', unsafe_allow_html=True)

    power_path = set(st.session_state.power_path)
    gas_path = set(st.session_state.gas_path)
    valid_cells = valid_next_cells()

    for r in range(ROWS):
        cols = st.columns(COLS)
        for c in range(COLS):
            pos = (r, c)
            label, help_text = cell_style(pos, scenario, power_path, gas_path, valid_cells)
            disabled = pos in scenario["obstacles"]

            button_type = "secondary"
            if pos in valid_cells or pos in {scenario["A"], scenario["B"], scenario["C"], scenario["D"]}:
                button_type = "primary"

            if cols[c].button(
                label,
                key=f"{r}-{c}",
                use_container_width=True,
                help=help_text,
                disabled=disabled,
                type=button_type,
            ):
                handle_cell_click(pos)
                st.rerun()

    st.markdown(
        '<div class="info-strip">💡 Guía inteligente: las celdas resaltadas indican por dónde puedes continuar el trazado.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Controles</div>', unsafe_allow_html=True)

    st.slider("Corriente [A]", 100, 1500, key="I")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("↩ Deshacer", use_container_width=True):
            undo_step()
            st.rerun()
    with c2:
        if st.button("🔁 Reintentar", use_container_width=True):
            reset_same_scenario()
            st.rerun()

    c3, c4 = st.columns(2)
    with c3:
        if st.button("🆕 Nuevo", use_container_width=True):
            new_scenario()
            st.rerun()
    with c4:
        if st.button("⤺ Anterior", use_container_width=True):
            restore_previous()
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Leyenda</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="legend-grid">
            <div class="legend-item">🟢A inicio eléctrico</div>
            <div class="legend-item">🟢B fin eléctrico</div>
            <div class="legend-item">🔵C inicio gas</div>
            <div class="legend-item">🔵D fin gas</div>
            <div class="legend-item">🔴━ red eléctrica</div>
            <div class="legend-item">🔵━ red de gas</div>
            <div class="legend-item">🏢 edificio</div>
            <div class="legend-item">🌳 parque</div>
            <div class="legend-item">⚡ infraestructura crítica</div>
            <div class="legend-item">▫️ movimiento válido</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
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
                <div>Puntaje</div>
                <div class="score-value {cls}">{score:.1f}</div>
                <div style="font-weight:800;">{desc}</div>
                <div class="small-note">Menor puntaje = menor interacción electromagnética</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="score-box">
                <div>Puntaje</div>
                <div class="score-value" style="color:#94a3b8;">--</div>
                <div style="font-weight:800;color:#64748b;">Aún no calculado</div>
                <div class="small-note">Completa ambas rutas para obtener el resultado</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown(
        '<div class="footer-tip">Actividad didáctica para analizar interacción entre infraestructuras subterráneas.</div>',
        unsafe_allow_html=True,
    )

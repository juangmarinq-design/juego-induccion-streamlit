import random
from collections import deque

import streamlit as st

st.set_page_config(
    page_title="Evita la Inducción",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# CONFIG
# ============================================================

ROWS = 10
COLS = 14
OBSTACLE_DENSITY = 0.18
MIN_DIST = 7

# ============================================================
# ESTILOS
# ============================================================

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 1400px;
    }

    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #0f172a;
        margin-bottom: 0.2rem;
    }

    .subtitle {
        font-size: 1.05rem;
        color: #334155;
        margin-bottom: 1rem;
    }

    .panel-card {
        background: #f8fafc;
        border: 1px solid #cbd5e1;
        border-radius: 16px;
        padding: 1rem 1rem 0.8rem 1rem;
        margin-bottom: 1rem;
    }

    .panel-title {
        font-size: 1.2rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 0.6rem;
    }

    .status-box {
        background: #eff6ff;
        border: 1px solid #93c5fd;
        color: #1e3a8a;
        border-radius: 12px;
        padding: 0.75rem 0.9rem;
        font-size: 1rem;
        font-weight: 600;
        margin-bottom: 0.8rem;
    }

    .score-box {
        background: #ffffff;
        border: 2px solid #cbd5e1;
        border-radius: 18px;
        padding: 1rem;
        text-align: center;
        margin-top: 0.8rem;
    }

    .score-label {
        font-size: 1rem;
        color: #475569;
        font-weight: 700;
        margin-bottom: 0.4rem;
    }

    .score-value {
        font-size: 2.6rem;
        font-weight: 800;
        line-height: 1.1;
    }

    .score-low { color: #15803d; }
    .score-mid { color: #d97706; }
    .score-high { color: #dc2626; }

    .legend-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px 12px;
        margin-top: 0.4rem;
    }

    .legend-item {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.95rem;
        color: #1f2937;
    }

    .legend-swatch {
        width: 22px;
        height: 22px;
        border-radius: 6px;
        border: 1px solid #475569;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 0.8rem;
        font-weight: 700;
        color: white;
        flex-shrink: 0;
    }

    .board-wrap {
        background: #e2e8f0;
        border: 2px solid #94a3b8;
        border-radius: 18px;
        padding: 14px;
        overflow-x: auto;
    }

    .board-row {
        display: flex;
        gap: 4px;
        margin-bottom: 4px;
    }

    .board-cell {
        width: 46px;
        height: 46px;
        border-radius: 10px;
        border: 1px solid #94a3b8;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 800;
        font-size: 1rem;
        user-select: none;
    }

    .cell-road {
        background: #cbd5e1;
        color: #334155;
    }

    .cell-empty {
        background: #f8fafc;
        color: #334155;
    }

    .cell-building {
        background: linear-gradient(180deg, #6b7280 0%, #4b5563 100%);
        color: white;
    }

    .cell-park {
        background: #86efac;
        color: #166534;
    }

    .cell-substation {
        background: #d1d5db;
        color: #111827;
    }

    .cell-power {
        background: #dc2626;
        color: white;
    }

    .cell-gas {
        background: #2563eb;
        color: white;
    }

    .cell-a, .cell-b {
        background: #16a34a;
        color: white;
        border: 2px solid #14532d;
    }

    .cell-c, .cell-d {
        background: #0891b2;
        color: white;
        border: 2px solid #164e63;
    }

    .cell-target {
        box-shadow: 0 0 0 4px rgba(250, 204, 21, 0.65) inset;
    }

    div[data-testid="stButton"] > button {
        width: 100%;
        border-radius: 12px;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# UTILS
# ============================================================

def neighbors(r, c):
    for dr, dc in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        rr, cc = r + dr, c + dc
        if 0 <= rr < ROWS and 0 <= cc < COLS:
            yield rr, cc


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def path_exists(start, end, obstacles):
    q = deque([start])
    visited = {start}

    while q:
        node = q.popleft()
        if node == end:
            return True
        for n in neighbors(*node):
            if n not in visited and n not in obstacles:
                visited.add(n)
                q.append(n)
    return False


def free_neighbors_count(cell, obstacles):
    return sum(1 for n in neighbors(*cell) if n not in obstacles)


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
                    weights=[70, 20, 10],
                    k=1,
                )[0]
                obstacles[(r, c)] = kind
    return obstacles


def generate_valid_scenario():
    max_attempts = 400
    for _ in range(max_attempts):
        obstacles = generate_obstacles()
        free = [(r, c) for r in range(ROWS) for c in range(COLS) if (r, c) not in obstacles]
        random.shuffle(free)

        A = B = C = D = None

        for a in free:
            Bs = [x for x in free if x != a and manhattan(a, x) >= MIN_DIST]
            if Bs:
                A = a
                B = random.choice(Bs)
                break

        if A is None or B is None:
            continue

        remaining = [x for x in free if x not in {A, B}]
        for c in remaining:
            Ds = [
                x for x in remaining
                if x != c
                and manhattan(c, x) >= MIN_DIST
                and manhattan(c, A) >= 4
                and manhattan(c, B) >= 4
                and manhattan(x, A) >= 4
                and manhattan(x, B) >= 4
            ]
            if Ds:
                C = c
                D = random.choice(Ds)
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
# PUNTAJE
# ============================================================

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
# ESTADO
# ============================================================

def init_state():
    if "scenario" not in st.session_state:
        scenario = generate_valid_scenario()
        st.session_state.scenario = scenario
        st.session_state.previous_scenario = None
        st.session_state.power_path = []
        st.session_state.gas_path = []
        st.session_state.mode = "power"
        st.session_state.done = False
        st.session_state.current_score = None


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
    prev = st.session_state.get("previous_scenario")
    if prev is not None:
        current = st.session_state.scenario
        st.session_state.scenario = prev
        st.session_state.previous_scenario = current
        reset_same_scenario()


init_state()
scenario = st.session_state.scenario

# ============================================================
# LÓGICA DE CLIC
# ============================================================

def handle_cell_click(pos):
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

    if pos in neighbors(*path[-1]):
        path.append(pos)

        if pos == target:
            if st.session_state.mode == "power":
                st.session_state.mode = "gas"
            else:
                st.session_state.done = True


# ============================================================
# CABECERA
# ============================================================

st.markdown('<div class="main-title">⚡ Evita la Inducción</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Diseña una red eléctrica A→B y una red de gas C→D minimizando su interacción.</div>',
    unsafe_allow_html=True,
)

left, right = st.columns([3.2, 1.3], gap="large")

# ============================================================
# TABLERO
# ============================================================

with left:
    if st.session_state.mode == "power":
        current_status = "Traza la red eléctrica desde A hasta B. Inicia haciendo clic sobre A."
        active_target = scenario["B"]
    elif not st.session_state.done:
        current_status = "Ahora traza la red de gas desde C hasta D. Inicia haciendo clic sobre C."
        active_target = scenario["D"]
    else:
        current_status = "Escenario completado. Revisa el puntaje y reintenta o genera un nuevo caso."
        active_target = None

    st.markdown(f'<div class="status-box">{current_status}</div>', unsafe_allow_html=True)

    board_html = ['<div class="board-wrap">']
    for r in range(ROWS):
        board_html.append('<div class="board-row">')
        for c in range(COLS):
            pos = (r, c)
            label = ""
            classes = ["board-cell"]

            if pos in scenario["obstacles"]:
                kind = scenario["obstacles"][pos]
                if kind == "building":
                    classes.append("cell-building")
                    label = "🏢"
                elif kind == "park":
                    classes.append("cell-park")
                    label = "🌳"
                else:
                    classes.append("cell-substation")
                    label = "⚡"
            elif pos == scenario["A"]:
                classes.append("cell-a")
                label = "A"
            elif pos == scenario["B"]:
                classes.append("cell-b")
                label = "B"
            elif pos == scenario["C"]:
                classes.append("cell-c")
                label = "C"
            elif pos == scenario["D"]:
                classes.append("cell-d")
                label = "D"
            elif pos in st.session_state.power_path:
                classes.append("cell-power")
                label = "E"
            elif pos in st.session_state.gas_path:
                classes.append("cell-gas")
                label = "G"
            else:
                classes.append("cell-empty")

            if active_target is not None and pos == active_target:
                classes.append("cell-target")

            board_html.append(f'<div class="{" ".join(classes)}">{label}</div>')
        board_html.append("</div>")
    board_html.append("</div>")

    st.markdown("".join(board_html), unsafe_allow_html=True)

    st.write("### Selecciona la siguiente celda")
    for r in range(ROWS):
        cols = st.columns(COLS)
        for c in range(COLS):
            pos = (r, c)

            if pos in scenario["obstacles"]:
                label = " "
                disabled = True
            elif pos == scenario["A"]:
                label = "A"
                disabled = False
            elif pos == scenario["B"]:
                label = "B"
                disabled = False
            elif pos == scenario["C"]:
                label = "C"
                disabled = False
            elif pos == scenario["D"]:
                label = "D"
                disabled = False
            else:
                label = "·"
                disabled = False

            if cols[c].button(label, key=f"cell_{r}_{c}", disabled=disabled):
                handle_cell_click(pos)
                if st.session_state.done:
                    st.session_state.current_score = score_path(
                        st.session_state.power_path,
                        st.session_state.gas_path,
                        st.session_state.current_a if "current_a" in st.session_state else 800,
                    )
                st.rerun()

# ============================================================
# PANEL DERECHO
# ============================================================

with right:
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">Controles</div>', unsafe_allow_html=True)

    current = st.slider("Corriente de la red eléctrica [A]", 100, 1500, 800, 50)
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

    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">Leyenda</div>', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="legend-grid">
            <div class="legend-item"><span class="legend-swatch" style="background:#16a34a;">A</span> Inicio eléctrico</div>
            <div class="legend-item"><span class="legend-swatch" style="background:#16a34a;">B</span> Fin eléctrico</div>
            <div class="legend-item"><span class="legend-swatch" style="background:#0891b2;">C</span> Inicio gas</div>
            <div class="legend-item"><span class="legend-swatch" style="background:#0891b2;">D</span> Fin gas</div>
            <div class="legend-item"><span class="legend-swatch" style="background:#dc2626;">E</span> Ruta eléctrica</div>
            <div class="legend-item"><span class="legend-swatch" style="background:#2563eb;">G</span> Ruta gas</div>
            <div class="legend-item"><span class="legend-swatch" style="background:#4b5563;">🏢</span> Edificio</div>
            <div class="legend-item"><span class="legend-swatch" style="background:#86efac;color:#166534;">🌳</span> Parque</div>
            <div class="legend-item"><span class="legend-swatch" style="background:#d1d5db;color:#111827;">⚡</span> Subestación</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">Estado del ejercicio</div>', unsafe_allow_html=True)

    st.write(f"**Ruta eléctrica:** {len(st.session_state.power_path)} celdas")
    st.write(f"**Ruta de gas:** {len(st.session_state.gas_path)} celdas")

    if st.session_state.done:
        score = score_path(st.session_state.power_path, st.session_state.gas_path, current)
        cls, desc = score_class(score)
        st.markdown(
            f"""
            <div class="score-box">
                <div class="score-label">Puntaje obtenido</div>
                <div class="score-value {cls}">{score:.1f}</div>
                <div class="{cls}" style="font-weight:700; font-size:1.05rem;">{desc}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="score-box">
                <div class="score-label">Puntaje obtenido</div>
                <div class="score-value" style="color:#64748b;">--</div>
                <div style="color:#64748b; font-weight:700;">Aún no calculado</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

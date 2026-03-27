import math
import random
from collections import deque

import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from streamlit_image_coordinates import streamlit_image_coordinates

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
CELL = 56
PAD = 18
GRID_GAP = 2

OBSTACLE_DENSITY = 0.17
MIN_DIST = 7
MAX_SCENARIO_ATTEMPTS = 500

ROAD_COLOR = "#D6DEE8"
EMPTY_COLOR = "#F8FAFC"
GRID_LINE = "#B8C4D1"
POWER_COLOR = "#D62828"
GAS_COLOR = "#2563EB"
A_COLOR = "#16A34A"
B_COLOR = "#15803D"
C_COLOR = "#0891B2"
D_COLOR = "#0E7490"
BUILDING_COLOR = "#6B7280"
PARK_COLOR = "#86EFAC"
SUB_COLOR = "#D1D5DB"
TARGET_GLOW = "#FACC15"
TEXT_DARK = "#0F172A"

# ============================================================
# ESTILOS
# ============================================================

st.markdown(
    """
    <style>
    .block-container {
        max-width: 1500px;
        padding-top: 1rem;
        padding-bottom: 1rem;
    }

    .main-title {
        font-size: 2.3rem;
        font-weight: 800;
        color: #0f172a;
        margin-bottom: 0.15rem;
    }

    .subtitle {
        font-size: 1.05rem;
        color: #334155;
        margin-bottom: 1rem;
    }

    .card {
        background: #f8fafc;
        border: 1px solid #cbd5e1;
        border-radius: 18px;
        padding: 1rem 1rem 0.9rem 1rem;
        margin-bottom: 1rem;
    }

    .card-title {
        font-size: 1.15rem;
        font-weight: 800;
        color: #0f172a;
        margin-bottom: 0.6rem;
    }

    .status-box {
        background: #eff6ff;
        border: 1px solid #93c5fd;
        color: #1e3a8a;
        border-radius: 12px;
        padding: 0.8rem 0.95rem;
        font-size: 1rem;
        font-weight: 700;
        margin-bottom: 0.8rem;
    }

    .score-box {
        background: white;
        border: 2px solid #cbd5e1;
        border-radius: 18px;
        padding: 1rem;
        text-align: center;
    }

    .score-label {
        font-size: 1rem;
        color: #475569;
        font-weight: 700;
        margin-bottom: 0.4rem;
    }

    .score-value {
        font-size: 2.8rem;
        font-weight: 900;
        line-height: 1.05;
    }

    .score-low { color: #15803d; }
    .score-mid { color: #d97706; }
    .score-high { color: #dc2626; }

    .legend-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px 12px;
    }

    .legend-item {
        display: flex;
        align-items: center;
        gap: 8px;
        color: #1f2937;
        font-size: 0.95rem;
    }

    .legend-swatch {
        width: 24px;
        height: 24px;
        border-radius: 7px;
        border: 1px solid #475569;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 0.8rem;
        font-weight: 800;
        color: white;
        flex-shrink: 0;
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
# FUENTES
# ============================================================

def get_font(size: int, bold: bool = False):
    candidates = [
        "arialbd.ttf" if bold else "arial.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
    ]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size=size)
        except Exception:
            continue
    return ImageFont.load_default()

FONT_SMALL = get_font(16, bold=True)
FONT_MED = get_font(22, bold=True)
FONT_BIG = get_font(28, bold=True)
FONT_SYMBOL = get_font(24, bold=True)

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
    q = deque([start])
    visited = {start}

    while q:
        current = q.popleft()
        if current == end:
            return True
        for n in neighbors(*current):
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
                    weights=[70, 18, 12],
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
    prev = st.session_state.get("previous_scenario")
    if prev is not None:
        current = st.session_state.scenario
        st.session_state.scenario = prev
        st.session_state.previous_scenario = current
        reset_same_scenario()

# ============================================================
# LÓGICA DE JUEGO
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

    if pos in neighbors(*path[-1]):
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
# TABLERO VISUAL
# ============================================================

def cell_bbox(r, c):
    x0 = PAD + c * (CELL + GRID_GAP)
    y0 = PAD + r * (CELL + GRID_GAP)
    x1 = x0 + CELL
    y1 = y0 + CELL
    return x0, y0, x1, y1


def draw_centered_text(draw, bbox, text, font, fill):
    x0, y0, x1, y1 = bbox
    bb = draw.textbbox((0, 0), text, font=font)
    tw = bb[2] - bb[0]
    th = bb[3] - bb[1]
    tx = x0 + (x1 - x0 - tw) / 2
    ty = y0 + (y1 - y0 - th) / 2 - 2
    draw.text((tx, ty), text, font=font, fill=fill)


def draw_building(draw, bbox):
    x0, y0, x1, y1 = bbox
    draw.rounded_rectangle(bbox, radius=10, fill=BUILDING_COLOR, outline="#374151", width=2)
    roof = [x0 + 4, y0 + 4, x1 - 4, y0 + 12]
    draw.rounded_rectangle(roof, radius=4, fill="#4B5563", outline="#374151", width=1)
    for wx in [x0 + 10, x0 + 26]:
        for wy in [y0 + 18, y0 + 33]:
            if wx + 8 < x1 - 6 and wy + 8 < y1 - 6:
                draw.rounded_rectangle([wx, wy, wx + 8, wy + 8], radius=2, fill="#FEF3C7")


def draw_park(draw, bbox):
    x0, y0, x1, y1 = bbox
    draw.rounded_rectangle(bbox, radius=10, fill=PARK_COLOR, outline="#16A34A", width=2)
    draw.ellipse([x0 + 11, y0 + 8, x0 + 31, y0 + 28], fill="#16A34A", outline="#166534")
    draw.rectangle([x0 + 19, y0 + 24, x0 + 23, y1 - 10], fill="#92400E")
    draw_centered_text(draw, bbox, "🌳", FONT_SMALL, "#166534")


def draw_substation(draw, bbox):
    x0, y0, x1, y1 = bbox
    draw.rounded_rectangle(bbox, radius=10, fill=SUB_COLOR, outline="#4B5563", width=2)
    draw.line([x0 + 10, y0 + 16, x1 - 10, y0 + 16], fill="#374151", width=2)
    draw.line([x0 + 10, y0 + 28, x1 - 10, y0 + 28], fill="#374151", width=2)
    draw.line([(x0 + x1) / 2, y0 + 10, (x0 + x1) / 2, y1 - 10], fill="#DC2626", width=2)
    draw_centered_text(draw, bbox, "⚡", FONT_SYMBOL, "#111827")


def draw_node(draw, bbox, label, fill, outline):
    draw.ellipse(
        [bbox[0] + 5, bbox[1] + 5, bbox[2] - 5, bbox[3] - 5],
        fill=fill,
        outline=outline,
        width=3,
    )
    draw_centered_text(draw, bbox, label, FONT_MED, "white")


def render_board_image():
    scenario = st.session_state.scenario
    power_path = set(st.session_state.power_path)
    gas_path = set(st.session_state.gas_path)

    width = PAD * 2 + COLS * CELL + (COLS - 1) * GRID_GAP
    height = PAD * 2 + ROWS * CELL + (ROWS - 1) * GRID_GAP

    img = Image.new("RGB", (width, height), "#E2E8F0")
    draw = ImageDraw.Draw(img)

    active_target = None
    if st.session_state.mode == "power":
        active_target = scenario["B"]
    elif not st.session_state.done:
        active_target = scenario["D"]

    for r in range(ROWS):
        for c in range(COLS):
            pos = (r, c)
            bbox = cell_bbox(r, c)

            draw.rounded_rectangle(bbox, radius=10, fill=EMPTY_COLOR, outline=GRID_LINE, width=1)

            if pos in scenario["obstacles"]:
                kind = scenario["obstacles"][pos]
                if kind == "building":
                    draw_building(draw, bbox)
                elif kind == "park":
                    draw_park(draw, bbox)
                else:
                    draw_substation(draw, bbox)
            elif pos in power_path:
                draw.rounded_rectangle(bbox, radius=10, fill=POWER_COLOR, outline="#991B1B", width=2)
                draw_centered_text(draw, bbox, "E", FONT_MED, "white")
            elif pos in gas_path:
                draw.rounded_rectangle(bbox, radius=10, fill=GAS_COLOR, outline="#1D4ED8", width=2)
                draw_centered_text(draw, bbox, "G", FONT_MED, "white")

            if pos == scenario["A"]:
                draw_node(draw, bbox, "A", A_COLOR, "#14532D")
            elif pos == scenario["B"]:
                draw_node(draw, bbox, "B", B_COLOR, "#14532D")
            elif pos == scenario["C"]:
                draw_node(draw, bbox, "C", C_COLOR, "#164E63")
            elif pos == scenario["D"]:
                draw_node(draw, bbox, "D", D_COLOR, "#164E63")

            if active_target is not None and pos == active_target:
                glow_bbox = [bbox[0] + 2, bbox[1] + 2, bbox[2] - 2, bbox[3] - 2]
                draw.rounded_rectangle(glow_bbox, radius=10, outline=TARGET_GLOW, width=4)

    return img


def pixel_to_cell(x, y):
    x -= PAD
    y -= PAD
    if x < 0 or y < 0:
        return None

    block = CELL + GRID_GAP
    col = x // block
    row = y // block

    if not (0 <= row < ROWS and 0 <= col < COLS):
        return None

    # verificar que el clic cayó dentro de la celda y no en la separación
    local_x = x % block
    local_y = y % block
    if local_x >= CELL or local_y >= CELL:
        return None

    return int(row), int(col)

# ============================================================
# UI
# ============================================================

init_state()

st.markdown('<div class="main-title">⚡ Evita la Inducción</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Haz clic directamente sobre el tablero para trazar la red eléctrica A→B y luego la red de gas C→D.</div>',
    unsafe_allow_html=True,
)

left, right = st.columns([3.4, 1.35], gap="large")

with left:
    if st.session_state.mode == "power":
        msg = "Traza la red eléctrica desde A hasta B. El nodo objetivo actual es B."
    elif not st.session_state.done:
        msg = "Ahora traza la red de gas desde C hasta D. El nodo objetivo actual es D."
    else:
        msg = "Escenario completado. Revisa el puntaje, reintenta el mismo caso o genera uno nuevo."

    st.markdown(f'<div class="status-box">{msg}</div>', unsafe_allow_html=True)

    board = render_board_image()
    click = streamlit_image_coordinates(
        board,
        key="board_click",
        use_column_width="auto",
    )

    if click is not None and "x" in click and "y" in click:
        pos = pixel_to_cell(click["x"], click["y"])
        if pos is not None:
            handle_cell_click(pos)
            st.rerun()

with right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Controles</div>', unsafe_allow_html=True)

    current = st.slider("Corriente de la red eléctrica [A]", 100, 1500, st.session_state.current_a, 50)
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
        <div class="legend-grid">
            <div class="legend-item"><span class="legend-swatch" style="background:#16a34a;">A</span> Inicio eléctrico</div>
            <div class="legend-item"><span class="legend-swatch" style="background:#15803d;">B</span> Fin eléctrico</div>
            <div class="legend-item"><span class="legend-swatch" style="background:#0891b2;">C</span> Inicio gas</div>
            <div class="legend-item"><span class="legend-swatch" style="background:#0e7490;">D</span> Fin gas</div>
            <div class="legend-item"><span class="legend-swatch" style="background:#d62828;">E</span> Ruta eléctrica</div>
            <div class="legend-item"><span class="legend-swatch" style="background:#2563eb;">G</span> Ruta de gas</div>
            <div class="legend-item"><span class="legend-swatch" style="background:#6b7280;">🏢</span> Edificio</div>
            <div class="legend-item"><span class="legend-swatch" style="background:#86efac;color:#166534;">🌳</span> Parque</div>
            <div class="legend-item"><span class="legend-swatch" style="background:#d1d5db;color:#111827;">⚡</span> Subestación</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Estado del ejercicio</div>', unsafe_allow_html=True)

    st.write(f"**Ruta eléctrica:** {len(st.session_state.power_path)} celdas")
    st.write(f"**Ruta de gas:** {len(st.session_state.gas_path)} celdas")

    if st.session_state.done:
        score = score_path(
            st.session_state.power_path,
            st.session_state.gas_path,
            st.session_state.current_a,
        )
        cls, desc = score_class(score)
        st.markdown(
            f"""
            <div class="score-box">
                <div class="score-label">Puntaje obtenido</div>
                <div class="score-value {cls}">{score:.1f}</div>
                <div class="{cls}" style="font-weight:800; font-size:1.08rem;">{desc}</div>
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
                <div style="color:#64748b; font-weight:800;">Aún no calculado</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

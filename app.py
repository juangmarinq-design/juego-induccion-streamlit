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
# ESTILOS (MEJORADOS)
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
    }

    .card-title {
        font-size: 1.1rem;
        font-weight: 800;
        margin-bottom: 0.6rem;
    }

    .status-box {
        background: #e0f2fe;
        border: 1px solid #7dd3fc;
        color: #0369a1;
        border-radius: 12px;
        padding: 0.8rem;
        font-weight: 700;
        margin-bottom: 0.8rem;
    }

    div[data-testid="stButton"] > button {
        width: 100%;
        min-height: 4.1rem;
        border-radius: 14px;
        font-weight: 800;
        font-size: 1.28rem;
        border: 1px solid #cbd5e1;
    }

    .score-box {
        border: 2px solid #cbd5e1;
        border-radius: 18px;
        padding: 1rem;
        text-align: center;
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
    }

    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# FUNCIONES
# ============================================================

def neighbors(r, c):
    for dr, dc in [(1,0),(-1,0),(0,1),(0,-1)]:
        rr, cc = r+dr, c+dc
        if 0<=rr<ROWS and 0<=cc<COLS:
            yield rr, cc

def manhattan(a,b):
    return abs(a[0]-b[0])+abs(a[1]-b[1])

def path_exists(start,end,obs):
    q=deque([start]); vis={start}
    while q:
        cur=q.popleft()
        if cur==end: return True
        for n in neighbors(*cur):
            if n not in vis and n not in obs:
                vis.add(n); q.append(n)
    return False

def score_path(p,g,I):
    s=0
    for a in p:
        for b in g:
            d=manhattan(a,b)
            if d==0: s+=1000
            else: s+=1/(d**2)
    return I*s/100

def score_class(x):
    if x<80: return "score-low","Baja"
    if x<150: return "score-mid","Media"
    return "score-high","Alta"

# ============================================================
# ESCENARIO
# ============================================================

def generate_obstacles():
    obs={}
    for r in range(ROWS):
        for c in range(COLS):
            if random.random()<OBSTACLE_DENSITY:
                kind=random.choice(["building","park","sub"])
                obs[(r,c)]=kind
    return obs

def generate_valid():
    for _ in range(400):
        obs=generate_obstacles()
        free=[(r,c) for r in range(ROWS) for c in range(COLS) if (r,c) not in obs]
        random.shuffle(free)

        A=random.choice(free)
        B=random.choice(free)
        C=random.choice(free)
        D=random.choice(free)

        if len({A,B,C,D})<4: continue
        if not path_exists(A,B,obs): continue
        if not path_exists(C,D,obs): continue

        return dict(obstacles=obs,A=A,B=B,C=C,D=D)

    raise RuntimeError

# ============================================================
# ESTADO
# ============================================================

if "scenario" not in st.session_state:
    st.session_state.scenario=generate_valid()
    st.session_state.power=[]
    st.session_state.gas=[]
    st.session_state.mode="power"
    st.session_state.done=False
    st.session_state.score=None
    st.session_state.I=800

# ============================================================
# UI
# ============================================================

sc=st.session_state.scenario

st.markdown('<div class="title-main">⚡ Evita la Inducción</div>',unsafe_allow_html=True)
st.markdown('<div class="subtitle-main">Diseña rutas minimizando inducción</div>',unsafe_allow_html=True)

left,right=st.columns([4.2,1.1])

# ============================================================
# TABLERO
# ============================================================

with left:

    if st.session_state.mode=="power":
        msg="Traza red eléctrica A→B"
    elif not st.session_state.done:
        msg="Ahora red de gas C→D"
    else:
        msg="Ejercicio completado"

    st.markdown(f'<div class="status-box">{msg}</div>',unsafe_allow_html=True)

    for r in range(ROWS):
        cols=st.columns(COLS)
        for c in range(COLS):
            pos=(r,c)

            if pos in sc["obstacles"]:
                k=sc["obstacles"][pos]
                label="🏢" if k=="building" else "🌳" if k=="park" else "⚡"

            elif pos==sc["A"]: label="🟢A"
            elif pos==sc["B"]: label="🟢B"
            elif pos==sc["C"]: label="🔵C"
            elif pos==sc["D"]: label="🔵D"
            elif pos in st.session_state.power: label="🔴━"
            elif pos in st.session_state.gas: label="🔵━"
            else: label=" "

            if cols[c].button(label,key=f"{r}-{c}",use_container_width=True):

                if pos in sc["obstacles"]: continue

                if st.session_state.mode=="power":
                    path=st.session_state.power; start=sc["A"]; target=sc["B"]
                else:
                    path=st.session_state.gas; start=sc["C"]; target=sc["D"]

                if len(path)==0:
                    if pos==start: path.append(pos)
                else:
                    if pos not in path and pos in neighbors(*path[-1]):
                        path.append(pos)

                        if pos==target:
                            if st.session_state.mode=="power":
                                st.session_state.mode="gas"
                            else:
                                st.session_state.done=True
                                st.session_state.score=score_path(
                                    st.session_state.power,
                                    st.session_state.gas,
                                    st.session_state.I
                                )
                st.rerun()

    st.markdown('<div class="info-strip">💡 Evita paralelismo y cercanía</div>',unsafe_allow_html=True)

# ============================================================
# PANEL DERECHO
# ============================================================

with right:

    st.slider("Corriente [A]",100,1500,key="I")

    if st.button("Nuevo"):
        st.session_state.clear()
        st.rerun()

    if st.session_state.done:
        scv=st.session_state.score
        cls,desc=score_class(scv)
        st.markdown(f"""
        <div class="score-box">
        <div>Puntaje</div>
        <div class="score-value {cls}">{scv:.1f}</div>
        <div>{desc}</div>
        </div>
        """,unsafe_allow_html=True)

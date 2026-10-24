import io
import random

import pandas as pd
import streamlit as st
import matplotlib

matplotlib.use("Agg")
from matplotlib.figure import Figure

st.set_page_config(page_title="Diagrama de Hasse", page_icon="📊", layout="centered")


# ============================================================
# LÓGICA (orden parcial, coberturas, niveles)
# ============================================================

def construir_matriz_directa(n, precedencias):
    matriz = [[False] * n for _ in range(n)]
    for tarea in range(1, n + 1):
        for p in precedencias[tarea]:
            matriz[p - 1][tarea - 1] = True
    return matriz


def construir_orden_parcial(n, matriz_directa):
    m = [fila[:] for fila in matriz_directa]
    for i in range(n):
        m[i][i] = True
    for k in range(n):
        for i in range(n):
            for j in range(n):
                if m[i][k] and m[k][j]:
                    m[i][j] = True
    return m


def obtener_relaciones(m, n):
    return [(i + 1, j + 1) for i in range(n) for j in range(n) if m[i][j]]


def obtener_coberturas(n, m):
    coberturas = []
    for i in range(n):
        for j in range(n):
            if i == j or not m[i][j]:
                continue
            es_cob = True
            for k in range(n):
                if k != i and k != j and m[i][k] and m[k][j]:
                    es_cob = False
                    break
            if es_cob:
                coberturas.append((i + 1, j + 1))
    return coberturas


def calcular_niveles(n, coberturas):
    preds = {i: [] for i in range(1, n + 1)}
    for a, b in coberturas:
        preds[b].append(a)

    niveles = {i: 0 for i in range(1, n + 1) if not preds[i]}
    while len(niveles) < n:
        progreso = False
        for t in range(1, n + 1):
            if t in niveles:
                continue
            if all(p in niveles for p in preds[t]):
                niveles[t] = max(niveles[p] + 1 for p in preds[t])
                progreso = True
        if not progreso:
            break
    return niveles


# ============================================================
# TIEMPO DEL PROYECTO (ruta crítica)
# ============================================================

def fmt(x):
    x = float(x)
    return str(int(x)) if x.is_integer() else f"{x:.2f}".rstrip("0").rstrip(".")


def calcular_plan(tareas, precedencias, coberturas):
    n = len(tareas)
    ES, EF = {}, {}
    for t in range(1, n + 1):
        ES[t] = max((EF[p] for p in precedencias[t]), default=0)
        EF[t] = ES[t] + tareas[t]["tiempo"]

    total = max(EF.values())

    sucesores = {i: [] for i in range(1, n + 1)}
    for t in range(1, n + 1):
        for p in precedencias[t]:
            sucesores[p].append(t)

    LF = {}
    for t in range(n, 0, -1):
        if sucesores[t]:
            LF[t] = min(LF[s] - tareas[s]["tiempo"] for s in sucesores[t])
        else:
            LF[t] = total

    criticas = {t for t in range(1, n + 1) if abs(LF[t] - EF[t]) < 1e-9}
    aristas_criticas = {
        (a, b) for a, b in coberturas
        if a in criticas and b in criticas and abs(EF[a] - ES[b]) < 1e-9
    }

    actual = min(t for t in criticas if abs(EF[t] - total) < 1e-9)
    ruta = [actual]
    while precedencias[actual]:
        previos = [
            p for p in precedencias[actual]
            if p in criticas and abs(EF[p] - ES[actual]) < 1e-9
        ]
        if not previos:
            break
        actual = min(previos)
        ruta.append(actual)
    ruta.reverse()

    return {
        "ES": ES,
        "EF": EF,
        "total": total,
        "suma": sum(tareas[t]["tiempo"] for t in tareas),
        "criticas": criticas,
        "aristas_criticas": aristas_criticas,
        "ruta": ruta,
    }


# ============================================================
# DIAGRAMA
# ============================================================

def crear_figura_hasse(tareas, coberturas, plan):
    n = len(tareas)
    niveles = calcular_niveles(n, coberturas)

    por_nivel = {}
    for t, nv in niveles.items():
        por_nivel.setdefault(nv, []).append(t)
    for nv in por_nivel:
        por_nivel[nv].sort()

    pos = {}
    for nv, lista in por_nivel.items():
        c = len(lista)
        if c == 1:
            pos[lista[0]] = (nv, 0)
        else:
            espacio = 2
            inicio = -((c - 1) * espacio) / 2
            for idx, t in enumerate(lista):
                pos[t] = (nv, inicio + idx * espacio)

    fig = Figure(figsize=(15, 8), dpi=110)
    gs = fig.add_gridspec(1, 2, width_ratios=[2.6, 1])
    ax = fig.add_subplot(gs[0])
    ax_t = fig.add_subplot(gs[1])

    for a, b in coberturas:
        x1, y1 = pos[a]
        x2, y2 = pos[b]
        critica = (a, b) in plan["aristas_criticas"]
        ax.plot(
            [x1, x2], [y1, y2],
            linewidth=3 if critica else 1.5,
            color="#d62728" if critica else "#444",
            zorder=2 if critica else 1,
        )

    for t, (x, y) in pos.items():
        es_critica = t in plan["criticas"]
        ax.scatter(
            x, y, s=900, zorder=3,
            color="#e8575a" if es_critica else "#4f8fd9",
            edgecolors="#9c1d20" if es_critica else "#1d4f91",
        )
        ax.text(
            x, y, f"T{t}", ha="center", va="center",
            fontsize=10, color="white", fontweight="bold", zorder=4
        )
        ax.text(
            x, y - 0.35,
            f"{tareas[t]['nombre']}\n{tareas[t]['tiempo']} h",
            ha="center", va="top", fontsize=8
        )

    ax.set_title("DIAGRAMA DE HASSE", fontsize=15, pad=12)
    ax.set_axis_off()

    if pos:
        xs = [p[0] for p in pos.values()]
        ys = [p[1] for p in pos.values()]
        ax.set_xlim(min(xs) - 1, max(xs) + 1)
        ax.set_ylim(min(ys) - 1.5, max(ys) + 1)

    # ---------- Tabla de tiempo total (al costado del Hasse) ----------
    ax_t.axis("off")
    filas = [
        [f"T{t}", fmt(tareas[t]["tiempo"]), fmt(plan["ES"][t]), fmt(plan["EF"][t])]
        for t in sorted(tareas)
    ]
    filas.append(["TOTAL", "", "", fmt(plan["total"])])

    alto_fila = 0.04
    n_filas = len(filas) + 1  # + encabezado
    
    # Forzamos la alineación a la izquierda en la tabla de matplotlib
    tabla = ax_t.table(
        cellText=filas,
        colLabels=["Tarea", "Tiempo", "Inicio", "Fin"],
        cellLoc="left", 
        colLoc="center",
        bbox=[0, 0.98 - n_filas * alto_fila, 1, n_filas * alto_fila],
    )
    tabla.auto_set_font_size(False)
    tabla.set_fontsize(9)

    for (fila, col), celda in tabla.get_celld().items():
        if fila == 0:
            celda.set_facecolor("#2f3b52")
            celda.set_text_props(color="white", fontweight="bold", ha='center')
        else:
            # Ajustamos el texto para que se pegue a la izquierda
            celda.set_text_props(ha='left', x=0.05) 
            
            if fila == len(filas):
                celda.set_facecolor("#ffe08a")
                celda.set_text_props(fontweight="bold")
            elif sorted(tareas)[fila - 1] in plan["criticas"]:
                celda.set_facecolor("#fde2e2")

    ruta_txt = " → ".join(f"T{t}" for t in plan["ruta"])
    ax_t.set_title("TIEMPO TOTAL DEL PROYECTO", fontsize=13, pad=12)
    y_texto = 0.98 - n_filas * alto_fila - 0.02
    
    ax_t.text(
        0.5, y_texto,
        f"Duración total: {fmt(plan['total'])} h\n"
        f"Ruta crítica: {ruta_txt}\n"
        f"(Suma de todas las tareas: {fmt(plan['suma'])} h)",
        ha="center", va="top", fontsize=9, transform=ax_t.transAxes,
    )

    fig.tight_layout()
    return fig


# ============================================================
# DATOS (tabla editable)
# ============================================================

COLUMNAS = ["Tarea", "Nombre", "Tiempo", "Precedentes"]


def crear_df(n, previo=None):
    filas = []
    for i in range(1, n + 1):
        if previo is not None and i <= len(previo):
            r = previo.iloc[i - 1]
            filas.append({
                "Tarea": f"T{i}",
                "Nombre": r["Nombre"],
                "Tiempo": r["Tiempo"],
                "Precedentes": r["Precedentes"],
            })
        else:
            filas.append({
                "Tarea": f"T{i}", "Nombre": "", "Tiempo": None, "Precedentes": ""
            })
    df = pd.DataFrame(filas, columns=COLUMNAS)
    df["Tiempo"] = df["Tiempo"].astype("float64")
    df["Nombre"] = df["Nombre"].astype("object")
    df["Precedentes"] = df["Precedentes"].astype("object")
    if len(df) > 0:
        df.loc[0, "Precedentes"] = ""
    return df


def df_aleatorio(n):
    filas = []
    for i in range(1, n + 1):
        if i == 1:
            precs = ""
        else:
            anteriores = list(range(1, i))
            cant = random.randint(1, min(3, len(anteriores)))
            precs = " ".join(map(str, sorted(random.sample(anteriores, cant))))
        filas.append({
            "Tarea": f"T{i}",
            "Nombre": f"Tarea {i}",
            "Tiempo": float(random.randint(1, 10)),
            "Precedentes": precs,
        })
    return pd.DataFrame(filas, columns=COLUMNAS)


def leer_datos(df):
    tareas = {}
    precedencias = {}

    for i, (_, fila) in enumerate(df.iterrows(), start=1):
        nombre = fila["Nombre"]
        nombre = "" if pd.isna(nombre) else str(nombre).strip()
        if not nombre:
            raise ValueError(f"T{i}: el nombre no puede estar vacío.")

        tiempo = fila["Tiempo"]
        if pd.isna(tiempo):
            raise ValueError(f"T{i}: falta el tiempo.")
        tiempo = float(tiempo)
        if tiempo <= 0:
            raise ValueError(f"T{i}: el tiempo debe ser mayor que 0.")
        if tiempo == int(tiempo):
            tiempo = int(tiempo)

        texto = fila["Precedentes"]
        texto = "" if pd.isna(texto) else str(texto).replace(",", " ").strip()
        try:
            precs = [int(x) for x in texto.split()] if texto else []
        except ValueError:
            raise ValueError(
                f"T{i}: los precedentes deben ser números separados por espacios."
            )

        if i == 1 and precs:
            raise ValueError("T1 no puede tener precedentes.")
        if len(precs) > 3:
            raise ValueError(f"T{i}: máximo 3 precedentes.")
        if len(set(precs)) != len(precs):
            raise ValueError(f"T{i}: no repita precedentes.")
        if any(p < 1 or p >= i for p in precs):
            raise ValueError(
                f"T{i}: solo puede tener tareas anteriores como precedentes."
            )

        tareas[i] = {"nombre": nombre, "tiempo": tiempo}
        precedencias[i] = sorted(precs)

    return tareas, precedencias


def procesar(df):
    tareas, precedencias = leer_datos(df)
    n = len(tareas)

    matriz_dir = construir_matriz_directa(n, precedencias)
    matriz_ord = construir_orden_parcial(n, matriz_dir)
    relaciones = obtener_relaciones(matriz_ord, n)
    coberturas = obtener_coberturas(n, matriz_ord)

    plan = calcular_plan(tareas, precedencias, coberturas)
    fig = crear_figura_hasse(tareas, coberturas, plan)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")

    tabla = pd.DataFrame([
        {
            "Tarea": f"T{t}",
            "Nombre": tareas[t]["nombre"],
            "Tiempo": str(tareas[t]["tiempo"]), # Convertido a string
            "Inicio": str(plan["ES"][t]),       # Convertido a string
            "Fin": str(plan["EF"][t]),          # Convertido a string
            "Precedentes directos": ", ".join(f"T{p}" for p in precedencias[t]) or "-",
        }
        for t in sorted(tareas)
    ])

    # Al ser strings, Streamlit los alineará a la izquierda obligatoriamente
    tabla_estilizada = tabla.style.set_properties(**{'text-align': 'left'})

    return {
        "plan": plan,
        "fig": fig,
        "png": buf.getvalue(),
        "tabla": tabla_estilizada,
        "relaciones": relaciones,
        "coberturas": coberturas,
    }


# ============================================================
# INTERFAZ
# ============================================================

st.title("📊 Diagrama de Hasse")
st.caption("Tareas, precedencias, orden parcial y relaciones de cobertura.")

if "base" not in st.session_state:
    st.session_state.base = crear_df(8)
    st.session_state.actual = st.session_state.base.copy()
    st.session_state.ver = 0
    st.session_state.res = None
    st.session_state.error = None

n = st.slider("Número de tareas", 8, 15, len(st.session_state.base))

if n != len(st.session_state.base):
    st.session_state.base = crear_df(n, st.session_state.actual)
    st.session_state.actual = st.session_state.base.copy()
    st.session_state.ver += 1
    st.session_state.res = None
    st.session_state.error = None
    st.rerun()

c1, c2, c3 = st.columns(3)
btn_aleatorio = c1.button("🎲 Aleatorio", width="stretch")
btn_limpiar = c2.button("🧹 Limpiar", width="stretch")
btn_calcular = c3.button("▶ Calcular", type="primary", width="stretch")

if btn_aleatorio:
    st.session_state.base = df_aleatorio(n)
    st.session_state.actual = st.session_state.base.copy()
    st.session_state.ver += 1
    try:
        st.session_state.res = procesar(st.session_state.actual)
        st.session_state.error = None
    except ValueError as e:
        st.session_state.res = None
        st.session_state.error = str(e)
    st.rerun()

if btn_limpiar:
    st.session_state.base = crear_df(n)
    st.session_state.actual = st.session_state.base.copy()
    st.session_state.ver += 1
    st.session_state.res = None
    st.session_state.error = None
    st.rerun()

st.markdown(
    "**Precedentes:** números separados por espacio (máx. 3, solo tareas "
    "anteriores). Ejemplo: `1 3`. T1 no tiene precedentes."
)

editado = st.data_editor(
    st.session_state.base,
    key=f"editor_{st.session_state.ver}",
    hide_index=True,
    width="stretch",
    disabled=["Tarea"],
    column_config={
        "Tarea": st.column_config.TextColumn("Tarea", width="small"),
        "Nombre": st.column_config.TextColumn("Nombre"),
        # Ojo: El st.data_editor (la tabla de ingreso) siempre alineará los números a la derecha por diseño de Streamlit.
        "Tiempo": st.column_config.NumberColumn("Tiempo", min_value=0.0, width="small", alignment="left"),
        "Precedentes": st.column_config.TextColumn("Precedentes"),
    },
)
st.session_state.actual = editado

if btn_calcular:
    try:
        st.session_state.res = procesar(editado)
        st.session_state.error = None
    except ValueError as e:
        st.session_state.res = None
        st.session_state.error = str(e)

if st.session_state.error:
    st.error(st.session_state.error)

res = st.session_state.res
if res:
    plan = res["plan"]
    m1, m2 = st.columns(2)
    m1.metric("⏱ Duración total del proyecto", f"{fmt(plan['total'])} h")
    m2.metric("Suma de todas las tareas", f"{fmt(plan['suma'])} h")
    st.info("Ruta crítica: " + " → ".join(f"T{t}" for t in plan["ruta"]))

    tab1, tab2, tab3 = st.tabs(["Diagrama de Hasse", "Tabla", "Relaciones"])

    with tab1:
        st.pyplot(res["fig"], width="stretch")
        st.download_button(
            "💾 Descargar imagen (PNG)",
            data=res["png"],
            file_name="diagrama_hasse.png",
            mime="image/png",
            width="stretch",
        )

    with tab2:
        # Aquí se mostrará la tabla con TODO alineado estrictamente a la izquierda
        st.dataframe(res["tabla"], hide_index=True, width="stretch")

    with tab3:
        st.subheader("Relación de orden parcial")
        st.code(
            "\n".join(
                f"T{i} {'≤' if i == j else '→'} T{j}" for i, j in res["relaciones"]
            ),
            language=None,
        )
        st.subheader("Relaciones de cobertura")
        if res["coberturas"]:
            st.code(
                "\n".join(f"T{i} → T{j}" for i, j in res["coberturas"]),
                language=None,
            )
        else:
            st.write("No se encontraron relaciones de cobertura.")
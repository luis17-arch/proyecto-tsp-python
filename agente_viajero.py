import itertools
import tkinter as tk
from tkinter import ttk, filedialog

import networkx as nx
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

FONDO = "#0f1219"
FONDO_ENCABEZADO = "#141824"
FONDO_TARJETA = "#1a1f2e"
FONDO_TARJETA_HOVER = "#212840"
FONDO_ENTRADA = "#10141f"
BORDE = "#2a3148"

TEXTO = "#e6e9f2"
APAGADO = "#8b93a7"

ACENTO = "#5b8def"
ACENTO_HOVER = "#7aa3f5"
MORADO = "#8f74d9"
MORADO_HOVER = "#a28be3"
VERDE_AZULADO = "#2fb5a2"
AMBAR = "#e3a857"
ERROR = "#e0566b"
EXITO = "#4fb477"

VERDE_OSCURO = "#2f6b4a"
AMBAR_OSCURO = "#7a5a26"
ROJO_OSCURO = "#7a2f3b"

FUENTE = "Segoe UI"

UNIDADES = {
    "Costo (dinero)": ("$", "Costo ($)"),
    "Tiempo (horas)": ("h", "Tiempo (h)"),
    "Tiempo (minutos)": ("min", "Tiempo (min)"),
    "Distancia (km)": ("km", "Distancia (km)"),
}

TITULOS = {
    "home": "Menú principal",
    "auto": "Generación automática",
    "archivo": "Grafo por archivo",
    "manual": "Grafo manual · Paso 1: datos generales",
    "matriz": "Grafo manual · Paso 2: aristas y pesos",
    "result": "Grafo generado",
    "solve": "Fuerza bruta · Ciclos hamiltonianos",
}

ESTILOS_ALERTA = {
    "error": (ERROR, "✕"),
    "warning": (AMBAR, "!"),
    "info": (ACENTO, "i"),
    "success": (EXITO, "✓"),
}

MENSAJE_INICIAL = "Completa la matriz y presiona «Verificar y generar grafo»."

N_MIN, N_MAX = 5, 10
LIMITE_PESO = 1_000_000
MAX_REGISTRO = 300
MAX_FILAS = 1000
MAX_ERRORES = 200

estado = {
    "raiz": None,
    "pantallas": {},
    "pila": [],
    "grafo": None,
    "pos": None,
    "aristas_df": None,
    "params": None,
    "origen": "auto",
    "boton_atras": None,
    "subtitulo": None,
}
auto = {}
manual = {}
archivo = {}
resultado = {}
sol = {}


# Función para dar formato a un valor con su unidad (por ejemplo $50 o 12 km)
def formato_valor(valor, simbolo):
    if simbolo == "$":
        return f"${valor}"
    return f"{valor} {simbolo}"


# Función para convertir una ruta en texto, por ejemplo A → B → C → A
def texto_ruta(ruta):
    return " → ".join(tuple(ruta) + (ruta[0],))


# Función para obtener las aristas (pares de nodos) que forman una ruta cerrada
def aristas_ruta(ruta):
    return [(ruta[i], ruta[(i + 1) % len(ruta)]) for i in range(len(ruta))]


# Función para generar los nombres de los nodos (A, B, C...) según la cantidad n
def etiquetas_nodos(n):
    return [chr(65 + i) for i in range(n)]


# Función para crear un botón con efecto hover que ejecuta un comando al hacer clic
def crear_boton(padre, texto, comando, fondo=ACENTO, hover=ACENTO_HOVER,
                fg="white", tam=11, padx=20, pady=10):
    boton = tk.Label(padre, text=texto, bg=fondo, fg=fg, cursor="hand2",
                     font=(FUENTE, tam, "bold"), padx=padx, pady=pady)

    # Función interna: cambia el color del botón cuando el mouse pasa por encima
    def entrar(evento):
        boton.config(bg=hover)

    # Función interna: devuelve el color original cuando el mouse sale del botón
    def salir(evento):
        boton.config(bg=fondo)

    # Función interna: ejecuta el comando solo si el clic se suelta dentro del botón
    def soltar(evento):
        dentro_x = 0 <= evento.x <= boton.winfo_width()
        dentro_y = 0 <= evento.y <= boton.winfo_height()
        if dentro_x and dentro_y:
            comando()

    boton.bind("<Enter>", entrar)
    boton.bind("<Leave>", salir)
    boton.bind("<ButtonRelease-1>", soltar)
    return boton


# Función para crear una caja de texto con el estilo oscuro del programa
def crear_entrada(padre, variable, ancho=14, tam=13, justificar="left"):
    return tk.Entry(padre, textvariable=variable, width=ancho, bg=FONDO_ENTRADA,
                    fg=TEXTO, insertbackground=TEXTO, relief="flat",
                    font=(FUENTE, tam), justify=justificar, highlightthickness=2,
                    highlightbackground=BORDE, highlightcolor=ACENTO,
                    disabledbackground=FONDO_ENTRADA)


# Función para pintar el borde de una caja de texto: rojo si hay error, normal si está bien
def marcar_entrada(entrada, correcta):
    if correcta:
        entrada.config(highlightbackground=BORDE, highlightcolor=ACENTO)
    else:
        entrada.config(highlightbackground=ERROR, highlightcolor=ERROR)


# Función para crear una cajita con un título y un valor (por ejemplo Nodos: 7)
def crear_estadistica(padre, fila, columna, titulo, color):
    caja = tk.Frame(padre, bg=FONDO_ENTRADA, padx=10, pady=7)
    caja.grid(row=fila, column=columna, sticky="nsew", padx=3, pady=3)
    tk.Label(caja, text=titulo, bg=FONDO_ENTRADA, fg=APAGADO,
             font=(FUENTE, 9)).pack(anchor="w")
    valor = tk.Label(caja, text="-", bg=FONDO_ENTRADA, fg=color,
                     font=(FUENTE, 13, "bold"))
    valor.pack(anchor="w")
    return valor


# Función para crear una tabla con barra de desplazamiento a partir de una lista de columnas
def crear_tabla(padre, columnas, modo=None):
    marco = tk.Frame(padre, bg=FONDO_TARJETA)
    marco.pack(fill="both", expand=True)
    identificadores = [c[0] for c in columnas]
    tabla = ttk.Treeview(marco, columns=identificadores, show="headings",
                         style="Dark.Treeview")
    if modo is not None:
        tabla.configure(selectmode=modo)
    for ident, texto, ancho, ancla in columnas:
        tabla.heading(ident, text=texto)
        tabla.column(ident, width=ancho, anchor=ancla)
    barra = ttk.Scrollbar(marco, orient="vertical", command=tabla.yview,
                          style="Dark.Vertical.TScrollbar")
    tabla.configure(yscrollcommand=barra.set)
    tabla.pack(side="left", fill="both", expand=True)
    barra.pack(side="right", fill="y")
    return tabla


# Función para centrar una ventana secundaria sobre la ventana principal
def centrar_ventana(ventana):
    raiz = estado["raiz"]
    ventana.update_idletasks()
    ancho = ventana.winfo_reqwidth()
    alto = ventana.winfo_reqheight()
    x = raiz.winfo_rootx() + (raiz.winfo_width() - ancho) // 2
    y = raiz.winfo_rooty() + (raiz.winfo_height() - alto) // 2
    ventana.geometry(f"+{max(x, 0)}+{max(y, 0)}")


# Función para mostrar una ventana y bloquear la principal hasta que se cierre
def abrir_modal(ventana):
    ventana.deiconify()
    ventana.wait_visibility()
    ventana.grab_set()
    ventana.focus_set()
    ventana.wait_window()


# Función para mostrar una alerta llamativa (error, advertencia, información o éxito)
def mostrar_alerta(titulo, mensajes, tipo="error"):
    raiz = estado["raiz"]
    color, simbolo = ESTILOS_ALERTA.get(tipo, ESTILOS_ALERTA["info"])

    ventana = tk.Toplevel(raiz)
    ventana.withdraw()
    ventana.title(titulo)
    ventana.configure(bg=FONDO_TARJETA)
    ventana.resizable(False, False)
    ventana.transient(raiz)

    tk.Frame(ventana, bg=color, height=6).pack(fill="x")
    cuerpo = tk.Frame(ventana, bg=FONDO_TARJETA, padx=28, pady=22)
    cuerpo.pack(fill="both", expand=True)

    icono = tk.Canvas(cuerpo, width=60, height=60, bg=FONDO_TARJETA,
                      highlightthickness=0)
    icono.create_oval(3, 3, 57, 57, fill=color, outline="")
    icono.create_text(30, 30, text=simbolo, fill="white", font=(FUENTE, 24, "bold"))
    icono.pack()

    tk.Label(cuerpo, text=titulo, bg=FONDO_TARJETA, fg=TEXTO,
             font=(FUENTE, 15, "bold")).pack(pady=(12, 8))

    if isinstance(mensajes, str):
        mensajes = [mensajes]
    for mensaje in mensajes:
        texto = mensaje if len(mensajes) == 1 else f"•  {mensaje}"
        tk.Label(cuerpo, text=texto, bg=FONDO_TARJETA, fg=APAGADO,
                 font=(FUENTE, 11), wraplength=400, justify="left",
                 anchor="w").pack(fill="x", pady=2)

    crear_boton(cuerpo, "Entendido", ventana.destroy, fondo=color, hover=color,
                padx=40, pady=9).pack(pady=(18, 0))

    ventana.bind("<Return>", lambda e: ventana.destroy())
    ventana.bind("<Escape>", lambda e: ventana.destroy())

    centrar_ventana(ventana)
    abrir_modal(ventana)


# Función para generar un grafo aleatorio que siempre tenga un ciclo hamiltoniano
def generar_grafo_aleatorio(n, peso_min, peso_max):
    azar = nx.utils.create_py_random_state(None)
    etiquetas = etiquetas_nodos(n)
    G = nx.Graph()
    G.add_nodes_from(etiquetas)

    orden = etiquetas[:]
    azar.shuffle(orden)
    for i in range(n):
        a, b = orden[i], orden[(i + 1) % n]
        G.add_edge(a, b, weight=azar.randint(peso_min, peso_max))

    densidad = azar.uniform(0.30, 0.65)
    for a, b in itertools.combinations(etiquetas, 2):
        if not G.has_edge(a, b) and azar.random() < densidad:
            G.add_edge(a, b, weight=azar.randint(peso_min, peso_max))
    return G


# Función para pasar las aristas del grafo a una tabla de Pandas (origen, destino, peso)
def grafo_a_dataframe(G):
    filas = [(min(u, v), max(u, v), d["weight"]) for u, v, d in G.edges(data=True)]
    df = pd.DataFrame(filas, columns=["Origen", "Destino", "Peso"])
    return df.sort_values(["Origen", "Destino"]).reset_index(drop=True)


# Función para construir la matriz de costos (0 en la diagonal, infinito si no hay arista)
def construir_matriz_costos(G):
    etiquetas = sorted(G.nodes)
    infinito = float("inf")
    datos = []
    for a in etiquetas:
        fila = []
        for b in etiquetas:
            if a == b:
                fila.append(0)
            elif G.has_edge(a, b):
                fila.append(G[a][b]["weight"])
            else:
                fila.append(infinito)
        datos.append(fila)
    return pd.DataFrame(datos, index=etiquetas, columns=etiquetas)


# Función para calcular las aristas que faltan, como mínimo, para tener un ciclo hamiltoniano
def buscar_faltantes(etiquetas, pesos):
    pares = set()
    for a, b in pesos:
        pares.add((a, b))
        pares.add((b, a))
    mejor_ruta = None
    mejor_faltantes = None
    limite = None
    for ruta in generar_rutas(etiquetas):
        faltantes = []
        completa = True
        for a, b in aristas_ruta(ruta):
            if (a, b) not in pares:
                faltantes.append((a, b) if a < b else (b, a))
                if limite is not None and len(faltantes) >= limite:
                    completa = False
                    break
        if completa:
            mejor_ruta, mejor_faltantes, limite = ruta, faltantes, len(faltantes)
            if limite == 0:
                break
    return mejor_ruta, mejor_faltantes


# Función generadora: entrega una por una todas las rutas posibles sin repetir las inversas
def generar_rutas(etiquetas):
    inicio = etiquetas[0]
    for permutacion in itertools.permutations(etiquetas[1:]):
        if permutacion[0] < permutacion[-1]:
            yield (inicio,) + permutacion


# Función para preparar el motor de fuerza bruta con sus datos iniciales
def crear_motor(etiquetas, G):
    factorial = 1
    for k in range(2, len(etiquetas)):
        factorial *= k
    return {
        "etiquetas": etiquetas,
        "pesos": {a: {b: G[a][b]["weight"] for b in G[a]} for a in etiquetas},
        "total": factorial // 2,
        "iterador": generar_rutas(etiquetas),
        "evaluadas": 0,
        "ciclos": [],
        "mejor_costo": None,
        "mejor_ruta": None,
        "terminado": False,
    }


# Función para calcular el costo total de una ruta (None si usa una arista que no existe)
def costo_ruta(motor, ruta):
    pesos = motor["pesos"]
    total = 0
    anterior = ruta[-1]
    for nodo in ruta:
        peso = pesos[anterior].get(nodo)
        if peso is None:
            return None
        total += peso
        anterior = nodo
    return total


# Función para obtener el detalle de una ruta: sus aristas, sus pesos y las que faltan
def detalle_ruta(motor, ruta):
    aristas = aristas_ruta(ruta)
    pesos = []
    faltantes = []
    for a, b in aristas:
        peso = motor["pesos"][a].get(b)
        if peso is None:
            faltantes.append((a, b))
        else:
            pesos.append(peso)
    return aristas, pesos, faltantes


# Función para evaluar rutas con fuerza bruta hasta cumplir el límite pedido o terminar
def avanzar(motor, max_pasos=None, hasta_valida=False):
    recientes = []
    pasos = 0
    while max_pasos is None or pasos < max_pasos:
        ruta = next(motor["iterador"], None)
        if ruta is None:
            break
        motor["evaluadas"] += 1
        pasos += 1
        costo = costo_ruta(motor, ruta)
        recientes.append((motor["evaluadas"], ruta, costo))
        if len(recientes) > 2 * MAX_REGISTRO:
            del recientes[:-MAX_REGISTRO]
        if costo is not None:
            motor["ciclos"].append((ruta, costo))
            if motor["mejor_costo"] is None or costo < motor["mejor_costo"]:
                motor["mejor_costo"] = costo
                motor["mejor_ruta"] = ruta
            if hasta_valida:
                break
    if motor["evaluadas"] >= motor["total"]:
        motor["terminado"] = True
    return recientes[-MAX_REGISTRO:], pasos


# Función para ordenar los ciclos hamiltonianos de menor a mayor costo
def ciclos_ordenados(motor):
    return sorted(motor["ciclos"], key=lambda c: c[1])


# Función para crear el lienzo de Matplotlib donde se dibuja el grafo dentro de Tkinter
def crear_lienzo(padre):
    marco = tk.Frame(padre, bg=FONDO_TARJETA)
    figura = Figure(figsize=(6.5, 5.5), dpi=100, facecolor=FONDO_TARJETA)
    canvas = FigureCanvasTkAgg(figura, master=marco)
    widget = canvas.get_tk_widget()
    widget.configure(bg=FONDO_TARJETA, highlightthickness=0)
    widget.pack(fill="both", expand=True)
    return {"marco": marco, "figura": figura, "canvas": canvas}


# Función para dibujar el grafo con sus pesos, resaltando un ciclo y las aristas faltantes
def dibujar_grafo(lienzo, G, pos, titulo, ciclo=None, color_ciclo=EXITO,
                  faltantes=None, inicio=None):
    figura = lienzo["figura"]
    figura.clear()
    ejes = figura.add_subplot(111)
    ejes.set_facecolor(FONDO_TARJETA)
    ejes.axis("off")

    conjunto_ciclo = set()
    for e in (ciclo or []):
        if G.has_edge(*e):
            conjunto_ciclo.add(frozenset(e))
    aristas_base = [e for e in G.edges() if frozenset(e) not in conjunto_ciclo]
    resaltando = bool(conjunto_ciclo or faltantes)

    if aristas_base:
        nx.draw_networkx_edges(G, pos, ax=ejes, edgelist=aristas_base,
                               edge_color="#4b5575", width=1.6,
                               alpha=0.45 if resaltando else 0.9)
    if conjunto_ciclo:
        nx.draw_networkx_edges(G, pos, ax=ejes,
                               edgelist=[tuple(e) for e in conjunto_ciclo],
                               edge_color=color_ciclo, width=4.5)
    if faltantes:
        H = nx.Graph()
        H.add_nodes_from(G.nodes)
        H.add_edges_from(faltantes)
        nx.draw_networkx_edges(H, pos, ax=ejes, edgelist=list(H.edges()),
                               style="dashed", edge_color=ERROR, width=3)

    colores = [MORADO if (inicio is not None and nodo == inicio) else ACENTO
               for nodo in G.nodes()]
    nx.draw_networkx_nodes(G, pos, ax=ejes, node_size=950, node_color=colores,
                           edgecolors="#9db9f7", linewidths=2)
    nx.draw_networkx_labels(G, pos, ax=ejes, font_color="white", font_size=13,
                            font_weight="bold")

    caja = dict(boxstyle="round,pad=0.25", fc=FONDO_TARJETA, ec="#3a4262", lw=0.8)
    etiquetas_base = {(u, v): G[u][v]["weight"] for u, v in aristas_base}
    etiquetas_ciclo = {}
    for e in conjunto_ciclo:
        u, v = tuple(e)
        etiquetas_ciclo[(u, v)] = G[u][v]["weight"]
    if etiquetas_base:
        nx.draw_networkx_edge_labels(G, pos, edge_labels=etiquetas_base, ax=ejes,
                                     font_size=9, font_color=AMBAR, label_pos=0.32,
                                     rotate=False, bbox=caja)
    if etiquetas_ciclo:
        nx.draw_networkx_edge_labels(G, pos, edge_labels=etiquetas_ciclo, ax=ejes,
                                     font_size=10, font_color="white",
                                     font_weight="bold", label_pos=0.32,
                                     rotate=False, bbox=caja)

    ejes.set_title(titulo, color=TEXTO, fontsize=12, pad=10)
    ejes.margins(0.12)
    figura.tight_layout()
    lienzo["canvas"].draw_idle()


# Función para crear el contenedor donde se muestra la matriz de costos
def crear_matriz(padre):
    marco = tk.Frame(padre, bg=BORDE)
    return {"marco": marco, "celdas": {}, "base": {}}


# Función para convertir el valor de una celda en texto (∞ si no hay arista)
def texto_celda(valor):
    if valor == float("inf"):
        return "∞"
    if float(valor).is_integer():
        return str(int(valor))
    return f"{valor:g}"


# Función para llenar la matriz visual con los datos de la tabla de costos
def llenar_matriz(matriz, df):
    marco = matriz["marco"]
    for widget in marco.winfo_children():
        widget.destroy()
    matriz["celdas"].clear()
    matriz["base"].clear()
    etiquetas = list(df.index)

    textos = {}
    for a in etiquetas:
        for b in etiquetas:
            textos[(a, b)] = "—" if a == b else texto_celda(df.loc[a, b])
    ancho = max(4, max(len(t) for t in textos.values()) + 1)
    tam = 11 if ancho <= 6 else 9

    # Función interna: crea una celda de la matriz y la coloca en su fila y columna
    def celda(fila, columna, texto, fondo, fg=TEXTO, negrita=False):
        etiqueta = tk.Label(marco, text=texto, bg=fondo, fg=fg, width=ancho, pady=6,
                            font=(FUENTE, tam, "bold" if negrita else "normal"))
        etiqueta.grid(row=fila, column=columna, padx=1, pady=1, sticky="nsew")
        return etiqueta

    celda(0, 0, "", FONDO_ENCABEZADO)
    for j, b in enumerate(etiquetas):
        celda(0, j + 1, b, "#2b3556", negrita=True)
    for i, a in enumerate(etiquetas):
        celda(i + 1, 0, a, "#2b3556", negrita=True)
        for j, b in enumerate(etiquetas):
            texto = textos[(a, b)]
            if a == b:
                base, fg = FONDO_ENCABEZADO, APAGADO
            elif texto == "∞":
                base, fg = FONDO_ENTRADA, APAGADO
            else:
                base, fg = FONDO_ENTRADA, TEXTO
            matriz["celdas"][(a, b)] = celda(i + 1, j + 1, texto, base, fg)
            matriz["base"][(a, b)] = base


# Función para resaltar en la matriz las celdas de las aristas de una ruta
def resaltar_matriz(matriz, grupos=()):
    for clave, etiqueta in matriz["celdas"].items():
        etiqueta.config(bg=matriz["base"][clave])
    for aristas, color in grupos:
        for a, b in aristas:
            for clave in ((a, b), (b, a)):
                if clave in matriz["celdas"]:
                    matriz["celdas"][clave].config(bg=color)


# Función para crear una tarjeta clicable de la pantalla principal
def crear_tarjeta(padre, icono, titulo, descripcion, insignia, color_insignia,
                  acento, comando):
    tarjeta = tk.Frame(padre, bg=FONDO_TARJETA, highlightthickness=2,
                       highlightbackground=BORDE, cursor="hand2")
    tk.Frame(tarjeta, bg=acento, height=5).pack(fill="x")
    interior = tk.Frame(tarjeta, bg=FONDO_TARJETA, padx=24, pady=26)
    interior.pack(fill="both", expand=True)

    circulo = tk.Canvas(interior, width=76, height=76, bg=FONDO_TARJETA,
                        highlightthickness=0)
    circulo.create_oval(4, 4, 72, 72, fill=acento, outline="")
    circulo.create_text(38, 38, text=icono, fill="white", font=(FUENTE, 28, "bold"))
    circulo.pack()

    tk.Label(interior, text=titulo, bg=FONDO_TARJETA, fg=TEXTO,
             font=(FUENTE, 16, "bold")).pack(pady=(16, 6))
    tk.Label(interior, text=descripcion, bg=FONDO_TARJETA, fg=APAGADO,
             font=(FUENTE, 11), wraplength=250, justify="center").pack(pady=(0, 14))
    tk.Label(interior, text=insignia, bg=color_insignia, fg="white",
             font=(FUENTE, 9, "bold"), padx=12, pady=3).pack()

    # Función interna: cambia el color de fondo de la tarjeta y de todo lo que lleva dentro
    def recolorear(widget, color):
        if widget.cget("bg") in (FONDO_TARJETA, FONDO_TARJETA_HOVER):
            widget.config(bg=color)
        for hijo in widget.winfo_children():
            recolorear(hijo, color)

    # Función interna: resalta la tarjeta cuando el mouse entra en ella
    def entrar(evento):
        recolorear(tarjeta, FONDO_TARJETA_HOVER)
        tarjeta.config(highlightbackground=acento)

    # Función interna: quita el resalte cuando el mouse sale de la tarjeta
    def salir(evento):
        x, y = tarjeta.winfo_pointerxy()
        debajo = tarjeta.winfo_containing(x, y)
        if debajo is not None and str(debajo).startswith(str(tarjeta)):
            return
        recolorear(tarjeta, FONDO_TARJETA)
        tarjeta.config(highlightbackground=BORDE)

    # Función interna: conecta los eventos del mouse a la tarjeta y a todos sus elementos
    def enlazar(widget):
        widget.bind("<Enter>", entrar)
        widget.bind("<Leave>", salir)
        widget.bind("<ButtonRelease-1>", lambda e: comando())
        for hijo in widget.winfo_children():
            enlazar(hijo)

    enlazar(tarjeta)
    return tarjeta


# Función para construir la pantalla principal con el título y las tres tarjetas
def construir_inicio(padre):
    marco = tk.Frame(padre, bg=FONDO)
    centro = tk.Frame(marco, bg=FONDO)
    centro.place(relx=0.5, rely=0.5, anchor="center")

    tk.Label(centro, text="PROBLEMA DEL AGENTE VIAJERO", bg=FONDO, fg=TEXTO,
             font=(FUENTE, 28, "bold")).pack()
    tk.Label(centro, text="Construcción de grafos ponderados  ·  Algoritmo de fuerza bruta",
             bg=FONDO, fg=APAGADO, font=(FUENTE, 13)).pack(pady=(6, 4))
    tk.Frame(centro, bg=ACENTO, height=3, width=90).pack(pady=(8, 34))

    fila = tk.Frame(centro, bg=FONDO)
    fila.pack()

    tarjetas = [
        ("✎", "Grafo manual",
         "Define los pesos de cada arista en una matriz y elige la unidad del valor.",
         "DISPONIBLE", EXITO, MORADO, lambda: navegar("manual")),
        ("⚙", "Grafo automático",
         "Indica la cantidad de nodos y el rango de pesos; el sistema genera el grafo.",
         "DISPONIBLE", EXITO, ACENTO, lambda: navegar("auto")),
        ("▤", "Grafo por archivo",
         "Carga un archivo Excel o CSV con una fila por arista: origen, destino y peso.",
         "DISPONIBLE", EXITO, VERDE_AZULADO, lambda: navegar("archivo")),
    ]
    for i, (icono, titulo, descripcion, insignia, color_insignia, acento, comando) in enumerate(tarjetas):
        tarjeta = crear_tarjeta(fila, icono, titulo, descripcion, insignia,
                                color_insignia, acento, comando)
        tarjeta.grid(row=0, column=i, padx=14, sticky="nsew")
    for i in range(3):
        fila.grid_columnconfigure(i, weight=1, uniform="c")

    tk.Label(centro, text="Selecciona un método para generar tu grafo", bg=FONDO,
             fg=APAGADO, font=(FUENTE, 11)).pack(pady=(30, 0))
    return marco


# Función para crear un campo con su etiqueta, su texto de ayuda y su caja de texto
def crear_campo(padre, etiqueta, pista, variable):
    tk.Label(padre, text=etiqueta, bg=FONDO_TARJETA, fg=TEXTO,
             font=(FUENTE, 12, "bold")).pack(anchor="w")
    tk.Label(padre, text=pista, bg=FONDO_TARJETA, fg=APAGADO,
             font=(FUENTE, 10)).pack(anchor="w", pady=(0, 4))
    entrada = crear_entrada(padre, variable, ancho=30)
    entrada.pack(fill="x", ipady=6)
    return entrada


# Función para marcar la lista desplegable en rojo si hay error
def marcar_combo(caja, correcta):
    caja.config(style="Dark.TCombobox" if correcta else "Err.TCombobox")


# Función para construir la pantalla de generación automática del grafo
def construir_auto(padre):
    marco = tk.Frame(padre, bg=FONDO)
    tarjeta = tk.Frame(marco, bg=FONDO_TARJETA, highlightthickness=2,
                       highlightbackground=BORDE)
    tarjeta.place(relx=0.5, rely=0.5, anchor="center")
    tk.Frame(tarjeta, bg=ACENTO, height=5).pack(fill="x")
    cuerpo = tk.Frame(tarjeta, bg=FONDO_TARJETA, padx=40, pady=30)
    cuerpo.pack()

    tk.Label(cuerpo, text="Generación automática del grafo", bg=FONDO_TARJETA,
             fg=TEXTO, font=(FUENTE, 20, "bold")).pack(anchor="w")
    tk.Label(cuerpo, text="El grafo tendrá densidad aleatoria y siempre contendrá "
                          "al menos un ciclo hamiltoniano.",
             bg=FONDO_TARJETA, fg=APAGADO, font=(FUENTE, 11), wraplength=520,
             justify="left").pack(anchor="w", pady=(4, 22))

    auto["n_var"] = tk.StringVar()
    auto["n_entrada"] = crear_campo(cuerpo, "Cantidad de nodos (n)",
                                    f"Número entero entre {N_MIN} y {N_MAX}",
                                    auto["n_var"])

    tk.Label(cuerpo, text="¿Qué valor representarán los pesos?", bg=FONDO_TARJETA,
             fg=TEXTO, font=(FUENTE, 12, "bold")).pack(anchor="w", pady=(14, 0))
    tk.Label(cuerpo, text="Dinero, tiempo (horas / minutos) o distancia (km)",
             bg=FONDO_TARJETA, fg=APAGADO, font=(FUENTE, 10)).pack(anchor="w", pady=(0, 4))
    auto["unidad_var"] = tk.StringVar()
    auto["unidad_caja"] = ttk.Combobox(cuerpo, textvariable=auto["unidad_var"],
                                       state="readonly", values=list(UNIDADES.keys()),
                                       style="Dark.TCombobox", font=(FUENTE, 12))
    auto["unidad_caja"].pack(fill="x", ipady=4)
    auto["unidad_caja"].bind("<<ComboboxSelected>>", lambda e: marcar_combo(auto["unidad_caja"], True))

    tk.Label(cuerpo, text="Rango de los pesos", bg=FONDO_TARJETA, fg=TEXTO,
             font=(FUENTE, 12, "bold")).pack(anchor="w", pady=(14, 0))
    tk.Label(cuerpo, text="Números enteros positivos; el mínimo no puede superar al máximo",
             bg=FONDO_TARJETA, fg=APAGADO, font=(FUENTE, 10)).pack(anchor="w", pady=(0, 4))
    rango = tk.Frame(cuerpo, bg=FONDO_TARJETA)
    rango.pack(fill="x")
    auto["min_var"] = tk.StringVar()
    auto["max_var"] = tk.StringVar()

    izquierda = tk.Frame(rango, bg=FONDO_TARJETA)
    izquierda.pack(side="left", fill="x", expand=True, padx=(0, 8))
    tk.Label(izquierda, text="Mínimo", bg=FONDO_TARJETA, fg=APAGADO,
             font=(FUENTE, 10)).pack(anchor="w")
    auto["min_entrada"] = crear_entrada(izquierda, auto["min_var"])
    auto["min_entrada"].pack(fill="x", ipady=6)

    derecha = tk.Frame(rango, bg=FONDO_TARJETA)
    derecha.pack(side="left", fill="x", expand=True, padx=(8, 0))
    tk.Label(derecha, text="Máximo", bg=FONDO_TARJETA, fg=APAGADO,
             font=(FUENTE, 10)).pack(anchor="w")
    auto["max_entrada"] = crear_entrada(derecha, auto["max_var"])
    auto["max_entrada"].pack(fill="x", ipady=6)

    crear_boton(cuerpo, "Generar grafo", generar_auto, tam=13, pady=12).pack(
        fill="x", pady=(26, 0))

    for entrada in (auto["n_entrada"], auto["min_entrada"], auto["max_entrada"]):
        entrada.bind("<Return>", lambda ev: generar_auto())
    return marco


# Función que se ejecuta al abrir la pantalla automática: pone el cursor en la primera caja
def al_mostrar_auto():
    auto["n_entrada"].focus_set()


# Función para revisar que un texto sea un número entero y devolver el error si no lo es
def analizar_entero(texto, nombre):
    texto = texto.strip()
    if not texto:
        return None, f"{nombre}: el campo está vacío."
    try:
        return int(texto), None
    except ValueError:
        pass
    try:
        decimal = float(texto.replace(",", "."))
        if decimal != decimal or decimal in (float("inf"), float("-inf")):
            return None, f"{nombre}: «{texto}» no es un número válido."
        return None, f"{nombre}: «{texto}» es decimal; debe ser un número entero."
    except ValueError:
        return None, f"{nombre}: «{texto}» no es un número; ingresa solo dígitos."


# Función para validar los datos de la pantalla automática (nodos, tipo de valor y pesos)
def validar_auto():
    errores = []
    for entrada in (auto["n_entrada"], auto["min_entrada"], auto["max_entrada"]):
        marcar_entrada(entrada, True)
    marcar_combo(auto["unidad_caja"], True)

    n, error = analizar_entero(auto["n_var"].get(), "Cantidad de nodos")
    if error:
        errores.append(error)
        marcar_entrada(auto["n_entrada"], False)
    elif not (N_MIN <= n <= N_MAX):
        errores.append(f"Cantidad de nodos: {n} está fuera del rango permitido "
                       f"[{N_MIN}, {N_MAX}].")
        marcar_entrada(auto["n_entrada"], False)
        n = None

    if not auto["unidad_var"].get():
        errores.append("Tipo de valor: debes seleccionar si los pesos son costo, "
                       "tiempo (horas/minutos) o distancia (km).")
        marcar_combo(auto["unidad_caja"], False)

    peso_min, error = analizar_entero(auto["min_var"].get(), "Peso mínimo")
    if error:
        errores.append(error)
        marcar_entrada(auto["min_entrada"], False)
    elif not (1 <= peso_min <= LIMITE_PESO):
        errores.append(f"Peso mínimo: {peso_min} debe estar entre 1 y {LIMITE_PESO:,}.")
        marcar_entrada(auto["min_entrada"], False)
        peso_min = None

    peso_max, error = analizar_entero(auto["max_var"].get(), "Peso máximo")
    if error:
        errores.append(error)
        marcar_entrada(auto["max_entrada"], False)
    elif not (1 <= peso_max <= LIMITE_PESO):
        errores.append(f"Peso máximo: {peso_max} debe estar entre 1 y {LIMITE_PESO:,}.")
        marcar_entrada(auto["max_entrada"], False)
        peso_max = None

    if peso_min is not None and peso_max is not None and peso_min > peso_max:
        errores.append(f"Rango de pesos: el mínimo ({peso_min}) no puede ser mayor "
                       f"que el máximo ({peso_max}).")
        marcar_entrada(auto["min_entrada"], False)
        marcar_entrada(auto["max_entrada"], False)

    if errores:
        return None, errores
    return (n, auto["unidad_var"].get(), peso_min, peso_max), None


# Función para generar el grafo automático si los datos son correctos
def generar_auto():
    params, errores = validar_auto()
    if errores:
        mostrar_alerta("¡Datos incorrectos!", errores, "error")
        return
    construir_grafo(*params)


# Función para construir la pantalla del paso 1 del grafo manual
def construir_manual(padre):
    manual["n_actual"] = None
    manual["unidad"] = None
    manual["faltantes"] = []
    manual["vars"] = {}
    manual["entradas"] = {}

    marco = tk.Frame(padre, bg=FONDO)
    tarjeta = tk.Frame(marco, bg=FONDO_TARJETA, highlightthickness=2,
                       highlightbackground=BORDE)
    tarjeta.place(relx=0.5, rely=0.5, anchor="center")
    tk.Frame(tarjeta, bg=MORADO, height=5).pack(fill="x")
    cuerpo = tk.Frame(tarjeta, bg=FONDO_TARJETA, padx=40, pady=30)
    cuerpo.pack()

    tk.Label(cuerpo, text="Grafo manual · Paso 1 de 2", bg=FONDO_TARJETA,
             fg=TEXTO, font=(FUENTE, 20, "bold")).pack(anchor="w")
    tk.Label(cuerpo, text="Indica cuántos nodos tendrá el grafo y qué representarán "
                          "los pesos. En el siguiente paso definirás las aristas.",
             bg=FONDO_TARJETA, fg=APAGADO, font=(FUENTE, 11), wraplength=520,
             justify="left").pack(anchor="w", pady=(4, 22))

    manual["n_var"] = tk.StringVar()
    manual["n_entrada"] = crear_campo(cuerpo, "Cantidad de nodos (n)",
                                      f"Número entero entre {N_MIN} y {N_MAX}",
                                      manual["n_var"])

    tk.Label(cuerpo, text="¿Qué valor representarán los pesos?", bg=FONDO_TARJETA,
             fg=TEXTO, font=(FUENTE, 12, "bold")).pack(anchor="w", pady=(14, 0))
    tk.Label(cuerpo, text="Dinero, tiempo (horas / minutos) o distancia (km)",
             bg=FONDO_TARJETA, fg=APAGADO, font=(FUENTE, 10)).pack(anchor="w", pady=(0, 4))
    manual["unidad_var"] = tk.StringVar()
    manual["unidad_caja"] = ttk.Combobox(cuerpo, textvariable=manual["unidad_var"],
                                         state="readonly", values=list(UNIDADES.keys()),
                                         style="Dark.TCombobox", font=(FUENTE, 12))
    manual["unidad_caja"].pack(fill="x", ipady=4)
    manual["unidad_caja"].bind("<<ComboboxSelected>>",
                               lambda e: marcar_combo(manual["unidad_caja"], True))

    crear_boton(cuerpo, "Continuar  →", continuar_manual, tam=13, pady=12).pack(
        fill="x", pady=(26, 0))
    manual["n_entrada"].bind("<Return>", lambda ev: continuar_manual())
    return marco


# Función que se ejecuta al abrir el paso 1 del grafo manual: pone el cursor en la primera caja
def al_mostrar_manual():
    manual["n_entrada"].focus_set()


# Función para validar la cantidad de nodos y el tipo de valor (sirve para manual y archivo)
def validar_n_y_unidad(pantalla):
    errores = []
    marcar_entrada(pantalla["n_entrada"], True)
    marcar_combo(pantalla["unidad_caja"], True)

    n, error = analizar_entero(pantalla["n_var"].get(), "Cantidad de nodos")
    if error:
        errores.append(error)
        marcar_entrada(pantalla["n_entrada"], False)
    elif not (N_MIN <= n <= N_MAX):
        errores.append(f"Cantidad de nodos: {n} está fuera del rango permitido "
                       f"[{N_MIN}, {N_MAX}].")
        marcar_entrada(pantalla["n_entrada"], False)

    if not pantalla["unidad_var"].get():
        errores.append("Tipo de valor: debes seleccionar si los pesos son costo, "
                       "tiempo (horas/minutos) o distancia (km).")
        marcar_combo(pantalla["unidad_caja"], False)

    if errores:
        return None, errores
    return (n, pantalla["unidad_var"].get()), None


# Función para validar los datos del paso 1 del grafo manual
def validar_manual():
    return validar_n_y_unidad(manual)


# Función para pasar del paso 1 al paso 2 del grafo manual
def continuar_manual():
    datos, errores = validar_manual()
    if errores:
        mostrar_alerta("¡Datos incorrectos!", errores, "error")
        return
    n, unidad = datos
    manual["unidad"] = unidad
    if manual["n_actual"] != n:
        reconstruir_cuadricula(n)
    manual["lbl_unidad"].config(text=f"Los pesos representan: {unidad}")
    navegar("matriz")


# Función para construir el paso 2 del grafo manual: la matriz donde se escriben los pesos
def construir_pantalla_matriz(padre):
    marco = tk.Frame(padre, bg=FONDO)
    marco.grid_columnconfigure(0, weight=0, minsize=560)
    marco.grid_columnconfigure(1, weight=1)
    marco.grid_rowconfigure(0, weight=1)

    izquierda = tk.Frame(marco, bg=FONDO_TARJETA, highlightthickness=2,
                         highlightbackground=BORDE)
    izquierda.grid(row=0, column=0, sticky="nsew", padx=(18, 9), pady=18)
    tk.Frame(izquierda, bg=MORADO, height=5).pack(fill="x")
    interior = tk.Frame(izquierda, bg=FONDO_TARJETA, padx=18, pady=14)
    interior.pack(fill="both", expand=True)

    tk.Label(interior, text="Matriz de pesos · Paso 2 de 2", bg=FONDO_TARJETA, fg=TEXTO,
             font=(FUENTE, 16, "bold")).pack(anchor="w")
    manual["lbl_unidad"] = tk.Label(interior, text="", bg=FONDO_TARJETA, fg=AMBAR,
                                    font=(FUENTE, 11, "bold"))
    manual["lbl_unidad"].pack(anchor="w", pady=(2, 0))
    tk.Label(interior, text="Escribe el peso de cada arista en la mitad superior de la "
                            "matriz; la mitad inferior se completa sola. Deja vacía la "
                            "celda si esa arista no existe. Solo enteros positivos.",
             bg=FONDO_TARJETA, fg=APAGADO, font=(FUENTE, 10), wraplength=520,
             justify="left").pack(anchor="w", pady=(4, 0))

    manual["marco_matriz"] = tk.Frame(interior, bg=FONDO_TARJETA)
    manual["marco_matriz"].pack(anchor="w", pady=(10, 0))
    manual["lbl_contador"] = tk.Label(interior, text="", bg=FONDO_TARJETA, fg=APAGADO,
                                      font=(FUENTE, 10))
    manual["lbl_contador"].pack(anchor="w", pady=(10, 0))

    botones = tk.Frame(interior, bg=FONDO_TARJETA)
    botones.pack(fill="x", pady=(12, 0))
    botones.grid_columnconfigure(0, weight=3)
    botones.grid_columnconfigure(1, weight=1)
    crear_boton(botones, "Verificar y generar grafo  →", generar_manual).grid(
        row=0, column=0, sticky="ew", padx=(0, 4))
    crear_boton(botones, "Limpiar", limpiar_matriz, fondo=BORDE,
                hover="#3a4262").grid(row=0, column=1, sticky="ew", padx=(4, 0))

    derecha = tk.Frame(marco, bg=FONDO_TARJETA, highlightthickness=2,
                       highlightbackground=BORDE)
    derecha.grid(row=0, column=1, sticky="nsew", padx=(9, 18), pady=18)
    tk.Frame(derecha, bg=VERDE_AZULADO, height=5).pack(fill="x")

    leyenda = tk.Frame(derecha, bg=FONDO_TARJETA)
    leyenda.pack(side="bottom", fill="x", padx=12, pady=(0, 10))
    for texto, color in (("■ Ciclo sugerido (aristas existentes)", AMBAR),
                         ("┄ Arista faltante", ERROR),
                         ("● Nodo inicial", MORADO)):
        tk.Label(leyenda, text=texto, bg=FONDO_TARJETA, fg=color,
                 font=(FUENTE, 10, "bold")).pack(side="left", padx=8)

    panel = tk.Frame(derecha, bg=FONDO_TARJETA)
    panel.pack(side="bottom", fill="x", padx=14, pady=(0, 8))
    manual["lbl_estado"] = tk.Label(panel, text=MENSAJE_INICIAL, bg=FONDO_TARJETA,
                                    fg=APAGADO, font=(FUENTE, 11, "bold"),
                                    wraplength=420, justify="left")
    manual["lbl_estado"].pack(anchor="w")
    manual["btn_agregar"] = crear_boton(panel, "＋  Agregar aristas faltantes",
                                        agregar_faltantes, fondo=AMBAR,
                                        hover="#efbb73", fg=FONDO, pady=8)

    manual["lienzo"] = crear_lienzo(derecha)
    manual["lienzo"]["marco"].pack(fill="both", expand=True, padx=8, pady=8)
    return marco


# Función para armar la cuadrícula de n × n donde el usuario escribe los pesos
def reconstruir_cuadricula(n):
    marco = manual["marco_matriz"]
    for widget in marco.winfo_children():
        widget.destroy()
    manual["vars"].clear()
    manual["entradas"].clear()
    manual["n_actual"] = n
    manual["faltantes"] = []
    etiquetas = etiquetas_nodos(n)
    ancho = 5 if n <= 8 else 4

    tk.Label(marco, text="", bg=FONDO_TARJETA, width=3).grid(row=0, column=0)
    for j, b in enumerate(etiquetas):
        tk.Label(marco, text=b, bg="#2b3556", fg=TEXTO, font=(FUENTE, 11, "bold"),
                 pady=4).grid(row=0, column=j + 1, padx=1, pady=1, sticky="nsew")
    for i, a in enumerate(etiquetas):
        tk.Label(marco, text=a, bg="#2b3556", fg=TEXTO, font=(FUENTE, 11, "bold"),
                 padx=8).grid(row=i + 1, column=0, padx=1, pady=1, sticky="nsew")
        for j, b in enumerate(etiquetas):
            if i == j:
                tk.Label(marco, text="—", bg=FONDO_ENCABEZADO, fg=APAGADO,
                         font=(FUENTE, 11)).grid(row=i + 1, column=j + 1, padx=1,
                                                 pady=1, sticky="nsew")
            elif i < j:
                variable = tk.StringVar()
                variable.trace_add("write", lambda *args: al_cambiar_matriz())
                entrada = crear_entrada(marco, variable, ancho=ancho, tam=11,
                                        justificar="center")
                entrada.grid(row=i + 1, column=j + 1, padx=1, pady=1, sticky="nsew")
                entrada.bind("<Return>", lambda e, clave=(a, b): siguiente_celda(clave))
                manual["vars"][(a, b)] = variable
                manual["entradas"][(a, b)] = entrada
            else:
                tk.Label(marco, textvariable=manual["vars"][(b, a)],
                         bg=FONDO_ENCABEZADO, fg=APAGADO, font=(FUENTE, 11)).grid(
                    row=i + 1, column=j + 1, padx=1, pady=1, sticky="nsew")
    for c in range(1, n + 1):
        marco.grid_columnconfigure(c, uniform="celdas")

    actualizar_contador()
    restablecer_estado()
    dibujar_vista_previa()


# Función para pasar a la siguiente celda con Enter (en la última, verifica el grafo)
def siguiente_celda(clave):
    orden = list(manual["entradas"].keys())
    posicion = orden.index(clave)
    if posicion + 1 < len(orden):
        manual["entradas"][orden[posicion + 1]].focus_set()
    else:
        generar_manual()


# Función para actualizar el contador de aristas ingresadas
def actualizar_contador():
    llenas = sum(1 for v in manual["vars"].values() if v.get().strip())
    total = len(manual["vars"])
    manual["lbl_contador"].config(text=f"Aristas ingresadas: {llenas} de {total} posibles")


# Función para volver el mensaje de estado a su texto inicial y ocultar el botón de faltantes
def restablecer_estado():
    manual["faltantes"] = []
    manual["btn_agregar"].pack_forget()
    manual["lbl_estado"].config(text=MENSAJE_INICIAL, fg=APAGADO)


# Función que se ejecuta cada vez que cambia el contenido de una celda de la matriz
def al_cambiar_matriz():
    actualizar_contador()
    if manual["faltantes"]:
        restablecer_estado()


# Función para dibujar la vista previa del grafo, solo con los nodos y sin aristas
def dibujar_vista_previa():
    n = manual["n_actual"]
    G0 = nx.Graph()
    G0.add_nodes_from(etiquetas_nodos(n))
    dibujar_grafo(manual["lienzo"], G0, nx.circular_layout(G0),
                  f"Vista previa · {n} nodos · aún sin aristas")


# Función para borrar todos los pesos de la matriz
def limpiar_matriz():
    for variable in manual["vars"].values():
        variable.set("")
    for entrada in manual["entradas"].values():
        marcar_entrada(entrada, True)
    actualizar_contador()
    restablecer_estado()
    dibujar_vista_previa()


# Función para validar los pesos escritos en la matriz y devolver las aristas válidas
def validar_matriz():
    errores = []
    pesos = {}
    for entrada in manual["entradas"].values():
        marcar_entrada(entrada, True)
    for (a, b), variable in manual["vars"].items():
        texto = variable.get().strip()
        if not texto:
            continue
        valor, error = analizar_entero(texto, f"Arista {a}–{b}")
        if error:
            errores.append(error)
            marcar_entrada(manual["entradas"][(a, b)], False)
        elif not (1 <= valor <= LIMITE_PESO):
            errores.append(f"Arista {a}–{b}: {valor} debe estar entre 1 y {LIMITE_PESO:,}.")
            marcar_entrada(manual["entradas"][(a, b)], False)
        else:
            pesos[(a, b)] = valor
    if not errores and not pesos:
        errores.append("No has ingresado ninguna arista. Escribe al menos un peso "
                       "en la matriz.")
    if len(errores) > 8:
        errores = errores[:8] + [f"... y {len(errores) - 8} errores más."]
    return pesos, errores


# Función para verificar la matriz y generar el grafo manual (si faltan aristas, las informa)
def generar_manual():
    pesos, errores = validar_matriz()
    if errores:
        mostrar_alerta("¡Datos incorrectos!", errores, "error")
        return
    n = manual["n_actual"]
    raiz = estado["raiz"]
    raiz.config(cursor="watch")
    raiz.update_idletasks()
    ruta, faltantes = buscar_faltantes(etiquetas_nodos(n), pesos)
    raiz.config(cursor="")
    if faltantes:
        mostrar_faltantes(n, pesos, ruta, faltantes)
        return
    restablecer_estado()
    construir_grafo_desde_pesos(n, manual["unidad"], pesos, "manual")


# Función para dibujar el ciclo sugerido con las aristas faltantes en rojo punteado
def dibujar_ciclo_incompleto(lienzo, n, pesos, ruta, faltantes):
    G = nx.Graph()
    G.add_nodes_from(etiquetas_nodos(n))
    for (a, b), peso in pesos.items():
        G.add_edge(a, b, weight=peso)
    existentes = [e for e in aristas_ruta(ruta) if G.has_edge(*e)]
    dibujar_grafo(lienzo, G, nx.circular_layout(G), "Ciclo hamiltoniano incompleto",
                  ciclo=existentes, color_ciclo=AMBAR, faltantes=faltantes,
                  inicio=ruta[0])


# Función para informar qué aristas faltan en el grafo manual
def mostrar_faltantes(n, pesos, ruta, faltantes):
    manual["faltantes"] = faltantes
    lista = ", ".join(f"{a}–{b}" for a, b in faltantes)

    manual["lbl_estado"].config(
        text=f"✘ No existe ningún ciclo hamiltoniano. "
             f"Faltan {len(faltantes)} arista(s): {lista}", fg=ERROR)
    manual["btn_agregar"].pack(fill="x", pady=(8, 0))
    dibujar_ciclo_incompleto(manual["lienzo"], n, pesos, ruta, faltantes)
    mostrar_alerta("Faltan aristas", [
        "Con las aristas ingresadas no existe ningún ciclo hamiltoniano.",
        f"Para completar al menos uno faltan {len(faltantes)} arista(s): {lista}.",
        f"Ciclo sugerido: {texto_ruta(ruta)}",
        "Usa el botón «Agregar aristas faltantes» o escríbelas tú en la matriz.",
    ], "error")


# Función para abrir la ventana que pide el peso de cada arista faltante
def pedir_pesos_faltantes(faltantes):
    raiz = estado["raiz"]
    salida = {"pesos": None}
    entradas = {}
    variables = {}

    dialogo = tk.Toplevel(raiz)
    dialogo.withdraw()
    dialogo.title("Agregar aristas faltantes")
    dialogo.configure(bg=FONDO_TARJETA)
    dialogo.resizable(False, False)
    dialogo.transient(raiz)

    tk.Frame(dialogo, bg=AMBAR, height=6).pack(fill="x")
    cuerpo = tk.Frame(dialogo, bg=FONDO_TARJETA, padx=28, pady=22)
    cuerpo.pack(fill="both", expand=True)
    tk.Label(cuerpo, text="Pesos de las aristas faltantes", bg=FONDO_TARJETA, fg=TEXTO,
             font=(FUENTE, 15, "bold")).pack(anchor="w")
    tk.Label(cuerpo, text=f"Escribe un número entero positivo para cada arista "
                          f"({manual['unidad']}).", bg=FONDO_TARJETA, fg=APAGADO,
             font=(FUENTE, 11), wraplength=380, justify="left").pack(anchor="w",
                                                                    pady=(4, 0))

    lista = tk.Frame(cuerpo, bg=FONDO_TARJETA)
    lista.pack(fill="x", pady=(14, 0))
    for fila, (a, b) in enumerate(faltantes):
        tk.Label(lista, text=f"{a}  —  {b}", bg=FONDO_TARJETA, fg=TEXTO,
                 font=(FUENTE, 13, "bold")).grid(row=fila, column=0, sticky="w",
                                                 padx=(0, 20), pady=4)
        variable = tk.StringVar()
        entrada = crear_entrada(lista, variable, ancho=10, tam=12)
        entrada.grid(row=fila, column=1, pady=4, ipady=3)
        variables[(a, b)] = variable
        entradas[(a, b)] = entrada

    # Función interna: valida los pesos escritos y, si están bien, cierra la ventana
    def confirmar():
        pesos = {}
        errores = []
        for entrada in entradas.values():
            marcar_entrada(entrada, True)
        for (a, b), entrada in entradas.items():
            valor, error = analizar_entero(variables[(a, b)].get(), f"Arista {a}–{b}")
            if error:
                errores.append(error)
                marcar_entrada(entrada, False)
            elif not (1 <= valor <= LIMITE_PESO):
                errores.append(f"Arista {a}–{b}: {valor} debe estar entre 1 y "
                               f"{LIMITE_PESO:,}.")
                marcar_entrada(entrada, False)
            else:
                pesos[(a, b)] = valor
        if errores:
            mostrar_alerta("¡Datos incorrectos!", errores, "error")
            dialogo.grab_set()
            return
        salida["pesos"] = pesos
        dialogo.destroy()

    botones = tk.Frame(cuerpo, bg=FONDO_TARJETA)
    botones.pack(fill="x", pady=(18, 0))
    botones.grid_columnconfigure(0, weight=2)
    botones.grid_columnconfigure(1, weight=1)
    crear_boton(botones, "Agregar aristas", confirmar, pady=9).grid(
        row=0, column=0, sticky="ew", padx=(0, 4))
    crear_boton(botones, "Cancelar", dialogo.destroy, fondo=BORDE, hover="#3a4262",
                pady=9).grid(row=0, column=1, sticky="ew", padx=(4, 0))

    dialogo.bind("<Return>", lambda e: confirmar())
    dialogo.bind("<Escape>", lambda e: dialogo.destroy())
    dialogo.after(100, lambda: entradas[faltantes[0]].focus_set())
    centrar_ventana(dialogo)
    abrir_modal(dialogo)
    return salida["pesos"]


# Función para agregar a la matriz las aristas faltantes con los pesos que escribió el usuario
def agregar_faltantes():
    faltantes = manual["faltantes"]
    if not faltantes:
        return
    nuevos = pedir_pesos_faltantes(faltantes)
    if not nuevos:
        return
    for clave, peso in nuevos.items():
        manual["vars"][clave].set(str(peso))
    lista = ", ".join(f"{a}–{b}" for a, b in nuevos)
    mostrar_alerta("Aristas agregadas",
                   f"Se agregaron {len(nuevos)} arista(s) a la matriz: {lista}.",
                   "success")
    generar_manual()


# Función para crear el grafo a partir de un diccionario de pesos y mostrar el resultado
def construir_grafo_desde_pesos(n, unidad, pesos, origen):
    G = nx.Graph()
    G.add_nodes_from(etiquetas_nodos(n))
    for (a, b), peso in pesos.items():
        G.add_edge(a, b, weight=peso)
    valores = list(pesos.values())
    guardar_grafo(G, (n, unidad, min(valores), max(valores)), origen)
    navegar("result")


# Función para dejar el lienzo vacío con un mensaje en el centro
def limpiar_lienzo(lienzo, mensaje):
    figura = lienzo["figura"]
    figura.clear()
    figura.text(0.5, 0.5, mensaje, color=APAGADO, ha="center", va="center", fontsize=12)
    lienzo["canvas"].draw_idle()


# Función para crear un panel de texto de solo lectura con barra de desplazamiento
def crear_panel_texto(padre):
    marco = tk.Frame(padre, bg=FONDO_TARJETA)
    marco.pack(fill="both", expand=True, pady=(6, 0))
    texto = tk.Text(marco, height=8, bg=FONDO_ENTRADA, fg=TEXTO, font=(FUENTE, 10),
                    relief="flat", wrap="word", padx=10, pady=8,
                    highlightthickness=0, state="disabled")
    barra = ttk.Scrollbar(marco, orient="vertical", command=texto.yview,
                          style="Dark.Vertical.TScrollbar")
    texto.configure(yscrollcommand=barra.set)
    texto.pack(side="left", fill="both", expand=True)
    barra.pack(side="right", fill="y")
    return texto


# Función para escribir un mensaje en el panel de texto con el color indicado
def escribir_panel(lineas, color):
    panel = archivo["panel"]
    panel.config(state="normal")
    panel.delete("1.0", "end")
    panel.tag_configure("color", foreground=color)
    panel.insert("end", "\n".join(lineas), "color")
    panel.config(state="disabled")


# Función para ajustar el ancho de las columnas de un Excel según su contenido
def ajustar_columnas(escritor):
    for hoja in escritor.sheets.values():
        for columna in hoja.iter_cols(min_row=1, max_row=min(hoja.max_row, 2000)):
            ancho = max(len(str(celda.value)) if celda.value is not None else 0
                        for celda in columna)
            hoja.column_dimensions[columna[0].column_letter].width = min(ancho + 3, 70)


# Función para construir la pantalla del grafo por archivo
def construir_archivo(padre):
    marco = tk.Frame(padre, bg=FONDO)
    marco.grid_columnconfigure(0, weight=0, minsize=560)
    marco.grid_columnconfigure(1, weight=1)
    marco.grid_rowconfigure(0, weight=1)

    izquierda = tk.Frame(marco, bg=FONDO_TARJETA, highlightthickness=2,
                         highlightbackground=BORDE)
    izquierda.grid(row=0, column=0, sticky="nsew", padx=(18, 9), pady=18)
    tk.Frame(izquierda, bg=VERDE_AZULADO, height=5).pack(fill="x")
    interior = tk.Frame(izquierda, bg=FONDO_TARJETA, padx=24, pady=16)
    interior.pack(fill="both", expand=True)

    tk.Label(interior, text="Grafo por archivo", bg=FONDO_TARJETA, fg=TEXTO,
             font=(FUENTE, 20, "bold")).pack(anchor="w")
    tk.Label(interior, text="Carga un archivo Excel (.xlsx, .xls) o CSV con las columnas "
                            "Origen, Destino y Peso: una fila por arista.",
             bg=FONDO_TARJETA, fg=APAGADO, font=(FUENTE, 11), wraplength=500,
             justify="left").pack(anchor="w", pady=(4, 12))

    archivo["n_var"] = tk.StringVar()
    archivo["n_entrada"] = crear_campo(interior, "Cantidad de nodos (n)",
                                       f"Número entero entre {N_MIN} y {N_MAX}",
                                       archivo["n_var"])

    tk.Label(interior, text="¿Qué valor representarán los pesos?", bg=FONDO_TARJETA,
             fg=TEXTO, font=(FUENTE, 12, "bold")).pack(anchor="w", pady=(10, 0))
    tk.Label(interior, text="Dinero, tiempo (horas / minutos) o distancia (km)",
             bg=FONDO_TARJETA, fg=APAGADO, font=(FUENTE, 10)).pack(anchor="w", pady=(0, 4))
    archivo["unidad_var"] = tk.StringVar()
    archivo["unidad_caja"] = ttk.Combobox(interior, textvariable=archivo["unidad_var"],
                                          state="readonly", values=list(UNIDADES.keys()),
                                          style="Dark.TCombobox", font=(FUENTE, 12))
    archivo["unidad_caja"].pack(fill="x", ipady=4)
    archivo["unidad_caja"].bind("<<ComboboxSelected>>",
                                lambda e: marcar_combo(archivo["unidad_caja"], True))

    botones = tk.Frame(interior, bg=FONDO_TARJETA)
    botones.pack(fill="x", pady=(16, 0))
    botones.grid_columnconfigure(0, weight=1, uniform="ba")
    botones.grid_columnconfigure(1, weight=1, uniform="ba")
    crear_boton(botones, "⭳  Descargar plantilla", descargar_plantilla, fondo=BORDE,
                hover="#3a4262", tam=10, pady=9).grid(row=0, column=0, sticky="ew",
                                                      padx=(0, 4))
    crear_boton(botones, "Seleccionar archivo  →", cargar_archivo, tam=10,
                pady=9).grid(row=0, column=1, sticky="ew", padx=(4, 0))

    archivo["lbl_archivo"] = tk.Label(interior, text="Ningún archivo cargado todavía.",
                                      bg=FONDO_TARJETA, fg=AMBAR, font=(FUENTE, 10, "bold"),
                                      wraplength=500, justify="left")
    archivo["lbl_archivo"].pack(anchor="w", pady=(12, 0))
    tk.Label(interior, text="Resultado de la validación", bg=FONDO_TARJETA, fg=TEXTO,
             font=(FUENTE, 12, "bold")).pack(anchor="w", pady=(8, 0))
    archivo["panel"] = crear_panel_texto(interior)

    derecha = tk.Frame(marco, bg=FONDO_TARJETA, highlightthickness=2,
                       highlightbackground=BORDE)
    derecha.grid(row=0, column=1, sticky="nsew", padx=(9, 18), pady=18)
    tk.Frame(derecha, bg=ACENTO, height=5).pack(fill="x")
    leyenda = tk.Frame(derecha, bg=FONDO_TARJETA)
    leyenda.pack(side="bottom", fill="x", padx=12, pady=(0, 10))
    for texto, color in (("■ Ciclo sugerido (aristas existentes)", AMBAR),
                         ("┄ Arista faltante", ERROR),
                         ("● Nodo inicial", MORADO)):
        tk.Label(leyenda, text=texto, bg=FONDO_TARJETA, fg=color,
                 font=(FUENTE, 10, "bold")).pack(side="left", padx=8)
    archivo["lienzo"] = crear_lienzo(derecha)
    archivo["lienzo"]["marco"].pack(fill="both", expand=True, padx=8, pady=8)

    escribir_panel(["Aquí aparecerá el resultado de la validación del archivo.",
                    "Si hay errores, corrígelos en el archivo y vuelve a cargarlo."],
                   APAGADO)
    limpiar_lienzo(archivo["lienzo"], "La vista previa aparecerá aquí")
    archivo["n_entrada"].bind("<Return>", lambda ev: cargar_archivo())
    return marco


# Función que se ejecuta al abrir la pantalla de archivo: pone el cursor en la primera caja
def al_mostrar_archivo():
    archivo["n_entrada"].focus_set()


# Función para obtener solo el nombre del archivo a partir de su ruta completa
def nombre_archivo(ruta):
    return ruta.replace("\\", "/").split("/")[-1]


# Función para guardar una plantilla de Excel con el formato que debe tener el archivo
def descargar_plantilla():
    ruta_archivo = filedialog.asksaveasfilename(
        parent=estado["raiz"], title="Guardar plantilla de Excel",
        defaultextension=".xlsx", initialfile="plantilla_grafo.xlsx",
        filetypes=[("Excel", "*.xlsx")])
    if not ruta_archivo:
        return
    ejemplo = pd.DataFrame({
        "Origen": ["A", "B", "C", "D", "E", "A", "B", "C"],
        "Destino": ["B", "C", "D", "E", "A", "C", "D", "E"],
        "Peso": [10, 15, 20, 12, 18, 25, 30, 22],
    })
    instrucciones = pd.DataFrame({"Instrucciones": [
        "Escribe una fila por arista en la hoja «Aristas» (la primera hoja del libro).",
        "No cambies los encabezados: Origen, Destino y Peso.",
        "Origen y Destino: letras de los nodos (A, B, C...) sin saltar letras.",
        "Peso: número entero positivo (mayor que 0).",
        "Una arista A–B es igual a B–A: escríbela una sola vez.",
        "No uses una arista de un nodo consigo mismo (A–A).",
        f"La cantidad de nodos debe estar entre {N_MIN} y {N_MAX}.",
        "Debe existir al menos un ciclo hamiltoniano que pase por todos los nodos.",
        "Las filas de ejemplo de la hoja «Aristas» se pueden borrar o reemplazar.",
    ]})
    try:
        with pd.ExcelWriter(ruta_archivo, engine="openpyxl") as escritor:
            ejemplo.to_excel(escritor, sheet_name="Aristas", index=False)
            instrucciones.to_excel(escritor, sheet_name="Instrucciones", index=False)
            ajustar_columnas(escritor)
    except ImportError:
        mostrar_alerta("Falta una librería",
                       "Para crear archivos Excel hay que instalar openpyxl. "
                       "Ejecuta en la terminal: pip install openpyxl", "error")
        return
    except OSError as error:
        mostrar_alerta("No se pudo guardar", f"Ocurrió un error al guardar: {error}",
                       "error")
        return
    mostrar_alerta("Plantilla guardada",
                   f"Se guardó la plantilla en:\n{ruta_archivo}\n"
                   f"Complétala y cárgala con «Seleccionar archivo».", "success")


# Función para leer el archivo (Excel o CSV) con Pandas, decidiendo cómo leerlo por su contenido
def leer_archivo(ruta):
    if not ruta.lower().endswith((".xlsx", ".xls", ".csv")):
        return None, "Formato no admitido: usa un archivo .xlsx, .xls o .csv."
    try:
        with open(ruta, "rb") as flujo:
            cabecera = flujo.read(8)
    except OSError as error:
        return None, f"No se pudo abrir el archivo: {error}"
    if not cabecera:
        return None, "El archivo está vacío."

    try:
        if cabecera.startswith(b"PK") or cabecera.startswith(b"\xd0\xcf\x11\xe0"):
            df = pd.read_excel(ruta, dtype=str)
        else:
            try:
                df = pd.read_csv(ruta, sep=None, engine="python", dtype=str,
                                 encoding="utf-8-sig")
            except UnicodeDecodeError:
                df = pd.read_csv(ruta, sep=None, engine="python", dtype=str,
                                 encoding="latin-1")
    except ImportError:
        return None, ("Falta instalar la librería para leer Excel. Ejecuta en la "
                      "terminal: pip install openpyxl (para archivos .xls antiguos: "
                      "pip install xlrd).")
    except pd.errors.EmptyDataError:
        return None, "El archivo está vacío."
    except Exception as error:
        if "delimiter" in str(error):
            return None, ("No se reconoce el formato del archivo: debe ser un Excel "
                          "(.xlsx) real o un CSV con las columnas Origen, Destino y "
                          "Peso separadas por comas o punto y coma.")
        return None, f"No se pudo leer el archivo: {error}"
    return df, None


# Función para convertir el valor de una celda en texto sin espacios (vacío si no hay dato)
def limpiar_celda(valor):
    if pd.isna(valor):
        return ""
    return str(valor).strip()


# Función para validar el peso de una fila del archivo (entero entre 1 y el límite)
def analizar_peso_archivo(texto, fila):
    if not texto:
        return None, f"Fila {fila}: falta el peso."
    try:
        valor = int(texto)
    except ValueError:
        try:
            decimal = float(texto.replace(",", "."))
        except ValueError:
            return None, f"Fila {fila}: el peso «{texto}» no es un número."
        if decimal != decimal or decimal in (float("inf"), float("-inf")):
            return None, f"Fila {fila}: el peso «{texto}» no es un número válido."
        if not decimal.is_integer():
            return None, f"Fila {fila}: el peso «{texto}» es decimal; debe ser un entero."
        valor = int(decimal)
    if not (1 <= valor <= LIMITE_PESO):
        return None, f"Fila {fila}: el peso {valor} debe estar entre 1 y {LIMITE_PESO:,}."
    return valor, None


# Función para validar todas las filas del archivo y devolver las aristas con sus pesos
def validar_aristas(df, n):
    errores = []
    pesos = {}
    vistos = {}
    etiquetas = etiquetas_nodos(n)
    rango = f"{etiquetas[0]}–{etiquetas[-1]}"

    df.columns = [str(c).strip().lower() for c in df.columns]
    requeridas = ["origen", "destino", "peso"]
    faltan = [c.capitalize() for c in requeridas if c not in df.columns]
    if faltan:
        encontradas = ", ".join(str(c) for c in df.columns) or "ninguno"
        return pesos, [f"Faltan las columnas: {', '.join(faltan)}. Encabezados "
                       f"encontrados: {encontradas}. La primera fila debe ser: "
                       f"Origen, Destino, Peso."]

    for posicion, (origen, destino, peso) in enumerate(df[requeridas].values.tolist()):
        fila = posicion + 2
        textos = [limpiar_celda(origen), limpiar_celda(destino), limpiar_celda(peso)]
        if not any(textos):
            continue

        nodos = []
        for nombre, texto in (("Origen", textos[0]), ("Destino", textos[1])):
            if not texto:
                errores.append(f"Fila {fila}: falta el dato de {nombre}.")
                nodos.append(None)
            elif len(texto) == 1 and texto.upper() in etiquetas:
                nodos.append(texto.upper())
            elif len(texto) == 1 and texto.isalpha():
                errores.append(f"Fila {fila}: el nodo «{texto.upper()}» no existe; con "
                               f"n = {n} los nodos son {rango}.")
                nodos.append(None)
            else:
                errores.append(f"Fila {fila}: {nombre} «{texto}» no es válido; usa una "
                               f"letra de la {etiquetas[0]} a la {etiquetas[-1]}.")
                nodos.append(None)

        valor, error = analizar_peso_archivo(textos[2], fila)
        if error:
            errores.append(error)
        if None in nodos or error:
            continue

        a, b = nodos
        if a == b:
            errores.append(f"Fila {fila}: la arista {a}–{b} une un nodo consigo mismo.")
            continue
        clave = (a, b) if a < b else (b, a)
        if clave in vistos:
            errores.append(f"Fila {fila}: la arista {clave[0]}–{clave[1]} ya aparece "
                           f"en la fila {vistos[clave]}.")
            continue
        vistos[clave] = fila
        pesos[clave] = valor

    if not pesos and not errores:
        errores.append("El archivo no contiene ninguna arista. Escribe al menos una "
                       "fila con Origen, Destino y Peso.")
    return pesos, errores


# Función para mostrar los errores del archivo en el panel y en una alerta
def informar_errores(errores):
    total = len(errores)
    lineas = [f"✘ Se encontraron {total} problema(s). Corrige el archivo y vuelve a "
              f"cargarlo:"]
    lineas += [f"{i}. {e}" for i, e in enumerate(errores[:MAX_ERRORES], 1)]
    if total > MAX_ERRORES:
        lineas.append(f"... y {total - MAX_ERRORES} problema(s) más.")
    escribir_panel(lineas, ERROR)
    limpiar_lienzo(archivo["lienzo"], "Hay errores en el archivo")
    resumen = errores[:8]
    if total > 8:
        resumen.append(f"... y {total - 8} problema(s) más. Revisa el detalle en el "
                       f"panel de validación.")
    mostrar_alerta("Archivo con errores", resumen, "error")


# Función para cargar el archivo, validarlo y generar el grafo si todo está correcto
def cargar_archivo():
    datos, errores = validar_n_y_unidad(archivo)
    if errores:
        mostrar_alerta("¡Datos incorrectos!", errores, "error")
        return
    n, unidad = datos

    ruta = filedialog.askopenfilename(
        parent=estado["raiz"], title="Seleccionar archivo del grafo",
        filetypes=[("Excel o CSV", "*.xlsx *.xls *.csv"), ("Excel", "*.xlsx *.xls"),
                   ("CSV", "*.csv")])
    if not ruta:
        return
    archivo["lbl_archivo"].config(text="Archivo: " + nombre_archivo(ruta))

    df, error = leer_archivo(ruta)
    if error:
        informar_errores([error])
        return
    pesos, errores = validar_aristas(df, n)
    if errores:
        informar_errores(errores)
        return

    raiz = estado["raiz"]
    raiz.config(cursor="watch")
    raiz.update_idletasks()
    ruta_sugerida, faltantes = buscar_faltantes(etiquetas_nodos(n), pesos)
    raiz.config(cursor="")

    if faltantes:
        lista = ", ".join(f"{a}–{b}" for a, b in faltantes)
        escribir_panel([
            "✘ El archivo tiene el formato correcto, pero con esas aristas no existe "
            "ningún ciclo hamiltoniano.",
            f"Faltan {len(faltantes)} arista(s): {lista}.",
            f"Ciclo sugerido: {texto_ruta(ruta_sugerida)}",
            "Agrega esas filas (Origen, Destino, Peso) al archivo y vuelve a cargarlo.",
        ], ERROR)
        dibujar_ciclo_incompleto(archivo["lienzo"], n, pesos, ruta_sugerida, faltantes)
        mostrar_alerta("Faltan aristas", [
            "Con las aristas del archivo no existe ningún ciclo hamiltoniano.",
            f"Para completar al menos uno faltan {len(faltantes)} arista(s): {lista}.",
            f"Ciclo sugerido: {texto_ruta(ruta_sugerida)}",
            "Agrégalas al archivo y vuelve a cargarlo.",
        ], "error")
        return

    escribir_panel([f"✔ Archivo válido: {len(pesos)} aristas leídas y existe al menos "
                    f"un ciclo hamiltoniano."], EXITO)
    construir_grafo_desde_pesos(n, unidad, pesos, "archivo")


# Función para construir la pantalla que muestra el grafo generado
def construir_resultado(padre):
    marco = tk.Frame(padre, bg=FONDO)
    marco.grid_columnconfigure(0, weight=0, minsize=360)
    marco.grid_columnconfigure(1, weight=1)
    marco.grid_rowconfigure(0, weight=1)

    izquierda = tk.Frame(marco, bg=FONDO_TARJETA, highlightthickness=2,
                         highlightbackground=BORDE)
    izquierda.grid(row=0, column=0, sticky="nsew", padx=(18, 9), pady=18)
    tk.Frame(izquierda, bg=ACENTO, height=5).pack(fill="x")
    interior = tk.Frame(izquierda, bg=FONDO_TARJETA, padx=18, pady=16)
    interior.pack(fill="both", expand=True)

    tk.Label(interior, text="Resumen del grafo", bg=FONDO_TARJETA, fg=TEXTO,
             font=(FUENTE, 16, "bold")).pack(anchor="w")

    estadisticas = tk.Frame(interior, bg=FONDO_TARJETA)
    estadisticas.pack(fill="x", pady=(12, 12))
    resultado["stats"] = {}
    claves = [("Nodos", ACENTO), ("Aristas", MORADO),
              ("Tipo de valor", VERDE_AZULADO), ("Rango de pesos", AMBAR)]
    for i, (clave, color) in enumerate(claves):
        resultado["stats"][clave] = crear_estadistica(estadisticas, i // 2, i % 2,
                                                      clave, color)
    estadisticas.grid_columnconfigure(0, weight=1, uniform="s")
    estadisticas.grid_columnconfigure(1, weight=1, uniform="s")

    tk.Label(interior, text="Aristas y pesos", bg=FONDO_TARJETA, fg=TEXTO,
             font=(FUENTE, 12, "bold")).pack(anchor="w", pady=(4, 6))

    botones = tk.Frame(interior, bg=FONDO_TARJETA)
    botones.pack(side="bottom", fill="x", pady=(14, 0))
    crear_boton(botones, "Calcular ciclos hamiltonianos  →",
                lambda: navegar("solve")).pack(fill="x")
    resultado["btn_secundario"] = crear_boton(botones, "↻  Regenerar grafo",
                                              accion_secundaria, fondo=MORADO,
                                              hover=MORADO_HOVER)
    resultado["btn_secundario"].pack(fill="x", pady=(8, 0))

    resultado["tabla"] = crear_tabla(interior, [
        ("o", "Origen", 80, "center"),
        ("d", "Destino", 80, "center"),
        ("p", "Peso", 100, "center"),
    ])

    derecha = tk.Frame(marco, bg=FONDO_TARJETA, highlightthickness=2,
                       highlightbackground=BORDE)
    derecha.grid(row=0, column=1, sticky="nsew", padx=(9, 18), pady=18)
    tk.Frame(derecha, bg=VERDE_AZULADO, height=5).pack(fill="x")
    resultado["lienzo"] = crear_lienzo(derecha)
    resultado["lienzo"]["marco"].pack(fill="both", expand=True, padx=8, pady=8)
    return marco


# Función del botón morado: regenera el grafo (automático) o vuelve a editar (manual o archivo)
def accion_secundaria():
    if estado["origen"] in ("manual", "archivo"):
        retroceder()
    else:
        regenerar_grafo()


# Función para generar otro grafo aleatorio con los mismos datos
def regenerar_grafo():
    n, unidad, peso_min, peso_max = estado["params"]
    construir_grafo(n, unidad, peso_min, peso_max, ir_a_resultado=False)
    cargar_resultado()


# Función para llenar la pantalla de resultado con los datos y el dibujo del grafo
def cargar_resultado():
    G = estado["grafo"]
    if G is None:
        return
    n, unidad, peso_min, peso_max = estado["params"]
    simbolo, encabezado = UNIDADES[unidad]

    if estado["origen"] == "manual":
        resultado["btn_secundario"].config(text="✎  Editar matriz de pesos")
    elif estado["origen"] == "archivo":
        resultado["btn_secundario"].config(text="↩  Cargar otro archivo")
    else:
        resultado["btn_secundario"].config(text="↻  Regenerar grafo")

    stats = resultado["stats"]
    stats["Nodos"].config(text=str(G.number_of_nodes()))
    stats["Aristas"].config(text=str(G.number_of_edges()))
    stats["Tipo de valor"].config(text=unidad.split(" (")[0] + f" ({simbolo})")
    stats["Rango de pesos"].config(text=f"{peso_min} – {peso_max}")

    tabla = resultado["tabla"]
    tabla.heading("p", text=encabezado)
    tabla.delete(*tabla.get_children())
    for _, fila in estado["aristas_df"].iterrows():
        tabla.insert("", "end", values=(fila["Origen"], fila["Destino"], fila["Peso"]))

    dibujar_grafo(resultado["lienzo"], G, estado["pos"],
                  f"Grafo ponderado no dirigido  ·  {n} nodos  ·  pesos en {simbolo}")


# Función para construir la pestaña 1: la matriz de costos
def construir_pestana_matriz(pestana):
    tk.Label(pestana, text="Matriz de costos", bg=FONDO_TARJETA, fg=TEXTO,
             font=(FUENTE, 16, "bold")).pack(anchor="w")
    tk.Label(pestana, text="Se construyó automáticamente a partir del grafo.  "
                           "∞ = no existe arista entre los nodos.",
             bg=FONDO_TARJETA, fg=APAGADO, font=(FUENTE, 10), wraplength=470,
             justify="left").pack(anchor="w", pady=(2, 12))
    sol["matriz"] = crear_matriz(pestana)
    sol["matriz"]["marco"].pack(anchor="w")
    sol["lbl_total"] = tk.Label(pestana, text="", bg=FONDO_TARJETA, fg=APAGADO,
                                font=(FUENTE, 11), wraplength=470, justify="left")
    sol["lbl_total"].pack(anchor="w", pady=(14, 0))

    crear_boton(pestana, "Iniciar paso a paso  →",
                lambda: sol["cuaderno"].select(sol["tab_pasos"])).pack(fill="x", pady=(18, 0))
    crear_boton(pestana, "⚡  Ejecutar fuerza bruta completa", ejecutar_todo,
                fondo=MORADO, hover=MORADO_HOVER).pack(fill="x", pady=(8, 0))


# Función para construir la pestaña 2: la fuerza bruta paso a paso
def construir_pestana_pasos(pestana):
    estadisticas = tk.Frame(pestana, bg=FONDO_TARJETA)
    estadisticas.pack(fill="x")
    for i in range(3):
        estadisticas.grid_columnconfigure(i, weight=1, uniform="st")
    sol["s_eval"] = crear_estadistica(estadisticas, 0, 0, "Rutas evaluadas", ACENTO)
    sol["s_validas"] = crear_estadistica(estadisticas, 0, 1, "Ciclos válidos", EXITO)
    sol["s_mejor"] = crear_estadistica(estadisticas, 0, 2, "Mejor costo actual", AMBAR)

    actual = tk.Frame(pestana, bg=FONDO_ENTRADA, padx=12, pady=10)
    actual.pack(fill="x", pady=10)
    tk.Label(actual, text="Ruta en evaluación", bg=FONDO_ENTRADA, fg=APAGADO,
             font=(FUENTE, 9)).pack(anchor="w")
    sol["lbl_ruta"] = tk.Label(actual, text="—", bg=FONDO_ENTRADA, fg=TEXTO,
                               wraplength=470, justify="left",
                               font=(FUENTE, 13, "bold"))
    sol["lbl_ruta"].pack(anchor="w", pady=(2, 2))
    sol["lbl_estado"] = tk.Label(actual, text="Pulsa «Siguiente ruta» para comenzar.",
                                 bg=FONDO_ENTRADA, fg=APAGADO, wraplength=470,
                                 justify="left", font=(FUENTE, 11, "bold"))
    sol["lbl_estado"].pack(anchor="w")
    sol["lbl_calculo"] = tk.Label(actual, text="", bg=FONDO_ENTRADA, fg=APAGADO,
                                  wraplength=470, justify="left", font=(FUENTE, 10))
    sol["lbl_calculo"].pack(anchor="w", pady=(2, 0))

    botones = tk.Frame(pestana, bg=FONDO_TARJETA)
    botones.pack(fill="x")
    for i in range(3):
        botones.grid_columnconfigure(i, weight=1, uniform="b")
    crear_boton(botones, "Siguiente ruta ▶", lambda: avanzar_paso(1),
                tam=10, padx=8, pady=8).grid(row=0, column=0, sticky="ew", padx=3, pady=3)
    crear_boton(botones, "Siguiente válida ⏭", lambda: avanzar_paso(None, True),
                tam=10, padx=8, pady=8).grid(row=0, column=1, sticky="ew", padx=3, pady=3)
    crear_boton(botones, "+100 rutas ⏩", lambda: avanzar_paso(100),
                tam=10, padx=8, pady=8).grid(row=0, column=2, sticky="ew", padx=3, pady=3)
    crear_boton(botones, "⚡ Ejecutar todo", ejecutar_todo, fondo=MORADO,
                hover=MORADO_HOVER, tam=10, padx=8, pady=8).grid(
        row=1, column=0, columnspan=2, sticky="ew", padx=3, pady=3)
    crear_boton(botones, "↺ Reiniciar", reiniciar_solucion, fondo=BORDE,
                hover="#3a4262", tam=10, padx=8, pady=8).grid(
        row=1, column=2, sticky="ew", padx=3, pady=3)

    tk.Label(pestana, text="Registro de rutas evaluadas (más reciente arriba)",
             bg=FONDO_TARJETA, fg=TEXTO, font=(FUENTE, 11, "bold")).pack(
        anchor="w", pady=(10, 4))
    sol["log"] = crear_tabla(pestana, [
        ("n", "N°", 55, "center"),
        ("ruta", "Ruta", 220, "w"),
        ("estado", "Estado", 105, "center"),
        ("costo", "Costo", 70, "center"),
    ])
    sol["log"].tag_configure("valid", foreground=EXITO)
    sol["log"].tag_configure("invalid", foreground="#c9788a")


# Función para construir la pestaña 3: los resultados y el ciclo óptimo
def construir_pestana_resultados(pestana):
    sol["res_placeholder"] = tk.Label(
        pestana, text="Aún no se ha completado la búsqueda.\n\n"
                      "Avanza paso a paso hasta evaluar todas las rutas\n"
                      "o usa «Ejecutar todo» para ver los resultados.",
        bg=FONDO_TARJETA, fg=APAGADO, font=(FUENTE, 12), justify="center")
    sol["res_placeholder"].pack(expand=True)

    cuerpo = tk.Frame(pestana, bg=FONDO_TARJETA)
    sol["res_cuerpo"] = cuerpo
    tk.Label(cuerpo, text="Solución del problema", bg=FONDO_TARJETA, fg=TEXTO,
             font=(FUENTE, 16, "bold")).pack(anchor="w")
    estadisticas = tk.Frame(cuerpo, bg=FONDO_TARJETA)
    estadisticas.pack(fill="x", pady=(8, 6))
    for i in range(3):
        estadisticas.grid_columnconfigure(i, weight=1, uniform="rs")
    sol["r_ciclos"] = crear_estadistica(estadisticas, 0, 0, "Ciclos hamiltonianos", EXITO)
    sol["r_eval"] = crear_estadistica(estadisticas, 0, 1, "Rutas evaluadas", ACENTO)
    sol["r_mejor"] = crear_estadistica(estadisticas, 0, 2, "Costo óptimo", AMBAR)

    banner = tk.Frame(cuerpo, bg=FONDO_ENTRADA, padx=12, pady=9)
    banner.pack(fill="x", pady=(2, 8))
    tk.Label(banner, text="★ Ciclo hamiltoniano óptimo", bg=FONDO_ENTRADA, fg=APAGADO,
             font=(FUENTE, 9)).pack(anchor="w")
    sol["r_ruta"] = tk.Label(banner, text="", bg=FONDO_ENTRADA, fg=EXITO,
                             wraplength=470, justify="left", font=(FUENTE, 12, "bold"))
    sol["r_ruta"].pack(anchor="w")
    sol["r_empates"] = tk.Label(banner, text="", bg=FONDO_ENTRADA, fg=AMBAR,
                                wraplength=470, justify="left", font=(FUENTE, 10))
    sol["r_empates"].pack(anchor="w")

    botones = tk.Frame(cuerpo, bg=FONDO_TARJETA)
    botones.pack(side="bottom", fill="x", pady=(10, 0))
    botones.grid_columnconfigure(0, weight=1, uniform="rb")
    botones.grid_columnconfigure(1, weight=1, uniform="rb")
    crear_boton(botones, "★ Ver ciclo óptimo", lambda: mostrar_ciclo(0), tam=10,
                pady=8).grid(row=0, column=0, sticky="ew", padx=3)
    crear_boton(botones, "⭳ Exportar Excel", exportar_excel, fondo=VERDE_AZULADO,
                hover="#47c4b1", tam=10, pady=8).grid(row=0, column=1, sticky="ew", padx=3)
    sol["r_nota"] = tk.Label(cuerpo, text="", bg=FONDO_TARJETA, fg=APAGADO,
                             font=(FUENTE, 9), wraplength=470, justify="left")
    sol["r_nota"].pack(side="bottom", anchor="w", pady=(6, 0))

    sol["res_tabla"] = crear_tabla(cuerpo, [
        ("n", "N°", 55, "center"),
        ("ciclo", "Ciclo hamiltoniano", 270, "w"),
        ("costo", "Costo total", 100, "center"),
    ], modo="browse")
    sol["res_tabla"].tag_configure("best", foreground=EXITO)
    sol["res_tabla"].bind("<<TreeviewSelect>>", al_seleccionar)


# Función para construir la pantalla de la fuerza bruta con sus tres pestañas
def construir_solucion(padre):
    marco = tk.Frame(padre, bg=FONDO)
    sol["cargado"] = None
    sol["motor"] = None
    sol["simbolo"] = ""
    sol["df_costos"] = None
    sol["df_resultados"] = None
    sol["ciclos"] = []
    sol["sincronizando"] = False

    marco.grid_columnconfigure(0, weight=0, minsize=540)
    marco.grid_columnconfigure(1, weight=1)
    marco.grid_rowconfigure(0, weight=1)

    izquierda = tk.Frame(marco, bg=FONDO_TARJETA, highlightthickness=2,
                         highlightbackground=BORDE)
    izquierda.grid(row=0, column=0, sticky="nsew", padx=(18, 9), pady=18)
    tk.Frame(izquierda, bg=MORADO, height=5).pack(fill="x")
    sol["cuaderno"] = ttk.Notebook(izquierda, style="Dark.TNotebook")
    sol["cuaderno"].pack(fill="both", expand=True, padx=10, pady=10)

    sol["tab_matriz"] = tk.Frame(sol["cuaderno"], bg=FONDO_TARJETA, padx=14, pady=12)
    sol["tab_pasos"] = tk.Frame(sol["cuaderno"], bg=FONDO_TARJETA, padx=14, pady=12)
    sol["tab_res"] = tk.Frame(sol["cuaderno"], bg=FONDO_TARJETA, padx=14, pady=12)
    sol["cuaderno"].add(sol["tab_matriz"], text=" 1 · Matriz de costos ")
    sol["cuaderno"].add(sol["tab_pasos"], text=" 2 · Paso a paso ")
    sol["cuaderno"].add(sol["tab_res"], text=" 3 · Resultados ")

    construir_pestana_matriz(sol["tab_matriz"])
    construir_pestana_pasos(sol["tab_pasos"])
    construir_pestana_resultados(sol["tab_res"])

    derecha = tk.Frame(marco, bg=FONDO_TARJETA, highlightthickness=2,
                       highlightbackground=BORDE)
    derecha.grid(row=0, column=1, sticky="nsew", padx=(9, 18), pady=18)
    tk.Frame(derecha, bg=VERDE_AZULADO, height=5).pack(fill="x")
    leyenda = tk.Frame(derecha, bg=FONDO_TARJETA)
    leyenda.pack(side="bottom", fill="x", padx=12, pady=(0, 10))
    elementos = (("■ Ruta válida / óptima", EXITO),
                 ("■ Arista de ruta descartada", AMBAR),
                 ("┄ Arista faltante", ERROR),
                 ("● Nodo inicial", MORADO))
    for texto, color in elementos:
        tk.Label(leyenda, text=texto, bg=FONDO_TARJETA, fg=color,
                 font=(FUENTE, 10, "bold")).pack(side="left", padx=8)
    sol["lienzo"] = crear_lienzo(derecha)
    sol["lienzo"]["marco"].pack(fill="both", expand=True, padx=8, pady=8)
    return marco


# Función que reinicia la fuerza bruta solo si el grafo cambió desde la última vez
def al_mostrar_solucion():
    if sol["cargado"] is not estado["grafo"]:
        reiniciar_solucion()


# Función para reiniciar la fuerza bruta: arma la matriz y deja todo en cero
def reiniciar_solucion():
    G = estado["grafo"]
    if G is None:
        return
    n, unidad, _, _ = estado["params"]
    sol["simbolo"] = UNIDADES[unidad][0]
    sol["motor"] = crear_motor(etiquetas_nodos(n), G)
    sol["df_resultados"] = None
    sol["ciclos"] = []

    sol["df_costos"] = construir_matriz_costos(G)
    llenar_matriz(sol["matriz"], sol["df_costos"])
    sol["lbl_total"].config(
        text=f"Rutas posibles a evaluar: (n − 1)! / 2 = {sol['motor']['total']:,}  "
             f"(el nodo {sol['motor']['etiquetas'][0]} es el inicio y cada ciclo se "
             f"cuenta una sola vez, sin su inverso).")

    sol["log"].delete(*sol["log"].get_children())
    sol["res_tabla"].delete(*sol["res_tabla"].get_children())
    sol["res_cuerpo"].pack_forget()
    sol["res_placeholder"].pack(expand=True)

    sol["s_eval"].config(text=f"0 / {sol['motor']['total']:,}")
    sol["s_validas"].config(text="0")
    sol["s_mejor"].config(text="—")
    sol["lbl_ruta"].config(text="—")
    sol["lbl_estado"].config(text="Pulsa «Siguiente ruta» para comenzar.", fg=APAGADO)
    sol["lbl_calculo"].config(text="")

    sol["cuaderno"].select(sol["tab_matriz"])
    dibujar_grafo(sol["lienzo"], G, estado["pos"],
                  f"Grafo ponderado  ·  {n} nodos  ·  pesos en {sol['simbolo']}")
    sol["cargado"] = G


# Función para ejecutar la fuerza bruta completa de una sola vez
def ejecutar_todo():
    avanzar_paso(None, False)


# Función para avanzar la fuerza bruta: una ruta, hasta la siguiente válida, 100 rutas o todas
def avanzar_paso(max_pasos=None, hasta_valida=False):
    motor = sol["motor"]
    if motor is None:
        return
    if motor["terminado"]:
        sol["cuaderno"].select(sol["tab_res"])
        return
    completo = max_pasos is None and not hasta_valida
    raiz = estado["raiz"]
    if completo:
        raiz.config(cursor="watch")
        raiz.update_idletasks()
    recientes, _ = avanzar(motor, max_pasos, hasta_valida)
    if completo:
        raiz.config(cursor="")
    if recientes:
        actualizar_tras_avance(recientes, not motor["terminado"])
    if motor["terminado"]:
        finalizar_busqueda()
    elif not completo:
        sol["cuaderno"].select(sol["tab_pasos"])


# Función para actualizar el registro, los contadores, la matriz y el grafo tras evaluar rutas
def actualizar_tras_avance(recientes, dibujar=True):
    motor = sol["motor"]
    simbolo = sol["simbolo"]
    log = sol["log"]
    for indice, ruta, costo in recientes:
        valida = costo is not None
        log.insert("", 0, values=(
            f"{indice:,}", texto_ruta(ruta),
            "✔ Válida" if valida else "✘ Descartada",
            formato_valor(costo, simbolo) if valida else "—"),
            tags=("valid" if valida else "invalid",))
    for iid in log.get_children()[MAX_REGISTRO:]:
        log.delete(iid)

    sol["s_eval"].config(text=f"{motor['evaluadas']:,} / {motor['total']:,}")
    sol["s_validas"].config(text=f"{len(motor['ciclos']):,}")
    if motor["mejor_costo"] is not None:
        sol["s_mejor"].config(text=formato_valor(motor["mejor_costo"], simbolo))
    else:
        sol["s_mejor"].config(text="—")

    indice, ruta, costo = recientes[-1]
    aristas, pesos, faltantes = detalle_ruta(motor, ruta)
    sol["lbl_ruta"].config(text=texto_ruta(ruta))

    if costo is not None:
        es_mejor = ruta == motor["mejor_ruta"]
        mensaje = "✔ VÁLIDA · es un ciclo hamiltoniano"
        if es_mejor:
            mensaje += "  ·  ¡nuevo mejor costo!"
        sol["lbl_estado"].config(text=mensaje, fg=EXITO)
        sol["lbl_calculo"].config(
            text="Costo = " + " + ".join(map(str, pesos)) +
                 f" = {formato_valor(costo, simbolo)}")
        grupos = [(aristas, VERDE_OSCURO)]
        argumentos = dict(ciclo=aristas, color_ciclo=EXITO)
        titulo = f"Ruta #{indice:,} · VÁLIDA · costo {formato_valor(costo, simbolo)}"
    else:
        lista = ", ".join(f"{a}–{b}" for a, b in faltantes)
        sol["lbl_estado"].config(
            text=f"✘ DESCARTADA · no existe(n) la(s) arista(s): {lista}", fg=ERROR)
        sol["lbl_calculo"].config(
            text="No se calcula el costo porque la ruta no es un ciclo.")
        existentes = [e for e in aristas if e not in faltantes]
        grupos = [(existentes, AMBAR_OSCURO), (faltantes, ROJO_OSCURO)]
        argumentos = dict(ciclo=existentes, color_ciclo=AMBAR, faltantes=faltantes)
        titulo = f"Ruta #{indice:,} · DESCARTADA"

    resaltar_matriz(sol["matriz"], grupos)
    if dibujar:
        dibujar_grafo(sol["lienzo"], estado["grafo"], estado["pos"], titulo,
                      inicio=ruta[0], **argumentos)


# Función para mostrar los resultados cuando ya se evaluaron todas las rutas
def finalizar_busqueda():
    motor = sol["motor"]
    ciclos = ciclos_ordenados(motor)
    if not ciclos:
        mostrar_alerta("Sin ciclos hamiltonianos",
                       "No se encontró ningún ciclo hamiltoniano en este grafo.",
                       "warning")
        return
    sol["ciclos"] = ciclos
    simbolo = sol["simbolo"]
    mejor = ciclos[0][1]
    empates = sum(1 for _, costo in ciclos if costo == mejor)

    sol["df_resultados"] = pd.DataFrame({
        "N°": range(1, len(ciclos) + 1),
        "Ciclo hamiltoniano": [texto_ruta(r) for r, _ in ciclos],
        f"Costo total ({simbolo})": [c for _, c in ciclos],
    })

    sol["r_ciclos"].config(text=f"{len(ciclos):,}")
    sol["r_eval"].config(text=f"{motor['evaluadas']:,}")
    sol["r_mejor"].config(text=formato_valor(mejor, simbolo))
    sol["r_ruta"].config(text=texto_ruta(ciclos[0][0]))
    if empates > 1:
        sol["r_empates"].config(
            text=f"Hay {empates} ciclos empatados con el costo mínimo; "
                 f"se muestra el primero.")
    else:
        sol["r_empates"].config(text="")

    tabla = sol["res_tabla"]
    tabla.heading("costo", text=f"Costo total ({simbolo})")
    tabla.delete(*tabla.get_children())
    for i, (ruta, costo) in enumerate(ciclos[:MAX_FILAS]):
        tabla.insert("", "end", iid=str(i),
                     values=(i + 1, texto_ruta(ruta), formato_valor(costo, simbolo)),
                     tags=("best",) if costo == mejor else ())
    nota = "Ordenados de menor a mayor costo. Selecciona una fila para verla en el grafo."
    if len(ciclos) > MAX_FILAS:
        nota += (f" Se muestran los {MAX_FILAS:,} mejores; el Excel incluye "
                 f"los {len(ciclos):,}.")
    sol["r_nota"].config(text=nota)

    sol["res_placeholder"].pack_forget()
    sol["res_cuerpo"].pack(fill="both", expand=True)
    sol["cuaderno"].select(sol["tab_res"])
    mostrar_ciclo(0)


# Función para mostrar en el grafo y en la matriz el ciclo elegido de la tabla de resultados
def mostrar_ciclo(i):
    if not sol["ciclos"]:
        return
    ruta, costo = sol["ciclos"][i]
    mejor = sol["ciclos"][0][1]
    aristas = aristas_ruta(ruta)
    valor = formato_valor(costo, sol["simbolo"])
    if costo == mejor:
        titulo = f"★ Ciclo óptimo · costo {valor}"
    else:
        titulo = f"Ciclo #{i + 1} · costo {valor}"
    resaltar_matriz(sol["matriz"], [(aristas, VERDE_OSCURO)])
    dibujar_grafo(sol["lienzo"], estado["grafo"], estado["pos"], titulo,
                  ciclo=aristas, color_ciclo=EXITO, inicio=ruta[0])
    tabla = sol["res_tabla"]
    if tabla.exists(str(i)) and tabla.selection() != (str(i),):
        sol["sincronizando"] = True
        tabla.selection_set(str(i))
        tabla.see(str(i))
        sol["sincronizando"] = False


# Función que se ejecuta al elegir una fila de la tabla de resultados
def al_seleccionar(evento):
    if sol["sincronizando"]:
        return
    seleccion = sol["res_tabla"].selection()
    if seleccion and sol["ciclos"]:
        mostrar_ciclo(int(seleccion[0]))


# Función para exportar el resumen, la matriz de costos y los ciclos a un archivo de Excel
def exportar_excel():
    if sol["df_resultados"] is None:
        return
    ruta_archivo = filedialog.asksaveasfilename(
        parent=estado["raiz"], title="Guardar resultados en Excel",
        defaultextension=".xlsx", initialfile="ciclos_hamiltonianos.xlsx",
        filetypes=[("Excel", "*.xlsx")])
    if not ruta_archivo:
        return

    n, unidad, _, _ = estado["params"]
    simbolo = sol["simbolo"]
    ciclos = sol["ciclos"]
    mejor_ruta, mejor_costo = ciclos[0]
    empates = sum(1 for _, costo in ciclos if costo == mejor_costo)
    resumen = pd.DataFrame({
        "Concepto": ["Cantidad de nodos", "Tipo de valor", "Aristas del grafo",
                     "Rutas evaluadas", "Ciclos hamiltonianos encontrados",
                     "Costo óptimo", "Ciclo óptimo", "Ciclos con el costo óptimo"],
        "Valor": [n, unidad, estado["grafo"].number_of_edges(),
                  sol["motor"]["evaluadas"], len(ciclos),
                  formato_valor(mejor_costo, simbolo), texto_ruta(mejor_ruta), empates],
    })

    raiz = estado["raiz"]
    raiz.config(cursor="watch")
    raiz.update_idletasks()
    try:
        with pd.ExcelWriter(ruta_archivo, engine="openpyxl") as escritor:
            resumen.to_excel(escritor, sheet_name="Resumen", index=False)
            sol["df_costos"].to_excel(escritor, sheet_name="Matriz de costos",
                                      index_label="Nodo", inf_rep="∞")
            sol["df_resultados"].to_excel(escritor, sheet_name="Ciclos hamiltonianos",
                                          index=False)
            ajustar_columnas(escritor)
    except ImportError:
        mostrar_alerta("Falta una librería",
                       "Para crear archivos Excel hay que instalar openpyxl. "
                       "Ejecuta en la terminal: pip install openpyxl", "error")
        return
    except OSError as error:
        mostrar_alerta("No se pudo guardar", f"Ocurrió un error al guardar: {error}",
                       "error")
        return
    finally:
        raiz.config(cursor="")
    mostrar_alerta("Archivo guardado",
                   f"Se exportaron {len(ciclos):,} ciclos a:\n{ruta_archivo}\n"
                   f"Incluye las hojas: Resumen, Matriz de costos y Ciclos hamiltonianos.",
                   "success")


# Función para definir los colores y estilos oscuros de tablas, pestañas y listas
def configurar_estilos(raiz):
    estilo = ttk.Style(raiz)
    estilo.theme_use("clam")
    raiz.option_add("*TCombobox*Listbox.background", FONDO_ENTRADA)
    raiz.option_add("*TCombobox*Listbox.foreground", TEXTO)
    raiz.option_add("*TCombobox*Listbox.selectBackground", ACENTO)
    raiz.option_add("*TCombobox*Listbox.selectForeground", "white")
    raiz.option_add("*TCombobox*Listbox.font", (FUENTE, 12))

    for nombre, borde in (("Dark.TCombobox", BORDE), ("Err.TCombobox", ERROR)):
        estilo.configure(nombre, fieldbackground=FONDO_ENTRADA, background=BORDE,
                         foreground=TEXTO, arrowcolor=TEXTO, bordercolor=borde,
                         lightcolor=borde, darkcolor=borde,
                         selectbackground=FONDO_ENTRADA, selectforeground=TEXTO,
                         padding=6)
        estilo.map(nombre, fieldbackground=[("readonly", FONDO_ENTRADA)],
                   foreground=[("readonly", TEXTO)],
                   background=[("active", ACENTO)])

    estilo.configure("Dark.Treeview", background=FONDO_ENTRADA,
                     fieldbackground=FONDO_ENTRADA, foreground=TEXTO, rowheight=26,
                     borderwidth=0, font=(FUENTE, 10))
    estilo.configure("Dark.Treeview.Heading", background=BORDE, foreground=TEXTO,
                     font=(FUENTE, 10, "bold"), relief="flat", padding=5)
    estilo.map("Dark.Treeview", background=[("selected", ACENTO)],
               foreground=[("selected", "white")])
    estilo.map("Dark.Treeview.Heading", background=[("active", "#38405c")])
    estilo.configure("Dark.Vertical.TScrollbar", background=BORDE,
                     troughcolor=FONDO_ENTRADA, bordercolor=FONDO_ENTRADA,
                     arrowcolor=TEXTO, lightcolor=BORDE, darkcolor=BORDE)

    estilo.configure("Dark.TNotebook", background=FONDO_TARJETA, borderwidth=0,
                     tabmargins=(0, 0, 0, 6))
    estilo.configure("Dark.TNotebook.Tab", background=BORDE, foreground=APAGADO,
                     padding=(12, 8), font=(FUENTE, 10, "bold"), borderwidth=0)
    estilo.map("Dark.TNotebook.Tab",
               background=[("selected", MORADO), ("active", "#38405c")],
               foreground=[("selected", "white"), ("active", TEXTO)])


# Función para construir la barra superior con el título y el botón Regresar
def construir_encabezado(raiz):
    encabezado = tk.Frame(raiz, bg=FONDO_ENCABEZADO, height=72)
    encabezado.pack(fill="x")
    encabezado.pack_propagate(False)

    espacio = tk.Frame(encabezado, bg=FONDO_ENCABEZADO, width=170)
    espacio.pack(side="left", fill="y", padx=(16, 0))
    espacio.pack_propagate(False)
    estado["boton_atras"] = crear_boton(espacio, "←  Regresar", retroceder,
                                        fondo=BORDE, hover="#3a4262", tam=11,
                                        padx=16, pady=8)

    titulos = tk.Frame(encabezado, bg=FONDO_ENCABEZADO)
    titulos.pack(side="left", fill="y", padx=10)
    tk.Label(titulos, text="Problema del Agente Viajero", bg=FONDO_ENCABEZADO,
             fg=TEXTO, font=(FUENTE, 17, "bold")).pack(anchor="w", pady=(12, 0))
    estado["subtitulo"] = tk.Label(titulos, text="", bg=FONDO_ENCABEZADO, fg=APAGADO,
                                   font=(FUENTE, 10))
    estado["subtitulo"].pack(anchor="w")

    tk.Frame(raiz, bg=ACENTO, height=2).pack(fill="x")


# Función para ir a una pantalla y anotarla en el historial de navegación
def navegar(nombre):
    pila = estado["pila"]
    if pila and pila[-1] == nombre:
        return
    pila.append(nombre)
    mostrar_pantalla(nombre)


# Función para volver a la pantalla anterior del historial
def retroceder():
    pila = estado["pila"]
    if len(pila) > 1:
        pila.pop()
        mostrar_pantalla(pila[-1])


# Función para mostrar una pantalla, actualizar el subtítulo y el botón Regresar
def mostrar_pantalla(nombre):
    estado["pantallas"][nombre].tkraise()
    estado["subtitulo"].config(text=TITULOS[nombre])
    if len(estado["pila"]) > 1:
        estado["boton_atras"].pack(expand=True, anchor="w")
    else:
        estado["boton_atras"].pack_forget()
    if nombre == "auto":
        al_mostrar_auto()
    elif nombre == "archivo":
        al_mostrar_archivo()
    elif nombre == "manual":
        al_mostrar_manual()
    elif nombre == "result":
        cargar_resultado()
    elif nombre == "solve":
        al_mostrar_solucion()


# Función para guardar en el estado el grafo y sus datos para usarlos en las demás pantallas
def guardar_grafo(G, params, origen):
    estado["grafo"] = G
    estado["pos"] = nx.circular_layout(G)
    estado["aristas_df"] = grafo_a_dataframe(G)
    estado["params"] = params
    estado["origen"] = origen


# Función para generar el grafo automático, guardarlo y mostrar la pantalla de resultado
def construir_grafo(n, unidad, peso_min, peso_max, ir_a_resultado=True):
    G = generar_grafo_aleatorio(n, peso_min, peso_max)
    guardar_grafo(G, (n, unidad, peso_min, peso_max), "auto")
    if ir_a_resultado:
        navegar("result")


# Función principal: crea la ventana, construye las pantallas e inicia el programa
def main():
    raiz = tk.Tk()
    estado["raiz"] = raiz
    raiz.title("Problema del Agente Viajero")
    raiz.configure(bg=FONDO)
    raiz.minsize(1040, 680)
    ancho = min(1260, raiz.winfo_screenwidth() - 40)
    alto = min(780, raiz.winfo_screenheight() - 80)
    x = (raiz.winfo_screenwidth() - ancho) // 2
    y = max((raiz.winfo_screenheight() - alto) // 2 - 20, 0)
    raiz.geometry(f"{ancho}x{alto}+{x}+{y}")

    configurar_estilos(raiz)
    construir_encabezado(raiz)

    contenedor = tk.Frame(raiz, bg=FONDO)
    contenedor.pack(fill="both", expand=True)
    contenedor.grid_rowconfigure(0, weight=1)
    contenedor.grid_columnconfigure(0, weight=1)

    constructores = (("home", construir_inicio), ("auto", construir_auto),
                     ("manual", construir_manual), ("matriz", construir_pantalla_matriz),
                     ("archivo", construir_archivo),
                     ("result", construir_resultado), ("solve", construir_solucion))
    for nombre, constructor in constructores:
        marco = constructor(contenedor)
        marco.grid(row=0, column=0, sticky="nsew")
        estado["pantallas"][nombre] = marco

    navegar("home")
    raiz.bind("<Escape>", lambda e: retroceder())
    raiz.mainloop()


if __name__ == "__main__":
    main()

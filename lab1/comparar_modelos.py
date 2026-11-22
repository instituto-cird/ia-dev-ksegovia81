"""
lab1/comparar_modelos.py · Lab 1 de M1 (cohorte 2026-II).

Corre la misma tarea de LegacyPay (clasificar reclamos de clientes) con
varios modelos y registra, para cada uno: aciertos, respuestas inválidas,
tokens, tiempo y costo estimado. También corre una «cascada»: un modelo
primero y el segundo solo cuando el chequeo automático no pasa.

Uso (desde la raíz del repositorio):
    uv run --frozen python lab1/comparar_modelos.py --listar
    uv run --frozen python lab1/comparar_modelos.py nube-chico --pausa 3.5
    uv run --frozen python lab1/comparar_modelos.py nube-grande --pausa 3.5
    uv run --frozen python lab1/comparar_modelos.py cascada --pausa 3.5
    uv run --frozen python lab1/comparar_modelos.py cascada --limite 5   # solo 5 reclamos
    uv run --frozen python lab1/comparar_modelos.py cascada --desde-resultados  # sin gastar pedidos
    uv run --frozen python lab1/comparar_modelos.py --resumen

Cada corrida guarda el detalle en lab1/resultados/<nombre>.csv y el resumen
de todas las corridas en lab1/resultados/resumen.md y grafico.svg.

Cualquier servidor compatible con la API de OpenAI sirve (Ollama, OpenRouter,
LM Studio). Las claves se leen de variables de entorno, nunca del código.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

CARPETA = Path(__file__).resolve().parent
RESULTADOS = CARPETA / "resultados"
CATEGORIAS = (
    "cobro_duplicado",
    "reembolso_pendiente",
    "sospecha_fraude",
    "consulta",
    "error_tecnico",
)

INSTRUCCION = (
    "Eres un clasificador de reclamos de LegacyPay, una empresa de pagos. "
    "Responde SOLO con un objeto JSON, sin texto adicional, con esta forma: "
    '{"categoria": "<una de: ' + ", ".join(CATEGORIAS) + '>", '
    '"confianza": "<alta o baja>"}. '
    'Usa "baja" si el reclamo podría pertenecer a más de una categoría.'
)


@dataclass
class Respuesta:
    categoria: str | None
    confianza: str | None
    tokens_entrada: int
    tokens_salida: int
    segundos: float
    texto: str


def leer_reclamos(ruta: Path = CARPETA / "reclamos.csv") -> list[dict[str, str]]:
    with ruta.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def leer_config(ruta: Path = CARPETA / "modelos.toml") -> dict[str, Any]:
    with ruta.open("rb") as f:
        return tomllib.load(f)


def interpretar(texto: str) -> tuple[str | None, str | None]:
    """Extrae categoría y confianza de la respuesta del modelo.

    Devuelve (None, None) si la respuesta no tiene el formato pedido o si la
    categoría no es una de las permitidas: eso cuenta como respuesta inválida.
    """
    # Algunos modelos «piensan» antes de responder: se descarta ese bloque.
    texto = re.sub(r"<think>.*?</think>", "", texto, flags=re.DOTALL)
    hallado = re.search(r"\{.*?\}", texto, flags=re.DOTALL)
    if not hallado:
        return None, None
    try:
        datos = json.loads(hallado.group(0))
    except json.JSONDecodeError:
        return None, None
    categoria = str(datos.get("categoria", "")).strip().lower()
    confianza = str(datos.get("confianza", "")).strip().lower() or None
    if categoria not in CATEGORIAS:
        return None, confianza
    return categoria, confianza


def chequeo_pasa(r: Respuesta) -> bool:
    """Chequeo automático que NO conoce la respuesta correcta.

    Pasa si el formato es válido y el modelo declaró confianza alta. Es un
    chequeo débil (la confianza es autodeclarada): parte de lo que se discute
    en el Lab 1.
    """
    return r.categoria is not None and r.confianza == "alta"


REINTENTOS_429 = 4


def _motivo(resp: httpx.Response) -> str:
    """Mensaje de error del proveedor, sin datos de la clave."""
    try:
        error = resp.json().get("error", {})
        motivo = error.get("message", "")
        detalle = (error.get("metadata") or {}).get("raw", "")
        return f"{motivo} {detalle}".strip()[:300] or resp.reason_phrase
    except (ValueError, AttributeError):
        return resp.reason_phrase


def _espera_429(resp: httpx.Response, intento: int) -> float:
    """Usa Retry-After si el proveedor lo envía; si no, 10, 20, 40 y 80 s."""
    try:
        return min(float(resp.headers.get("retry-after", "")), 120.0)
    except ValueError:
        return 10.0 * 2 ** (intento - 1)


def preguntar(
    cliente: httpx.Client, cfg: dict[str, Any], reclamo: str
) -> Respuesta:
    clave = os.environ.get(cfg.get("api_key_env") or "", "")
    encabezados = {"Authorization": f"Bearer {clave}"} if clave else {}
    cuerpo = {
        "model": cfg["modelo"],
        "temperature": 0,
        "messages": [
            {"role": "system", "content": INSTRUCCION},
            {"role": "user", "content": reclamo},
        ],
    }
    url = cfg["base_url"].rstrip("/") + "/chat/completions"
    inicio = time.perf_counter()
    resp = cliente.post(url, json=cuerpo, headers=encabezados)
    # 429 = demasiados pedidos. Se espera y se reintenta, hasta 4 veces.
    for intento in range(1, REINTENTOS_429 + 1):
        if resp.status_code != 429:
            break
        espera = _espera_429(resp, intento)
        print(f"    429 ({_motivo(resp)}); reintento {intento} en {espera:.0f} s", file=sys.stderr)
        time.sleep(espera)
        resp = cliente.post(url, json=cuerpo, headers=encabezados)
    segundos = time.perf_counter() - inicio
    if resp.is_error:
        sys.exit(f"Error {resp.status_code} de {cfg['modelo']}: {_motivo(resp)}")
    datos = resp.json()
    texto = datos["choices"][0]["message"].get("content") or ""
    uso = datos.get("usage") or {}
    categoria, confianza = interpretar(texto)
    return Respuesta(
        categoria,
        confianza,
        int(uso.get("prompt_tokens", 0)),
        int(uso.get("completion_tokens", 0)),
        segundos,
        texto,
    )


def costo(cfg: dict[str, Any], entrada: int, salida: int) -> float:
    return (
        entrada * float(cfg.get("precio_entrada", 0))
        + salida * float(cfg.get("precio_salida", 0))
    ) / 1_000_000


def correr(
    nombre: str,
    config: dict[str, Any],
    reclamos: list[dict[str, str]],
    cliente: httpx.Client,
    pausa: float = 0.0,
) -> list[dict[str, Any]]:
    modelos = {m["nombre"]: m for m in config.get("modelo", [])}
    cascadas = {c["nombre"]: c for c in config.get("cascada", [])}
    filas = []
    for r in reclamos:
        if nombre in cascadas:
            pasos = [modelos[cascadas[nombre]["primero"]], modelos[cascadas[nombre]["si_falla"]]]
        else:
            pasos = [modelos[nombre]]
        usado, respuesta, gasto, tok_in, tok_out, seg = "", None, 0.0, 0, 0, 0.0
        for paso in pasos:
            respuesta = preguntar(cliente, paso, r["texto"])
            usado = paso["nombre"]
            gasto += costo(paso, respuesta.tokens_entrada, respuesta.tokens_salida)
            tok_in += respuesta.tokens_entrada
            tok_out += respuesta.tokens_salida
            seg += respuesta.segundos
            if pausa:
                time.sleep(pausa)
            if chequeo_pasa(respuesta):
                break
        assert respuesta is not None
        filas.append(
            {
                "id": r["id"],
                "esperada": r["categoria_esperada"],
                "obtenida": respuesta.categoria or "INVALIDA",
                "confianza": respuesta.confianza or "",
                "acierto": int(respuesta.categoria == r["categoria_esperada"]),
                "modelo_final": usado,
                "tokens_entrada": tok_in,
                "tokens_salida": tok_out,
                "segundos": round(seg, 2),
                "costo_usd": round(gasto, 6),
            }
        )
        print(f"{r['id']}: {filas[-1]['obtenida']:<20} esperada {r['categoria_esperada']}")
    return filas


def cascada_desde_resultados(
    nombre: str, config: dict[str, Any], sufijo: str = ""
) -> list[dict[str, Any]]:
    """Arma una cascada con las corridas ya guardadas, sin llamar a ningún modelo.

    Para cada reclamo toma la respuesta del primer modelo si pasa el chequeo;
    si no, la del segundo, y suma los tokens, el tiempo y el costo de los dos
    (en una cascada real se pagan las dos llamadas). Supone que cada modelo
    respondería igual que en su corrida: como los modelos no son
    deterministas, una cascada corrida de verdad puede variar un poco.
    """
    cascadas = {c["nombre"]: c for c in config.get("cascada", [])}
    if nombre not in cascadas:
        sys.exit(f"«{nombre}» no es una cascada de modelos.toml (ver --listar)")
    cascada = cascadas[nombre]

    def leer(modelo: str) -> dict[str, dict[str, str]]:
        ruta = RESULTADOS / f"{modelo}{sufijo}.csv"
        if not ruta.exists():
            sys.exit(f"Falta {ruta.name}: primero hay que correr «{modelo}» con los mismos reclamos")
        with ruta.open(encoding="utf-8") as f:
            return {fila["id"]: fila for fila in csv.DictReader(f)}

    primero, segundo = leer(cascada["primero"]), leer(cascada["si_falla"])
    filas = []
    for id_, a in primero.items():
        if a["obtenida"] != "INVALIDA" and a["confianza"] == "alta":
            fila: dict[str, Any] = dict(a, modelo_final=cascada["primero"])
        else:
            if id_ not in segundo:
                sys.exit(f"Falta el reclamo {id_} en la corrida de «{cascada['si_falla']}»")
            b = segundo[id_]
            fila = {
                "id": id_,
                "esperada": a["esperada"],
                "obtenida": b["obtenida"],
                "confianza": b["confianza"],
                "acierto": int(b["acierto"]),
                "modelo_final": cascada["si_falla"],
                "tokens_entrada": int(a["tokens_entrada"]) + int(b["tokens_entrada"]),
                "tokens_salida": int(a["tokens_salida"]) + int(b["tokens_salida"]),
                "segundos": round(float(a["segundos"]) + float(b["segundos"]), 2),
                "costo_usd": round(float(a["costo_usd"]) + float(b["costo_usd"]), 6),
            }
        filas.append(fila)
        print(f"{id_}: {fila['obtenida']:<20} esperada {fila['esperada']} ({fila['modelo_final']})")
    return filas


def guardar(nombre: str, filas: list[dict[str, Any]]) -> Path:
    RESULTADOS.mkdir(exist_ok=True)
    ruta = RESULTADOS / f"{nombre}.csv"
    with ruta.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)
    return ruta


def resumir(filas: list[dict[str, Any]]) -> dict[str, float]:
    n = len(filas)
    return {
        "aciertos": sum(int(f["acierto"]) for f in filas),
        "total": n,
        "invalidas": sum(f["obtenida"] == "INVALIDA" for f in filas),
        "tokens": sum(int(f["tokens_entrada"]) + int(f["tokens_salida"]) for f in filas),
        "segundos": round(sum(float(f["segundos"]) for f in filas), 1),
        "costo_usd": round(sum(float(f["costo_usd"]) for f in filas), 6),
    }


def _escala(maximo: float) -> float:
    """Redondea hacia arriba a un valor «limpio» para el eje (1, 2 o 5 × 10^n)."""
    if maximo <= 0:
        return 1.0
    potencia = 10 ** (len(str(int(maximo))) - 1)
    for paso in (1, 2, 5, 10):
        if paso * potencia >= maximo:
            return float(paso * potencia)
    return float(10 * potencia)


def grafico_svg(resumenes: dict[str, dict[str, float]]) -> str:
    """Aciertos (%) contra gasto (tokens), sin dependencias externas.

    Cada punto lleva un número; la leyenda de abajo dice qué configuración
    es y sus valores. Así las etiquetas no se pisan aunque los puntos
    queden juntos (por ejemplo, todos con 100 % de aciertos).
    """
    izq, der, arr = 70, 30, 64
    ancho, alto_graf = 640, 260
    abajo = arr + alto_graf
    n = len(resumenes)
    alto = abajo + 60 + 20 * n
    max_x = _escala(max((r["tokens"] for r in resumenes.values()), default=1) * 1.1)

    def px(tokens: float) -> float:
        return izq + tokens / max_x * (ancho - izq - der)

    def py(porcentaje: float) -> float:
        return abajo - porcentaje / 100 * alto_graf

    gris, azul = "#c9ced6", "#065A82"
    partes = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{ancho}" height="{alto}" '
        'font-family="sans-serif" font-size="12">',
        f'<rect width="{ancho}" height="{alto}" fill="#ffffff"/>',
        f'<text x="{izq}" y="22" font-size="14" font-weight="bold">'
        "Aciertos contra gasto · arriba y a la izquierda es mejor</text>",
    ]
    for pct in (0, 25, 50, 75, 100):
        y = py(pct)
        partes.append(f'<line x1="{izq}" y1="{y:.0f}" x2="{ancho - der}" y2="{y:.0f}" stroke="{gris}" stroke-width="0.5"/>')
        partes.append(f'<text x="{izq - 8}" y="{y + 4:.0f}" text-anchor="end">{pct} %</text>')
    for k in range(5):
        valor = max_x * k / 4
        x = px(valor)
        partes.append(f'<line x1="{x:.0f}" y1="{abajo}" x2="{x:.0f}" y2="{abajo + 5}" stroke="#333"/>')
        partes.append(f'<text x="{x:.0f}" y="{abajo + 18}" text-anchor="middle">{valor:,.0f}</text>'.replace(",", "."))
    partes += [
        f'<line x1="{izq}" y1="{abajo}" x2="{ancho - der}" y2="{abajo}" stroke="#333"/>',
        f'<line x1="{izq}" y1="{arr}" x2="{izq}" y2="{abajo}" stroke="#333"/>',
        f'<text x="{(izq + ancho - der) / 2}" y="{abajo + 38}" text-anchor="middle">Gasto (tokens totales)</text>',
        f'<text x="16" y="{arr + alto_graf / 2}" transform="rotate(-90 16 {arr + alto_graf / 2})" '
        'text-anchor="middle">Aciertos (%)</text>',
    ]
    ubicadas: list[tuple[float, float]] = []
    for numero, (nombre, r) in enumerate(resumenes.items(), start=1):
        pct = 100 * r["aciertos"] / r["total"] if r["total"] else 0
        x, y = px(r["tokens"]), py(pct)
        # Si hay otro número cerca, este sube un renglón.
        ly = y - 10
        while any(abs(x - ux) < 22 and abs(ly - uy) < 13 for ux, uy in ubicadas):
            ly -= 13
        ubicadas.append((x, ly))
        partes.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="5" fill="{azul}"/>')
        partes.append(f'<text x="{x:.0f}" y="{ly:.0f}" text-anchor="middle" font-weight="bold">{numero}</text>')
        tokens = f"{r['tokens']:,.0f}".replace(",", ".")
        partes.append(
            f'<text x="{izq}" y="{abajo + 64 + 20 * (numero - 1)}">'
            f"<tspan font-weight=\"bold\">{numero}</tspan>  {nombre}: "
            f"{r['aciertos']}/{r['total']} aciertos · {tokens} tokens</text>"
        )
    partes.append("</svg>")
    return "\n".join(partes)


def escribir_resumen() -> None:
    resumenes = {}
    for ruta in sorted(RESULTADOS.glob("*.csv")):
        with ruta.open(encoding="utf-8") as f:
            resumenes[ruta.stem] = resumir(list(csv.DictReader(f)))
    if not resumenes:
        sys.exit("No hay resultados todavía: correr primero alguna configuración.")
    lineas = [
        "| Configuración | Aciertos | Inválidas | Tokens | Segundos | Costo estimado (USD) |",
        "|---|---|---|---|---|---|",
    ]
    for nombre, r in resumenes.items():
        lineas.append(
            f"| {nombre} | {r['aciertos']}/{r['total']} | {r['invalidas']} | "
            f"{r['tokens']} | {r['segundos']} | {r['costo_usd']} |"
        )
    (RESULTADOS / "resumen.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    (RESULTADOS / "grafico.svg").write_text(grafico_svg(resumenes), encoding="utf-8")
    print("\n".join(lineas))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("nombre", nargs="?", help="configuración o cascada de modelos.toml")
    p.add_argument("--pausa", type=float, default=0.0, help="segundos entre llamadas (OpenRouter gratis: 20 por minuto)")
    p.add_argument("--listar", action="store_true", help="muestra las configuraciones disponibles")
    p.add_argument("--resumen", action="store_true", help="tabla y gráfico con todas las corridas")
    p.add_argument("--limite", type=int, default=0, help="usa solo los primeros N reclamos (para ensayar sin gastar pedidos)")
    p.add_argument(
        "--desde-resultados", action="store_true",
        help="arma la cascada con las corridas ya guardadas de sus dos modelos, sin gastar pedidos",
    )
    args = p.parse_args()
    config = leer_config()
    if args.listar:
        for m in config.get("modelo", []):
            print(f"{m['nombre']}: {m['modelo']} en {m['base_url']}")
        for c in config.get("cascada", []):
            print(f"{c['nombre']}: {c['primero']} y, si el chequeo no pasa, {c['si_falla']}")
        return
    if args.resumen:
        escribir_resumen()
        return
    if not args.nombre:
        p.error("falta el nombre de la configuración (ver --listar)")
    if args.desde_resultados:
        sufijo = f"-{args.limite}" if args.limite > 0 else ""
        filas = cascada_desde_resultados(args.nombre, config, sufijo)
        print(f"Guardado en {guardar(f'{args.nombre}-armada{sufijo}', filas)}")
        escribir_resumen()
        return
    with httpx.Client(timeout=120) as cliente:
        reclamos = leer_reclamos()
        if args.limite > 0:
            reclamos = reclamos[: args.limite]
        filas = correr(args.nombre, config, reclamos, cliente, args.pausa)
    # Con --limite, se guarda aparte para no pisar la corrida completa.
    salida = f"{args.nombre}-{args.limite}" if args.limite > 0 else args.nombre
    print(f"Guardado en {guardar(salida, filas)}")
    escribir_resumen()


if __name__ == "__main__":
    main()

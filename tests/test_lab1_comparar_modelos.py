"""Pruebas del script del Lab 1 sin red: un servidor falso responde."""

from __future__ import annotations

import json

import httpx

from lab1 import comparar_modelos as cm

CONFIG = {
    "modelo": [
        {"nombre": "chico", "base_url": "http://falso/v1", "modelo": "c",
         "api_key_env": "", "precio_entrada": 0.0, "precio_salida": 0.0},
        {"nombre": "grande", "base_url": "http://falso/v1", "modelo": "g",
         "api_key_env": "", "precio_entrada": 1.0, "precio_salida": 2.0},
    ],
    "cascada": [{"nombre": "cascada", "primero": "chico", "si_falla": "grande"}],
}
RECLAMOS = [
    {"id": "A", "texto": "me cobraron dos veces", "categoria_esperada": "cobro_duplicado"},
    {"id": "B", "texto": "no sé qué pasó", "categoria_esperada": "consulta"},
]


def servidor(peticion: httpx.Request) -> httpx.Response:
    cuerpo = json.loads(peticion.content)
    texto = cuerpo["messages"][-1]["content"]
    if cuerpo["model"] == "c" and "dos veces" in texto:
        contenido = '{"categoria": "cobro_duplicado", "confianza": "alta"}'
    elif cuerpo["model"] == "c":
        contenido = "No estoy seguro."  # formato inválido
    else:
        contenido = '<think>...</think>{"categoria": "consulta", "confianza": "alta"}'
    return httpx.Response(200, json={
        "choices": [{"message": {"content": contenido}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 10},
    })


def cliente() -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(servidor))


def test_interpretar_valido_e_invalido() -> None:
    assert cm.interpretar('{"categoria": "consulta", "confianza": "baja"}') == ("consulta", "baja")
    assert cm.interpretar("texto suelto") == (None, None)
    assert cm.interpretar('{"categoria": "otra_cosa"}')[0] is None


def test_un_modelo_cuenta_aciertos_e_invalidas() -> None:
    filas = cm.correr("chico", CONFIG, RECLAMOS, cliente())
    r = cm.resumir(filas)
    assert (r["aciertos"], r["invalidas"], r["tokens"]) == (1, 1, 220)


def test_cascada_escala_solo_lo_que_no_pasa_el_chequeo() -> None:
    filas = cm.correr("cascada", CONFIG, RECLAMOS, cliente())
    assert [f["modelo_final"] for f in filas] == ["chico", "grande"]
    assert cm.resumir(filas)["aciertos"] == 2
    # el grande solo se pagó en el segundo reclamo: (100*1 + 10*2) / 1e6
    assert filas[1]["costo_usd"] == round(120 / 1_000_000, 6)


def test_grafico_tiene_un_punto_por_configuracion() -> None:
    svg = cm.grafico_svg({
        "a": {"aciertos": 10, "total": 20, "tokens": 500},
        "b": {"aciertos": 18, "total": 20, "tokens": 900},
    })
    assert svg.count("<circle") == 2


def test_cascada_desde_resultados_no_llama_a_ningun_modelo(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(cm, "RESULTADOS", tmp_path)
    cm.guardar("chico", cm.correr("chico", CONFIG, RECLAMOS, cliente()))
    cm.guardar("grande", cm.correr("grande", CONFIG, RECLAMOS, cliente()))
    armada = cm.cascada_desde_resultados("cascada", CONFIG)
    real = cm.correr("cascada", CONFIG, RECLAMOS, cliente())
    # Con un servidor que siempre responde igual, la cascada armada y la real coinciden.
    assert [f["modelo_final"] for f in armada] == [f["modelo_final"] for f in real]
    assert cm.resumir(armada) == cm.resumir(real)

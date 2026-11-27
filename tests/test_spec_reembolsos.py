"""Criterios de la spec de reembolsos, escritos como pruebas antes del código.

Cada prueba está marcada como «falla esperada» (xfail) por ausencia del módulo: la funcionalidad se
implementa en M3. Cuando exista y la prueba pase, pytest avisa (strict=True)
y hay que quitar la marca.
"""

from decimal import Decimal

import pytest

PENDIENTE = pytest.mark.xfail(
    strict=True,
    raises=ModuleNotFoundError,
    reason="Spec M2: el módulo app.reembolsos aún no existe",
)


@PENDIENTE
def test_rechaza_reembolso_mayor_al_saldo() -> None:
    # Criterio (EARS, no deseado): si el monto pedido supera el saldo
    # reembolsable, entonces el sistema deberá rechazar el pedido con el
    # código AMOUNT_EXCEEDS_BALANCE.
    from app.reembolsos import evaluar_reembolso_parcial

    resultado = evaluar_reembolso_parcial(
        monto_original=Decimal("100.00"),
        ya_reembolsado=Decimal("70.00"),
        monto_pedido=Decimal("40.00"),
    )
    assert resultado["aprobado"] is False
    assert resultado["codigo"] == "AMOUNT_EXCEEDS_BALANCE"


@PENDIENTE
def test_rechaza_pedido_si_el_saldo_es_cero() -> None:
    # Criterio (EARS, por estado): mientras el saldo reembolsable de una
    # transacción se encuentre en cero, el sistema deberá rechazar cualquier
    # nuevo pedido de reembolso con el código AMOUNT_EXCEEDS_BALANCE.
    from app.reembolsos import evaluar_reembolso_parcial

    resultado = evaluar_reembolso_parcial(
        monto_original=Decimal("100.00"),
        ya_reembolsado=Decimal("100.00"),
        monto_pedido=Decimal("10.00"),
    )
    assert resultado["aprobado"] is False
    assert resultado["codigo"] == "AMOUNT_EXCEEDS_BALANCE"

# Criterios del reembolso parcial (LegacyPay)

## Requisitos en EARS

1. **Por evento:** Cuando un comercio solicite un reembolso parcial de una transacción aprobada por un monto mayor que cero, el sistema deberá devolver el monto exacto solicitado, sin exceder el saldo reembolsable.
2. **No deseado:** Si el monto solicitado supera el saldo reembolsable disponible, entonces el sistema deberá rechazar la solicitud y retornar el código de error `AMOUNT_EXCEEDS_BALANCE`.
3. **Por estado:** Mientras el saldo reembolsable de una transacción se encuentre en cero, el sistema deberá rechazar cualquier nuevo pedido de reembolso sobre esa transacción y retornar el código de error `AMOUNT_EXCEEDS_BALANCE`.

## Escenarios (dado / cuando / entonces)

**Escenario 1**
- Dado: una transacción aprobada de 200,00 con 50,00 ya reembolsados (saldo reembolsable: 150,00)
- Cuando: el comercio pide un reembolso de 80,00
- Entonces: el sistema devuelve exactamente 80,00; el saldo reembolsable queda en 70,00

**Escenario 2**
- Dado: una transacción aprobada de 300,00 con 120,00 ya reembolsados (saldo reembolsable: 180,00)
- Cuando: el comercio pide un reembolso de 200,00
- Entonces: el sistema rechaza el pedido con el código `AMOUNT_EXCEEDS_BALANCE` y no devuelve ningún monto

## Métrica de resultado

Ningún reembolso parcial pagado supera el saldo reembolsable de su transacción: 0 casos en todos los reembolsos procesados.

## Guardrail (lo que no tiene que empeorar)

Ni las respuestas ni los registros de un reembolso muestran el número completo de la tarjeta ni el código de seguridad del cliente.

## Preguntas abiertas (no se resuelven con supuestos)

1. ¿Qué política de reembolsos se aplica a una transacción en disputa?
2. ¿Existe un plazo máximo para pedir un reembolso parcial, y de cuántos días?
3. ¿Quién puede pedir un reembolso parcial: solo el comercio, o también el cliente?
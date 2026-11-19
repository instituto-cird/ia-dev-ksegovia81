# AI_USAGE.md · Registro de uso de IA

> Este archivo documenta el **origen** del trabajo: qué hizo la IA, qué hizo la persona y cómo se verificó. Se completa en cada laboratorio. En las revisiones y en la defensa final se puede preguntar por cualquier entrada. El formato es un criterio del programa.

## Cuándo registrar

**Se registra cuando hubo una decisión, no cuando hubo un autocompletado.**

Se registra si:
- El pedido se reescribió tres veces o más hasta obtener el resultado
- La salida no funcionó al primer intento y hubo que depurarla
- Se aceptó un diseño que la persona no había pensado antes
- Se **rechazó** una sugerencia (por seguridad, rendimiento o corrección)
- La IA **inventó** algo (librería, función, dato) y se detectó
- Un agente modificó varios archivos o ejecutó comandos
- Se usó IA para diagnosticar un error

No hace falta registrar el autocompletado de un `import`, de un nombre de variable o de un bloque que la persona iba a escribir de todos modos.

> **Regla práctica:** si dentro de tres meses no se va a recordar por qué el código quedó así, se registra.

## Niveles de autonomía

Se usan los cinco niveles de Feng, McDonald y Zhang (2025), definidos por el rol de la persona frente al agente: **1 operador** (la persona planifica y ejecuta; la IA sugiere a pedido) · **2 colaborador** (trabajo compartido; la persona puede tomar el control) · **3 consultor** (el agente planifica y ejecuta; la persona orienta en momentos clave) · **4 aprobador** (el agente trabaja solo; la persona destraba bloqueos y aprueba acciones importantes) · **5 observador** (la persona solo revisa el registro o detiene al agente).

Fuente: Feng, K. J. K., McDonald, D. W. y Zhang, A. X. (2025). *Levels of Autonomy for AI Agents*. arXiv:2506.12469. Preprint sin revisión por pares.

---

## Entradas

### Entrada 000 · Lab 0 · Onboarding

| Campo | Detalle |
|---|---|
| Fecha | 2026-11-01 |
| Herramienta | Claude (chat en claude.ai) |
| Nivel de autonomía | 1 operador |
| Para qué se usó | Para preparar mi entorno de desarrollo en Windows: instalar VS Code y uv, clonar mi repositorio, instalar las dependencias y verificar que todo funcione. También para entender qué trae el repositorio de la plantilla. |
| Qué hizo la IA | Me indicó los comandos paso a paso y me ayudó a entender los mensajes de error. También revisó el repositorio en modo lectura y me explicó qué contiene. Cuando le pregunté si podía usar la rama develop, me confirmó que era posible. |
| Qué hubo que corregir o rehacer | Una parte. La IA había supuesto que mi computadora era una Dell con 8 GB; lo verifiqué con un comando y era una ASUS con 16 GB. |
| Cómo se verificó | Ejecuté yo cada comando. Las 37 pruebas pasaron, ruff no marcó errores y la API abrió en /docs. |
| Qué decisión fue propia | Crear la rama develop y, después de leer el README de la profe, volver a trabajar desde main en la rama feature/m0-onboarding, como ella pide. Elegir yo el objetivo de la sección Autor/a del README, entre varias opciones que la IA propuso. |
| Commit o PR | PR #1 (feature/m0-onboarding hacia main), commit db796bd |

### Entrada 001 · Lab 1 · Ejercitario «¿Cuánto le delego al agente?»

| Campo | Detalle |
|---|---|
| Fecha | 2026-11-19 |
| Herramienta | Claude (chat en claude.ai) |
| Nivel de autonomía | 1 operador |
| Para qué se usó | Para entender el ejercitario, elegir la tarea (LegacyPay) y diseñar una política de permisos para un agente. También para escribir .vscode/settings.json, agregar mis comandos a la prueba y correrla, y para resumir las lecturas de la clase. |
| Qué hizo la IA | Me propuso la tabla de la tarea (LegacyPay, nivel 4 aprobador) y la tabla de cinco acciones. Me dio los comandos paso a paso, me explicó qué comprueba el archivo de prueba y resumió las lecturas de Feng y de Anthropic. No pudo leer el ensayo de Osmani. |
| Qué hubo que corregir o rehacer | Poco. La IA supuso que AI_USAGE.md estaba en la rama nueva; solo estaba en feature/m0-onboarding y hubo que traerlo. |
| Cómo se verificó | Ejecuté yo cada comando. La prueba de la política pasó (7 pasaron, 6 saltadas) y falló a propósito cuando cambié "git push" a true. ruff pasó y las 44 pruebas pasaron con 100 % de cobertura. |
| Qué decisión fue propia | Aprobar LegacyPay como tarea y el nivel 4. Aceptar las cinco acciones de la política y agregar a la prueba git push, uv lock y uv remove requests. |
| Commit o PR | (se completa al abrir el PR) |

**Mi hipótesis antes de pedir:** Esperaba que bastara con escribir las reglas en settings.json para que quedaran cumplidas.
**Una cosa que el agente no verificó:** Que las reglas se respeten en Autopilot o Allow all, y que se pueda bloquear la lectura de archivos con claves (.env). Las reglas de VS Code solo permiten o piden aprobación, y la prueba solo comprueba que estén escritas.
**Decisiones y supuestos del agente que acepté:** Que LegacyPay con nivel 4 era una buena tarea. Que las reglas de terminal alcanzan para las cinco acciones, aunque la de .env necesita un sandbox u otro control.

<!-- Copiar el bloque de la entrada para cada nueva (001, 002…) -->

---

## Resumen por laboratorio

Al cerrar cada laboratorio se completa una fila. Al final del programa, cada participante tiene sus propios números de **autonomía** y **retrabajo**, dos métricas que aparecen en descripciones de puestos de equipos que trabajan con agentes (revisadas por el programa en 2026, uso interno).

| Lab | Entradas | Nivel más usado | Parte hecha por el agente (aprox. %) | Parte que hubo que rehacer (aprox. %) |
|---|---|---|---|---|
| Lab 0 | 1 | 1 operador | ~30% | ~10% |
| Lab 1 | | | | |
| Lab 2 | | | | |
| Lab 3 | | | | |
| Lab 4 | | | | |

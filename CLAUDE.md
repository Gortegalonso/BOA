# CLAUDE.md — Vigilancia de las Pruebas de Obtención de Título (POT) de FP en Aragón

> Versión 3, 17 de agosto de 2026. Documento vivo. Todo lo marcado `[VERIFICAR]` no está
> confirmado y **no debe darse por bueno sin comprobarlo contra la fuente**. Las secciones
> 1-9 y 12 son la especificación original (por qué del proyecto, reglas, diseño); la sección
> 0 es el estado real de la implementación y la 10-11 documentan cómo se llegó hasta aquí.
> Si algo de 0/10/11 contradice a 1-9, **gana lo verificado con datos reales** — la
> especificación se ha ido corrigiendo sobre la marcha (ver 3 y 7.1).

---

## 0. Estado del proyecto y mapa del repositorio

Léela primero si retomas este proyecto sin contexto previo — resume qué existe, dónde está y
cómo se ejecuta, sin repetir el detalle de las secciones 1-9 (la especificación) ni 10-11
(la bitácora de las fases).

### 0.1 Resumen de una frase por fase

| Fase | Qué hace | Estado |
|---|---|---|
| 0. Verificación de fuentes | `robots.txt`, URL del RSS, buscador JSON del BOA | ✅ completa (salvo alta de correo, manual) |
| 1. Colector A + filtro | Vigila el BOA, decide qué es relevante | ✅ completa |
| 2. Caché histórica | Materia prima offline para el backtest | ✅ completa (reinterpretada, ver 10) |
| 3. Backtest | Recall 100% sobre 12 documentos reales 2018-2026 | ✅ **puerta superada** |
| 4. Colector B | Vigila `educa.aragon.es` (listas, calendario, sedes) | ✅ completa |
| 5. Extracción con LLM | PDF → JSON (plazos, módulos, sedes) | ✅ completa, verificada contra las APIs reales |
| 6. Cruce alumno-módulo | Qué debe inscribir cada alumno | ✅ completa, verificada extremo a extremo con la convocatoria real |
| 7. Alertas y robustez operativa | Canario, keepalive, pruebas de contrato/regresión/estacional | ✅ completa, adelantada junto con la Fase 1 |
| — Panel (GitHub Pages / `index.html`) | Visualización local del estado | ⏳ no empezada |
| — Suscripción por correo al BOA | Canal 1 de 7.1, respaldo del RSS | ⏳ dos tareas pendientes, ver 0.5: alta manual (usuario) + lector IMAP (sin construir) |

Detalle de cómo se hizo cada fase, decisiones tomadas y por qué: sección 10. Lo que queda
sin confirmar: sección 11.

### 0.2 Árbol del repositorio

```
boa_monitor/                   # Paquete Python del sistema. Sin dependencias externas
│                               # salvo pytest (solo para tests). Todo en español.
├── rss.py                     # Colector A: descarga y parsea el RSS del BOA (7.1, 7.1.1)
├── filtro.py                  # Reglas R1-R4 + cubos seguro/ambiguo/descartado (7.3)
├── cache.py                   # Caché local del RSS crudo + registro de DOCN ya vistos
├── main.py                    # Orquesta rss+filtro+cache, escribe estado.json y
│                               # convocatorias.json. Punto de entrada: `python -m boa_monitor.main`
├── educa.py                   # Colector B: diff de enlaces PDF en educa.aragon.es (7.2)
│                               # Punto de entrada: `python -m boa_monitor.educa`
├── backtest.py                # Ejecuta el filtro contra el conjunto de verdad y da
│                               # recall/precisión. `python -m boa_monitor.backtest`
├── contrato.py                # Prueba de contrato (9.3): ¿el RSS del BOA sigue igual?
│                               # `python -m boa_monitor.contrato`
├── alerta_estacional.py       # Prueba 9.4: ¿ha pasado el 10 de sept. sin convocatoria?
│                               # `python -m boa_monitor.alerta_estacional`
├── extraccion.py              # Fase 5: PDF → JSON con LLM (imagen, no texto) + validación
│                               # determinista (7.4-7.5). Fallback Gemini → Mistral, los dos
│                               # gratuitos y con API compatible con OpenAI (urllib, sin SDK).
│                               # `python -m boa_monitor.extraccion <ruta_al_pdf>`
└── cruce.py                   # Fase 6: cruce alumno-módulo (7.6). Lee el Excel del usuario
                                # (fuera del repo) y lo compara contra los `modulos_convocados`
                                # de la Fase 5. `python -m boa_monitor.cruce <alumnos.xlsx> <convocatoria.json>`

tests/                         # pytest. 60 tests, todos deterministas y offline
├── test_rss.py                # Parseo del RSS contra el fixture real de 2026
├── test_filtro.py             # Reglas del filtro + pruebas de robustez de redacción
├── test_main.py                # Orquestación end-to-end con red simulada (monkeypatch)
├── test_educa.py               # Extracción y diff de PDFs de Colector B
├── test_regresion.py           # Recall sobre los 12 fixtures históricos (9.2)
├── test_backtest.py            # Puerta de la Fase 3: recall 100% obligatorio (10)
├── test_alerta_estacional.py   # Casos de la alerta del 10 de septiembre
├── test_extraccion.py          # Render PDF→imagen, validación 7.5, fallback entre proveedores
│                                # (red simulada con monkeypatch, igual que test_educa.py)
└── test_cruce.py                # Carga de Excel, filtro por "pendiente", marca convocado/no
                                  # convocado, contra el fixture de alumnos inventados

fixtures/
├── regresion/                  # RSS real cacheado de los 12 días con positivo conocido
│   ├── *.rss                   # 2018-02-09 a 2026-08-06, ver positivos_esperados.json
│   └── positivos_esperados.json  # Conjunto de verdad: fecha → DOCN esperado, tipo, orden
├── educa/
│   ├── pots_calendario_2026-08-17.html      # HTML real de la página de Colector B
│   └── anexo_iii_calendario_pot_2026.pdf    # PDF real (calendario de la convocatoria 2026),
│                                             # fixture de test_extraccion.py
└── cruce/
    └── alumnos_ejemplo.xlsx    # Alumnos INVENTADOS (nombres y códigos ficticios) para
                                 # probar y desarrollar la Fase 6 sin datos reales — no es una
                                 # plantilla oficial ni contiene a nadie real, ver sección 8

data/                           # Estado y resultados. Se versiona (son datos públicos,
│                                # nunca de alumnos — ver sección 8 y .gitignore).
├── cache_rss/*.rss             # Caché cruda del RSS, por fecha
├── vistos.json                 # DOCN ya procesados por Colector A (evita re-alertar)
├── estado.json                 # Prueba de vida de Colector A (9.1)
├── convocatorias.json          # Documentos marcados "seguro"/"ambiguo" por Colector A
├── estado_educa.json           # Última foto de enlaces PDF por página vigilada (Colector B)
└── documentos_educa.json       # Documentos PDF nuevos detectados por Colector B

.github/workflows/
├── colector.yml                # Cron de Colector A (horario/30min según sección 7.1)
├── colector-educa.yml          # Cron de Colector B (10:00, 13:00, 17:00 L-V)
├── regresion.yml               # Semanal: pytest contra los fixtures (9.2)
├── contrato.yml                # Semanal: ¿el RSS del BOA sigue igual? Abre issue si falla (9.3)
├── alerta_estacional.yml       # 10 de septiembre: ¿hay convocatoria? Abre issue si no (9.4)
└── keepalive.yml               # Semanal: evita que GitHub desactive los crons por inactividad

alumnos/                        # Vacío a propósito. Aquí va el CSV de alumnos del usuario,
│                                # NUNCA versionado (.gitignore lo excluye). Ver sección 8.
.gitignore                      # Excluye alumnos/, CSVs, credenciales, entorno virtual
requirements.txt                # pytest (dev) + pymupdf (runtime, solo para extraccion.py)
CLAUDE.md                       # Este documento
```

### 0.3 Cómo arrancar en frío

```powershell
# Entorno (Windows/PowerShell; el proyecto usa un venv propio en .venv/)
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# Tests (deterministas, offline, ~0.6 s)
.\.venv\Scripts\python.exe -m pytest -q

# Backtest completo con informe legible
.\.venv\Scripts\python.exe -m boa_monitor.backtest

# Ejecutar un colector a mano (escribe en data/, hace peticiones reales)
.\.venv\Scripts\python.exe -m boa_monitor.main            # Colector A (BOA), fecha de hoy
.\.venv\Scripts\python.exe -m boa_monitor.main 2026-08-06  # Colector A, fecha concreta
.\.venv\Scripts\python.exe -m boa_monitor.educa            # Colector B (educa.aragon.es)

# Pruebas de contrato / estacional a mano
.\.venv\Scripts\python.exe -m boa_monitor.contrato
.\.venv\Scripts\python.exe -m boa_monitor.alerta_estacional

# Fase 5: extraer un PDF real a JSON (necesita GEMINI_API_KEY y/o
# MISTRAL_API_KEY en el entorno — ver 7.4 y 0.5)
$env:GEMINI_API_KEY = "..."
$env:MISTRAL_API_KEY = "..."
.\.venv\Scripts\python.exe -m boa_monitor.extraccion "fixtures\educa\anexo_iii_calendario_pot_2026.pdf"
```

Convenciones del código: todo en español (identificadores, mensajes, tests), sin comentarios
que expliquen el qué (los nombres ya lo dicen), stdlib únicamente en tiempo de ejecución
(`urllib`, `xml.etree`, `json`, `re`) — ver el porqué en sección 6. Cada módulo de
`boa_monitor/` es ejecutable como script (`python -m boa_monitor.<módulo>`) y tiene su propio
fichero de test homónimo en `tests/`.

### 0.4 Repositorio remoto

`https://github.com/Gortegalonso/BOA` (público). El repo local usa git normal; no hay
credenciales guardadas en `.git/config` — el push se hace con un token temporal embebido en
la URL del remoto solo durante el `push` y se revierte a la URL limpia inmediatamente
después. `API KEY.txt` (tokens personales del usuario) está en `.gitignore` y nunca se
versiona.

### 0.5 Qué haría falta para continuar (por orden de dependencia)

1. **Fase 5 (extracción LLM) — completa y verificada el 18/08/2026 contra las APIs reales.**
   `boa_monitor/extraccion.py` implementa 7.4 (PDF→imagen con PyMuPDF, prompt con el esquema
   JSON, llamada por `urllib` sin SDK) y 7.5 (validación determinista; el umbral de 30 días
   se corrigió a 60 con el dato real de 2026, ver sección 7.5). Fallback en orden: **Gemini**
   (`gemini-flash-latest`, endpoint compatible con OpenAI, variable `GEMINI_API_KEY`) →
   **Mistral** (`mistral-large-latest`, incluye visión vía Pixtral en su tier gratuito,
   variable `MISTRAL_API_KEY`). Se descartó Groq como candidato pese a ser buen fallback en
   velocidad: sus modelos de visión gratuitos (Llama 4 Maverick y Scout) se retiraron en
   febrero y junio de 2026, confirmando en vivo el riesgo que ya avisaba 7.4. 9 tests con red
   simulada (`tests/test_extraccion.py`) + fixture real
   (`fixtures/educa/anexo_iii_calendario_pot_2026.pdf`).
   **Ejecutado con claves reales el 18/08/2026** (ver el detalle en la sección 10, bitácora de
   la Fase 5): Gemini devolvió `503 UNAVAILABLE` ("alta demanda") — error del lado de Google,
   no de configuración, confirmado inspeccionando el cuerpo de la respuesta — y el fallback a
   Mistral funcionó correctamente, extrayendo el plazo real (10-17 de septiembre) del Anexo
   III y marcando como ausentes, sin inventar nada, los campos que ese documento en concreto
   no trae (código de orden, módulos, etc., regla 7). El sistema completo —render, llamada,
   fallback, validación— queda verificado de extremo a extremo con un documento real.
2. **Fase 6 (cruce alumno-módulo) — completa y verificada el 18/08/2026 con la convocatoria
   real.** `boa_monitor/cruce.py` implementa 7.6: lee un Excel de alumnos (vía `openpyxl` —
   única forma de leer .xlsx sin librería) y lo cruza contra los `modulos_convocados` que
   devuelve la Fase 5. **Corregido con datos reales**: la clave del cruce es el título/ciclo
   (`titulo_codigo_oficial`, p.ej. `HOT201`), no el módulo — el Anexo II solo convoca a nivel
   de título (ver el detalle completo en 7.6). Se ejecutó de extremo a extremo contra la
   extracción real del Anexo II (110 títulos) y un Excel de alumnos inventados, con resultado
   correcto en los seis casos de prueba (pendientes, superados, convalidados, título no
   convocado, dos módulos del mismo título convocado, aviso de grado incoherente). La lista
   de títulos de hostelería (antes pendiente `[VERIFICAR]`) queda confirmada con códigos
   oficiales reales en 7.6, salvo la duda menor sobre si `HOT301`-`HOT303` (turismo) también
   los imparte el centro del usuario.
3. **Panel local (`index.html`)**: descrito en sección 6 y 9.1 pero no implementado. Depende
   de tener `convocatorias.json` con datos reales de un año completo para ser útil de probar.
4. **Suscripción por correo al BOA (canal 1 de 7.1) — dos tareas separadas, ninguna hecha
   todavía (anotado 18/08/2026).**
   1. **Alta de la suscripción, puramente manual**: darse de alta en la suscripción gratuita
      del BOA al sumario diario. Es un trámite en la web del BOA, no algo que el código
      pueda hacer — pide al usuario que confirme que la ha hecho antes de construir lo
      siguiente.
   2. **Lectura automática por IMAP, sin construir todavía**: hoy el Colector A solo
      implementa el canal 2 (RSS, `boa_monitor/rss.py`). Leer el correo automáticamente como
      canal de respaldo requeriría un módulo nuevo (`boa_monitor/correo.py`, mismo patrón que
      `rss.py`: descarga, caché, tests con fixture real) que se conecte por IMAP, descargue
      el resumen diario y lo parsee, más las credenciales de esa cuenta de correo como secret
      de GitHub Actions — nunca en el repo, mismo patrón que `GEMINI_API_KEY`/
      `MISTRAL_API_KEY`. No es urgente: el RSS ya es el canal validado y en producción (Fase
      0-1), este sería solo un respaldo adicional.
5. Antes de dar por buena la Fase 4 en producción, confirmar en la primera convocatoria real
   que se recojan documentos nuevos en `educa.aragon.es` a lo largo del ciclo (listas de
   admitidos, etc.) que el diff de Colector B los detecta — de momento solo se ha probado
   con la foto actual de la página (4 PDFs) y con estados sintéticos en los tests.

---

## 1. Objetivo

Detectar, con recall efectivo del 100 %, la publicación anual en el BOA de la convocatoria
de **pruebas para la obtención directa de los títulos de Técnico y Técnico Superior de
Formación Profesional** en Aragón, junto con sus documentos derivados, y extraer de ellos la
información operativa (plazos, módulos convocados, sedes) para gestionar la inscripción de
50-100 alumnos al año en los ciclos de hostelería y restauración.

El sistema es una **red de seguridad**, no la única fuente. El usuario mantiene además la
suscripción manual gratuita al BOA.

---

## 2. Glosario del dominio

Leer antes de escribir código. Confundir estos términos produce un modelo de datos erróneo.

| Término | Significado |
|---|---|
| **POT** | Prueba de Obtención de Título. Examen que permite superar módulos profesionales sin cursarlos. En Aragón **no es una "prueba libre"**: exige requisitos concretos de acceso. |
| **Módulo profesional** | La asignatura. **Es la unidad de examen y la unidad de inscripción.** El alumno se inscribe a módulos concretos, no "al título". |
| **Ciclo formativo** | Conjunto de módulos que componen un título. |
| **Convalidación** | Mecanismo **distinto** de la POT: reconocimiento de módulos ya superados o de unidades de competencia acreditadas. Se solicita **en el momento de la inscripción**. |
| **FCT** | Formación en Centros de Trabajo. Aparentemente **excluida** de la POT. `[VERIFICAR]` |
| **Grado Medio / Superior** | Técnico (18 años mínimo) / Técnico Superior (20 años mínimo). |

**Regla derivada:** el modelo de datos se ancla en `modulo`, no en `titulo`.

---

## 3. Hechos verificados

Verificados el 17 de agosto de 2026, ampliados el mismo día con un backtest real 2018-2026.

- **Convocatoria 2026 ya publicada**: ORDEN ECU/1145/2026, de 21 de julio, BOA nº 151 de 6
  de agosto de 2026.
- **Convocatoria 2025**: ORDEN ECD/941/2025, de 24 de julio, BOA nº 148 de 4 de agosto.
- **CORREGIDO — la "ventana crítica" de la versión 1 era errónea.** Se basaba en n=2 y decía
  "1 julio – 30 septiembre". El backtest sobre 2011-2026 (16 años, buscador oficial del BOA,
  ver más abajo) muestra fechas de publicación en **febrero, marzo, mayo, junio, julio,
  agosto, noviembre y diciembre**, sin ningún patrón mensual estable. La fecha de publicación
  se ha ido desplazando progresivamente hacia el verano en los últimos años, pero no hay base
  para excluir ningún mes. **No estrechar nunca la ventana de vigilancia por debajo de todo el
  año.** El colector ya vigila los 12 meses (ver 7.1), así que el recall no estaba en riesgo;
  lo único mal calibrado era qué meses reciben el sondeo cada 30 min en vez de cada hora.
- **Posible hueco en 2020**: no se ha encontrado ninguna orden de convocatoria firmada en el
  año natural 2020. La ORDEN ECD/1655/2019 (28 de noviembre de 2019) cubre expresamente el
  año 2020, y la siguiente es la ORDEN ECD/460/2021 (3 de mayo de 2021). Compatible con una
  disrupción por la pandemia. `[VERIFICAR]`
- **El prefijo de la orden cambió de `ECD` a `ECU`** entre 2025 y 2026; antes fue `ECD`
  (2018-2025), y en 2011 era simplemente `ORDEN de <fecha>, de la Consejera de Educación...`
  sin código de orden. El filtro nunca debe anclarse a un prefijo concreto (ya lo dice la
  regla 5, y el backtest lo confirma con datos reales).
- **El BOA está disponible a las 00:15 h** el 99 % de los días, según su carta de servicios.
  Excepción explícita: **boletines extraordinarios**, a cualquier hora y cualquier día.
- **Publicación de lunes a viernes**, salvo festivos nacionales o autonómicos.
- **El BOA ofrece RSS diario y suscripción gratuita por correo** al sumario o a cualquier
  sección.
- **El feed RSS está confirmado y validado.** Descargado para el 6/08/2026: devuelve 26
  documentos y **contiene la ORDEN ECU/1145/2026** (item 15, no 14 — recontar tras decodificar
  bien ISO-8859-1). Sirve como fuente primaria.
- **`robots.txt` de boa.aragon.es verificado (Fase 0, resuelve el pendiente de la sección 11
  antigua).** No bloquea `RSSLST`, `VERLST` ni `VERDOC` de forma genérica. Solo contiene
  ~2000 líneas de bajas puntuales por documento (`MLKOB=...`, retiradas legales caso a caso) y
  una entrada residual de un `VERDOC` sobre otra base (`BZHT`) sin relación con nuestro uso.
  El canal RSS (opción 1 de 7.1) queda confirmado como libre de restricción.
- **El feed SÍ incluye la Sección I (resuelve el otro pendiente de la sección 11 antigua).**
  Comprobado comparando el RSS del 4/08/2026 contra el sumario HTML oficial de esa fecha: el
  primer ítem de ambos coincide exactamente (RESOLUCIÓN del Secretario General de la
  Presidencia, Sección I, csv `BOA20260804001`).
- **Volumen real: ~26-46 documentos al día** según el boletín (variación observada en el
  backtest: de 20 a 60 documentos), unos 6.000-9.000 al año.
- **Descubierto un buscador oficial con salida JSON estructurada.** El BOA (aplicación
  Angular) usa internamente `CMD=VERLST&BASE=BZHT&SEC=OPENDATABOAJSONELI&OUTPUTMODE=JSON` con
  parámetros de campo: `TITU` (título, texto libre con AND-de-palabras, no frase exacta),
  `TEXT-C` (texto completo del documento, más ruidoso), `ORGA-C` (organismo), `RANG-C` (tipo:
  ORDEN, RESOLUCIÓN, DECRETO...), `PUBL-GE`/`PUBL-LE` (rango de fecha de publicación),
  `FDIS-C`/`FDIS-GE` (fecha de disposición), `MATE-C` (materia), `SECC-C` (sección). Los
  acentos se codifican como ISO-8859-1 percent-encoded (`ó` → `%F3`, `í` → `%ED`, etc., no
  UTF-8). La barra `/` en los valores de los parámetros rompe la consulta (devuelve HTML de
  error, no JSON) — evitarla o sustituirla por espacios. Cada resultado JSON trae `DOCN`,
  `FechaPublicacion`, `Fechadisposicion`, `Rango`, `Emisor`, `Titulo` y el `Texto` completo.
  **Esto fue decisivo para la Fase 3**: permitió construir el conjunto de verdad sin
  descargar miles de sumarios diarios. No es un canal documentado ni estable frente a
  cambios de la web (a diferencia del RSS), así que **no usar en producción**, solo para
  investigación puntual y para reconstruir el backtest si hace falta ampliarlo.
- **Backtest 2018-2026 completado (Fase 3, ver sección 10): recall 100 %, 12/12 documentos
  reales capturados.** Conjunto de verdad = 8 órdenes de convocatoria (una por año, salvo el
  hueco de 2020) + 4 correcciones de errores, localizadas con el buscador anterior y
  verificadas con una segunda búsqueda con términos distintos (sin solapamiento en los
  resultados, lo que descarta que falte alguna con redacción distinta). Precisión agregada
  sobre esos 12 boletines reales: 75 % (16 marcados, 12 positivos); los 4 falsos positivos
  vienen todos de R3 (auxiliar) y caen en el cubo "ambiguo", nunca en "seguro".
- **Hallazgo importante — ningún documento derivado de la POT (listas de admitidos,
  calendario, sedes, tribunales) aparece en el BOA entre 2018 y 2026**, pese a probar varias
  combinaciones de búsqueda (`admitidas`+`profesional`, `tribunales`+`profesional`,
  `calendario`+`profesional`+`tecnico`, búsqueda por organismo=educación + tipo=RESOLUCIÓN).
  Todo lo encontrado con esas palabras son procesos selectivos de personal de la
  Administración, no de la POT. Esto **resuelve a favor de "solo educa.aragon.es"** el
  pendiente de la sección 11 sobre qué documentos van al BOA — aunque la ausencia de
  evidencia no es prueba definitiva, refuerza que el Colector B (7.2) es imprescindible, no
  opcional. `[VERIFICAR]` mantenido por prudencia, pero con bastante más peso a favor.
- **Licencia de los datos**: Creative Commons Attribution 4.0. Atribución obligatoria si se
  redistribuye contenido.
- **Requisito de acceso aplicable a estos alumnos**: matrícula previa en un ciclo formativo
  en centro sostenido con fondos públicos de Aragón, con al menos cinco módulos superados
  (art. 126.4 del Decreto 91/2024).
- **Calendario completo de la convocatoria 2026, extraído del Anexo III (18/08/2026,
  resuelve el pendiente urgente de la sección 11):**

  | Actuación | Fecha prevista |
  |---|---|
  | Presentación de solicitudes | Del 10 al 17 de septiembre |
  | Listados provisionales de admitidos/no admitidos | 5 de octubre |
  | Plazo de reclamación a los listados provisionales | Del 6 al 9 de octubre |
  | Listados definitivos de admitidos/no admitidos | 20 de octubre |
  | Constitución de las Comisiones de evaluación | Antes del 21 de octubre |
  | Publicación de datos de las pruebas por las Comisiones | Antes del 23 de octubre |
  | Realización de las pruebas | Del 3 al 13 de noviembre |
  | Publicación de calificaciones | Hasta el 18 de noviembre |
  | Periodo de reclamaciones | Hasta el 20 de noviembre |
  | Sesiones de evaluación | Hasta el 27 de noviembre |

  Fuente: `https://educa.aragon.es/documents/20126/6840006/Anexo+III+Orden+POT_2026+v3.pdf`
  (URL capturada por el Colector B, ver `data/documentos_educa.json`). **Da además un punto
  de verificación natural para el pendiente 0.5.5**: los listados de admitidos deberían
  aparecer en `educa.aragon.es` (no en el BOA, según el hallazgo de la Fase 3) sobre el 5 de
  octubre — comprobar entonces que el Colector B los captura.

---

## 4. Alcance

**Dentro:** Aragón exclusivamente. POT de Técnico y Técnico Superior. Documentos derivados:
corrección de errores, ampliación de plazo, listas provisionales y definitivas de admitidos
y excluidos, calendario, sedes, tribunales.

**Fuera:** subvenciones y ayudas. Pruebas de acceso a ciclos. Certificados de
profesionalidad y acreditación de competencias. Otras comunidades autónomas. BOE y
boletines provinciales, que **no publican convocatorias educativas autonómicas**.

---

## 5. Reglas de diseño no negociables

1. **Maximizar recall, ignorar la precisión.** Falso negativo: un año perdido para el
   alumno. Falso positivo: 10 segundos de revisión. 50 falsos positivos al año son
   aceptables; un falso negativo no.
2. **El recorte a hostelería NO se aplica en la detección.** La convocatoria es única y
   cubre muchos ciclos; filtrar por "hostelería" al detectar haría que el documento no
   dispare ninguna regla. El filtro se queda ancho; el recorte ocurre en el cruce (7.5).
3. **Sin cribado por LLM.** Con ~1 documento relevante al año, un modelo en la decisión de
   descarte añade un modo de fallo sin ganancia. La detección es determinista y auditable.
4. **La decisión final la toma el código, nunca el modelo.** El LLM convierte PDF en JSON;
   el código valida y decide.
5. **No anclar el filtro en nada mutable**: ni el prefijo de la orden (`ECD` → `ECU` ya
   ocurrió), ni el número o nombre de sección, ni el nombre del departamento, ni la
   redacción exacta del título.
6. **El silencio es el estado normal.** Once meses al año el resultado correcto es "nada".
   Distinguir "no hay nada" de "estoy roto" es un requisito, no una mejora.
7. **Nunca inventar datos.** Campo no encontrado, valor `null` y marca de revisión humana.
   Jamás rellenar plazos, códigos de módulo o sedes por inferencia.
8. **Los datos de alumnos no entran nunca en un repositorio público.** Ver sección 10.

---

## 6. Stack

| Pieza | Decisión | Motivo |
|---|---|---|
| Ejecución | GitHub Actions con `on: schedule` | Sin instalar nada, gratis, logs, secrets |
| Zona horaria | Campo `timezone: Europe/Madrid` | Disponible desde marzo de 2026; evita el lío del horario de verano |
| Persistencia | Ficheros JSON o CSV versionados en el repo | Diffs legibles = auditoría gratis. SQLite sería un binario opaco para git |
| Base de datos | **Ninguna** | Cientos de registros al año. SQL no aporta nada a esta escala |
| Panel | GitHub Pages, estático, generado por el workflow | Sin servidor. **Sin datos de alumnos** |
| Lenguaje | Abierto, se sugiere Python | Criterio: mínimo de dependencias |

### Reparto híbrido GitHub / local

| Dónde | Qué |
|---|---|
| Repo público + Actions | Cron, colectores, filtro, extracción, caché del BOA, `convocatorias.json`. Todo dato público. |
| Local | `alumnos.csv`, cruce, `index.html`. No sale de la máquina del usuario. |
| Puente | `git pull` |

Detalle práctico: si el `index.html` se abre por `file://` y hace `fetch()` de un JSON local,
el navegador lo bloquea por CORS. Solución sin instalar nada: `python3 -m http.server` en la
carpeta y abrir `localhost:8000`.

### Trampa crítica de GitHub Actions

**En un repositorio público, los workflows programados se desactivan automáticamente tras 60
días sin actividad en el repositorio.** Este proyecto está inactivo once meses al año, así
que sin corregirlo el sistema se apaga solo en otoño y llega muerto a julio. La
documentación de GitHub enuncia la regla solo para repos públicos y guarda silencio sobre
los privados: **no dar por resuelto el problema haciendo el repo privado.** `[VERIFICAR]`

Mitigación obligatoria: un paso de *keepalive* que escriba un fichero marcador con fecha y
haga commit sobre la rama por defecto cada pocas semanas. Existe la acción
`efrecon/gh-action-keepalive`, que hace exactamente eso a los 41 días de inactividad.

Además, `on: schedule` está documentado como "best effort": sin garantía de puntualidad y
**sin ningún aviso si deja de dispararse**. De ahí la sección 9.

---

## 7. Componentes

### 7.1 Colector A — BOA

Frecuencia: cada hora entre las 08:00 y las 20:00. En ventana crítica (1 jul – 30 sep), cada
30 minutos. La frecuencia **no** es para detectarlo antes (el BOA sale a las 00:15 y los
plazos se cuentan en días), sino para cubrir boletines extraordinarios.

**Nota (Fase 3):** el backtest 2011-2026 muestra convocatorias publicadas en meses muy
distintos (febrero, marzo, mayo, junio, julio, agosto, noviembre, diciembre — ver sección
3). La franja jul-sep con sondeo cada 30 min sigue siendo razonable porque es donde se ha
concentrado la publicación en los últimos años, pero **no excluye nada el resto del año**:
el colector corre cada hora los 12 meses, así que el recall no depende de esta franja. Si se
quiere revisar, la opción más simple es quitar la distinción y sondear cada hora todo el año
de forma uniforme, sin ninguna ventana "crítica" diferenciada — la ganancia de los 30 min en
jul-sep frente a un festivo/boletín extraordinario es marginal y ya no está respaldada por
los datos con la misma fuerza que antes.

Orden de preferencia del canal, revisado por el riesgo de `robots.txt`:

1. **Suscripción gratuita por correo al sumario, leída por IMAP.** Canal ofrecido por el
   propio BOA. Sin scraping, sin conflicto con `robots.txt`, inmune a cambios de la web.
   Pendiente de alta manual por el usuario — no depende del código. `[VERIFICAR]` (no
   automatizable de comprobar; requiere que el usuario confirme que se ha suscrito).
2. **RSS del boletín diario. CONFIRMADO Y VALIDADO** — canal principal recomendado y el que
   implementa `boa_monitor/rss.py`:
   ```
   https://www.boa.aragon.es/cgi-bin/EBOA/BRSCGI
     ?CMD=RSSLST&DOCS=1-200&BASE=BOLE&SEC=BOARSS&SEPARADOR=&PUBL-C=AAAAMMDD
   ```
3. **Sumario HTML vía BRSCGI**, como último recurso. **CONFIRMADO** (usado para verificar la
   inclusión de la Sección I en el RSS, ver sección 3):
   ```
   https://www.boa.aragon.es/cgi-bin/EBOA/BRSCGI
     ?CMD=VERLST&DOCS=1-200&BASE=BOLE&SEC=FIRMA&SEPARADOR=&PUBL=AAAAMMDD
   ```
   Documento individual: `CMD=VEROBJ&MLKOB=<id>`. La parte del `MLKOB` no se ha probado
   todavía. `[VERIFICAR]`

**`robots.txt` verificado (Fase 0, 17/08/2026): no bloquea nada de lo que usamos.** Solo
contiene bajas puntuales de documentos concretos por `MLKOB` (retiradas legales caso a caso,
no una política general) y una entrada residual sobre otra base (`BZHT`) sin relación. El
canal 2 (RSS) es la opción principal sin reservas.

Requisitos: reintentos con backoff, `User-Agent` identificable con contacto, una petición por
hora como máximo, caché local de todo lo descargado.

**No usar Playwright ni un navegador headless.** Funcionaría, pero no autoriza nada: solo
hace más difícil identificar al cliente. A cambio añade ~300 MB de Chromium por ejecución,
arranques lentos y fragilidad. Una petición HTTP simple basta, como demuestra la descarga
manual del feed. Si algún día bloquean por IP, pasar a la opción 1.

### 7.1.1 Parseo del RSS: trampas verificadas

Las cuatro comprobadas sobre el fichero real del 6/08/2026:

1. **Codificación ISO-8859-1**, declarada en la cabecera XML. Leerlo como UTF-8 destruye las
   tildes y "obtención" deja de coincidir con el patrón. Decodificar explícitamente.
2. **`pubDate` es incorrecto.** Para el boletín del 6/08/26 el campo contiene ` 8/06/26`:
   día y mes intercambiados y con espacio inicial. **No usarlo jamás.** La fecha fiable está
   en el prefijo del título (`BOA 6/08/26 - …`) o en el parámetro `PUBL-C` de la consulta.
3. **Los títulos contienen saltos de línea internos.** Normalizar espacios en blanco antes
   de aplicar cualquier expresión regular, o los patrones multipalabra fallarán de forma
   intermitente.
4. **Los enlaces son relativos** y tienen la forma `CMD=VERDOC&BASE=BOLE&DOCN=007960400`. Ese
   `DOCN` es un identificador numérico limpio: **usarlo como clave de deduplicación**, no un
   hash del título. Anteponer `https://www.boa.aragon.es` al enlace.

**Estructura del item: solo `title`, `link` y `pubDate`.** No hay categoría, sección, órgano
ni departamento estructurados. Ver 7.3.

**Completitud del feed: VERIFICADA.** El RSS es el sumario íntegro, no un subconjunto. Tres
comprobaciones independientes sobre el 6/08/2026:

1. Los 26 documentos ocupan los `DOCN` 7960400 a 7960425: secuencia continua, sin huecos ni
   duplicados.
2. Las órdenes van de la 1137 a la 1148 sin faltar ninguna (`PJC/1137`–`PJC/1143`,
   `VFL/1144`, `ECU/1145`–`ECU/1148`).
3. **Decisiva**: el csv oficial de la ORDEN ECU/1145/2026 es `BOA20260806015`, o sea el
   documento nº 15 del boletín, y en el feed ocupa exactamente la posición 15. La
   correspondencia es 1 a 1, luego el feed arranca en el documento 001.

Los 26 documentos mezclan cuatro tipos de acto (12 órdenes, 8 anuncios, 5 resoluciones, 1
decreto comarcal), lo que descarta que `SEC=BOARSS` sea un filtro por sección.

**Dos salvedades.** Las pruebas anclan el principio del bloque, no el final: nada demuestra
formalmente que no hubiera un documento 027 truncado, aunque es improbable porque se pidió
`DOCS=1-200` y devolvió 26. Y ese día no había documentos de la sección I, así que no queda
probado que el feed la incluya. Prueba residual de dos minutos: descargar el RSS del
**4/08/2026** (BOA nº 149), cuyo sumario empieza con un documento de sección I con csv
`BOA20260804001`, y comprobar que aparece como primer item. Poco relevante para este
proyecto, porque la POT es una ORDEN de la sección III y el feed las lleva. `[VERIFICAR]`

### 7.2 Colector B — educa.aragon.es — IMPLEMENTADA (Fase 4)

Frecuencia: 10:00, 13:00 y 17:00 Europe/Madrid, L-V. Aquí sí actualizan personas en horario
de oficina. Implementado en `boa_monitor/educa.py` y `.github/workflows/colector-educa.yml`.

**Página vigilada, localizada navegando desde la home de educa.aragon.es** (`Formación
Profesional` → enlace "Pruebas de Obtención de Títulos de FP" dentro del bloque de
calendario de convocatorias):

```
https://educa.aragon.es/-/formacion-profesional/calendario/pots
```

El 17/08/2026 esta página tenía exactamente 4 PDF: la orden de convocatoria ("Convocatoria
actual"), el Anexo I (solicitud de inscripción), el Anexo II (títulos convocados y centros de
examen) y el Anexo III (calendario de la convocatoria). **Esto confirma la sospecha de la
Fase 3**: el calendario, las sedes y los títulos convocados no van al BOA — van aquí, como
anexos de esta misma página. No se ha visto todavía una lista de admitidos/excluidos en esta
página porque la convocatoria 2026 está a mitad de ciclo (solicitudes abiertas, examen en
noviembre); si aparece más adelante, el diseño de diff por URL (no por texto) la detectará
igual sin cambios de código.

Método: extraer el **conjunto de enlaces a PDF** de las páginas vigiladas y compararlo con
el guardado en la ejecución anterior (`data/estado_educa.json`). No hashear la página entera:
los elementos volátiles (fechas, banners, identificadores de sesión) generan falsas alarmas
diarias, y un hash solo dice "algo ha cambiado", mientras que la diferencia de conjuntos dice
**qué** documento es nuevo y cómo se llama. **La clave de comparación es la URL completa del
PDF, no el texto del enlace**: el gestor documental (Liferay) incrusta un identificador de
versión en la propia URL, así que si el Departamento sustituye un PDF por una corrección
manteniendo el mismo texto de enlace ("Convocatoria actual."), la URL cambia y el diff lo
detecta como documento nuevo igualmente — comprobado en
`tests/test_educa.py::test_documento_nuevo_se_detecta_por_url_no_por_texto`.

Los documentos nuevos se registran en `data/documentos_educa.json` (mismo espíritu que
`convocatorias.json` de Colector A, pero sin cubos ni reglas — aquí todo lo nuevo se registra,
no hay filtro de relevancia porque la página entera ya está acotada al tema).

**Primera ejecución de una página nueva**: no hay "estado anterior" con el que comparar, así
que todo lo que hay en ese momento cuenta como "nuevo para el sistema" — igual que el primer
día de Colector A marca como relevante lo que encuentra ese día. No es un error, es la línea
base.

**Pendiente de verificar en producción** (ver 0.5): el diseño se ha probado con la foto real
de la página tal como está el 17/08/2026 y con estados sintéticos en los tests, pero no se ha
observado todavía un ciclo completo (aparición real de una lista de admitidos, por ejemplo)
para confirmar en vivo que el diff los captura.

### 7.3 Filtro determinista

Normalizar a minúsculas y sin acentos. Dispara si se cumple **cualquiera**:

- `"obtencion directa"` y `"titulo"`
- `"pruebas"` y `"formacion profesional"` y (`"tecnico"` o `"tecnico superior"`)
- órgano contiene `"educacion"` y el texto contiene `"prueba"`
- `"modulos profesionales"` y (`"convocan"` o `"convocatoria"`)

Ampliar si el backtest revela fallos. **Nunca reducir para mejorar la precisión.**

**No existe un campo de órgano.** El RSS no lo trae. El órgano vive dentro del texto del
título ("del Director General de Justicia", "del Instituto Aragonés de Gestión Ambiental").
El prefijo del código de orden (`ECU`, `PJC`, `VFL`) es lo más parecido, pero solo lo llevan
las ÓRDENES —las RESOLUCIONES y los ANUNCIOS no tienen código— y además cambia con las
reorganizaciones. **Úsalo como señal auxiliar, nunca como eje principal del filtro.**

Resultado medido sobre el 6/08/2026: R1 y R2 capturan la convocatoria; la regla de órgano
añade 3 falsos positivos (otras órdenes ECU). 4 marcados de 26. Precisión del 25 %,
perfectamente aceptable.

### Uso acotado del LLM sobre los ambiguos

Permitido bajo una restricción que lo hace seguro: **el LLM nunca puede descartar.**

| Cubo | Criterio | Destino |
|---|---|---|
| Seguro | Dispara R1 o R2 | Alerta inmediata, sin pasar por el modelo |
| Ambiguo | Solo reglas débiles (órgano) | El LLM clasifica. Si dice sí → alerta. Si dice no → **resumen semanal de revisión, no se borra** |
| Descartado | No dispara ninguna regla | Se archiva |

El modelo solo mueve documentos entre "avísame ya" y "míralo el domingo", nunca entre
"existe" y "no existe". Decidir si compensa **después** del backtest: con 4 marcados de 26,
puede que el ruido sea tan bajo que el LLM sobre en esta etapa.

### 7.4 Extracción con LLM — implementada y verificada contra la API real el 18/08/2026

`boa_monitor/extraccion.py`. Punto de entrada: `python -m boa_monitor.extraccion <ruta.pdf>`.

**Entrada: las páginas del anexo como imágenes, no como texto extraído.** Las tablas del BOA
en PDF se desordenan al pasarlas a texto plano y el modelo alucinará códigos de módulo.
`pdf_a_imagenes()` usa PyMuPDF para renderizar cada página a PNG — única dependencia de
runtime del proyecto fuera de la stdlib (ver sección 6 y `requirements.txt`), porque no hay
forma de rasterizar un PDF sin una librería dedicada.

Coste: 5-20 llamadas al año. **El tier gratuito es irrelevante como criterio de elección;
escoger por calidad de extracción.** Si se usa uno gratuito, la capa de acceso debe ser
compatible con la API de OpenAI y tener un proveedor alternativo configurado: los
proveedores retiran modelos gratuitos sin previo aviso.

**Proveedores elegidos, con fallback automático en este orden (verificado el 18/08/2026):**

1. **Gemini** (`gemini-flash-latest` — alias que Google mantiene apuntando siempre al Flash
   vigente, en vez de fijar un número de versión que quedará obsoleto). Endpoint compatible
   con OpenAI: `https://generativelanguage.googleapis.com/v1beta/openai/`. Clave en
   `GEMINI_API_KEY`.
2. **Mistral** (`mistral-large-latest`, incluye capacidad de visión —heredera de Pixtral— en
   el tier gratuito "Experiment"). Endpoint: `https://api.mistral.ai/v1`. Clave en
   `MISTRAL_API_KEY`.

Se descartó **Groq** como candidato pese a ser el más rápido: sus modelos de visión
gratuitos se han ido retirando durante 2026 (Llama 4 Maverick en febrero, Llama 4 Scout en
junio, sin sustituto de visión equivalente en el tier gratuito a día de hoy) — confirma en
vivo, siete meses después de escribirse, la advertencia de este mismo párrafo sobre
proveedores gratuitos. `[VERIFICAR]`: la disponibilidad de modelos cambia constantemente;
antes de depender de esto en producción, comprobar en la documentación de cada proveedor que
`gemini-flash-latest` y `mistral-large-latest` siguen existiendo y siguen soportando imagen +
JSON estricto.

Cada llamada se hace con `urllib` puro (mismo patrón que `rss.py`/`educa.py`), sin SDK de
ningún proveedor — la API de ambos es compatible con el formato de OpenAI (`chat/completions`
con `image_url` en base64 y `response_format: json_object`), así que no hace falta.

**Verificado contra las dos APIs reales el 18/08/2026** (ver la bitácora completa en la
sección 10): con el PDF real del Anexo III, Gemini devolvió `503 UNAVAILABLE` (sobrecarga
del lado de Google, no un fallo de configuración) y el fallback a Mistral extrajo
correctamente el plazo de inscripción real, dejando en `null` — sin inventar nada, regla 7 —
los campos que ese documento no trae. `tests/test_extraccion.py` cubre además el renderizado
de PDF y la lógica de fallback/validación con red simulada.

Salida JSON estricta, temperatura 0:

```json
{
  "anio": 2026,
  "codigo_orden": "ECU/1145/2026",
  "fecha_orden": "2026-07-21",
  "fecha_publicacion_boa": "2026-08-06",
  "numero_boa": 151,
  "plazo_inscripcion_inicio": null,
  "plazo_inscripcion_fin": null,
  "modulos_convocados": [
    {"codigo": null, "denominacion": null, "ciclo": null, "grado": null, "centro_examinador": null}
  ],
  "modulos_excluidos": [],
  "sedes": [],
  "url_solicitud": null,
  "campos_no_encontrados": []
}
```

### 7.5 Validación determinista

Antes de alertar:

- `plazo_fin > plazo_inicio > fecha_publicacion_boa`
- `plazo_fin - plazo_inicio` entre 5 y 40 días naturales
- `plazo_inicio - fecha_publicacion_boa` menor de 60 días — **corregido con datos reales
  (18/08/2026)**: la versión original decía "menor de 30 días", pero la convocatoria 2026
  real (BOA 6 de agosto, plazo del 10 al 17 de septiembre, ver sección 3) tiene 35 días de
  hueco y hubiera disparado la validación como "no fiable" sin motivo. Mismo espíritu que la
  ventana crítica de 7.1: no estrechar un umbral por debajo de lo que ya se ha observado
  ocurrir de verdad.
- todo módulo tiene código **y** denominación
- `codigo_orden` casa con `[A-Z]{2,4}/\d+/\d{4}`

Si alguna falla: **alertar igualmente**, marcando el registro como no fiable. Nunca silenciar
por fallo de validación.

### 7.6 Cruce alumno-módulo — implementada y verificada el 18/08/2026

`boa_monitor/cruce.py`. Punto de entrada:
`python -m boa_monitor.cruce <alumnos.xlsx> <convocatoria.json>`.

Justificación: 50-100 alumnos × 2-6 módulos pendientes = 150-500 inscripciones al año. El
objetivo no es ahorrar tiempo, sino evitar errores de transcripción de códigos, que son
irreversibles: un módulo mal solicitado equivale a un año perdido.

**Corrección importante de diseño, con datos reales (Anexo II real de 2026 + lectura del
Anexo I): la convocatoria NO cierra módulo a módulo, cierra a nivel de título/ciclo.** El
Anexo II ("Títulos convocados y centros de realización de las pruebas") solo trae código de
título (p.ej. `HOT201`) y centro examinador — nunca código de módulo. El propio formulario
de inscripción (Anexo I) trae la tabla "Código módulo / Módulos profesionales" **en blanco**
para que cada alumno declare libremente cuáles necesita de su título, y su declaración
responsable dice literalmente "no estoy matriculado/a... en ninguno de los módulos
profesionales del mismo Ciclo Formativo". Es decir: si el título está convocado, todos los
módulos pendientes de ese título son examinables en el centro asignado; no existe una lista
de módulos convocados por separado. El diseño original de este documento asumía cruce a
nivel de módulo — corregido tras comprobarlo contra los documentos reales.

Entrada dinámica por Excel (`.xlsx`, vía `openpyxl` — única forma de leerlo sin librería,
ver sección 6), **fuera del repositorio**. Esquema:

```csv
alumno_id,nombre,ciclo,grado,titulo_codigo_oficial,modulo_codigo,modulo_denominacion,estado
A001,Ana Pérez,COCI,medio,HOT201,0026,Procesos de preelaboración,pendiente
```

- `estado`: `pendiente` | `superado` | `convalidado` | `solicitada_convalidacion`. Solo
  `pendiente` entra en la salida del cruce.
- `ciclo` es el código o nombre **interno** del centro (el que ya use el usuario en su
  gestión diaria) — el cruce nunca lo usa, es solo para que el usuario identifique al alumno
  de un vistazo. Decisión del usuario (18/08/2026): mantener las dos columnas en paralelo en
  vez de sustituir una por otra, aunque la interna quede sin uso en el código.
- `titulo_codigo_oficial` es el código oficial de Aragón (`HOT201`, `HOT203`... ver Anexo II)
  — **esta es la clave real del cruce**, no `modulo_codigo`.
- `modulo_codigo`/`modulo_denominacion` se conservan porque son lo que el alumno declarará
  en el Anexo I, pero no participan en si está convocado.

Aquí, y solo aquí, se aplica el recorte a la familia de Hostelería y Turismo — de forma
implícita: el Excel del usuario ya viene acotado a sus propios alumnos, así que basta con
cruzar cada `titulo_codigo_oficial` contra la convocatoria completa. **Títulos de hostelería
confirmados con el Anexo II real de 2026** (resuelve el pendiente `[VERIFICAR]` de la
versión anterior de este documento):

| Código | Título | Grado | Centro examinador 2026 |
|---|---|---|---|
| `HOT201` | Técnico/a en Cocina y Gastronomía | Medio | CPIFP San Lorenzo |
| `HOT203` | Técnico/a en Servicios de Restauración | Medio | CPIFP San Lorenzo |
| `HOT304` | Técnico/a Superior en Dirección de Servicios de Restauración | Superior | CPIFP Escuela de Hostelería y Turismo de Teruel |
| `HOT305` | Técnico/a Superior en Dirección de Cocina | Superior | CPIFP Escuela de Hostelería y Turismo de Teruel |

También existen `HOT301`-`HOT303` (Agencias de Viajes, Alojamientos Turísticos, Guía
Turística) en el mismo bloque `HOT`, pero son de la rama de turismo, no de restauración —
`[VERIFICAR]` si el centro del usuario los imparte también.

Salida por alumno (`ResultadoCruce`): módulo pendiente, si el título está convocado este
año, código exacto a consignar, centro examinador, fecha límite (el `plazo_inscripcion_fin`
de la Fase 5) y una `advertencia` si el grado declarado por el alumno no casa con el de la
convocatoria para ese código — no bloquea el resultado (regla 1: maximizar recall), pero
marca el registro para revisión humana, mismo espíritu que 7.5.

**Verificado de extremo a extremo el 18/08/2026** con un Excel de alumnos inventados
(`fixtures/cruce/alumnos_ejemplo.xlsx` — nombres y situaciones ficticias, no son datos
reales) contra la extracción real del Anexo II: separó correctamente los módulos pendientes
de los superados/convalidados, marcó como convocados dos módulos distintos de un mismo
título ya convocado (confirma que la clave es el título, no el módulo), detectó un código de
título inventado que no existe en la convocatoria real, y disparó el aviso de grado
incoherente para un caso fabricado a propósito. 6 tests, todos deterministas y offline.

---

## 8. Datos personales

Un fichero con 50-100 alumnos identificados y su expediente académico es un tratamiento de
datos personales sujeto al RGPD. Reglas:

- El CSV de alumnos **nunca** se versiona en un repositorio público.
- GitHub Pages publica solo el estado de detección y los datos de la convocatoria, que son
  públicos por definición. Nunca listados de alumnos.
- Si se quiere el cruce automatizado, o el repositorio entero es privado o el cruce se
  ejecuta en local.
- El `.gitignore` debe cubrir el directorio de datos de alumnos desde el primer commit.

---

## 9. Verificación continua: tres pruebas distintas

Son tres fallos diferentes y necesitan tres comprobaciones diferentes. No mezclarlas.

### 9.1 Prueba de vida — ¿se ha ejecutado?

El workflow escribe en cada ejecución un fichero de estado con la marca de tiempo y el
número de documentos recogidos, y lo commitea. Esto además cuenta como actividad del repo y
ayuda con el problema de los 60 días.

Punto ciego: si el workflow nunca llega a ejecutarse, nadie escribe y nadie avisa. Se
resuelve con un observador fuera del workflow, y la arquitectura híbrida ya lo da gratis:
**el `index.html` local, al abrirse, lee la marca de tiempo del último `git pull` y muestra
un aviso en rojo si tiene más de tres días.** Complementar con recordatorios de calendario
para el 25 de julio y el 10 de septiembre.

### 9.2 Prueba de regresión — ¿mi código sigue acertando?

Guardar en el repo los ficheros RSS de una decena de días con positivo conocido, como
fixtures, y pasarles el filtro semanalmente. Verifica que un positivo sigue siendo un
positivo tras cualquier cambio en el código. Offline, instantánea, sin tocar el servidor.

### 9.3 Prueba de contrato — ¿la fuente sigue igual?

Descargar en vivo el RSS de una fecha pasada conocida y comprobar que sigue devolviendo
`<item>`, los tres campos, la codificación ISO-8859-1 y el número esperado de documentos.
Detecta cambios en el BOA, que es un fallo distinto del anterior: 9.2 comprueba tu código,
9.3 comprueba la fuente.

### 9.4 Alerta estacional

Si llega el 10 de septiembre sin convocatoria detectada, avisar con el mensaje "no he
detectado nada, revísalo a mano". La ausencia de señal es señal.

**Nota (Fase 3):** el backtest muestra convocatorias históricas publicadas hasta noviembre y
diciembre (2018, 2019). Si el patrón revirtiera a esas fechas, esta alerta dispararía en
falso el 10 de septiembre. Es un coste aceptable (rule 1: falso positivo = revisión de 10
segundos) y el mecanismo ya falla de forma segura — abre un issue para revisión humana, no
detiene nada ni oculta el resultado real cuando llegue.

---

## 10. Fases de trabajo

| Fase | Contenido | Puerta | Estado |
|---|---|---|---|
| 0 | Verificar `robots.txt`, la URL del RSS y dar de alta la suscripción por correo | — | robots.txt y RSS ✅. Suscripción por correo pendiente del usuario (no automatizable). |
| 1 | Colector A + filtro determinista + caché local | — | ✅ `boa_monitor/rss.py`, `filtro.py`, `cache.py`, `main.py`, 37 tests |
| 2 | **Descarga y caché de los sumarios 2018-2026** | — | ✅ reinterpretada, ver nota abajo |
| 3 | **Backtest sobre esa caché** | **Bloqueante** | ✅ **recall 100% (12/12), precisión 75%** — puerta superada |
| 4 | Colector B | — | ✅ `boa_monitor/educa.py`, 5 tests, ver 7.2 |
| 5 | Extracción con LLM + validación | — | ✅ completa y verificada contra las APIs reales (18/08/2026) |
| 6 | Cruce alumno-módulo | — | ✅ completa y verificada contra la convocatoria real (18/08/2026) |
| 7 | Alertas, canario externo y keepalive | — | ✅ adelantada junto con la Fase 1 (workflows `contrato.yml`, `alerta_estacional.yml`, `keepalive.yml`) |

### Fase 2: caché histórica — reinterpretada con datos reales

El plan original pedía descargar el sumario RSS de cada día entre 2018 y 2026 (~2000
peticiones). Durante la Fase 3 se descubrió que el propio BOA expone un buscador con salida
JSON (`SEC=OPENDATABOAJSONELI`, ver sección 3) que permite localizar directamente los
documentos relevantes por título, órgano y rango de fechas, sin recorrer boletín a boletín.
Se usó ese buscador para construir el conjunto de verdad y, a partir de las fechas exactas
que devolvió, se descargó y cacheó el **RSS real** de esos 12 días concretos (no un muestreo
sintético) en `fixtures/regresion/*.rss` — el mismo fichero sirve a la vez de fixture de
regresión (9.2) y de materia prima del backtest (9.3). Esto cumple el objetivo de la fase
(backtest reproducible y offline) sin las ~2000 peticiones al servidor. El buscador JSON no
es un canal documentado ni estable — no usarlo en producción, solo si hace falta ampliar el
conjunto de verdad más adelante.

### Fase 3: backtest — completada

Conjunto de verdad para 2018-2026, localizado con el buscador anterior y verificado con una
segunda búsqueda con términos distintos: **9 órdenes de convocatoria**, una por cada año
cubierto entre 2018 y 2026 salvo 2020 (ese ciclo lo cubrió la orden firmada en noviembre de
2019 — ver el hallazgo del posible hueco de 2020 en la sección 3; 2018 tuvo dos, una para el
propio 2018 y otra en octubre para el ciclo 2019) + **3 correcciones de errores** (2018, 2022,
2025) = **12 documentos**, detalle completo en
`fixtures/regresion/positivos_esperados.json`. Menos que el objetivo
original de 30-40, pero ese número era una estimación a priori; la búsqueda exhaustiva no
encontró ninguna ampliación de plazo, lista de admitidos, calendario, sede ni tribunal
publicados en el BOA en esos 9 años (ver el hallazgo de la sección 3) — el conjunto de verdad
real es este.

- **Recall = 100 % (12/12).** Verificado en `tests/test_backtest.py` y
  `tests/test_regresion.py`. Puerta de la Fase 3 superada.
- **Precisión agregada = 75 %** (16 marcados de 439 documentos en los 12 boletines reales, 12
  positivos). Los 4 falsos positivos disparan solo R3 (auxiliar) y caen en "ambiguo", nunca en
  "seguro" — verificado explícitamente en `test_los_falsos_positivos_nunca_caen_en_el_cubo_seguro`.
- **Prueba de robustez**: además de alterar sintéticamente la redacción del título de 2026
  (`tests/test_filtro.py`), se verificó contra la redacción real de 2018 (15 años más
  antigua, con vocabulario ligeramente distinto) y disparó igual.

Ejecutar `python -m boa_monitor.backtest` para ver el informe completo.

### Fase 4: Colector B — completada

Ver el detalle completo en 7.2. Resumen: localizada la página
`https://educa.aragon.es/-/formacion-profesional/calendario/pots` navegando desde la home
pública (Formación Profesional → "Pruebas de Obtención de Títulos de FP"), que resultó ser
exactamente donde vive el calendario, las sedes y los títulos convocados que la Fase 3 no
encontró en el BOA. Implementado el diff de enlaces PDF por URL (no por texto, para detectar
sustituciones) en `boa_monitor/educa.py`, con 5 tests contra un fixture HTML real y estados
sintéticos que simulan un "día anterior". Workflow `colector-educa.yml` a las 10:00, 13:00 y
17:00 Europe/Madrid, L-V.

### Fase 5: extracción con LLM — completada y verificada

Ver el detalle completo en 7.4-7.5. Resumen: usando uno de los cuatro PDF que ya había
capturado el Colector B (`documentos_educa.json`), se descargó el Anexo III (calendario de
la convocatoria 2026) y se leyó a mano para resolver el pendiente urgente de la sección 11 —
**plazo de inscripción: del 10 al 17 de septiembre de 2026**, calendario completo hasta el 27
de noviembre, ver sección 3. Ese mismo PDF real se guardó como fixture
(`fixtures/educa/anexo_iii_calendario_pot_2026.pdf`) y sirvió para construir y probar
`boa_monitor/extraccion.py`: renderizado de PDF a imagen con PyMuPDF, prompt con el esquema
JSON de 7.4, llamada por `urllib` a un proveedor compatible con OpenAI, y fallback automático
a un segundo proveedor si el primero falla. Elegidos Gemini y Mistral (los dos con tier
gratuito y soporte de imagen); se investigó y descartó Groq porque sus modelos de visión
gratuitos llevan retirándose durante todo 2026. La validación determinista de 7.5 se probó
contra los datos reales de 2026 y **reveló que el umbral original de 30 días entre
publicación e inicio del plazo era demasiado estricto** (el caso real tiene 35): corregido a
60 con el mismo criterio que ya se aplicó a la ventana crítica de 7.1 — no estrechar por
debajo de lo observado. 9 tests nuevos, todos deterministas y offline (red simulada con
monkeypatch, igual que `test_educa.py`).

**Verificación contra las APIs reales, el mismo 18/08/2026**: con las claves dadas de alta
por el usuario (`GEMINI_API_KEY`, `MISTRAL_API_KEY`) se ejecutó
`python -m boa_monitor.extraccion` contra el propio Anexo III real. Gemini respondió
`503 UNAVAILABLE` ("This model is currently experiencing high demand"): confirmado
inspeccionando el cuerpo de la respuesta que es sobrecarga temporal del servicio, no un
problema de clave, endpoint o nombre de modelo. El fallback a Mistral se disparó como estaba
diseñado y devolvió una extracción correcta: `plazo_inscripcion_inicio`/`fin` exactos
(2026-09-10/17), `modulos_convocados` vacío (correcto, el Anexo III no lista módulos) y los
ocho campos que este documento no trae listados en `campos_no_encontrados` en vez de
inventados. De paso se corrigió un aviso de deprecación de PyMuPDF (`import fitz` →
`import pymupdf`) que salió en la primera ejecución. La Fase 5 queda verificada de extremo a
extremo con un documento y unas claves reales, no solo con red simulada.

**Extracción de los 3 PDF restantes y bug de codificación, mismo día**: se extrajeron
también el Anexo I (formulario de inscripción, sin datos estructurados de interés — es un
formulario en blanco) y el Anexo II (**110 títulos convocados** con código oficial,
denominación, ciclo, grado y centro examinador, más el listado de sedes por localidad — la
extracción más grande probada hasta ahora, 7 páginas). Con 7 páginas a resolución
`zoom=2.0` el payload ronda los 2,3 MB en base64: el timeout original de 120 s se quedaba
corto y Mistral lo agotó en el primer intento. Se subió el timeout a 240 s y se añadió
reintento con backoff distinguiendo errores permanentes (4xx, p.ej. clave inválida — no se
reintentan) de temporales (5xx, como el 503 de Gemini — sí se reintentan), mismo patrón que
`rss.py`/`educa.py`. **Bug real encontrado y corregido**: en Windows, `print()` en el bloque
`__main__` usaba la codificación de la consola (cp1252) en vez de UTF-8 tanto en pantalla
como redirigido a fichero, corrompiendo los acentos del JSON de salida
(`Técnico` → `T\xe9cnico`). Corregido con `sys.stdout.reconfigure(encoding="utf-8")` al
principio del bloque `__main__`, y verificado con una segunda ejecución que los bytes del
fichero de salida son UTF-8 válido.

### Fase 6: cruce alumno-módulo — completada y verificada, con una corrección de diseño

Ver el detalle completo en 7.6. El usuario pidió crear un Excel de alumnos inventados para
poder probar y desarrollar la Fase 6 sin esperar a tener datos reales de alumnos (que nunca
saldrían del repositorio de todos modos, sección 8). Al construir el cruce contra los 110
títulos reales que acababa de devolver la extracción del Anexo II, se detectó que el diseño
original de este documento (comparar por `modulo_codigo`) no podía funcionar nunca: el Anexo
II solo trae códigos de título, no de módulo. Se leyó el Anexo I (formulario de inscripción)
para confirmar por qué — trae la tabla de módulos profesionales en blanco, de libre
declaración por el alumno, con una declaración responsable de que no está matriculado en
esos módulos "del mismo Ciclo Formativo" — y se confirmó: **la convocatoria cierra a nivel
de título, no de módulo**.

Consultado el usuario sobre cómo identificar el título de cada alumno en su Excel sin
comprometer el dato interno que ya usa el centro, decidió (18/08/2026): mantener la columna
`ciclo` interna tal cual (sin uso en el código, solo para que el usuario reconozca al alumno
de un vistazo) y añadir `titulo_codigo_oficial` como la clave real del cruce. `cruce.py` se
reescribió con esta clave y con un aviso (no bloqueante, regla 1) cuando el grado declarado
por el alumno no casa con el de la convocatoria para ese código — un error de transcripción
real que interesa detectar. Se regeneró el fixture de alumnos inventados
(`fixtures/cruce/alumnos_ejemplo.xlsx`) usando cuatro códigos de título reales de hostelería
(`HOT201`, `HOT203`, `HOT305`, y un `HOT999` inventado a propósito para probar el caso "no
convocado") y se verificó de extremo a extremo contra la extracción real del Anexo II: separó
bien pendientes de superados/convalidados, marcó como convocados dos módulos distintos de un
mismo título (confirmando que la clave es el título), detectó el título inexistente, y
disparó el aviso de grado incoherente en el caso fabricado para probarlo. 6 tests, todos
deterministas y offline. Este mismo trabajo resolvió de paso el pendiente `[VERIFICAR]` sobre
la lista definitiva de títulos de hostelería (sección 11): ahora hay códigos oficiales reales
confirmados.

---

## 11. Pendiente de verificar

Resueltos el 17 de agosto de 2026 (Fases 0, 3 y 4): la inclusión de la Sección I en el feed,
qué bloquea `robots.txt` (nada de lo que usamos), qué documentos derivados van al BOA y
cuáles a educa.aragon.es (con bastante peso a favor, aunque no concluyente al 100 %; ver
sección 3), y las páginas concretas que debe vigilar el Colector B (sección 7.2).

- [ ] Estabilidad del patrón `BRSCGI` para el sumario diario a largo plazo (solo se ha
      verificado en un punto en el tiempo).
- [ ] Si el feed cubre los boletines extraordinarios.
- [ ] Si la regla de los 60 días de GitHub Actions aplica a repos privados.
- [ ] Qué módulos excluye exactamente la ORDEN ECU/1145/2026 (¿FCT y Proyecto?).
- [x] ~~Si el anexo lista títulos concretos o cubre todos los ciclos ofertados en Aragón.~~
      **Resuelto el 18/08/2026**: el Anexo II lista 110 títulos con código, denominación,
      ciclo, grado y centro — parece cubrir todos los ciclos de FP ofertados en Aragón para
      esta convocatoria, no un subconjunto (ver sección 10, bitácora de la Fase 5).
- [ ] Confirmación definitiva de que las listas de admitidos/excluidos y la composición de
      tribunales de la POT se publican en algún sitio (no aparecían todavía en
      `educa.aragon.es/-/formacion-profesional/calendario/pots` el 17/08/2026, con la
      convocatoria a mitad de ciclo — puede que se publiquen más adelante en la misma página,
      o en otra no localizada aún).
- [x] ~~Lista definitiva de títulos de hostelería que prepara el centro.~~ **Resuelto el
      18/08/2026** con códigos oficiales reales del Anexo II: `HOT201`, `HOT203`, `HOT304`,
      `HOT305` (ver la tabla completa en 7.6). Queda una duda menor: `HOT301`-`HOT303`
      (Agencias de Viajes, Alojamientos Turísticos, Guía Turística) son del mismo bloque
      `HOT` pero de la rama de turismo — confirmar con el usuario si su centro también los
      imparte o si son ruido.
- [ ] Confirmar con documentación oficial la causa del posible hueco de 2020 (¿pandemia?).
- [ ] **Fiabilidad de Gemini como proveedor primario de la Fase 5.** Resuelto en parte el
      18/08/2026 (ver sección 10): la clave y el modelo `gemini-flash-latest` son correctos,
      pero la única llamada real hecha hasta ahora recibió `503 UNAVAILABLE` por sobrecarga
      del servicio. El fallback a Mistral cubrió el caso, así que el sistema no está en
      riesgo, pero falta ver si es un incidente puntual o si Gemini es poco fiable en
      producción — si se repite, valorar invertir el orden (Mistral primero).
- [ ] **Canal 1 de 7.1 (correo del BOA) sin construir, anotado el 18/08/2026 para retomar
      más adelante — ver el detalle completo en 0.5.** Dos tareas independientes: (1) alta de
      la suscripción gratuita en la web del BOA, manual, pendiente del usuario; (2) módulo
      `boa_monitor/correo.py` que la lea por IMAP como respaldo del RSS — sin empezar. No
      bloquea nada: el RSS (canal 2) es el canal validado en producción.

---

## 12. Qué no hacer

- No construir colectores para BOE ni boletines provinciales.
- No usar un LLM para decidir si un documento es relevante.
- No aplicar el filtro de hostelería en la fase de detección.
- No inventar URLs de API ni de feeds.
- No rellenar campos ausentes por inferencia.
- No optimizar la precisión del filtro a costa del recall.
- No pasar a la fase 4 sin superar el backtest.
- No meter una base de datos donde bastan ficheros versionados.
- No publicar datos de alumnos en GitHub Pages ni en un repo público.
- No confiar en un canario que se ejecuta dentro del workflow que vigila.
- No sustituir la suscripción manual gratuita al BOA por este sistema.

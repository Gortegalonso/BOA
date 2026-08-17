# CLAUDE.md — Vigilancia de las Pruebas de Obtención de Título (POT) de FP en Aragón

> Versión 2. Documento vivo. Todo lo marcado `[VERIFICAR]` no está confirmado y
> **no debe darse por bueno sin comprobarlo contra la fuente**.

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

Verificados el 17 de agosto de 2026.

- **Convocatoria 2026 ya publicada**: ORDEN ECU/1145/2026, de 21 de julio, BOA nº 151 de 6
  de agosto de 2026.
- **Convocatoria 2025**: ORDEN ECD/941/2025, de 24 de julio, BOA nº 148 de 4 de agosto.
- **Patrón temporal (n=2, débil)**: firma a finales de julio, publicación primeros días de
  agosto. Ventana crítica: **1 julio – 30 septiembre**.
- **El prefijo de la orden cambió de `ECD` a `ECU`** entre 2025 y 2026.
- **El BOA está disponible a las 00:15 h** el 99 % de los días, según su carta de servicios.
  Excepción explícita: **boletines extraordinarios**, a cualquier hora y cualquier día.
- **Publicación de lunes a viernes**, salvo festivos nacionales o autonómicos.
- **El BOA ofrece RSS diario y suscripción gratuita por correo** al sumario o a cualquier
  sección.
- **El feed RSS está confirmado y validado.** Descargado para el 6/08/2026: devuelve 26
  documentos y **contiene la ORDEN ECU/1145/2026** (item 14). Sirve como fuente primaria.
- **Volumen real: ~26 documentos al día**, unos 6.000 al año. (Una estimación anterior de
  15.000-20.000 era errónea.)
- **Prueba del filtro contra ese día real: 4 marcados de 26, 1 verdadero positivo.** La
  convocatoria dispara dos reglas independientes (R1 y R2), lo que da redundancia frente a
  cambios de redacción.
- **Licencia de los datos**: Creative Commons Attribution 4.0. Atribución obligatoria si se
  redistribuye contenido.
- **Requisito de acceso aplicable a estos alumnos**: matrícula previa en un ciclo formativo
  en centro sostenido con fondos públicos de Aragón, con al menos cinco módulos superados
  (art. 126.4 del Decreto 91/2024).

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

Orden de preferencia del canal, revisado por el riesgo de `robots.txt`:

1. **Suscripción gratuita por correo al sumario, leída por IMAP.** Canal ofrecido por el
   propio BOA. Sin scraping, sin conflicto con `robots.txt`, inmune a cambios de la web.
2. **RSS del boletín diario. CONFIRMADO Y VALIDADO** — canal principal recomendado:
   ```
   https://www.boa.aragon.es/cgi-bin/EBOA/BRSCGI
     ?CMD=RSSLST&DOCS=1-200&BASE=BOLE&SEC=BOARSS&SEPARADOR=&PUBL-C=AAAAMMDD
   ```
3. **Sumario HTML vía BRSCGI**, como último recurso:
   ```
   https://www.boa.aragon.es/cgi-bin/EBOA/BRSCGI
     ?CMD=VERLST&DOCS=1-200&BASE=BOLE&SEC=FIRMA&SEPARADOR=&PUBL=AAAAMMDD
   ```
   Documento individual: `CMD=VEROBJ&MLKOB=<id>`. `[VERIFICAR]`

**Aviso sobre `robots.txt`:** hay indicios de que `boa.aragon.es` desaconseja el acceso
automatizado, probablemente bajo `/cgi-bin/`. No es una prohibición legal (datos CC BY,
servicio público), pero sí un riesgo de bloqueo por IP, agravado porque los runners de
GitHub salen por rangos muy conocidos. **Leer el `robots.txt` antes de elegir el canal.** Si
solo bloquea otras rutas, el RSS vuelve a ser la opción 1. `[VERIFICAR]`

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

### 7.2 Colector B — educa.aragon.es

Frecuencia: 10:00, 13:00 y 17:00. Aquí sí actualizan personas en horario de oficina.

Método: extraer el **conjunto de enlaces a PDF** de las páginas vigiladas y compararlo con
el del día anterior. No hashear la página entera: los elementos volátiles (fechas, banners,
identificadores de sesión) generan falsas alarmas diarias, y un hash solo dice "algo ha
cambiado", mientras que la diferencia de conjuntos dice **qué** documento es nuevo y cómo se
llama.

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

### 7.4 Extracción con LLM

**Entrada: las páginas del anexo como imágenes, no como texto extraído.** Las tablas del BOA
en PDF se desordenan al pasarlas a texto plano y el modelo alucinará códigos de módulo.

Coste: 5-20 llamadas al año. **El tier gratuito es irrelevante como criterio de elección;
escoger por calidad de extracción.** Si se usa uno gratuito, la capa de acceso debe ser
compatible con la API de OpenAI y tener un proveedor alternativo configurado: los
proveedores retiran modelos gratuitos sin previo aviso.

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
- `plazo_inicio - fecha_publicacion_boa` menor de 30 días
- todo módulo tiene código **y** denominación
- `codigo_orden` casa con `[A-Z]{2,4}/\d+/\d{4}`

Si alguna falla: **alertar igualmente**, marcando el registro como no fiable. Nunca silenciar
por fallo de validación.

### 7.6 Cruce alumno-módulo

Justificación: 50-100 alumnos × 2-6 módulos pendientes = 150-500 inscripciones al año. El
objetivo no es ahorrar tiempo, sino evitar errores de transcripción de códigos, que son
irreversibles: un módulo mal solicitado equivale a un año perdido.

Entrada dinámica por CSV o Excel, **fuera del repositorio**. Esquema mínimo:

```csv
alumno_id,nombre,ciclo,grado,modulo_codigo,modulo_denominacion,estado
A001,,COCI,medio,0026,Procesos de preelaboración,pendiente
```

`estado`: `pendiente` | `superado` | `convalidado` | `solicitada_convalidacion`.
`alumno_id` es la clave; `nombre` es opcional y prescindible para el cruce.

Aquí, y solo aquí, se aplica el recorte a la familia de Hostelería y Turismo. Títulos de
interés, a confirmar con el usuario: Técnico en Cocina y Gastronomía, Técnico en Servicios
en Restauración, Técnico Superior en Dirección de Cocina, Técnico Superior en Dirección de
Servicios de Restauración. `[VERIFICAR]`

Salida por alumno: módulos pendientes, cuáles están convocados este año, cuáles no, código
exacto a consignar, centro examinador y fecha límite.

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

---

## 10. Fases de trabajo

| Fase | Contenido | Puerta |
|---|---|---|
| 0 | Verificar `robots.txt`, la URL del RSS y dar de alta la suscripción por correo | — |
| 1 | Colector A + filtro determinista + caché local | — |
| 2 | **Descarga y caché de los sumarios 2018-2026** | — |
| 3 | **Backtest sobre esa caché** | **Bloqueante** |
| 4 | Colector B | — |
| 5 | Extracción con LLM + validación | — |
| 6 | Cruce alumno-módulo | — |
| 7 | Alertas, canario externo y keepalive | — |

### Fase 2: caché histórica

Descargar una sola vez los sumarios de 2018 a 2026 y guardarlos en disco. Todo el desarrollo
y las repeticiones del backtest trabajan contra esa copia local. Motivo doble: no golpear
repetidamente el servidor del BOA durante el desarrollo, y hacer el backtest reproducible y
ejecutable sin red. Ritmo de descarga conservador, con pausa entre peticiones.

### Fase 3: backtest

Construir el **conjunto de verdad** localizando a mano, por cada año de 2018 a 2026: la
orden de convocatoria, sus correcciones de errores, ampliaciones de plazo y resoluciones
asociadas. Objetivo 30-40 documentos, no solo las 8-9 convocatorias principales: un `n`
mayor es lo que hace significativa la calibración.

- **Recall** = relevantes capturados / relevantes existentes. **Objetivo: 100 %.** Cualquier
  fallo obliga a ampliar el filtro y repetir.
- **Precisión** = relevantes / marcados. **Sin objetivo.** Un 2 % es aceptable.

**Prueba de robustez adicional**, porque con `n` pequeño el recall no basta: alterar
deliberadamente la redacción de los títulos históricos (quitar "directa", cambiar "pruebas"
por "prueba", cambiar el prefijo de la orden) y comprobar que el filtro sigue disparando. Un
filtro que acierta 9 de 9 solo con la redacción literal es frágil.

---

## 11. Pendiente de verificar

- [ ] Confirmar que el feed incluye la sección I: descargar el RSS del 4/08/2026 y comprobar
      que el documento `BOA20260804001` aparece como primer item. (La completitud general ya
      está verificada, ver 7.1.1.)
- [ ] `robots.txt` de `boa.aragon.es`: qué rutas bloquea exactamente.
- [ ] Estabilidad del patrón `BRSCGI` para el sumario diario.
- [ ] Si el feed cubre los boletines extraordinarios.
- [ ] Si la regla de los 60 días de GitHub Actions aplica a repos privados.
- [ ] Qué módulos excluye exactamente la ORDEN ECU/1145/2026 (¿FCT y Proyecto?).
- [ ] Si el anexo lista títulos concretos o cubre todos los ciclos ofertados en Aragón.
- [ ] **Plazo de inscripción de la convocatoria 2026 — urgente, publicada el 6 de agosto.**
- [ ] Qué documentos derivados van al BOA y cuáles solo a educa.aragon.es.
- [ ] Páginas concretas de educa.aragon.es que debe vigilar el colector B.
- [ ] Lista definitiva de títulos de hostelería que prepara el centro.

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

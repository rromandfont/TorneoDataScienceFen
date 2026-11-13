# Diccionario de datos · Base USD/CLP

Extraida de Bloomberg el **2026-10-07**. 66 series, 475.857 observaciones, 1990-01-01 a 2026-10-06.

Este documento describe **columna por columna** que contiene la base: que es, en que unidad esta, hasta donde llega y con que hay que tener cuidado.

## Como leer la base

Hay dos presentaciones del mismo contenido:

| archivo | forma | para que |
|---|---|---|
| `base_usdclp_<fecha>.parquet` y su `.csv` | formato largo: una fila por `(fecha, ticker, campo, valor)` | la version canonica, para programar |
| `base_usdclp.xlsx`, hoja `datos` | formato ancho: una fila por fecha, una columna por `ticker\|campo` | para mirar en planilla |

En la version ancha, el nombre de cada columna es el **ticker de Bloomberg**, un `|` y el **campo**. Por ejemplo `USDCLP Curncy|PX_LAST` es el cierre del dolar-peso. Los campos que aparecen son:

- `PX_LAST` — ultimo precio o valor de cierre
- `PX_OPEN` — precio de apertura
- `PX_HIGH` — precio maximo de la jornada
- `PX_LOW` — precio minimo de la jornada
- `YLD_YTM_MID` — tasa interna de retorno, punto medio
- `FECHA_RELEASE` — fecha en que el dato se publico

Para pasar de largo a ancho:

```python
import pandas as pd
largo = pd.read_parquet('base_usdclp_20261007.parquet')
ancha = largo.pivot_table(index='fecha', columns=['ticker', 'campo'], values='valor')
```

## La base viene en bruto

No tiene faltantes rellenados, no trae retornos ni transformaciones y no hay columnas derivadas. **Decidir como tratar los huecos y que variables usar es parte del ejercicio.** Las celdas vacias son informacion: significan que esa serie no tuvo dato ese dia, ya sea porque todavia no existia, porque su mercado estaba cerrado o porque se publica con menor frecuencia.

Las series no traen todas los mismos dias, porque cada mercado tiene su propio calendario.

### Que dias trae cada serie

Cada mercado tiene su propio calendario de feriados: hay dias en que Santiago no opera y Nueva York si, y al reves. Ademas las series macro son mensuales. El indice de fechas de la version ancha es la **union** de las fechas nativas de todas las series, sin recortar ni completar: por eso quedan celdas vacias, y por eso aparecen sabados y domingos, ya que la UF (`CHUF Index`) se publica todos los dias corridos. Cada valor esta en la fila de su propia fecha; lo que falta es decidir con que conjunto de fechas trabajar, y esa decision es de cada equipo.

### A que hora se observo cada valor

Cada serie cierra con la sesion de su propio mercado, a la hora de esa plaza. **Para este challenge no tienen que preocuparse de eso:** asuman que el modelo corre en produccion al cierre de cada sesion, de modo que los valores de cierre de una misma fecha estan todos disponibles al momento de decidir. Usen los cierres tal como vienen. La columna `plaza_y_hora_cierre_declarada` de `diccionario_datos.csv` deja constancia de la plaza de cada serie, por si la necesitan para interpretar un resultado.

En las tablas de mas abajo, la columna **vs USD/CLP** compara el numero de observaciones de esa serie contra las jornadas en que cotiza el USD/CLP dentro del mismo tramo de fechas. Sirve para detectar series con huecos. Puede pasar de 100%: significa que la serie tiene datos en dias en que el USD/CLP no cotiza, ya sea porque se publica todos los dias calendario o porque su mercado abre en feriados chilenos.

## Que revisar antes de modelar

La base no viene depurada, y varias de sus caracteristicas pueden arruinar un modelo en silencio: no producen un error, producen un resultado que parece bueno y no lo es. La lista siguiente no trae respuestas, sino las preguntas que conviene responder con los datos a la vista. Contestarlas es parte del ejercicio.

1. **¿A que jornada corresponde el dolar observado?** Es un dato publicado, no una cotizacion en tiempo real. Compara `CLFXDOOB Index` contra el spot del mismo dia y contra el del dia anterior, y saca tu conclusion antes de construir cualquier retorno con el.
2. **¿Desde cuando cada serie mide lo que crees que mide?** El USD/CLP cubre mas de tres decadas, y el regimen cambiario de Chile no fue el mismo todo ese tiempo. Grafica el nivel y la variacion diaria por decada antes de elegir tu ventana de entrenamiento. Lo mismo aplica a las tasas locales y a las monedas de la region.
3. **¿Las columnas de precios intradia tienen contenido?** Si vas a usar las convenciones de apertura o promedio, verifica primero en que parte de la muestra `PX_OPEN`, `PX_HIGH` y `PX_LOW` aportan informacion distinta del cierre.
4. **¿Hay quiebres de unidad?** Algunas series cambian de definicion o de unidad monetaria a lo largo del periodo. Un retorno calculado a traves de un quiebre no significa nada. Graficar el nivel completo de cada serie los deja en evidencia.
5. **¿Que hago con los huecos?** Las celdas vacias tienen causas distintas: la serie aun no existia, su mercado estaba cerrado ese dia, o se publica con menor frecuencia. Cada causa pide un tratamiento distinto, y rellenar hacia adelante sin pensarlo fabrica datos rancios que el modelo tomara por nuevos.
6. **¿El dato estaba disponible cuando lo uso?** Para las series macro, la fecha de la fila es el mes al que se refiere el dato, no el dia en que se publico. Para eso estan las columnas `|FECHA_RELEASE`.

## Bloques

| bloque | series | contenido |
|---|---|---|
| `objetivo` | 2 | Objetivo y precios de ejecucion |
| `carry_cl` | 18 | Carry y tasas locales |
| `tasas_us` | 6 | Tasas externas |
| `commodities` | 8 | Cobre y commodities |
| `dolar` | 6 | Dolar global |
| `fx_em` | 6 | FX regional y emergente |
| `riesgo` | 6 | Riesgo y renta variable |
| `vol_clp` | 2 | Volatilidad implicita del peso |
| `cl_soberano` | 2 | Soberano chileno |
| `flujos_cl` | 5 | Flujos y posicionamiento cambiario |
| `macro_cl` | 5 | Macro chilena (point-in-time) |

---

## Objetivo y precios de ejecucion

### `USDCLP Curncy`

Tipo de cambio dolar-peso, la serie que hay que predecir.

- **Unidad:** CLP por USD
- **Frecuencia:** diaria
- **Cierre declarado:** cierre del mercado formal local (PRICING_SOURCE: Regional BGN onshore)

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `USDCLP Curncy\|PX_OPEN` | 9.294 | 1990-01-01 | 2026-10-06 | 100% | 295,18 | 553,40 | 1.032 | 968,22 |
| `USDCLP Curncy\|PX_HIGH` | 9.294 | 1990-01-01 | 2026-10-06 | 100% | 295,18 | 555,38 | 1.061 | 974,38 |
| `USDCLP Curncy\|PX_LOW` | 9.294 | 1990-01-01 | 2026-10-06 | 100% | 295,18 | 550,88 | 1.027 | 962,91 |
| `USDCLP Curncy\|PX_LAST` | 9.294 | 1990-01-01 | 2026-10-06 | 100% | 295,18 | 553,16 | 1.048 | 973,95 |

**Cuidado.** Serie objetivo. Antes de confiar en PX_OPEN/HIGH/LOW para las convenciones de apertura y promedio, verifica desde cuando el rango intradia tiene contenido real. Hay cotizaciones rancias en feriados.

### `CLFXDOOB Index`

Dolar observado: el fijo oficial que publica el Banco Central de Chile.

- **Unidad:** CLP por USD
- **Frecuencia:** diaria
- **Cierre declarado:** Santiago, publicado en la manana

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `CLFXDOOB Index\|PX_LAST` | 9.238 | 1990-01-02 | 2026-10-06 | 99% | 280,88 | 552,39 | 1.043 | 977,25 |

**Cuidado.** DOLAR OBSERVADO del Banco Central. Se entrega tal como se publica. Antes de usarlo para definir un retorno, establece empiricamente a que jornada corresponde el valor publicado cada dia: comparalo con el spot del mismo dia y con el del dia anterior.

---

## Carry y tasas locales

### `CHN1W Curncy`

Puntos forward NDF a 1 semana. El forward es spot + puntos.

- **Unidad:** CLP
- **Frecuencia:** diaria
- **Cierre declarado:** Nueva York 17:00 ET (convencion FX, fuente Bloomberg BGN)

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `CHN1W Curncy\|PX_LAST` | 6.463 | 2000-09-11 | 2026-10-06 | 99% | -1,43 | 0,14 | 1,50 | -0,03 |

**Cuidado.** Puntos NDF CLP 1 semana.

### `CHN1M Curncy`

Puntos forward NDF a 1 mes. Positivo implica tasa en pesos por sobre la tasa en dolares.

- **Unidad:** CLP
- **Frecuencia:** diaria
- **Cierre declarado:** Nueva York 17:00 ET (convencion FX, fuente Bloomberg BGN)

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `CHN1M Curncy\|PX_LAST` | 7.315 | 1998-04-17 | 2026-10-06 | 103% | -2,55 | 0,75 | 15,95 | -0,28 |

**Cuidado.** Puntos NDF CLP 1 mes.

### `CHN3M Curncy`

Puntos forward NDF a 3 meses.

- **Unidad:** CLP
- **Frecuencia:** diaria
- **Cierre declarado:** Nueva York 17:00 ET (convencion FX, fuente Bloomberg BGN)

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `CHN3M Curncy\|PX_LAST` | 7.294 | 1997-10-22 | 2026-10-06 | 101% | -10,50 | 2,55 | 18,88 | -1,18 |

**Cuidado.** Puntos NDF CLP 3 meses.

### `CHN6M Curncy`

Puntos forward NDF a 6 meses.

- **Unidad:** CLP
- **Frecuencia:** diaria
- **Cierre declarado:** Nueva York 17:00 ET (convencion FX, fuente Bloomberg BGN)

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `CHN6M Curncy\|PX_LAST` | 7.359 | 1997-10-22 | 2026-10-06 | 101% | -8,89 | 5,40 | 37,32 | -2,85 |

**Cuidado.** Puntos NDF CLP 6 meses.

### `CHN12M Curncy`

Puntos forward NDF a 12 meses.

- **Unidad:** CLP
- **Frecuencia:** diaria
- **Cierre declarado:** Nueva York 17:00 ET (convencion FX, fuente Bloomberg BGN)

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `CHN12M Curncy\|PX_LAST` | 7.345 | 1997-10-22 | 2026-10-06 | 101% | -12,20 | 11,50 | 69,25 | -4,80 |

**Cuidado.** Puntos NDF CLP 12 meses.

### `CHNI1M Curncy`

Rendimiento en pesos implicito en el NDF a 1 mes.

- **Unidad:** % anual
- **Frecuencia:** diaria
- **Cierre declarado:** Nueva York 17:00 ET (convencion FX, fuente Bloomberg BGN)

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `CHNI1M Curncy\|PX_LAST` | 6.553 | 2000-07-21 | 2026-10-06 | 100% | -7,57 | 4,09 | 12,98 | 3,59 |

**Cuidado.** Rendimiento implicito del NDF 1M: la via tradeable del carry, incorpora el basis onshore/offshore.

### `CHNI3M Curncy`

Rendimiento en pesos implicito en el NDF a 3 meses.

- **Unidad:** % anual
- **Frecuencia:** diaria
- **Cierre declarado:** Nueva York 17:00 ET (convencion FX, fuente Bloomberg BGN)

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `CHNI3M Curncy\|PX_LAST` | 6.616 | 2000-07-21 | 2026-10-06 | 101% | -6,35 | 4,12 | 14,49 | 3,55 |

**Cuidado.** Rendimiento implicito NDF 3M.

### `CHNI6M Curncy`

Rendimiento en pesos implicito en el NDF a 6 meses.

- **Unidad:** % anual
- **Frecuencia:** diaria
- **Cierre declarado:** Nueva York 17:00 ET (convencion FX, fuente Bloomberg BGN)

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `CHNI6M Curncy\|PX_LAST` | 6.634 | 2000-07-21 | 2026-10-06 | 101% | -2,05 | 4,04 | 11,51 | 3,59 |

**Cuidado.** Rendimiento implicito NDF 6M.

### `CHOVCHOV Index`

Tasa de Politica Monetaria (TPM) del Banco Central, en terminos nominales.

- **Unidad:** % anual nominal
- **Frecuencia:** diaria
- **Cierre declarado:** Santiago

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `CHOVCHOV Index\|PX_LAST` | 9.190 | 2001-08-09 | 2026-10-06 | 147% | 0,5 | 3,75 | 11,25 | 4,50 |

**Cuidado.** Tasa de Politica Monetaria (TPM) del Banco Central. Ver la advertencia de CHON Index si vas a empalmar ambas series.

### `CLICP Index`

Indice de Camara Promedio: acumula el interes overnight interbancario. Es un indice de devengo, no una tasa: la tasa diaria sale de su variacion, dividida por los dias transcurridos.

- **Unidad:** nivel de indice
- **Frecuencia:** diaria
- **Cierre declarado:** Santiago

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `CLICP Index\|PX_LAST` | 5.953 | 2002-11-04 | 2026-10-06 | 100% | 10.052 | 16.189 | 26.963 | 26.963 |

**Cuidado.** Indice de Camara Promedio: es un indice de devengo, NO una tasa. La tasa overnight se obtiene de su variacion diaria, dividida por los dias transcurridos (si no se divide, los fines de semana triplican la tasa). Por construccion deberia ser monotono creciente, y lo es salvo dos retrocesos minusculos de la fuente: -0.023% el 2004-02-26 y -0.012% el 2004-12-07.

### `CLICREAL Index`

Indice de Camara Promedio en terminos reales, expresado en UF.

- **Unidad:** nivel de indice
- **Frecuencia:** diaria
- **Cierre declarado:** Santiago

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `CLICREAL Index\|PX_LAST` | 4.957 | 2006-11-20 | 2026-10-06 | 101% | 9.722 | 10.610 | 11.027 | 10.754 |

**Cuidado.** Indice de Camara Promedio real, en UF.

### `CHON Index`

Tasa objetivo overnight previa a la nominalizacion de agosto de 2001, indexada a UF.

- **Unidad:** % anual real
- **Frecuencia:** diaria
- **Cierre declarado:** Santiago

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `CHON Index\|PX_LAST` | 1.507 | 1995-05-29 | 2001-08-09 | 93% | 3,50 | 6,00 | 14,00 | 3,50 |

**Cuidado.** Tasa objetivo overnight anterior a agosto de 2001. Si piensas empalmarla con CHOVCHOV, verifica primero que ambas esten expresadas en la misma unidad.

### `CHSWP1 Curncy`

Swap de tasa en pesos contra camara, 1 ano.

- **Unidad:** % anual
- **Frecuencia:** diaria
- **Cierre declarado:** Santiago

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `CHSWP1 Curncy\|PX_LAST` | 5.401 | 2003-06-04 | 2026-10-06 | 93% | 0,36 | 4,42 | 12,21 | 4,82 |

**Cuidado.** Swap CLP vs camara 1 ano.

### `CHSWP2 Curncy`

Swap de tasa en pesos contra camara, 2 anos.

- **Unidad:** % anual
- **Frecuencia:** diaria
- **Cierre declarado:** Santiago

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `CHSWP2 Curncy\|PX_LAST` | 5.645 | 2003-06-03 | 2026-10-06 | 97% | 0,47 | 4,40 | 10,58 | 5,04 |

**Cuidado.** Swap CLP vs camara 2 anos.

### `CHSWP5 Curncy`

Swap de tasa en pesos contra camara, 5 anos.

- **Unidad:** % anual
- **Frecuencia:** diaria
- **Cierre declarado:** Santiago

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `CHSWP5 Curncy\|PX_LAST` | 5.802 | 2003-06-03 | 2026-10-06 | 100% | 1,04 | 4,93 | 8,14 | 5,48 |

**Cuidado.** Swap CLP vs camara 5 anos.

### `CHSWP10 Curncy`

Swap de tasa en pesos contra camara, 10 anos.

- **Unidad:** % anual
- **Frecuencia:** diaria
- **Cierre declarado:** Santiago

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `CHSWP10 Curncy\|PX_LAST` | 5.475 | 2004-08-25 | 2026-10-06 | 100% | 1,96 | 5,22 | 8,11 | 5,91 |

**Cuidado.** Swap CLP vs camara 10 anos.

### `CHSWC2 Curncy`

Swap UF contra camara a 2 anos. La diferencia con CHSWP2 aproxima la inflacion implicita.

- **Unidad:** % anual real
- **Frecuencia:** diaria
- **Cierre declarado:** Santiago

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `CHSWC2 Curncy\|PX_LAST` | 5.834 | 2003-06-03 | 2026-10-06 | 101% | -2,36 | 1,36 | 4,79 | 1,53 |

**Cuidado.** Swap UF vs camara 2 anos: inflacion implicita.

### `CHUF Index`

Unidad de Fomento, la unidad de cuenta indexada a inflacion.

- **Unidad:** CLP por UF
- **Frecuencia:** diaria
- **Cierre declarado:** Santiago

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `CHUF Index\|PX_LAST` | 13.428 | 1990-01-01 | 2026-10-06 | 144% | 5.435 | 20.031 | 41.106 | 41.106 |

**Cuidado.** Unidad de Fomento. Se publica con anticipacion: el valor de los proximos dias se conoce de antemano.

---

## Tasas externas

### `SOFRRATE Index`

SOFR: tasa overnight garantizada en dolares.

- **Unidad:** % anual
- **Frecuencia:** diaria
- **Cierre declarado:** Nueva York, publicado el dia siguiente

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `SOFRRATE Index\|PX_LAST` | 2.127 | 2018-04-02 | 2026-10-06 | 99% | 0,01 | 2,43 | 5,40 | 3,90 |

**Cuidado.** SOFR: tasa overnight garantizada en dolares. Averigua a que hora se publica el valor de cada jornada antes de usarlo como variable explicativa. Historia desde 2018-04.

### `FEDL01 Index`

Fed funds effective: tasa overnight efectiva en dolares.

- **Unidad:** % anual
- **Frecuencia:** diaria
- **Cierre declarado:** Nueva York, publicado el dia siguiente

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `FEDL01 Index\|PX_LAST` | 9.339 | 1990-01-01 | 2026-10-06 | 100% | 0,04 | 2,96 | 10,39 | 3,88 |

**Cuidado.** Fed funds effective. Misma consideracion de horario de publicacion que el SOFR. Sirve para empalmar la tasa en dolares antes de 2018-04.

### `US0001M Index`

ICE LIBOR USD a 1 mes.

- **Unidad:** % anual
- **Frecuencia:** diaria
- **Cierre declarado:** Londres 11:00

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `US0001M Index\|PX_LAST` | 8.775 | 1990-01-01 | 2024-09-30 | 100% | 0,0726 | 2,51 | 9,13 | 4,96 |

**Cuidado.** ICE LIBOR USD 1M. DESCONTINUADO: su ultimo dato es del 2024-09-30, asi que no sirve como tasa USD para el tramo reciente. Usar SOFRRATE o FEDL01.

### `USGG3M Index`

Tasa del Tesoro de EE.UU. a 3 meses, generica.

- **Unidad:** % anual
- **Frecuencia:** diaria
- **Cierre declarado:** Nueva York 17:00

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `USGG3M Index\|PX_LAST` | 9.577 | 1990-01-02 | 2026-10-06 | 103% | -0,1372 | 2,88 | 8,24 | 4,12 |

### `USGG2YR Index`

Tasa del Tesoro de EE.UU. a 2 anos, generica.

- **Unidad:** % anual
- **Frecuencia:** diaria
- **Cierre declarado:** Nueva York 17:00

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `USGG2YR Index\|PX_LAST` | 9.574 | 1990-01-02 | 2026-10-06 | 103% | 0,1013 | 3,49 | 9,03 | 4,80 |

### `USGG10YR Index`

Tasa del Tesoro de EE.UU. a 10 anos, generica.

- **Unidad:** % anual
- **Frecuencia:** diaria
- **Cierre declarado:** Nueva York 17:00

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `USGG10YR Index\|PX_LAST` | 9.576 | 1990-01-02 | 2026-10-06 | 103% | 0,5069 | 4,18 | 9,06 | 5,28 |

---

## Cobre y commodities

### `LMCADS03 Comdty`

Cobre LME a 3 meses. El principal determinante de los terminos de intercambio de Chile.

- **Unidad:** USD por tonelada
- **Frecuencia:** diaria
- **Cierre declarado:** Londres, cierre LME

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `LMCADS03 Comdty\|PX_LAST` | 9.289 | 1990-01-02 | 2026-10-06 | 100% | 1.338 | 5.261 | 14.768 | 14.415 |

**Cuidado.** Cobre LME 3 meses. Determinante principal de los terminos de intercambio de Chile.

### `HG1 Comdty`

Cobre COMEX, primer futuro generico. Equivale al LME dividido por 2204.6 libras por tonelada.

- **Unidad:** centavos de USD por libra
- **Frecuencia:** diaria
- **Cierre declarado:** Nueva York, settlement COMEX 13:00 ET

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `HG1 Comdty\|PX_LAST` | 9.243 | 1990-01-02 | 2026-10-06 | 99% | 60,60 | 240,60 | 680,35 | 664,95 |

**Cuidado.** Cobre COMEX, primer generico: la serie incluye rolado de contrato.

### `LMAHDS03 Comdty`

Aluminio LME a 3 meses.

- **Unidad:** USD por tonelada
- **Frecuencia:** diaria
- **Cierre declarado:** Londres, cierre LME

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `LMAHDS03 Comdty\|PX_LAST` | 9.289 | 1990-01-02 | 2026-10-06 | 100% | 1.040 | 1.803 | 3.849 | 3.134 |

**Cuidado.** Aluminio LME 3 meses.

### `CO1 Comdty`

Petroleo Brent, primer futuro generico.

- **Unidad:** USD por barril
- **Frecuencia:** diaria
- **Cierre declarado:** Londres, settlement ICE

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `CO1 Comdty\|PX_LAST` | 9.403 | 1990-01-02 | 2026-10-06 | 101% | 9,64 | 53,31 | 146,08 | 100,58 |

**Cuidado.** Brent, primer generico.

### `CL1 Comdty`

Petroleo WTI, primer futuro generico.

- **Unidad:** USD por barril
- **Frecuencia:** diaria
- **Cierre declarado:** Nueva York, settlement NYMEX 14:30 ET

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `CL1 Comdty\|PX_LAST` | 9.242 | 1990-01-02 | 2026-10-06 | 99% | -37,63 | 50,29 | 145,29 | 89,44 |

**Cuidado.** WTI, primer generico. Contiene un precio NEGATIVO real: -37.63 el 2020-04-20. No es un error y no se corrigio, pero invalida cualquier transformacion logaritmica de la serie.

### `SCO1 Comdty`

Mineral de hierro, primer futuro generico.

- **Unidad:** USD por tonelada
- **Frecuencia:** diaria
- **Cierre declarado:** Singapur, settlement SGX

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `SCO1 Comdty\|PX_LAST` | 3.467 | 2013-04-08 | 2026-10-06 | 102% | 38,15 | 99,10 | 223,94 | 91,28 |

**Cuidado.** Mineral de hierro, primer generico.

### `XAU Curncy`

Oro spot.

- **Unidad:** USD por onza troy
- **Frecuencia:** diaria
- **Cierre declarado:** Nueva York 17:00 ET (convencion FX, fuente Bloomberg BGN)

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `XAU Curncy\|PX_LAST` | 9.533 | 1990-01-02 | 2026-10-06 | 103% | 252,55 | 866,95 | 5.417 | 4.164 |

**Cuidado.** Oro spot.

### `BCOM Index`

Bloomberg Commodity Index: canasta amplia de materias primas.

- **Unidad:** nivel de indice
- **Frecuencia:** diaria
- **Cierre declarado:** Nueva York, cierre

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `BCOM Index\|PX_LAST` | 9.228 | 1990-01-02 | 2026-10-06 | 99% | 59,48 | 104,43 | 237,95 | 142,81 |

**Cuidado.** Indice agregado de commodities.

---

## Dolar global

### `DXY Curncy`

Dollar Index: el dolar contra una canasta de seis monedas desarrolladas.

- **Unidad:** nivel de indice
- **Frecuencia:** diaria
- **Cierre declarado:** Nueva York 17:00 ET (convencion FX, fuente Bloomberg BGN)

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `DXY Curncy\|PX_LAST` | 9.517 | 1990-01-02 | 2026-10-06 | 102% | 71,33 | 92,97 | 120,90 | 101,83 |

### `BBDXY Index`

Bloomberg Dollar Spot Index: canasta mas amplia que el DXY, incluye emergentes.

- **Unidad:** nivel de indice
- **Frecuencia:** diaria
- **Cierre declarado:** Nueva York 17:00 ET (convencion FX, fuente Bloomberg BGN)

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `BBDXY Index\|PX_LAST` | 5.567 | 2004-12-31 | 2026-10-06 | 103% | 905,27 | 1.145 | 1.353 | 1.220 |

### `EURUSD Curncy`

Euro-dolar. Ojo con la direccion: sube cuando el dolar se debilita.

- **Unidad:** USD por EUR
- **Frecuencia:** diaria
- **Cierre declarado:** Nueva York 17:00 ET (convencion FX, fuente Bloomberg BGN)

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `EURUSD Curncy\|PX_LAST` | 9.520 | 1990-01-02 | 2026-10-06 | 102% | 0,8272 | 1,19 | 1,60 | 1,13 |

### `USDJPY Curncy`

Dolar-yen.

- **Unidad:** JPY por USD
- **Frecuencia:** diaria
- **Cierre declarado:** Nueva York 17:00 ET (convencion FX, fuente Bloomberg BGN)

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `USDJPY Curncy\|PX_LAST` | 9.592 | 1990-01-01 | 2026-10-06 | 103% | 75,82 | 112,19 | 163,86 | 158,10 |

### `USDCNH Curncy`

Dolar-yuan offshore, el que se transa libremente en Hong Kong.

- **Unidad:** CNH por USD
- **Frecuencia:** diaria
- **Cierre declarado:** Nueva York 17:00 ET (convencion FX, fuente Bloomberg BGN)

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `USDCNH Curncy\|PX_LAST` | 4.203 | 2010-08-23 | 2026-10-06 | 107% | 6,02 | 6,65 | 7,43 | 6,70 |

**Cuidado.** Offshore. Historia desde 2010-08.

### `USDCNY Curncy`

Dolar-yuan onshore, administrado por el banco central chino.

- **Unidad:** CNY por USD
- **Frecuencia:** diaria
- **Cierre declarado:** cierre del mercado formal local (PRICING_SOURCE: Regional BGN onshore)

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `USDCNY Curncy\|PX_LAST` | 9.304 | 1990-01-01 | 2026-09-30 | 100% | 4,73 | 6,98 | 8,73 | 6,71 |

**Cuidado.** Onshore: cierra con la sesion de Shanghai.

---

## FX regional y emergente

### `USDBRL Curncy`

Dolar-real brasileno.

- **Unidad:** BRL por USD
- **Frecuencia:** diaria
- **Cierre declarado:** cierre del mercado formal local (PRICING_SOURCE: Regional BGN onshore)

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `USDBRL Curncy\|PX_LAST` | 8.871 | 1992-01-15 | 2026-10-06 | 101% | 0,0004 | 2,27 | 6,29 | 4,98 |

**Cuidado.** Onshore: cierra con la sesion de Sao Paulo. Grafica el nivel de la serie completa antes de calcular retornos: Brasil cambio de unidad monetaria mas de una vez en el periodo cubierto.

### `USDMXN Curncy`

Dolar-peso mexicano, la moneda emergente mas liquida de la region.

- **Unidad:** MXN por USD
- **Frecuencia:** diaria
- **Cierre declarado:** Nueva York 17:00 ET (convencion FX, fuente Bloomberg BGN)

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `USDMXN Curncy\|PX_LAST` | 9.589 | 1990-01-01 | 2026-10-06 | 103% | 2,68 | 11,42 | 25,36 | 17,98 |

### `USDCOP Curncy`

Dolar-peso colombiano.

- **Unidad:** COP por USD
- **Frecuencia:** diaria
- **Cierre declarado:** cierre del mercado formal local (PRICING_SOURCE: Regional BGN onshore)

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `USDCOP Curncy\|PX_LAST` | 8.643 | 1992-08-19 | 2026-10-06 | 100% | 689,21 | 2.286 | 5.120 | 3.242 |

**Cuidado.** Onshore: cierra con la sesion de Bogota.

### `USDPEN Curncy`

Dolar-sol peruano. Peru es el otro gran exportador de cobre.

- **Unidad:** PEN por USD
- **Frecuencia:** diaria
- **Cierre declarado:** cierre del mercado formal local (PRICING_SOURCE: Regional BGN onshore)

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `USDPEN Curncy\|PX_LAST` | 8.449 | 1992-08-12 | 2026-10-06 | 98% | 1,28 | 3,27 | 4,14 | 3,43 |

**Cuidado.** Onshore: cierra con la sesion de Lima.

### `USDZAR Curncy`

Dolar-rand sudafricano: moneda de commodities fuera de la region.

- **Unidad:** ZAR por USD
- **Frecuencia:** diaria
- **Cierre declarado:** Nueva York 17:00 ET (convencion FX, fuente Bloomberg BGN)

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `USDZAR Curncy\|PX_LAST` | 9.589 | 1990-01-01 | 2026-10-06 | 103% | 2,50 | 7,79 | 19,80 | 16,54 |

**Cuidado.** Otra moneda de commodities, fuera de la region.

### `JPMVXYEM Index`

J.P. Morgan EM-VXY: volatilidad implicita de las monedas emergentes.

- **Unidad:** % anual
- **Frecuencia:** diaria
- **Cierre declarado:** Nueva York, cierre

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `JPMVXYEM Index\|PX_LAST` | 6.975 | 2000-01-03 | 2026-10-06 | 104% | 5,80 | 9,46 | 32,96 | 6,99 |

**Cuidado.** Volatilidad implicita de FX emergente.

---

## Riesgo y renta variable

### `SPX Index`

S&P 500.

- **Unidad:** puntos de indice
- **Frecuencia:** diaria
- **Cierre declarado:** Nueva York 16:00 ET

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `SPX Index\|PX_LAST` | 9.258 | 1990-01-02 | 2026-10-06 | 100% | 295,46 | 1.314 | 7.819 | 7.819 |

### `VIX Index`

Volatilidad implicita del S&P 500 a 30 dias.

- **Unidad:** % anual
- **Frecuencia:** diaria
- **Cierre declarado:** Nueva York 16:15 ET

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `VIX Index\|PX_LAST` | 9.288 | 1990-01-02 | 2026-10-06 | 100% | 9,14 | 17,57 | 82,69 | 15,01 |

### `MOVE Index`

Volatilidad implicita de las tasas del Tesoro de EE.UU.

- **Unidad:** puntos base anuales
- **Frecuencia:** diaria
- **Cierre declarado:** Nueva York, cierre

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `MOVE Index\|PX_LAST` | 9.501 | 1990-01-01 | 2026-10-06 | 102% | 36,62 | 91,48 | 264,60 | 105,20 |

**Cuidado.** Volatilidad implicita de tasas USD.

### `IPSA Index`

S&P/CLX IPSA en pesos, version de retorno total.

- **Unidad:** nivel de indice
- **Frecuencia:** diaria
- **Cierre declarado:** Santiago, cierre bursatil

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `IPSA Index\|PX_LAST` | 9.138 | 1990-01-02 | 2026-08-31 | 99% | 80,02 | 2.940 | 11.628 | 11.315 |

**Cuidado.** Es el indice de RETORNO TOTAL (reinvierte dividendos), no un indice de precios. Estaba rancio al extraer: su ultimo dato es del 2026-08-31, 37 dias antes de la extraccion.

### `MXEF Index`

MSCI Emerging Markets.

- **Unidad:** nivel de indice
- **Frecuencia:** diaria
- **Cierre declarado:** calculo MSCI tras el cierre de los mercados componentes

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `MXEF Index\|PX_LAST` | 9.592 | 1990-01-01 | 2026-10-06 | 103% | 175,34 | 833,70 | 1.803 | 1.743 |

### `SHCOMP Index`

Shanghai Composite: termometro del demandante final del cobre.

- **Unidad:** puntos de indice
- **Frecuencia:** diaria
- **Cierre declarado:** Shanghai 15:00 CST

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `SHCOMP Index\|PX_LAST` | 8.734 | 1990-12-19 | 2026-09-30 | 97% | 99,98 | 2.192 | 6.092 | 3.842 |

**Cuidado.** Termometro del demandante final del cobre.

---

## Volatilidad implicita del peso

### `USDCLPV1M Curncy`

Volatilidad implicita de opciones USD/CLP a 1 mes.

- **Unidad:** % anual
- **Frecuencia:** diaria
- **Cierre declarado:** Nueva York 17:00 ET (convencion FX, fuente Bloomberg BGN)

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `USDCLPV1M Curncy\|PX_LAST` | 7.014 | 1998-07-28 | 2026-10-06 | 99% | 4,00 | 11,15 | 38,98 | 13,64 |

**Cuidado.** Vol implicita USD/CLP 1M.

### `USDCLPV3M Curncy`

Volatilidad implicita de opciones USD/CLP a 3 meses.

- **Unidad:** % anual
- **Frecuencia:** diaria
- **Cierre declarado:** Nueva York 17:00 ET (convencion FX, fuente Bloomberg BGN)

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `USDCLPV3M Curncy\|PX_LAST` | 7.019 | 1998-07-28 | 2026-10-06 | 99% | 5,00 | 11,50 | 30,80 | 12,76 |

**Cuidado.** Vol implicita USD/CLP 3M.

---

## Soberano chileno

### `GTCLP5Y Govt`

Bono de Tesoreria en pesos, generico a 5 anos.

- **Unidad:** % anual
- **Frecuencia:** diaria
- **Cierre declarado:** Santiago

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `GTCLP5Y Govt\|PX_LAST` | 2.949 | 2005-11-10 | 2026-05-25 | 58% | 1,24 | 5,14 | 8,43 | 5,30 |
| `GTCLP5Y Govt\|YLD_YTM_MID` | 2.949 | 2005-11-10 | 2026-05-25 | 58% | 1,24 | 5,14 | 8,43 | 5,30 |

**Cuidado.** Bono de Tesoreria en pesos, generico 5 anos. OJO: en la serie historica PX_LAST devuelve la TASA, no el precio, de modo que las dos columnas son identicas y ambas estan en % anual (verificado: el bid supera al ask, lo que solo tiene sentido en tasas). Ademas esta rancia: su ultimo dato es del 2026-05-25, 135 dias antes de la extraccion.

### `GTCLP10Y Govt`

Bono de Tesoreria en pesos, generico a 10 anos.

- **Unidad:** % anual
- **Frecuencia:** diaria
- **Cierre declarado:** Santiago

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `GTCLP10Y Govt\|PX_LAST` | 2.565 | 2005-09-29 | 2026-09-23 | 50% | 2,02 | 5,26 | 8,22 | 6,02 |
| `GTCLP10Y Govt\|YLD_YTM_MID` | 2.565 | 2005-09-29 | 2026-09-23 | 50% | 2,02 | 5,26 | 8,22 | 6,02 |

**Cuidado.** Bono de Tesoreria en pesos, generico 10 anos. OJO: en la serie historica PX_LAST devuelve la TASA, no el precio; las dos columnas son identicas y estan en % anual. Es un generico: el bono subyacente cambia con el tiempo (hoy BTPCL 6 01/01/43), asi que la serie tiene saltos de empalme. Rancia al extraer: su ultimo dato es del 2026-09-23, 14 dias antes de la extraccion.

---

## Flujos y posicionamiento cambiario

### `CLPBODMB Index`

Posicion neta de la banca local en derivados cambiarios con contrapartes offshore, segun el Banco Central de Chile.

- **Unidad:** millones de USD
- **Frecuencia:** diaria
- **Cierre declarado:** Santiago, publicado por el BCCh con rezago

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `CLPBODMB Index\|PX_LAST` | 1.183 | 2022-01-03 | 2026-10-05 | 98% | -20.424 | -4.621 | 7.970 | -19.902 |

**Cuidado.** Posicion neta de la banca local en derivados cambiarios con contrapartes offshore, publicada por el Banco Central. Historia desde 2022-01-03. Averigua con que rezago se publica el valor de cada jornada y que significa su signo antes de usarlo como variable explicativa. Se traslapa con CLPBODM Index (su version antigua) entre 2022-01 y 2023-02: compara ambas en el traslape antes de empalmarlas.

### `CLPBODM Index`

Version antigua (2008-2023, descontinuada) de la posicion neta en derivados cambiarios con contrapartes offshore. Se traslapa con CLPBODMB entre 2022-01 y 2023-02.

- **Unidad:** millones de USD
- **Frecuencia:** diaria
- **Cierre declarado:** Santiago, publicado por el BCCh con rezago

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `CLPBODM Index\|PX_LAST` | 3.634 | 2008-10-01 | 2023-02-28 | 104% | -27.621 | -7.916 | 7.956 | -3.552 |

**Cuidado.** Version antigua y descontinuada de la posicion neta en derivados cambiarios con contrapartes offshore, publicada por el Banco Central. Historia 2008-10 a 2023-02. Se traslapa con CLPBODMB Index entre 2022-01 y 2023-02: antes de empalmarlas, verifica si miden lo mismo.

### `CLPBLDMB Index`

Posicion neta de la banca local en derivados cambiarios con contrapartes locales (AFP, empresas), segun el Banco Central de Chile.

- **Unidad:** millones de USD
- **Frecuencia:** diaria
- **Cierre declarado:** Santiago, publicado por el BCCh con rezago

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `CLPBLDMB Index\|PX_LAST` | 1.183 | 2022-01-03 | 2026-10-05 | 98% | 10.087 | 23.636 | 46.696 | 45.742 |

**Cuidado.** Posicion neta de la banca en derivados cambiarios con contrapartes locales, publicada por el Banco Central. Historia desde 2022-01-03. Misma pregunta de rezago de publicacion que CLPBODMB. Se traslapa con CLPBLDM Index (su version antigua) entre 2022-01 y 2023-02.

### `CLPBLDM Index`

Version antigua (2008-2023, descontinuada) de la posicion en derivados cambiarios con contrapartes locales. Se traslapa con CLPBLDMB entre 2022-01 y 2023-02.

- **Unidad:** millones de USD
- **Frecuencia:** diaria
- **Cierre declarado:** Santiago, publicado por el BCCh con rezago

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `CLPBLDM Index\|PX_LAST` | 3.634 | 2008-10-01 | 2023-02-28 | 104% | 8.558 | 17.510 | 38.414 | 23.421 |

**Cuidado.** Version antigua y descontinuada de la posicion en derivados cambiarios con contrapartes locales. Historia 2008-10 a 2023-02. Se traslapa con CLPBLDMB Index entre 2022-01 y 2023-02: antes de empalmarlas, verifica si miden lo mismo.

### `CLPBSMB Index`

Posicion neta de la banca local en el mercado cambiario spot, segun el Banco Central de Chile.

- **Unidad:** millones de USD
- **Frecuencia:** diaria
- **Cierre declarado:** Santiago, publicado por el BCCh con rezago

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `CLPBSMB Index\|PX_LAST` | 1.182 | 2022-01-03 | 2026-10-05 | 98% | -28.109 | -17.870 | -12.183 | -21.468 |

**Cuidado.** Posicion neta de la banca en el mercado cambiario spot, publicada por el Banco Central. Historia desde 2022-01-03. Misma pregunta de rezago de publicacion que el resto del bloque.

---

## Macro chilena (point-in-time)

### `CLIMMOMS Index`

IMACEC desestacionalizado: la actividad economica mes contra mes.

- **Unidad:** % variacion mensual
- **Frecuencia:** mensual
- **Cierre declarado:** publicacion segun ECO_RELEASE_DT
- **Se revisa:** si. El valor entregado es el ya revisado, no el primero publicado.

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `CLIMMOMS Index\|PX_LAST` | 367 | 1996-02-29 | 2026-08-31 | mensual | -8,01 | 0,29 | 5,82 | -0,67 |

**Fecha de publicacion.** En la columna `CLIMMOMS Index|FECHA_RELEASE`, disponible en 177 de 367 observaciones, desde 2011-12. Donde falta, no se imputo nada.

**Cuidado.** IMACEC m/m desestacionalizado. Se revisa: la fecha de publicacion elimina la fuga por rezago, no la fuga por revision.

### `CLIMYOYN Index`

IMACEC sin desestacionalizar: actividad economica ano contra ano.

- **Unidad:** % variacion anual
- **Frecuencia:** mensual
- **Cierre declarado:** publicacion segun ECO_RELEASE_DT
- **Se revisa:** si. El valor entregado es el ya revisado, no el primero publicado.

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `CLIMYOYN Index\|PX_LAST` | 356 | 1997-01-31 | 2026-08-31 | mensual | -15,98 | 3,47 | 20,38 | -1,01 |

**Fecha de publicacion.** En la columna `CLIMYOYN Index|FECHA_RELEASE`, disponible en 294 de 356 observaciones, desde 2002-03. Donde falta, no se imputo nada.

**Cuidado.** IMACEC a/a sin desestacionalizar. Se revisa.

### `CLINNSMO Index`

IPC mes contra mes, serie enlazada.

- **Unidad:** % variacion mensual
- **Frecuencia:** mensual
- **Cierre declarado:** publicacion segun ECO_RELEASE_DT
- **Se revisa:** si. El valor entregado es el ya revisado, no el primero publicado.

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `CLINNSMO Index\|PX_LAST` | 200 | 2010-01-31 | 2026-08-31 | mensual | -0,5 | 0,3 | 1,90 | 0,6 |

**Fecha de publicacion.** En la columna `CLINNSMO Index|FECHA_RELEASE`, disponible en 92 de 200 observaciones, desde 2019-01. Donde falta, no se imputo nada.

**Cuidado.** IPC m/m, serie enlazada.

### `CLINNSYO Index`

IPC ano contra ano, serie enlazada.

- **Unidad:** % variacion anual
- **Frecuencia:** mensual
- **Cierre declarado:** publicacion segun ECO_RELEASE_DT
- **Se revisa:** si. El valor entregado es el ya revisado, no el primero publicado.

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `CLINNSYO Index\|PX_LAST` | 440 | 1990-01-31 | 2026-08-31 | mensual | -2,30 | 4,00 | 30,40 | 4,10 |

**Fecha de publicacion.** En la columna `CLINNSYO Index|FECHA_RELEASE`, disponible en 92 de 440 observaciones, desde 2019-01. Donde falta, no se imputo nada.

**Cuidado.** IPC a/a, serie enlazada.

### `CHUETOTL Index`

Tasa de desempleo del INE, trimestre movil.

- **Unidad:** % de la fuerza de trabajo
- **Frecuencia:** mensual
- **Cierre declarado:** publicacion segun ECO_RELEASE_DT
- **Se revisa:** si. El valor entregado es el ya revisado, no el primero publicado.

| columna | obs | desde | hasta | vs USD/CLP | minimo | mediana | maximo | ultimo |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `CHUETOTL Index\|PX_LAST` | 440 | 1990-01-31 | 2026-08-31 | mensual | 5,10 | 7,70 | 13,10 | 9,60 |

**Fecha de publicacion.** En la columna `CHUETOTL Index|FECHA_RELEASE`, disponible en 341 de 440 observaciones, desde 1998-04. Donde falta, no se imputo nada.

**Cuidado.** Tasa de desempleo INE, trimestre movil.

---

## Procedencia

Todas las series provienen de Bloomberg y son datos publicos de mercado. El archivo `manifiesto.json` trae la fecha de extraccion, el rango y el hash SHA-256 del parquet, de modo que cualquiera pueda verificar que trabaja sobre exactamente la misma base.

# Map Routing - Integrante 2

## Agente de búsqueda de rutas

Mi responsabilidad dentro del proyecto Map Routing fue construir el agente que
encuentra la ruta óptima entre dos puntos del mapa.

Es el componente central de la asignatura: el que decide, dados un grafo con
más de trescientas mil conexiones y dos nodos cualesquiera, cuál de todos los
recorridos posibles es el mejor.

Implementé dos algoritmos desde cero, sin utilizar ninguna librería que calcule
rutas. Primero Uniform Cost Search, que me sirve de línea base, y después A*
con dos heurísticas distintas. También desarrollé el sistema de métricas que
compara ambos algoritmos sobre el mapa real de Santo Domingo.

## Archivos desarrollados

`src/search/route_result.py`

Define el formato de salida que devuelven todos los algoritmos y las
validaciones que ambos comparten.

`src/search/ucs.py`

Uniform Cost Search, equivalente a Dijkstra con prueba de meta.

`src/search/astar.py`

A*, la búsqueda informada.

`src/search/heuristics.py`

Las dos heurísticas y el cálculo de la velocidad máxima de la red.

`src/search/metrics.py`

Genera la tabla comparativa del informe ejecutando los algoritmos sobre el
grafo real.

`tests/test_search.py`

Diecinueve pruebas sobre un grafo pequeño construido a mano.

`tests/test_search_real.py`

Seis pruebas sobre los 156,431 nodos del mapa completo.

`docs/metricas.md`

La tabla de métricas, generada automáticamente.

## El problema que resuelvo

En términos de Inteligencia Artificial, esto es un problema de búsqueda en un
espacio de estados.

Cada estado es un nodo del grafo, es decir, una intersección o un punto de una
calle. Las acciones disponibles desde un estado son las aristas que salen de
ese nodo, o sea, los tramos de calle por los que se puede avanzar. Cada acción
tiene un costo asociado, que puede ser la distancia en metros o el tiempo en
segundos.

El objetivo es encontrar la secuencia de acciones de menor costo total que
lleva del estado inicial al estado meta.

Lo que hace interesante el problema es el tamaño. El grafo de Santo Domingo
tiene 156,431 nodos y 328,071 aristas dirigidas. Probar todos los recorridos
posibles es imposible, así que la solución tiene que ser un algoritmo que
descarte caminos sin llegar a explorarlos.

## El contrato de salida

Los dos algoritmos devuelven exactamente el mismo diccionario. Esto lo acordé
con el equipo antes de escribir una sola línea.

```python
result = {
    "success": bool,
    "path": list[int],
    "distance_m": float,
    "estimated_time_s": float,
    "visited_nodes": int,
    "runtime_ms": float,
    "algorithm": str,
    "heuristic": str,
    "message": str,
}
```

Que UCS y A* compartan formato tuvo dos consecuencias prácticas.

La primera es que Gabriel pudo desarrollar toda la interfaz llamando a UCS
mientras yo todavía estaba escribiendo A*, y cambiar de algoritmo después le
costó una sola línea.

La segunda es que puedo comparar los dos algoritmos directamente, sin ninguna
traducción entre ellos, que es justo lo que necesita la tabla de métricas.

Cuando la búsqueda falla, `success` viene en `False`, `path` viene vacío y
`message` trae el texto en español ya redactado para mostrarle al usuario. El
agente nunca lanza una excepción hacia la interfaz.

## Uniform Cost Search

La idea de UCS es mantener una frontera de nodos por explorar y expandir
siempre el de menor costo acumulado desde el origen.

Uso una cola de prioridad de la biblioteca estándar. Lo que el profesor exige
construir desde cero es el agente de búsqueda, no la estructura de datos, así
que manejo a mano el montículo, el diccionario de costos, el de predecesores y
el conjunto de nodos cerrados.

```python
open_heap = [(0.0, start)]
g_score = {start: 0.0}
came_from = {}
closed_set = set()
```

El bucle principal saca el nodo más barato, lo marca como cerrado y expande sus
vecinos. Si encuentra un camino mejor hacia un vecino, actualiza su costo y lo
vuelve a insertar en la cola.

UCS garantiza la ruta óptima porque ningún peso del grafo es negativo. Cuando
un nodo sale de la cola, su costo ya no puede mejorar: cualquier otro camino
hacia él tendría que pasar por algún nodo de la frontera, que por definición
cuesta más o igual.

Este algoritmo es mi línea base. Como no usa ninguna heurística, su resultado
es el óptimo por definición, y me sirve para verificar que A* no se equivoca.

## Dos detalles de implementación que valen la pena

**La meta se comprueba al sacar el nodo de la cola, no al insertarlo.**

Cuando inserto un nodo en la frontera, su costo todavía puede bajar más
adelante si aparece un camino mejor. Si cortara la búsqueda en el momento de
insertar el destino, devolvería la primera ruta encontrada y no la más barata.

En mi grafo de pruebas hay un caso preparado exactamente para esto: existe una
arista directa del nodo 1 al 3 que cuesta 2000 metros, mientras que el camino
1 → 2 → 3 cuesta 1000. El destino entra en la cola con costo 2000 antes de que
se descubra el camino bueno. Solo comprobando la meta al sacarla se devuelve la
ruta correcta.

**El borrado perezoso.**

La cola de prioridad estándar no permite bajar la prioridad de una entrada ya
insertada. En vez de buscarla y modificarla, inserto el nodo otra vez con su
nuevo costo. Las entradas viejas quedan en la cola, y cuando salen se descartan
comprobando si el nodo ya está cerrado.

## A*

A* es UCS con información del terreno.

En vez de expandir siempre el nodo de menor costo acumulado, expande el de
menor valor de `f(n)`:

```
f(n) = g(n) + h(n)
```

Esa suma es la mejor estimación disponible del costo total de la ruta completa
que pasa por `n`. Ordenar la cola por `f` en lugar de por `g` es el único
cambio estructural respecto a UCS, y es lo que hace que la búsqueda deje de
crecer como un círculo alrededor del origen y se estire hacia el destino.

## Qué representan g(n), h(n) y f(n)

`g(n)` es el costo real ya gastado para llegar desde el origen hasta el nodo
`n`. Es un dato duro: se calcula sumando los pesos de las aristas realmente
recorridas.

`h(n)` es la estimación de lo que falta desde `n` hasta el destino. Es una
apuesta: no se conoce el camino todavía, se aproxima.

`f(n)` es la suma de ambos, es decir, la estimación del costo total de la ruta
completa si pasara por `n`.

Con `h(n) = 0` para todos los nodos, A* se convierte exactamente en UCS. Por
eso digo que UCS es un caso particular de A*, y por eso los dos algoritmos
están en el proyecto: para poder demostrar esa relación con números medidos.

Hay un error que quise evitar desde el principio. Dentro del bucle, el costo
acumulado se lee siempre del diccionario `g_score`, nunca del valor que acaba
de salir de la cola de prioridad. En UCS ese valor es `g`, pero en A* es `f`, y
usarlo para acumular metería la heurística dentro del costo real corrompiendo
todos los cálculos siguientes.

## Heurística 1: distancia geográfica

```python
distance_heuristic(current_node, goal_node, coordinates) -> float
```

Devuelve la distancia en línea recta, calculada con la fórmula de Haversine,
entre el nodo actual y el destino.

Se usa junto con el costo `distance_m` de cada arista, y produce la **ruta más
corta** en metros.

## Heurística 2: tiempo estimado

```python
time_heuristic(current_node, goal_node, coordinates, max_speed_mps) -> float
```

Toma la misma distancia en línea recta y la divide entre la velocidad máxima de
toda la red vial. Devuelve los segundos mínimos imaginables hasta el destino.

Se usa junto con el costo `time_s` de cada arista, y produce la **ruta más
rápida**.

Con estas dos heurísticas el sistema queda con dos modalidades reales, y no son
la misma ruta con otro nombre. Entre Sala Carlos Piantini y Plaza Juan Barón,
el modo distancia devuelve 2,673 metros en 243 segundos, y el modo tiempo
devuelve 3,245 metros en 203 segundos. La segunda ruta es 571 metros más larga
pero llega 40 segundos antes, porque toma avenidas más rápidas.

## Por qué las heurísticas son admisibles

Una heurística es admisible cuando nunca sobreestima lo que falta:

```
h(n) <= costo real óptimo desde n hasta el destino
```

Esa condición es la que garantiza que A* devuelva la ruta óptima.

La primera heurística es admisible porque el costo de cada arista se mide en
metros recorridos por la calle, y ninguna calle puede ser más corta que la
línea recta entre sus extremos. Como mucho la iguala, en una avenida
perfectamente recta.

La segunda es admisible porque ningún trayecto real puede completarse más
rápido que recorrer la línea recta a la velocidad máxima de la red. Para
lograrlo habría que ir más derecho que la línea recta, que es imposible, o más
rápido que la vía más veloz del mapa, que tampoco.

No me quedé con la demostración teórica. En `tests/test_search.py` hay una
prueba que recorre todos los nodos del grafo de pruebas, calcula el costo
óptimo real con UCS y verifica que la heurística nunca lo supera. Es una
comprobación numérica de la admisibilidad, no una afirmación.

## Por qué además son consistentes

Mi implementación de A* usa un conjunto de nodos cerrados y nunca vuelve a
revisar un nodo ya cerrado. Eso solo es correcto si la heurística cumple una
condición más fuerte que la admisibilidad, llamada consistencia:

```
h(n) <= costo(n -> n') + h(n')      para toda arista n -> n'
```

Las dos heurísticas la cumplen, y la demostración cabe en una línea. La
distancia en línea recta satisface la desigualdad triangular, así que la recta
del nodo al destino nunca supera la recta hasta el vecino más la recta del
vecino al destino. Y como el costo de la arista es siempre mayor o igual que la
recta hasta el vecino, la condición sale sola. Para la heurística de tiempo es
el mismo razonamiento dividido entre la velocidad máxima.

Si me preguntan por qué puedo cerrar un nodo y no volver a mirarlo nunca, esta
es la respuesta. Y también está verificada arista por arista en las pruebas.

## La velocidad máxima de la red

Este fue el problema más interesante que encontré.

La heurística de tiempo divide entre la velocidad máxima de la red. El plan
original fijaba ese valor en 80 km/h, que es el máximo de la tabla de
velocidades por defecto que usa Deivy.

Al medirlo sobre el grafo cargado descubrí que la velocidad máxima real es de
**100 km/h**, porque algunos tramos de la Autopista Las Américas traen esa
etiqueta de velocidad en OpenStreetMap.

Con una cota de 80 sobre una red que llega a 100, la heurística de tiempo
sobreestima y A* deja de ser óptimo. Lo comprobé sobre 343 pares de puntos
tomados cerca de la autopista: **16 de ellos devolvieron una ruta peor que la
óptima**, hasta un 1.97% más lenta. Con la cota correcta, ninguno.

La solución no fue cambiar el número, sino dejar de escribirlo a mano:

```python
def graph_max_speed_mps(graph):
    """Velocidad maxima real de las aristas del grafo, en m/s."""
```

Esta función recorre el grafo una sola vez y calcula la velocidad más alta que
existe de verdad. Así, si Deivy cambia su tabla de velocidades o cambiamos el
archivo del mapa, la heurística sigue siendo admisible sin que nadie tenga que
acordarse de actualizar una constante.

La lección que me llevo es que una constante escrita a mano miente en cuanto
alguien cambia los datos, y que el error se manifiesta como rutas ligeramente
peores, que es la clase de fallo que nadie nota mirando la pantalla.

## Reconstrucción de la ruta

Durante la búsqueda mantengo un diccionario `came_from` donde guardo, para cada
nodo, desde qué otro nodo se llegó a él por el mejor camino conocido.

Cuando la búsqueda encuentra el destino, retrocedo desde él hasta el origen
siguiendo ese diccionario, y luego invierto la lista.

```python
path = [goal]
current_node = goal

while current_node != start:
    current_node = came_from[current_node]
    path.append(current_node)

path.reverse()
```

El recorrido es iterativo, sin recursión. Una ruta sobre el grafo real puede
tener cientos de nodos, y en el caso más largo que probé tiene 641: una versión
recursiva es un riesgo innecesario.

Después calculo siempre la distancia total y el tiempo total reales sumando las
aristas de la ruta devuelta, sin importar en qué modo busqué. El costo que
optimiza la búsqueda es solo uno de los dos, pero la interfaz necesita mostrar
los dos.

## Casos especiales

El agente nunca lanza una excepción. Todos estos casos vuelven con
`success: False` y un mensaje en español listo para mostrar:

- El grafo está vacío.
- El modo de búsqueda no es válido.
- El nodo de origen no existe en el grafo.
- El nodo de destino no existe en el grafo.
- El origen y el destino son el mismo punto.
- No existe ruta entre los dos puntos.

El último caso merece una explicación, porque no es teórico.

La poda que hace Deivy conserva la componente conexa **no dirigida**, y eso no
garantiza que exista un camino dirigido entre dos nodos cualesquiera. Lo medí:
el 99.20% de los nodos son mutuamente alcanzables, pero **1,247 nodos quedan
fuera**. Son calles de sentido único mal cerradas, rampas y callejones desde
los que no se puede salir o a los que no se puede llegar.

Un usuario puede hacer clic exactamente ahí, así que el caso ocurre de verdad.

## Métricas de efectividad

El módulo `metrics.py` genera la tabla del informe ejecutando los algoritmos
sobre el mapa real. Ningún número está escrito a mano.

```bash
python3 -m src.search.metrics --repeticiones 5
```

Cada escenario se resuelve con cuatro configuraciones y el script comprueba
solo que A* iguale el costo de su UCS correspondiente. Si no coincide, escribe
un fallo en la tabla en vez de publicar el número.

Nodos explorados por escenario, UCS contra A*:

| Escenario | Distancia | Modo distancia | Modo tiempo |
|---|---|---|---|
| Sector corto, Gazcue | 1,316 m | 667 → 140 | 608 → 293 |
| Zona Colonial a la UASD | 5,364 m | 14,603 → 407 | 15,259 → 4,851 |
| Extremo oeste al este | 37,242 m | 155,845 → 41,974 | 151,408 → 49,838 |
| Avenidas principales | 10,175 m | 59,057 → 5,443 | 55,341 → 15,416 |
| Calles unidireccionales | 1,104 m | 349 → 42 | 321 → 158 |
| Sin ruta posible | — | 155,875 | 155,875 |

En promedio, A* explora un **85.6% menos de nodos** que UCS en modo distancia,
entre un 73.1% y un 97.2% según el caso, y resuelve la búsqueda 5.2 veces más
rápido. En modo tiempo el ahorro baja al 62.0%.

En los cinco escenarios con ruta, **A* devolvió exactamente el mismo costo que
UCS**. Esa igualdad es la evidencia de que mis heurísticas no sobreestiman.

La fila más elocuente es la tercera. Para una ruta de 37 kilómetros, UCS tuvo
que expandir 155,845 nodos, es decir, casi todo Santo Domingo. A* resolvió lo
mismo con 41,974.

## Dos resultados que no esperaba

**El modo tiempo rinde la mitad que el modo distancia.**

La causa es que solo 438 de las 73,507 vías del mapa traen etiqueta de
velocidad. El 77.7% de las aristas se queda con el valor por defecto de 30
km/h, mientras mi heurística asume un techo de 100. La estimación se queda muy
corta, `h` aporta poca información y A* se parece más a UCS.

No es un error del algoritmo: es una consecuencia de la calidad de los datos de
OpenStreetMap en Santo Domingo. Lo dejo documentado como limitación y como
mejora futura.

**Cuando no hay ruta, A* es más lento que UCS.**

En el escenario sin ruta, A* tardó 1,057 milisegundos contra los 435 de UCS.
Ambos recorren el grafo entero antes de rendirse, pero A* paga además el
cálculo de la heurística en 155,875 nodos sin recibir ninguna guía a cambio.

La heurística solo rinde cuando existe un destino al que dirigirse. Me pareció
un resultado lo bastante interesante como para dejarlo en la tabla en vez de
esconderlo.

## Pruebas realizadas

Escribí veinticinco pruebas repartidas en dos archivos.

**Diecinueve sobre un grafo de juguete** de seis nodos, diseñado a mano para
que las rutas óptimas se puedan calcular sin computadora y yo pueda
defenderlas. Tiene una arista directa cara que obliga al algoritmo a optimizar
costo y no cantidad de saltos, una ruta sur más corta y una norte más rápida
para que los dos modos den resultados distintos, y un nodo al que no llega
nadie para probar el caso sin ruta.

Las más importantes son estas cuatro:

- La heurística nunca sobreestima, comprobado contra el costo óptimo real de
  UCS desde todos los nodos.
- La heurística es consistente, comprobado arista por arista.
- UCS y A* devuelven el mismo costo en ocho pares distintos y en los dos modos.
- Con una cota de velocidad falsa, A* devuelve una ruta peor. Esta prueba
  reproduce a propósito el fallo de optimalidad, para demostrar que la
  condición de admisibilidad no es un adorno teórico.

**Seis sobre el grafo real** de 156,431 nodos, que verifican lo mismo donde de
verdad importa: que A* iguale el costo de UCS en los cinco escenarios del
informe, que la cota de velocidad cubra la vía más rápida del mapa, que la ruta
devuelta exista realmente como aristas dirigidas del grafo, y que el caso sin
ruta se maneje sin excepciones.

Estas seis se saltan solas cuando falta `data/santo_domingo.osm`, que no viaja
en el repositorio por su tamaño. Con el mapa presente la suite completa corre
en 7.9 segundos; sin él, en 0.019 segundos con seis pruebas omitidas. Así
cualquiera del equipo puede clonar y ejecutar las pruebas sin descargar 94 MB.

```bash
python3 -m unittest discover -s tests -t .
```

## Dificultades encontradas

**Confundir el costo real con la prioridad de la cola.**

En UCS el valor que sale de la cola es el costo acumulado, pero en A* es la
suma del costo y la heurística. La primera vez que escribí A* estuve a punto de
usar ese valor para acumular el costo de los vecinos, lo que habría metido la
heurística dentro del costo real. Ahora el código lee siempre de `g_score` y
tiene un comentario explicando por qué.

**La cota de velocidad equivocada.**

Ya la expliqué más arriba. Lo relevante como dificultad es que el error no daba
ningún síntoma visible: las rutas seguían saliendo, seguían pareciendo
razonables, y solo comparando contra UCS sobre cientos de pares aparecieron las
dieciséis que estaban mal.

**Una verificación que no verificaba nada.**

La igualdad entre A* y UCS sobre el mapa real existía solo como texto dentro de
`docs/metricas.md`: el generador escribía la palabra "FALLO" en el documento si
no coincidían, pero no rompía ninguna prueba. Un error en la heurística habría
pasado inadvertido con la suite entera en verde. Lo convertí en las seis
pruebas de `test_search_real.py`.

De ahí saqué una idea que me parece la más útil de todo el proyecto: un informe
que se genera solo no es una verificación mientras nadie lo lea.

**Perder trabajo por no commitear.**

A* con sus heurísticas y el generador de métricas llegaron a existir, se
validaron sobre el mapa real y se perdieron al reemplazar la carpeta de trabajo
antes de haberlos commiteado. Los reconstruí con las mediciones, que sí
sobrevivían anotadas. Desde entonces hago commit y push al terminar cada parte,
no al final del día.

## Riesgos y limitaciones

**El grafo no está fuertemente conexo.** El 0.80% de los nodos, 1,247 en total,
no son alcanzables desde el resto o no pueden alcanzar al resto. Una mejora
futura sería podar por componente fuertemente conexa en lugar de por componente
no dirigida.

**La heurística de tiempo está mal informada** por la escasez de etiquetas de
velocidad en los datos. Una mejora sería estimar velocidades por tipo de vía
con datos reales de tráfico.

**No hay restricciones de giro.** El grafo no modela prohibiciones de giro a la
izquierda ni separadores centrales, así que alguna ruta puede indicar un giro
que en la calle real no está permitido.

**No hay tráfico ni semáforos.** El tiempo estimado supone circulación libre a
la velocidad máxima de cada vía.

**El caso sin ruta es el más costoso del sistema.** Recorre el grafo completo
antes de rendirse, hasta un segundo y medio. Se lo advertí a Gabriel para que
la interfaz mostrara un indicador de carga durante el cálculo.

## Contrato para los demás integrantes

```python
from src.search.astar import astar
from src.search.heuristics import graph_max_speed_mps

max_speed = graph_max_speed_mps(graph)   # calcular una sola vez

result = astar(
    graph,
    coordinates,
    start_node,
    goal_node,
    mode="distance",          # o "time"
    max_speed_mps=max_speed,
)
```

`ucs(graph, start, goal, mode)` tiene la misma salida y no recibe
`coordinates`, porque no usa heurística.

Conviene calcular la velocidad máxima una sola vez al cargar el grafo y
guardarla: la función recorre las 328,071 aristas completas.

La ruta se devuelve en `result["path"]` como una lista ordenada de
identificadores de nodo, para que la interfaz obtenga sus coordenadas del
diccionario `coordinates` y dibuje la línea.

## Conclusión

El agente cumple con lo que pide el enunciado: encuentra la ruta óptima entre
dos puntos de un grafo dirigido y ponderado, sin usar ninguna librería que
calcule rutas, y con dos criterios de optimización distintos.

Lo que más valor tiene, a mi juicio, no es que funcione sino que esté
verificado. Sé que A* devuelve la ruta óptima porque coincide con UCS en
veinticinco pruebas y en cinco escenarios del mapa real, no porque el código
parezca correcto. Y sé exactamente cuánto gana A* sobre UCS porque está medido,
no estimado: un 85.6% menos de nodos explorados para el mismo resultado.

# Map Routing - Integrante 1

## Procesamiento de OpenStreetMap y construcción del grafo

Mi responsabilidad dentro del proyecto Map Routing fue preparar los datos cartográficos que posteriormente utilizarán los algoritmos de búsqueda de rutas.

El punto de partida fue el archivo `santo_domingo.osm`, obtenido a partir de datos de OpenStreetMap. A partir de este archivo desarrollé el procesamiento necesario para identificar las calles transitables por vehículos y convertirlas en un grafo dirigido y ponderado.

También implementé el cálculo de las distancias y tiempos estimados de cada segmento, la eliminación de zonas aisladas del mapa, la búsqueda del nodo más cercano a unas coordenadas y un sistema de caché para evitar procesar nuevamente el archivo OSM en cada ejecución.

## Archivos desarrollados

Los archivos correspondientes a esta parte del proyecto son:

`src/geo_utils.py`

Contiene la fórmula de Haversine utilizada para calcular la distancia en metros entre dos coordenadas geográficas.

`src/osm_parser.py`

Se encarga de leer el archivo OSM, identificar las vías utilizables por vehículos y obtener las coordenadas de los nodos necesarios.

`src/graph_builder.py`

Construye el grafo dirigido y ponderado, interpreta la dirección de las calles, calcula los tiempos estimados, elimina componentes aisladas y maneja la caché del grafo.

`src/nearest_node.py`

Permite encontrar el nodo del grafo más cercano a una latitud y longitud utilizando una rejilla espacial.

`tests/test_graph.py`

Contiene las pruebas automáticas utilizadas para comprobar el funcionamiento de las partes principales del grafo.

## Archivo cartográfico utilizado

Para este proyecto se utilizó el archivo:

`data/santo_domingo.osm`

El archivo contiene información cartográfica de Santo Domingo en formato XML de OpenStreetMap.

OpenStreetMap organiza sus datos principalmente mediante nodos, vías y etiquetas.

Los nodos contienen un identificador y sus coordenadas de latitud y longitud.

Las vías contienen una secuencia ordenada de referencias a nodos. Estas secuencias permiten representar calles y otros elementos lineales.

Las etiquetas o tags describen las características de cada elemento. Por ejemplo, permiten identificar el tipo de calle, su nombre, su velocidad máxima y si es de una sola vía.

## Lectura del archivo OSM

Debido al tamaño del archivo, no se carga completamente en memoria.

Para procesarlo utilicé `xml.etree.ElementTree.iterparse()`, que permite recorrer progresivamente los elementos del XML.

Después de procesar los elementos que ya no son necesarios se utiliza `elem.clear()` para liberar memoria.

El procesamiento se realiza en dos pasadas.

En la primera pasada se identifican las vías que pueden ser utilizadas por vehículos y se almacenan los identificadores de los nodos que forman parte de ellas.

En la segunda pasada se vuelve a recorrer el archivo para guardar únicamente las coordenadas de esos nodos.

De esta forma no es necesario conservar información de todos los nodos presentes originalmente en el archivo.

## Filtrado de vías

Para el perfil de automóvil se aceptaron los siguientes tipos principales de vías:

* motorway
* trunk
* primary
* secondary
* tertiary
* unclassified
* residential
* living_street
* service

También se incluyen las variantes `*_link` correspondientes.

Se excluyen automáticamente los tipos de vías que no están dentro de esa lista, como senderos peatonales, ciclovías, caminos y escaleras.

Además, se descartan vías que indiquen restricciones como:

`access=no`

`access=private`

`motor_vehicle=no`

Después de aplicar estos criterios se obtuvieron 32,263 vías vehiculares.

## Construcción del grafo

El mapa fue convertido a un grafo dirigido.

Cada nodo del grafo corresponde a un nodo de OpenStreetMap utilizado por alguna vía vehicular.

Cada par de nodos consecutivos de una vía genera una conexión.

La estructura utilizada para almacenar el grafo es:

```python
graph[node_id][neighbor_id] = {
    "distance_m": float,
    "time_s": float,
    "street": str,
    "highway": str,
    "way_id": int,
}
```

Las coordenadas se almacenan por separado:

```python
coordinates[node_id] = (latitude, longitude)
```

Esta estructura permite que los algoritmos de búsqueda puedan obtener directamente los vecinos de un nodo y el costo asociado a cada conexión.

## Direccionalidad

Durante la construcción del grafo se toman en cuenta las restricciones de dirección presentes en OpenStreetMap.

Los valores `oneway=yes`, `oneway=true` y `oneway=1` crean conexiones únicamente en el orden de los nodos de la vía.

Los valores `oneway=-1` y `oneway=reverse` crean las conexiones en sentido contrario.

Las rotondas identificadas mediante `junction=roundabout` también se consideran unidireccionales.

Cuando una vía no tiene restricción de dirección se generan las conexiones en ambos sentidos.

La dirección utilizada para estudiar las componentes conexas es una representación auxiliar. Esta representación no modifica las direcciones reales almacenadas en el grafo.

## Distancias

La distancia entre nodos consecutivos se calcula utilizando la fórmula de Haversine.

Se utiliza un radio medio terrestre de 6,371,000 metros.

Las distancias se almacenan en metros y no se redondean durante los cálculos internos.

Los segmentos cuya distancia fuera igual o menor que cero son descartados.

En la validación final no se encontraron aristas con distancia cero o negativa.

Resultados obtenidos:

Distancia mínima: 0.0445 metros

Distancia máxima: 808.4130 metros

Distancia promedio: 36.6920 metros

La distancia total de una ruta debe obtenerse sumando las distancias de todos los segmentos recorridos y no mediante una línea directa entre origen y destino.

## Velocidad y tiempo estimado

Cuando una vía contiene un valor numérico en `maxspeed`, se utiliza ese valor.

Cuando no existe un valor utilizable se emplean velocidades predeterminadas según el tipo de vía.

Las velocidades utilizadas son:

* motorway: 80 km/h
* trunk: 70 km/h
* primary: 60 km/h
* secondary: 50 km/h
* tertiary: 40 km/h
* residential: 30 km/h
* unclassified: 30 km/h
* living_street: 20 km/h
* service: 20 km/h

Las variantes `*_link` utilizan la velocidad correspondiente a su tipo base.

La velocidad se convierte de kilómetros por hora a metros por segundo y el tiempo se calcula mediante la relación entre distancia y velocidad.

Resultados finales:

Tiempo mínimo: 0.0080 segundos

Tiempo máximo: 108.3702 segundos

Tiempo promedio: 4.3501 segundos

No se encontraron aristas con tiempo igual o menor que cero.

## Aristas paralelas

La representación `graph[u][v]` solamente permite una conexión almacenada entre dos nodos determinados.

Si dos vías diferentes conectan el mismo par de nodos en la misma dirección, se conserva la conexión que tenga la menor distancia.

Esto evita cambiar el contrato del grafo y mantiene una sola arista por cada par origen-destino.

## Componente conexa mayor

Después de construir el grafo se identifican sus componentes conexas utilizando una representación no dirigida auxiliar.

La exploración se realiza mediante BFS iterativo utilizando `collections.deque`.

No se utiliza recursión debido a la gran cantidad de nodos presentes en el mapa.

Antes de la poda existían 156,865 nodos.

La componente mayor contiene 156,431 nodos.

Se eliminaron 434 nodos pertenecientes a componentes pequeñas o aisladas.

Esto representa aproximadamente el 0.2767 % de los nodos.

La poda permite trabajar principalmente con la zona del mapa que se encuentra conectada y es útil para el cálculo de rutas.

## Nodo más cercano

Se desarrolló la función:

```python
find_nearest_node(latitude, longitude, coordinates)
```

Su objetivo es convertir unas coordenadas geográficas introducidas por el usuario en un nodo real del grafo.

Para evitar revisar los más de 156 mil nodos en cada consulta se utiliza una rejilla espacial con celdas de aproximadamente 0.002 grados.

Los nodos se agrupan según la celda donde se encuentran.

La búsqueda comienza en la celda correspondiente al punto recibido y se expande mediante anillos.

Cuando aparecen candidatos por primera vez también se revisa el siguiente anillo, ya que el nodo más cercano puede estar ubicado justo al otro lado del borde de una celda.

Después de reducir el conjunto de candidatos se utiliza Haversine para determinar cuál de ellos tiene realmente la menor distancia.

Como prueba se utilizó el punto:

Latitud: 18.4861

Longitud: -69.9312

El resultado obtenido fue:

Nodo: 310242934

Coordenadas del nodo: 18.4860185, -69.9315766

Distancia aproximada: 40.7361 metros

## Caché del grafo

Procesar nuevamente el archivo OSM cada vez que se inicia la aplicación sería innecesario.

Por esta razón el grafo procesado y sus coordenadas se almacenan utilizando `pickle` en:

`data/graph_cache.pkl`

El archivo generado actualmente ocupa aproximadamente 22 MB.

Cuando la caché existe, `build_graph()` carga directamente sus datos.

Cuando no existe, el sistema procesa el archivo OSM, construye el grafo y crea nuevamente la caché.

Tanto `santo_domingo.osm` como `graph_cache.pkl` están excluidos del repositorio mediante `.gitignore`.

## Resultados finales

Después del procesamiento se obtuvieron:

* Vías vehiculares: 32,263
* Nodos antes de la poda: 156,865
* Nodos finales: 156,431
* Nodos descartados: 434
* Porcentaje descartado: 0.2767 %
* Aristas dirigidas: 328,071
* Nodos con conexiones salientes: 156,415
* Nodos sin conexiones salientes: 16
* Aristas con nombre de calle: 168,167
* Aristas sin nombre: 159,904
* Aristas con distancia inválida: 0
* Aristas con tiempo inválido: 0
* Aristas con coordenadas faltantes: 0

## Pruebas realizadas

Se creó un archivo OSM pequeño específicamente para las pruebas automáticas.

Esto permite controlar exactamente qué resultado debe producir cada caso sin utilizar los 94 MB del mapa real.

Se comprobaron los siguientes comportamientos:

1. Una vía bidireccional genera conexiones en ambos sentidos.
2. Una vía con `oneway=yes` no permite circular en sentido contrario.
3. Todas las aristas tienen una distancia mayor que cero.
4. Todos los nodos utilizados en las aristas tienen coordenadas.
5. Las vías `footway` son excluidas.
6. El cálculo del tiempo utiliza `maxspeed` cuando existe y la velocidad predeterminada cuando no existe.
7. La búsqueda del nodo más cercano devuelve el nodo esperado.

Resultado:

`Ran 7 tests`

`OK`

Las siete pruebas fueron superadas.

## Contrato para los demás integrantes

La función principal que deben utilizar los demás componentes es:

```python
from src.graph_builder import build_graph

graph, coordinates = build_graph(
    "data/santo_domingo.osm"
)
```

La primera ejecución puede construir el grafo desde el archivo OSM.

Las siguientes ejecuciones cargarán automáticamente `data/graph_cache.pkl`.

Para convertir una coordenada en un nodo del grafo:

```python
from src.nearest_node import find_nearest_node

node_id = find_nearest_node(
    latitude,
    longitude,
    coordinates,
)
```

Los algoritmos de búsqueda deben utilizar los pesos existentes dentro de cada arista.

Para optimizar por distancia:

```python
graph[u][v]["distance_m"]
```

Para optimizar por tiempo:

```python
graph[u][v]["time_s"]
```

La distancia de una ruta completa debe calcularse sumando las distancias de sus aristas.

No se deben modificar directamente las estructuras `graph` ni `coordinates` desde los otros componentes.

## Dificultades encontradas

Una de las principales dificultades fue procesar correctamente un archivo XML de gran tamaño sin cargarlo completamente en memoria.

Esto se solucionó utilizando `iterparse()` y liberando progresivamente los elementos procesados.

También fue necesario tener cuidado al usar `elem.clear()`. Los elementos internos de una vía, como `nd` y `tag`, no pueden eliminarse antes de procesar el elemento `way` que los contiene.

Otra dificultad fue manejar correctamente las diferentes direcciones de las calles y las rotondas sin convertir accidentalmente el grafo en bidireccional.

Finalmente, para evitar búsquedas innecesarias entre más de 150 mil nodos, se implementó una rejilla espacial para la búsqueda del nodo más cercano.

## Conclusión

El resultado de esta parte es un grafo dirigido y ponderado construido directamente a partir de OpenStreetMap, preparado para ser utilizado por los algoritmos de búsqueda de rutas del proyecto.

El procesamiento conserva la dirección de las calles, utiliza distancias geográficas reales entre segmentos, estima el tiempo de recorrido, elimina pequeñas zonas aisladas y ofrece una forma eficiente de relacionar coordenadas con nodos del grafo.

Las validaciones realizadas y las siete pruebas automáticas permiten comprobar que el resultado cumple con el contrato establecido para la integración con los demás integrantes.

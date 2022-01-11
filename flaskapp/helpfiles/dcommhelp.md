Tras ver el tutorial sobre _"Ayuda de comentarios"_, habrás visto que hay dos tipos de resultados,  _árboles_ de comentarios o _estadísticas_ (Resúmenes de los árboles). Pongamos que has obtenido un árbol, de esta otra manera, quizá más completa. (El del tutorial anterior también valdrá para la demostración):

*(usuario) ->* `Propuestas sobre el tema "urbanismo"`
(chatbot) -> _Se va a proceder a buscar propuestas con estos parametros de búsqueda (filtros):_
*(usuario) ->* `No` - no más filtros, ejecutando la búsqueda
(chatbot) -> 
Mostrando resultados (10 de 11):
- 1) "Plan integral contra grafitis" (2015-09-15)(pid: 494)[830👍]
*(usuario) ->* `Comentarios de las propuestas anteriores` - (o pulsar _"Comentarios"_)
(chatbot) -> Bajo los criterios de búsqueda especificados, se han obtenido:
- Número de propuestas en la búsqueda: 11
- Media de comentarios: 117.27 [...]
*(usuario) ->* `(Hace click "Árbol de comentarios")`

(chatbot) -> Mostrando resultados (4 de 1301):
\[*L2*]-|-*P494*: "Plan integral contra grafitis" (2015-09-15)(pid: 494)[830👍]
\[*L3*]-|-_P494_->|*C162653*: francisca M.| "El otro dia estuve en el [...]

*Arriba nos ha salido un ÁRBOL DE COMENTARIOS. (similar al que llegamos en el tutorial anterior)*.

*Cada fila que empieza por un '-|-' es un 'resultado' del árbol; en este caso éstos son los comentarios buscados y las propuestas de los que surgieron*. Las propuestas empiezan por su identificador (id) en *negrita* (*P494*, por ejemplo en la línea *L2*). Los comentarios empiezan por el identificador de la propuesta (_en cursiva_) y, tras una serie de *'->|'* (cada '->|' implica que el comentario es a su vez respuesta de un comentario/propuesta anterior) *aparece el "id" del comentario*, (*C162653* en este primer caso). 

*Así, la línea L3 corresponde con el comentario C162653, que fue escrito directamente (1 sóla '->|') contra la propuesta con id P494*.

*En este punto podemos intentar obtener detalle de cualquier comentario del árbol anterior con:*

*(usuario) ->* `Ver comentario C142288`
(chatbot) -> 
Comentario de la propuesta 494 (cid: *142288*) por "ipino" \[...]

O bien, si obtienes demasiados resultados, antes *filtrar* de alguna manera el _árbol_ (mostrar sólo ciertos comentarios). Actualmente se permite por ejemplo:
*(usuario) ->* `Comentarios que contengan "Valdebebas"`
(chatbot) -> Bajo los criterios de búsqueda especificados, se han obtenido:
- Número de propuestas en la búsqueda: 3
- Media de comentarios: 51.67 \[...]

*(usuario) ->* `Ver comentarios` (o pulsa "Árbol comentarios") - (Esto incluye las propuestas)
(chatbot) -> Mostrando resultados (4 de 158):
-|-*P15711*: "STOP ARTEfacto Valdebebas" (2017-01-26)(pid: 15711)[3628👍]
-|-_P15711_->|*C132462*: '(No adecuado a búsqueda)' \[...]

NOTA: Si aparece '(No adecuado a búsqueda)' en algún comentario, quiere decir que éste no ha cumplido el requisito/s pedido/s, pero alguna respuesta al mismo sí. 

*También hay otras opciones, como ORDENAR por votos o controversia los comentarios, fíjate en los botones disponibles. La ordenación funciona por "niveles". Así, aparecerán en orden las propuestas, y dentro de cada propuesta, por orden los comentarios directos y por cada comentario, por orden las respuestas a los mismos y así sucesivamente hasta los comentarios sin respuesta*.

*Por último, podrá ver además los comentarios de un comentario, sin ver nada más. Para ello, tendrás que ver los *detalles* de un comentario y luego pulsar el botón para "ver comentarios".*

*Con esto concluye el tutorialARGUMENTOS básicoARGUMENTOS. *

_Te proponemos, para poner en práctica lo aprendido, que trates de llegar al detalle de un comentario que contenga el término "perros" dentro de un árbol cualquiera y que compruebes que es una respuesta a otro comentario de la propuesta P7._

ARGUMENTOSDirígete a _"Ayuda de Argumentos"_ para completar el tutorial. Se te explicará el resto de funcionalidad que aún no se ha presentado.ARGUMENTOS
En _"Ayuda de argumentos"_ vimos una breve introducción al concepto intuitivo de *argumento*. Aquí veremos de qué se componen (al nivel que se necesita para usar esta herramienta con el chatbot).

Los argumentos no son más que extracciones y resaltos de ciertas partes de algunas oraciones que se pueden encuadrar como *afirmaciones* (sentencias que afirma el usuario) y su correspondiente *premisa* (argumentos que defienden la afirmación), unidas por un *conector sintáctico* (_porque_,  _pero_, _para_, etc).

La combinación de esos elementos permite aproximar las _intenciones_ del usuario al escribir ese argumento, las cuales se entienden con un tándem de 2 tipologías argumentales combinadas para cada *argumento* detectado. Por ejemplo, en el argumento de abajo, _contraste(🎭)/oposición(😡)_ son esas dos tipologías que conforman la _intención_ del usuario y se entendería como que el usuario se _opone_ a su interlocutor _contrastando_ su visión con su argumento.

Esto es el detalle de un argumento, al que se accede siguiendo la secuencia de abajo,

(chatbot) -> (mostrando árbol)
*(usuario) ->* `Ver detalle del argumento A1236` (tras obtener un _árbol de argumentos_, como el de _"Ayuda de Argumentos"_)
(chatbot) -> *A1236* - Argumento positivo-apoyo(🟩) de la propuesta P7382 realizado en el comentario 'base' C53024, el cual responde al comentario 'raíz' C52953 por Carlos Díaz
URL propuesta: https://decide.madrid.es//proposals/7382-digitalizar-las-calles

"El pensar en suprimir mas tarde las placas de las calles es para ver de quitarnos la eterna lucha de los nombres, que incordian a muchos y pagamos los gastos todos."
El argumento, con carácter positivo-apoyo, tiene la intencionalidad consecuencia(👉)-objetivo(🎯) contra la afirmación (en cursiva)
"_El pensar en suprimir mas tarde las placas de las calles es_"
expresando la premisa (negrita):
"*ver de quitarnos la eterna lucha de los nombres , que incordian a muchos y pagamos los gastos todos*"
El conector "*para*", une ambas expresiones.
El comentario base (del que se extrajo el argumento) tiene 0 votos

*Verás que tienes la opción de ver la propuesta y el comentario base de los cuales salió este comentario, así como navegar al comentario del que salió el comentario base* (el _"raíz"_) *y ver comentarios o argumentos desde el comentario base* (click en _"Ver respuestas (argumentales)/(comentarios)"_). 

*Hay otra característica especial de los argumentos, y es que el chatbot permite formar grupos de argumentos con la misma* _intencionalidad_ *demostrada por el usuario en su argumentación*. Las agrupaciones se pueden hacer en los listados de _árboles de argumentos_ o _árboles completos_, pero siempre contendrán exclusivamente argumentos. Los resultados que se obtienen son, por cada "página", las _estadísticas_ o _resúmenes de resultados_ de los argumentos de cada intencionalidad (de cada combinación de 2 de esos "tipos" de argumentación):

*(usuario) ->* `Argumentos por intención` (tras obtener un _árbol de argumentos_, como el de _"Ayuda de Argumentos"_)
(chatbot) -> Mostrando resultados (3 de 12):

-|-Agrupando por...
- 'causa(🤔➡️)'
- 'razón(🧐)' \[...]

*(usuario) ->* `Ver más` (o pulsa en "Ver más") - (*así se ven las siguientes "páginas" o grupos de argumentos con la siguiente común intencionalidad*)
(chatbot) -> Mostrando resultados (6 de 12):

-|-Agrupando por...
- 'causa(🤔➡️)'
- 'condición(🚦)' \[...]

Y así hasta ver todos los grupos de argumentos para cada intención encontrada en ellos. 

Esto concluye el tutorial. Hay más funcionalidad, pero es bastante intuitiva y el chatbot te seguirá guiando en casi todo momento, así que no te preocupes. Esta referencia siempre la tendrás disponible con sólo escribir _"ayuda"_ y navegar hacia las opciones que quieras.


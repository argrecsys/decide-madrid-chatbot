# Chatbot argumentativo para gobierno electrónico

Agente conversacional para la exploración de información argumentativa en plataformas de participación electrónica. Este proyecto es la base de código utilizado en el Trabajo de Fin de Grado de Informática del autor principal, Andrés Holgado Sánchez ([ahsholgadosanchez@gmail.com]()), en su Doble Grado de Informática y Matemáticas cursado en la Universidad Autónoma de Madrid bajo la tutela del profesor Iván Cantador ([ivan.cantador@uam.es]()).

## Finalidad del proyecto
El presente proyecto utiliza un snapshot de la base de datos de la plataforma de propuestas ciudadanas [Decide Madrid](https://decide.madrid.es/). Los propósitos de la plataforma consisten en permitir a los ciudadanos hacer propuestas para el ayuntamiento de Madrid de forma que se puedan aprobar las propuestas más votadas. En nuestro estudio, pretendemos hacer un chatbot que permita al ciudadano consultar las propuestas ya existentes de forma más productiva que simplemente buscando a mano, de forma que éste pueda hacer una votación más fundada a la hora de seleccionar qué propuestas votar o no. Para ello, el chatbot permitirá buscar las propuestas de forma textual y buscar con muchos filtros sin necesidad de utilizar la plataforma oficial, que es mucho más rígida. 
Además, el chatbot permitirá buscar argumentos a favor y en contra de las propuestas encontradas. Estos argumentos no existen en la base de datos actual, y serán generados mediante un sistema original propuesto e implementado sobre los mismos datos por el doctorando Germán Andrés Segura Tinoco (en su [proyecto de Github relacionado](https://github.com/argrecsys/arg-miner/)) dentro de sus estudios en la Universidad Autónoma de Madrid, con un prototipo presentado en [Joint Workshop of the 3rd Edition of Knowledge-aware and Conversational Recommender Systems (KaRS) and the 5th Edition of Recommendation in Complex Environments (ComplexRec)](http://ceur-ws.org/Vol-2960/).

El agente está compuesto por varios elementos, no todos presentes en este repositorio.

## Estructura del chatbot
Un elemento fundamental es el framework [DialogFlow ES](https://cloud.google.com/dialogflow/es/docs), que es el que implementa el flujo conversacional. La implementación para este chatbot se realiza en la propia plataforma, sin código fuente, por lo que no es posible compartirlo por aquí. 

En DialogFlow se definen unas situaciones conversacionales llamados "Intents", que para cada posible petición del usuario, dan una o varias respuestas asociadas. Usando machine Learning, se pueden extraer parámetros y datos útiles de las peticiones. 

Las respuestas se pueden indicar en el propio framework de DialogFlow, pero en nuestro caso, al haber tanta lógica interna, hemos optado por utilizar el recurso llamado "[fulfillment](https://cloud.google.com/dialogflow/es/docs/fulfillment-overview)", que es simplemente la delegación de la creación de las respuestas en un servicio web externo. 

Este servicio externo debe ser capaz de interpretar peticiones [Webhook](https://cloud.google.com/dialogflow/es/docs/fulfillment-webhook?hl=es-419) para leer las peticiones del usuario y datos asociados (parámetros, contextos, etc) y en base a ello, elaborar una respuesta que se enviará en un formato similar de vuelta al agente de DialogFlow.

Además de la comunicación DialogFlow - Servidor WebHook, se facilita una [integración con un bot de Telegram](https://cloud.google.com/dialogflow/es/docs/integrations/telegram?hl=es-419), que simplemente realiza comunicación con DialogFlow para enviarle las preguntas del usuario y para recibir posteriormente las respuestas que produce DialogFlow (o el Webhook).

El enlace al chatbot de Telegram, que puede usarse actualmente (puede que no funcione de manera continuada porque está en desarrollo) es:
[https://t.me/chat_tfg_coll_bot](https://t.me/chat_tfg_coll_bot)

## Servidor Webhook (repositorio)
El presente repositorio aloja el código utilizado por el servidor de Webhook, que ha sido implementado usando la herramienta [Flask](https://flask.palletsprojects.com/en/2.0.x/) para creación de servidores sencillos y el uso de algunas librerías externas para el manejo de peticiones Webhook. El servidor se aloja en la plataforma [Heroku](https://devcenter.heroku.com/categories/reference), y usando la facilidad Heroku Postgres para mantener la base de datos.

## Datos utilizados
La base de datos de Decide Madrid ha sido ligeramente modificada para albergar una serie de métricas y una estructura argumental pregenerada para mejorar la búsqueda de argumentos en comentarios y propuestas. El chatbot además, mejora temporalmente en memoria las relaciones argumentativas representables en la base de datos a petición de los usuarios.

## Librerías externas destacadas
* [pydialogflow-fulfillment](https://pypi.org/project/pydialogflow-fulfillment/): Apache Software License. Usada para manejar peticiones Webhook
* [SQLAlchemy](https://www.sqlalchemy.org/): Python sponsored, MIT license. Usada para manejar la base de datos
* [Flask](https://flask.palletsprojects.com/en/2.0.x/): BSD-3-Clause Source License, Pallets 2010. Librería que facilita el uso y creación de servidores cualesquiera en Python.

## Instalación
Este código está pensado para ser ejecutado con un entorno virtual y con una infraestructura muy concreta que depende del establecimiento de una conexión remota con un servidor dedicado (como se explica por encima en la sección anterior), así que si desea probar a ejecutar este proyecto en su máquina, necesita ponerse en contacto con los desarrolladores.

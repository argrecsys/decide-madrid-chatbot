# Decide madrid 2019 Chatbot
![version](https://img.shields.io/badge/version-1.0.0-blue)
![last-update](https://img.shields.io/badge/last_update-11/01/2022-orange)
![license](https://img.shields.io/badge/license-Apache_2.0-brightgreen)

Chatbot of the [Decide Madrid](https://decide.madrid.es/) 2019 system. This version was used in the [DGO.2022 conference](https://dgsociety.org/dgo-2022/).

## Solution
This repository contains the [fulfillment](https://cloud.google.com/dialogflow/es/docs/fulfillment-overview) section described in the article "_A Conversational Agent for Argument-driven E-participation_", used for the [(DGO 2022) 23st Annual International Conference on Digital Government Research
Theme: Intelligent Technologies, Governments and Citizens](https://dgsociety.org/dgo-2022/). This is, therefore, Flask Server source code ready to be installed in a Heroku server. It accepts [Webhook](https://cloud.google.com/dialogflow/es/docs/fulfillment-webhook?hl=es-419) petitions (JSON formatted POST requests with specific contents) at https://chatbot-tfg-server.herokuapp.com/webhook.

Interaction to this server is automatically managed by a [DialogFlow ES](https://cloud.google.com/dialogflow/es/docs) conversational agent. Then, an integration via Telegram is used to simplify user access to the chatbot, which can be accessed via this Telegram user link: [https://t.me/chat_tfg_coll_bot](https://t.me/chat_tfg_coll_bot)
## Resources
This project uses arguments extracted in this [repository](https://github.com/argrecsys/arg-miner) by  <a href="https://github.com/ansegura7" target="_blank">Andrés Segura-Tinoco</a> in this organization.

## Deployment - Results
For the experiment, two populations where considered: one with and one without facilities to gather arguments from the proposals or comments.
This separation is considered in this version of the chatbot. The solution to gather these two populations was taking Telegram's permanent `chat_id` of each user as a key for each user. Each new `chat_id` (each new user interacting with the chatbot) is either asigned a version with arguments or without arguments if the last user had no arguments and viceversa, respectively and that characteristic is annotated in the following interaction "logs", which allowed the experiments to be analyzed. [Logs can be seen with this Heroku link](https://data.heroku.com/dataclips/igegnagpokdriykszurgvflxivvy)

## Server structure and architecture
Main folder contains environment variables and other Heroku server deployment files.

Server files and source code is located under `/flaskapp` [folder](https://github.com/argrecsys/decide-madrid-chatbot/blob/main/flaskapp/).

Server routes file is located [here](https://github.com/argrecsys/decide-madrid-chatbot/blob/main/flaskapp/__init__.py). One endpoint is used (https://chatbot-tfg-server.herokuapp.com/webhook) for all the chatbot interactions, the others being used for maintenance purposes.

The way Dialogflow interactions work is via conversational intents, or conversational situations automatically detected under certain user inputs. That intent information is passed to this server in a webhook petition, which is analyzed and then a python method is called to solve that conversational intent according to other metadata read in the DialogFlow platform (entities, parameters, contexts,...)

More explicitly, in the file `intents.py` ([here](https://github.com/argrecsys/decide-madrid-chatbot/blob/main/flaskapp/intents.py)) an IntentManager class is instantiated once for each `chat_id`. Then, when a user with a specific `chat_id` puts an input to DialogFlow, that platform sends to this server a webhook petition with the detected intent name and analyzed metadata. The server reads the `chat_id` and the corresponding IntentManager is invoked. Inside it, a method with name the one of the given intent and a `dfr` parameter (where all the metadata is supplied) is called to produce the final webhook answer which is sent back to DialogFlow as an HTTP response.

Database management is used via [SQLAlchemy](https://www.sqlalchemy.org/) ORM facilities. The structure can be found in the `models.py` [file](https://github.com/argrecsys/decide-madrid-chatbot/blob/main/flaskapp/intents.py).

Other modules are just used to distribute functionality implementation.

## Main Dependencies
- [pydialogflow-fulfillment 0.1.4](https://pypi.org/project/pydialogflow-fulfillment/): Apache Software License. Webhook petitions facility
- [SQLAlchemy 1.4.21](https://www.sqlalchemy.org/): Python sponsored, MIT license. Database management
- [Flask 2.0.1](https://flask.palletsprojects.com/en/2.0.x/): BSD-3-Clause Source License, Pallets 2010. Server library
## Other dependencies
- Flask SQLAlchemy 2.5.1
- Gunicorn 20.1.0
- Psycopg2 2.8.6
- Python YAML 6.0
 
## Authors
Created on Dec 31, 2021  
Created by:
- <a href="https://github.com/andresh26-uam" target="_blank">Andrés Holgado-Sánchez</a>

## License
This project is licensed under the terms of the <a href="https://github.com/argrecsys/decide-madrid-chatbot/blob/main/LICENSE">Apache License 2.0</a>.

## Acknowledgements
This work was supported by the Spanish Ministry of Science and Innovation (PID2019-108965GB-I00) and the Centre of Andalusian Studies (PR137/19). The authors thank to all people who participated in the reported study.

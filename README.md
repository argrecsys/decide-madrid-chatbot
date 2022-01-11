# Decide madrid 2019 Chatbot
![version](https://img.shields.io/badge/version-1.0.0-blue)
![last-update](https://img.shields.io/badge/last_update-11/01/2022-orange)
![license](https://img.shields.io/badge/license-Apache_2.0-brightgreen)

Chatbot of the [Decide Madrid](https://decide.madrid.es/) 2019 system. This version was used in the [DGO.2022 conference](https://dgsociety.org/dgo-2022/).

## Solution
This repository contains the fulfillment section described in the article (TODO: PAPER). This is, therefore, Flask Server source code ready to be installed in a Heroku server. It accepts webhook petitions (JSON formatted POST requests with specific contents) at https://chatbot-tfg-server.herokuapp.com/webhook.

Interaction to this server is automatically managed by a [DialogFlow ES](https://cloud.google.com/dialogflow/es/docs) conversational agent. Then, an integration via Telegram is used to simplify user access to the chatbot, which can be accessed via this Telegram user link:
## Resources
This project uses arguments extracted in this [repository](https://github.com/argrecsys/arg-miner) by  <a href="https://github.com/ansegura7" target="_blank">Andrés Segura-Tinoco</a> in this organization. 

## Deployment - Results
For the experiment at (TODO: PAPER), two populations where considered: one with and one without facilities to gather arguments from the proposals or comments.
This separation is considered in this version of the chatbot. The solution to gather these two populations was taking Telegram's permanent `chat_id` of each user as a key for each user. Each new `chat_id` (each new user interacting with the chatbot) is either asigned a version with arguments or without arguments if the last user had no arguments and viceversa, respectively and that characteristic is annotated in the following interaction "logs", which allowed the experiments to be analyzed. [Logs can be seen with this Heroku link](https://data.heroku.com/dataclips/igegnagpokdriykszurgvflxivvy)


## Authors
Created on Dec 31, 2021  
Created by:
- <a href="#" target="_blank">Andrés Holgado-Sánchez</a>

## License
This project is licensed under the terms of the <a href="https://github.com/argrecsys/decide-madrid-chatbot/blob/main/LICENSE">Apache License 2.0</a>.

## Acknowledgements
This work was supported by the Spanish Ministry of Science and Innovation (PID2019-108965GB-I00) and the Centre of Andalusian Studies (PR137/19). The authors thank to all people who participated in the reported study.

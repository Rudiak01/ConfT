Prérequis : Python 3.8 ou supérieur.

- Ouvrez un terminal dans le dossier du projet
- Faire un environnement python : 
    py -m venv env
- Activer les scripts :
    (Linux/Mac)
        source env/bin/activate
    (Windows)
        env\Scripts\activate
- Installez les librairies : 
    python3 -m pip install -r back/requirements.txt
- Lancer les scripts avec : 
    python3 -m back.nomduscript

En cas d'erreur avec les templates TextFSM, définissez la variable d'environnement NET_TEXTFSM pointant vers le dossier des templates (Netmiko s'en charge normalement tout seul si ntc-templates est installé via pip).
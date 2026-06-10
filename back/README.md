Prérequis Système :

Python 3.8 ou supérieur.

Installation des dépendances :

Ouvrez un terminal dans le dossier du projet.

(Recommandé) Créez un environnement virtuel : python -m venv venv

Activez-le : source venv/bin/activate (Linux/Mac) ou venv\Scripts\activate (Windows).

Installez les librairies : pip install -r requirements.txt

Important : Pour que Netmiko trouve les templates TextFSM, définissez la variable d'environnement NET_TEXTFSM pointant vers le dossier des templates (Netmiko s'en charge souvent tout seul si ntc-templates est installé via pip, mais c'est bon à savoir en cas d'erreur).
Prérequis : Python 3.8 ou supérieur.

- Ouvrez un terminal dans le dossier du projet.
- Faire un environnement Python :
  ```bash
  py -m venv env
  ```
- Activer les scripts :
  - **Linux/Mac**
    ```bash
    source env/bin/activate
    ```
  - **Windows**
    ```powershell
    env\Scripts\activate
    ```
- Installez les librairies :
  ```bash
  python3 -m pip install -r back/requirements.txt
  ```
- Lancez les scripts avec :
  ```bash
  python3 -m back.nomduscript
  ```

En cas d'erreur avec les templates TextFSM, définissez la variable d'environnement `NET_TEXTFSM` pointant vers le dossier des templates (Netmiko s'en charge normalement tout seul si `ntc-templates` est installé via `pip`).
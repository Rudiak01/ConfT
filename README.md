# ConfT - Network Configuration Tool

ConfT is a web-based network configuration and topology mapping tool. It uses a Flask backend with SQLAlchemy and a MariaDB database to store network nodes, edges, and their configurations, and provides a graphical interface (D3.js) to interact with them.

## Prerequisites

- **Python 3.8+**
- **Docker** and **Docker Compose** (for the MariaDB and phpMyAdmin services)
- The Python virtual environment should be set up in the `env` folder with the necessary dependencies installed (`flask`, `flask-cors`, `sqlalchemy`, `pymysql`, `paramiko`, etc.).

## Project Structure

- `api/`: Contains the Flask backend application (models, database connection, routes).
- `back/`: Contains backend scripts for extracting and applying configurations to network devices (Netmiko-based, functional implementation).
- `front/`: Frontend files (HTML, CSS, JavaScript with D3.js).
- `node_edge/`: Sample topology data files.
- `compose.yml`: Docker Compose configuration for MariaDB and phpMyAdmin.
- `start.bat`: Launch script to easily start the database and the web server.
- `.env`: Environment variables (credentials, secrets — not tracked by git).

## How to Launch

To easily start the application, simply run the provided `start.bat` script:

1. Double-click on `start.bat` or run it from a command prompt:
   ```cmd
   start.bat
   ```

**What `start.bat` does:**
1. *(Commented out)* Starts the Docker containers (MariaDB and phpMyAdmin) in the background.
2. Activates the Python virtual environment (`env`).
3. Starts the Flask web server on port 5000.

## Accessing the Application

Once launched, you can access the application at:
- **ConfT Web Interface**: [http://localhost:5000](http://localhost:5000)
- **phpMyAdmin** (Database Management): [http://localhost:8080](http://localhost:8080)

## Database

The application uses MariaDB accessible at `127.0.0.1:3306`. Default credentials are configured in `.env`:
- User: `root`
- Password: `test`
- Database: `test`

## Troubleshooting

- **Database Connection Error**: If you see a MySQL connection error `[WinError 10061]`, ensure that Docker is running and the MariaDB container has started successfully (`docker compose up -d`).
- **Missing dependencies**: Run `pip install -r api/requirements.txt` to install all Python dependencies.

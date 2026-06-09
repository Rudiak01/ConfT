# ConfT - Network Configuration Tool

ConfT is a web-based network configuration and topology mapping tool. It uses a FastAPI backend with a MariaDB database to store network nodes, edges, and their configurations, and provides a graphical interface to interact with them.

## Prerequisites

- **Python 3.8+**
- **Docker** and **Docker Compose** (for the MariaDB and phpMyAdmin services)
- The Python virtual environment should be set up in the `env` folder with the necessary dependencies installed (`fastapi`, `uvicorn`, `sqlalchemy`, `pymysql`, `pydantic`, etc.).

## Project Structure

- `api/`: Contains the FastAPI backend application (models, database connection, routes).
- `back/`: Contains backend scripts for extracting and applying configurations to network devices.
- `js/`, `node_edge/`, `index.html`, `style.css`: Frontend files (HTML, CSS, JavaScript).
- `compose.yml`: Docker Compose configuration for MariaDB and phpMyAdmin.
- `start.bat`: Launch script to easily start the database and the web server.

## How to Launch

To easily start the application, simply run the provided `start.bat` script:

1. Double-click on `start.bat` or run it from a command prompt:
   ```cmd
   start.bat
   ```

**What `start.bat` does:**
1. Starts the Docker containers (MariaDB and phpMyAdmin) in the background.
2. Waits a few seconds for the database to initialize.
3. Activates the Python virtual environment (`env`).
4. Starts the FastAPI web server using `uvicorn`.

## Accessing the Application

Once launched, you can access the application at:
- **ConfT Web Interface**: [http://localhost:8000](http://localhost:8000)
- **phpMyAdmin** (Database Management): [http://localhost:8080](http://localhost:8080)
- **API Documentation** (Swagger UI): [http://localhost:8000/docs](http://localhost:8000/docs)

## Troubleshooting

- **Database Connection Error**: If you see a MySQL connection error `[WinError 10061]`, ensure that Docker is running and the MariaDB container has started successfully.
- **Import Error (Relative Import)**: The server must be started via `uvicorn api.main:app` rather than directly executing the python file. `start.bat` handles this automatically.

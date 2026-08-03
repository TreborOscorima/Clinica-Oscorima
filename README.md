# Sistema de Gestión para Clínica Estética (Flask + MySQL + HTML/JS/CSS)

Proyecto inicial **listo para correr localmente** con autenticación JWT, roles y dos módulos funcionales (Pacientes y Turnos) para que puedas probar y extender. Frontend en **HTML + JavaScript puro + CSS** sirviendo desde Flask; Backend en **Python + Flask + SQLAlchemy**; DB **MySQL**.

## Requisitos
- Python 3.11+
- MySQL 8+
- (Opcional) PowerShell/Terminal con `python -m venv`

## Configuración rápida (local)
1. Clona o descomprime este proyecto.
2. Crea entorno virtual e instala dependencias:
   ```bash
   cd WaykiSAC
   python -m venv .venv
   # Windows PowerShell
   .venv\Scripts\Activate.ps1
   # Linux/Mac
   # source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Crea base de datos MySQL y credenciales:
   ```sql
   CREATE DATABASE life_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER 'clinica_user'@'localhost' IDENTIFIED BY 'clinica_pass';
   GRANT ALL PRIVILEGES ON life_db.* TO 'clinica_user'@'localhost';
   FLUSH PRIVILEGES;
   ```
4. Crea archivo `.env`:
   ```ini
   FLASK_ENV=development
   AUTH_SECRET_KEY=super-secreto-123
   JWT_SECRET_KEY=jwt-super-secreto-123
   MYSQL_USER=clinica_user
   MYSQL_PASSWORD=clinica_pass
   MYSQL_HOST=127.0.0.1
   MYSQL_PORT=3306
   MYSQL_DB=life_db
   ```
5. Inicializa la app y crea tablas:
   ```bash
   # desde la raíz del proyecto
   python app.py db_create
   python app.py seed_admin
   python app.py run
   ```
6. Abre el navegador en: **http://localhost:5000**  
   Usuario de prueba: **admin@clinic.local** / **Admin123!**

## Estructura
- `app.py`: punto de entrada con comandos utilitarios (crear DB, seed de admin, correr servidor)
- `config.py`, `extensions.py`: configuración y extensiones (SQLAlchemy, Marshmallow, JWT, CORS)
- `models/`: modelos SQLAlchemy
- `schemas/`: validación/serialización con Marshmallow
- `routes/`: Blueprints (auth, pacientes, turnos, placeholders de otros módulos)
- `utils/`: decoradores y auditoría
- `templates/`, `static/`: frontend HTML/JS/CSS con menú lateral y pantallas básicas

## Notas
- Los módulos **Caja/Facturación**, **Inventario**, **Servicios**, **Profesionales**, **Reportes** vienen con rutas *placeholder* para ampliar.
- Exportaciones (CSV/PDF) tienen endpoint de ejemplo para CSV. PDF queda preparado para ampliar con WeasyPrint o ReportLab.
- Auditoría básica registra IP, usuario y acción.

¡Ajustá a gusto y desplegá luego en tu hosting (uWSGI/Gunicorn + Nginx recomendado)!

./env/Scripts/activate

$Env:MARIADB_STRING="mysql+pymysql://root:test@localhost/test?charset=utf8mb4"
$Env:SOCIETY_ADMIN_PASSWORD="admin123"
$Env:SOCIETY_ADMIN_EMAIL="admin@societe.fr"
$Env:FASTAPI_SECRET_KEY="600e617a213d68266c2f52c9f4f0bf378a9c909650aa311ecb41eaafc3af18c4"
$Env:IS_DEV="True"
$Env:EXPOSE_PORT="8000"


python -m api.main
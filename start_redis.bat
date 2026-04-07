@echo off
:: start_redis.bat — Inicia Redis portable para desarrollo
:: Ejecutar como usuario normal (no requiere administrador)

SET REDIS_DIR=C:\Users\%USERNAME%\AppData\Local\Redis
SET REDIS_SERVER=%REDIS_DIR%\redis-server.exe
SET REDIS_CLI=%REDIS_DIR%\redis-cli.exe

echo [WaykiSAC] Verificando Redis...
%REDIS_CLI% ping >nul 2>&1
IF %ERRORLEVEL% == 0 (
    echo [WaykiSAC] Redis ya esta corriendo en localhost:6379
    goto :end
)

echo [WaykiSAC] Iniciando Redis en puerto 6379...
START "" /B "%REDIS_SERVER%" --port 6379 --loglevel warning --save 60 1

timeout /t 2 /nobreak >nul

%REDIS_CLI% ping >nul 2>&1
IF %ERRORLEVEL% == 0 (
    echo [WaykiSAC] Redis iniciado correctamente ^(PONG recibido^)
) ELSE (
    echo [ADVERTENCIA] Redis no pudo iniciarse. El rate limiting usara memoria RAM.
    echo               Verifica que %REDIS_SERVER% exista.
)

:end

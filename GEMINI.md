# Reglas del Proyecto - Timba Predictor

## 🔄 Flujo de Git y Despliegue Obligatorio (Memoria Permanente)
En cada tarea o cambio realizado en este repositorio (`proyecto timba ver 2` / `1nachu/timba-predicciones`):

1. **Verificación**: Correr las pruebas necesarias (`PYTHONPATH=src .venv/bin/pytest`) para asegurar integridad.
2. **Stage**: Ejecutar `git add` de los archivos modificados o creados.
3. **Commit**: Ejecutar `git commit` con un mensaje claro y descriptivo siguiendo Conventional Commits (ej. `feat: ...`, `fix: ...`, `refactor: ...`).
4. **Push**: Ejecutar `git push origin main` para sincronizar inmediatamente con el repositorio remoto en GitHub.

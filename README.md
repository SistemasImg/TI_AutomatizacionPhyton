# TI_AutomatizacionPhyton

## Configuración local

Instala las dependencias con `python -m pip install -r requirements.txt`.
Si aún no tienes un `.env`, copia `.env.example` a `.env` en la misma carpeta
que los scripts y completa los valores de las integraciones que vas a usar.

- `SF_*`: autenticación de Salesforce para los cuatro scripts que la usan.
- `SMTP_*`: credenciales de los scripts que envían correo.
- `API_*`: credenciales y URLs de las integraciones de `API Sender.py`. Algunas
  funciones comparten la misma URL o clave.

Las variables definidas en el entorno tienen prioridad sobre `.env`. Si falta
una variable requerida, el error identifica su nombre sin mostrar su valor.
`MarkdownConverter.py` no necesita credenciales.

Sube `.env.example`, nunca `.env`. Si GitHub bloquea el envío por un secreto
en un commit anterior, limpiar el archivo actual no basta: rota la credencial
y quita el secreto del historial que vas a publicar. No omitas la protección de GitHub.
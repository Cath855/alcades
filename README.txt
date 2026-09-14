VISOR STREAMLIT - DESPLIEGUE SEGURO

1. El Survey ID permanece fijo en 916501.
2. No subas .streamlit/secrets.toml a Git.
3. Streamlit Community Cloud:
   - App > Settings > Secrets
   - Copia el contenido de .streamlit/secrets.toml.example
   - Sustituye los placeholders por las claves reales.
4. Servidor propio:
   - Copia .streamlit/secrets.toml.example a .streamlit/secrets.toml
   - Completa las claves reales.
   - Ejecuta: streamlit run app.py
5. El código valida TLS (ya no usa verify=False).
6. Tras validar funcionamiento, rota la clave api_visor porque existió en texto plano en una versión previa.

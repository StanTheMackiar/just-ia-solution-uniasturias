# Entregables – Caso Práctico Unidad 1 (IA Aplicada al Desarrollo de Software)
Stanly Leon Calle Samper

- **Caso Practico Unidad 1 - IA Aplicada al Desarrollo de Software.docx**: documento con la solución, la justificación de cada actividad, la aplicación práctica y las referencias APA.

| Carpeta | Contenido | Cómo se ejecuta |
|---|---|---|
| Actividad 1 - Preprocesamiento | `actividad1_preprocesamiento.py`, corpus original (62 fragmentos) y corpus limpio (.csv y .json) | `python3 actividad1_preprocesamiento.py` |
| Actividad 2 - Diccionario juridico | `diccionario_juridico.json`, `actividad2_clasificador.py` (función `predecir_categoria`), `preguntas_prueba.csv` | `python3 actividad2_clasificador.py` o `python3 actividad2_clasificador.py "texto"` |
| Actividad 3 - Consola JustIA | `actividad3_justia_consola.py`, capturas de pantalla, documentos de prueba y registro de trazabilidad | `python3 actividad3_justia_consola.py` |

Requisitos: Python 3.9+. Solo usa la librería estándar; para leer PDF en la actividad 3 se necesita `pypdf` (`pip install pypdf`). Si spaCy y `es_core_news_sm` están instalados, la actividad 1 los usa para lematizar.
Las actividades 2 y 3 reutilizan el código de las anteriores, por eso las tres carpetas deben quedar juntas.
Todos los textos del corpus y los documentos de prueba son simulados con fines académicos.

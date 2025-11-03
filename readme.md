\# Gestor de Notas por Módulo (Mecatrónica Industrial)



Aplicación web creada con Streamlit para gestionar las calificaciones por módulos y resultados de aprendizaje (RAs).



\## Características principales

\- Roles: \*\*Tutor\*\* y \*\*Profesor\*\*

\- El tutor puede \*\*importar o editar\*\* la lista de alumnos (desde Excel o manualmente)

\- Los profesores pueden \*\*calificar alumnos existentes\*\*

\- Cada módulo tiene varios \*\*RAs con pesos personalizados\*\*

\- Control de \*\*asistencia\*\* (si < 80% → N.C)

\- Registro de \*\*notas por trimestre\*\*: Diciembre, Marzo, Ordinaria 1 (OR1), Ordinaria 2 (OR2)

\- Cálculo automático de nota final redondeada

\- Exportación a Excel / CSV

\- Base de datos compartida (`notas\_modulos.db`)



\## Ejecución local

```bash

pip install -r requirements.txt

streamlit run app.py




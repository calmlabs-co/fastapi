## 💁‍♀️ How to use

### Use Conda to manage environment
`conda env create -f environment.yml`

- Run locally using `python runserver.py`

## 📝 Notes

- To learn about how to use FastAPI with most of its features, you can visit the [FastAPI Documentation](https://fastapi.tiangolo.com/tutorial/)
- To learn about Uvicorn and how to configure it, read their [Documentation](https://www.uvicorn.org/)

# Project
##  Structure
The project is organized into several directories and files, each serving a specific purpose:
backend/app: Contains the main application logic, including API endpoints, models, schemas, and core settings.
backend/data: Contains initial data to be loaded into the database.
frontend/login: Contains the frontend templates and static files for the login page.
backend/security: Contains security-related code, such as user authentication.
backend/tests: Presumably contains test cases (though not shown in the snippets).
### Main Application Entry Point
`backend/app/main.py `
-  sets up the FastAPI application, including middleware, routers, and the database initialization.
### Database Initialization
`backend/app/dependencies/database.py`

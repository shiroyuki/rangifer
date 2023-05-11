# Rangifer

**Rangifer** is an asynchronous web framework (based on FastAPI) primarily designed for scientific applications.

**What not using FastAPI directly?**
* It emphasizes the easy/simplified setup or convention for common tasks, e.g., DB configuration, web handlers, etc.
* Configurable via a configuration file in JSON/YAML format.
* Configuration can be overridden with environment
* As it is based on FastAPI, you still can do absolutely everything that FastAPI allows you to.

**What is it for?**
* Fast prototype
* Scientific applications

**What will be available right out of the box?**
* Automatic Dependency Injection (with `imagination`)
* Automatic Scanning for Web Handlers (methods or classes)
* Optional: Basic Relational DB Data Accessor based on SQLAlchemy (asynchronous)
* Optional: Basic Relational DB Migration Tool based on SQLAlchemy and "Unnamed external DB migration tool"
* Optional: Template Rendering with Jinja2
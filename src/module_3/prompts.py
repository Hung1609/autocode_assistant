import logging

logger = logging.getLogger(__name__)

# --- Generic Fallback Prompt ---
# Used when no specific prompt matches the file type
GENERIC_CODE_PROMPT = """
Generate the complete, production-ready code for the file specified below, based *only* on the provided context.
Adhere strictly to the details in the context, including file path, description, technology stack, and any relevant design specifications (APIs, data models, etc.).
Follow best practices for the specified language and framework.
Output *only* the raw code for the file '{file_path}'. Do not include any explanations, comments outside the code, or markdown formatting.

Context:
```json
{context}
```

Code for {file_path}:
"""

# --- Backend Model/Schema Prompts ---

# Example for Python/Flask/SQLAlchemy (or similar ORM)
FLASK_SQLALCHEMY_MODEL_PROMPT = """
Generate the complete Python code for a SQLAlchemy model file based *only* on the provided context.
The file path is '{file_path}'.
Define the SQLAlchemy model class(es) corresponding to the data models specified in the context's `data_design.data_Models`.
Implement all fields with the correct SQLAlchemy column types and constraints (primary keys, foreign keys, nullability, uniqueness) as detailed in the `fields` and `relationships` sections of the data models.
Include necessary imports (e.g., `from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey`, `from sqlalchemy.orm import relationship`, `from .database import Base` - assuming a Base declarative base exists).
Follow standard Python and Flask/SQLAlchemy conventions.
Output *only* the raw Python code for the file. Do not include explanations or markdown.

Context:
```json
{context}
```

Code for {file_path}:
"""

# Example for Node.js/Express/Mongoose
NODE_MONGOOSE_MODEL_PROMPT = """
Generate the complete JavaScript code for a Mongoose schema and model file based *only* on the provided context.
The file path is '{file_path}'.
Define the Mongoose schema(s) corresponding to the data models specified in the context's `data_design.data_Models`.
Implement all fields with the correct Mongoose schema types (String, Number, Boolean, Date, ObjectId, Array) and options (required, unique, default, ref for relationships) as detailed in the `fields` and `relationships` sections of the data models.
Include necessary imports (`const mongoose = require('mongoose'); const Schema = mongoose.Schema;`).
Export the Mongoose model (`module.exports = mongoose.model('ModelName', modelSchema);`).
Follow standard Node.js and Mongoose conventions.
Output *only* the raw JavaScript code for the file. Do not include explanations or markdown.

Context:
```json
{context}
```

Code for {file_path}:
"""

# --- Backend Controller/Router Prompts ---

# Example for Python/Flask
FLASK_CONTROLLER_PROMPT = """
Generate the complete Python code for a Flask Blueprint route/controller file based *only* on the provided context.
The file path is '{file_path}'.
Implement Flask routes for the API endpoints defined in the context's `interface_Design.api_Specifications` that seem relevant to this controller's likely responsibility (inferred from the file path or description).
For each route:
- Use the correct HTTP method (`@blueprint.route('/path', methods=['METHOD'])`).
- Implement basic request handling (e.g., getting data from `request.json` or `request.args`).
- Include placeholder comments (`# TODO: Add validation`, `# TODO: Add business logic/service call`, `# TODO: Interact with models`) for the core logic.
- Return appropriate JSON responses (e.g., `jsonify(data), status_code`) based on the API specification's success/error schemas.
- Include necessary imports (e.g., `from flask import Blueprint, request, jsonify`, potentially model imports).
Follow standard Python and Flask conventions.
Output *only* the raw Python code for the file. Do not include explanations or markdown.

Context:
```json
{context}
```

Code for {file_path}:
"""

# Example for Node.js/Express
NODE_EXPRESS_ROUTER_PROMPT = """
Generate the complete JavaScript code for an Express router file based *only* on the provided context.
The file path is '{file_path}'.
Implement Express routes (`router.METHOD('/path', handler)`) for the API endpoints defined in the context's `interface_Design.api_Specifications` that seem relevant to this router's likely responsibility (inferred from the file path or description).
For each route handler:
- Implement basic request handling (e.g., accessing `req.body`, `req.params`, `req.query`).
- Include placeholder comments (`// TODO: Add validation`, `// TODO: Add business logic/service call`, `// TODO: Interact with models`) for the core logic.
- Send appropriate JSON responses (e.g., `res.status(200).json(data)`, `res.status(400).json({{ error: 'message' }})`) based on the API specification's success/error schemas.
- Include necessary imports (`const express = require('express'); const router = express.Router();`, potentially controller/model imports).
- Export the router (`module.exports = router;`).
Follow standard Node.js and Express conventions.
Output *only* the raw JavaScript code for the file. Do not include explanations or markdown.

Context:
```json
{context}
```

Code for {file_path}:
"""

# --- Frontend Component Prompt Example ---

# Example for React
REACT_COMPONENT_PROMPT = """
Generate the complete JavaScript code (JSX) for a React functional component based *only* on the provided context.
The file path is '{file_path}'.
The component should render basic HTML structure relevant to its description (e.g., a form, a list, a display section).
If the context includes `ui_interaction_notes` or relevant `api_endpoints_summary`, include placeholder comments for state management (`// TODO: Add state for...`), event handlers (`// TODO: Implement handleInputChange`, `// TODO: Implement handleSubmit`), and potential API calls (`// TODO: Call API endpoint [API Summary]`).
Include necessary React imports (`import React, { useState, useEffect } from 'react';`).
Include basic prop handling if the description implies it (`const MyComponent = (props) => {{ ... }}`).
Export the component (`export default MyComponent;`).
Follow standard JavaScript and React conventions.
Output *only* the raw JavaScript code (JSX) for the file. Do not include explanations or markdown.

Context:
```json
{context}
```

Code for {file_path}:
"""


# --- Simple File Prompts ---
HTML_PROMPT = """
Generate the complete HTML code for the file '{file_path}' based *only* on the provided context.
Include standard HTML5 boilerplate (`<!DOCTYPE html>`, `<html>`, `<head>`, `<body>`).
Populate the `<head>` with a relevant `<title>` based on the project or file description. Link to CSS/JS files if specified or conventional (e.g., `<link rel="stylesheet" href="style.css">`).
Populate the `<body>` with basic HTML structure relevant to the file's description (e.g., headings, paragraphs, divs, placeholders for dynamic content).
Output *only* the raw HTML code. Do not include explanations or markdown.

Context:
```json
{context}
```

Code for {file_path}:
"""

CSS_PROMPT = """
Generate basic CSS rules for the file '{file_path}' based *only* on the provided context.
Include placeholder selectors and styles relevant to the project type or file description (e.g., body styling, basic layout classes, component placeholders).
Example:
body {{ font-family: sans-serif; margin: 0; }}
.container {{ max-width: 960px; margin: auto; padding: 20px; }}
/* TODO: Add styles for components mentioned in context */

Output *only* the raw CSS code. Do not include explanations or markdown comments other than placeholders like the one above.

Context:
```json
{context}
```

Code for {file_path}:
"""


# --- Prompt Selection Logic ---

def select_prompt_for_file(file_info, tech_stack):
    """
    Selects the most appropriate prompt template based on file info and tech stack.

    Args:
        file_info (dict): Dictionary containing 'path' and 'description'.
        tech_stack (dict): Dictionary containing 'backend' and 'frontend' tech details.

    Returns:
        str: The selected prompt template string.
    """
    path = file_info.get("path", "").lower()
    desc = file_info.get("description", "").lower()
    backend_lang = tech_stack.get("backend", {}).get("language", "").lower()
    backend_fw = tech_stack.get("backend", {}).get("framework", "").lower()
    frontend_fw = tech_stack.get("frontend", {}).get("framework", "").lower()

    # Backend Models
    if ("model" in desc or "schema" in desc or "entity" in desc) and ("backend" in path or not "frontend" in path):
        if backend_lang == "python" and backend_fw in ["flask", "django", "fastapi"]: # Assume ORM like SQLAlchemy
            logger.debug(f"Selected FLASK_SQLALCHEMY_MODEL_PROMPT for {path}")
            return FLASK_SQLALCHEMY_MODEL_PROMPT
        elif backend_lang == "node.js" and backend_fw == "express": # Assume Mongoose
            logger.debug(f"Selected NODE_MONGOOSE_MODEL_PROMPT for {path}")
            return NODE_MONGOOSE_MODEL_PROMPT
        # Add more conditions for other backend stacks (Java/Spring, C#/ASP.NET, etc.)

    # Backend Controllers/Routers
    elif ("controller" in desc or "route" in desc or "view" in desc or "api" in desc) and ("backend" in path or not "frontend" in path):
         if backend_lang == "python" and backend_fw in ["flask", "django", "fastapi"]:
            logger.debug(f"Selected FLASK_CONTROLLER_PROMPT for {path}")
            return FLASK_CONTROLLER_PROMPT
         elif backend_lang == "node.js" and backend_fw == "express":
            logger.debug(f"Selected NODE_EXPRESS_ROUTER_PROMPT for {path}")
            return NODE_EXPRESS_ROUTER_PROMPT
        # Add more conditions

    # Frontend Components
    elif ("component" in desc or "page" in desc) and ("frontend" in path or not "backend" in path):
        if frontend_fw == "react" and (path.endswith(".js") or path.endswith(".jsx")):
             logger.debug(f"Selected REACT_COMPONENT_PROMPT for {path}")
             return REACT_COMPONENT_PROMPT
        # Add conditions for Vue, Angular, Svelte etc.

    # Basic HTML/CSS
    elif path.endswith(".html"):
        logger.debug(f"Selected HTML_PROMPT for {path}")
        return HTML_PROMPT
    elif path.endswith(".css"):
         logger.debug(f"Selected CSS_PROMPT for {path}")
         return CSS_PROMPT

    # Fallback
    logger.warning(f"No specific prompt matched for {path}. Using GENERIC_CODE_PROMPT.")
    return GENERIC_CODE_PROMPT

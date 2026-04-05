from app import create_app

app = create_app()

# Register all SQLAlchemy models (do not use `import app.models` — it rebinds name `app` to the package)
from app import models  # noqa: F401

if __name__ == "__main__":
    app.run(debug=True, use_reloader=True)

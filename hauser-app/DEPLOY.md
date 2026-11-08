# Hauser Python prototype deployment

This folder must contain the files from `hauser-render-ready.zip` (the root of the ZIP): `app/main.py`, `app/review.py`, `app/importers.py`, `app/assemblies.py`, `app/static/index.html`, `app/static/review.html` and requirements. This manifest alone does not deploy the app.

Render build command: `cd hauser-app && pip install -r requirements.txt`

Render start command: `cd hauser-app && uvicorn app.main:app --host 0.0.0.0 --port $PORT`

For a public service, add authentication and persistent storage before accepting any customer drawings. This MVP is not production ready.

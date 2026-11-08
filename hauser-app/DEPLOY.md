# Hauser demo deployment

This is a **prototype** using sample data. Do not upload confidential customer drawings to a public demonstration deployment.

1. Create a private GitHub repository named `hauser-estimator`.
2. Upload the contents of this folder to the repository root (not the enclosing `hauser-mvp` directory).
3. In Render, create a Web Service from the repository using Python runtime, build command `pip install -r requirements.txt`, and start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
4. Select the free plan and Frankfurt region, and open `/review` on the resulting URL.

The included `render.yaml` describes the same configuration for Blueprint deployments.

## Limitations

The free service filesystem is ephemeral. Do not rely on it for persistent estimates or uploaded drawings. The demo has not been security-hardened for public access and has no user authentication. Add authentication and persistent storage before handling real projects.

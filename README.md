# KT APP

## Installation

1. Create a virtual environment with Python 3.11
2. Install requirements with `pip install -r requirements.txt`

## Running Locally

1. Copy `.env.example` to `.env` and populate the required values
2. Run Django migrations with `python manage.py migrate`
3. Start the Django webserver with `python manage.py runserver`

To run with Docker, run `docker compose build web` to build the image, and `docker compose up -d` to run the services.

## Testing

Tests can be run with `python manage.py test`

## Publishing a New Version

This project uses GitHub Actions to automatically publish Docker images to Docker Hub for tags matching the format `x.y.z`.

To publish a new version, create a Git tag with the desired version number (e.g., `1.0.0`):
```bash
git tag 1.0.0
git push origin 1.0.0
```

Once the Git tag is pushed, the GitHub Actions workflow will trigger automatically, building and pushing the Docker image to Docker Hub with the corresponding tag. The built image will be available at `scriptblazer/kt-app:1.0.0`

from setuptools import setup, find_packages

setup(
    name="sur-backend",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi==0.88.0",
        "uvicorn==0.20.0",
        "python-multipart==0.0.6",
        "python-dotenv==0.19.2",
        "demucs==4.0.1",
        "torch==2.0.1",
        "torchaudio==2.0.2",
    ],
)
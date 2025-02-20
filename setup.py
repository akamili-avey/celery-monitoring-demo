from setuptools import setup, find_namespace_packages

setup(
    name="celery-pq-monitor",
    version="0.1",
    packages=find_namespace_packages(include=['app', 'app.*']),
    install_requires=[
        "Django>=4.2.19",
        "celery>=5.3.6",
        "prometheus-client>=0.19.0",
        "python-dotenv>=1.0.1",
        "gunicorn>=21.2.0",
        "flower>=2.0.1",
        "requests>=2.31.0",
        "celery-exporter>=1.5.0",
        "whitenoise>=6.6.0",
        "dj-database-url>=2.1.0",
    ],
) 
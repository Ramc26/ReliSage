FROM python:3.13

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY repo_release_notes.py ./

CMD ["python", "repo_release_notes.py"]
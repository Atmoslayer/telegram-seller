FROM python:3.10.7
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
COPY requirements.txt /telegram-seller/requirements.txt
WORKDIR /telegram-seller
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
COPY . .
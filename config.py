import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "delivery-dev-secret")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "110120119")
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "keshe")
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4",
    )
    IMG_PATH = os.getenv("IMG_PATH", r"C:\Users\Tsing\Desktop\系统\server\imgs")

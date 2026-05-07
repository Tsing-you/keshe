from datetime import datetime, timedelta

def get_cst_time():
    return datetime.utcnow() + timedelta(hours=8)

from decimal import Decimal
import os
from sqlite3 import OperationalError as SQLiteOperationalError

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    event,
)
from sqlalchemy.orm import declarative_base, relationship, scoped_session, sessionmaker
from sqlalchemy.pool import StaticPool

from config import Config


Base = declarative_base()
engine_options = {"future": True, "pool_pre_ping": True}
if Config.DATABASE_URL.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False, "timeout": 30}
if Config.DATABASE_URL == "sqlite:///:memory:":
    engine_options.update({"poolclass": StaticPool})
engine = create_engine(Config.DATABASE_URL, **engine_options)
SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, expire_on_commit=False))


@event.listens_for(engine, "connect")
def configure_sqlite(dbapi_connection, _connection_record):
    if not Config.DATABASE_URL.startswith("sqlite"):
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA busy_timeout=30000")
    if Config.DATABASE_URL != "sqlite:///:memory:":
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
        except SQLiteOperationalError:
            pass
    cursor.close()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False, unique=True)
    password = Column(String(128), nullable=False)
    role = Column(Enum("customer", "merchant", "rider", name="user_role"), nullable=False)
    phone = Column(String(30), unique=True)
    address = Column(String(255))
    created_at = Column(DateTime, default=get_cst_time, nullable=False)

    merchant_profile = relationship("Merchant", back_populates="owner", uselist=False)
    addresses = relationship("UserAddress", back_populates="user", cascade="all, delete-orphan")


class UserAddress(Base):
    __tablename__ = "user_addresses"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    label = Column(String(50), nullable=False)
    receiver_name = Column(String(50))
    receiver_phone = Column(String(30))
    address = Column(String(255), nullable=False)
    is_default = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=get_cst_time, nullable=False)

    user = relationship("User", back_populates="addresses")


class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255))
    logo_path = Column(String(255))
    is_available = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=get_cst_time, nullable=False)

    owner = relationship("User", back_populates="merchant_profile")
    dishes = relationship("Dish", back_populates="merchant", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="merchant")
    reviews = relationship("Review", back_populates="merchant")


class Dish(Base):
    __tablename__ = "dishes"

    id = Column(Integer, primary_key=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    name = Column(String(100), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    description = Column(String(255))
    image_path = Column(String(255))
    is_available = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=get_cst_time, nullable=False)

    merchant = relationship("Merchant", back_populates="dishes")
    __table_args__ = (
        UniqueConstraint("merchant_id", "name", name="uq_dish_merchant_name"),
        CheckConstraint("price >= 0", name="ck_dish_price_nonnegative"),
    )


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    rider_id = Column(Integer, ForeignKey("users.id"))
    status = Column(
        Enum("pending", "accepted", "delivered", "completed", "reviewed", name="order_status"),
        default="pending",
        nullable=False,
    )
    total_amount = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    delivery_address = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=get_cst_time, nullable=False)
    accepted_at = Column(DateTime)
    delivered_at = Column(DateTime)
    completed_at = Column(DateTime)

    customer = relationship("User", foreign_keys=[customer_id])
    rider = relationship("User", foreign_keys=[rider_id])
    merchant = relationship("Merchant", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    review = relationship("Review", back_populates="order", uselist=False)
    rider_review = relationship("RiderReview", back_populates="order", uselist=False)


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    dish_id = Column(Integer, ForeignKey("dishes.id"), nullable=False)
    dish_name = Column(String(100), nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    quantity = Column(Integer, nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)

    order = relationship("Order", back_populates="items")
    dish = relationship("Dish")
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_order_item_quantity_positive"),)


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, unique=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text)
    created_at = Column(DateTime, default=get_cst_time, nullable=False)

    order = relationship("Order", back_populates="review")
    merchant = relationship("Merchant", back_populates="reviews")
    customer = relationship("User")
    __table_args__ = (CheckConstraint("rating between 1 and 5", name="ck_review_rating_range"),)


class RiderReview(Base):
    __tablename__ = "rider_reviews"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, unique=True)
    rider_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text)
    created_at = Column(DateTime, default=get_cst_time, nullable=False)

    order = relationship("Order", back_populates="rider_review")
    rider = relationship("User", foreign_keys=[rider_id])
    customer = relationship("User", foreign_keys=[customer_id])
    __table_args__ = (CheckConstraint("rating between 1 and 5", name="ck_rider_review_rating_range"),)


def seed_data():
    db = SessionLocal()
    try:
        if db.query(User).count():
            return
        customer = User(
            username="customer",
            password="123456",
            role="customer",
            phone="13800000001",
            address="1号楼101",
        )
        merchant_user = User(username="merchant", password="123456", role="merchant", phone="13800000002")
        rider = User(username="rider", password="123456", role="rider", phone="13800000003")
        merchant = Merchant(owner=merchant_user, name="校园快餐", description="米饭套餐、热炒和饮品")
        customer.addresses = [
            UserAddress(label="宿舍", receiver_name="customer", receiver_phone="13800000001", address="1号楼101", is_default=1)
        ]
        img_root = Config.IMG_PATH
        merchant.dishes = [
            Dish(
                name="红烧牛肉饭",
                price=Decimal("22.00"),
                description="牛肉、土豆、米饭",
                image_path=os.path.join(img_root, "beef_rice.jpg"),
            ),
            Dish(
                name="鱼香肉丝盖饭",
                price=Decimal("18.00"),
                description="经典下饭菜",
                image_path=os.path.join(img_root, "yuxiang.jpg"),
            ),
            Dish(
                name="柠檬茶",
                price=Decimal("6.00"),
                description="冰爽解腻",
                image_path=os.path.join(img_root, "lemon_tea.jpg"),
            ),
        ]
        db.add_all([customer, merchant_user, rider, merchant])
        db.flush()
        order = Order(
            customer_id=customer.id,
            merchant_id=merchant.id,
            rider_id=rider.id,
            status="completed",
            total_amount=Decimal("40.00"),
            delivery_address="1号楼101",
            accepted_at=datetime.utcnow(),
            delivered_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
        db.add(order)
        db.flush()
        dish_one = merchant.dishes[0]
        dish_two = merchant.dishes[1]
        db.add_all(
            [
                OrderItem(
                    order_id=order.id,
                    dish_id=dish_one.id,
                    dish_name=dish_one.name,
                    unit_price=dish_one.price,
                    quantity=1,
                    subtotal=dish_one.price,
                ),
                OrderItem(
                    order_id=order.id,
                    dish_id=dish_two.id,
                    dish_name=dish_two.name,
                    unit_price=dish_two.price,
                    quantity=1,
                    subtotal=dish_two.price,
                ),
            ]
        )
        db.add(
            Review(
                order_id=order.id,
                merchant_id=merchant.id,
                customer_id=customer.id,
                rating=5,
                comment="送餐很快，味道不错",
            )
        )
        db.add(
            RiderReview(
                order_id=order.id,
                rider_id=rider.id,
                customer_id=customer.id,
                rating=5,
                comment="态度很好",
            )
        )
        db.commit()
    finally:
        db.close()


def normalize_demo_data(db):
    customer = db.query(User).filter_by(username="customer").first()
    merchant_user = db.query(User).filter_by(username="merchant").first()
    rider = db.query(User).filter_by(username="rider").first()
    if customer:
        customer.phone = customer.phone or "13800000001"
        customer.address = "1号楼101"
    if merchant_user:
        merchant_user.phone = merchant_user.phone or "13800000002"
    if rider:
        rider.phone = rider.phone or "13800000003"
    db.commit()

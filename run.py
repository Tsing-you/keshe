import os
import json
import re
from uuid import uuid4
from datetime import datetime, timedelta
from decimal import Decimal
from textwrap import dedent
import urllib.error
import urllib.request
import jwt

from flask import Flask, jsonify, request, send_from_directory
from sqlalchemy import or_, update, func
from werkzeug.utils import secure_filename

from config import Config
from models import (
    Dish,
    Merchant,
    Order,
    OrderItem,
    Review,
    RiderReview,
    SessionLocal,
    User,
    UserAddress,
    get_cst_time,
)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    @app.teardown_appcontext
    def remove_session(_exc=None):
        SessionLocal.remove()

    @app.get("/")
    def index():
        return jsonify({"status": "ok", "service": "delivery-backend"})

    @app.get("/stats")
    def stats():
        db = SessionLocal()
        try:
            return jsonify(
                {
                    "users": db.query(User).count(),
                    "merchants": db.query(Merchant).count(),
                    "dishes": db.query(Dish).count(),
                    "orders": db.query(Order).count(),
                }
            )
        finally:
            db.close()

    def pic_dir():
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "pic")

    def ensure_pic_dir():
        directory = pic_dir()
        os.makedirs(directory, exist_ok=True)
        return directory

    def save_uploaded_image(upload_file, prefix):
        directory = ensure_pic_dir()
        original_name = secure_filename(upload_file.filename or "")
        ext = os.path.splitext(original_name)[1].lower()
        if ext not in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}:
            ext = ".png"
        safe_prefix = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in (prefix or "image"))
        filename = f"{safe_prefix}_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{uuid4().hex[:8]}{ext}"
        upload_file.save(os.path.join(directory, filename))
        return f"/api/pic/{filename}"

    @app.get("/pic/<path:filename>")
    def serve_pic(filename):
        return send_from_directory(pic_dir(), filename)


    def payload_from_request():
        if request.is_json:
            return request.get_json(silent=True) or {}
        return request.form.to_dict()

    def build_help_knowledge(context=None):
        context = context or {}
        route = context.get("route") or "未知"
        role = context.get("role") or "未登录"
        username = context.get("username") or ""
        role_name_text = context.get("role_name") or ""
        return dedent(f"""
        你是 JLU FOODLAB 本地配送系统的帮助助手。你的任务是根据项目真实功能，回答用户关于使用、排错、接口和开发的问题。

        当前上下文：
        - 当前路由：{route}
        - 当前角色：{role}
        - 当前用户名：{username}
        - 角色名称：{role_name_text}

        项目事实：
        - 前端是 Vue 3 + Vite，开发代理把 /api 转发到 http://127.0.0.1:5000。
        - 后端入口是 run.py，默认使用 Flask、SQLAlchemy、PyJWT 和 MySQL。
        - 登录和注册支持用户名或手机号登录，注册可选择 customer、rider、merchant 三种角色。
        - 登录后前端会在 localStorage 保存 user、token 和可选的 credentials；请求优先携带 Bearer token。
        - 401 表示登录状态过期，前端会清除会话并跳回登录页。
        - 图片访问路径通常是 /api/pic/... 或 /pic/....

        路由与角色：
        - /login：登录与注册页。
        - /customer：普通用户工作台。
        - /customer/merchant/:id：商家详情与点餐页。
        - /rider：骑手工作台。
        - /merchant：商家工作台。
        - 路由守卫会根据 localStorage.user.role 限制页面访问。

        普通用户功能：
        - 浏览商家列表，按名称或简介筛选。
        - 查看商家详情、菜品、评价和营业状态。
        - 管理收货地址，支持多个地址和默认地址。
        - 下单时先选择菜品并加入购物车，再选择收货地址提交。
        - 订单状态包括 pending、accepted、delivered、completed、reviewed。
        - 进行中订单可以刷新、确认收货、查看联系方式。
        - 已完成订单可以评价商家和骑手。

        骑手功能：
        - 查看 /available 的待接订单大厅。
        - 通过 /claim 接单，通过 /deliver 标记送达。
        - 查看 /history 和 /orders/my 获取历史与当前任务。
        - 查看 /rider/stats 获取平均评分与最近评价。
        - 可以在订单中查看联系信息。

        商家功能：
        - 查看和修改店铺资料：名称、简介、头像、营业状态。
        - 通过 /merchant/dishes、/merchant/dish/create、/merchant/dish/update、/merchant/dish/delete 管理菜品。
        - 查看 /merchant/orders、/merchant/reviews、/merchant/profile。
        - 商家营业状态为休息时，用户可以浏览菜单但不能下单。
        - 商家经营分析页面会展示订单量、营业额、趋势和菜品分析。

        关键接口：
        - POST /register
        - POST /login
        - POST /merchants
        - POST /menu
        - POST /order
        - POST /orders/my
        - POST /complete
        - POST /review
        - POST /order/contact
        - POST /user/profile
        - POST /user/profile/update
        - POST /user/addresses
        - POST /user/address/save
        - POST /user/address/delete
        - POST /available
        - POST /claim
        - POST /deliver
        - POST /history
        - POST /rider/stats
        - POST /merchant/profile
        - POST /merchant/profile/update
        - POST /merchant/dishes
        - POST /merchant/dish/create
        - POST /merchant/dish/update
        - POST /merchant/dish/delete
        - POST /merchant/orders
        - POST /merchant/reviews

        回答要求：
        - 必须使用中文。
        - 优先给出具体步骤、按钮位置、页面名称或接口名。
        - 如果问题属于当前项目，就按项目真实功能回答，不要编造。
        - 如果涉及开发者调试，说明启动顺序：npm install、python run.py、npm run dev、npm run build。
        - 如果信息不足，先说明你需要哪一项补充信息，再给出最可能的排查路径。
        - 输出纯文本，不使用 markdown 语法，不要用引号包裹整段答案。
        - 不要输出密钥、内部实现细节或与问题无关的长篇泛化说明。
        """).strip()

    def normalize_help_history(history):
        normalized = []
        if not isinstance(history, list):
            return normalized
        for item in history[-8:]:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            content = (item.get("content") or "").strip()
            if role not in {"user", "assistant"} or not content:
                continue
            normalized.append({"role": role, "content": content[:2500]})
        return normalized

    def call_help_model(messages):
        payload = json.dumps(
            {
                "model": Config.AI_MODEL,
                "messages": messages,
                "temperature": 0.2,
                "top_p": 0.85,
                "max_tokens": 1200,
                "stream": False,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Config.AI_API_KEY}",
        }
        request_obj = urllib.request.Request(
            Config.AI_BASE_URL,
            data=payload,
            headers=request_headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request_obj, timeout=60) as response:
                raw_body = response.read().decode("utf-8", errors="ignore")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"大模型请求失败：HTTP {exc.code} {detail[:300]}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"大模型连接失败：{exc.reason}") from exc

        try:
            response_data = json.loads(raw_body)
        except Exception as exc:
            raise RuntimeError("大模型返回了无法解析的内容") from exc

        choices = response_data.get("choices") or []
        if choices:
            message = choices[0].get("message") or {}
            answer = (message.get("content") or "").strip()
            if answer:
                return answer

        error_message = response_data.get("error", {}).get("message") or "大模型没有返回有效答案"
        raise RuntimeError(error_message)

    def sanitize_help_answer(text):
        content = (text or "").strip()
        if not content:
            return ""

        # Remove fenced markdown code blocks while preserving the inner text.
        content = re.sub(r"```(?:\w+)?\n?(.*?)```", r"\1", content, flags=re.DOTALL)

        # Drop common markdown markers for plain-text chat display.
        content = re.sub(r"^\s{0,3}(#{1,6}|>|[-*+]\s)\s*", "", content, flags=re.MULTILINE)
        content = content.replace("**", "").replace("__", "")
        content = content.replace("`", "")

        # Remove wrapper quotes repeatedly: 'text', "text", ''text'', “text”, ‘text’
        quote_pairs = [("'", "'"), ('"', '"'), ("“", "”"), ("‘", "’")]
        changed = True
        while changed and len(content) >= 2:
            changed = False
            content = content.strip()
            for left, right in quote_pairs:
                if content.startswith(left) and content.endswith(right) and len(content) > 1:
                    content = content[1:-1].strip()
                    changed = True

        # Normalize blank lines and remove isolated quote fragments.
        content = re.sub(r"\n{3,}", "\n\n", content)
        content = re.sub(r"\s*''\s*", " ", content)
        content = re.sub(r'\s*""\s*', " ", content)
        content = re.sub(r"[ \t]{2,}", " ", content)

        return content.strip()

    class AuthError(Exception):
        def __init__(self, message, status=401):
            super().__init__(message)
            self.status = status

    def create_token(user):
        payload = {
            'user_id': int(user.id),
            'exp': datetime.utcnow() + timedelta(days=7)
        }
        return jwt.encode(payload, Config.SECRET_KEY, algorithm='HS256')

    def get_user_from_token(db, token):
        try:
            payload = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
            uid = int(payload.get('user_id'))
            user = db.get(User, uid)
            if not user:
                raise AuthError('无效的用户', 401)
            return user
        except jwt.ExpiredSignatureError:
            raise AuthError('登录已过期', 401)
        except AuthError:
            raise
        except Exception:
            raise AuthError('无效的令牌', 401)

    def authenticate(db, data):
        # Prefer Authorization header Bearer token
        auth = request.headers.get('Authorization', '') or request.headers.get('authorization', '')
        if auth and auth.startswith('Bearer '):
            token = auth.split(' ', 1)[1]
            return get_user_from_token(db, token)

        # Fallback to account/password in body (legacy)
        account = data.get('account', '')
        password = data.get('password', '')
        if not account or not password:
            raise AuthError('账号或密码缺失', 401)
        user = db.query(User).filter(or_(User.username == account, User.phone == account), User.password == password).first()
        if not user:
            raise AuthError('账号或密码错误', 401)
        return user

    def role_name(role):
        return {"customer": "用户", "merchant": "商家", "rider": "骑手"}.get(role, role)

    def status_text(status):
        return {
            "pending": "等待骑手接单",
            "accepted": "骑手已接单，配送中",
            "delivered": "已送达，请用户取餐并确认收货",
            "completed": "已确认收货，待评价",
            "reviewed": "已完成评价",
        }.get(status, status)

    def login_user(db, account, password):
        user = db.query(User).filter(or_(User.username == account, User.phone == account), User.password == password).first()
        if not user:
            raise ValueError("账号或密码错误")
        return user

    def get_merchant_profile(db, user):
        if user.role != "merchant":
            raise ValueError("只有商家可以操作")
        merchant = db.query(Merchant).filter_by(owner_id=user.id).first()
        if not merchant:
            raise ValueError("商家资料不存在")
        return merchant

    def parse_decimal(value, field_name):
        try:
            amount = Decimal(str(value))
        except Exception as exc:
            raise ValueError(f"{field_name}格式不正确") from exc
        if amount < 0:
            raise ValueError(f"{field_name}不能为负数")
        return amount

    def serialize_dish(dish):
        return {
            "id": dish.id,
            "name": dish.name,
            "price": str(dish.price),
            "description": dish.description or "",
            "image_path": dish.image_path or "",
            "is_available": int(dish.is_available),
        }

    def serialize_order(order):
        return {
            "id": order.id,
            "merchant": order.merchant.name,
            "customer": order.customer.username,
            "rider": order.rider.username if order.rider else "待接单",
            "status": order.status,
            "status_text": status_text(order.status),
            "total_amount": str(order.total_amount),
            "delivery_address": order.delivery_address,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "items": [
                {"dish_name": item.dish_name, "quantity": item.quantity, "subtotal": str(item.subtotal)}
                for item in order.items
            ],
        }

    def query_orders_by_role(db, user):
        query = db.query(Order)
        if user.role == "customer":
            query = query.filter_by(customer_id=user.id)
        elif user.role == "rider":
            query = query.filter_by(rider_id=user.id)
        elif user.role == "merchant":
            merchant = get_merchant_profile(db, user)
            query = query.filter_by(merchant_id=merchant.id)
        else:
            raise ValueError("不支持的角色")
        return query

    def json_response(payload, status=200):
        return jsonify(payload), status

    @app.post("/help/chat")
    def help_chat():
        data = payload_from_request()
        question = (data.get("question") or "").strip()
        if not question:
            return json_response({"ok": False, "error": "请先输入问题"}, 400)

        context = {
            "route": (data.get("route") or "").strip(),
            "role": (data.get("role") or "").strip(),
            "username": (data.get("username") or "").strip(),
            "role_name": (data.get("role_name") or "").strip(),
        }
        messages = [{"role": "system", "content": build_help_knowledge(context)}]
        messages.extend(normalize_help_history(data.get("history")))
        messages.append({"role": "user", "content": question[:3000]})

        try:
            answer = sanitize_help_answer(call_help_model(messages))
            return json_response({
                "ok": True,
                "answer": answer,
                "model": Config.AI_MODEL,
            })
        except Exception as exc:
            return json_response({"ok": False, "error": str(exc)}, 500)

    @app.post("/register")
    def register():
        data = payload_from_request()
        db = SessionLocal()
        try:
            username = data.get("username", "").strip()
            password = data.get("password", "")
            role = data.get("role", "")
            phone = data.get("phone", "").strip()
            if not username or not password or not role:
                raise ValueError("请提供完整的账号、密码和角色")
            if role not in ["customer", "merchant", "rider"]:
                raise ValueError("无效的角色")
            
            if db.query(User).filter((User.username == username) | (User.phone == phone)).first():
                raise ValueError("用户名或手机号已存在")

            user = User(
                username=username,
                password=password,
                role=role,
                phone=phone,
                address=data.get("address", "").strip() if role == "customer" else None
            )
            db.add(user)
            db.flush()

            if role == "merchant":
                merchant_name = data.get("merchant_name", "").strip()
                if not merchant_name:
                    raise ValueError("商家需提供店铺名称")
                merchant = Merchant(
                    owner_id=user.id,
                    name=merchant_name,
                    description="新注册商家"
                )
                db.add(merchant)
            
            db.commit()
            return json_response({"ok": True, "message": "注册成功，请登录！"})
        except Exception as exc:
            db.rollback()
            return json_response({"ok": False, "error": str(exc)}, 400)
        finally:
            db.close()

    @app.post("/login")
    def login():
        data = payload_from_request()
        db = SessionLocal()
        try:
            account = data.get("account", "")
            password = data.get("password", "")
            if not account or not password:
                raise AuthError('账号或密码缺失', 401)
            user = db.query(User).filter(or_(User.username == account, User.phone == account), User.password == password).first()
            if not user:
                raise AuthError('账号或密码错误', 401)
            token = create_token(user)
            return json_response(
                {
                    "ok": True,
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "phone": user.phone,
                        "role": user.role,
                        "role_name": role_name(user.role),
                    },
                    "token": token,
                }
            )
        except AuthError as ae:
            return json_response({"ok": False, "error": str(ae)}, ae.status)
        except Exception as exc:
            return json_response({"ok": False, "error": str(exc)}, 400)
        finally:
            db.close()

    @app.post("/merchants")
    def merchants():
        data = payload_from_request()
        db = SessionLocal()
        try:
            user = authenticate(db, data)
            if user.role != "customer":
                raise ValueError("只有用户可以浏览商家")

            order_count_subquery = (
                db.query(Order.merchant_id, func.count(Order.id).label("order_count"))
                .group_by(Order.merchant_id)
                .subquery()
            )
            avg_rating_subquery = (
                db.query(Review.merchant_id, func.avg(Review.rating).label("avg_rating"))
                .group_by(Review.merchant_id)
                .subquery()
            )

            merchants_list = []
            for merchant in (
                db.query(Merchant, order_count_subquery.c.order_count, avg_rating_subquery.c.avg_rating)
                .outerjoin(order_count_subquery, Merchant.id == order_count_subquery.c.merchant_id)
                .outerjoin(avg_rating_subquery, Merchant.id == avg_rating_subquery.c.merchant_id)
                .order_by(Merchant.id)
                .all()
            ):
                m, order_count, avg_rating = merchant
                merchants_list.append(
                    {
                        "id": m.id,
                        "name": m.name,
                        "description": m.description or "",
                        "logo_path": m.logo_path or "",
                        "is_available": int(m.is_available),
                        "order_count": int(order_count or 0),
                        "avg_rating": round(float(avg_rating or 0), 1),
                    }
                )

            return json_response({"ok": True, "merchants": merchants_list})
        except AuthError as ae:
            return json_response({"ok": False, "error": str(ae)}, ae.status)
        except Exception as exc:
            return json_response({"ok": False, "error": str(exc)}, 400)
        finally:
            db.close()

    @app.post("/menu")
    def menu():
        data = payload_from_request()
        db = SessionLocal()
        try:
            user = authenticate(db, data)
            if user.role != "customer":
                raise ValueError("只有用户可以查看菜单")
            merchant = db.get(Merchant, int(data.get("merchant_id", 0)))
            if not merchant:
                raise ValueError("商家不存在")
            dishes = [
                {"id": d.id, "name": d.name, "price": str(d.price), "description": d.description or "", "image_path": d.image_path or ""}
                for d in db.query(Dish).filter_by(merchant_id=merchant.id, is_available=1).all()
            ]
            reviews = [
                {"rating": r.rating, "comment": r.comment or "", "customer": r.customer.username}
                for r in db.query(Review).filter_by(merchant_id=merchant.id).order_by(Review.id.desc()).all()
            ]
            return json_response(
                {
                    "ok": True,
                    "merchant": {
                        "id": merchant.id,
                        "name": merchant.name,
                        "logo_path": merchant.logo_path or "",
                        "is_available": int(merchant.is_available),
                    },
                    "dishes": dishes,
                    "reviews": reviews,
                }
            )
        except AuthError as ae:
            return json_response({"ok": False, "error": str(ae)}, ae.status)
        except Exception as exc:
            return json_response({"ok": False, "error": str(exc)}, 400)
        finally:
            db.close()

    @app.post("/user/profile")
    def user_profile():
        data = payload_from_request()
        db = SessionLocal()
        try:
            user = authenticate(db, data)
            return json_response(
                {
                    "ok": True,
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "phone": user.phone or "",
                        "address": user.address or "",
                        "role": user.role,
                        "created_at": user.created_at.isoformat() if user.created_at else None,
                    }
                }
            )
        except AuthError as ae:
            return json_response({"ok": False, "error": str(ae)}, ae.status)
        except Exception as exc:
            return json_response({"ok": False, "error": str(exc)}, 400)
        finally:
            db.close()

    @app.post("/user/profile/update")
    def user_profile_update():
        data = payload_from_request()
        db = SessionLocal()
        try:
            user = authenticate(db, data)
            if "username" in data:
                username = (data.get("username") or "").strip()
                if username:
                    if username != user.username:
                        existing = db.query(User).filter(User.username == username, User.id != user.id).first()
                        if existing:
                            raise ValueError("用户名已被占用")
                        user.username = username
            if "phone" in data:
                phone = (data.get("phone") or "").strip()
                if phone:
                    existing = db.query(User).filter(User.phone == phone, User.id != user.id).first()
                    if existing:
                        raise ValueError("手机号已被占用")
                user.phone = phone
            if "address" in data:
                user.address = (data.get("address") or "").strip()
            if "password" in data:
                pwd = data.get("password")
                if pwd and str(pwd).strip():
                    user.password = str(pwd).strip()
            db.commit()
            return json_response({"ok": True, "message": "个人信息已更新"})
        except AuthError as ae:
            db.rollback()
            return json_response({"ok": False, "error": str(ae)}, ae.status)
        except Exception as exc:
            db.rollback()
            return json_response({"ok": False, "error": str(exc)}, 400)
        finally:
            db.close()

    @app.post("/user/addresses")
    def get_addresses():
        data = payload_from_request()
        db = SessionLocal()
        try:
            user = authenticate(db, data)
            addresses = db.query(UserAddress).filter_by(user_id=user.id).all()
            return json_response({
                "ok": True,
                "addresses": [{
                    "id": a.id,
                    "label": a.label,
                    "receiver_name": a.receiver_name,
                    "receiver_phone": a.receiver_phone,
                    "address": a.address,
                    "is_default": a.is_default,
                } for a in addresses]
            })
        except AuthError as ae:
            return json_response({"ok": False, "error": str(ae)}, ae.status)
        except Exception as exc:
            return json_response({"ok": False, "error": str(exc)}, 400)
        finally:
            db.close()

    @app.post("/user/address/save")
    def save_address():
        data = payload_from_request()
        db = SessionLocal()
        try:
            user = authenticate(db, data)
            address_id = data.get("id")
            label = (data.get("label") or "").strip()
            receiver_name = (data.get("receiver_name") or "").strip()
            receiver_phone = (data.get("receiver_phone") or "").strip()
            address_text = (data.get("address") or "").strip()
            is_default = int(data.get("is_default", 0))

            if not label or not address_text:
                raise ValueError("标签和详细地址不能为空")

            if is_default == 1:
                db.query(UserAddress).filter_by(user_id=user.id).update({"is_default": 0})
            
            if address_id:
                addr = db.query(UserAddress).filter_by(id=address_id, user_id=user.id).first()
                if not addr:
                    raise ValueError("地址不存在")
                addr.label = label
                addr.receiver_name = receiver_name
                addr.receiver_phone = receiver_phone
                addr.address = address_text
                addr.is_default = is_default
            else:
                addr = UserAddress(
                    user_id=user.id,
                    label=label,
                    receiver_name=receiver_name,
                    receiver_phone=receiver_phone,
                    address=address_text,
                    is_default=is_default
                )
                db.add(addr)
            db.commit()
            return json_response({"ok": True, "message": "地址已保存"})
        except AuthError as ae:
            db.rollback()
            return json_response({"ok": False, "error": str(ae)}, ae.status)
        except Exception as exc:
            db.rollback()
            return json_response({"ok": False, "error": str(exc)}, 400)
        finally:
            db.close()

    @app.post("/user/address/delete")
    def delete_address():
        data = payload_from_request()
        db = SessionLocal()
        try:
            user = authenticate(db, data)
            address_id = data.get("id")
            if not address_id:
                raise ValueError("缺少地址ID")
            db.query(UserAddress).filter_by(id=address_id, user_id=user.id).delete()
            db.commit()
            return json_response({"ok": True, "message": "地址已删除"})
        except AuthError as ae:
            db.rollback()
            return json_response({"ok": False, "error": str(ae)}, ae.status)
        except Exception as exc:
            db.rollback()
            return json_response({"ok": False, "error": str(exc)}, 400)
        finally:
            db.close()

    @app.post("/merchant/profile/update")
    def merchant_profile_update():
        data = payload_from_request()
        db = SessionLocal()
        try:
            user = authenticate(db, data)
            merchant = get_merchant_profile(db, user)
            if "name" in data:
                name = (data.get("name") or "").strip()
                if not name:
                    raise ValueError("商家名称不能为空")
                merchant.name = name
            if "description" in data:
                merchant.description = (data.get("description") or "").strip()
            if "logo_path" in data:
                merchant.logo_path = (data.get("logo_path") or "").strip()
            if "is_available" in data:
                try:
                    merchant.is_available = 1 if int(data.get("is_available")) else 0
                except (TypeError, ValueError) as exc:
                    raise ValueError("营业状态不正确") from exc
            db.commit()
            return json_response({"ok": True, "message": "资料已更新"})
        except AuthError as ae:
            db.rollback()
            return json_response({"ok": False, "error": str(ae)}, ae.status)
        except Exception as exc:
            db.rollback()
            return json_response({"ok": False, "error": str(exc)}, 400)
        finally:
            db.close()

    @app.post("/upload/image")
    def upload_image():
        data = payload_from_request()
        db = SessionLocal()
        try:
            authenticate(db, data)
            upload_file = request.files.get("file") or request.files.get("image") or request.files.get("upload")
            if not upload_file or not upload_file.filename:
                raise ValueError("请选择要上传的图片")
            image_path = save_uploaded_image(upload_file, data.get("kind") or "image")
            return json_response({"ok": True, "path": image_path})
        except AuthError as ae:
            return json_response({"ok": False, "error": str(ae)}, ae.status)
        except Exception as exc:
            return json_response({"ok": False, "error": str(exc)}, 400)
        finally:
            db.close()

    @app.post("/merchant/profile")
    def merchant_profile():
        data = payload_from_request()
        db = SessionLocal()
        try:
            user = authenticate(db, data)
            merchant = get_merchant_profile(db, user)
            return json_response(
                {
                    "ok": True,
                    "merchant": {
                        "id": merchant.id,
                        "name": merchant.name,
                        "description": merchant.description or "",
                        "logo_path": merchant.logo_path or "",
                        "is_available": int(merchant.is_available),
                    },
                }
            )
        except AuthError as ae:
            return json_response({"ok": False, "error": str(ae)}, ae.status)
        except Exception as exc:
            return json_response({"ok": False, "error": str(exc)}, 400)
        finally:
            db.close()

    @app.post("/merchant/dishes")
    def merchant_dishes():
        data = payload_from_request()
        db = SessionLocal()
        try:
            user = authenticate(db, data)
            merchant = get_merchant_profile(db, user)
            dishes = (
                db.query(Dish)
                .filter_by(merchant_id=merchant.id)
                .order_by(Dish.id.desc())
                .all()
            )
            return json_response({"ok": True, "dishes": [serialize_dish(d) for d in dishes]})
        except Exception as exc:
            return json_response({"ok": False, "error": str(exc)}, 400)
        finally:
            db.close()

    @app.post("/merchant/dish/create")
    def merchant_dish_create():
        data = payload_from_request()
        db = SessionLocal()
        try:
            user = authenticate(db, data)
            merchant = get_merchant_profile(db, user)
            name = (data.get("name") or "").strip()
            if not name:
                raise ValueError("菜品名称不能为空")
            price = parse_decimal(data.get("price"), "价格")
            description = (data.get("description") or "").strip()
            dish = Dish(
                merchant_id=merchant.id,
                name=name,
                price=price,
                description=description,
                image_path=(data.get("image_path") or "").strip(),
                is_available=1,
            )
            db.add(dish)
            db.commit()
            return json_response({"ok": True, "message": "菜品已添加", "dish": serialize_dish(dish)})
        except AuthError as ae:
            db.rollback()
            return json_response({"ok": False, "error": str(ae)}, ae.status)
        except Exception as exc:
            db.rollback()
            return json_response({"ok": False, "error": str(exc)}, 400)
        finally:
            db.close()

    @app.post("/merchant/dish/update")
    def merchant_dish_update():
        data = payload_from_request()
        db = SessionLocal()
        try:
            user = authenticate(db, data)
            merchant = get_merchant_profile(db, user)
            dish = db.get(Dish, int(data.get("dish_id", 0)))
            if not dish or dish.merchant_id != merchant.id:
                raise ValueError("菜品不存在")
            if "name" in data:
                name = (data.get("name") or "").strip()
                if not name:
                    raise ValueError("菜品名称不能为空")
                dish.name = name
            if "price" in data:
                dish.price = parse_decimal(data.get("price"), "价格")
            if "description" in data:
                dish.description = (data.get("description") or "").strip()
            if "image_path" in data:
                dish.image_path = (data.get("image_path") or "").strip()
            if "is_available" in data:
                try:
                    dish.is_available = 1 if int(data.get("is_available")) else 0
                except (TypeError, ValueError) as exc:
                    raise ValueError("上架状态不正确") from exc
            db.commit()
            return json_response({"ok": True, "message": "菜品已更新", "dish": serialize_dish(dish)})
        except AuthError as ae:
            db.rollback()
            return json_response({"ok": False, "error": str(ae)}, ae.status)
        except Exception as exc:
            db.rollback()
            return json_response({"ok": False, "error": str(exc)}, 400)
        finally:
            db.close()

    @app.post("/merchant/dish/delete")
    def merchant_dish_delete():
        data = payload_from_request()
        db = SessionLocal()
        try:
            user = authenticate(db, data)
            merchant = get_merchant_profile(db, user)
            dish = db.get(Dish, int(data.get("dish_id", 0)))
            if not dish or dish.merchant_id != merchant.id:
                raise ValueError("菜品不存在")
            if db.query(OrderItem).filter_by(dish_id=dish.id).count() > 0:
                raise ValueError("该菜品已有订单记录，建议下架而不是删除")
            db.delete(dish)
            db.commit()
            return json_response({"ok": True, "message": "菜品已删除"})
        except Exception as exc:
            db.rollback()
            return json_response({"ok": False, "error": str(exc)}, 400)
        finally:
            db.close()

    @app.post("/merchant/orders")
    def merchant_orders():
        data = payload_from_request()
        db = SessionLocal()
        try:
            user = authenticate(db, data)
            merchant = get_merchant_profile(db, user)
            query = db.query(Order).filter_by(merchant_id=merchant.id)
            status = data.get("status")
            if status:
                if isinstance(status, list):
                    query = query.filter(Order.status.in_(status))
                else:
                    query = query.filter_by(status=status)
            orders = [serialize_order(o) for o in query.order_by(Order.id.desc()).all()]
            return json_response({"ok": True, "orders": orders})
        except AuthError as ae:
            return json_response({"ok": False, "error": str(ae)}, ae.status)
        except AuthError as ae:
            return json_response({"ok": False, "error": str(ae)}, ae.status)
        except Exception as exc:
            return json_response({"ok": False, "error": str(exc)}, 400)
        finally:
            db.close()

    @app.post("/merchant/reviews")
    def merchant_reviews():
        data = payload_from_request()
        db = SessionLocal()
        try:
            user = authenticate(db, data)
            merchant = get_merchant_profile(db, user)
            reviews = (
                db.query(Review)
                .filter_by(merchant_id=merchant.id)
                .order_by(Review.id.desc())
                .all()
            )
            payload = [
                {
                    "id": r.id,
                    "rating": r.rating,
                    "comment": r.comment or "",
                    "customer": r.customer.username,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in reviews
            ]
            return json_response({"ok": True, "reviews": payload})
        except AuthError as ae:
            return json_response({"ok": False, "error": str(ae)}, ae.status)
        except Exception as exc:
            return json_response({"ok": False, "error": str(exc)}, 400)
        finally:
            db.close()

    @app.post("/order")
    def create_order():
        data = payload_from_request()
        db = SessionLocal()
        try:
            user = authenticate(db, data)
            if user.role != "customer":
                raise ValueError("只有用户可以下单")
            merchant = db.get(Merchant, int(data.get("merchant_id", 0)))
            if not merchant:
                raise ValueError("商家不存在")
            if not merchant.is_available:
                raise ValueError("商家当前休息中，暂不支持下单")
            
            items = []
            total = Decimal("0")
            for item in data.get("items", []):
                dish = db.get(Dish, int(item.get("dish_id", 0)))
                if not dish or dish.merchant_id != merchant.id or not dish.is_available:
                    raise ValueError(f"菜品不可用")
                quantity = int(item.get("quantity", 1))
                if quantity <= 0:
                    continue
                subtotal = dish.price * quantity
                total += subtotal
                items.append(
                    OrderItem(
                        dish_id=dish.id,
                        dish_name=dish.name,
                        unit_price=dish.price,
                        quantity=quantity,
                        subtotal=subtotal,
                    )
                )
            if not items:
                raise ValueError("请至少选择一道菜")
            order = Order(
                customer_id=user.id,
                merchant_id=merchant.id,
                total_amount=total,
                delivery_address=data.get("address") or user.address or "未填写",
                items=items,
            )
            db.add(order)
            db.commit()
            return json_response({"ok": True, "message": f"下单成功，订单号 #{order.id}", "order": serialize_order(order)})
        except AuthError as ae:
            db.rollback()
            return json_response({"ok": False, "error": str(ae)}, ae.status)
        except Exception as exc:
            db.rollback()
            return json_response({"ok": False, "error": str(exc)}, 400)
        finally:
            db.close()

    @app.post("/available")
    def available_orders():
        data = payload_from_request()
        db = SessionLocal()
        try:
            user = authenticate(db, data)
            if user.role != "rider":
                raise ValueError("只有骑手可以查看接单大厅")
            orders = [serialize_order(o) for o in db.query(Order).filter_by(status="pending").order_by(Order.id).all()]
            return json_response({"ok": True, "orders": orders})
        except AuthError as ae:
            return json_response({"ok": False, "error": str(ae)}, ae.status)
        except Exception as exc:
            return json_response({"ok": False, "error": str(exc)}, 400)
        finally:
            db.close()

    @app.post("/claim")
    def claim_order():
        data = payload_from_request()
        db = SessionLocal()
        try:
            user = authenticate(db, data)
            if user.role != "rider":
                raise ValueError("只有骑手可以接单")
            result = db.execute(
                update(Order)
                .where(Order.id == int(data.get("order_id", 0)), Order.status == "pending")
                .values(rider_id=user.id, status="accepted", accepted_at=get_cst_time())
            )
            if result.rowcount != 1:
                db.rollback()
                raise ValueError("订单不存在或已被其他骑手接走")
            db.commit()
            return json_response({"ok": True, "message": f"接单成功：#{data.get('order_id')}"})
        except AuthError as ae:
            db.rollback()
            return json_response({"ok": False, "error": str(ae)}, ae.status)
        except Exception as exc:
            db.rollback()
            return json_response({"ok": False, "error": str(exc)}, 400)
        finally:
            db.close()

    @app.post("/deliver")
    def delivered_order():
        data = payload_from_request()
        db = SessionLocal()
        try:
            user = authenticate(db, data)
            order = db.get(Order, int(data.get("order_id", 0)))
            if user.role != "rider" or not order or order.rider_id != user.id or order.status != "accepted":
                raise ValueError("该订单当前不能标记已送达")
            order.status = "delivered"
            order.delivered_at = get_cst_time()
            db.commit()
            return json_response({"ok": True, "message": f"已送达：#{order.id}，已提醒用户取餐"})
        except AuthError as ae:
            db.rollback()
            return json_response({"ok": False, "error": str(ae)}, ae.status)
        except Exception as exc:
            db.rollback()
            return json_response({"ok": False, "error": str(exc)}, 400)
        finally:
            db.close()

    @app.post("/history")
    def history():
        data = payload_from_request()
        db = SessionLocal()
        try:
            user = authenticate(db, data)
            query = query_orders_by_role(db, user).filter(Order.status.in_(["completed", "reviewed"]))
            orders = [serialize_order(o) for o in query.order_by(Order.id.desc()).all()]
            return json_response({"ok": True, "orders": orders})
        except Exception as exc:
            return json_response({"ok": False, "error": str(exc)}, 400)
        finally:
            db.close()

    @app.post("/orders/my")
    def my_orders():
        data = payload_from_request()
        db = SessionLocal()
        try:
            user = authenticate(db, data)
            query = query_orders_by_role(db, user)

            active_status = ["pending", "accepted", "delivered"]
            if user.role == "rider":
                active_status = ["accepted", "delivered"]

            active_orders = [
                serialize_order(o)
                for o in query.filter(Order.status.in_(active_status)).order_by(Order.id.desc()).all()
            ]
            history_orders = [
                serialize_order(o)
                for o in query.filter(Order.status.in_(["completed", "reviewed"])).order_by(Order.id.desc()).all()
            ]

            return json_response({"ok": True, "active": active_orders, "history": history_orders})
        except Exception as exc:
            return json_response({"ok": False, "error": str(exc)}, 400)
        finally:
            db.close()

    @app.post("/complete")
    def complete_order():
        data = payload_from_request()
        db = SessionLocal()
        try:
            user = authenticate(db, data)
            order = db.get(Order, int(data.get("order_id", 0)))
            if user.role != "customer" or not order or order.customer_id != user.id or order.status != "delivered":
                raise ValueError("骑手标记已送达后，用户才可以确认收货")
            order.status = "completed"
            order.completed_at = get_cst_time()
            db.commit()
            return json_response({"ok": True, "message": f"已确认收货：#{order.id}"})
        except AuthError as ae:
            db.rollback()
            return json_response({"ok": False, "error": str(ae)}, ae.status)
        except Exception as exc:
            db.rollback()
            return json_response({"ok": False, "error": str(exc)}, 400)
        finally:
            db.close()

    @app.post("/review")
    def review_order():
        data = payload_from_request()
        db = SessionLocal()
        try:
            user = authenticate(db, data)
            order = db.get(Order, int(data.get("order_id", 0)))
            if user.role != "customer" or not order or order.customer_id != user.id or order.status != "completed":
                raise ValueError("该订单暂不可评价")
            if order.review or order.rider_review:
                raise ValueError("该订单已评价")

            merchant_rating = data.get("merchant_rating", data.get("rating", 0))
            merchant_comment = data.get("merchant_comment", data.get("comment"))
            rider_rating = data.get("rider_rating", 0)
            rider_comment = data.get("rider_comment", "")

            if not order.rider_id:
                raise ValueError("该订单没有可评价的骑手")

            review = Review(
                order_id=order.id,
                merchant_id=order.merchant_id,
                customer_id=user.id,
                rating=int(merchant_rating),
                comment=merchant_comment,
            )
            rider_review = RiderReview(
                order_id=order.id,
                rider_id=order.rider_id,
                customer_id=user.id,
                rating=int(rider_rating),
                comment=rider_comment,
            )
            order.status = "reviewed"
            db.add(review)
            db.add(rider_review)
            db.commit()
            return json_response({"ok": True, "message": "评价成功"})
        except AuthError as ae:
            db.rollback()
            return json_response({"ok": False, "error": str(ae)}, ae.status)
        except Exception as exc:
            db.rollback()
            return json_response({"ok": False, "error": str(exc)}, 400)
        finally:
            db.close()

    @app.post('/order/contact')
    def order_contact():
        data = payload_from_request()
        db = SessionLocal()
        try:
            user = authenticate(db, data)
            order = db.get(Order, int(data.get('order_id', 0)))
            if not order:
                raise ValueError('订单不存在')

            merchant_owner = order.merchant.owner if order.merchant else None

            allowed = False
            # customer can see merchant and rider for their order
            if user.role == 'customer' and order.customer_id == user.id:
                allowed = True
            # rider can see customer and merchant for their assigned order
            if user.role == 'rider' and order.rider_id == user.id:
                allowed = True
            # merchant (店主) can see customer and rider for orders of their shop
            if user.role == 'merchant' and merchant_owner and merchant_owner.id == user.id:
                allowed = True

            if not allowed:
                raise ValueError('无权限查看该订单的联系方式')

            payload = {
                'order_id': order.id,
                'customer': {
                    'username': order.customer.username if order.customer else '',
                    'phone': order.customer.phone if order.customer and order.customer.phone else ''
                },
                'merchant': {
                    'name': order.merchant.name if order.merchant else '',
                    'phone': merchant_owner.phone if merchant_owner and merchant_owner.phone else ''
                },
                'rider': {
                    'username': order.rider.username if order.rider else '',
                    'phone': order.rider.phone if order.rider and order.rider.phone else ''
                },
            }
            return json_response({'ok': True, 'contacts': payload})
        except AuthError as ae:
            return json_response({'ok': False, 'error': str(ae)}, ae.status)
        except Exception as exc:
            return json_response({'ok': False, 'error': str(exc)}, 400)
        finally:
            db.close()

    @app.post('/rider/stats')
    def rider_stats():
        data = payload_from_request()
        db = SessionLocal()
        try:
            user = authenticate(db, data)
            if user.role != 'rider':
                raise ValueError('仅骑手可查看自己的评价统计')
            stats = db.query(func.count(RiderReview.id).label('count'), func.avg(RiderReview.rating).label('avg')).filter(RiderReview.rider_id == user.id).first()
            recent = db.query(RiderReview).filter(RiderReview.rider_id == user.id).order_by(RiderReview.id.desc()).limit(5).all()
            recent_payload = [
                {
                    'id': r.id,
                    'order_id': r.order_id,
                    'customer': r.customer.username if r.customer else '',
                    'rating': r.rating,
                    'comment': r.comment or '',
                    'created_at': r.created_at.isoformat() if r.created_at else None,
                }
                for r in recent
            ]
            return json_response({'ok': True, 'count': int(stats.count or 0), 'avg': float(stats.avg or 0), 'recent': recent_payload})
        except AuthError as ae:
            return json_response({'ok': False, 'error': str(ae)}, ae.status)
        except Exception as exc:
            return json_response({'ok': False, 'error': str(exc)}, 400)
        finally:
            db.close()

    return app


app = create_app()


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug, use_reloader=False, host="127.0.0.1", port=int(os.getenv("PORT", "5000")))

from models import SessionLocal, User

db = SessionLocal()
for u in db.query(User).all():
    print(u.id, u.username, u.password, u.role)
    
db.close()

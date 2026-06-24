from database import SessionLocal
from models import User
from core.security import get_password_hash
from services.user_service import generate_serial_number

def create_first_admin():
    db = SessionLocal()
    admin_phone = "08000000000"
    
    # Check if we already ran this
    existing_admin = db.query(User).filter(User.phone_number == admin_phone).first()
    if existing_admin:
        print("Admin account already exists!")
        db.close()
        return

    # Generate their ID and hash a custom, easy-to-remember password
    new_serial = generate_serial_number(db)
    hashed_pwd = get_password_hash("admin123")

    admin_user = User(
        serial_number=new_serial,
        first_name="Chief",
        last_name="HOD",
        phone_number=admin_phone,
        hashed_password=hashed_pwd,
        role="hod",  # THIS is the magic key
        is_active=True
    )

    db.add(admin_user)
    db.commit()
    print(f"✅ Admin Created Successfully!")
    print(f"📞 Phone: {admin_phone}")
    print(f"🔑 Password: admin123")
    print(f"🏷️ Serial: {new_serial}")
    
    db.close()

if __name__ == "__main__":
    create_first_admin()
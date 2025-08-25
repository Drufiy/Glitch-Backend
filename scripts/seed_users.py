import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from app.models import Base, User

# Create tables
Base.metadata.create_all(bind=engine)

def seed_users():
    db = SessionLocal()
    try:
        # First check if users already exist
        if db.query(User).count() > 0:
            print("Users already exist in database. Skipping seeding.")
            return

        # Add your pre-registered users here
        users = [
            {
                "email": "admin@example.com",
                "password": "admin123",  # Change this to a secure password
                "name": "Admin User"
            },
            {
                "email": "user1@example.com",
                "password": "user123",  # Change this to a secure password
                "name": "Test User 1"
            },
            # Add more users as needed
        ]

        for user_data in users:
            user = User(
                email=user_data["email"],
                name=user_data["name"]
            )
            user.set_password(user_data["password"])
            db.add(user)
            print(f"Created user: {user_data['email']}")

        db.commit()
        print("Successfully seeded users!")

    except Exception as e:
        print(f"Error seeding users: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting user seeding...")
    seed_users() 
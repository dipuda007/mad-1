from app import app, db
from models import User

def init_database():
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Check if admin already exists
        admin = User.query.filter_by(email='admin@portal.com').first()
        if not admin:
            admin = User(
                email='admin@portal.com',
                role='admin',
                is_active=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Admin user created successfully!")
            print("Email: admin@portal.com")
            print("Password: admin123")
        else:
            print("Admin user already exists!")
        
        print("Database initialized successfully!")

if __name__ == '__main__':
    init_database()

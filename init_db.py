from app import app, db
from models import User
from passlib.hash import bcrypt

def init_db():
    with app.app_context():
        # Crear todas las tablas
        db.create_all()
        
        # Crear usuario administrador si no existe
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@example.com',
                password_hash=bcrypt.hash('admin123'),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
            print("Usuario administrador creado exitosamente")
        else:
            print("El usuario administrador ya existe")

if __name__ == '__main__':
    init_db() 
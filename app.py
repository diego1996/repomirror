from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from datetime import timedelta
import os
import yaml
import logging
from logging.handlers import RotatingFileHandler
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Repository, Backup, SecurityLog
from services.github_service import GitHubService
from services.storage_service import StorageService
from services.security_service import SecurityService
from services.notification_service import NotificationService

# Configuración de la aplicación
app = Flask(__name__, static_folder='web/static', template_folder='web/templates')
CORS(app)

# Cargar configuración
def load_config():
    config_path = os.getenv('CONFIG_PATH', 'config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

config = load_config()

# Configuración de la base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = config.get('database', {}).get('uri', 'sqlite:///repomirror.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuración de JWT
app.config['JWT_SECRET_KEY'] = config.get('security', {}).get('jwt_secret', 'your-secret-key')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)

# Inicialización de extensiones
jwt = JWTManager(app)
db.init_app(app)

# Configuración de logging
if not os.path.exists('logs'):
    os.makedirs('logs')

file_handler = RotatingFileHandler('logs/repomirror.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('RepoMirror startup')

# Inicialización de servicios
github_service = GitHubService(config.get('github', {}))
storage_service = StorageService(config.get('storage', {}))
security_service = SecurityService()
notification_service = NotificationService()

# Rutas de autenticación
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data.get('username')).first()
    
    if user and check_password_hash(user.password_hash, data.get('password')):
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)
        
        security_service.log_login(user.id, True)
        return jsonify({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user.to_dict()
        })
    
    security_service.log_login(data.get('username'), False)
    return jsonify({'error': 'Credenciales inválidas'}), 401

@app.route('/api/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    current_user = get_jwt_identity()
    access_token = create_access_token(identity=current_user)
    return jsonify({'access_token': access_token})

@app.route('/api/auth/logout', methods=['POST'])
@jwt_required()
def logout():
    current_user = get_jwt_identity()
    security_service.log_logout(current_user)
    return jsonify({'message': 'Sesión cerrada exitosamente'})

# Rutas de repositorios
@app.route('/api/repositories', methods=['GET'])
@jwt_required()
def get_repositories():
    user_id = get_jwt_identity()
    repositories = Repository.query.filter_by(user_id=user_id).all()
    return jsonify([repo.to_dict() for repo in repositories])

@app.route('/api/repositories', methods=['POST'])
@jwt_required()
def add_repository():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    try:
        repo = Repository(
            user_id=user_id,
            url=data['url'],
            storage_type=data['storage_type'],
            schedule=data.get('schedule', 'manual')
        )
        db.session.add(repo)
        db.session.commit()
        
        notification_service.send_notification(
            user_id,
            'success',
            'Repositorio agregado',
            f'El repositorio {data["url"]} ha sido agregado exitosamente'
        )
        
        return jsonify(repo.to_dict())
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error adding repository: {str(e)}')
        return jsonify({'error': 'Error al agregar el repositorio'}), 500

@app.route('/api/repositories/<int:repo_id>/backup', methods=['POST'])
@jwt_required()
def start_backup(repo_id):
    user_id = get_jwt_identity()
    repo = Repository.query.filter_by(id=repo_id, user_id=user_id).first_or_404()
    
    try:
        backup = Backup(repository_id=repo.id)
        db.session.add(backup)
        db.session.commit()
        
        # Iniciar backup en segundo plano
        github_service.clone_repository(repo.url, backup.id)
        storage_service.upload_backup(backup.id, repo.storage_type)
        
        notification_service.send_notification(
            user_id,
            'info',
            'Backup iniciado',
            f'Se ha iniciado el backup del repositorio {repo.url}'
        )
        
        return jsonify({'message': 'Backup iniciado'})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error starting backup: {str(e)}')
        return jsonify({'error': 'Error al iniciar el backup'}), 500

# Rutas de seguridad
@app.route('/api/security/status', methods=['GET'])
@jwt_required()
def get_security_status():
    user_id = get_jwt_identity()
    status = security_service.get_security_status(user_id)
    return jsonify(status)

@app.route('/api/security/logs', methods=['GET'])
@jwt_required()
def get_security_logs():
    user_id = get_jwt_identity()
    logs = SecurityLog.query.filter_by(user_id=user_id).order_by(SecurityLog.timestamp.desc()).limit(100).all()
    return jsonify([log.to_dict() for log in logs])

# Rutas de notificaciones
@app.route('/api/notifications', methods=['GET'])
@jwt_required()
def get_notifications():
    user_id = get_jwt_identity()
    notifications = notification_service.get_notifications(user_id)
    return jsonify(notifications)

# Rutas de estadísticas
@app.route('/api/stats', methods=['GET'])
@jwt_required()
def get_stats():
    user_id = get_jwt_identity()
    
    stats = {
        'total_repos': Repository.query.filter_by(user_id=user_id).count(),
        'total_backups': Backup.query.join(Repository).filter(Repository.user_id == user_id).count(),
        'storage_used': storage_service.get_total_storage_used(user_id),
        'recent_activity': get_recent_activity(user_id)
    }
    
    return jsonify(stats)

def get_recent_activity(user_id):
    recent_backups = Backup.query.join(Repository).filter(
        Repository.user_id == user_id
    ).order_by(Backup.created_at.desc()).limit(5).all()
    
    return [backup.to_dict() for backup in recent_backups]

# Rutas de archivos estáticos
@app.route('/')
def index():
    return send_from_directory(app.template_folder, 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(app.static_folder, path)

# Manejo de errores
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Recurso no encontrado'}), 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f'Server Error: {error}')
    return jsonify({'error': 'Error interno del servidor'}), 500

# Inicialización de la base de datos
def init_app():
    with app.app_context():
        db.create_all()
        
        # Crear usuario administrador si no existe
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                password_hash=generate_password_hash('admin'),
                email='admin@example.com',
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
            app.logger.info('Usuario administrador creado')

# Inicializar la app
init_app()

if __name__ == '__main__':
    app.run(debug=True) 
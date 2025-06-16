from models import db, SecurityLog, User
from datetime import datetime, timedelta
import hashlib
import re
import logging

class SecurityService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.password_regex = re.compile(
            r'^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]{8,}$'
        )
        self.max_login_attempts = 5
        self.lockout_duration = timedelta(minutes=30)

    def log_login(self, user_id_or_username, success):
        """
        Registra un intento de inicio de sesión.
        
        Args:
            user_id_or_username: ID o nombre de usuario
            success: Si el intento fue exitoso
        """
        log = SecurityLog(
            user_id=user_id_or_username if isinstance(user_id_or_username, int) else None,
            username=user_id_or_username if isinstance(user_id_or_username, str) else None,
            action='login',
            success=success,
            ip_address=self._get_client_ip(),
            user_agent=self._get_user_agent()
        )
        
        db.session.add(log)
        db.session.commit()
        
        if not success:
            self._handle_failed_login(user_id_or_username)

    def log_logout(self, user_id):
        """
        Registra un cierre de sesión.
        
        Args:
            user_id: ID del usuario
        """
        log = SecurityLog(
            user_id=user_id,
            action='logout',
            success=True,
            ip_address=self._get_client_ip(),
            user_agent=self._get_user_agent()
        )
        
        db.session.add(log)
        db.session.commit()

    def get_security_status(self, user_id):
        """
        Obtiene el estado de seguridad de un usuario.
        
        Args:
            user_id: ID del usuario
        """
        user = User.query.get(user_id)
        if not user:
            return {'is_secure': False, 'warnings': ['Usuario no encontrado']}
        
        warnings = []
        
        # Verificar contraseña
        if not self._is_password_secure(user.password_hash):
            warnings.append({
                'id': 'weak_password',
                'title': 'Contraseña débil',
                'message': 'Se recomienda cambiar la contraseña por una más segura'
            })
        
        # Verificar intentos de inicio de sesión fallidos
        failed_attempts = self._get_failed_login_attempts(user_id)
        if failed_attempts >= self.max_login_attempts:
            warnings.append({
                'id': 'too_many_attempts',
                'title': 'Demasiados intentos fallidos',
                'message': 'La cuenta está bloqueada temporalmente'
            })
        
        # Verificar actividad sospechosa
        suspicious_activity = self._check_suspicious_activity(user_id)
        if suspicious_activity:
            warnings.append({
                'id': 'suspicious_activity',
                'title': 'Actividad sospechosa detectada',
                'message': suspicious_activity
            })
        
        return {
            'is_secure': len(warnings) == 0,
            'warnings': warnings,
            'last_check': datetime.utcnow().isoformat()
        }

    def _handle_failed_login(self, user_id_or_username):
        """
        Maneja un intento de inicio de sesión fallido.
        
        Args:
            user_id_or_username: ID o nombre de usuario
        """
        if isinstance(user_id_or_username, int):
            user = User.query.get(user_id_or_username)
        else:
            user = User.query.filter_by(username=user_id_or_username).first()
        
        if user:
            failed_attempts = self._get_failed_login_attempts(user.id)
            if failed_attempts >= self.max_login_attempts:
                user.locked_until = datetime.utcnow() + self.lockout_duration
                db.session.commit()
                self.logger.warning(f'Usuario {user.username} bloqueado por demasiados intentos fallidos')

    def _get_failed_login_attempts(self, user_id):
        """
        Obtiene el número de intentos de inicio de sesión fallidos recientes.
        
        Args:
            user_id: ID del usuario
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=30)
        return SecurityLog.query.filter(
            SecurityLog.user_id == user_id,
            SecurityLog.action == 'login',
            SecurityLog.success == False,
            SecurityLog.timestamp > cutoff_time
        ).count()

    def _check_suspicious_activity(self, user_id):
        """
        Verifica si hay actividad sospechosa.
        
        Args:
            user_id: ID del usuario
        """
        # Verificar múltiples inicios de sesión desde diferentes IPs
        recent_logins = SecurityLog.query.filter(
            SecurityLog.user_id == user_id,
            SecurityLog.action == 'login',
            SecurityLog.success == True,
            SecurityLog.timestamp > datetime.utcnow() - timedelta(hours=24)
        ).all()
        
        unique_ips = len(set(log.ip_address for log in recent_logins))
        if unique_ips > 3:
            return 'Se detectaron inicios de sesión desde múltiples ubicaciones'
        
        return None

    def _is_password_secure(self, password_hash):
        """
        Verifica si una contraseña es segura.
        
        Args:
            password_hash: Hash de la contraseña
        """
        # Aquí podrías implementar una verificación más compleja
        # Por ahora, solo verificamos que el hash no sea el predeterminado
        return password_hash != 'default_hash'

    def _get_client_ip(self):
        """
        Obtiene la IP del cliente.
        """
        # Implementar según el framework web que estés usando
        return '127.0.0.1'

    def _get_user_agent(self):
        """
        Obtiene el User-Agent del cliente.
        """
        # Implementar según el framework web que estés usando
        return 'Unknown'

    def validate_password(self, password):
        """
        Valida que una contraseña cumpla con los requisitos de seguridad.
        
        Args:
            password: Contraseña a validar
        """
        if not self.password_regex.match(password):
            return False, 'La contraseña debe tener al menos 8 caracteres, una letra, un número y un carácter especial'
        
        return True, None

    def generate_password_hash(self, password):
        """
        Genera un hash seguro para una contraseña.
        
        Args:
            password: Contraseña a hashear
        """
        salt = hashlib.sha256(str(datetime.utcnow()).encode()).hexdigest()
        return hashlib.sha256((password + salt).encode()).hexdigest() 
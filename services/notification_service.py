from models import db, Notification
from datetime import datetime, timedelta
import json

class NotificationService:
    def __init__(self):
        self.notification_types = {
            'success': {
                'icon': 'check-circle',
                'color': 'green'
            },
            'error': {
                'icon': 'exclamation-circle',
                'color': 'red'
            },
            'warning': {
                'icon': 'exclamation-triangle',
                'color': 'yellow'
            },
            'info': {
                'icon': 'info-circle',
                'color': 'blue'
            }
        }

    def send_notification(self, user_id, type, title, message, duration=5000):
        """
        Envía una notificación a un usuario específico.
        
        Args:
            user_id: ID del usuario
            type: Tipo de notificación (success, error, warning, info)
            title: Título de la notificación
            message: Mensaje de la notificación
            duration: Duración en milisegundos (0 para persistente)
        """
        notification = Notification(
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            duration=duration,
            created_at=datetime.utcnow()
        )
        
        db.session.add(notification)
        db.session.commit()
        
        return notification

    def get_notifications(self, user_id, limit=50):
        """
        Obtiene las notificaciones recientes de un usuario.
        
        Args:
            user_id: ID del usuario
            limit: Número máximo de notificaciones a obtener
        """
        # Obtener notificaciones no leídas y recientes
        notifications = Notification.query.filter_by(
            user_id=user_id,
            read=False
        ).order_by(
            Notification.created_at.desc()
        ).limit(limit).all()
        
        # Marcar como leídas las notificaciones antiguas
        old_notifications = Notification.query.filter(
            Notification.user_id == user_id,
            Notification.read == False,
            Notification.created_at < datetime.utcnow() - timedelta(days=7)
        ).all()
        
        for notification in old_notifications:
            notification.read = True
        
        db.session.commit()
        
        return [self._format_notification(n) for n in notifications]

    def mark_as_read(self, notification_id, user_id):
        """
        Marca una notificación como leída.
        
        Args:
            notification_id: ID de la notificación
            user_id: ID del usuario
        """
        notification = Notification.query.filter_by(
            id=notification_id,
            user_id=user_id
        ).first()
        
        if notification:
            notification.read = True
            db.session.commit()
            return True
        
        return False

    def delete_notification(self, notification_id, user_id):
        """
        Elimina una notificación.
        
        Args:
            notification_id: ID de la notificación
            user_id: ID del usuario
        """
        notification = Notification.query.filter_by(
            id=notification_id,
            user_id=user_id
        ).first()
        
        if notification:
            db.session.delete(notification)
            db.session.commit()
            return True
        
        return False

    def _format_notification(self, notification):
        """
        Formatea una notificación para el frontend.
        
        Args:
            notification: Objeto Notification
        """
        type_config = self.notification_types.get(notification.type, self.notification_types['info'])
        
        return {
            'id': notification.id,
            'type': notification.type,
            'title': notification.title,
            'message': notification.message,
            'duration': notification.duration,
            'created_at': notification.created_at.isoformat(),
            'read': notification.read,
            'icon': type_config['icon'],
            'color': type_config['color']
        }

    def cleanup_old_notifications(self, days=30):
        """
        Limpia las notificaciones antiguas.
        
        Args:
            days: Número de días después de los cuales eliminar notificaciones
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        Notification.query.filter(
            Notification.created_at < cutoff_date
        ).delete()
        
        db.session.commit() 
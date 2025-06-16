const NotificationSystem = {
    template: `
        <div class="fixed bottom-0 right-0 p-4 space-y-4 z-50">
            <transition-group name="notification">
                <div v-for="notification in notifications" 
                     :key="notification.id"
                     :class="getNotificationClass(notification.type)"
                     class="max-w-sm w-full bg-white shadow-lg rounded-lg pointer-events-auto flex">
                    <div class="flex-1 p-4">
                        <div class="flex items-start">
                            <div class="flex-shrink-0">
                                <i :class="getNotificationIcon(notification.type)" 
                                   class="h-6 w-6"></i>
                            </div>
                            <div class="ml-3 w-0 flex-1">
                                <p class="text-sm font-medium text-gray-900">
                                    {{ notification.title }}
                                </p>
                                <p class="mt-1 text-sm text-gray-500">
                                    {{ notification.message }}
                                </p>
                            </div>
                            <div class="ml-4 flex-shrink-0 flex">
                                <button @click="removeNotification(notification.id)"
                                        class="bg-white rounded-md inline-flex text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                                    <span class="sr-only">Cerrar</span>
                                    <i class="fas fa-times"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </transition-group>
        </div>
    `,
    
    data() {
        return {
            notifications: [],
            nextId: 1
        }
    },
    
    methods: {
        addNotification(type, title, message, duration = 5000) {
            const id = this.nextId++;
            this.notifications.push({ id, type, title, message });
            
            if (duration > 0) {
                setTimeout(() => {
                    this.removeNotification(id);
                }, duration);
            }
        },
        
        removeNotification(id) {
            this.notifications = this.notifications.filter(n => n.id !== id);
        },
        
        getNotificationClass(type) {
            const classes = {
                'success': 'bg-green-50 border-l-4 border-green-400',
                'error': 'bg-red-50 border-l-4 border-red-400',
                'warning': 'bg-yellow-50 border-l-4 border-yellow-400',
                'info': 'bg-blue-50 border-l-4 border-blue-400'
            };
            return classes[type] || classes.info;
        },
        
        getNotificationIcon(type) {
            const icons = {
                'success': 'fas fa-check-circle text-green-400',
                'error': 'fas fa-exclamation-circle text-red-400',
                'warning': 'fas fa-exclamation-triangle text-yellow-400',
                'info': 'fas fa-info-circle text-blue-400'
            };
            return icons[type] || icons.info;
        }
    }
}; 
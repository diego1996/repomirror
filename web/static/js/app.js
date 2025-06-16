const app = new Vue({
    el: '#app',
    components: {
        'dashboard': Dashboard,
        'repository-manager': RepositoryManager,
        'notification-system': NotificationSystem
    },
    data: {
        currentView: 'dashboard',
        user: null,
        securityStatus: {
            isSecure: true,
            lastCheck: null,
            warnings: []
        }
    },
    template: `
        <div class="min-h-screen bg-gray-100">
            <!-- Barra de navegación -->
            <nav class="bg-white shadow-sm">
                <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div class="flex justify-between h-16">
                        <div class="flex">
                            <div class="flex-shrink-0 flex items-center">
                                <img class="h-8 w-auto" src="/static/img/logo.png" alt="RepoMirror">
                                <span class="ml-2 text-xl font-bold text-gray-900">RepoMirror</span>
                            </div>
                            <div class="hidden sm:ml-6 sm:flex sm:space-x-8">
                                <button @click="currentView = 'dashboard'"
                                        :class="{'border-blue-500 text-gray-900': currentView === 'dashboard',
                                                'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700': currentView !== 'dashboard'}"
                                        class="border-b-2 px-1 pt-1 text-sm font-medium">
                                    Dashboard
                                </button>
                                <button @click="currentView = 'repositories'"
                                        :class="{'border-blue-500 text-gray-900': currentView === 'repositories',
                                                'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700': currentView !== 'repositories'}"
                                        class="border-b-2 px-1 pt-1 text-sm font-medium">
                                    Repositorios
                                </button>
                            </div>
                        </div>
                        <div class="hidden sm:ml-6 sm:flex sm:items-center space-x-4">
                            <!-- Indicador de seguridad -->
                            <div class="security-badge" 
                                 :class="{'insecure': !securityStatus.isSecure}"
                                 @click="showSecurityDetails">
                                <i class="fas fa-shield-alt text-gray-600"></i>
                            </div>
                            
                            <!-- Menú de usuario -->
                            <div class="ml-3 relative">
                                <div>
                                    <button @click="showUserMenu = !showUserMenu"
                                            class="max-w-xs bg-white flex items-center text-sm rounded-full focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                                        <img class="h-8 w-8 rounded-full" :src="user?.avatar" alt="">
                                    </button>
                                </div>
                                <div v-if="showUserMenu"
                                     class="origin-top-right absolute right-0 mt-2 w-48 rounded-md shadow-lg py-1 bg-white ring-1 ring-black ring-opacity-5">
                                    <a href="#" @click="showProfile" class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                                        Perfil
                                    </a>
                                    <a href="#" @click="showSecuritySettings" class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                                        Seguridad
                                    </a>
                                    <a href="#" @click="logout" class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                                        Cerrar Sesión
                                    </a>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </nav>

            <!-- Contenido principal -->
            <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
                <component :is="currentView === 'dashboard' ? 'dashboard' : 'repository-manager'"></component>
            </main>

            <!-- Sistema de notificaciones -->
            <notification-system ref="notifications"></notification-system>

            <!-- Modal de seguridad -->
            <div v-if="showSecurityModal" class="fixed z-10 inset-0 overflow-y-auto">
                <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
                    <div class="fixed inset-0 transition-opacity" aria-hidden="true">
                        <div class="absolute inset-0 bg-gray-500 opacity-75"></div>
                    </div>
                    <div class="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
                        <div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                            <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">
                                Estado de Seguridad
                            </h3>
                            <div class="space-y-4">
                                <div v-for="warning in securityStatus.warnings" 
                                     :key="warning.id"
                                     class="flex items-start">
                                    <i class="fas fa-exclamation-triangle text-yellow-400 mt-1"></i>
                                    <div class="ml-3">
                                        <p class="text-sm font-medium text-gray-900">
                                            {{ warning.title }}
                                        </p>
                                        <p class="text-sm text-gray-500">
                                            {{ warning.message }}
                                        </p>
                                    </div>
                                </div>
                                <div v-if="securityStatus.warnings.length === 0" 
                                     class="text-sm text-gray-500">
                                    No se detectaron problemas de seguridad.
                                </div>
                            </div>
                        </div>
                        <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                            <button @click="showSecurityModal = false" 
                                    class="w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm">
                                Cerrar
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `,
    methods: {
        async checkAuth() {
            try {
                const response = await axios.get('/api/auth/me');
                this.user = response.data;
                this.checkSecurityStatus();
            } catch (error) {
                window.location.href = '/login';
            }
        },
        
        async logout() {
            try {
                await SecurityService.logout();
                window.location.href = '/login';
            } catch (error) {
                this.$refs.notifications.addNotification(
                    'error',
                    'Error',
                    'Error al cerrar sesión. Por favor, intente nuevamente.'
                );
            }
        },
        
        showProfile() {
            // Implementar vista de perfil
            this.$refs.notifications.addNotification(
                'info',
                'Próximamente',
                'La funcionalidad de perfil estará disponible próximamente.'
            );
        },
        
        showSecuritySettings() {
            // Implementar configuración de seguridad
            this.$refs.notifications.addNotification(
                'info',
                'Próximamente',
                'La configuración de seguridad estará disponible próximamente.'
            );
        },
        
        showSecurityDetails() {
            this.showSecurityModal = true;
        },
        
        async checkSecurityStatus() {
            try {
                const response = await axios.get('/api/security/status');
                this.securityStatus = response.data;
                
                if (!this.securityStatus.isSecure) {
                    this.$refs.notifications.addNotification(
                        'warning',
                        'Advertencia de Seguridad',
                        'Se han detectado problemas de seguridad. Haga clic en el ícono de escudo para más detalles.'
                    );
                }
            } catch (error) {
                console.error('Error checking security status:', error);
            }
        }
    },
    mounted() {
        this.checkAuth();
        
        // Verificar estado de seguridad cada 5 minutos
        setInterval(() => {
            this.checkSecurityStatus();
        }, 5 * 60 * 1000);
    }
}); 
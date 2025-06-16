const SecurityService = {
    // Configuración de seguridad
    config: {
        tokenKey: 'repomirror_token',
        refreshTokenKey: 'repomirror_refresh_token',
        tokenExpiryKey: 'repomirror_token_expiry',
        refreshInterval: 5 * 60 * 1000, // 5 minutos
    },

    // Métodos de autenticación
    async login(username, password) {
        try {
            const response = await axios.post('/api/auth/login', {
                username,
                password
            });
            
            this.setTokens(response.data);
            return response.data;
        } catch (error) {
            throw this.handleAuthError(error);
        }
    },

    async logout() {
        try {
            await axios.post('/api/auth/logout');
            this.clearTokens();
        } catch (error) {
            console.error('Error during logout:', error);
        }
    },

    async refreshToken() {
        try {
            const refreshToken = localStorage.getItem(this.config.refreshTokenKey);
            if (!refreshToken) {
                throw new Error('No refresh token available');
            }

            const response = await axios.post('/api/auth/refresh', {
                refresh_token: refreshToken
            });

            this.setTokens(response.data);
            return response.data;
        } catch (error) {
            this.clearTokens();
            throw this.handleAuthError(error);
        }
    },

    // Gestión de tokens
    setTokens(data) {
        localStorage.setItem(this.config.tokenKey, data.access_token);
        localStorage.setItem(this.config.refreshTokenKey, data.refresh_token);
        localStorage.setItem(this.config.tokenExpiryKey, 
            (Date.now() + data.expires_in * 1000).toString());
    },

    clearTokens() {
        localStorage.removeItem(this.config.tokenKey);
        localStorage.removeItem(this.config.refreshTokenKey);
        localStorage.removeItem(this.config.tokenExpiryKey);
    },

    getToken() {
        return localStorage.getItem(this.config.tokenKey);
    },

    isTokenValid() {
        const expiry = localStorage.getItem(this.config.tokenExpiryKey);
        if (!expiry) return false;
        return Date.now() < parseInt(expiry);
    },

    // Interceptor de Axios para manejar tokens
    setupAxiosInterceptors() {
        // Interceptor para agregar el token a las peticiones
        axios.interceptors.request.use(
            config => {
                if (this.isTokenValid()) {
                    config.headers.Authorization = `Bearer ${this.getToken()}`;
                }
                return config;
            },
            error => Promise.reject(error)
        );

        // Interceptor para manejar errores de autenticación
        axios.interceptors.response.use(
            response => response,
            async error => {
                const originalRequest = error.config;

                // Si el error es 401 y no es una petición de refresh
                if (error.response.status === 401 && !originalRequest._retry) {
                    originalRequest._retry = true;

                    try {
                        await this.refreshToken();
                        originalRequest.headers.Authorization = `Bearer ${this.getToken()}`;
                        return axios(originalRequest);
                    } catch (refreshError) {
                        this.clearTokens();
                        window.location.href = '/login';
                        return Promise.reject(refreshError);
                    }
                }

                return Promise.reject(error);
            }
        );
    },

    // Iniciar el servicio de seguridad
    init() {
        this.setupAxiosInterceptors();
        this.startTokenRefresh();
    },

    // Refrescar token automáticamente
    startTokenRefresh() {
        setInterval(() => {
            if (this.isTokenValid()) {
                const expiry = parseInt(localStorage.getItem(this.config.tokenExpiryKey));
                const timeUntilExpiry = expiry - Date.now();
                
                // Si el token expira en menos de 5 minutos, refrescarlo
                if (timeUntilExpiry < 5 * 60 * 1000) {
                    this.refreshToken().catch(error => {
                        console.error('Error refreshing token:', error);
                    });
                }
            }
        }, this.config.refreshInterval);
    },

    // Manejo de errores de autenticación
    handleAuthError(error) {
        if (error.response) {
            switch (error.response.status) {
                case 401:
                    this.clearTokens();
                    window.location.href = '/login';
                    return new Error('Sesión expirada. Por favor, inicie sesión nuevamente.');
                case 403:
                    return new Error('No tiene permisos para realizar esta acción.');
                default:
                    return new Error('Error de autenticación. Por favor, intente nuevamente.');
            }
        }
        return error;
    },

    // Verificación de permisos
    hasPermission(permission) {
        const user = JSON.parse(localStorage.getItem('user') || '{}');
        return user.permissions && user.permissions.includes(permission);
    },

    // Verificación de roles
    hasRole(role) {
        const user = JSON.parse(localStorage.getItem('user') || '{}');
        return user.roles && user.roles.includes(role);
    }
}; 
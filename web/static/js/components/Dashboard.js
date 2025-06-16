const Dashboard = {
    template: `
        <div class="p-6">
            <!-- Header con estadísticas principales -->
            <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                <div class="bg-white rounded-lg shadow p-6">
                    <div class="flex items-center">
                        <div class="p-3 rounded-full bg-blue-100 text-blue-600">
                            <i class="fas fa-code-branch text-2xl"></i>
                        </div>
                        <div class="ml-4">
                            <p class="text-sm text-gray-500">Repositorios Totales</p>
                            <p class="text-2xl font-semibold">{{ stats.totalRepos }}</p>
                        </div>
                    </div>
                </div>
                
                <div class="bg-white rounded-lg shadow p-6">
                    <div class="flex items-center">
                        <div class="p-3 rounded-full bg-green-100 text-green-600">
                            <i class="fas fa-sync text-2xl"></i>
                        </div>
                        <div class="ml-4">
                            <p class="text-sm text-gray-500">Respaldos Activos</p>
                            <p class="text-2xl font-semibold">{{ stats.activeBackups }}</p>
                        </div>
                    </div>
                </div>
                
                <div class="bg-white rounded-lg shadow p-6">
                    <div class="flex items-center">
                        <div class="p-3 rounded-full bg-purple-100 text-purple-600">
                            <i class="fas fa-hdd text-2xl"></i>
                        </div>
                        <div class="ml-4">
                            <p class="text-sm text-gray-500">Almacenamiento</p>
                            <p class="text-2xl font-semibold">{{ formatStorage(stats.storageUsed) }}</p>
                        </div>
                    </div>
                </div>
                
                <div class="bg-white rounded-lg shadow p-6">
                    <div class="flex items-center">
                        <div class="p-3 rounded-full bg-yellow-100 text-yellow-600">
                            <i class="fas fa-clock text-2xl"></i>
                        </div>
                        <div class="ml-4">
                            <p class="text-sm text-gray-500">Último Respaldo</p>
                            <p class="text-2xl font-semibold">{{ formatDate(stats.lastBackup) }}</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Gráficos y métricas -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                <!-- Gráfico de respaldos por día -->
                <div class="bg-white rounded-lg shadow p-6">
                    <h3 class="text-lg font-semibold mb-4">Respaldos por Día</h3>
                    <canvas ref="backupsChart"></canvas>
                </div>
                
                <!-- Distribución de almacenamiento -->
                <div class="bg-white rounded-lg shadow p-6">
                    <h3 class="text-lg font-semibold mb-4">Distribución de Almacenamiento</h3>
                    <canvas ref="storageChart"></canvas>
                </div>
            </div>

            <!-- Actividad reciente -->
            <div class="bg-white rounded-lg shadow">
                <div class="p-6 border-b">
                    <h3 class="text-lg font-semibold">Actividad Reciente</h3>
                </div>
                <div class="p-6">
                    <div v-if="activities.length === 0" class="text-center text-gray-500 py-4">
                        No hay actividad reciente
                    </div>
                    <div v-else class="space-y-4">
                        <div v-for="activity in activities" :key="activity.id" 
                             class="flex items-center p-4 bg-gray-50 rounded-lg">
                            <div :class="getActivityIconClass(activity.type)" class="p-2 rounded-full">
                                <i :class="getActivityIcon(activity.type)"></i>
                            </div>
                            <div class="ml-4">
                                <p class="font-medium">{{ activity.description }}</p>
                                <p class="text-sm text-gray-500">{{ formatDate(activity.timestamp) }}</p>
                            </div>
                            <div class="ml-auto">
                                <span :class="getStatusClass(activity.status)" 
                                      class="px-2 py-1 rounded-full text-xs">
                                    {{ activity.status }}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `,
    
    data() {
        return {
            stats: {
                totalRepos: 0,
                activeBackups: 0,
                storageUsed: 0,
                lastBackup: null
            },
            activities: [],
            backupsChart: null,
            storageChart: null
        }
    },
    
    methods: {
        formatStorage(bytes) {
            const units = ['B', 'KB', 'MB', 'GB', 'TB'];
            let size = bytes;
            let unitIndex = 0;
            
            while (size >= 1024 && unitIndex < units.length - 1) {
                size /= 1024;
                unitIndex++;
            }
            
            return `${size.toFixed(2)} ${units[unitIndex]}`;
        },
        
        formatDate(date) {
            if (!date) return 'Nunca';
            return new Date(date).toLocaleString();
        },
        
        getActivityIcon(type) {
            const icons = {
                'backup': 'fas fa-sync',
                'clone': 'fas fa-code-branch',
                'delete': 'fas fa-trash',
                'error': 'fas fa-exclamation-circle'
            };
            return icons[type] || 'fas fa-info-circle';
        },
        
        getActivityIconClass(type) {
            const classes = {
                'backup': 'bg-blue-100 text-blue-600',
                'clone': 'bg-green-100 text-green-600',
                'delete': 'bg-red-100 text-red-600',
                'error': 'bg-yellow-100 text-yellow-600'
            };
            return classes[type] || 'bg-gray-100 text-gray-600';
        },
        
        getStatusClass(status) {
            const classes = {
                'success': 'bg-green-100 text-green-800',
                'error': 'bg-red-100 text-red-800',
                'pending': 'bg-yellow-100 text-yellow-800',
                'in_progress': 'bg-blue-100 text-blue-800'
            };
            return classes[status] || 'bg-gray-100 text-gray-800';
        },
        
        async fetchData() {
            try {
                const [statsResponse, activitiesResponse] = await Promise.all([
                    axios.get('/api/stats'),
                    axios.get('/api/activities')
                ]);
                
                this.stats = statsResponse.data;
                this.activities = activitiesResponse.data;
                
                this.updateCharts();
            } catch (error) {
                console.error('Error fetching dashboard data:', error);
            }
        },
        
        updateCharts() {
            // Actualizar gráfico de respaldos
            if (this.backupsChart) {
                this.backupsChart.destroy();
            }
            
            const backupsCtx = this.$refs.backupsChart.getContext('2d');
            this.backupsChart = new Chart(backupsCtx, {
                type: 'line',
                data: {
                    labels: this.stats.backupHistory.map(h => h.date),
                    datasets: [{
                        label: 'Respaldos',
                        data: this.stats.backupHistory.map(h => h.count),
                        borderColor: 'rgb(59, 130, 246)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });
            
            // Actualizar gráfico de almacenamiento
            if (this.storageChart) {
                this.storageChart.destroy();
            }
            
            const storageCtx = this.$refs.storageChart.getContext('2d');
            this.storageChart = new Chart(storageCtx, {
                type: 'doughnut',
                data: {
                    labels: this.stats.storageDistribution.map(d => d.type),
                    datasets: [{
                        data: this.stats.storageDistribution.map(d => d.size),
                        backgroundColor: [
                            'rgb(59, 130, 246)',
                            'rgb(16, 185, 129)',
                            'rgb(245, 158, 11)'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });
        }
    },
    
    mounted() {
        this.fetchData();
        // Actualizar datos cada 5 minutos
        setInterval(this.fetchData, 300000);
    }
}; 
// Analytics page - fetch and display detection statistics with charts

let hourlyChart = null;
let dailyChart = null;
let confidenceChart = null;
let statusChart = null;

async function initAnalytics() {
    try {
        // Fetch stats from APIs
        const statsResponse = await fetch('/api/stats');
        if (!statsResponse.ok) throw new Error(`Stats API error: ${statsResponse.status}`);
        const stats = await statsResponse.json();
        
        const hourlyResponse = await fetch('/api/detections/hourly');
        if (!hourlyResponse.ok) throw new Error(`Hourly API error: ${hourlyResponse.status}`);
        const hourlyData = await hourlyResponse.json();
        
        if (hourlyData.error) {
            throw new Error(`Hourly API returned error: ${hourlyData.error}`);
        }
        
        const dailyResponse = await fetch('/api/detections/daily');
        if (!dailyResponse.ok) throw new Error(`Daily API error: ${dailyResponse.status}`);
        const dailyData = await dailyResponse.json();
        
        if (dailyData.error) {
            throw new Error(`Daily API returned error: ${dailyData.error}`);
        }

        // Render insights
        renderInsights(stats, hourlyData, dailyData);

        // Initialize charts
        initHourlyChart(hourlyData);
        initDailyChart(dailyData);
        initConfidenceChart(stats);
        initStatusChart(stats);
    } catch (error) {
        console.error('Failed to load analytics data:', error);
        document.getElementById('report-insights').innerHTML = 
            `<li style="color: red;"><strong>❌ Error:</strong> ${error.message}</li>`;
    }
}

function renderInsights(stats, hourlyData, dailyData) {
    const insightsList = document.getElementById('report-insights');
    const insights = [];
    
    const totalDetections = stats.detection_status.detected;
    const avgConfidence = (stats.avg_confidence * 100).toFixed(1);
    const totalHourly = hourlyData.data.reduce((a, b) => a + b, 0);
    const totalDaily = dailyData.data.reduce((a, b) => a + b, 0);
    
    if (totalDetections === 0) {
        insights.push('Belum ada data deteksi.');
    } else {
        insights.push(`Total deteksi rokok tercatat: <strong>${totalDetections}</strong> kejadian`);
        insights.push(`Rata-rata tingkat keyakinan: <strong>${avgConfidence}%</strong>`);
        
        const maxHourly = Math.max(...hourlyData.data);
        const maxDailyIndex = dailyData.data.indexOf(Math.max(...dailyData.data));
        const maxDaily = dailyData.data[maxDailyIndex];
        
        if (maxHourly > 0) {
            insights.push(`Jam tersibuk: <strong>${maxHourly}</strong> deteksi dalam satu jam`);
        }
        if (maxDaily > 0) {
            insights.push(`Hari tersibuk: <strong>${dailyData.labels[maxDailyIndex]}</strong> dengan <strong>${maxDaily}</strong> deteksi`);
        }
    }
    
    insightsList.innerHTML = insights
        .map(insight => `<li>${insight}</li>`)
        .join('');
}

function initHourlyChart(data) {
    try {
        const ctx = document.getElementById('chart-hourly');
        if (ctx && hourlyChart) {
            hourlyChart.destroy();
        }
        
        if (ctx) {
            hourlyChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: 'Jumlah Deteksi',
                        data: data.data,
                        backgroundColor: '#ff6b6b',
                        borderRadius: 4
                    }]
                },
                options: {
                    indexAxis: 'y', // Horizontal bar chart
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: {
                            display: true,
                            labels: { font: { size: 12 } }
                        }
                    },
                    scales: {
                        x: {
                            beginAtZero: true,
                            ticks: { stepSize: 1 }
                        }
                    }
                }
            });
        }
    } catch (error) {
        console.error('Error initializing hourly chart:', error);
    }
}

function initDailyChart(data) {
    try {
        const ctx = document.getElementById('chart-daily');
        if (ctx && dailyChart) {
            dailyChart.destroy();
        }
        
        if (ctx) {
            dailyChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: 'Jumlah Deteksi',
                        data: data.data,
                        backgroundColor: '#4a90e2',
                        borderRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: {
                            display: true,
                            labels: { font: { size: 12 } }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: { stepSize: 1 }
                        }
                    }
                }
            });
        }
    } catch (error) {
        console.error('Error initializing daily chart:', error);
    }
}

function initConfidenceChart(stats) {
    try {
        const ctx = document.getElementById('chart-confidence');
        if (ctx && confidenceChart) {
            confidenceChart.destroy();
        }
        
        if (ctx) {
            confidenceChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['Rata-rata Keyakinan'],
                    datasets: [{
                        label: 'Tingkat Keyakinan (%)',
                        data: [(stats.avg_confidence * 100).toFixed(1)],
                        backgroundColor: '#50c878',
                        borderRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    indexAxis: 'y',
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        x: {
                            beginAtZero: true,
                            max: 100
                        }
                    }
                }
            });
        }
    } catch (error) {
        console.error('Error initializing confidence chart:', error);
    }
}

function initStatusChart(stats) {
    try {
        const ctx = document.getElementById('chart-status');
        if (ctx && statusChart) {
            statusChart.destroy();
        }
        
        if (ctx) {
            statusChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Terdeteksi', 'Tidak Terdeteksi'],
                    datasets: [{
                        data: [
                            stats.detection_status.detected,
                            stats.detection_status.not_detected || 0
                        ],
                        backgroundColor: ['#ff4444', '#ddd'],
                        borderColor: '#fff',
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 15,
                                font: { size: 12 }
                            }
                        }
                    }
                }
            });
        }
    } catch (error) {
        console.error('Error initializing status chart:', error);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', initAnalytics);

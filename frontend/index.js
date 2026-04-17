// Location King - восстановленная рабочая версия

// Глобальные переменные
let satelliteMap, guessMap;
let currentSession = null;
let currentRound = null;
let selectedPoint = null;
let score = 0;
let totalRounds = 0;
let correctAnswer = null;

// Базовый URL API - ИСПРАВЛЕНО!
const API_BASE = 'http://localhost:8000/api';

// Инициализация карт
function initMaps() {
    try {
        satelliteMap = new ol.Map({
            target: 'satelliteMap',
            layers: [
                new ol.layer.Tile({
                    source: new ol.source.XYZ({
                        url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
                    })
                })
            ],
            view: new ol.View({
                center: ol.proj.fromLonLat([37.6173, 55.7558]),
                zoom: 10
            })
        });
        
        guessMap = new ol.Map({
            target: 'guessMap',
            layers: [
                new ol.layer.Tile({
                    source: new ol.source.OSM()
                })
            ],
            view: new ol.View({
                center: ol.proj.fromLonLat([37.6173, 55.7558]),
                zoom: 3
            })
        });
        
        guessMap.on('click', function(event) {
            if (!currentSession) {
                addLog('Сначала начните игру!', 'error');
                return;
            }
            
            const coords = ol.proj.toLonLat(event.coordinate);
            selectedPoint = { lat: coords[1], lon: coords[0] };
            addLog(`Точка выбрана: ${selectedPoint.lat.toFixed(4)}, ${selectedPoint.lon.toFixed(4)}`, 'success');
        });
        
        addLog('Карты готовы!', 'success');
    } catch (error) {
        addLog(`Ошибка карт: ${error.message}`, 'error');
    }
}

// Начать игру
async function startGame() {
    try {
        showLoading(true);
        addLog('Начинаем игру...', 'info');
        
        const response = await fetch(`${API_BASE}/mock/sessions/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ rounds_total: 3, view_extent_km: 5, difficulty: 3 })
        });
        
        if (!response.ok) throw new Error(`API: ${response.status}`);
        
        const data = await response.json();
        currentSession = data;
        currentRound = data.current_round;
        totalRounds = data.rounds_total;
        
        score = 0;
        selectedPoint = null;
        correctAnswer = null;
        
        document.getElementById('startBtn').disabled = true;
        document.getElementById('submitBtn').disabled = false;
        document.getElementById('centerBtn').disabled = false;
        
        updateStats();
        addLog(`Игра начата! Раунд 1/${totalRounds}`, 'success');
        
    } catch (error) {
        addLog(`Ошибка: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

// Отправить ответ
async function submitGuess() {
    if (!selectedPoint) {
        addLog('Выберите точку на карте!', 'error');
        return;
    }
    
    try {
        showLoading(true);
        addLog('Отправляю догадку...', 'info');
        
        const response = await fetch(`${API_BASE}/mock/rounds/${currentRound.id}/guess`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lat: selectedPoint.lat, lon: selectedPoint.lon })
        });
        
        if (!response.ok) throw new Error(`API: ${response.status}`);
        
        const result = await response.json();
        correctAnswer = result.target_point;
        score += result.score;
        
        updateStats();
        addLog(`Расстояние: ${(result.distance_meters / 1000).toFixed(1)} км`, 'info');
        addLog(`Очки: ${result.score}`, 'success');
        addLog(`Всего: ${score}`, 'success');
        
        if (result.next_round) {
            currentRound = result.next_round;
            addLog(`Следующий раунд!`, 'info');
            selectedPoint = null;
            correctAnswer = null;
        } else if (result.session_completed) {
            addLog('Игра завершена! 🎉', 'success');
            document.getElementById('submitBtn').disabled = true;
            document.getElementById('centerBtn').disabled = true;
            document.getElementById('startBtn').disabled = false;
        }
        
    } catch (error) {
        addLog(`Ошибка: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

// Центрировать карту
function centerSatelliteMap() {
    if (!correctAnswer) {
        addLog('Нет активного раунда для центрирования', 'error');
        return;
    }
    
    const center = ol.proj.fromLonLat([correctAnswer.lon, correctAnswer.lat]);
    satelliteMap.getView().setCenter(center);
    satelliteMap.getView().setZoom(10);
    addLog('Карта отцентрирована на правильный ответ', 'info');
}

// Переключить карту OSM
function toggleOSMMap() {
    const guessMap = document.getElementById('guessMap');
    const toggleBtn = document.getElementById('toggleMinimapBtn');
    
    if (guessMap.classList.contains('expanded')) {
        guessMap.classList.remove('expanded');
        toggleBtn.innerHTML = '<i class="fas fa-map"></i>';
        toggleBtn.classList.remove('active');
        addLog('Карта OSM свернута', 'info');
    } else {
        guessMap.classList.add('expanded');
        toggleBtn.innerHTML = '<i class="fas fa-compress"></i>';
        toggleBtn.classList.add('active');
        addLog('Карта OSM развернута', 'info');
    }
}

// Вспомогательные функции
function addLog(message, type = 'info') {
    const log = document.getElementById('gameLog');
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    let icon = 'fa-info-circle';
    if (type === 'success') icon = 'fa-check-circle';
    if (type === 'error') icon = 'fa-exclamation-circle';
    entry.innerHTML = `<i class="fas ${icon}"></i> ${message}`;
    log.appendChild(entry);
    log.scrollTop = log.scrollHeight;
}

function updateStats() {
    document.getElementById('scoreValue').textContent = score;
    document.getElementById('roundValue').textContent = currentSession ? 
        `${currentSession.rounds_done}/${totalRounds}` : '0/0';
}

function showLoading(show) {
    document.getElementById('loadingOverlay').style.display = show ? 'flex' : 'none';
}

// Загрузка
document.addEventListener('DOMContentLoaded', function() {
    initMaps();
    updateStats();
    addLog('Добро пожаловать! Нажмите "НАЧАТЬ ИГРУ"', 'info');
});

// Экспорт функций - ВАЖНО!
window.startGame = startGame;
window.submitGuess = submitGuess;
window.centerSatelliteMap = centerSatelliteMap;
window.toggleOSMMap = toggleOSMMap;
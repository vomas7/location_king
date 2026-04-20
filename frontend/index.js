// Location King - восстановленная рабочая версия

// Глобальные переменные
let satelliteMap, guessMap;
let currentSession = null;
let currentRound = null;
let selectedPoint = null;
let score = 0;
let totalRounds = 0;
let correctAnswer = null;

// Базовый URL API - для production
const API_BASE = 'http://api.locationking.ru';

// Инициализация карт
function initMaps() {
    console.log('initMaps: начал выполнение');
    try {
        console.log('initMaps: создаю satelliteMap');
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
        
        console.log('initMaps: satelliteMap создан');
        
        console.log('initMaps: создаю guessMap');
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
        
        console.log('initMaps: guessMap создан');
        console.log('initMaps: успешно завершено');
        
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
    console.log('startGame вызвана');
    
    try {
        console.log('Показываем загрузку...');
        showLoading(true);
        
        console.log('Добавляем лог...');
        addLog('Начинаем игру...', 'info');
        
        console.log('Отправляем запрос к API:', `${API_BASE}/api/mock/sessions/start`);
        const response = await fetch(`${API_BASE}/api/mock/sessions/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                rounds_total: parseInt(document.getElementById('roundsSelect').value) || 3,
                view_extent_km: 5,
                difficulty: parseInt(document.getElementById('difficultySelect').value) || 3
            })
        });
        
        console.log('Ответ API:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`API: ${response.status} - ${errorText}`);
        }
        
        const data = await response.json();
        console.log('Данные API:', data);
        
        currentSession = data;
        currentRound = data.current_round;
        totalRounds = data.rounds_total;
        
        console.log('startGame: currentRound =', currentRound);
        console.log('startGame: totalRounds =', totalRounds);
        
        score = 0;
        selectedPoint = null;
        correctAnswer = null;
        
        console.log('Обновляем UI...');
        document.getElementById('startBtn').disabled = true;
        document.getElementById('submitBtn').disabled = false;
        document.getElementById('centerBtn').disabled = false;
        
        updateStats();
        addLog(`Игра начата! Раунд 1/${totalRounds}`, 'success');
        
        console.log('Игра успешно начата');
        
    } catch (error) {
        console.error('Ошибка в startGame:', error);
        addLog(`Ошибка: ${error.message}`, 'error');
        alert(`Ошибка при запуске игры: ${error.message}`);
    } finally {
        console.log('Скрываем загрузку...');
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
        
        const response = await fetch(`${API_BASE}/api/mock/rounds/${currentRound.id}/guess`, {
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
    console.log(`[${type}] ${message}`);
    
    try {
        const log = document.getElementById('gameLog');
        if (!log) {
            console.error('Элемент gameLog не найден!');
            return;
        }
        
        const entry = document.createElement('div');
        entry.className = `log-entry ${type}`;
        let icon = 'fa-info-circle';
        if (type === 'success') icon = 'fa-check-circle';
        if (type === 'error') icon = 'fa-exclamation-circle';
        entry.innerHTML = `<i class="fas ${icon}"></i> ${message}`;
        log.appendChild(entry);
        log.scrollTop = log.scrollHeight;
    } catch (error) {
        console.error('Ошибка в addLog:', error);
    }
}

function updateStats() {
    document.getElementById('scoreValue').textContent = score;
    document.getElementById('roundValue').textContent = currentSession ? 
        `${currentSession.rounds_done}/${totalRounds}` : '0/0';
}

function showLoading(show) {
    console.log(`showLoading: ${show}`);
    
    try {
        const overlay = document.getElementById('loadingOverlay');
        if (!overlay) {
            console.error('Элемент loadingOverlay не найден!');
            return;
        }
        overlay.style.display = show ? 'flex' : 'none';
    } catch (error) {
        console.error('Ошибка в showLoading:', error);
    }
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

// Глобальная обработка ошибок
window.onerror = function(message, source, lineno, colno, error) {
    console.error('Глобальная ошибка:', message, 'в', source, 'строка', lineno);
    alert('Произошла ошибка: ' + message);
    return true;
};

// Обработка необработанных промисов
window.addEventListener('unhandledrejection', function(event) {
    console.error('Необработанный промис:', event.reason);
    alert('Ошибка промиса: ' + event.reason);
    event.preventDefault();
});
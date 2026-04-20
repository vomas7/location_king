// Location King - восстановленная рабочая версия

// Глобальные переменные
let satelliteMap, guessMap;
let guessVectorSource, centerMarkerSource;
let currentSession = null;
let currentRound = null;
let selectedPoint = null;
let score = 0;
let totalRounds = 0;
let correctAnswer = null;
let completedRounds = 0;

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
        
        // Добавляем слой для маркеров на guessMap
        const guessVectorSource = new ol.source.Vector();
        const guessVectorLayer = new ol.layer.Vector({
            source: guessVectorSource,
            style: new ol.style.Style({
                image: new ol.style.Circle({
                    radius: 6,
                    fill: new ol.style.Fill({ color: '#ff0000' }),
                    stroke: new ol.style.Stroke({ color: '#ffffff', width: 2 })
                })
            })
        });
        guessMap.addLayer(guessVectorLayer);
        
        // Добавляем желтый крест на satelliteMap
        const centerMarkerSource = new ol.source.Vector();
        const centerMarkerLayer = new ol.layer.Vector({
            source: centerMarkerSource,
            style: new ol.style.Style({
                image: new ol.style.RegularShape({
                    points: 4,
                    radius: 10,
                    radius2: 0,
                    angle: 0,
                    fill: new ol.style.Fill({ color: '#ffff00' }),
                    stroke: new ol.style.Stroke({ color: '#000000', width: 2 })
                })
            })
        });
        satelliteMap.addLayer(centerMarkerLayer);
        
        // Добавляем крест в центр
        const centerMarker = new ol.Feature({
            geometry: new ol.geom.Point(ol.proj.fromLonLat([0, 0]))
        });
        centerMarkerSource.addFeature(centerMarker);
        
        console.log('initMaps: успешно завершено');
        
        guessMap.on('click', function(event) {
            if (!currentSession) {
                addLog('Сначала начните игру!', 'error');
                return;
            }
            
            const coords = ol.proj.toLonLat(event.coordinate);
            selectedPoint = { lat: coords[1], lon: coords[0] };
            
            // Очищаем старые маркеры
            guessVectorSource.clear();
            
            // Добавляем новый маркер
            const marker = new ol.Feature({
                geometry: new ol.geom.Point(event.coordinate)
            });
            guessVectorSource.addFeature(marker);
            
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
        completedRounds = 0;
        selectedPoint = null;
        correctAnswer = null;
        
        // Очищаем маркеры
        if (guessVectorSource) guessVectorSource.clear();
        
        // Перемещаем карту к области первого раунда
        if (currentRound && currentRound.target_point) {
            moveSatelliteToRound(currentRound);
        }
        
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
        completedRounds++;
        
        updateStats();
        addLog(`Расстояние: ${(result.distance_meters / 1000).toFixed(1)} км`, 'info');
        addLog(`Очки: ${result.score}`, 'success');
        addLog(`Всего: ${score}`, 'success');
        
        // Показываем маркер правильного ответа
        showAnswerMarker(result.target_point);
        
        if (result.next_round) {
            currentRound = result.next_round;
            selectedPoint = null;
            correctAnswer = null;
            
            // Очищаем маркер догадки
            if (guessVectorSource) guessVectorSource.clear();
            
            // Через 2 секунды перемещаем карту к следующему раунду
            setTimeout(() => {
                moveSatelliteToRound(currentRound);
                addLog(`Раунд ${completedRounds + 1}/${totalRounds} начат!`, 'info');
            }, 2000);
            
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
    if (currentRound) {
        moveSatelliteToRound(currentRound);
        addLog('Карта возвращена к текущей области', 'info');
    } else {
        addLog('Сначала начните игру!', 'error');
    }
}

// Переключить карту OSM
function toggleOSMMap() {
    const guessMapElement = document.getElementById('guessMap');
    const toggleBtn = document.getElementById('toggleMinimapBtn');
    
    if (guessMapElement.classList.contains('expanded')) {
        guessMapElement.classList.remove('expanded');
        toggleBtn.innerHTML = '<i class="fas fa-map"></i>';
        toggleBtn.classList.remove('active');
        addLog('Карта OSM свернута', 'info');
    } else {
        guessMapElement.classList.add('expanded');
        toggleBtn.innerHTML = '<i class="fas fa-compress"></i>';
        toggleBtn.classList.add('active');
        addLog('Карта OSM развернута', 'info');
    }
    
    // Обновляем размер карты OpenLayers после изменения CSS
    setTimeout(() => {
        if (guessMap) {
            guessMap.updateSize();
        }
    }, 100);
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

// Переместить спутниковую карту к области текущего раунда
function moveSatelliteToRound(round) {
    if (!round || !round.target_point) return;
    
    const lat = round.target_point.lat;
    const lon = round.target_point.lon;
    const extentKm = round.view_extent_km || 5;
    
    // Вычисляем квадрат области
    const R = 6371; // радиус Земли в км
    const deltaLat = (extentKm / 2 / R) * (180 / Math.PI);
    const deltaLon = (extentKm / 2 / (R * Math.cos(lat * Math.PI / 180))) * (180 / Math.PI);
    
    const extent = ol.proj.transformExtent(
        [lon - deltaLon, lat - deltaLat, lon + deltaLon, lat + deltaLat],
        'EPSG:4326', 'EPSG:3857'
    );
    
    satelliteMap.getView().fit(extent, { size: satelliteMap.getSize() });
    
    // Обновляем позицию желтого креста
    if (centerMarkerSource) {
        centerMarkerSource.clear();
        const centerFeature = new ol.Feature({
            geometry: new ol.geom.Point(ol.proj.fromLonLat([lon, lat]))
        });
        centerMarkerSource.addFeature(centerFeature);
    }
}

// Показать маркер правильного ответа на карте догадок
function showAnswerMarker(targetPoint) {
    if (!targetPoint || !guessMap) return;
    
    // Создаем отдельный слой для маркера ответа
    if (!window.answerMarkerSource) {
        window.answerMarkerSource = new ol.source.Vector();
        const answerMarkerLayer = new ol.layer.Vector({
            source: window.answerMarkerSource,
            style: new ol.style.Style({
                image: new ol.style.Icon({
                    src: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><path fill="%2300ff00" d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/></svg>',
                    scale: 1.5
                })
            })
        });
        guessMap.addLayer(answerMarkerLayer);
    }
    
    // Очищаем старые маркеры ответов
    window.answerMarkerSource.clear();
    
    // Добавляем новый маркер
    const marker = new ol.Feature({
        geometry: new ol.geom.Point(ol.proj.fromLonLat([targetPoint.lon, targetPoint.lat]))
    });
    window.answerMarkerSource.addFeature(marker);
}

function updateStats() {
    document.getElementById('scoreValue').textContent = score;
    document.getElementById('roundValue').textContent = 
        currentSession ? `${completedRounds}/${totalRounds}` : '0/0';
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
    return false; // не подавлять дефолтное поведение
};

// Обработка необработанных промисов
window.addEventListener('unhandledrejection', function(event) {
    console.error('Необработанный промис:', event.reason);
    // не показываем alert
});
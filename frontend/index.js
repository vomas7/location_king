// Location King - ULTRA SIMPLE FIX
// Без ol.control.defaults, без сложностей!

// Глобальные переменные
let satelliteMap, guessMap;
let currentSession = null;
let currentRound = null;
let selectedPoint = null;
let score = 0;
let totalRounds = 0;
let correctAnswer = null; // Правильный ответ для текущего раунда
let satelliteCenterMarker = null; // Маркер центра спутниковой карты
let guessClickMarker = null; // Маркер клика на карте выбора

// Базовый URL API
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost/api'
    : 'http://api.locationking.ru/api';

// ============================================================================
// ПРОСТАЯ ИНИЦИАЛИЗАЦИЯ КАРТ
// ============================================================================
function initMaps() {
    console.log('Initializing maps...');
    
    try {
        // 1. Спутниковая карта - ПРОСТО БЕЗ КОНТРОЛОВ
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
            // НИКАКИХ controls!
        });
        
        console.log('Satellite map OK');
        
        // 2. Карта для выбора - ПРОСТО БЕЗ КОНТРОЛОВ
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
            // НИКАКИХ controls!
        });
        
        console.log('Guess map OK');
        
        // Клик/тап на карте выбора
        guessMap.on('click', function(event) {
            if (!currentSession) {
                addLog('Сначала начните игру!', 'error');
                return;
            }
            
            const coords = ol.proj.toLonLat(event.coordinate);
            selectedPoint = {
                lat: coords[1],
                lon: coords[0]
            };
            
            // Удаляем предыдущий маркер клика
            if (guessClickMarker) {
                guessMap.removeLayer(guessClickMarker);
            }
            
            // Создаем красный крестик для выбранной точки
            const clickMarker = new ol.Feature({
                geometry: new ol.geom.Point(event.coordinate)
            });
            
            const clickStyle = new ol.style.Style({
                image: new ol.style.Icon({
                    src: 'data:image/svg+xml;utf8,' + encodeURIComponent(
                        '<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">' +
                        '<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 15l-5-5 1.41-1.41L11 14.17l7.59-7.59L20 8l-9 9z" fill="red" stroke="white" stroke-width="1"/>' +
                        '</svg>'
                    ),
                    scale: 1,
                    anchor: [0.5, 0.5]
                })
            });
            
            clickMarker.setStyle(clickStyle);
            
            const vectorSource = new ol.source.Vector({
                features: [clickMarker]
            });
            
            guessClickMarker = new ol.layer.Vector({
                source: vectorSource
            });
            
            guessMap.addLayer(guessClickMarker);
            
            addLog(`Точка выбрана: ${selectedPoint.lat.toFixed(4)}, ${selectedPoint.lon.toFixed(4)}`, 'success');
        });
        
        // Оптимизация для тач-устройств
        if (isMobileDevice()) {
            // Увеличиваем размер тап-областей
            guessMap.getTargetElement().style.cursor = 'pointer';
            
            // Добавляем вибрацию при выборе точки (если поддерживается)
            guessMap.on('click', function() {
                if (navigator.vibrate) {
                    navigator.vibrate(50);
                }
            });
        }
        
        console.log('Maps ready!');
        addLog('Карты готовы!', 'success');
        
    } catch (error) {
        console.error('Map error:', error);
        addLog(`Ошибка карт: ${error.message}`, 'error');
        alert(`OpenLayers ошибка: ${error.message}`);
    }
}

// ============================================================================
// ИГРА
// ============================================================================
async function startGame() {
    try {
        showLoading(true);
        addLog('Начинаем игру...', 'info');
        
        const response = await fetch(`${API_BASE}/mock/sessions/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                rounds_total: 3,
                view_extent_km: 5,
                difficulty: 3
            })
        });
        
        if (!response.ok) {
            const error = await response.text();
            throw new Error(`API: ${response.status} - ${error}`);
        }
        
        const data = await response.json();
        currentSession = data;
        currentRound = data.current_round;
        totalRounds = data.rounds_total;
        
        // Сбрасываем состояние
        selectedPoint = null;
        correctAnswer = null;
        clearMapMarkers();
        
        // UI
        document.getElementById('startBtn').disabled = true;
        document.getElementById('submitBtn').disabled = false;
        document.getElementById('hintBtn').disabled = false;
        
        updateStats();
        
        addLog(`Игра начата!`, 'success');
        addLog(`Раунд 1/${totalRounds}`, 'info');
        
        // Получаем координаты центра снимка из API
        // В реальном API это будет target_point, но в mock API нам нужно получить его
        // Для теста используем случайные координаты, но в реальности будем получать из API
        
        // Загружаем информацию о раунде для получения центра снимка
        try {
            const roundResponse = await fetch(`${API_BASE}/mock/rounds/${currentRound.id}`);
            if (roundResponse.ok) {
                const roundData = await roundResponse.json();
                
                // Центрируем спутниковую карту на реальном центре снимка
                const centerLon = roundData.target_point.lon;
                const centerLat = roundData.target_point.lat;
                
                satelliteMap.getView().setCenter(ol.proj.fromLonLat([centerLon, centerLat]));
                satelliteMap.getView().setZoom(12);
                
                // Добавляем желтый крестик в центр снимка
                addSatelliteCenterMarker(centerLon, centerLat);
                
                addLog(`Центр снимка: ${centerLat.toFixed(4)}, ${centerLon.toFixed(4)}`, 'info');
            } else {
                // Fallback: случайные координаты России
                const randomLon = 37.6173 + (Math.random() - 0.5) * 20;
                const randomLat = 55.7558 + (Math.random() - 0.5) * 10;
                satelliteMap.getView().setCenter(ol.proj.fromLonLat([randomLon, randomLat]));
                satelliteMap.getView().setZoom(12);
                
                // Добавляем желтый крестик
                addSatelliteCenterMarker(randomLon, randomLat);
            }
        } catch (error) {
            console.error('Error loading round data:', error);
            // Fallback: случайные координаты России
            const randomLon = 37.6173 + (Math.random() - 0.5) * 20;
            const randomLat = 55.7558 + (Math.random() - 0.5) * 10;
            satelliteMap.getView().setCenter(ol.proj.fromLonLat([randomLon, randomLat]));
            satelliteMap.getView().setZoom(12);
            
            // Добавляем желтый крестик
            addSatelliteCenterMarker(randomLon, randomLat);
        }
        
        // Устанавливаем ограничения зума и перемещения
        setMapConstraints();
        
    } catch (error) {
        console.error('Start game error:', error);
        addLog(`Ошибка: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

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
            body: JSON.stringify({
                lat: selectedPoint.lat,
                lon: selectedPoint.lon
            })
        });
        
        if (!response.ok) {
            const error = await response.text();
            throw new Error(`API: ${response.status} - ${error}`);
        }
        
        const result = await response.json();
        
        // Сохраняем правильный ответ
        correctAnswer = result.target_point;
        
        // Статистика
        score += result.score;
        updateStats();
        
        // Показываем результат
        addLog(`Расстояние: ${(result.distance_meters / 1000).toFixed(1)} км`, 'info');
        addLog(`Очки: ${result.score}`, 'success');
        addLog(`Всего: ${score}`, 'success');
        
        // Показываем правильный ответ
        addLog(`Правильный ответ: ${correctAnswer.lat.toFixed(4)}, ${correctAnswer.lon.toFixed(4)}`, 'info');
        
        // Отображаем на карте
        showCorrectAnswerOnMap();
        
        if (result.next_round) {
            currentRound = result.next_round;
            addLog(`Следующий раунд!`, 'info');
            selectedPoint = null;
            correctAnswer = null; // Сбрасываем правильный ответ
            clearMapMarkers(); // Очищаем маркеры
            
            // Центрируем спутниковую карту на новом центре снимка
            setTimeout(async () => {
                try {
                    const roundResponse = await fetch(`${API_BASE}/mock/rounds/${currentRound.id}`);
                    if (roundResponse.ok) {
                        const roundData = await roundResponse.json();
                        
                        // Центрируем спутниковую карту на реальном центре снимка
                        const centerLon = roundData.target_point.lon;
                        const centerLat = roundData.target_point.lat;
                        
                        satelliteMap.getView().setCenter(ol.proj.fromLonLat([centerLon, centerLat]));
                        satelliteMap.getView().setZoom(12);
                        
                        // Добавляем желтый крестик в центр снимка
                        addSatelliteCenterMarker(centerLon, centerLat);
                        
                        addLog(`Центр снимка: ${centerLat.toFixed(4)}, ${centerLon.toFixed(4)}`, 'info');
                    }
                } catch (error) {
                    console.error('Error loading next round data:', error);
                }
            }, 500);
        } else if (result.session_completed) {
            addLog('Игра завершена! 🎉', 'success');
            document.getElementById('submitBtn').disabled = true;
            document.getElementById('hintBtn').disabled = true;
            document.getElementById('startBtn').disabled = false;
            
            // Сбрасываем ограничения карты
            resetMapConstraints();
            
            // Очищаем маркеры
            clearMapMarkers();
        }
        
    } catch (error) {
        console.error('Submit error:', error);
        addLog(`Ошибка: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

// ============================================================================
// ВСПОМОГАТЕЛЬНЫЕ
// ============================================================================
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

// Ограничение зума и перемещения карты спутника
function setMapConstraints() {
    const view = satelliteMap.getView();
    
    // Ограничиваем зум
    view.setMinZoom(10);
    view.setMaxZoom(15);
    
    // Ограничиваем область просмотра (примерно границы России)
    const russiaExtent = ol.proj.transformExtent(
        [20, 40, 190, 80],  // minLon, minLat, maxLon, maxLat
        'EPSG:4326',
        'EPSG:3857'
    );
    
    // Устанавливаем экстент
    view.setConstrainResolution(true);
    
    // Добавляем ограничение центра
    const originalCenter = view.getCenter();
    const constrainCenter = function() {
        const center = view.getCenter();
        const constrainedCenter = [
            Math.max(russiaExtent[0], Math.min(russiaExtent[2], center[0])),
            Math.max(russiaExtent[1], Math.min(russiaExtent[3], center[1]))
        ];
        
        if (center[0] !== constrainedCenter[0] || center[1] !== constrainedCenter[1]) {
            view.setCenter(constrainedCenter);
        }
    };
    
    // Сохраняем ссылку на функцию для удаления
    window._constrainCenter = constrainCenter;
    view.on('change:center', constrainCenter);
}

// Сброс ограничений
function resetMapConstraints() {
    const view = satelliteMap.getView();
    view.setMinZoom(1);
    view.setMaxZoom(19);
    
    if (window._constrainCenter) {
        view.un('change:center', window._constrainCenter);
        window._constrainCenter = null;
    }
}

function getHint() {
    addLog('Подсказка: смотрите на реки и дороги.', 'info');
}

// Показать правильный ответ на карте
function showCorrectAnswerOnMap() {
    if (!correctAnswer) return;
    
    // Очищаем предыдущие маркеры
    clearMapMarkers();
    
    // Создаем маркер для правильного ответа (зеленый)
    const correctMarker = new ol.Feature({
        geometry: new ol.geom.Point(
            ol.proj.fromLonLat([correctAnswer.lon, correctAnswer.lat])
        )
    });
    
    const correctStyle = new ol.style.Style({
        image: new ol.style.Circle({
            radius: 8,
            fill: new ol.style.Fill({
                color: 'rgba(0, 255, 0, 0.7)' // Зеленый
            }),
            stroke: new ol.style.Stroke({
                color: 'white',
                width: 2
            })
        }),
        text: new ol.style.Text({
            text: '✓ Правильно',
            offsetY: -15,
            fill: new ol.style.Fill({
                color: 'white'
            }),
            stroke: new ol.style.Stroke({
                color: 'rgba(0, 0, 0, 0.7)',
                width: 3
            }),
            font: 'bold 12px sans-serif'
        })
    });
    
    correctMarker.setStyle(correctStyle);
    
    // Создаем маркер для выбранной точки (синий)
    if (selectedPoint) {
        const guessMarker = new ol.Feature({
            geometry: new ol.geom.Point(
                ol.proj.fromLonLat([selectedPoint.lon, selectedPoint.lat])
            )
        });
        
        const guessStyle = new ol.style.Style({
            image: new ol.style.Circle({
                radius: 6,
                fill: new ol.style.Fill({
                    color: 'rgba(67, 97, 238, 0.7)' // Синий (primary)
                }),
                stroke: new ol.style.Stroke({
                    color: 'white',
                    width: 2
                })
            }),
            text: new ol.style.Text({
                text: 'Ваш выбор',
                offsetY: -15,
                fill: new ol.style.Fill({
                    color: 'white'
                }),
                stroke: new ol.style.Stroke({
                    color: 'rgba(0, 0, 0, 0.7)',
                    width: 3
                }),
                font: 'bold 12px sans-serif'
            })
        });
        
        guessMarker.setStyle(guessStyle);
        
        // Добавляем оба маркера на карту
        const vectorSource = new ol.source.Vector({
            features: [correctMarker, guessMarker]
        });
        
        const vectorLayer = new ol.layer.Vector({
            source: vectorSource
        });
        
        guessMap.addLayer(vectorLayer);
        
        // Сохраняем ссылку на слой для очистки
        window._answerLayer = vectorLayer;
        
        // Центрируем карту на середине между точками
        const centerLon = (correctAnswer.lon + selectedPoint.lon) / 2;
        const centerLat = (correctAnswer.lat + selectedPoint.lat) / 2;
        
        guessMap.getView().setCenter(ol.proj.fromLonLat([centerLon, centerLat]));
        guessMap.getView().setZoom(10);
        
        // Добавляем линию между точками
        const line = new ol.Feature({
            geometry: new ol.geom.LineString([
                ol.proj.fromLonLat([selectedPoint.lon, selectedPoint.lat]),
                ol.proj.fromLonLat([correctAnswer.lon, correctAnswer.lat])
            ])
        });
        
        const lineStyle = new ol.style.Style({
            stroke: new ol.style.Stroke({
                color: 'rgba(255, 0, 0, 0.5)',
                width: 2,
                lineDash: [5, 5]
            })
        });
        
        line.setStyle(lineStyle);
        vectorSource.addFeature(line);
        
    } else {
        // Только правильный ответ
        const vectorSource = new ol.source.Vector({
            features: [correctMarker]
        });
        
        const vectorLayer = new ol.layer.Vector({
            source: vectorSource
        });
        
        guessMap.addLayer(vectorLayer);
        window._answerLayer = vectorLayer;
        
        // Центрируем на правильном ответе
        guessMap.getView().setCenter(ol.proj.fromLonLat([correctAnswer.lon, correctAnswer.lat]));
        guessMap.getView().setZoom(12);
    }
    
    // Показываем кнопку для отображения на спутниковой карте
    const showAnswerBtn = document.getElementById('showAnswerBtn');
    if (showAnswerBtn) {
        showAnswerBtn.style.display = 'flex';
        showAnswerBtn.innerHTML = '<i class="fas fa-eye"></i> Показать ответ';
        showAnswerBtn.classList.remove('active');
    }
}

// Очистить маркеры на карте
function clearMapMarkers() {
    if (window._answerLayer) {
        guessMap.removeLayer(window._answerLayer);
        window._answerLayer = null;
    }
    
    // Очищаем маркер клика
    if (guessClickMarker) {
        guessMap.removeLayer(guessClickMarker);
        guessClickMarker = null;
    }
    
    // Очищаем маркеры на спутниковой карте
    clearSatelliteMarkers();
}

// Очистить маркеры на спутниковой карте
function clearSatelliteMarkers() {
    if (window._satelliteAnswerLayer) {
        satelliteMap.removeLayer(window._satelliteAnswerLayer);
        window._satelliteAnswerLayer = null;
    }
    
    // Удаляем маркер центра
    if (satelliteCenterMarker) {
        satelliteMap.removeLayer(satelliteCenterMarker);
        satelliteCenterMarker = null;
    }
    
    // Скрываем кнопку
    const showAnswerBtn = document.getElementById('showAnswerBtn');
    if (showAnswerBtn) {
        showAnswerBtn.style.display = 'none';
        showAnswerBtn.classList.remove('active');
    }
}

// Добавить желтый крестик в центр спутниковой карты
function addSatelliteCenterMarker(lon, lat) {
    // Удаляем предыдущий маркер центра
    if (satelliteCenterMarker) {
        satelliteMap.removeLayer(satelliteCenterMarker);
    }
    
    // Создаем желтый крестик для центра снимка
    const centerFeature = new ol.Feature({
        geometry: new ol.geom.Point(ol.proj.fromLonLat([lon, lat]))
    });
    
    const centerStyle = new ol.style.Style({
        image: new ol.style.Icon({
            src: 'data:image/svg+xml;utf8,' + encodeURIComponent(
                '<svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">' +
                '<circle cx="16" cy="16" r="14" fill="yellow" stroke="black" stroke-width="2" opacity="0.8"/>' +
                '<path d="M16 8v16M8 16h16" stroke="black" stroke-width="3" stroke-linecap="round"/>' +
                '</svg>'
            ),
            scale: 1,
            anchor: [0.5, 0.5]
        })
    });
    
    centerFeature.setStyle(centerStyle);
    
    const vectorSource = new ol.source.Vector({
        features: [centerFeature]
    });
    
    satelliteCenterMarker = new ol.layer.Vector({
        source: vectorSource
    });
    
    satelliteMap.addLayer(satelliteCenterMarker);
}

// Показать правильный ответ на спутниковой карте
function showAnswerOnSatelliteMap() {
    if (!correctAnswer) return;
    
    const showAnswerBtn = document.getElementById('showAnswerBtn');
    if (!showAnswerBtn) return;
    
    // Переключаем состояние
    const isActive = showAnswerBtn.classList.contains('active');
    
    if (isActive) {
        // Скрываем маркер
        clearSatelliteMarkers();
        showAnswerBtn.innerHTML = '<i class="fas fa-eye"></i> Показать ответ';
        showAnswerBtn.classList.remove('active');
    } else {
        // Показываем маркер
        clearSatelliteMarkers();
        
        // Создаем маркер для правильного ответа на спутниковой карте
        const marker = new ol.Feature({
            geometry: new ol.geom.Point(
                ol.proj.fromLonLat([correctAnswer.lon, correctAnswer.lat])
            )
        });
        
        const markerStyle = new ol.style.Style({
            image: new ol.style.Circle({
                radius: 10,
                fill: new ol.style.Fill({
                    color: 'rgba(0, 255, 0, 0.8)' // Ярко-зеленый
                }),
                stroke: new ol.style.Stroke({
                    color: 'white',
                    width: 3
                })
            })
        });
        
        marker.setStyle(markerStyle);
        
        const vectorSource = new ol.source.Vector({
            features: [marker]
        });
        
        const vectorLayer = new ol.layer.Vector({
            source: vectorSource
        });
        
        satelliteMap.addLayer(vectorLayer);
        window._satelliteAnswerLayer = vectorLayer;
        
        // Обновляем кнопку
        showAnswerBtn.innerHTML = '<i class="fas fa-eye-slash"></i> Скрыть ответ';
        showAnswerBtn.classList.add('active');
        
        // Центрируем на правильном ответе
        satelliteMap.getView().setCenter(ol.proj.fromLonLat([correctAnswer.lon, correctAnswer.lat]));
        satelliteMap.getView().setZoom(14);
    }
}

// ============================================================================
// ФУНКЦИИ ДЛЯ МОБИЛЬНЫХ УСТРОЙСТВ
// ============================================================================
function toggleMinimap() {
    const minimap = document.getElementById('guessMap');
    const toggleBtn = document.getElementById('toggleMinimapBtn');
    
    if (minimap.style.display === 'none') {
        minimap.style.display = 'block';
        toggleBtn.classList.add('active');
        toggleBtn.innerHTML = '<i class="fas fa-map"></i>';
        addLog('Мини-карта показана', 'info');
    } else {
        minimap.style.display = 'none';
        toggleBtn.classList.remove('active');
        toggleBtn.innerHTML = '<i class="fas fa-eye-slash"></i>';
        addLog('Мини-карта скрыта', 'info');
    }
}

// Проверка мобильного устройства
function isMobileDevice() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
}

// ============================================================================
// ЗАГРУЗКА
// ============================================================================
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded');
    initMaps();
    updateStats();
    addLog('Добро пожаловать!', 'info');
    addLog('Нажмите "НАЧАТЬ ИГРУ"', 'info');
    
    // Настройка для мобильных устройств
    if (isMobileDevice()) {
        addLog('Мобильный режим активирован', 'info');
        
        // Добавляем обработчик для кнопки переключения мини-карты
        const toggleBtn = document.getElementById('toggleMinimapBtn');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', toggleMinimap);
            
            // На очень маленьких экранах скрываем мини-карту по умолчанию
            if (window.innerWidth <= 480) {
                setTimeout(() => {
                    toggleMinimap(); // Скрываем мини-карту
                }, 1000);
            }
        }
    }
});

// Глобальные функции
window.startGame = startGame;
window.submitGuess = submitGuess;
window.getHint = getHint;
window.toggleMinimap = toggleMinimap;
window.showAnswerOnSatelliteMap = showAnswerOnSatelliteMap;
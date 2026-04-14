// Location King - Modern Frontend JavaScript

// Глобальные переменные
let satelliteMap, guessMap;
let currentSession = null;
let currentRound = null;
let selectedPoint = null;
let marker = null;
let score = 0;
let totalRounds = 0;
let completedRounds = 0;

// Базовый URL API
const API_BASE = window.location.hostname === 'localhost' 
    ? 'http://localhost/api' 
    : 'https://api.locationking.ru/api';

// Инициализация при загрузке
document.addEventListener('DOMContentLoaded', function() {
    initMaps();
    updateStats();
    addLog('Добро пожаловать в Location King! 🦁', 'info');
    addLog('Нажмите "НАЧАТЬ ИГРУ" чтобы начать', 'info');
});

// Инициализация карт
function initMaps() {
    // Карта со спутниковым снимком (верхняя, большая)
    satelliteMap = new ol.Map({
        target: 'satelliteMap',
        layers: [
            new ol.layer.Tile({
                source: new ol.source.XYZ({
                    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                    attributions: '© Esri, Maxar, Earthstar Geographics, USDA FSA, USGS, Aerogrid, IGN, IGP, and the GIS User Community'
                })
            })
        ],
        view: new ol.View({
            center: ol.proj.fromLonLat([37.6173, 55.7558]), // Москва
            zoom: 10,
            minZoom: 1,
            maxZoom: 19
        }),
        controls: ol.control.defaults({
            zoom: false,
            rotate: false
        })
    });
    
    // Карта для выбора точки (нижняя, маленькая)
    guessMap = new ol.Map({
        target: 'guessMap',
        layers: [
            new ol.layer.Tile({
                source: new ol.source.OSM()
            })
        ],
        view: new ol.View({
            center: ol.proj.fromLonLat([37.6173, 55.7558]), // Москва
            zoom: 3,
            minZoom: 1,
            maxZoom: 19
        })
    });
    
    // Обработчик клика на карте для выбора
    guessMap.on('click', function(event) {
        if (!currentSession) {
            addLog('Сначала начните игру!', 'error');
            return;
        }
        
        const coords = ol.proj.toLonLat(event.coordinate);
        selectedPoint = {
            type: 'Point',
            coordinates: coords
        };
        
        // Удаляем старый маркер
        if (marker) {
            guessMap.removeLayer(marker);
        }
        
        // Добавляем новый маркер
        marker = new ol.layer.Vector({
            source: new ol.source.Vector({
                features: [
                    new ol.Feature({
                        geometry: new ol.geom.Point(event.coordinate)
                    })
                ]
            }),
            style: new ol.style.Style({
                image: new ol.style.Circle({
                    radius: 8,
                    fill: new ol.style.Fill({
                        color: 'rgba(255, 0, 0, 0.7)'
                    }),
                    stroke: new ol.style.Stroke({
                        color: 'white',
                        width: 3
                    })
                })
            })
        });
        
        guessMap.addLayer(marker);
        
        // Включаем кнопку отправки
        document.getElementById('submitBtn').disabled = false;
        
        addLog(`Выбрана точка: ${coords[0].toFixed(4)}, ${coords[1].toFixed(4)}`, 'info');
    });
}

// Начать игру
async function startGame() {
    showLoading(true);
    
    try {
        const roundsTotal = parseInt(document.getElementById('roundsSelect').value);
        const viewExtentKm = parseInt(document.getElementById('extentSelect').value);
        const difficulty = parseInt(document.getElementById('difficultySelect').value);
        
        addLog(`Создаю сессию: ${roundsTotal} раунд(ов), квадрат ${viewExtentKm} км...`, 'info');
        
        const response = await fetch(`${API_BASE}/test/session/start`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                rounds_total: roundsTotal,
                view_extent_km: viewExtentKm
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        currentSession = data;
        currentRound = data.current_round;
        totalRounds = data.rounds_total;
        completedRounds = 0;
        score = 0;
        
        // Обновляем спутниковую карту чтобы показать квадрат
        if (currentRound && currentRound.target_point) {
            const targetCoords = currentRound.target_point.coordinates;
            const center = ol.proj.fromLonLat(targetCoords);
            
            // Устанавливаем центр на спутниковой карте
            satelliteMap.getView().setCenter(center);
            satelliteMap.getView().setZoom(12);
            
            // Добавляем квадрат на карту
            addSquareToMap(targetCoords, viewExtentKm);
            
            addLog(`🎯 Раунд начат! Найдите центр квадрата на карте`, 'success');
            addLog(`Размер квадрата: ${viewExtentKm} км`, 'info');
        }
        
        // Обновляем UI
        document.getElementById('startBtn').disabled = true;
        document.getElementById('startBtn').innerHTML = '<i class="fas fa-play-circle"></i> ИГРА ИДЁТ';
        document.getElementById('submitBtn').disabled = true;
        document.getElementById('hintBtn').disabled = false;
        
        updateStats();
        
        addLog('✅ Сессия создана! Выберите точку на карте справа внизу', 'success');
        
    } catch (error) {
        console.error('Error starting game:', error);
        addLog(`❌ Ошибка при создании сессии: ${error.message}`, 'error');
        
        // Fallback для демо
        if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
            addLog('⚠️ Использую демо-режим (API недоступен)', 'warning');
            startDemoMode();
        }
    } finally {
        showLoading(false);
    }
}

// Добавить квадрат на карту
function addSquareToMap(centerCoords, extentKm) {
    // Удаляем старый квадрат если есть
    const oldLayer = satelliteMap.getLayers().getArray().find(layer => 
        layer.get('name') === 'squareLayer'
    );
    if (oldLayer) {
        satelliteMap.removeLayer(oldLayer);
    }
    
    // Рассчитываем границы квадрата
    const earthRadius = 6371; // км
    const lat = centerCoords[1];
    const lng = centerCoords[0];
    
    // Смещение в градусах
    const deltaLat = (extentKm / 2 / earthRadius) * (180 / Math.PI);
    const deltaLng = (extentKm / 2 / (earthRadius * Math.cos(lat * Math.PI / 180))) * (180 / Math.PI);
    
    const coordinates = [
        [lng - deltaLng, lat - deltaLat],
        [lng + deltaLng, lat - deltaLat],
        [lng + deltaLng, lat + deltaLat],
        [lng - deltaLng, lat + deltaLat],
        [lng - deltaLng, lat - deltaLat]
    ];
    
    const polygon = new ol.geom.Polygon([coordinates.map(coord => ol.proj.fromLonLat(coord))]);
    
    const squareLayer = new ol.layer.Vector({
        source: new ol.source.Vector({
            features: [
                new ol.Feature({
                    geometry: polygon
                })
            ]
        }),
        style: new ol.style.Style({
            stroke: new ol.style.Stroke({
                color: 'rgba(255, 0, 0, 0.8)',
                width: 4
            }),
            fill: new ol.style.Fill({
                color: 'rgba(255, 0, 0, 0.1)'
            })
        })
    });
    
    squareLayer.set('name', 'squareLayer');
    satelliteMap.addLayer(squareLayer);
}

// Отправить ответ
async function submitGuess() {
    if (!selectedPoint || !currentSession || !currentRound) {
        addLog('Сначала выберите точку на карте!', 'error');
        return;
    }
    
    showLoading(true);
    
    try {
        addLog('Отправляю ответ...', 'info');
        
        // В реальном приложении здесь был бы вызов API
        // Для демо просто симулируем ответ
        
        // Рассчитываем расстояние (демо)
        const targetCoords = currentRound.target_point.coordinates;
        const distance = calculateDistance(
            selectedPoint.coordinates[1], selectedPoint.coordinates[0],
            targetCoords[1], targetCoords[0]
        );
        
        // Рассчитываем очки
        const maxScore = 5000;
        const roundScore = Math.max(0, Math.round(maxScore * (1 - distance / 100)));
        
        score += roundScore;
        completedRounds++;
        
        // Обновляем статистику
        document.getElementById('distanceValue').textContent = `${distance.toFixed(1)} км`;
        document.getElementById('accuracyValue').textContent = `${Math.round(100 - distance)}%`;
        
        addLog(`🎯 Расстояние: ${distance.toFixed(1)} км`, 'info');
        addLog(`🏆 Очки за раунд: ${roundScore}`, 'success');
        addLog(`📊 Всего очков: ${score}`, 'info');
        
        // Проверяем завершение игры
        if (completedRounds >= totalRounds) {
            finishGame();
        } else {
            // Начинаем следующий раунд
            setTimeout(() => {
                addLog('🌀 Начинаю следующий раунд...', 'info');
                startNextRound();
            }, 2000);
        }
        
        updateStats();
        
    } catch (error) {
        console.error('Error submitting guess:', error);
        addLog(`❌ Ошибка при отправке ответа: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

// Начать следующий раунд
function startNextRound() {
    // В демо-режиме просто генерируем случайную точку в России
    const randomCoords = [
        20 + Math.random() * 100, // 20-120° в.д.
        40 + Math.random() * 30   // 40-70° с.ш.
    ];
    
    currentRound = {
        target_point: {
            type: 'Point',
            coordinates: randomCoords
        }
    };
    
    const viewExtentKm = parseInt(document.getElementById('extentSelect').value);
    
    // Обновляем спутниковую карту
    const center = ol.proj.fromLonLat(randomCoords);
    satelliteMap.getView().setCenter(center);
    satelliteMap.getView().setZoom(12);
    
    // Добавляем квадрат
    addSquareToMap(randomCoords, viewExtentKm);
    
    // Сбрасываем выбор
    selectedPoint = null;
    if (marker) {
        guessMap.removeLayer(marker);
        marker = null;
    }
    
    document.getElementById('submitBtn').disabled = true;
    
    addLog(`🎯 Раунд ${completedRounds + 1} из ${totalRounds} начат!`, 'success');
}

// Завершить игру
function finishGame() {
    addLog('🎉 ИГРА ЗАВЕРШЕНА!', 'success');
    addLog(`🏆 Итоговый счёт: ${score} очков`, 'success');
    addLog(`🎯 Средняя точность: ${Math.round(score / totalRounds / 50)}%`, 'info');
    
    document.getElementById('startBtn').disabled = false;
    document.getElementById('startBtn').innerHTML = '<i class="fas fa-redo"></i> ИГРАТЬ СНОВА';
    document.getElementById('submitBtn').disabled = true;
    document.getElementById('hintBtn').disabled = true;
    
    // Показываем итоговую статистику
    setTimeout(() => {
        alert(`🎮 Игра завершена!\n\n🏆 Итоговый счёт: ${score}\n🎯 Раундов: ${completedRounds}/${totalRounds}\n🌟 Отличная игра!`);
    }, 1000);
}

// Получить подсказку
function getHint() {
    if (!currentRound) {
        addLog('Сначала начните игру!', 'error');
        return;
    }
    
    // В демо-режиме показываем приблизительное местоположение
    const targetCoords = currentRound.target_point.coordinates;
    const region = getRegionName(targetCoords[1], targetCoords[0]);
    
    addLog(`💡 Подсказка: Ищите в регионе ${region}`, 'info');
    addLog('⚠️ Использование подсказки уменьшит максимальный счёт', 'warning');
}

// Демо-режим
function startDemoMode() {
    addLog('🚀 Запускаю демо-режим...', 'info');
    
    const roundsTotal = 3;
    const viewExtentKm = 3;
    
    currentSession = { id: 'demo-session', rounds_total: roundsTotal };
    totalRounds = roundsTotal;
    completedRounds = 0;
    score = 0;
    
    // Генерируем первую точку
    startNextRound();
    
    document.getElementById('startBtn').disabled = true;
    document.getElementById('startBtn').innerHTML = '<i class="fas fa-play-circle"></i> ИГРА ИДЁТ (ДЕМО)';
    document.getElementById('hintBtn').disabled = false;
    
    updateStats();
    addLog('✅ Демо-режим запущен! Выберите точку на карте', 'success');
}

// Вспомогательные функции
function calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 6371; // Радиус Земли в км
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = 
        Math.sin(dLat/2) * Math.sin(dLat/2) +
        Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
        Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
}

function getRegionName(lat, lng) {
    // Простая логика определения региона по координатам
    if (lng > 100) return 'Восточная Сибирь';
    if (lng > 60) return 'Западная Сибирь';
    if (lng > 40) return 'Центральная Россия';
    if (lng > 30) return 'Украина/Беларусь';
    if (lng > 20) return 'Восточная Европа';
    return 'Западная Европа';
}

function addLog(message, type = 'info') {
    const logContainer = document.getElementById('gameLog');
    const entry = document.createElement('div');
    entry.className = `log-entry fade-in ${type}`;
    
    let icon = 'fas fa-info-circle';
    let color = 'text-primary';
    
    if (type === 'success') {
        icon = 'fas fa-check-circle';
        color = 'text-success';
    } else if (type === 'error') {
        icon = 'fas fa-exclamation-circle';
        color = 'text-danger';
    } else if (type === 'warning') {
        icon = 'fas fa-exclamation-triangle';
        color = 'text-warning';
    }
    
    entry.innerHTML = `<i class="${icon} ${color}"></i> ${message}`;
    logContainer.appendChild(entry);
    logContainer.scrollTop = logContainer.scrollHeight;
}

function updateStats() {
    document.getElementById('scoreValue').textContent = score;
    document.getElementById('roundValue').textContent = `${completedRounds}/${totalRounds}`;
}

function showLoading(show) {
    document.getElementById('loadingOverlay').style.display = show ? 'flex' : 'none';
}

// Экспортируем функции для глобального использования
window.startGame = startGame;
window.submitGuess = submitGuess;
window.getHint = getHint;
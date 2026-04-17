                correctAnswer.lat])
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

// Проверка мобильного устройства
function isMobileDevice() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
}

// Переключение карты OSM
function toggleOSMMap() {
    const guessMap = document.getElementById('guessMap');
    const toggleBtn = document.getElementById('toggleMinimapBtn');
    
    if (guessMap.classList.contains('expanded')) {
        // Сворачиваем карту
        guessMap.classList.remove('expanded');
        toggleBtn.innerHTML = '<i class="fas fa-map"></i>';
        toggleBtn.classList.remove('active');
        addLog('Карта OSM свернута', 'info');
    } else if (guessMap.classList.contains('hidden')) {
        // Показываем карту
        guessMap.classList.remove('hidden');
        toggleBtn.innerHTML = '<i class="fas fa-map"></i>';
        addLog('Карта OSM показана', 'info');
    } else {
        // Разворачиваем карту
        guessMap.classList.add('expanded');
        toggleBtn.innerHTML = '<i class="fas fa-compress"></i>';
        toggleBtn.classList.add('active');
        addLog('Карта OSM развернута', 'info');
    }
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
        
        // На очень маленьких экранах показываем подсказку про карту
        if (window.innerWidth <= 480) {
            setTimeout(() => {
                addLog('Нажмите на значок карты внизу слева для отметки точки', 'info');
            }, 1000);
        }
    }
});

// Глобальные функции
window.startGame = startGame;
window.submitGuess = submitGuess;
window.centerSatelliteMap = centerSatelliteMap;
window.toggleOSMMap = toggleOSMMap;
window.showAnswerOnSatelliteMap = showAnswerOnSatelliteMap;
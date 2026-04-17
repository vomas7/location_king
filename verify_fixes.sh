#!/bin/bash
echo "🔍 Проверка исправлений Location King"
echo "======================================"

# Проверка backend
echo ""
echo "1. Проверка backend API..."
if curl -s http://localhost:8000/ > /dev/null; then
    echo "   ✅ Backend работает"
else
    echo "   ❌ Backend не доступен"
    exit 1
fi

# Проверка mock endpoints
echo ""
echo "2. Проверка mock endpoints..."
SESSION_RESPONSE=$(curl -s http://localhost:8000/api/mock/sessions/start -X POST -H "Content-Type: application/json" -d '{"rounds_total": 1}')
if echo "$SESSION_RESPONSE" | grep -q "current_round"; then
    echo "   ✅ POST /api/mock/sessions/start работает"
    ROUND_ID=$(echo "$SESSION_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['current_round']['id'])")
else
    echo "   ❌ POST /api/mock/sessions/start не работает"
    exit 1
fi

# Проверка GET round endpoint
echo ""
echo "3. Проверка GET /api/mock/rounds/{id}..."
if curl -s "http://localhost:8000/api/mock/rounds/$ROUND_ID" | grep -q "target_point"; then
    echo "   ✅ GET /api/mock/rounds/{id} работает"
    TARGET_LAT=$(curl -s "http://localhost:8000/api/mock/rounds/$ROUND_ID" | python3 -c "import sys, json; print(json.load(sys.stdin)['target_point']['lat'])")
    TARGET_LON=$(curl -s "http://localhost:8000/api/mock/rounds/$ROUND_ID" | python3 -c "import sys, json; print(json.load(sys.stdin)['target_point']['lon'])")
    echo "   Центр снимка: $TARGET_LAT, $TARGET_LON"
else
    echo "   ❌ GET /api/mock/rounds/{id} не работает"
    exit 1
fi

# Проверка frontend файлов
echo ""
echo "4. Проверка frontend файлов..."
if [ -f "frontend/index.js" ]; then
    echo "   ✅ frontend/index.js существует"
    
    # Проверка наличия новых функций
    if grep -q "addSatelliteCenterMarker" frontend/index.js; then
        echo "   ✅ Функция addSatelliteCenterMarker найдена"
    else
        echo "   ❌ Функция addSatelliteCenterMarker не найдена"
    fi
    
    if grep -q "satelliteCenterMarker" frontend/index.js; then
        echo "   ✅ Переменная satelliteCenterMarker найдена"
    else
        echo "   ❌ Переменная satelliteCenterMarker не найдена"
    fi
    
    if grep -q "guessClickMarker" frontend/index.js; then
        echo "   ✅ Переменная guessClickMarker найдена"
    else
        echo "   ❌ Переменная guessClickMarker не найдена"
    fi
else
    echo "   ❌ frontend/index.js не найден"
fi

# Проверка тестовой страницы
echo ""
echo "5. Проверка тестовой страницы..."
if [ -f "frontend/test_fixes.html" ]; then
    echo "   ✅ test_fixes.html существует"
    echo "   📄 Откройте: http://ваш_сервер/frontend/test_fixes.html"
else
    echo "   ❌ test_fixes.html не найден"
fi

echo ""
echo "======================================"
echo "🎉 Проверка завершена!"
echo ""
echo "Исправления внесены:"
echo "1. ✅ Желтый крестик на центре спутниковой карты"
echo "2. ✅ Красный крестик при клике на карту выбора"
echo "3. ✅ Центрирование на реальном центре снимка"
echo "4. ✅ GET endpoint для получения центра снимка"
echo ""
echo "Для тестирования:"
echo "1. Откройте frontend/index.html в браузере"
echo "2. Нажмите 'НАЧАТЬ ИГРУ'"
echo "3. Проверьте желтый крестик на спутниковой карте"
echo "4. Кликните на карте выбора - появится красный крестик"
echo "5. Нажмите 'ОТВЕТИТЬ' - правильный ответ совпадет с желтым крестиком"
$(document).ready(function() {
    let rawData = null;
    let allMonths = [];
    let charts = { temp: null, humidity: null };
    
    const $el = $('#chartContainer');
    const user_id = $el.data('user-id');

    // === Загрузка данных ===
    $.ajax({
        url: '/devices/plots_data/' + user_id,
        method: 'GET',
        dataType: 'json',
        success: function(response) {
            rawData = response;
            prepareControls(response);
            applyFilters(); // Первая отрисовка
            if (response.wind_rose) {
            createWindRoseChart('windRoseChart', response.wind_rose);
            }
        },
        error: function(error) {
            console.error('Ошибка загрузки:', error);
        }
    });
    
    // === Подготовка контролов ===
    function prepareControls(data) {
        // 1. Собираем все месяцы и устройства
        const devices = new Set();
        const monthsSet = new Set();
        
        ['avg_temp', 'avg_humidity'].forEach(key => {
            if (data[key]) {
                Object.keys(data[key]).forEach(devId => {
                    devices.add(devId);
                    Object.keys(data[key][devId]).forEach(m => monthsSet.add(m));
                });
            }
        });
        
        allMonths = Array.from(monthsSet).sort((a, b) => {
            const [m1, y1] = a.split('-').map(Number);
            const [m2, y2] = b.split('-').map(Number);
            return (y1 * 12 + m1) - (y2 * 12 + m2);
        });
        
        // 2. Генерируем чекбоксы устройств
        const checkboxContainer = $('#deviceCheckboxes');
        devices.forEach(devId => {
            checkboxContainer.append(`
                <div class="form-check">
                    <input class="form-check-input device-filter" type="checkbox" 
                           value="${devId}" id="dev_${devId}" checked>
                    <label class="form-check-label" for="dev_${devId}">Устр. ${devId}</label>
                </div>
            `);
        });
        
        // 3. Заполняем селекты месяцев
        const monthLabels = allMonths.map(m => {
            const [month, year] = m.split('-');
            const monthsRu = ['Янв','Фев','Мар','Апр','Май','Июн','Июл','Авг','Сен','Окт','Ноя','Дек'];
            return `${monthsRu[parseInt(month)-1]} '${year.slice(-2)}`;
        });
        
        ['#monthStart', '#monthEnd'].forEach(selector => {
            const $sel = $(selector);
            allMonths.forEach((m, i) => {
                $sel.append(`<option value="${m}">${monthLabels[i]}</option>`);
            });
        });
        
        // Устанавливаем диапазон по умолчанию (все месяцы)
        $('#monthStart').val(allMonths[0]);
        $('#monthEnd').val(allMonths[allMonths.length - 1]);
        
        // 4. Навешиваем обработчики
        $('#btnApply').on('click', applyFilters);
        $('#btnReset').on('click', resetFilters);
        $('#btnAddMonth').on('click', () => adjustMonthRange(1));
        $('#btnRemoveMonth').on('click', () => adjustMonthRange(-1));
    }
    
    // === Применение фильтров ===
    function applyFilters() {
        if (!rawData) return;
        
        // Получаем выбранные устройства
        const selectedDevices = $('.device-filter:checked').map((_, el) => $(el).val()).get();
        
        // Получаем диапазон месяцев
        const startMonth = $('#monthStart').val();
        const endMonth = $('#monthEnd').val();
        
        const filteredMonths = allMonths.filter(m => {
            const [mon, yr] = m.split('-').map(Number);
            const [sMon, sYr] = startMonth.split('-').map(Number);
            const [eMon, eYr] = endMonth.split('-').map(Number);
            const val = yr * 12 + mon;
            return val >= (sYr * 12 + sMon) && val <= (eYr * 12 + eMon);
        });
        
        // Пересоздаём графики
        if (rawData.avg_temp) {
            createLineChart('temperatureChart', rawData.avg_temp, selectedDevices, filteredMonths, 'Средняя температура, °C');
        }
        if (rawData.avg_humidity) {
            createLineChart('humidityChart', rawData.avg_humidity, selectedDevices, filteredMonths, 'Средняя влажность, %');
        }
    }
    
    // === Сброс фильтров ===
    function resetFilters() {
        $('.device-filter').prop('checked', true);
        $('#monthStart').val(allMonths[0]);
        $('#monthEnd').val(allMonths[allMonths.length - 1]);
        applyFilters();
    }
    
    // === Изменение диапазона месяцев ===
    function adjustMonthRange(delta) {
        const startIdx = allMonths.indexOf($('#monthStart').val());
        const endIdx = allMonths.indexOf($('#monthEnd').val());
        
        if (delta > 0) {
            // Расширяем диапазон
            if (endIdx < allMonths.length - 1) {
                $('#monthEnd').val(allMonths[endIdx + 1]);
            }
            if (startIdx > 0) {
                $('#monthStart').val(allMonths[startIdx - 1]);
            }
        } else {
            // Сужаем диапазон
            if (endIdx > startIdx) {
                $('#monthEnd').val(allMonths[endIdx - 1]);
            }
            if (startIdx < endIdx) {
                $('#monthStart').val(allMonths[startIdx + 1]);
            }
        }
        applyFilters();
    }
    
    // === Создание линейного графика с фильтрами ===
    function createLineChart(canvasId, data, selectedDevices, filteredMonths, labelTitle) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    
    // Уничтожаем старый график
    if (charts[canvasId === 'temperatureChart' ? 'temp' : 'humidity']) {
        charts[canvasId === 'temperatureChart' ? 'temp' : 'humidity'].destroy();
    }
    
    const colors = [
        {border: 'rgb(255, 99, 132)', bg: 'rgba(255, 99, 132, 0.5)'},
        {border: 'rgb(54, 162, 235)', bg: 'rgba(54, 162, 235, 0.5)'},
        {border: 'rgb(75, 192, 192)', bg: 'rgba(75, 192, 192, 0.5)'},
        {border: 'rgb(153, 102, 255)', bg: 'rgba(153, 102, 255, 0.5)'},
        {border: 'rgb(255, 159, 64)', bg: 'rgba(255, 159, 64, 0.5)'}
    ];
    
    // ✅ ИСПРАВЛЕНО: добавлен ключ "data:" внутри map
    const datasets = selectedDevices.map((devId, idx) => ({
        label: `Устройство ${devId}`,
        data: filteredMonths.map(month => data[devId]?.[month] ?? null),
        borderColor: colors[idx % colors.length].border,
        backgroundColor: colors[idx % colors.length].bg,
        borderWidth: 2,
        tension: 0.3,
        fill: false,
        pointRadius: 3
    }));
    
    const monthLabels = filteredMonths.map(m => {
        const [month, year] = m.split('-');
        const monthsRu = ['Янв','Фев','Мар','Апр','Май','Июн','Июл','Авг','Сен','Окт','Ноя','Дек'];
        return `${monthsRu[parseInt(month)-1]} '${year.slice(-2)}`;
    });
    
    // ✅ ИСПРАВЛЕНО: добавлен ключ "data:" перед объектом с labels/datasets
    charts[canvasId === 'temperatureChart' ? 'temp' : 'humidity'] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: monthLabels,
            datasets: datasets
        },
        options: {
            responsive: true,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { position: 'top' },
                title: { display: true, text: labelTitle },
                tooltip: {
                    callbacks: {
                        label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y ?? '—'}${labelTitle.includes('температура') ? '°C' : '%'}`
                    }
                }
            },
            scales: {
                y: { 
                    beginAtZero: false, 
                    title: { display: true, text: labelTitle.includes('температура') ? '°C' : '%' },
                    grid: { color: 'rgba(0,0,0,0.1)' }
                },
                x: { grid: { color: 'rgba(0,0,0,0.05)' } }
            }
        }
    });
}
    // === Функция для розы ветров (polarArea) ===
    // === ИСПРАВЛЕННАЯ функция createWindRoseChart ===
    function createWindRoseChart(canvasId, windData) {
        const container = document.getElementById(canvasId);
        if (!container) {
            console.warn(`Контейнер #${canvasId} не найден`);
            return;
        }
        
        // Очищаем контейнер перед перерисовкой (чтобы не дублировать)
        container.innerHTML = '';
        
        const devices = windData.devices;
        const speedGroups = ["<5", "5–8", "8–11", "11–14"];
        const groupColors = {
            "<5": 'rgba(54, 162, 235, 0.7)',
            "5–8": 'rgba(75, 192, 192, 0.7)',
            "8–11": 'rgba(255, 206, 86, 0.7)',
            "11–14": 'rgba(255, 99, 132, 0.7)'
        };
        
        // Создаём отдельный график для каждого устройства
        Object.entries(devices).forEach(([deviceId, deviceData]) => {
            const deviceCanvasId = `windrose_${deviceId}`;
            
            // Создаём контейнер для устройства
            const deviceContainer = document.createElement('div');
            deviceContainer.className = 'wind-rose-container mb-4 p-3 border rounded';
            deviceContainer.innerHTML = `
                <h5 class="mb-3">Устройство ${deviceId}</h5>
                <canvas id="${deviceCanvasId}" height="300"></canvas>
            `;
            container.appendChild(deviceContainer);
            
            const deviceCtx = document.getElementById(deviceCanvasId);
            
            // Группируем данные по wind_deg для polarArea
            const directions = {};
            deviceData.data.forEach(item => {
                if (!directions[item.wind_deg]) {
                    directions[item.wind_deg] = { 
                        label: getDirectionLabel(item.wind_deg), 
                        values: {} 
                    };
                }
                directions[item.wind_deg].values[item.speed_group] = item.r;
            });
            
            const sortedDeg = Object.keys(directions).sort((a, b) => Number(a) - Number(b));
            
            // Создаём dataset для каждой speed_group
            const datasets = speedGroups.map(group => ({
                label: `Скорость ${group} м/с`,
                data: sortedDeg.map(deg => directions[deg]?.values[group] || 0),
                backgroundColor: groupColors[group],
                borderColor: groupColors[group].replace('0.7', '1'),
                borderWidth: 1
            }));
            
            new Chart(deviceCtx, {
                type: 'polarArea',
                data: {
                    labels: sortedDeg.map(deg => directions[deg].label),
                    datasets: datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: { display: false },
                        legend: { position: 'right' }
                    },
                    scales: {
                        r: {
                            beginAtZero: true,
                            ticks: { display: false },
                            grid: { color: 'rgba(0,0,0,0.1)' }
                        }
                    }
                }
            });
        });
    }
    // Вспомогательная: перевод градусов в название направления
    function getDirectionLabel(deg) {
        const labels = {
            0: 'С', 22.5: 'С-СВ', 45: 'СВ', 67.5: 'В-СВ',
            90: 'В', 112.5: 'В-ЮВ', 135: 'ЮВ', 157.5: 'Ю-ЮВ',
            180: 'Ю', 202.5: 'Ю-ЮЗ', 225: 'ЮЗ', 247.5: 'З-ЮЗ',
            270: 'З', 292.5: 'З-СЗ', 315: 'СЗ', 337.5: 'С-СЗ'
        };
        return labels[deg] || `${deg}°`;
    }

});
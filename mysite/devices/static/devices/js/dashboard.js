// $(document).ready(function() {
//     // ID устройства можно передать из Django через контекст
//     // или получить из data-атрибута
//     const user_id = 1;
    
//     // AJAX-запрос к нашему API [citation:4]
//     $.ajax({
//         url: `/devices/plots_data/${user_id}/`,
//         method: 'GET',
//         dataType: 'json',
//         success: function(response) {
//             console.log('Данные получены:', response);
            
//             // Вызываем функцию создания графика
//             //createChart(response);
//         },
//         error: function(xhr, status, error) {
//             console.error('Ошибка загрузки:', error);
//         }
//     });
// });
function myFunction() {
  alert("Hello from a static file!");
}

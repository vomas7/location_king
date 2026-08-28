/*
 * Оформление до первой отрисовки.
 *
 * Отдельный файл, а не строчка в index.html: строгая CSP запрещает
 * встроенные скрипты, а тема должна встать до того, как страница
 * нарисовалась, — иначе светлая начинается с тёмной вспышки.
 *
 * Здесь только чтение: выбор игрока хранится на сервере и приезжает
 * вместе с профилем, а в браузере лежит его копия — чтобы знать тему до
 * ответа сервера.
 */
(function () {
  var stored = null;
  try {
    stored = localStorage.getItem("location-king:theme");
  } catch (error) {
    // Приватный режим: тема будет системной, пока не приедет профиль
  }

  var system = window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  var theme = stored === "dark" || stored === "light" ? stored : system;

  document.documentElement.setAttribute("data-theme", theme);
})();

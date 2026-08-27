# Шрифты

Подмножества переменных шрифтов с Google Fonts: только латиница и кириллица,
формат woff2. Лежат рядом со страницей, потому что игра не делает запросов на
сторонние домены — иначе пришлось бы расширять CSP.

| Семейство      | Роль                  | Файлы                    | Источник                                                         |
| -------------- | --------------------- | ------------------------ | ---------------------------------------------------------------- |
| Unbounded      | заголовки и знак игры | `unbounded-*.woff2`      | [Google Fonts](https://fonts.google.com/specimen/Unbounded)      |
| Onest          | основной текст        | `onest-*.woff2`          | [Google Fonts](https://fonts.google.com/specimen/Onest)          |
| JetBrains Mono | цифры и коды          | `jetbrains-mono-*.woff2` | [Google Fonts](https://fonts.google.com/specimen/JetBrains+Mono) |

Все три — под [SIL Open Font License 1.1](OFL.txt): распространять вместе с
приложением можно, продавать сами файлы нельзя. Правообладатели разные — The
Unbounded Project Authors, Martin Vácha (Onest) и JetBrains s.r.o., — текст
лицензии у всех один.

Обновляются повторной загрузкой подмножеств с `fonts.googleapis.com/css2`;
диапазоны символов в `src/styles/fonts.css` нужно тогда сверить с новыми.

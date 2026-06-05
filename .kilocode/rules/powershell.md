# PowerShell и команды терминала

Среда по умолчанию — Windows PowerShell.

Перед выполнением команд учитывай синтаксис PowerShell. Не используй bash-style escaping, если явно не запущен bash, Git Bash, WSL или другой bash-compatible shell.

## Общие правила

* Не предполагай, что терминал поддерживает bash-синтаксис.
* Для путей используй кавычки, если путь содержит пробелы или спецсимволы.
* Для строковых аргументов в PowerShell предпочитай одинарные кавычки, если не нужна интерполяция.
* Не используй `\"` как способ экранирования кавычек внутри PowerShell-строки.
* Если команда содержит сложный regex, сначала запиши regex в переменную.
* Если regex содержит кириллицу, предпочитай переменную или single-quoted here-string.

## Regex-команды

Для `git grep`, `rg`, `findstr` и похожих команд используй PowerShell-safe quoting.

Правильно:

```powershell
$pattern = '(ПодключитьВнешнююКомпоненту|Новый\([[:space:]]*"AddIn\.|AddIn\.OPI_|OPI_Компоненты|ТипВнешнейКомпоненты|Template\.addin)'
git grep -n -i -E $pattern -- 'BellerageOnline/src'
```

Также допустимо:

```powershell
$pattern = @'
(ПодключитьВнешнююКомпоненту|Новый\([[:space:]]*"AddIn\.|AddIn\.OPI_|OPI_Компоненты|ТипВнешнейКомпоненты|Template\.addin)
'@

git grep -n -i -E $pattern -- 'BellerageOnline/src'
```

Неправильно:

```powershell
git grep -n -i -E "(ПодключитьВнешнююКомпоненту|Новый\([[:space:]]*\"AddIn\.|AddIn\.OPI_|OPI_Компоненты|ТипВнешнейКомпоненты|Template\.addin)" -- "BellerageOnline/src"
```

## Обработка ошибок PowerShell

Если команда упала с ошибкой:

* `ParserError`;
* `UnexpectedToken`;
* `Missing closing`;
* ошибка около `)` или `"`;
* кракозябры в тексте ошибки из-за кодировки;

не повторяй команду без изменений.

Сначала перепиши её с PowerShell-safe quoting:

* одинарные кавычки;
* переменная `$pattern`;
* here-string;
* разбиение сложной команды на несколько простых шагов.

## Кодировка

Если в выводе или ошибках видны кракозябры, можно выполнить:

```powershell
chcp 65001
[Console]::InputEncoding  = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()
```

Не меняй кодировку файлов массово без явного подтверждения пользователя.

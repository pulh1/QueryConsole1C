# Аудит semantic benchmark на реальных запросах

Дата исходного измерения: 2026-08-31.
Дата аудита provenance: 2026-09-02.

## Итог

Ранее опубликованное сравнение baseline/feature аннулировано. Восемь feature
sidecar заявляли source commit
60e610164c01e52198015d9d88ae53c2b9599863, но четыре artifact hash не
соответствовали файлам этого commit и не совпали ни с одним commit объединённой
ветки. По этим файлам нельзя воспроизвести измеренную feature-реализацию,
поэтому прежние проценты и PASS gate больше не считаются доказательством.

Недостоверные feature-sidecar удалены. Baseline-sidecar сохранены как
исторические абсолютные измерения исходного commit
0f0b17d3325216fd8af16f05ced9bc2c17021475; они не образуют сравнительный
эксперимент без согласованного feature-run.

## Причина отбраковки

В каждом из восьми feature-sidecar расходились строки:

| Роль | SHA-256 в sidecar | SHA-256 файла commit 60e6101 |
| --- | --- | --- |
| provider_registry | 86f8b9beddbdfd231382564b5b061f2c054b51f06d047ac9b9d07b3cb360b666 | 7c96a73aa2c4031fb831c636220ee878cfcfacbf9778637ad926307ed81f6b5a |
| standard_provider | 46e2c34714a8c8185959b1c3ccc141da6facdb51198b9dde509c63481f49ba28 | 06eb527bdcd08595ccddfef6f53e50798f2787137a66af9f37b1aae4da5c90cf |
| executable_provider | 194fcae6e5c7e4b7097ada0d6b68fa16098e03c252c2ed12d1087d9624146074 | 4030409355d23adb80006748baf3bfc21fed8017b9dd5eb8f08ebe2552f8879e |
| metadata_contract | 3404b03ffa2b7c3d30a4ed3f99ac3bded31cc22e1f98a250c98c1bd1be46a3e1 | 69e22b8e53d45bef02078251ffd8148ae402b555c4f34c978f7edd104c4f54e3 |

Поиск заявленных SHA-256 по истории commit объединённой ветки не нашёл
соответствующей зафиксированной ревизии.

## Сохранённое baseline evidence

- 2026-08-31-full-semantic-pipeline-lazy-baseline-1.json;
- 2026-08-31-full-semantic-pipeline-lazy-baseline-2.json;
- 2026-08-31-full-semantic-pipeline-lazy-repeat-baseline-1.json;
- 2026-08-31-full-semantic-pipeline-lazy-repeat-baseline-2.json;
- 2026-08-31-full-semantic-pipeline-real-baseline-1.json;
- 2026-08-31-full-semantic-pipeline-real-baseline-2.json;
- 2026-08-31-full-semantic-pipeline-real-repeat-baseline-1.json;
- 2026-08-31-full-semantic-pipeline-real-repeat-baseline-2.json.

Новый корректный absolute feature-run публикуется отдельно в
2026-09-02-metadata-provider-unified-verification.md. Сравнительный old/new
verdict допустим только после нового согласованного baseline-run с теми же
corpora, runtime, methodology и проверяемым provenance.

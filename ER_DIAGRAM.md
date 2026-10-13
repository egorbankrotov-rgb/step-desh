# ER-диаграмма: Россвязь, план нумерации

```mermaid
erDiagram
    REGIONS   ||--o{ NUMBER_RANGES : "содержит"
    OPERATORS ||--o{ NUMBER_RANGES : "владеет"
    EMPLOYEES ||--o{ NUMBER_RANGES : "вносит"

    REGIONS {
        int id PK
        text code UK "код субъекта РФ"
        text name
    }
    OPERATORS {
        int id PK
        text name UK
        text inn
    }
    EMPLOYEES {
        int id PK
        text full_name
        text position
        text username UK "логин"
        text password_hash "хэш личного пароля"
        text salt "своя соль"
        text role "admin / operator"
        int is_active "доступ открыт / закрыт"
    }
    NUMBER_RANGES {
        int id PK
        text def_code "3 цифры"
        text range_from "7 цифр"
        text range_to "7 цифр"
        int operator_id FK
        int region_id FK
        int created_by FK "кто внёс"
    }
```

Связи (все 1:N): регион → диапазоны, оператор → диапазоны, работник → диапазоны (кто внёс).
Таблица `number_ranges` по сути связывает операторов и регионы (M:N).
У каждого работника свой логин и свой пароль (в базе хранится только хэш с индивидуальной солью).

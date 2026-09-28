# Milestone — Backend: Inventario con SQLModel y doble base de datos
## Empresa: Brasaland

## 00. Qué vamos a construir

> Este Milestone **no crea un proyecto nuevo**. Vamos a extender el servicio FastAPI que ya existe dentro de tu monorepo.
>
> La arquitectura queda así:
>
> - **TinyDB** sigue manejando usuarios y autenticación.
> - **Supabase / PostgreSQL** guarda el inventario.
> - **SQLModel** conecta Python con las tablas de Supabase.
> - El stock **no se guarda ni se modifica directamente**: se calcula siempre como `entradas - salidas`.
> - Cada entrada o salida guarda el `user_uuid` del usuario autenticado de TinyDB.
> - Todas las rutas nuevas quedan agrupadas bajo `/inventory`.


Antes de tocar código, leé tu archivo de contexto:

`CONTEXT-brasaland.es.md`

En esta empresa trabajamos con:

| Rol | Entidad |
|---|---|
| Producto de inventario | `Ingredient` |
| Entrada de stock | `IngredientEntry` |
| Salida de stock | `IngredientExit` |
| FK de movimientos | `ingredient_id` |
| Tipo de cantidad | `float` |
| Stock calculado | `float` |

Valores importantes del contexto:

- `category`: `meat`, `produce`, `sauce`, `beverage`, `packaging`, `cleaning`.
- `country`: `CO` o `US`.
- `location_id`: entero entre `1` y `14`.



---

## 01. Abrí tu monorepo existente

Entrá a **GitHub** y abrí el fork que venís usando desde los milestones anteriores.

No crees otro repositorio. Este hito se monta encima de la API existente.

Desde GitHub:

1. Abrí tu repositorio.
2. Tocá **Code**.
3. Entrá en **Codespaces**.
4. Abrí el Codespace que ya venías usando.

La idea es continuar con algo de esta forma:

```text
monorepo/
└── services/
    ├── main.py
    ├── database.py
    ├── ...
    └── data/
```

Tu autenticación con TinyDB debe seguir funcionando antes de continuar.

---

## 02. Entrá a `services/`

Desde la terminal:

```powershell
Set-Location "services"
```

Comprobá que estás parado donde vive tu aplicación FastAPI.

Por ejemplo:

```powershell
Get-ChildItem
```

Deberías reconocer archivos como `main.py`, la configuración de TinyDB y los archivos de autenticación que ya construiste.

---

## 03. Instalá SQLModel y el driver de PostgreSQL

Ejecutá:

```powershell
& "$HOME\.local\bin\uv.exe" add sqlmodel psycopg2-binary
```

Con esto agregamos:

- `sqlmodel`: ORM que vamos a usar.
- `psycopg2-binary`: driver para conectarnos a PostgreSQL/Supabase.

No reemplazamos TinyDB. A partir de ahora la aplicación usa **dos bases de datos**.

---

## 04. Creá o abrí tu proyecto en Supabase

Entrá a **Supabase** y abrí un proyecto existente o creá uno nuevo. Puede estar completamente vacío: las tablas se crearán después desde SQLModel.

Una vez que estés **dentro del dashboard de ese proyecto**, buscá el botón **Connect** en la parte superior.

Después:

1. Abrí **Connect**.
2. Elegí **Direct**.
3. En **Connection Method** seleccioná **Transaction pooler**.
4. En **Type** elegí **URI**.
5. Copiá la cadena PostgreSQL.

Vas a ver algo parecido a:

```text
postgresql://postgres.xxxxx:[YOUR-PASSWORD]@aws-...pooler.supabase.com:6543/postgres
```

Reemplazá **todo** `[YOUR-PASSWORD]` por la contraseña real de tu base, **sin los corchetes**.

Si la contraseña contiene caracteres especiales como `@`, `:`, `/`, `#` o `%`, puede necesitar URL encoding dentro de la URI.

---

## 05. Guardá la conexión en `.env`

Dentro de `services/.env` agregá:

```env
DATABASE_URL=postgresql://postgres.xxxxx:TU_PASSWORD@aws-...pooler.supabase.com:6543/postgres
```

No borres las variables que ya usa TinyDB o tu autenticación.

Verificá también que `.env` esté ignorado por Git:

```gitignore
.env
```

**Nunca subas la contraseña de Supabase al repositorio.** Bastante caos genera ya una base de datos sin regalarle las llaves a internet.

---

## 06. Dejá `database.py` preparado para las dos bases

Tu conexión actual con TinyDB debe seguir existiendo.

**No reemplaces `database.py`.** Conservá todo lo que ya tenés de TinyDB y agregá la conexión de Supabase debajo.

Si tu archivo actual tiene `users_table`, eso se queda. Después agregá el motor de SQLModel y una sesión por request:

```python
import os

from dotenv import load_dotenv
from sqlmodel import Session, create_engine

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no está configurada")

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

def get_db():
    with Session(engine) as session:
        yield session
```

La idea es:

```text
TinyDB
└── usuarios + autenticación

Supabase
└── Ingredient
└── IngredientEntry
└── IngredientExit
```

No crees una sesión SQLModel global. Cada request recibe su propia sesión mediante `Depends(get_db)`.

---

## 07. Creá `models.py`

Dentro de `services/` creá:

```text
models.py
```

Pegá una base como esta:

```python
from datetime import datetime
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class Ingredient(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    sku: str = Field(index=True, unique=True)
    unit: str
    category: str
    country: str

    entries: list["IngredientEntry"] = Relationship(back_populates="product")
    exits: list["IngredientExit"] = Relationship(back_populates="product")


class IngredientEntry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ingredient_id: int = Field(foreign_key="ingredient.id")
    quantity: float
    supplier_name: str
    location_id: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    user_uuid: str

    product: Optional[Ingredient] = Relationship(back_populates="entries")


class IngredientExit(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ingredient_id: int = Field(foreign_key="ingredient.id")
    quantity: float
    reason: str
    location_id: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    user_uuid: str

    product: Optional[Ingredient] = Relationship(back_populates="exits")
```

### Qué hay que entender acá

`ingredient_id` es la **FK real** que relaciona las tablas.

En cambio:

```python
entries = Relationship(...)
exits = Relationship(...)
product = Relationship(...)
```

son accesos ORM para navegar entre objetos sin tener que armar manualmente cada relación.

`current_stock` **no aparece en este modelo** porque no se almacena en la base.

---

## 08. Creá `schemas.py`

Los schemas de request y response van separados de los modelos ORM.

Creá:

```text
schemas.py
```

Base:

```python
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, model_validator


class IngredientCreate(BaseModel):
    name: str
    sku: str
    unit: str
    category: str
    country: str


class IngredientResponse(IngredientCreate):
    id: int
    current_stock: float


class IngredientEntryCreate(BaseModel):
    ingredient_id: int
    quantity: float
    supplier_name: str
    location_id: int


class IngredientExitCreate(BaseModel):
    ingredient_id: int
    quantity: float
    reason: str
    location_id: int

    @model_validator(mode="after")
    def validate_reason(self):
        if self.reason not in {"consumption", "waste"}:
            raise ValueError("reason must be 'consumption' or 'waste'")
        return self


class IngredientEntryResponse(IngredientEntryCreate):
    id: int
    created_at: datetime
    user_uuid: str

    model_config = ConfigDict(from_attributes=True)


class IngredientExitResponse(IngredientExitCreate):
    id: int
    created_at: datetime
    user_uuid: str

    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    id: int
    movement_type: str
    quantity: float
    created_at: datetime
    user_uuid: str
    product: IngredientResponse
```

### Regla específica

`reason` solo puede ser `"consumption"` o `"waste"`. Validalo antes de guardar.

Los schemas sirven para validar lo que entra y controlar exactamente lo que sale de la API.

No devuelvas directamente instancias ORM desde los endpoints. Convertí la instancia a un schema de respuesta (`...Response`) antes de devolverla.

---

## 09. Creá el router de inventario

Dentro de `services/`:

```powershell
New-Item -ItemType Directory -Path "routers" -Force
New-Item -ItemType File -Path "routers\inventory.py" -Force
```

La estructura queda:

```text
services/
├── main.py
├── database.py
├── models.py
├── schemas.py
└── routers/
    └── inventory.py
```

---

## 10. Prepará el router y las dependencias

En `routers/inventory.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, func, select

from database import get_db
from models import Ingredient, IngredientEntry, IngredientExit
from schemas import (
    IngredientCreate,
    IngredientResponse,
    IngredientEntryCreate,
    IngredientEntryResponse,
    IngredientExitCreate,
    IngredientExitResponse,
)

# Ajustá solamente este import a la ubicación REAL de tu auth existente.
from auth import get_current_user

router = APIRouter(prefix="/inventory", tags=["inventory"])
```

No reescribas la autenticación. Usá el mismo `get_current_user` que ya funciona con TinyDB.

Las escrituras requieren autenticación. Los GET pueden quedar públicos salvo que tu implementación previa o consigna general los proteja.

---

## 11. Creá una función para calcular el stock

En el mismo `routers/inventory.py`:

```python
def calculate_stock(
    db: Session,
    ingredient_id: int,

) -> float:

    inbound_statement = (
        select(func.coalesce(func.sum(IngredientEntry.quantity), 0))
        .where(IngredientEntry.ingredient_id == ingredient_id)

    )

    outbound_statement = (
        select(func.coalesce(func.sum(IngredientExit.quantity), 0))
        .where(IngredientExit.ingredient_id == ingredient_id)

    )

    total_in = db.exec(inbound_statement).one()
    total_out = db.exec(outbound_statement).one()

    return total_in - total_out
```

En Brasaland el `current_stock` se calcula por ingrediente según sus movimientos. `location_id` queda registrado en cada movimiento, pero el CONTEXT no exige un stock separado por local para el endpoint general.

El dato importante es este:

```text
current_stock = SUM(entradas) - SUM(salidas)
```

No existe ningún endpoint para hacer algo como:

```json
{
  "current_stock": 500
}
```

El stock cambia únicamente creando movimientos.

---

## 12. Implementá `GET /inventory/products`

Ejemplo:

```python
@router.get("/products", response_model=list[IngredientResponse])
def get_products(db: Session = Depends(get_db)):
    products = db.exec(select(Ingredient)).all()

    response = []

    for product in products:
        current_stock = calculate_stock(
            db,
            product.id,

        )

        response.append(
            IngredientResponse(
                id=product.id,
                name=product.name,
                sku=product.sku,
                unit=product.unit,
                category=product.category,
                country=product.country,
                current_stock=current_stock,
            )
        )

    return response
```

Este endpoint lista los productos y agrega `current_stock` **calculado en ese momento**.

---

## 13. Implementá creación y consulta de productos

```python
@router.post("/products", response_model=IngredientResponse)
def create_product(
    payload: IngredientCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    product = Ingredient(**payload.model_dump())

    db.add(product)
    db.commit()
    db.refresh(product)

    return IngredientResponse(
        id=product.id,
        **payload.model_dump(),
        current_stock=0,
    )
```

Un producto nuevo empieza con stock `0`.

Para buscar uno:

```python
@router.get("/products/{product_id}", response_model=IngredientResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Ingredient, product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    current_stock = calculate_stock(
        db,
        product.id,

    )

    return IngredientResponse(
        id=product.id,
        name=product.name,
        sku=product.sku,
                unit=product.unit,
                category=product.category,
                country=product.country,
        current_stock=current_stock,
    )
```

---

## 14. Implementá la orden de entrada

Ruta obligatoria:

```text
POST /inventory/orders/inbound
```

Ejemplo:

```python
@router.post("/orders/inbound", response_model=IngredientEntryResponse)
def create_inbound_order(
    payload: IngredientEntryCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    product = db.get(Ingredient, payload.ingredient_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    order = IngredientEntry(
        **payload.model_dump(),
        user_uuid=str(current_user.uuid),
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    return IngredientEntryResponse.model_validate(order)
```

La entrada suma stock porque queda registrada en `IngredientEntry`.

El `user_uuid` **no viene del body**: sale del usuario autenticado.

Si en tu objeto de usuario el UUID se accede de otra forma, conservá tu estructura existente. Lo importante es que nunca confíes en un UUID enviado por el cliente.

---

## 15. Implementá la salida y evitá stock negativo

Ruta:

```text
POST /inventory/orders/outbound
```

La validación crítica sucede **antes del `db.add()`**:

```python
@router.post("/orders/outbound", response_model=IngredientExitResponse)
def create_outbound_order(
    payload: IngredientExitCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    product = db.get(Ingredient, payload.ingredient_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    available = calculate_stock(
        db,
        product.id,

    )

    if payload.quantity > available:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock for ingredient '{product.name}'. Available: {available}, requested: {payload.quantity}.",
        )

    order = IngredientExit(
        **payload.model_dump(),
        user_uuid=str(current_user.uuid),
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    return IngredientExitResponse.model_validate(order)
```

Si la salida supera el stock:

```text
HTTP 400
```

y **no se escribe nada**.

---

## 16. Implementá `GET /inventory/orders` sin caer en N+1

Este código va **al final de `routers/inventory.py`**, debajo de los endpoints de entrada y salida.

La idea es traer cada movimiento junto con su producto en el mismo `JOIN`. Así evitamos consultar el producto nuevamente dentro de un loop.

Pegá este endpoint completo:

```python
@router.get("/orders")
def get_orders(
    db: Session = Depends(get_db),
):
    entry_statement = (
        select(IngredientEntry, Ingredient)
        .join(
            Ingredient,
            IngredientEntry.ingredient_id == Ingredient.id,
        )
    )

    exit_statement = (
        select(IngredientExit, Ingredient)
        .join(
            Ingredient,
            IngredientExit.ingredient_id == Ingredient.id,
        )
    )

    entries = db.exec(entry_statement).all()
    exits = db.exec(exit_statement).all()

    movements = []

    for entry, ingredient in entries:
        movements.append({
            "id": entry.id,
            "movement_type": "inbound",
            "quantity": entry.quantity,
            "created_at": entry.created_at,
            "user_uuid": entry.user_uuid,
            "ingredient": {
                "id": ingredient.id,
                "name": ingredient.name,
                "sku": ingredient.sku,
                "unit": ingredient.unit,
                "category": ingredient.category,
                "country": ingredient.country
            },
        })

    for exit_order, ingredient in exits:
        movements.append({
            "id": exit_order.id,
            "movement_type": "outbound",
            "quantity": exit_order.quantity,
            "created_at": exit_order.created_at,
            "user_uuid": exit_order.user_uuid,
            "ingredient": {
                "id": ingredient.id,
                "name": ingredient.name,
                "sku": ingredient.sku,
                "unit": ingredient.unit,
                "category": ingredient.category,
                "country": ingredient.country
            },
        })

    movements.sort(
        key=lambda movement: movement["created_at"]
    )

    return movements
```

¿Por qué hacemos el `JOIN`?

Esto puede generar el problema N+1:

```python
orders = db.exec(select(IngredientEntry)).all()

for order in orders:
    print(order.product.name)
```

Primero consulta las órdenes y después el ORM puede terminar consultando un producto por cada orden.

Con el endpoint anterior hacemos solamente las consultas necesarias:

```text
entradas + producto
salidas + producto
```

y devolvemos todos los movimientos juntos.

## 17. Registrá las tablas y el router en `main.py`

**No reemplaces tu `main.py` completo.** Ya tenés FastAPI y autenticación funcionando.

Agregá estos imports arriba:

```python
from sqlmodel import SQLModel

from database import engine
import models
from routers.inventory import router as inventory_router
```

Después de crear tu `app` y conservar los routers que ya tenías, agregá:

```python
SQLModel.metadata.create_all(engine)

app.include_router(inventory_router)
```

Por ejemplo, si tu aplicación ya tenía autenticación:

```python
from fastapi import FastAPI
from sqlmodel import SQLModel

from auth import router as auth_router
from database import engine
import models
from routers.inventory import router as inventory_router


app = FastAPI(
    title="Company Project API",
    version="1.0.0",
)

app.include_router(auth_router)

SQLModel.metadata.create_all(engine)
app.include_router(inventory_router)
```

Lo importante es conservar lo anterior y **sumar** Inventario. No borres el router de autenticación.

## 18. Cargá los datos semilla de Brasaland

No cargues los registros uno por uno desde Swagger. Vamos a crear un script `seed.py` para cargar todo de una vez.

### 18.1 Creá un usuario una sola vez

Si todavía no tenés un usuario en TinyDB:

1. Levantá la API.
2. Abrí `/docs`.
3. Ejecutá `POST /auth/register`.
4. Copiá el valor de `uuid` que devuelve la respuesta.

Ejemplo:

```json
{
  "uuid": "0db585e4-eac4-45bb-981e-db708e775d22",
  "username": "profe",
  "email": "profe@test.com"
}
```

**No necesitás hacer login ni ejecutar `/auth/me` para el seed.**

El seed solamente necesita guardar un UUID real de TinyDB en las entradas y salidas.

También podés ver los usuarios existentes desde PowerShell:

```powershell
Get-Content "data\users.json"
```

### 18.2 Creá `seed.py`

Dentro de `services/`, creá el archivo:

```powershell
New-Item -ItemType File -Path "seed.py" -Force
```

Abrilo y pegá:

```python
from sqlmodel import Session, SQLModel, select

from database import engine
from models import Ingredient, IngredientEntry, IngredientExit


# 1) Creá primero un usuario desde POST /auth/register.
# 2) Copiá el uuid que devuelve Swagger y pegalo acá.
USER_UUID = "PEGA_ACA_EL_UUID_DE_TINYDB"


def seed():
    SQLModel.metadata.create_all(engine)

    with Session(engine) as db:
        existing = db.exec(select(Ingredient)).first()

        if existing:
            print("Ya hay ingredientes cargados. No se ejecutó el seed.")
            return

        ingredients = [
            Ingredient(
                name="Falda de ternera",
                sku="BRS-BEEF-001",
                unit="kg",
                category="meat",
                country="CO",
            ),
            Ingredient(
                name="Costilla de cerdo",
                sku="BRS-PORK-001",
                unit="kg",
                category="meat",
                country="US",
            ),
            Ingredient(
                name="Chimichurri",
                sku="BRS-SAUCE-001",
                unit="litro",
                category="sauce",
                country="CO",
            ),
            Ingredient(
                name="Salsa BBQ de la casa",
                sku="BRS-SAUCE-002",
                unit="litro",
                category="sauce",
                country="US",
            ),
            Ingredient(
                name="Yuca",
                sku="BRS-PROD-001",
                unit="kg",
                category="produce",
                country="CO",
            ),
            Ingredient(
                name="Caja para llevar (M)",
                sku="BRS-PKG-001",
                unit="unidad",
                category="packaging",
                country="CO",
            ),
        ]

        db.add_all(ingredients)
        db.commit()

        for ingredient in ingredients:
            db.refresh(ingredient)

        by_sku = {ingredient.sku: ingredient for ingredient in ingredients}

        entries = [
            IngredientEntry(
                ingredient_id=by_sku["BRS-BEEF-001"].id,
                quantity=50,
                supplier_name="Carnes del Valle S.A.",
                location_id=1,
                user_uuid=USER_UUID,
            ),
            IngredientEntry(
                ingredient_id=by_sku["BRS-BEEF-001"].id,
                quantity=30,
                supplier_name="Carnes del Valle S.A.",
                location_id=1,
                user_uuid=USER_UUID,
            ),
            IngredientEntry(
                ingredient_id=by_sku["BRS-PORK-001"].id,
                quantity=40,
                supplier_name="MiamiMeat Co.",
                location_id=2,
                user_uuid=USER_UUID,
            ),
            IngredientEntry(
                ingredient_id=by_sku["BRS-SAUCE-001"].id,
                quantity=20,
                supplier_name="Salsas Artesanales Ltda.",
                location_id=3,
                user_uuid=USER_UUID,
            ),
        ]

        db.add_all(entries)
        db.commit()

        exits = [
            IngredientExit(
                ingredient_id=by_sku["BRS-BEEF-001"].id,
                quantity=10,
                reason="consumption",
                location_id=1,
                user_uuid=USER_UUID,
            ),
            IngredientExit(
                ingredient_id=by_sku["BRS-BEEF-001"].id,
                quantity=5,
                reason="waste",
                location_id=1,
                user_uuid=USER_UUID,
            ),
            IngredientExit(
                ingredient_id=by_sku["BRS-PORK-001"].id,
                quantity=8,
                reason="consumption",
                location_id=2,
                user_uuid=USER_UUID,
            ),
        ]

        db.add_all(exits)
        db.commit()

        print("Seed de Brasaland cargado correctamente.")


if __name__ == "__main__":
    seed()
```

### 18.3 Pegá tu UUID

Buscá:

```python
USER_UUID = "PEGA_ACA_EL_UUID_DE_TINYDB"
```

y reemplazalo por el UUID real del usuario que creaste:

```python
USER_UUID = "0db585e4-eac4-45bb-981e-db708e775d22"
```

El script carga de una vez:

- los `6` ingredientes;
- `4` entradas;
- `3` salidas;
- al menos una salida `waste`;
- el mismo `user_uuid` real de TinyDB en los movimientos.

### 18.4 Ejecutá el seed

Parado dentro de `services/`:

```powershell
& "$HOME\.local\bin\uv.exe" run python seed.py
```

Si salió bien vas a ver:

```text
Seed de Brasaland cargado correctamente.
```

El script está preparado para no volver a cargar todo si detecta productos existentes.

> `seed.py` escribe directamente en Supabase mediante SQLModel. No necesita JWT ni pasa por los endpoints de FastAPI. El UUID se guarda solamente para mantener la trazabilidad exigida por el proyecto.

## 19. Levantá la API y probá todo

Desde `services/`:

```powershell
& "$HOME\.local\bin\uv.exe" run uvicorn main:app --reload
```

Abrí:

```text
http://127.0.0.1:8000/docs
```

Como ya cargaste el seed, no hace falta volver a crear todos los registros a mano.

Probá:

1. `GET /inventory/products`
2. `GET /inventory/products/{id}`
3. `GET /inventory/orders`
4. `POST /inventory/products`
5. `POST /inventory/orders/inbound`
6. `POST /inventory/orders/outbound`

Para los `POST` protegidos, iniciá sesión y autorizate con el JWT antes de probarlos.

Después intentá crear una salida con una cantidad mayor al stock disponible.

Debe devolver:

```text
HTTP 400
```

y el stock debe permanecer igual.

## 20. Checklist final

Antes de entregar verificá:

- [ ] Seguís trabajando en el mismo monorepo.
- [ ] TinyDB sigue manejando usuarios y autenticación.
- [ ] Supabase guarda `Ingredient`, `IngredientEntry` y `IngredientExit`.
- [ ] `DATABASE_URL` está en `.env`.
- [ ] `.env` está en `.gitignore`.
- [ ] Usaste SQLModel, no SQLAlchemy directamente.
- [ ] `ingredient_id` es una FK real.
- [ ] `current_stock` no existe como columna editable.
- [ ] El stock se calcula desde entradas y salidas.
- [ ] Las salidas con stock insuficiente devuelven `HTTP 400`.
- [ ] `user_uuid` sale del usuario autenticado de TinyDB.
- [ ] `models.py` y `schemas.py` están separados.
- [ ] La sesión SQLModel entra mediante `Depends(get_db)`.
- [ ] Todas las rutas están bajo `/inventory`.
- [ ] `GET /inventory/orders` evita el problema N+1.
- [ ] Los nombres y campos coinciden exactamente con el CONTEXT de Brasaland.
- [ ] Los datos semilla están cargados.
- [ ] `seed.py` carga los datos de ejemplo de una sola vez.
- [ ] `reason` acepta solamente `consumption` o `waste`.
- [ ] `location_id` está presente en entradas y salidas.
- [ ] `country` está presente en el modelo y schema de `Ingredient`.

---

## Mapa mental final

```text
REQUEST
   │
   ▼
FastAPI
   │
   ├── autenticación ─────────────► TinyDB
   │                                └── User / UUID
   │
   └── /inventory ────────────────► SQLModel
                                    │
                                    ▼
                                 Supabase
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          ▼                         ▼                         ▼
      Ingredient              IngredientEntry                  IngredientExit
          │                         │                         │
          └──────────── current_stock = entradas - salidas ──┘
```

El punto central del milestone es que **el inventario se reconstruye desde el historial de movimientos**. No hay un número mágico de stock que alguien pueda editar y romper silenciosamente.

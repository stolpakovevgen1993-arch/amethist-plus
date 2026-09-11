from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles

from database import engine, Base, get_db
from models import Department, User, Ticket, Order, WorkShift, WarehouseItem, WorkerConfig, Equipment

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(title="Система Головного Інженера", lifespan=lifespan)

# Дозволяємо браузеру спілкуватися з сервером
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- СХЕМИ ДАНИХ ---
class WorkerConfigCreate(BaseModel):
    name: str
    shift_pattern: str

class DepartmentCreate(BaseModel):
    name: str
    is_active: bool = True

class UserCreate(BaseModel):
    full_name: str
    role: str
    department_name: str = "Загальний"
    pin_code: str = "1234"

class TicketCreate(BaseModel):
    department_name: str
    equipment: str
    description: str
    priority: str = "Очікує"
    mechanic_name: str = ""
    status: str = "Нова"
    specialty: str = "Слюсар"

class TicketUpdate(BaseModel):
    status: str | None = None
    priority: str | None = None
    mechanic_name: str | None = None
    used_parts: str | None = None
    specialty: str | None = None

class EquipmentCreate(BaseModel):
    name: str
    location: str

class OrderCreate(BaseModel):
    item_name: str
    order_date: str
    receipt_date: str
    invoice_number: str
    payment_date: str
    bill_number: str
    company: str
    has_document: bool

class ShiftCreate(BaseModel):
    worker_name: str
    year: int
    month: int
    day_of_month: int
    shift_mark: str
    brigadier: int = 0
    overtime: int = 0
    equipment: int = 0

class ItemCreate(BaseModel):
    name: str
    category: str
    quantity: int
    unit: str
    min_quantity: int

class LoginRequest(BaseModel):
    full_name: str
    pin_code: str

class RoleUpdate(BaseModel):
    role: str
    department_name: str


# --- 1. ЦЕХИ ---
@app.post("/departments/")
async def create_department(dept: DepartmentCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Department).where(Department.name == dept.name))
    existing_dept = result.scalars().first()
    if existing_dept:
        return {"status": "error", "message": "Department already exists"}
        
    new_dept = Department(name=dept.name, is_active=dept.is_active)
    db.add(new_dept)
    await db.commit()
    return {"status": "success"}

@app.get("/departments/")
async def get_departments(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Department))
    return result.scalars().all()


# --- 2. ПЕРСОНАЛ ТА АВТОРИЗАЦІЯ ---
@app.post("/users/")
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    # Нові користувачі за замовчуванням потребують затвердження (крім першого Головного інженера, якщо це потрібно)
    result = await db.execute(select(User))
    all_users = result.scalars().all()
    
    is_first_user = len(all_users) == 0
    
    new_user = User(
        full_name=user.full_name, 
        role=user.role, 
        department_name=user.department_name,
        pin_code=user.pin_code,
        is_approved=is_first_user # Перший користувач системи стає затвердженим одразу
    )
    db.add(new_user)
    await db.commit()
    return {"status": "success"}

@app.get("/users/")
async def get_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    return result.scalars().all()

@app.post("/auth/login")
async def login_user(creds: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.full_name == creds.full_name, User.pin_code == creds.pin_code)
    )
    user = result.scalars().first()
    if not user:
        return {"status": "error", "message": "Невірне прізвище або PIN-код"}
    
    # Перевіряємо статус модерації
    if not user.is_approved:
        return {
            "status": "pending", 
            "message": "Ваш акаунт зареєстровано, але ще не затверджено Головним інженером."
        }

    return {
        "status": "success", 
        "role": user.role, 
        "full_name": user.full_name, 
        "department": user.department_name
    }

@app.put("/users/{user_id}/role")
async def update_user_role(user_id: int, data: RoleUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if user:
        user.role = data.role
        user.department_name = data.department_name
        user.is_approved = True # При зміні ролі або збереженні через панель інженера акаунт автоматично затверджується
        await db.commit()
        return {"status": "success"}
    return {"status": "error", "message": "Користувача не знайдено"}


# --- 3. ЗАЯВКИ (ТОіР) ---
@app.post("/tickets/")
async def create_ticket(ticket: TicketCreate, db: AsyncSession = Depends(get_db)):
    new_ticket = Ticket(
        department_name=ticket.department_name,
        equipment=ticket.equipment,
        description=ticket.description,
        status=ticket.status,
        priority=ticket.priority,
        mechanic_name=ticket.mechanic_name,
        specialty=ticket.specialty
    )
    db.add(new_ticket)
    await db.commit()
    return {"status": "success"}

@app.get("/tickets/")
async def get_tickets(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Ticket))
    return result.scalars().all()

@app.put("/tickets/{ticket_id}")
async def update_ticket(ticket_id: int, ticket_data: TicketUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalars().first()
    
    if ticket:
        if ticket_data.status is not None:
            ticket.status = ticket_data.status
        if ticket_data.priority is not None:
            ticket.priority = ticket_data.priority
        if ticket_data.mechanic_name is not None:
            ticket.mechanic_name = ticket_data.mechanic_name
        if ticket_data.used_parts is not None:
            ticket.used_parts = ticket_data.used_parts
        if ticket_data.specialty is not None:
            ticket.specialty = ticket_data.specialty
            
        await db.commit()
        return {"status": "success"}
    return {"status": "error"}


# --- 4. ЗАКУПІВЛІ (КЕРІВНИК) ---
@app.post("/orders/")
async def create_order(order: OrderCreate, db: AsyncSession = Depends(get_db)):
    new_order = Order(
        item_name=order.item_name,
        order_date=order.order_date,
        receipt_date=order.receipt_date,
        invoice_number=order.invoice_number,
        payment_date=order.payment_date,
        bill_number=order.bill_number,
        company=order.company,
        has_document=order.has_document
    )
    db.add(new_order)
    await db.commit()
    return {"status": "success"}

@app.get("/orders/")
async def get_orders(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order))
    return result.scalars().all()

@app.put("/orders/{order_id}")
async def update_order(order_id: int, order_data: OrderCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalars().first()
    
    if order:
        order.item_name = order_data.item_name
        order.order_date = order_data.order_date
        order.receipt_date = order_data.receipt_date
        order.invoice_number = order_data.invoice_number
        order.payment_date = order_data.payment_date
        order.bill_number = order_data.bill_number
        order.company = order_data.company
        order.has_document = order_data.has_document
        
        await db.commit()
        return {"status": "success"}
    return {"status": "error"}


# --- 5. ГРАФІК РОБОТИ ---
@app.post("/shifts/")
async def save_shift(shift: ShiftCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WorkShift).where(
            WorkShift.worker_name == shift.worker_name,
            WorkShift.year == shift.year,
            WorkShift.month == shift.month,
            WorkShift.day_of_month == shift.day_of_month
        )
    )
    existing_shift = result.scalars().first()
    
    if existing_shift:
        existing_shift.shift_mark = shift.shift_mark
        existing_shift.brigadier = shift.brigadier
        existing_shift.overtime = shift.overtime
        existing_shift.equipment = shift.equipment
    else:
        new_shift = WorkShift(
            worker_name=shift.worker_name,
            year=shift.year,
            month=shift.month,
            day_of_month=shift.day_of_month,
            shift_mark=shift.shift_mark,
            brigadier=shift.brigadier,
            overtime=shift.overtime,
            equipment=shift.equipment
        )
        db.add(new_shift)
    await db.commit()
    return {"status": "success"}

@app.get("/shifts/")
async def get_shifts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WorkShift))
    return result.scalars().all()


# --- 6. СКЛАД ЗАПЧАСТИН ---
@app.post("/warehouse/")
async def create_item(item: ItemCreate, db: AsyncSession = Depends(get_db)):
    new_item = WarehouseItem(
        name=item.name,
        category=item.category,
        quantity=item.quantity,
        unit=item.unit,
        min_quantity=item.min_quantity
    )
    db.add(new_item)
    await db.commit()
    return {"status": "success"}

@app.get("/warehouse/")
async def get_items(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WarehouseItem))
    return result.scalars().all()

@app.put("/warehouse/{item_id}")
async def update_item(item_id: int, item_data: ItemCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WarehouseItem).where(WarehouseItem.id == item_id))
    item = result.scalars().first()

    if item:
        item.name = item_data.name
        item.category = item_data.category
        item.quantity = item_data.quantity
        item.unit = item_data.unit
        item.min_quantity = item_data.min_quantity
        await db.commit()
        return {"status": "success"}
    return {"status": "error"}


# --- 7. УПРАВЛІННЯ ПЕРСОНАЛОМ У ТАБЕЛІ ---
@app.post("/workers/")
async def add_worker(worker: WorkerConfigCreate, db: AsyncSession = Depends(get_db)):
    new_worker = WorkerConfig(name=worker.name, shift_pattern=worker.shift_pattern)
    db.add(new_worker)
    await db.commit()
    return {"status": "success"}

@app.get("/workers/")
async def get_workers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WorkerConfig))
    return result.scalars().all()

@app.get("/workers/active")
async def get_active_workers(year: int, month: int, day: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WorkShift).where(
            WorkShift.year == year,
            WorkShift.month == month,
            WorkShift.day_of_month == day,
            WorkShift.shift_mark.notin_(["В", "Л", "Вд", "Відп"])
        )
    )
    shifts = result.scalars().all()
    active_names = list(set([s.worker_name for s in shifts]))
    return [{"name": name} for name in active_names]

@app.delete("/workers/{worker_id}")
async def delete_worker(worker_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WorkerConfig).where(WorkerConfig.id == worker_id))
    worker = result.scalars().first()
    if worker:
        await db.delete(worker)
        await db.commit()
        return {"status": "success"}
    return {"status": "error"}


# --- 8. ОБЛАДНАННЯ ТА QR-КОДИ ---
@app.post("/equipment/")
async def add_equipment(eq: EquipmentCreate, db: AsyncSession = Depends(get_db)):
    new_eq = Equipment(name=eq.name, location=eq.location)
    db.add(new_eq)
    await db.commit()
    return {"status": "success"}

@app.get("/equipment/")
async def get_equipment(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Equipment))
    return result.scalars().all()

# Статика (для роздачі HTML-файлів)
app.mount("/", StaticFiles(directory=".", html=True), name="static")
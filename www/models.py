from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from database import Base

class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    is_active = Column(Boolean, default=True)

class User(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String) # Прибрано зайвий index=True для уникнення дублів індексів
    role = Column(String)                           
    department_name = Column(String, default="Загальний")
    pin_code = Column(String, default="1234")       
    is_approved = Column(Boolean, default=True)

class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True, index=True)
    department_name = Column(String)                
    equipment = Column(String)                      
    description = Column(String)                    
    status = Column(String, default="Нова")
    priority = Column(String, default="Очікує")
    mechanic_name = Column(String, default="")      
    used_parts = Column(String, default="")         
    specialty = Column(String, default="Слюсар")
    created_at = Column(DateTime, default=datetime.now)

class Equipment(Base):
    __tablename__ = "equipments"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    location = Column(String)

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    item_name = Column(String)              
    order_date = Column(String)             
    receipt_date = Column(String)           
    invoice_number = Column(String)         
    payment_date = Column(String)           
    bill_number = Column(String)            
    company = Column(String)                
    has_document = Column(Boolean, default=False)

class WorkShift(Base):
    __tablename__ = "work_shifts"
    id = Column(Integer, primary_key=True, index=True)
    worker_name = Column(String, index=True)
    year = Column(Integer)                     
    month = Column(Integer)                    
    day_of_month = Column(Integer)
    shift_mark = Column(String)
    brigadier = Column(Integer, default=0)
    overtime = Column(Integer, default=0)
    equipment = Column(Integer, default=0)

class WarehouseItem(Base):
    __tablename__ = "warehouse_items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)           
    category = Column(String)                   
    quantity = Column(Integer, default=0)       
    unit = Column(String)                       
    min_quantity = Column(Integer, default=0)   

class WorkerConfig(Base):
    __tablename__ = "worker_configs"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)  
    shift_pattern = Column(String)
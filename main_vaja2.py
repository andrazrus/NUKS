from fastapi import FastAPI, Depends, HTTPException
from fastapi_versioning import VersionedFastAPI, version
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import NoResultFound
from pydantic import BaseModel
from typing import List

from models import Base, Item as ItemModel
from database import engine, SessionLocal
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles



app = FastAPI()



@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Pydantic Schemas
class ItemCreate(BaseModel):
    name: str
    description: str = None

class ItemRead(ItemCreate):
    id: int

    class Config:
        orm_mode = True

# Dependency
async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session

@app.get("/")
@version(1)
def read_root():
    return "Items app"

@app.get("/")
@version(2)
def read_root():
    return "Items app 2"

@app.post("/items/", response_model=ItemRead)
@version(1)
async def create_item(item: ItemCreate, session: AsyncSession = Depends(get_session)):
    db_item = ItemModel(name=item.name, description=item.description)
    session.add(db_item)
    await session.commit()
    await session.refresh(db_item)
    return db_item

@app.get("/items/", response_model=List[ItemRead])
@version(1)
async def read_items(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(ItemModel))
    return result.scalars().all()

@app.get("/items/{item_id}", response_model=ItemRead)
@version(1)
async def read_item(item_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(ItemModel).where(ItemModel.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.put("/items/{item_id}", response_model=ItemRead)
@version(1)
async def update_item(item_id: int, item: ItemCreate, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(ItemModel).where(ItemModel.id == item_id))
    db_item = result.scalar_one_or_none()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    db_item.name = item.name
    db_item.description = item.description
    await session.commit()
    await session.refresh(db_item)
    return db_item

@app.delete("/items/{item_id}")
@version(1)
async def delete_item(item_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(ItemModel).where(ItemModel.id == item_id))
    db_item = result.scalar_one_or_none()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    await session.delete(db_item)
    await session.commit()
    return {"detail": "Item deleted"}


app = VersionedFastAPI(app, version_format='{major}', prefix_format='/v{major}')
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/", StaticFiles(directory=".", html=True), name="static")
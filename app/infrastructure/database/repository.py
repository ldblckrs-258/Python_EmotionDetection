# Abstract base repository and concrete repositories for MongoDB access
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from motor.motor_asyncio import AsyncIOMotorCollection
from app.services.database import get_collection

class Repository(ABC):
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection

    @abstractmethod
    async def get_by_id(self, id: Any) -> Optional[Dict]:
        pass

    @abstractmethod
    async def create(self, data: Dict) -> Any:
        pass

    @abstractmethod
    async def update(self, id: Any, data: Dict) -> bool:
        pass

    @abstractmethod
    async def delete(self, id: Any) -> bool:
        pass

class DetectionRepository(Repository):
    async def get_by_id(self, id: Any) -> Optional[Dict]:
        return await self.collection.find_one({'_id': id})

    async def create(self, data: Dict) -> Any:
        result = await self.collection.insert_one(data)
        return result.inserted_id

    async def update(self, id: Any, data: Dict) -> bool:
        result = await self.collection.update_one({'_id': id}, {'$set': data})
        return result.modified_count > 0

    async def delete(self, id: Any) -> bool:
        result = await self.collection.delete_one({'_id': id})
        return result.deleted_count > 0

class UserRepository(Repository):
    async def get_by_id(self, id: Any) -> Optional[Dict]:
        return await self.collection.find_one({'_id': id})

    async def create(self, data: Dict) -> Any:
        result = await self.collection.insert_one(data)
        return result.inserted_id

    async def update(self, id: Any, data: Dict) -> bool:
        result = await self.collection.update_one({'_id': id}, {'$set': data})
        return result.modified_count > 0

    async def delete(self, id: Any) -> bool:
        result = await self.collection.delete_one({'_id': id})
        return result.deleted_count > 0

class RefreshTokenRepository:
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection

    async def create(self, data: dict):
        await self.collection.insert_one(data)

    async def get_by_token(self, refresh_token: str):
        return await self.collection.find_one({"refresh_token": refresh_token})

    async def delete(self, refresh_token: str):
        await self.collection.delete_one({"refresh_token": refresh_token})

def get_refresh_token_repository():
    collection = get_collection("refresh_tokens")
    return RefreshTokenRepository(collection)

# main.py
import os # New import
from dotenv import load_dotenv # New import
from fastapi import FastAPI, HTTPException, status, Query
from pymongo import MongoClient
from pydantic import BaseModel, Field
from typing import List, Optional
from bson import ObjectId
import re

# Load environment variables from .env file
load_dotenv()

# MongoDB Connection
MONGO_URI = os.getenv("MONGO_URI") # Use the MONGO_URI from the .env file
if not MONGO_URI:
    raise ValueError("No MONGO_URI found in environment variables")
client = MongoClient(MONGO_URI)
db = client["ecommerce"]
products_collection = db["products"]
orders_collection = db["orders"]

app = FastAPI()

# Pydantic Models
class Size(BaseModel):
    size: str
    quantity: int

class Product(BaseModel):
    name: str
    price: float
    sizes: List[Size]

class ProductInDB(Product):
    id: str = Field(..., alias="_id")

class OrderItem(BaseModel):
    productId: str
    qty: int

class Order(BaseModel):
    userId: str
    items: List[OrderItem]

class OrderInDB(Order):
    id: str = Field(..., alias="_id")

# Helper to convert ObjectId to string
def str_object_id(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

# API Endpoints

@app.post("/products", status_code=status.HTTP_201_CREATED)
async def create_product(product: Product):
    """
    Creates a new product.
    """
    product_dict = product.dict()
    result = products_collection.insert_one(product_dict)
    return {"id": str(result.inserted_id)}

@app.get("/products")
async def list_products(
    name: Optional[str] = Query(None),
    size: Optional[str] = Query(None),
    limit: int = Query(10, ge=1),
    offset: int = Query(0, ge=0)
):
    """
    Lists products with optional filters and pagination.
    """
    query = {}
    if name:
        query["name"] = {"$regex": re.escape(name), "$options": "i"}
    if size:
        query["sizes.size"] = size

    products = list(products_collection.find(query, {"sizes": 0}).skip(offset).limit(limit))

    for product in products:
        product['id'] = str(product.pop('_id'))

    return {
        "data": products,
        "page": {
            "next": offset + limit,
            "limit": len(products),
            "previous": max(0, offset - limit)
        }
    }

@app.post("/orders", status_code=status.HTTP_201_CREATED)
async def create_order(order: Order):
    """
    Creates a new order.
    """
    order_dict = order.dict()
    # You might want to add logic to verify product IDs and quantities
    result = orders_collection.insert_one(order_dict)
    return {"id": str(result.inserted_id)}

@app.get("/orders/{user_id}")
async def get_user_orders(
    user_id: str,
    limit: int = Query(10, ge=1),
    offset: int = Query(0, ge=0)
):
    """
    Retrieves a list of orders for a specific user with pagination.
    """
    pipeline = [
        {"$match": {"userId": user_id}},
        {"$unwind": "$items"},
        {
            "$lookup": {
                "from": "products",
                "localField": "items.productId",
                "foreignField": "_id",
                "as": "items.productDetails"
            }
        },
        {"$unwind": "$items.productDetails"},
        {
            "$group": {
                "_id": "$_id",
                "items": {"$push": "$items"},
                "total": {"$sum": {"$multiply": ["$items.qty", "$items.productDetails.price"]}}
            }
        },
        {"$skip": offset},
        {"$limit": limit}
    ]

    orders = list(orders_collection.aggregate(pipeline))

    for order in orders:
        order['id'] = str(order.pop('_id'))
        for item in order['items']:
            item['productDetails']['id'] = str(item['productDetails'].pop('_id'))
            del item['productDetails']['sizes'] # Remove sizes from output

    return {
        "data": orders,
        "page": {
            "next": offset + limit,
            "limit": len(orders),
            "previous": max(0, offset - limit)
        }
    }
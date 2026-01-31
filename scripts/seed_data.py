"""
Database Seed Script
Populates MongoDB with realistic mock data for testing and demonstration
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
import random
from faker import Faker

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import connect_to_mongodb, get_database, close_mongodb_connection
from app.models import UserRole, SwapStatus, BatteryStatus, TransportJobStatus

fake = Faker()


async def seed_users():
    """Seed users: consumers, staff, transporters, admins"""
    print("🌱 Seeding users...")
    db = get_database()
    
    users = []
    
    # 50 Consumers
    for i in range(50):
        users.append({
            "_id": f"consumer_{i+1:03d}",
            "name": fake.name(),
            "email": f"consumer{i+1}@navswap.com",
            "phone": fake.phone_number(),
            "role": UserRole.CONSUMER,
            "created_at": datetime.utcnow() - timedelta(days=random.randint(1, 365)),
            "credits": random.randint(0, 500)
        })
    
    # 30 Station Staff
    for i in range(30):
        users.append({
            "_id": f"staff_{i+1:03d}",
            "name": fake.name(),
            "email": f"staff{i+1}@navswap.com",
            "phone": fake.phone_number(),
            "role": UserRole.STAFF,
            "created_at": datetime.utcnow() - timedelta(days=random.randint(1, 180)),
            "credits": 0
        })
    
    # 15 Transporters
    for i in range(15):
        users.append({
            "_id": f"transporter_{i+1:03d}",
            "name": fake.name(),
            "email": f"transporter{i+1}@navswap.com",
            "phone": fake.phone_number(),
            "role": UserRole.TRANSPORTER,
            "created_at": datetime.utcnow() - timedelta(days=random.randint(1, 180)),
            "credits": random.randint(500, 5000)
        })
    
    # 3 Admins
    for i in range(3):
        users.append({
            "_id": f"admin_{i+1:03d}",
            "name": f"Admin {i+1}",
            "email": f"admin{i+1}@navswap.com",
            "phone": fake.phone_number(),
            "role": UserRole.ADMIN,
            "created_at": datetime.utcnow() - timedelta(days=365),
            "credits": 0
        })
    
    await db.users.insert_many(users)
    print(f"✅ Created {len(users)} users")


async def seed_stations():
    """Seed 20+ stations with varying capacities"""
    print("🌱 Seeding stations...")
    db = get_database()
    
    stations = []
    
    # Major cities coordinates (simplified)
    locations = [
        {"city": "New York", "lat": 40.7128, "lon": -74.0060},
        {"city": "Los Angeles", "lat": 34.0522, "lon": -118.2437},
        {"city": "Chicago", "lat": 41.8781, "lon": -87.6298},
        {"city": "Houston", "lat": 29.7604, "lon": -95.3698},
        {"city": "Phoenix", "lat": 33.4484, "lon": -112.0740},
        {"city": "San Francisco", "lat": 37.7749, "lon": -122.4194},
        {"city": "Seattle", "lat": 47.6062, "lon": -122.3321},
        {"city": "Miami", "lat": 25.7617, "lon": -80.1918},
    ]
    
    for i in range(25):
        loc = random.choice(locations)
        # Add some random offset for multiple stations per city
        lat = loc["lat"] + random.uniform(-0.1, 0.1)
        lon = loc["lon"] + random.uniform(-0.1, 0.1)
        
        capacity = random.choice([15, 20, 25, 30])
        healthy = random.randint(5, capacity - 3)
        charging = random.randint(0, 5)
        faulty = random.randint(0, 2)
        
        stations.append({
            "_id": f"station_{i+1:03d}",
            "name": f"{loc['city']} Station {chr(65+i%10)}",
            "location": {
                "latitude": lat,
                "longitude": lon
            },
            "capacity": capacity,
            "inventory": {
                "total_batteries": healthy + charging + faulty,
                "healthy_batteries": healthy,
                "charging_batteries": charging,
                "faulty_batteries": faulty
            },
            "is_active": True,
            "created_at": datetime.utcnow() - timedelta(days=random.randint(30, 730))
        })
    
    await db.stations.insert_many(stations)
    print(f"✅ Created {len(stations)} stations")
    return stations


async def seed_partner_shops(stations):
    """Seed 10 partner shops"""
    print("🌱 Seeding partner shops...")
    db = get_database()
    
    shops = []
    
    for i in range(10):
        # Place near a random station
        station = random.choice(stations)
        lat = station["location"]["latitude"] + random.uniform(-0.05, 0.05)
        lon = station["location"]["longitude"] + random.uniform(-0.05, 0.05)
        
        shops.append({
            "_id": f"partner_{i+1:03d}",
            "name": f"Partner Shop {fake.company()}",
            "location": {
                "latitude": lat,
                "longitude": lon
            },
            "storage_capacity": random.choice([20, 30, 40, 50]),
            "current_inventory": random.randint(5, 30),
            "created_at": datetime.utcnow() - timedelta(days=random.randint(30, 365))
        })
    
    await db.partner_shops.insert_many(shops)
    print(f"✅ Created {len(shops)} partner shops")
    return shops


async def seed_batteries(stations, shops):
    """Seed batteries across stations and shops"""
    print("🌱 Seeding batteries...")
    db = get_database()
    
    batteries = []
    battery_id = 1
    
    # Batteries at stations
    for station in stations:
        inventory = station["inventory"]
        
        # Healthy batteries
        for _ in range(inventory["healthy_batteries"]):
            batteries.append({
                "_id": f"battery_{battery_id:05d}",
                "battery_id": f"BAT-{battery_id:05d}",
                "status": BatteryStatus.HEALTHY,
                "health_percentage": random.uniform(85, 100),
                "charge_cycles": random.randint(0, 500),
                "current_location": station["_id"],
                "manufactured_date": datetime.utcnow() - timedelta(days=random.randint(30, 730)),
                "last_swap_date": datetime.utcnow() - timedelta(days=random.randint(0, 30)),
                "swap_count": random.randint(0, 200)
            })
            battery_id += 1
        
        # Charging batteries
        for _ in range(inventory["charging_batteries"]):
            batteries.append({
                "_id": f"battery_{battery_id:05d}",
                "battery_id": f"BAT-{battery_id:05d}",
                "status": BatteryStatus.HEALTHY,
                "health_percentage": random.uniform(80, 95),
                "charge_cycles": random.randint(100, 600),
                "current_location": station["_id"],
                "manufactured_date": datetime.utcnow() - timedelta(days=random.randint(30, 730)),
                "last_swap_date": datetime.utcnow() - timedelta(hours=random.randint(1, 24)),
                "swap_count": random.randint(50, 300)
            })
            battery_id += 1
        
        # Faulty batteries
        for _ in range(inventory["faulty_batteries"]):
            batteries.append({
                "_id": f"battery_{battery_id:05d}",
                "battery_id": f"BAT-{battery_id:05d}",
                "status": BatteryStatus.FAULTY,
                "health_percentage": random.uniform(30, 70),
                "charge_cycles": random.randint(500, 1000),
                "current_location": station["_id"],
                "manufactured_date": datetime.utcnow() - timedelta(days=random.randint(365, 1095)),
                "last_swap_date": datetime.utcnow() - timedelta(days=random.randint(1, 10)),
                "swap_count": random.randint(400, 800)
            })
            battery_id += 1
    
    # Batteries at partner shops
    for shop in shops:
        for _ in range(shop["current_inventory"]):
            batteries.append({
                "_id": f"battery_{battery_id:05d}",
                "battery_id": f"BAT-{battery_id:05d}",
                "status": BatteryStatus.HEALTHY,
                "health_percentage": random.uniform(85, 100),
                "charge_cycles": random.randint(0, 400),
                "current_location": shop["_id"],
                "manufactured_date": datetime.utcnow() - timedelta(days=random.randint(30, 365)),
                "last_swap_date": None,
                "swap_count": 0
            })
            battery_id += 1
    
    await db.batteries.insert_many(batteries)
    print(f"✅ Created {len(batteries)} batteries")


async def seed_historical_swaps():
    """Seed historical swap records"""
    print("🌱 Seeding historical swaps...")
    db = get_database()
    
    swaps = []
    
    for i in range(200):
        created_at = datetime.utcnow() - timedelta(days=random.randint(0, 90))
        completed_at = created_at + timedelta(minutes=random.randint(5, 15))
        
        swaps.append({
            "_id": f"swap_{i+1:05d}",
            "user_id": f"consumer_{random.randint(1, 50):03d}",
            "station_id": f"station_{random.randint(1, 25):03d}",
            "status": SwapStatus.COMPLETED,
            "qr_token": None,
            "created_at": created_at,
            "started_at": created_at + timedelta(minutes=random.randint(5, 30)),
            "completed_at": completed_at,
            "old_battery_id": f"BAT-{random.randint(1, 500):05d}",
            "new_battery_id": f"BAT-{random.randint(1, 500):05d}",
            "staff_id": f"staff_{random.randint(1, 30):03d}"
        })
    
    await db.swaps.insert_many(swaps)
    print(f"✅ Created {len(swaps)} historical swaps")


async def seed_transport_jobs():
    """Seed transport job history"""
    print("🌱 Seeding transport jobs...")
    db = get_database()
    
    jobs = []
    
    for i in range(50):
        created_at = datetime.utcnow() - timedelta(days=random.randint(0, 60))
        
        status = random.choice([
            TransportJobStatus.DELIVERED,
            TransportJobStatus.DELIVERED,
            TransportJobStatus.IN_TRANSIT,
            TransportJobStatus.PENDING
        ])
        
        completed_at = None
        if status == TransportJobStatus.DELIVERED:
            completed_at = created_at + timedelta(hours=random.randint(1, 6))
        
        jobs.append({
            "_id": f"transport_{i+1:05d}",
            "from_location": f"station_{random.randint(1, 25):03d}",
            "to_location": f"station_{random.randint(1, 25):03d}",
            "battery_ids": [f"BAT-{random.randint(1, 500):05d}" for _ in range(random.randint(1, 5))],
            "battery_count": random.randint(1, 5),
            "status": status,
            "priority": random.randint(1, 5),
            "assigned_transporter_id": f"transporter_{random.randint(1, 15):03d}" if status != TransportJobStatus.PENDING else None,
            "created_at": created_at,
            "accepted_at": created_at + timedelta(minutes=random.randint(5, 60)) if status != TransportJobStatus.PENDING else None,
            "completed_at": completed_at,
            "credits_earned": random.randint(100, 500) if status == TransportJobStatus.DELIVERED else None
        })
    
    await db.transport_jobs.insert_many(jobs)
    print(f"✅ Created {len(jobs)} transport jobs")


async def seed_tickets():
    """Seed fault tickets"""
    print("🌱 Seeding tickets...")
    db = get_database()
    
    tickets = []
    
    for i in range(30):
        created_at = datetime.utcnow() - timedelta(days=random.randint(0, 30))
        
        status = random.choice(["open", "in_progress", "resolved", "closed"])
        
        tickets.append({
            "_id": f"ticket_{i+1:05d}",
            "ticket_number": f"TKT-{datetime.utcnow().strftime('%Y%m%d')}-{i+1:04d}",
            "status": status,
            "related_entity_type": random.choice(["station", "battery"]),
            "related_entity_id": f"station_{random.randint(1, 25):03d}",
            "fault_level": random.choice(["level_1", "level_2", "level_3"]),
            "title": fake.sentence(),
            "description": fake.paragraph(),
            "priority": random.randint(1, 5),
            "created_at": created_at,
            "assigned_to": f"staff_{random.randint(1, 30):03d}" if status != "open" else None,
            "resolved_at": created_at + timedelta(hours=random.randint(1, 48)) if status in ["resolved", "closed"] else None
        })
    
    await db.tickets.insert_many(tickets)
    print(f"✅ Created {len(tickets)} tickets")


async def seed_gps_logs():
    """Seed GPS movement samples"""
    print("🌱 Seeding GPS logs...")
    db = get_database()
    
    logs = []
    
    # Sample GPS logs for 20 users over last 24 hours
    for user_num in range(1, 21):
        user_id = f"consumer_{user_num:03d}"
        base_lat = 40.7128 + random.uniform(-0.5, 0.5)
        base_lon = -74.0060 + random.uniform(-0.5, 0.5)
        
        # 10 location updates per user
        for j in range(10):
            timestamp = datetime.utcnow() - timedelta(hours=random.randint(0, 24))
            
            logs.append({
                "user_id": user_id,
                "location": {
                    "latitude": base_lat + random.uniform(-0.01, 0.01),
                    "longitude": base_lon + random.uniform(-0.01, 0.01)
                },
                "speed": random.uniform(0, 60),
                "heading": random.uniform(0, 360),
                "timestamp": timestamp
            })
    
    await db.gps_logs.insert_many(logs)
    print(f"✅ Created {len(logs)} GPS logs")


async def main():
    """Main seed function"""
    print("\n🚀 Starting NavSwap Database Seeding...\n")
    
    # Connect to database
    await connect_to_mongodb()
    db = get_database()
    
    # Clear existing data
    print("🧹 Clearing existing data...")
    collections = await db.list_collection_names()
    for collection in collections:
        await db[collection].delete_many({})
    print("✅ Cleared all collections\n")
    
    # Seed in order (respecting dependencies)
    await seed_users()
    stations = await seed_stations()
    shops = await seed_partner_shops(stations)
    await seed_batteries(stations, shops)
    await seed_historical_swaps()
    await seed_transport_jobs()
    await seed_tickets()
    await seed_gps_logs()
    
    # Close connection
    await close_mongodb_connection()
    
    print("\n✅ Database seeding completed successfully!\n")
    print("📊 Summary:")
    print("   - 98 Users (50 consumers, 30 staff, 15 transporters, 3 admins)")
    print("   - 25 Stations")
    print("   - 10 Partner Shops")
    print("   - 500+ Batteries")
    print("   - 200 Historical Swaps")
    print("   - 50 Transport Jobs")
    print("   - 30 Tickets")
    print("   - 200 GPS Logs")
    print("\n🎉 Ready for testing!\n")


if __name__ == "__main__":
    asyncio.run(main())

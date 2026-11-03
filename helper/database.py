import secrets
import motor.motor_asyncio
from datetime import datetime, timedelta, timezone
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError


def _utcnow() -> datetime:
    # Naive UTC, matching what Motor returns for stored dates (needed for TTL + comparisons).
    return datetime.now(timezone.utc).replace(tzinfo=None)


class MongoDB:
    _instances = {}

    def __new__(cls, uri: str, db_name: str):
        if (uri, db_name) not in cls._instances:
            instance = super().__new__(cls)
            instance.client = motor.motor_asyncio.AsyncIOMotorClient(uri)
            instance.db = instance.client[db_name]
            instance.user_data = instance.db["users"]
            instance.channel_data = instance.db["channels"]
            instance.premium_users = instance.db['pros']
            instance.fsub_status = instance.db['fsub_status']  # New collection for fsub status tracking
            instance.request_sub = instance.db['request_sub']  # New collection for join request tracking
            instance.admins_data = instance.db['admins']       # Dedicated collection for admins
            # Credits (only written by the credits-enabled bot)
            instance.credits = instance.db['credits']                # _id = Telegram user ID
            instance.credit_rewards = instance.db['credit_rewards']  # _id = verify token; unique one-time ledger
            instance.verify_tokens = instance.db['verify_tokens']    # one-time shortener verification tokens
            cls._instances[(uri, db_name)] = instance
        return cls._instances[(uri, db_name)]

    async def set_channels(self, channels: list[int]):
        await self.user_data.update_one(
            {"_id": 1},
            {"$set": {"channels": channels}},
            upsert=True
        )

    async def get_channels(self) -> list[int]:
        data = await self.user_data.find_one({"_id": 1})
        return data.get("channels", []) if data else []

    async def add_channel_user(self, channel_id: int, user_id: int):
        await self.channel_data.update_one(
            {"_id": channel_id},
            {"$addToSet": {"users": user_id}},
            upsert=True
        )

    async def remove_channel_user(self, channel_id: int, user_id: int):
        await self.channel_data.update_one(
            {"_id": channel_id},
            {"$pull": {"users": user_id}}
        )

    async def get_channel_users(self, channel_id: int) -> list[int]:
        doc = await self.channel_data.find_one({"_id": channel_id})
        return doc.get("users", []) if doc else []

    async def is_user_in_channel(self, channel_id: int, user_id: int) -> bool:
        doc = await self.channel_data.find_one(
            {"_id": channel_id, "users": {"$in": [user_id]}},
            {"_id": 1}
        )
        return doc is not None

    # ✅ PRO FEATURES

    async def add_pro(self, user_id: int, expiry_date: datetime = None):
        try:
            await self.premium_users.update_one(
                {'_id': user_id},
                {'$set': {'expiry_date': expiry_date}},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Failed to add premium user: {e}")
            return False

    async def remove_pro(self, user_id: int):
        try:
            await self.premium_users.delete_one({'_id': user_id})
            return True
        except Exception as e:
            print(f"Failed to remove premium user: {e}")
            return False

    async def clean_expired_pros(self) -> int:
        """Purge all expired premium users from the database."""
        try:
            now = datetime.now()
            result = await self.premium_users.delete_many({
                'expiry_date': {'$ne': None, '$lte': now}
            })
            return result.deleted_count
        except Exception as e:
            print(f"Failed to clean expired pro users: {e}")
            return 0

    async def is_pro(self, user_id: int):
        doc = await self.premium_users.find_one({'_id': user_id})
        if not doc:
            return False
        if 'expiry_date' not in doc:
            return True  # Legacy premium users without expiry date
        if doc['expiry_date'] is None:
            return True  # Permanent premium users
        if doc['expiry_date'] <= datetime.now():
            # Automatically delete expired premium user from DB
            await self.remove_pro(user_id)
            return False
        return True

    async def get_pros_list(self):
        # Purge expired users from DB first
        await self.clean_expired_pros()
        current_time = datetime.now()
        cursor = self.premium_users.find({
            '$or': [
                {'expiry_date': None},  # Permanent premium users
                {'expiry_date': {'$exists': False}},  # Legacy premium users
                {'expiry_date': {'$gt': current_time}}  # Active premium users
            ]
        })
        return [doc['_id'] async for doc in cursor]
        
    async def get_expiry_date(self, user_id: int) -> datetime:
        doc = await self.premium_users.find_one({'_id': user_id})
        if not doc:
            return None
        expiry = doc.get('expiry_date')
        if expiry and expiry <= datetime.now():
            await self.remove_pro(user_id)
            return None
        return expiry

    # ✅ USER FUNCTIONS

    async def present_user(self, user_id: int) -> bool:
        found = await self.user_data.find_one({'_id': user_id})
        return bool(found)

    async def add_user(self, user_id: int, ban: bool = False):
        await self.user_data.insert_one({'_id': user_id, 'ban': ban})

    async def full_userbase(self) -> list[int]:
        cursor = self.user_data.find()
        return [doc['_id'] async for doc in cursor]

    async def del_user(self, user_id: int):
        await self.user_data.delete_one({'_id': user_id})

    async def ban_user(self, user_id: int):
        await self.user_data.update_one({'_id': user_id}, {'$set': {'ban': True}})

    async def unban_user(self, user_id: int):
        await self.user_data.update_one({'_id': user_id}, {'$set': {'ban': False}})

    async def is_banned(self, user_id: int) -> bool:
        user = await self.user_data.find_one({'_id': user_id})
        return user.get('ban', False) if user else False

    # ✅ FSUB CHANNELS FUNCTIONS

    async def set_fsub_channels(self, fsub_data: dict):
        """Store fsub channels data to database for persistence across bot restarts"""
        await self.user_data.update_one(
            {"_id": "fsub_channels"},
            {"$set": {"channels": fsub_data}},
            upsert=True
        )

    async def get_fsub_channels(self) -> dict:
        """Get fsub channels data from database"""
        data = await self.user_data.find_one({"_id": "fsub_channels"})
        return data.get("channels", {}) if data else {}

    async def add_fsub_channel(self, channel_id: int, channel_data: list):
        """Add a single fsub channel to database"""
        current_data = await self.get_fsub_channels()
        current_data[str(channel_id)] = channel_data
        await self.set_fsub_channels(current_data)

    async def remove_fsub_channel(self, channel_id: int):
        """Remove a single fsub channel from database"""
        current_data = await self.get_fsub_channels()
        current_data.pop(str(channel_id), None)
        await self.set_fsub_channels(current_data)

    # ✅ SHORTNER SETTINGS FUNCTIONS

    async def set_shortner_settings(self, shortner_data: dict):
        """Store shortner settings to database for persistence across bot restarts"""
        await self.user_data.update_one(
            {"_id": "shortner_settings"},
            {"$set": {"settings": shortner_data}},
            upsert=True
        )

    async def get_shortner_settings(self) -> dict:
        """Get shortner settings from database"""
        data = await self.user_data.find_one({"_id": "shortner_settings"})
        return data.get("settings", {}) if data else {}

    async def update_shortner_setting(self, key: str, value: str):
        """Update a single shortner setting"""
        current_data = await self.get_shortner_settings()
        current_data[key] = value
        await self.set_shortner_settings(current_data)

    async def get_shortner_status(self) -> bool:
        """Get shortner on/off status"""
        settings = await self.get_shortner_settings()
        return settings.get('enabled', True)  # Default is enabled

    async def set_shortner_status(self, enabled: bool):
        """Set shortner on/off status"""
        await self.update_shortner_setting('enabled', enabled)

    # ✅ FSUB STATUS COLLECTION FUNCTIONS

    async def update_fsub_status(self, user_id: int, channel_id: int, status: str):
        """Update user's subscription status for a specific channel"""
        await self.fsub_status.update_one(
            {"user_id": user_id, "channel_id": channel_id},
            {"$set": {"status": status, "last_updated": datetime.now()}},
            upsert=True
        )

    async def get_fsub_status(self, user_id: int, channel_id: int) -> str:
        """Get user's subscription status for a specific channel"""
        doc = await self.fsub_status.find_one({"user_id": user_id, "channel_id": channel_id})
        return doc.get("status") if doc else None

    async def remove_fsub_status(self, user_id: int, channel_id: int):
        """Remove user's fsub status record"""
        await self.fsub_status.delete_one({"user_id": user_id, "channel_id": channel_id})

    async def get_user_fsub_statuses(self, user_id: int) -> dict:
        """Get all fsub statuses for a user"""
        cursor = self.fsub_status.find({"user_id": user_id})
        statuses = {}
        async for doc in cursor:
            statuses[doc["channel_id"]] = doc["status"]
        return statuses

    async def clear_expired_fsub_statuses(self, days: int = 7):
        """Clear fsub status records older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        await self.fsub_status.delete_many({"last_updated": {"$lt": cutoff_date}})

    # ✅ REQUEST SUB COLLECTION FUNCTIONS

    async def add_join_request(self, user_id: int, channel_id: int, request_id: int = None):
        """Record a join request submission"""
        await self.request_sub.update_one(
            {"user_id": user_id, "channel_id": channel_id},
            {"$set": {
                "request_id": request_id,
                "status": "pending",
                "submitted_at": datetime.now(),
                "last_updated": datetime.now()
            }},
            upsert=True
        )

    async def update_join_request_status(self, user_id: int, channel_id: int, status: str):
        """Update join request status (pending, approved, rejected)"""
        await self.request_sub.update_one(
            {"user_id": user_id, "channel_id": channel_id},
            {"$set": {"status": status, "last_updated": datetime.now()}}
        )

    async def get_join_request_status(self, user_id: int, channel_id: int) -> str:
        """Get join request status"""
        doc = await self.request_sub.find_one({"user_id": user_id, "channel_id": channel_id})
        return doc.get("status") if doc else None

    async def has_submitted_join_request(self, user_id: int, channel_id: int) -> bool:
        """Check if user has submitted a join request for channel"""
        doc = await self.request_sub.find_one({"user_id": user_id, "channel_id": channel_id})
        return doc is not None

    async def remove_join_request(self, user_id: int, channel_id: int):
        """Remove join request record"""
        await self.request_sub.delete_one({"user_id": user_id, "channel_id": channel_id})

    async def get_pending_requests_for_channel(self, channel_id: int) -> list:
        """Get all pending join requests for a channel"""
        cursor = self.request_sub.find({"channel_id": channel_id, "status": "pending"})
        requests = []
        async for doc in cursor:
            requests.append({
                "user_id": doc["user_id"],
                "request_id": doc.get("request_id"),
                "submitted_at": doc["submitted_at"]
            })
        return requests

    async def clear_old_join_requests(self, days: int = 30):
        """Clear join request records older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        await self.request_sub.delete_many({"submitted_at": {"$lt": cutoff_date}})

    async def cleanup_database(self):
        """Perform comprehensive database maintenance - clean old records and validate data"""
        try:
            # Clean old fsub status records (older than 7 days)
            await self.clear_expired_fsub_statuses(7)
            # Clean old join request records (older than 30 days)
            await self.clear_old_join_requests(30)
            
            # Additional cleanup for orphaned records
            await self.cleanup_orphaned_records()
            
            return True
        except Exception as e:
            print(f"Database cleanup error: {e}")
            return False

    async def cleanup_orphaned_records(self):
        """Clean up records that are no longer valid"""
        try:
            # Remove fsub status records for users who no longer exist
            users = await self.full_userbase()
            user_ids_set = set(users)
            
            # Clean fsub_status collection
            async for doc in self.fsub_status.find({"user_id": {"$nin": users}}):
                await self.fsub_status.delete_one({"_id": doc["_id"]})
            
            # Clean request_sub collection
            async for doc in self.request_sub.find({"user_id": {"$nin": users}}):
                await self.request_sub.delete_one({"_id": doc["_id"]})
                
            return True
        except Exception as e:
            print(f"Error cleaning orphaned records: {e}")
            return False

    async def get_comprehensive_fsub_statistics(self):
        """Get detailed statistics about fsub system"""
        try:
            # Basic counts
            fsub_count = await self.fsub_status.count_documents({})
            request_count = await self.request_sub.count_documents({})
            pending_requests = await self.request_sub.count_documents({"status": "pending"})
            approved_requests = await self.request_sub.count_documents({"status": "approved"})
            rejected_requests = await self.request_sub.count_documents({"status": "rejected"})
            
            # Status breakdown
            status_breakdown = {}
            async for doc in self.fsub_status.aggregate([
                {"$group": {"_id": "$status", "count": {"$sum": 1}}}
            ]):
                status_breakdown[doc["_id"]] = doc["count"]
            
            # Channel-wise statistics
            channel_stats = {}
            async for doc in self.fsub_status.aggregate([
                {"$group": {"_id": "$channel_id", "count": {"$sum": 1}}}
            ]):
                channel_stats[doc["_id"]] = doc["count"]
            
            # Recent activity (last 24 hours)
            from datetime import datetime, timedelta
            yesterday = datetime.now() - timedelta(days=1)
            recent_fsub_updates = await self.fsub_status.count_documents(
                {"last_updated": {"$gte": yesterday}}
            )
            recent_requests = await self.request_sub.count_documents(
                {"submitted_at": {"$gte": yesterday}}
            )
            
            return {
                "total_fsub_records": fsub_count,
                "total_join_requests": request_count,
                "pending_requests": pending_requests,
                "approved_requests": approved_requests,
                "rejected_requests": rejected_requests,
                "status_breakdown": status_breakdown,
                "channel_statistics": channel_stats,
                "recent_activity": {
                    "fsub_updates_24h": recent_fsub_updates,
                    "join_requests_24h": recent_requests
                }
            }
        except Exception as e:
            print(f"Error getting comprehensive fsub statistics: {e}")
            return {}

    async def get_user_activity_summary(self, user_id: int):
        """Get comprehensive activity summary for a specific user"""
        try:
            # Get all fsub statuses
            fsub_statuses = await self.get_user_fsub_statuses(user_id)
            
            # Get join request history
            join_requests = []
            async for doc in self.request_sub.find({"user_id": user_id}):
                join_requests.append({
                    "channel_id": doc["channel_id"],
                    "status": doc["status"],
                    "submitted_at": doc["submitted_at"],
                    "last_updated": doc["last_updated"]
                })
            
            # Check if user is banned
            is_banned = await self.is_banned(user_id)
            
            # Check if user is premium
            is_premium = await self.is_pro(user_id)
            
            return {
                "user_id": user_id,
                "is_banned": is_banned,
                "is_premium": is_premium,
                "fsub_statuses": fsub_statuses,
                "join_request_history": join_requests,
                "total_channels_joined": len([s for s in fsub_statuses.values() if s == "joined"]),
                "total_requests_submitted": len(join_requests)
            }
        except Exception as e:
            print(f"Error getting user activity summary for {user_id}: {e}")
            return {}

    async def get_channel_activity_summary(self, channel_id: int):
        """Get comprehensive activity summary for a specific channel"""
        try:
            # Get all users in channel
            channel_users = await self.get_channel_users(channel_id)
            
            # Get fsub status breakdown for this channel
            status_counts = {}
            async for doc in self.fsub_status.aggregate([
                {"$match": {"channel_id": channel_id}},
                {"$group": {"_id": "$status", "count": {"$sum": 1}}}
            ]):
                status_counts[doc["_id"]] = doc["count"]
            
            # Get join request stats for this channel
            request_stats = {}
            async for doc in self.request_sub.aggregate([
                {"$match": {"channel_id": channel_id}},
                {"$group": {"_id": "$status", "count": {"$sum": 1}}}
            ]):
                request_stats[doc["_id"]] = doc["count"]
            
            # Get recent activity (last 7 days)
            from datetime import datetime, timedelta
            week_ago = datetime.now() - timedelta(days=7)
            recent_joins = await self.fsub_status.count_documents({
                "channel_id": channel_id,
                "status": "joined",
                "last_updated": {"$gte": week_ago}
            })
            
            recent_requests = await self.request_sub.count_documents({
                "channel_id": channel_id,
                "submitted_at": {"$gte": week_ago}
            })
            
            return {
                "channel_id": channel_id,
                "total_users": len(channel_users),
                "status_breakdown": status_counts,
                "request_statistics": request_stats,
                "recent_activity_7d": {
                    "new_joins": recent_joins,
                    "new_requests": recent_requests
                }
            }
        except Exception as e:
            print(f"Error getting channel activity summary for {channel_id}: {e}")
            return {}

    async def bulk_update_user_statuses(self, updates: list):
        """Perform bulk updates for user statuses - useful for synchronization"""
        try:
            operations = []
            for update in updates:
                user_id = update["user_id"]
                channel_id = update["channel_id"]
                status = update["status"]
                
                operations.append({
                    "updateOne": {
                        "filter": {"user_id": user_id, "channel_id": channel_id},
                        "update": {
                            "$set": {
                                "status": status,
                                "last_updated": datetime.now()
                            }
                        },
                        "upsert": True
                    }
                })
            
            if operations:
                result = await self.fsub_status.bulk_write(operations)
                return result
            return None
        except Exception as e:
            print(f"Error in bulk update user statuses: {e}")
            return None

    async def sync_channel_members(self, channel_id: int, current_members: list):
        """Synchronize database with actual channel members"""
        try:
            # Get stored users for this channel
            stored_users = await self.get_channel_users(channel_id)
            
            # Find users to add (in channel but not in database)
            users_to_add = set(current_members) - set(stored_users)
            
            # Find users to remove (in database but not in channel)
            users_to_remove = set(stored_users) - set(current_members)
            
            # Add new users
            for user_id in users_to_add:
                await self.add_channel_user(channel_id, user_id)
                await self.update_fsub_status(user_id, channel_id, "joined")
            
            # Remove old users
            for user_id in users_to_remove:
                await self.remove_channel_user(channel_id, user_id)
                await self.update_fsub_status(user_id, channel_id, "left")
            
            return {
                "added": len(users_to_add),
                "removed": len(users_to_remove),
                "synced": True
            }
        except Exception as e:
            print(f"Error syncing channel members for {channel_id}: {e}")
            return {"synced": False, "error": str(e)}

    async def export_fsub_data(self, channel_id: int = None):
        """Export force subscription data for backup or analysis"""
        try:
            export_data = {
                "export_timestamp": datetime.now().isoformat(),
                "fsub_statuses": [],
                "join_requests": []
            }
            
            # Filter by channel if specified
            filter_query = {"channel_id": channel_id} if channel_id else {}
            
            # Export fsub statuses
            async for doc in self.fsub_status.find(filter_query):
                doc["_id"] = str(doc["_id"])  # Convert ObjectId to string
                if "last_updated" in doc:
                    doc["last_updated"] = doc["last_updated"].isoformat()
                export_data["fsub_statuses"].append(doc)
            
            # Export join requests
            async for doc in self.request_sub.find(filter_query):
                doc["_id"] = str(doc["_id"])  # Convert ObjectId to string
                if "submitted_at" in doc:
                    doc["submitted_at"] = doc["submitted_at"].isoformat()
                if "last_updated" in doc:
                    doc["last_updated"] = doc["last_updated"].isoformat()
                export_data["join_requests"].append(doc)
            
            return export_data
        except Exception as e:
            print(f"Error exporting fsub data: {e}")
            return None

    async def get_fsub_statistics(self):
        """Get statistics about fsub collections"""
        try:
            fsub_count = await self.fsub_status.count_documents({})
            request_count = await self.request_sub.count_documents({})
            pending_requests = await self.request_sub.count_documents({"status": "pending"})
            
            return {
                "fsub_status_records": fsub_count,
                "join_request_records": request_count,
                "pending_requests": pending_requests
            }
        except Exception as e:
            print(f"Error getting fsub statistics: {e}")
            return {}

    # ✅ DB CHANNELS FUNCTIONS

    async def set_db_channels(self, db_channels_data: dict):
        """Store DB channels data to database for persistence across bot restarts"""
        await self.user_data.update_one(
            {"_id": "db_channels"},
            {"$set": {"channels": db_channels_data}},
            upsert=True
        )

    async def get_db_channels(self) -> dict:
        """Get DB channels data from database"""
        data = await self.user_data.find_one({"_id": "db_channels"})
        return data.get("channels", {}) if data else {}

    async def add_db_channel(self, channel_id: int, channel_data: dict):
        """Add a single DB channel to database"""
        current_data = await self.get_db_channels()
        current_data[str(channel_id)] = channel_data
        await self.set_db_channels(current_data)

    async def remove_db_channel(self, channel_id: int):
        """Remove a single DB channel from database"""
        current_data = await self.get_db_channels()
        current_data.pop(str(channel_id), None)
        await self.set_db_channels(current_data)

    async def update_db_channel(self, channel_id: int, channel_data: dict):
        """Update a single DB channel in database"""
        current_data = await self.get_db_channels()
        if str(channel_id) in current_data:
            current_data[str(channel_id)].update(channel_data)
            await self.set_db_channels(current_data)

    async def get_primary_db_channel(self) -> int:
        """Get the primary DB channel ID"""
        db_channels = await self.get_db_channels()
        for channel_id_str, channel_data in db_channels.items():
            if channel_data.get('is_primary', False):
                return int(channel_id_str)
        return None

    async def set_primary_db_channel(self, channel_id: int):
        """Set a DB channel as primary (remove primary from others)"""
        db_channels = await self.get_db_channels()
        # Remove primary status from all channels
        for ch_id, ch_data in db_channels.items():
            ch_data['is_primary'] = False
        # Set new primary channel
        if str(channel_id) in db_channels:
            db_channels[str(channel_id)]['is_primary'] = True
        await self.set_db_channels(db_channels)

    async def get_active_db_channels(self) -> dict:
        """Get all active DB channels"""
        db_channels = await self.get_db_channels()
        active_channels = {}
        for channel_id_str, channel_data in db_channels.items():
            if channel_data.get('is_active', True):
                active_channels[channel_id_str] = channel_data
        return active_channels

    async def toggle_db_channel_status(self, channel_id: int):
        """Toggle DB channel active/inactive status"""
        db_channels = await self.get_db_channels()
        if str(channel_id) in db_channels:
            current_status = db_channels[str(channel_id)].get('is_active', True)
            db_channels[str(channel_id)]['is_active'] = not current_status
            await self.set_db_channels(db_channels)
            return not current_status
        return None

    # ✅ BOT SETTINGS FUNCTIONS

    async def set_bot_settings(self, settings_data: dict):
        """Store bot settings to database for persistence across bot restarts"""
        await self.user_data.update_one(
            {"_id": "bot_settings"},
            {"$set": {"settings": settings_data}},
            upsert=True
        )

    async def get_bot_settings(self) -> dict:
        """Get bot settings from database"""
        data = await self.user_data.find_one({"_id": "bot_settings"})
        return data.get("settings", {}) if data else {}

    async def update_bot_setting(self, key: str, value):
        """Update a single bot setting"""
        current_data = await self.get_bot_settings()
        current_data[key] = value
        await self.set_bot_settings(current_data)

    async def get_bot_setting(self, key: str, default=None):
        """Get a single bot setting with default fallback"""
        settings = await self.get_bot_settings()
        return settings.get(key, default)

    # ✅ MESSAGES SETTINGS FUNCTIONS

    async def set_messages_settings(self, messages_data: dict):
        """Store messages settings to database for persistence across bot restarts"""
        await self.user_data.update_one(
            {"_id": "messages_settings"},
            {"$set": {"messages": messages_data}},
            upsert=True
        )

    async def get_messages_settings(self) -> dict:
        """Get messages settings from database"""
        data = await self.user_data.find_one({"_id": "messages_settings"})
        return data.get("messages", {}) if data else {}

    async def update_message_setting(self, key: str, value: str):
        """Update a single message setting"""
        current_data = await self.get_messages_settings()
        current_data[key] = value
        await self.set_messages_settings(current_data)

    async def get_message_setting(self, key: str, default: str = ""):
        """Get a single message setting with default fallback"""
        messages = await self.get_messages_settings()
        return messages.get(key, default)

    # ✅ CUSTOM CAPTION FUNCTIONS
    async def set_caption(self, caption: str):
        """Store custom caption template in database"""
        await self.user_data.update_one(
            {"_id": "custom_caption"},
            {"$set": {"caption": caption}},
            upsert=True
        )

    async def get_caption(self) -> str | None:
        """Get custom caption template from database"""
        data = await self.user_data.find_one({"_id": "custom_caption"})
        return data.get("caption") if data else None

    async def del_caption(self):
        """Delete custom caption template from database"""
        await self.user_data.delete_one({"_id": "custom_caption"})

    # ✅ ADMIN SETTINGS FUNCTIONS (Collection: "admins")

    async def get_admins_list(self) -> list:
        """Get all admin IDs from the 'admins' collection"""
        try:
            admins = []
            async for doc in self.admins_data.find({}):
                doc_id = doc.get("_id")
                if isinstance(doc_id, int):
                    admins.append(doc_id)
                elif isinstance(doc_id, str) and doc_id.lstrip("-").isdigit():
                    admins.append(int(doc_id))
            
            # Migration check: if admins collection is empty, check legacy user_data doc
            if not admins:
                legacy = await self.user_data.find_one({"_id": "admins_list"})
                if legacy and legacy.get("admins"):
                    for a_id in legacy.get("admins", []):
                        if isinstance(a_id, (int, str)) and str(a_id).lstrip("-").isdigit():
                            int_id = int(a_id)
                            admins.append(int_id)
                            await self.admins_data.update_one(
                                {"_id": int_id},
                                {"$set": {"_id": int_id, "added_at": datetime.now()}},
                                upsert=True
                            )
            return list(set(admins))
        except Exception as e:
            print(f"Error getting admins list: {e}")
            return []

    async def set_admins_list(self, admins_list: list):
        """Store/sync admins list to 'admins' collection"""
        try:
            target_ids = set()
            for a_id in admins_list:
                if isinstance(a_id, (int, str)) and str(a_id).lstrip("-").isdigit():
                    int_id = int(a_id)
                    target_ids.add(int_id)
                    await self.admins_data.update_one(
                        {"_id": int_id},
                        {"$set": {"_id": int_id, "updated_at": datetime.now()}},
                        upsert=True
                    )
            # Remove any admins not in the new list
            if target_ids:
                await self.admins_data.delete_many({"_id": {"$nin": list(target_ids)}})
            else:
                await self.admins_data.delete_many({})
            return True
        except Exception as e:
            print(f"Error setting admins list: {e}")
            return False

    async def add_admin(self, admin_id: int):
        """Add an admin to the 'admins' collection"""
        try:
            int_id = int(admin_id)
            await self.admins_data.update_one(
                {"_id": int_id},
                {"$set": {"_id": int_id, "added_at": datetime.now()}},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error adding admin {admin_id}: {e}")
            return False

    async def remove_admin(self, admin_id: int):
        """Remove an admin from the 'admins' collection"""
        try:
            int_id = int(admin_id)
            await self.admins_data.delete_one({"_id": int_id})
            return True
        except Exception as e:
            print(f"Error removing admin {admin_id}: {e}")
            return False

    async def is_admin(self, admin_id: int) -> bool:
        """Check if user is in 'admins' collection"""
        try:
            int_id = int(admin_id)
            doc = await self.admins_data.find_one({"_id": int_id})
            return doc is not None
        except Exception:
            return False

    # ✅ BATCH SETTINGS FUNCTIONS

    async def save_all_settings(self, bot_settings: dict, messages: dict, admins: list):
        """Save all settings in a single transaction for efficiency"""
        try:
            await self.set_bot_settings(bot_settings)
            await self.set_messages_settings(messages)
            await self.set_admins_list(admins)
            return True
        except Exception as e:
            print(f"Error saving all settings: {e}")
            return False

    async def load_all_settings(self) -> dict:
        """Load all settings in a single call for efficiency"""
        try:
            bot_settings = await self.get_bot_settings()
            messages = await self.get_messages_settings()
            admins = await self.get_admins_list()
            shortner_settings = await self.get_shortner_settings()
            
            return {
                "bot_settings": bot_settings,
                "messages": messages,
                "admins": admins,
                "shortner_settings": shortner_settings
            }
        except Exception as e:
            print(f"Error loading all settings: {e}")
            return {
                "bot_settings": {},
                "messages": {},
                "admins": [],
                "shortner_settings": {}
            }

    # ✅ CREDITS (credits-enabled bot only)
    # These methods let database errors propagate: callers must refuse delivery when they raise.
    #
    # credits:         {_id: user_id, balance, earned, spent, updated_at}
    # credit_rewards:  {_id: verify token, user_id, amount, created_at}  — unique, never sliced
    # verify_tokens:   {_id: token, user_id, payload, status: issued|claimed|rewarded,
    #                   short_link, created_at, expires_at (TTL), claimed_at}

    async def ensure_credit_indexes(self):
        await self.verify_tokens.create_index("expires_at", expireAfterSeconds=0)
        await self.verify_tokens.create_index([("user_id", 1), ("payload", 1), ("status", 1)])
        await self.credit_rewards.create_index("user_id")

    async def get_credits(self, user_id: int) -> int:
        doc = await self.credits.find_one({"_id": user_id}, {"balance": 1})
        return int(doc.get("balance", 0)) if doc else 0

    async def spend_credit(self, user_id: int, amount: int) -> int | None:
        """Atomically deduct `amount`. Returns the new balance, or None if the balance is insufficient."""
        doc = await self.credits.find_one_and_update(
            {"_id": user_id, "balance": {"$gte": amount}},
            {"$inc": {"balance": -amount, "spent": amount}, "$set": {"updated_at": _utcnow()}},
            return_document=ReturnDocument.AFTER,
        )
        return None if doc is None else int(doc["balance"])

    async def refund_credit(self, user_id: int, amount: int):
        await self.credits.update_one(
            {"_id": user_id},
            {"$inc": {"balance": amount, "spent": -amount}, "$set": {"updated_at": _utcnow()}},
        )

    async def award_credits_once(self, user_id: int, reward_id: str, amount: int) -> bool:
        """
        Add `amount` credits for `reward_id` exactly once.

        The unique `_id` on `credit_rewards` is the replay guard (it is never truncated).
        Prefers a replica-set transaction so a crash cannot record the token without
        incrementing the balance. If transactions are unavailable, falls back to
        insert-then-increment with a compensating delete on increment failure.
        """
        now = _utcnow()
        ledger = {
            "_id": reward_id,
            "user_id": user_id,
            "amount": amount,
            "created_at": now,
        }
        increment = {
            "$inc": {"balance": amount, "earned": amount},
            "$set": {"updated_at": now},
            "$setOnInsert": {"spent": 0, "created_at": now},
        }

        async def _apply(session=None):
            kwargs = {"session": session} if session is not None else {}
            try:
                await self.credit_rewards.insert_one(ledger, **kwargs)
            except DuplicateKeyError:
                return False
            try:
                await self.credits.update_one(
                    {"_id": user_id}, increment, upsert=True, **kwargs
                )
            except Exception:
                if session is None:
                    await self.credit_rewards.delete_one({"_id": reward_id})
                raise
            return True

        try:
            async with await self.client.start_session() as session:
                async with session.start_transaction():
                    return await _apply(session)
        except DuplicateKeyError:
            return False
        except Exception:
            return await _apply()

    async def create_verify_token(self, user_id: int, payload: str, ttl_seconds: int) -> dict:
        now = _utcnow()
        doc = {
            "_id": secrets.token_urlsafe(16),
            "user_id": user_id,
            "payload": payload,
            "status": "issued",
            "short_link": None,
            "created_at": now,
            "expires_at": now + timedelta(seconds=ttl_seconds),
        }
        await self.verify_tokens.insert_one(doc)
        return doc

    async def find_open_verify_token(self, user_id: int, payload: str, min_remaining_seconds: int) -> dict | None:
        """An unredeemed token for the same user + link that is still valid long enough to reuse."""
        return await self.verify_tokens.find_one({
            "user_id": user_id,
            "payload": payload,
            "status": "issued",
            "short_link": {"$ne": None},
            "expires_at": {"$gt": _utcnow() + timedelta(seconds=min_remaining_seconds)},
        })

    async def set_verify_short_link(self, token: str, short_link: str):
        await self.verify_tokens.update_one({"_id": token, "status": "issued"}, {"$set": {"short_link": short_link}})

    async def discard_verify_token(self, token: str):
        await self.verify_tokens.delete_one({"_id": token, "status": "issued"})

    async def claim_verify_token(self, token: str, user_id: int, min_age_seconds: int) -> tuple[str, dict | None]:
        """
        Atomically move a token issued -> claimed for its owner. Returns (status, doc):
          "claimed"  - caller may apply the reward (also returned for a token left claimed by an
                       interrupted earlier attempt; award_credits_once keeps that idempotent)
          "used"     - reward already applied
          "expired" | "too_fast" | "invalid"
        """
        now = _utcnow()
        doc = await self.verify_tokens.find_one_and_update(
            {
                "_id": token,
                "user_id": user_id,
                "status": "issued",
                "expires_at": {"$gt": now},
                "created_at": {"$lte": now - timedelta(seconds=min_age_seconds)},
            },
            {"$set": {"status": "claimed", "claimed_at": now}},
            return_document=ReturnDocument.AFTER,
        )
        if doc:
            return "claimed", doc
        existing = await self.verify_tokens.find_one({"_id": token})
        if not existing or existing.get("user_id") != user_id:
            return "invalid", None
        if existing["status"] == "rewarded":
            return "used", existing
        if existing["expires_at"] <= now:
            return "expired", None
        if existing["status"] == "claimed":
            return "claimed", existing
        return "too_fast", None

    async def mark_verify_token_rewarded(self, token: str):
        await self.verify_tokens.update_one({"_id": token}, {"$set": {"status": "rewarded"}})

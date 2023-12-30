from pymongo import MongoClient
import bcrypt
from pymongo.errors import DuplicateKeyError
import logging


class DB:
    def __init__(self):
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['p2p-chat']

    def is_account_exist(self, username):
        return len(list(self.db.accounts.find({'username': username}))) > 0

    def register(self, username, password):
        if len(username) < 3:
            return "join-failed-username"
        if len(password) < 5:
            return "join-failed-password"

        hashed_password = bcrypt.hashpw(
            password.encode('utf-8'), bcrypt.gensalt())
        account = {
            "username": username,
            "password": hashed_password
        }
        self.db.accounts.insert_one(account)
        return "join-success"

    def get_password(self, username, password):
        hashed = self.db.accounts.find_one({"username": username})["password"]
        return bcrypt.checkpw(password.encode('utf-8'), hashed)

    def is_account_online(self, username):
        return len(list(self.db.online_peers.find({"username": username}))) > 0

    def user_login(self, username, ip, port):
        online_peer = {
            "username": username,
            "ip": ip,
            "port": port
        }
        self.db.online_peers.insert_one(online_peer)

    def user_logout(self, username):
        self.db.online_peers.delete_one({"username": username})

    def get_peer_ip_port(self, username):
        res = self.db.online_peers.find_one({"username": username})
        return (res["ip"], res["port"])

    def is_address_connected(self, ip, port):
        return len(list(self.db.online_peers.find({"ip": ip, "port": port}))) > 0

    def get_online_users(self):
        projection = {'username': 1, '_id': 0}
        return list(self.db.online_peers.find({}, projection))

    def get_rooms(self):
        projection = {'_id': 0, 'roomId': 1}
        return list(self.db.rooms.find({}, projection))

    def is_room_exist(self, roomId):
        return bool(self.db.rooms.find_one({'roomId': roomId}))

    def create_room(self, roomId):
        print(self.is_room_exist(roomId))
        if self.is_room_exist(roomId):
            return False
        room = {"peers": [], "roomId": roomId}
        self.db.rooms.insert_one(room)
        return True

    def get_room_users(self, roomId):
        res = self.db.rooms.find_one({"roomId": roomId})
        return res.get("peers", [])

    def update_room(self, roomId, peer):
        projection = {"roomId": roomId}
        update_data = {"$push": {"peers": peer}}
        self.db.rooms.update_one(projection, update_data)
        logging.info(f"Room {roomId} updated with new peers.")

    def remove_user(self, roomId, peer):
        projection = {"roomId": roomId}
        update_data = {"$pull": {"peers": peer}}
        self.db.rooms.update_one(projection, update_data)
        logging.info(f"User {peer} removed from room {roomId}.")

    def remove_room(self, roomId):
        if not self.is_room_exist(roomId):
            logging.error(f"Error removing room {roomId}. Room not found.")
            return False

        self.db.rooms.delete_one({"roomId": roomId})
        logging.info(f"Room {roomId} removed.")
        return True

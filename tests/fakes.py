class FakeRedis:
    def __init__(self):
        self.storage = {}
        self.expiry = {}

    async def set(self, key, value, ex=None, nx=False):
        if nx and key in self.storage:
            return False
        self.storage[key] = value
        self.expiry[key] = ex
        return True

    async def get(self, key):
        return self.storage.get(key)

    async def delete(self, key):
        self.storage.pop(key, None)
        self.expiry.pop(key, None)
        return True

    async def incr(self, key):
        value = int(self.storage.get(key, 0)) + 1
        self.storage[key] = value
        return value

    async def expire(self, key, seconds):
        self.expiry[key] = seconds
        return True

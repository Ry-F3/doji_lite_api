# api_counter.py
class APICounter:
    def __init__(self):
        self.count = 0

    def increment(self):
        self.count += 1

    def get_count(self):
        return self.count


# Singleton instance
api_counter = APICounter()
